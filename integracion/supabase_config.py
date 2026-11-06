"""
Configuración y utilidades para conectar con Supabase.
"""
import hashlib
import os
import json
from typing import Any, Dict, List, Optional

try:
    from supabase import create_client, Client
    SUPABASE_DISPONIBLE = True
except ImportError:
    SUPABASE_DISPONIBLE = False
    Client = Any

BUCKET_PROMPTS = "prompts"


def cargar_env_supabase(ruta_env: str = None):
    """Carga variables de entorno de Supabase desde un archivo .env"""
    if ruta_env is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ruta_env = os.path.join(base_dir, ".env")
    
    if not os.path.exists(ruta_env):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ruta_env = os.path.join(base_dir, "..", "agentes", "interpretacion", ".env")
    
    if os.path.exists(ruta_env):
        with open(ruta_env, encoding="utf-8") as archivo:
            for linea in archivo:
                linea = linea.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                clave, valor = linea.split("=", 1)
                valor = valor.strip()
                if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in ("'", '"'):
                    valor = valor[1:-1]
                os.environ.setdefault("SUPABASE_URL", clave.strip() if clave.strip() == "SUPABASE_URL" else os.environ.get("SUPABASE_URL", ""))
                os.environ.setdefault("SUPABASE_KEY", clave.strip() if clave.strip() == "SUPABASE_KEY" else os.environ.get("SUPABASE_KEY", ""))
                os.environ.setdefault("SUPABASE_ANON_KEY", clave.strip() if clave.strip() == "SUPABASE_ANON_KEY" else os.environ.get("SUPABASE_ANON_KEY", ""))
                os.environ.setdefault("SUPABASE_SERVICE_KEY", clave.strip() if clave.strip() == "SUPABASE_SERVICE_KEY" else os.environ.get("SUPABASE_SERVICE_KEY", ""))
                if clave.strip() in ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_KEY"):
                    os.environ[clave.strip()] = valor


class SupabaseManager:
    def __init__(self):
        cargar_env_supabase()
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.client: Optional[Client] = None
        
        if not SUPABASE_DISPONIBLE:
            print("[Supabase] Librería supabase no instalada. Ejecuta: pip install supabase")
            return
        if not self.url or not self.key:
            print("[Supabase] Faltan SUPABASE_URL y SUPABASE_KEY en .env")
            return
        try:
            self.client = create_client(self.url, self.key)
            print("[Supabase] Conectado correctamente")
        except Exception as e:
            print(f"[Supabase] Error al conectar: {e}")
    
    def guardar_solicitud(self, entrada: Dict[str, Any], resultado: Dict[str, Any], docente_nombre: str = None, curso_nombre: str = None) -> Optional[str]:
        if not self.client:
            return None
        try:
            datos_resultado = resultado.get("datos", {})
            formulario = entrada.get("formulario", {})
            aportes = entrada.get("aportes", {})
            pedido = entrada.get("pedido", "")
            
            # Buscar o crear docente
            docente_id = None
            if docente_nombre:
                doc_res = self.client.table("docentes").select("id").eq("nombre", docente_nombre).execute()
                if doc_res.data:
                    docente_id = doc_res.data[0]["id"]
                else:
                    nuevo_doc = self.client.table("docentes").insert({"nombre": docente_nombre}).execute()
                    if nuevo_doc.data:
                        docente_id = nuevo_doc.data[0]["id"]
            
            # Buscar o crear curso
            curso_id = None
            if curso_nombre and docente_id:
                cur_res = self.client.table("cursos").select("id").eq("nombre", curso_nombre).eq("docente_id", docente_id).execute()
                if cur_res.data:
                    curso_id = cur_res.data[0]["id"]
                else:
                    nuevo_cur = self.client.table("cursos").insert({
                        "docente_id": docente_id,
                        "nombre": curso_nombre,
                        "materia": formulario.get("materia") or datos_resultado.get("materia")
                    }).execute()
                    if nuevo_cur.data:
                        curso_id = nuevo_cur.data[0]["id"]
            
            # Insertar solicitud
            solicitud_data = {
                "docente_id": docente_id,
                "curso_id": curso_id,
                "materia": formulario.get("materia") or datos_resultado.get("materia"),
                "comision": formulario.get("comision") or datos_resultado.get("comision"),
                "modalidad": formulario.get("modalidad") or datos_resultado.get("modalidad"),
                "vigencia_hasta": formulario.get("vigencia_hasta") or datos_resultado.get("vigencia_hasta"),
                "tipo": resultado.get("tipo", "solicitud_normalizada"),
                "version_contrato": resultado.get("version_contrato", "1.0"),
                "ok": resultado.get("ok", False),
                "tema": datos_resultado.get("tema"),
                "objetivo": datos_resultado.get("objetivo"),
                "nivel": datos_resultado.get("nivel"),
                "criterios": datos_resultado.get("criterios") or [],
                "partes_citadas": datos_resultado.get("partes") or [],
                "faltantes": datos_resultado.get("faltantes") or [],
                "errores": resultado.get("errores") or [],
                "aportes": aportes,
                "pedido_original": pedido
            }
            
            sol_res = self.client.table("solicitudes").insert(solicitud_data).execute()
            if sol_res.data:
                return sol_res.data[0]["id"]
            return None
        except Exception as e:
            print(f"[Supabase] Error al guardar solicitud: {e}")
            return None
    
    def guardar_material(self, nombre_archivo: str, contenido_texto: str, material_id: str = "MAT-01", docente_nombre: str = None) -> Optional[str]:
        if not self.client:
            return None
        try:
            docente_id = None
            if docente_nombre:
                doc_res = self.client.table("docentes").select("id").eq("nombre", docente_nombre).execute()
                if doc_res.data:
                    docente_id = doc_res.data[0]["id"]
            
            mat_res = self.client.table("materiales").insert({
                "material_id": material_id,
                "docente_id": docente_id,
                "nombre_archivo": nombre_archivo,
                "tipo_archivo": "pdf",
                "contenido_texto": contenido_texto
            }).execute()
            
            if not mat_res.data:
                return None
            material_uuid = mat_res.data[0]["id"]
            
            # Guardar partes
            from agentes.interpretacion.lectura_pdf import dividir_en_partes
            partes = dividir_en_partes(contenido_texto)
            for i, parte in enumerate(partes):
                self.client.table("material_partes").insert({
                    "material_id": material_uuid,
                    "parte_id": parte["id"],
                    "texto": parte["texto"],
                    "orden": i + 1
                }).execute()
            return material_uuid
        except Exception as e:
            print(f"[Supabase] Error al guardar material: {e}")
            return None

    def obtener_cursos_predeterminados(self) -> List[Dict[str, Any]]:
        """Devuelve la lista de cursos predeterminados desde Supabase."""
        if not self.client:
            return []
        try:
            res = self.client.table("cursos_predeterminados") \
                .select("id,nombre,anio,orden") \
                .eq("activo", True) \
                .order("orden") \
                .execute()
            return res.data or []
        except Exception as e:
            print(f"[Supabase] Error al obtener cursos predeterminados: {e}")
            return []

    # ------------------------------------------------------------------
    # Prompts de actividad: Storage (bucket "prompts") + vinculacion
    # ------------------------------------------------------------------

    def siguiente_version_prompt(self, solicitud_id: str) -> int:
        """Devuelve el numero de version libre para el prompt de una solicitud."""
        if not self.client or not solicitud_id:
            return 1
        try:
            res = self.client.table("solicitud_prompts") \
                .select("version") \
                .eq("solicitud_id", solicitud_id) \
                .order("version", desc=True) \
                .limit(1) \
                .execute()
            if res.data:
                return int(res.data[0]["version"]) + 1
        except Exception as e:
            print(f"[Supabase] Error al calcular la version del prompt: {e}")
        return 1

    def guardar_prompt(self, solicitud_id: str, contenido: str, version: int = None,
                       bucket: str = BUCKET_PROMPTS) -> Optional[Dict[str, Any]]:
        """Sube el prompt .txt a Storage y lo vincula con la solicitud.

        Ruta: ``{bucket}/{solicitud_id}/v{n}_actividad.txt``.
        Inserta la fila en ``solicitud_prompts`` y actualiza
        ``solicitudes.ultimo_prompt_id``.

        Devuelve la fila insertada o ``None`` si algo falla.
        """
        if not self.client or not solicitud_id or not contenido:
            return None
        data = contenido.encode("utf-8")
        contenido_hash = hashlib.sha256(data).hexdigest()

        for intento in (1, 2):
            if version is None:
                version = self.siguiente_version_prompt(solicitud_id)
            nombre_archivo = "v%d_actividad.txt" % version
            storage_path = "%s/%s" % (solicitud_id, nombre_archivo)
            try:
                self.client.storage.from_(bucket).upload(
                    storage_path,
                    data,
                    {"content-type": "text/plain; charset=utf-8", "upsert": "true"},
                )
            except Exception as e:
                print(f"[Supabase] Error al subir el prompt a Storage: {e}")
                return None

            try:
                fila = {
                    "solicitud_id": solicitud_id,
                    "version": version,
                    "storage_bucket": bucket,
                    "storage_path": storage_path,
                    "nombre_archivo": nombre_archivo,
                    "contenido_hash": contenido_hash,
                    "tamano_bytes": len(data),
                }
                insert = self.client.table("solicitud_prompts").insert(fila).execute()
            except Exception as e:
                print(f"[Supabase] Error al vincular el prompt con la solicitud: {e}")
                self._borrar_objeto_prompt(storage_path, bucket)
                if intento == 1 and "duplicate" in str(e).lower():
                    version = None
                    continue
                return None

            if not insert.data:
                self._borrar_objeto_prompt(storage_path, bucket)
                return None

            registro = insert.data[0]
            try:
                self.client.table("solicitudes") \
                    .update({"ultimo_prompt_id": registro["id"]}) \
                    .eq("id", solicitud_id) \
                    .execute()
            except Exception as e:
                print(f"[Supabase] Aviso: no se actualizo ultimo_prompt_id: {e}")
            return registro

        return None

    def _borrar_objeto_prompt(self, storage_path: str, bucket: str = BUCKET_PROMPTS):
        """Borra un objeto de Storage sin levantar error (limpieza)."""
        try:
            self.client.storage.from_(bucket).remove([storage_path])
        except Exception as e:
            print(f"[Supabase] Aviso: no se pudo limpiar {storage_path}: {e}")

    def url_publica_prompt(self, storage_path: str, bucket: str = BUCKET_PROMPTS) -> Optional[str]:
        """Devuelve la URL publica del prompt (el bucket es publico por ahora)."""
        if not self.client or not storage_path:
            return None
        try:
            res = self.client.storage.from_(bucket).get_public_url(storage_path)
            if isinstance(res, dict):
                return res.get("publicURL") or res.get("publicUrl") or res.get("public_url")
            return res
        except Exception as e:
            print(f"[Supabase] Error al obtener la URL publica del prompt: {e}")
            return None

    def obtener_ultimo_prompt(self, solicitud_id: str) -> Optional[Dict[str, Any]]:
        """Devuelve la fila del prompt mas reciente de una solicitud."""
        if not self.client or not solicitud_id:
            return None
        try:
            res = self.client.table("solicitud_prompts") \
                .select("*") \
                .eq("solicitud_id", solicitud_id) \
                .order("version", desc=True) \
                .limit(1) \
                .execute()
            return res.data[0] if res.data else None
        except Exception as e:
            print(f"[Supabase] Error al obtener el ultimo prompt: {e}")
            return None

    def descargar_prompt(self, storage_path: str, bucket: str = BUCKET_PROMPTS) -> Optional[str]:
        """Descarga un prompt de Storage y lo devuelve como texto UTF-8."""
        if not self.client or not storage_path:
            return None
        try:
            data = self.client.storage.from_(bucket).download(storage_path)
            if isinstance(data, (bytes, bytearray)):
                return bytes(data).decode("utf-8")
            contenido = getattr(data, "content", None)
            if isinstance(contenido, (bytes, bytearray)):
                return bytes(contenido).decode("utf-8")
            if isinstance(data, str):
                return data
        except Exception as e:
            print(f"[Supabase] Error al descargar el prompt: {e}")
        return None

    def obtener_contenido_prompt(self, solicitud_id: str, version: int = None) -> Optional[str]:
        """Devuelve el texto del prompt pedido (ultima version por defecto)."""
        if not self.client or not solicitud_id:
            return None
        try:
            if version is None:
                registro = self.obtener_ultimo_prompt(solicitud_id)
            else:
                res = self.client.table("solicitud_prompts") \
                    .select("*") \
                    .eq("solicitud_id", solicitud_id) \
                    .eq("version", version) \
                    .limit(1) \
                    .execute()
                registro = res.data[0] if res.data else None
            if not registro:
                return None
            return self.descargar_prompt(
                registro.get("storage_path"),
                registro.get("storage_bucket") or BUCKET_PROMPTS,
            )
        except Exception as e:
            print(f"[Supabase] Error al obtener el contenido del prompt: {e}")
            return None


# Instancia global
supabase_manager = SupabaseManager()
