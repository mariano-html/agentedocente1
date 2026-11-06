"""
Script para probar conexión con Supabase
Ejecutar desde la raíz: python integracion/test_supabase.py
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(BASE_DIR)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, RAIZ)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

from supabase_api import supabase_api


def probar_prompts(solicitudes):
    """Sube, descarga, verifica y borra un prompt .txt de prueba."""
    print("\nProbando Storage de prompts (subir / descargar / borrar)...")
    try:
        from supabase_config import supabase_manager
    except Exception as error:
        print(f"   - No se pudo cargar supabase_config: {error}")
        return

    if not supabase_manager or not supabase_manager.client:
        print("   - supabase_config no conectado; se omite la prueba.")
        return
    if not solicitudes:
        print("   - No hay solicitudes para vincular el prompt de prueba; se omite.")
        return

    solicitud_id = solicitudes[0].get("id")

    # Guardar el valor anterior para restaurarlo al limpiar
    anterior = None
    try:
        res = supabase_manager.client.table("solicitudes") \
            .select("ultimo_prompt_id").eq("id", solicitud_id).execute()
        if res.data:
            anterior = res.data[0].get("ultimo_prompt_id")
    except Exception as error:
        print(f"   - Aviso: no se pudo leer ultimo_prompt_id: {error}")

    contenido = "Prueba de prompt para el Agente 2. Token: " + os.urandom(4).hex()
    registro = supabase_manager.guardar_prompt(solicitud_id, contenido)
    if not registro:
        print("   - ERROR: no se pudo guardar el prompt.")
        print("     Revisá: bucket 'prompts', policies de storage.objects y tabla solicitud_prompts.")
        return

    storage_path = registro.get("storage_path")
    print(f"   - Subido: {storage_path} (version {registro.get('version')})")
    print(f"   - Hash: {str(registro.get('contenido_hash'))[:16]}...")

    descargado = supabase_manager.descargar_prompt(storage_path)
    if descargado != contenido:
        print("   - ERROR: el contenido descargado no coincide con el subido.")
    else:
        print("   - Descarga OK: el contenido coincide.")

    print(f"   - URL publica: {supabase_manager.url_publica_prompt(storage_path)}")

    # Limpieza: restaurar el puntero, borrar la fila y el archivo de prueba
    try:
        supabase_manager.client.table("solicitudes") \
            .update({"ultimo_prompt_id": anterior}).eq("id", solicitud_id).execute()
        supabase_manager.client.table("solicitud_prompts") \
            .delete().eq("id", registro["id"]).execute()
        supabase_manager._borrar_objeto_prompt(storage_path)
        print("   - Limpieza OK (registro y archivo de prueba borrados).")
    except Exception as error:
        print(f"   - Aviso: no se pudo limpiar del todo: {error}")


def main():
    print("=" * 40)
    print("TEST DE CONEXIÓN A SUPABASE")
    print("=" * 40)

    if not supabase_api.is_connected():
        print("\n❌ NO CONECTADO")
        print("Revisá:")
        print("1. Tener supabase instalado: pip install -r integracion/requirements_supabase.txt")
        print("2. Crear integracion/.env con SUPABASE_URL y SUPABASE_ANON_KEY")
        print("3. Haber corrido el SQL en Supabase SQL Editor")
        return

    print("\n[OK] CONECTADO CORRECTAMENTE")

    print("\nProbando lectura de tablas...")
    solicitudes = []
    try:
        solicitudes = supabase_api.listar_solicitudes(limit=5)
        print(f"   - solicitudes: {len(solicitudes)} registros encontrados")
    except Exception as e:
        print(f"   - Error al leer solicitudes: {e}")

    probar_prompts(solicitudes)

    print("\n" + "=" * 40)
    print("TODO OK")
    print("=" * 40)


if __name__ == "__main__":
    main()
