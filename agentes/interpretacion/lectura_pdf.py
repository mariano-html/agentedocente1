"""Lectura de archivos PDF para el Agente 1.

Extrae el texto de uno o varios PDF y lo divide en partes numeradas
(F01, F02...), con el mismo formato de 'material' que usa el Agente 1.

Solo funciona con PDF que tengan texto seleccionable. Un PDF escaneado
(imagen) no tiene texto extraible y devuelve un error claro.
"""

import io
import os
import re

from pypdf import PdfReader


class ErrorPDF(Exception):
    """Error al leer un archivo PDF."""


def extraer_texto_pdf(fuente, nombre=None):
    """Devuelve todo el texto de un PDF.

    Acepta una ruta, bytes o un archivo abierto (por ejemplo un BytesIO).
    """
    if isinstance(fuente, (bytes, bytearray)):
        origen = io.BytesIO(fuente)
    elif hasattr(fuente, "read"):
        origen = fuente
    else:
        if not os.path.exists(fuente):
            raise ErrorPDF("No existe el archivo PDF: %s" % fuente)
        origen = fuente
    etiqueta = nombre or (fuente if isinstance(fuente, str) else "el PDF")

    try:
        lector = PdfReader(origen)
        paginas = [(pagina.extract_text() or "") for pagina in lector.pages]
    except Exception as error:
        raise ErrorPDF("No se pudo leer el PDF %s: %s" % (etiqueta, error))

    texto = "\n\n".join(paginas).strip()
    if not texto:
        raise ErrorPDF("El PDF %s no tiene texto extraible (puede ser un escaneo)." % etiqueta)
    return texto


def dividir_en_partes(texto):
    """Separa el texto en partes por parrafos y las numera F01, F02..."""
    bloques = [b.strip() for b in re.split(r"\n\s*\n", texto) if b.strip()]
    return [{"id": "F%02d" % indice, "texto": bloque} for indice, bloque in enumerate(bloques, start=1)]


def material_desde_pdf(fuente, material_id="MAT-01"):
    """Arma el 'material' del Agente 1 a partir de una o varias fuentes.

    Cada fuente puede ser una ruta, bytes o un archivo abierto.
    """
    if isinstance(fuente, (str, bytes, bytearray)) or hasattr(fuente, "read"):
        fuentes = [fuente]
    else:
        fuentes = list(fuente)
    textos = [extraer_texto_pdf(f) for f in fuentes]
    return {"material_id": material_id, "partes": dividir_en_partes("\n\n".join(textos))}
