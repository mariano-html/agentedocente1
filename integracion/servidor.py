"""Servidor local de integracion.

Sirve el front (Aula IA.html) y lo conecta con el Agente 1 de interpretacion.
El front no se modifica: el puente se inyecta al servir la pagina.

Uso:
    python integracion/servidor.py
    Abrir http://localhost:8000
"""

import base64
import io
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(BASE_DIR)
sys.path.insert(0, os.path.join(RAIZ, "agentes", "interpretacion"))
sys.path.insert(0, BASE_DIR)

import agente_interpretacion as agente  # noqa: E402
import prompt_actividad  # noqa: E402
from lectura_pdf import ErrorPDF, material_desde_pdf, extraer_texto_pdf  # noqa: E402

try:
    from supabase_config import supabase_manager
    SUPABASE_ACTIVO = supabase_manager.client is not None
except Exception:
    supabase_manager = None
    SUPABASE_ACTIVO = False

ARCHIVO_HTML = "Aula IA (1).html"
PUERTO = 8000
ETIQUETA_PUENTE = '<script src="/puente.js"></script>'
MATERIAL_ID = "MAT-01"

CURSOS_PREDETERMINADOS_FALLBACK = [
    {"nombre": "1er Año - M. Curie", "anio": "1er Año", "orden": 1},
    {"nombre": "1er Año - R. Favaloro", "anio": "1er Año", "orden": 2},
    {"nombre": "1er Año - C. Milstein", "anio": "1er Año", "orden": 3},
    {"nombre": "2do Año - C. Grierson", "anio": "2do Año", "orden": 4},
    {"nombre": "2do Año - B. Houssay", "anio": "2do Año", "orden": 5},
    {"nombre": "2do Año - A. Moreau de Justo", "anio": "2do Año", "orden": 6},
    {"nombre": "3er Año - E. Bachofen", "anio": "3er Año", "orden": 7},
    {"nombre": "3er Año - F. Leloir", "anio": "3er Año", "orden": 8},
    {"nombre": "3er Año - A. Perez Esquivel", "anio": "3er Año", "orden": 9},
    {"nombre": "4to Año - I. Lehmann", "anio": "4to Año", "orden": 10},
    {"nombre": "4to Año - A. Lovelace", "anio": "4to Año", "orden": 11},
    {"nombre": "4to Año - M. Sadosky", "anio": "4to Año", "orden": 12},
    {"nombre": "5to Año - J. Backus", "anio": "5to Año", "orden": 13},
    {"nombre": "5to Año - C. Berdichevski", "anio": "5to Año", "orden": 14},
    {"nombre": "5to Año - E. Mortola", "anio": "5to Año", "orden": 15},
]


def _decodificar(archivos):
    """Convierte los archivos subidos (solo PDF) en streams de bytes."""
    streams = []
    avisos = []
    for archivo in archivos or []:
        nombre = archivo.get("nombre", "")
        if not nombre.lower().endswith(".pdf"):
            avisos.append("Se ignoro el archivo no-PDF: %s." % nombre)
            continue
        try:
            datos = base64.b64decode(archivo.get("contenido_base64", ""))
        except Exception:
            avisos.append("No se pudo leer el archivo: %s." % nombre)
            continue
        streams.append(io.BytesIO(datos))
    return streams, avisos


def _extracto(texto, limite=140):
    """Recorta el texto de una parte para mostrarlo como vista previa."""
    limpio = " ".join((texto or "").replace("*", "").replace("`", "").split())
    if len(limpio) > limite:
        corte = limpio.rfind(" ", 0, limite)
        limpio = limpio[:corte if corte > 0 else limite] + "..."
    return limpio


def procesar(entrada):
    """Recibe la entrada del front y devuelve la solicitud_normalizada."""
    formulario = entrada.get("formulario") or {}
    pedido = entrada.get("pedido") or ""
    aportes = entrada.get("aportes") or {}
    streams, avisos = _decodificar(entrada.get("archivos"))

    if streams:
        try:
            material = material_desde_pdf(streams, MATERIAL_ID)
            # Guardar material en Supabase si está disponible
            if SUPABASE_ACTIVO and supabase_manager:
                try:
                    texto_completo = "\n\n".join([p.get("texto", "") for p in material.get("partes", [])])
                    for stream in streams:
                        stream.seek(0)
                        nombre = entrada.get("archivos", [{}])[0].get("nombre", "material.pdf")
                        supabase_manager.guardar_material(nombre, texto_completo, MATERIAL_ID)
                        break
                except Exception as e:
                    print(f"[Supabase] Error al guardar material: {e}")
        except ErrorPDF as error:
            return agente._respuesta(False, {}, [str(error)])
    else:
        material = {}

    resultado = agente.interpretar(pedido, formulario, material, aportes=aportes)

    datos = resultado.get("datos") or {}
    usados = datos.get("partes") or []
    textos = {p.get("id"): p.get("texto", "") for p in material.get("partes", [])}
    if usados:
        resultado["material_usado"] = [
            {"id": pid, "extracto": _extracto(textos.get(pid, ""))} for pid in usados
        ]

    if avisos:
        resultado["avisos"] = avisos

    # Guardar solicitud en Supabase si está disponible
    if SUPABASE_ACTIVO and supabase_manager:
        docente_nombre = entrada.get("docente") or formulario.get("docente")
        curso_nombre = formulario.get("comision")
        solicitud_id = None
        try:
            solicitud_id = supabase_manager.guardar_solicitud(
                entrada, resultado, docente_nombre, curso_nombre)
        except Exception as e:
            print(f"[Supabase] Error al guardar solicitud: {e}")

        # El prompt para el Agente 2 solo se genera cuando la solicitud esta completa.
        if solicitud_id and resultado.get("ok"):
            try:
                partes_prompt = [(pid, textos.get(pid, "")) for pid in usados]
                contenido = prompt_actividad.construir_prompt_actividad(
                    datos=datos,
                    partes=partes_prompt,
                    docente=docente_nombre or "",
                    curso=curso_nombre or "",
                    pedido=pedido,
                    solicitud_id=solicitud_id,
                    version_contrato=resultado.get("version_contrato", "1.0"),
                )
                registro = supabase_manager.guardar_prompt(solicitud_id, contenido)
                if registro:
                    resultado["prompt"] = {
                        "guardado": True,
                        "solicitud_id": solicitud_id,
                        "prompt_id": registro.get("id"),
                        "version": registro.get("version"),
                        "nombre_archivo": registro.get("nombre_archivo"),
                        "storage_path": registro.get("storage_path"),
                        "url": supabase_manager.url_publica_prompt(registro.get("storage_path")),
                    }
                else:
                    resultado.setdefault("avisos", []).append(
                        "La solicitud se guardo, pero el prompt no se pudo guardar en Storage.")
            except Exception as e:
                print(f"[Supabase] Error al generar/guardar el prompt: {e}")
                resultado.setdefault("avisos", []).append(
                    "La solicitud se guardo, pero el prompt no se pudo generar.")

    return resultado


class Manejador(BaseHTTPRequestHandler):
    def _enviar(self, codigo, cuerpo, tipo):
        if isinstance(cuerpo, str):
            cuerpo = cuerpo.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _json(self, codigo, objeto):
        self._enviar(codigo, json.dumps(objeto, ensure_ascii=False),
                     "application/json; charset=utf-8")

    def do_GET(self):
        ruta = urlparse(self.path)
        if ruta.path in ("/", "/index.html"):
            with open(os.path.join(RAIZ, ARCHIVO_HTML), encoding="utf-8") as archivo:
                html = archivo.read()
            if ETIQUETA_PUENTE not in html:
                html = html.replace("</body>", ETIQUETA_PUENTE + "\n</body>")
            self._enviar(200, html, "text/html; charset=utf-8")
        elif ruta.path == "/puente.js":
            with open(os.path.join(BASE_DIR, "puente.js"), encoding="utf-8") as archivo:
                self._enviar(200, archivo.read(), "application/javascript; charset=utf-8")
        elif ruta.path == "/api/cursos":
            cursos = []
            if SUPABASE_ACTIVO and supabase_manager:
                try:
                    cursos = supabase_manager.obtener_cursos_predeterminados()
                except Exception:
                    cursos = []
            if not cursos:
                cursos = CURSOS_PREDETERMINADOS_FALLBACK
            self._json(200, {"cursos": cursos})
        elif ruta.path.startswith("/api/prompt/"):
            self._prompt(ruta)
        else:
            self._json(404, {"error": "No encontrado"})

    def _prompt(self, ruta):
        """Devuelve el .txt del prompt como text/plain (para el Agente 2)."""
        solicitud_id = ruta.path[len("/api/prompt/"):].strip("/")
        if not solicitud_id:
            self._json(400, {"error": "Falta solicitud_id"})
            return
        if not (SUPABASE_ACTIVO and supabase_manager):
            self._json(503, {"error": "Supabase no disponible"})
            return
        version = None
        parametros = parse_qs(ruta.query)
        if parametros.get("version"):
            try:
                version = int(parametros["version"][0])
            except ValueError:
                self._json(400, {"error": "version invalida"})
                return
        contenido = supabase_manager.obtener_contenido_prompt(solicitud_id, version)
        if contenido is None:
            self._json(404, {"error": "No hay prompt guardado para esa solicitud"})
            return
        self._enviar(200, contenido, "text/plain; charset=utf-8")

    def do_POST(self):
        if self.path != "/api/interpretar":
            self._json(404, {"error": "No encontrado"})
            return
        largo = int(self.headers.get("Content-Length", 0))
        crudo = self.rfile.read(largo) if largo else b""
        try:
            entrada = json.loads(crudo or b"{}")
        except ValueError:
            self._json(400, {"error": "JSON invalido"})
            return
        try:
            resultado = procesar(entrada)
        except Exception as error:
            resultado = agente._respuesta(False, {}, ["Error interno del servidor: %s" % error])
        self._json(200, resultado)

    def log_message(self, formato, *args):
        sys.stderr.write("[servidor] %s\n" % (formato % args))


def main():
    agente.cargar_env(os.path.join(RAIZ, "agentes", "interpretacion", ".env"))
    servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador)
    print("Agente 1 escuchando en http://localhost:%d" % PUERTO)
    print("Ctrl+C para detener.")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nDetenido.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
