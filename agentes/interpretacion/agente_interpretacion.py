"""Agente 1 - Interpretacion (back).

Convierte el pedido libre de un docente en una solicitud_normalizada, la
estructura ordenada que entienden los demas componentes.

Regla central: NO inventa. Si un dato no puede deducirse del pedido ni del
material autorizado, lo devuelve en "faltantes" para que el docente lo complete.

El modelo de IA es configurable por variables de entorno (OpenRouter u otro
servicio compatible). Ver README.md.
"""

import argparse
import json
import os
import re

import requests

from lectura_pdf import ErrorPDF, material_desde_pdf

VERSION_CONTRATO = "1.0"
MODELO_DEFECTO = "openrouter/free"
BASE_URL_DEFECTO = "https://openrouter.ai/api/v1"
TIEMPO_ESPERA = 60

CAMPOS_FORMULARIO = ("materia", "comision", "modalidad", "vigencia_hasta")

INSTRUCCIONES = """Sos el Agente 1 (Interpretacion) de un banco de actividades escolar.
Tu unica tarea es convertir el pedido de un docente en una solicitud ordenada.

Recibis el pedido libre del docente, los datos del formulario y el material
autorizado dividido en partes numeradas (por ejemplo F01, F02).

Devolve SOLO un objeto JSON, sin texto extra, con esta forma:
{
  "tema": "texto",
  "objetivo": "texto",
  "nivel": "texto",
  "criterios": ["texto", "texto"],
  "partes": ["F02", "F03"],
  "faltantes": ["nombre del campo que falta"]
}

Reglas:
1. Usa unicamente el material autorizado. No agregues contenidos que no esten en las partes.
2. DEDUCE tema, objetivo, nivel y criterios a partir del pedido del docente y del material autorizado.
3. Solo deja un campo vacio si NO hay ninguna pista en el pedido ni en el material.
4. Para los "criterios" de evaluación, propone 2 a 4 criterios claros, medibles y acordes al tema usando ÚNICAMENTE el material.
5. "partes" solo puede contener ids que existan en el material, y solo los que correspondan al tema.
6. Si el tema pedido no aparece en el material, deja "partes": [] y agrega "tema" a "faltantes".
7. Responde unicamente con el objeto JSON: sin bloques de codigo, sin markdown y sin texto antes ni despues.
8. Si el mensaje incluye "Datos aportados por el docente", usalos tal cual y tienen PRIORIDAD ABSOLUTA: no los marques como faltantes.

Ejemplo de salida valida:
{"tema":"Ciclos en Python","objetivo":"Practicar el ciclo for","nivel":"Intermedio","criterios":["Usa el ciclo for correctamente"],"partes":["F02"],"faltantes":[]}
"""

# Cargar guia del proyecto para que el agente siempre la tenga en contexto
try:
    _BASE_DIR_AGENTE = os.path.dirname(os.path.abspath(__file__))
    _ROOT_DIR_PROYECTO = os.path.dirname(os.path.dirname(_BASE_DIR_AGENTE))
    _AGENTS_PATH = os.path.join(_ROOT_DIR_PROYECTO, "Agents.md")
    if os.path.exists(_AGENTS_PATH):
        with open(_AGENTS_PATH, encoding="utf-8") as _f_agents:
            _AGENTS_MD_CONTENIDO = _f_agents.read()
        if _AGENTS_MD_CONTENIDO.strip():
            INSTRUCCIONES = INSTRUCCIONES + "\n\n## GUÍA DEL PROYECTO (Agents.md)\n" + _AGENTS_MD_CONTENIDO
except Exception:
    pass


class ErrorModelo(Exception):
    """Error al comunicarse con el modelo de IA."""


def preguntar_al_modelo(mensajes, model=None, api_key=None, base_url=None):
    """Llama al modelo y devuelve el texto de la respuesta (formato JSON)."""
    api_key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ErrorModelo("Falta OPENROUTER_API_KEY. Cargala en el entorno o en un archivo .env.")
    model = model or os.getenv("OPENROUTER_MODEL", MODELO_DEFECTO)
    base_url = (base_url or os.getenv("OPENROUTER_BASE_URL", BASE_URL_DEFECTO)).rstrip("/")

    try:
        respuesta = requests.post(
            base_url + "/chat/completions",
            headers={
                "Authorization": "Bearer " + api_key,
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": mensajes,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
            timeout=TIEMPO_ESPERA,
        )
    except requests.RequestException as error:
        raise ErrorModelo("No se pudo contactar al modelo: %s" % error)
    if respuesta.status_code != 200:
        raise ErrorModelo("El modelo devolvio %s: %s" % (respuesta.status_code, respuesta.text[:300]))
    try:
        contenido = respuesta.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError):
        raise ErrorModelo("El modelo devolvio una respuesta con formato inesperado.")
    if not contenido:
        raise ErrorModelo("El modelo devolvio una respuesta vacia (sin contenido).")
    return contenido


def armar_mensajes(pedido, formulario, material, aportes=None):
    """Arma los mensajes (system + usuario) que recibe el modelo."""
    lineas = []
    for parte in material.get("partes", []):
        lineas.append("- %s: %s" % (parte.get("id"), parte.get("texto", "")))
    partes_texto = "\n".join(lineas)

    usuario = (
        "Pedido del docente:\n%s\n\n"
        "Datos del formulario:\n"
        "- materia: %s\n"
        "- comision: %s\n"
        "- modalidad: %s\n"
        "- vigencia_hasta: %s\n\n"
        % (
            pedido,
            formulario.get("materia"),
            formulario.get("comision"),
            formulario.get("modalidad"),
            formulario.get("vigencia_hasta"),
        )
    )
    aportes_texto = _aportes_texto(aportes)
    if aportes_texto:
        usuario += (
            "Datos aportados por el docente (usar tal cual, tienen prioridad):\n"
            "%s\n\n" % aportes_texto
        )
    usuario += "Material autorizado (material_id: %s):\n%s" % (
        material.get("material_id"), partes_texto)
    return [
        {"role": "system", "content": INSTRUCCIONES},
        {"role": "user", "content": usuario},
    ]


def _texto(valor):
    if valor is None:
        return ""
    return valor.strip() if isinstance(valor, str) else str(valor)


def _a_lista(valor):
    if isinstance(valor, list):
        return [str(x).strip() for x in valor if str(x).strip()]
    if isinstance(valor, str) and valor.strip():
        return [valor.strip()]
    return []


def _aportes_texto(aportes):
    """Formatea los datos aportados por el docente como lineas legibles."""
    lineas = []
    for campo, valor in (aportes or {}).items():
        if isinstance(valor, list):
            valor = "; ".join(str(v) for v in valor if str(v).strip())
        valor = _texto(valor)
        if valor:
            lineas.append("- %s: %s" % (campo, valor))
    return "\n".join(lineas)


def _bloque_json(texto, inicio):
    """Devuelve el objeto balanceado que empieza en 'inicio', o None."""
    profundidad = 0
    en_texto = False
    escape = False
    for indice in range(inicio, len(texto)):
        caracter = texto[indice]
        if escape:
            escape = False
        elif caracter == "\\":
            escape = True
        elif caracter == '"':
            en_texto = not en_texto
        elif not en_texto and caracter == "{":
            profundidad += 1
        elif not en_texto and caracter == "}":
            profundidad -= 1
            if profundidad == 0:
                return texto[inicio:indice + 1]
    return None


def _extraer_json(texto):
    """Extrae el primer objeto JSON valido del texto del modelo."""
    if not isinstance(texto, str):
        raise ValueError("La respuesta del modelo no es texto.")
    limpio = re.sub(r"```[a-zA-Z]*", "", texto).replace("```", "")
    ultimo_error = None
    inicio = limpio.find("{")
    while inicio != -1:
        bloque = _bloque_json(limpio, inicio)
        if bloque is not None:
            try:
                return json.loads(bloque)
            except ValueError as error:
                ultimo_error = error
        inicio = limpio.find("{", inicio + 1)
    if ultimo_error is not None:
        raise ValueError("El JSON del modelo no se pudo interpretar: %s" % ultimo_error)
    raise ValueError("No hay JSON en la respuesta.")


def _respuesta(ok, datos, errores):
    return {
        "tipo": "solicitud_normalizada",
        "version_contrato": VERSION_CONTRATO,
        "ok": ok,
        "datos": datos,
        "errores": errores,
    }


def interpretar(pedido, formulario, material, llm=None, aportes=None):
    """Funcion principal del Agente 1.

    pedido     -> str con lo que escribio el docente.
    formulario -> dict con materia, comision, modalidad y vigencia_hasta.
    material   -> dict con material_id y una lista de partes [{id, texto}], o
                  una ruta (o lista de rutas) de PDFs para extraer el texto.
    llm        -> funcion opcional que recibe los mensajes y devuelve el JSON
                  del modelo. Por defecto usa OpenRouter.
    aportes    -> dict opcional con datos que completa el docente (tema,
                  objetivo, nivel, criterios). Se usan tal cual y tienen prioridad.

    Devuelve el contrato: tipo, version_contrato, ok, datos, errores.
    """
    formulario = formulario or {}
    aportes = aportes or {}
    errores = []

    if isinstance(material, (str, list, tuple)):
        try:
            material = material_desde_pdf(material)
        except ErrorPDF as error:
            return _respuesta(False, {}, [str(error)])
    material = material or {}

    if not _texto(pedido):
        errores.append("El pedido del docente esta vacio.")
    faltan_formulario = [c for c in CAMPOS_FORMULARIO if not _texto(formulario.get(c))]
    if faltan_formulario:
        errores.append("Faltan datos del formulario: " + ", ".join(faltan_formulario) + ".")
    partes = material.get("partes") or []
    if not partes:
        errores.append("El material no tiene partes cargadas.")
    if errores:
        return _respuesta(False, {}, errores)

    ids_validos = [p.get("id") for p in partes]
    llamar = llm or preguntar_al_modelo
    mensajes = armar_mensajes(pedido, formulario, material, aportes)
    crudo = None
    for intento in (1, 2):
        try:
            texto = llamar(mensajes)
        except ErrorModelo as error:
            return _respuesta(False, {}, [str(error)])
        if not texto:
            return _respuesta(False, {}, ["El modelo no devolvio una respuesta valida."])
        try:
            crudo = _extraer_json(texto)
            break
        except ValueError:
            if intento == 2:
                fragmento = _texto(texto)[:200]
                return _respuesta(False, {}, [
                    "El modelo no devolvio un JSON valido. Fragmento: " + fragmento])
            mensajes = mensajes + [
                {"role": "assistant", "content": texto},
                {"role": "user", "content": "Tu respuesta anterior no fue un JSON valido. "
                                            "Responde SOLO el objeto JSON, sin texto ni markdown."},
            ]

    partes_ok = []
    partes_inexistentes = []
    for parte_id in _a_lista(crudo.get("partes")):
        if parte_id in ids_validos:
            partes_ok.append(parte_id)
        else:
            partes_inexistentes.append(parte_id)

    datos = {
        "materia": formulario.get("materia"),
        "comision": formulario.get("comision"),
        "tema": _texto(crudo.get("tema")),
        "objetivo": _texto(crudo.get("objetivo")),
        "nivel": _texto(crudo.get("nivel")),
        "criterios": _a_lista(crudo.get("criterios")),
        "modalidad": formulario.get("modalidad"),
        "vigencia_hasta": formulario.get("vigencia_hasta"),
        "material_id": material.get("material_id"),
        "partes": partes_ok,
    }

    for campo in ("tema", "objetivo", "nivel", "criterios"):
        if not aportes.get(campo):
            continue
        if campo == "criterios":
            datos["criterios"] = _a_lista(aportes[campo])
        else:
            datos[campo] = _texto(aportes[campo])

    faltantes = _a_lista(crudo.get("faltantes"))
    for campo in ("tema", "objetivo", "nivel", "criterios"):
        if not datos[campo] and campo not in faltantes:
            faltantes.append(campo)
    faltantes = [campo for campo in faltantes if not datos.get(campo)]
    if not datos["partes"] and "partes" not in faltantes:
        faltantes.append("partes")

    if partes_inexistentes:
        errores.append("El modelo cito partes que no existen en el material: " + ", ".join(partes_inexistentes) + ".")
    if faltantes:
        datos["faltantes"] = faltantes
        errores.append("Falta informacion que el docente debe completar: " + ", ".join(faltantes) + ".")

    return _respuesta(not errores, datos, errores)


def cargar_env(ruta=".env"):
    """Carga variables desde un archivo .env sencillo (opcional)."""
    if not os.path.exists(ruta):
        return
    with open(ruta, encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            valor = valor.strip()
            if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in ("'", '"'):
                valor = valor[1:-1]
            os.environ.setdefault(clave.strip(), valor)


def main():
    parser = argparse.ArgumentParser(description="Agente 1 - Interpretacion del pedido docente.")
    parser.add_argument("--pdf", nargs="+", metavar="RUTA", help="Uno o mas PDFs para usar como material.")
    parser.add_argument("--material-id", default="MAT-01", help="Identificador del material (default: MAT-01).")
    args = parser.parse_args()

    base = os.path.dirname(os.path.abspath(__file__))
    cargar_env(os.path.join(base, ".env"))
    with open(os.path.join(base, "datos", "ejemplo_pedido.json"), encoding="utf-8") as archivo:
        entrada = json.load(archivo)

    if args.pdf:
        try:
            material = material_desde_pdf(args.pdf, args.material_id)
        except ErrorPDF as error:
            print(json.dumps(_respuesta(False, {}, [str(error)]), ensure_ascii=False, indent=2))
            return
    else:
        with open(os.path.join(base, "datos", "ejemplo_material.json"), encoding="utf-8") as archivo:
            material = json.load(archivo)

    resultado = interpretar(entrada["pedido"], entrada["formulario"], material)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
