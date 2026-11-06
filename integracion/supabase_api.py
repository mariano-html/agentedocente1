"""
API de Supabase para el Agente Docente Bourbon
Funciones reutilizables para guardar solicitudes, materiales, actividades, etc.
"""

import os
from typing import Any, Dict, List, Optional

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = Any


class SupabaseAPI:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.client: Optional[Client] = None

        if not SUPABASE_AVAILABLE:
            print("[SUPABASE_API] Falta instalar 'supabase'. Ejecuta: pip install -r integracion/requirements_supabase.txt")
            return

        if not self.url or not self.key:
            print("[SUPABASE_API] Faltan SUPABASE_URL y SUPABASE_ANON_KEY en las variables de entorno")
            return

        try:
            self.client = create_client(self.url, self.key)
            print("[SUPABASE_API] Conexión a Supabase exitosa")
        except Exception as e:
            print(f"[SUPABASE_API] Error al conectar: {e}")

    def is_connected(self) -> bool:
        return self.client is not None

    def get_or_create_docente(self, nombre: str, email: str = None) -> Optional[str]:
        if not self.is_connected() or not nombre:
            return None
        try:
            res = self.client.table("docentes").select("id").eq("nombre", nombre).execute()
            if res.data:
                return res.data[0]["id"]
            data = {"nombre": nombre}
            if email:
                data["email"] = email
            res = self.client.table("docentes").insert(data).execute()
            return res.data[0]["id"] if res.data else None
        except Exception as e:
            print(f"[SUPABASE_API] Error get_or_create_docente: {e}")
            return None

    def get_or_create_curso(self, docente_id: str, nombre_curso: str, materia: str = None) -> Optional[str]:
        if not self.is_connected() or not docente_id or not nombre_curso:
            return None
        try:
            res = self.client.table("cursos").select("id").eq("docente_id", docente_id).eq("nombre", nombre_curso).execute()
            if res.data:
                return res.data[0]["id"]
            data = {"docente_id": docente_id, "nombre": nombre_curso}
            if materia:
                data["materia"] = materia
            res = self.client.table("cursos").insert(data).execute()
            return res.data[0]["id"] if res.data else None
        except Exception as e:
            print(f"[SUPABASE_API] Error get_or_create_curso: {e}")
            return None

    def guardar_material_completo(self, nombre_archivo: str, contenido_texto: str, material_id_externo: str = "MAT-01", docente_nombre: str = None, curso_nombre: str = None) -> Optional[Dict[str, Any]]:
        if not self.is_connected():
            return None
        try:
            docente_id = self.get_or_create_docente(docente_nombre) if docente_nombre else None
            curso_id = None
            if docente_id and curso_nombre:
                curso_id = self.get_or_create_curso(docente_id, curso_nombre)

            mat_res = self.client.table("materiales").insert({
                "material_id": material_id_externo,
                "docente_id": docente_id,
                "curso_id": curso_id,
                "nombre_archivo": nombre_archivo,
                "tipo_archivo": "pdf",
                "contenido_texto": contenido_texto
            }).execute()

            if not mat_res.data:
                return None

            material_uuid = mat_res.data[0]["id"]

            try:
                from agentes.interpretacion.lectura_pdf import dividir_en_partes
                partes = dividir_en_partes(contenido_texto)
                inserts = []
                for i, p in enumerate(partes):
                    inserts.append({
                        "material_id": material_uuid,
                        "parte_id": p["id"],
                        "texto": p["texto"],
                        "orden": i + 1
                    })
                if inserts:
                    self.client.table("material_partes").insert(inserts).execute()
            except Exception as e:
                print(f"[SUPABASE_API] Aviso: no se guardaron las partes: {e}")

            return {"material_uuid": material_uuid, "material_id": material_id_externo}
        except Exception as e:
            print(f"[SUPABASE_API] Error guardar_material_completo: {e}")
            return None

    def guardar_solicitud_completa(self, entrada: Dict[str, Any], resultado: Dict[str, Any]) -> Optional[str]:
        if not self.is_connected():
            return None
        try:
            formulario = entrada.get("formulario") or {}
            aportes = entrada.get("aportes") or {}
            datos = resultado.get("datos") or {}

            docente_nombre = entrada.get("docente") or formulario.get("docente")
            curso_nombre = formulario.get("comision") or formulario.get("curso")

            docente_id = self.get_or_create_docente(docente_nombre) if docente_nombre else None
            curso_id = self.get_or_create_curso(docente_id, curso_nombre, formulario.get("materia")) if docente_id and curso_nombre else None

            payload = {
                "docente_id": docente_id,
                "curso_id": curso_id,
                "materia": formulario.get("materia") or datos.get("materia"),
                "comision": formulario.get("comision") or datos.get("comision"),
                "modalidad": formulario.get("modalidad") or datos.get("modalidad"),
                "vigencia_hasta": formulario.get("vigencia_hasta") or datos.get("vigencia_hasta"),
                "tipo": resultado.get("tipo", "solicitud_normalizada"),
                "version_contrato": resultado.get("version_contrato", "1.0"),
                "ok": bool(resultado.get("ok")),
                "tema": datos.get("tema"),
                "objetivo": datos.get("objetivo"),
                "nivel": datos.get("nivel"),
                "criterios": datos.get("criterios") or [],
                "partes_citadas": datos.get("partes") or [],
                "faltantes": datos.get("faltantes") or [],
                "errores": resultado.get("errores") or [],
                "aportes": aportes,
                "pedido_original": entrada.get("pedido") or ""
            }

            res = self.client.table("solicitudes").insert(payload).execute()
            return res.data[0]["id"] if res.data else None
        except Exception as e:
            print(f"[SUPABASE_API] Error guardar_solicitud_completa: {e}")
            return None

    def listar_solicitudes(self, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.is_connected():
            return []
        try:
            res = self.client.table("solicitudes").select("*").order("created_at", desc=True).limit(limit).execute()
            return res.data or []
        except Exception as e:
            print(f"[SUPABASE_API] Error listar_solicitudes: {e}")
            return []

    def obtener_solicitud(self, solicitud_id: str) -> Optional[Dict[str, Any]]:
        if not self.is_connected():
            return None
        try:
            res = self.client.table("solicitudes").select("*").eq("id", solicitud_id).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            print(f"[SUPABASE_API] Error obtener_solicitud: {e}")
            return None


supabase_api = SupabaseAPI()
