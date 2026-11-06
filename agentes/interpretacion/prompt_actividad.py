"""Constructor del prompt de actividad (documento .txt para el Agente 2).

El Agente 1 produce una ``solicitud_normalizada``. Con esos datos y el texto
COMPLETO de las partes citadas del material, este modulo arma el documento de
texto plano que el Agente 2 (generador de la actividad) consume.

El resultado es un ``str`` UTF-8 listo para guardarse como
``{solicitud_id}/v{n}_actividad.txt`` en el bucket ``prompts`` de Supabase.

Modulo puro: no usa red ni base de datos, para poder testearlo aislado.
"""

VERSION_PROMPT = "1.0"

SIN_DATO = "(no informado)"

REGLAS = """REGLAS
1. Usa unicamente el material autorizado que aparece arriba. No agregues contenido externo.
2. No inventes datos, fechas, nombres ni conceptos que no esten en el material.
3. La actividad debe ser autocontenida y resoluble por el estudiante sin conexion a internet.
4. Adapta la dificultad y el vocabulario al nivel indicado.
5. Cada criterio de evaluacion debe poder verificarse con lo que el estudiante produce en la actividad.
6. No incluyas la clave de correccion dentro del mismo archivo visible para el estudiante,
   salvo que la consigna lo pida explicitamente.
7. Devuelve SOLO el archivo HTML completo, sin explicaciones ni texto adicional.
"""

SALIDA_ESPERADA = """SALIDA ESPERADA
Un unico documento HTML5 completo, con CSS y JavaScript embebidos en el mismo archivo
(<style> y <script>), que funcione al abrirlo directamente en un navegador.
"""


def _texto(valor, defecto=SIN_DATO):
    """Normaliza un valor a texto limpio."""
    if valor is None:
        return defecto
    if isinstance(valor, str):
        limpio = valor.strip()
        return limpio if limpio else defecto
    return str(valor)


def _lista(valor):
    """Normaliza un valor a lista de textos no vacios."""
    if isinstance(valor, list):
        return [str(x).strip() for x in valor if str(x).strip()]
    if isinstance(valor, str) and valor.strip():
        return [valor.strip()]
    return []


def _normalizar_partes(partes):
    """Acepta {id: texto} o [{id, texto}] y devuelve una lista ordenada [(id, texto)]."""
    if isinstance(partes, dict):
        return [(str(k), str(v or "")) for k, v in partes.items()]
    resultado = []
    for parte in partes or []:
        if isinstance(parte, dict):
            resultado.append((str(parte.get("id", "")), str(parte.get("texto", ""))))
        elif isinstance(parte, (list, tuple)) and len(parte) == 2:
            resultado.append((str(parte[0]), str(parte[1] or "")))
    return resultado


def construir_prompt_actividad(datos, partes, docente="", curso="", pedido="",
                               solicitud_id="", version_contrato="1.0"):
    """Arma el documento .txt que consume el Agente 2.

    datos         -> dict ``datos`` de la solicitud_normalizada.
    partes        -> dict ``{id: texto}`` o lista ``[{id, texto}]`` con el texto
                     COMPLETO de las partes del material que se autorizan.
    docente       -> nombre del docente que hizo la solicitud.
    curso         -> curso/comision de la solicitud.
    pedido        -> pedido original del docente (texto libre).
    solicitud_id  -> UUID de la fila en ``solicitudes``.
    version_contrato -> version del contrato de la solicitud_normalizada.

    Devuelve un ``str`` en UTF-8.
    """
    datos = datos or {}
    criterios = _lista(datos.get("criterios"))
    partes_norm = _normalizar_partes(partes)

    lineas = []
    lineas.append("ROL")
    lineas.append(
        "Sos el Agente 2 (Generacion) de un banco de actividades escolar. "
        "Tu tarea es crear UNA actividad educativa a partir de la solicitud normalizada "
        "y del material autorizado que se detallan abajo."
    )
    lineas.append("")

    lineas.append("RESTRICCION TECNOLOGICA (obligatoria)")
    lineas.append("- Solo HTML, CSS y JavaScript vanilla.")
    lineas.append("- Sin librerias, frameworks, CDN ni dependencias externas.")
    lineas.append("- Todo el CSS y el JavaScript deben ir embebidos en el mismo archivo HTML.")
    lineas.append("- Debe funcionar abriendo el archivo en el navegador, sin servidor ni conexion.")
    lineas.append("")

    lineas.append("DATOS DE LA SOLICITUD")
    lineas.append("solicitud_id: %s" % _texto(solicitud_id))
    lineas.append("version_contrato: %s" % _texto(version_contrato))
    lineas.append("docente: %s" % _texto(docente))
    lineas.append("curso: %s" % _texto(curso or datos.get("comision")))
    lineas.append("materia: %s" % _texto(datos.get("materia")))
    lineas.append("modalidad: %s" % _texto(datos.get("modalidad")))
    lineas.append("vigencia_hasta: %s" % _texto(datos.get("vigencia_hasta")))
    lineas.append("nivel: %s" % _texto(datos.get("nivel")))
    lineas.append("tema: %s" % _texto(datos.get("tema")))
    lineas.append("objetivo: %s" % _texto(datos.get("objetivo")))
    lineas.append("material_id: %s" % _texto(datos.get("material_id")))
    ids_partes = _lista(datos.get("partes")) or [pid for pid, _ in partes_norm]
    lineas.append("partes: %s" % (", ".join(ids_partes) if ids_partes else SIN_DATO))
    lineas.append("")

    lineas.append("CRITERIOS DE EVALUACION (la actividad debe permitir verificarlos)")
    if criterios:
        for indice, criterio in enumerate(criterios, start=1):
            lineas.append("%d. %s" % (indice, criterio))
    else:
        lineas.append(SIN_DATO)
    lineas.append("")

    lineas.append("MATERIAL AUTORIZADO (unica fuente de contenido; texto completo)")
    if partes_norm:
        for parte_id, texto in partes_norm:
            lineas.append("--- %s ---" % _texto(parte_id, "(sin id)"))
            lineas.append(texto.strip() if texto.strip() else "(parte sin texto)")
    else:
        lineas.append(SIN_DATO)
    lineas.append("")

    lineas.append("CONSIGNA ORIGINAL DEL DOCENTE (texto literal)")
    lineas.append(_texto(pedido))
    lineas.append("")

    lineas.append(REGLAS.rstrip())
    lineas.append("")
    lineas.append(SALIDA_ESPERADA.rstrip())
    lineas.append("")

    return "\n".join(lineas)
