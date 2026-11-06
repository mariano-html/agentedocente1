CREATE TABLE public.actividades (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  solicitud_id uuid,
  docente_id uuid,
  curso_id uuid,
  estado text DEFAULT 'borrador'::text,
  codigo_actividad text,
  contenido_html text,
  contenido_css text,
  contenido_js text,
  aprobado_por uuid,
  aprobado_en timestamp with time zone,
  activada_en timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE public.alumnos_respuestas (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  actividad_id uuid,
  alumno_identificador text,
  respuesta_html text,
  respuesta_css text,
  respuesta_js text,
  puntaje numeric,
  feedback text,
  corregido_en timestamp with time zone,
  created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE public.cursos_predeterminados (
  id bigint NOT NULL,
  nombre text NOT NULL,
  anio text,
  orden integer NOT NULL,
  activo boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE public.docentes (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  nombre text NOT NULL,
  email text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE public.material_partes (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  material_id uuid,
  parte_id text NOT NULL,
  texto text NOT NULL,
  orden integer NOT NULL
);

CREATE TABLE public.materiales (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  material_id text NOT NULL,
  curso_id uuid,
  docente_id uuid,
  nombre_archivo text NOT NULL,
  tipo_archivo text DEFAULT 'pdf'::text,
  contenido_texto text,
  storage_path text,
  created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE public.solicitud_partes_usadas (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  solicitud_id uuid,
  material_parte_id uuid,
  extracto text,
  created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE public.solicitud_prompts (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  solicitud_id uuid NOT NULL,
  version integer NOT NULL DEFAULT 1,
  storage_bucket text NOT NULL DEFAULT 'prompts'::text,
  storage_path text NOT NULL,
  nombre_archivo text NOT NULL,
  contenido_hash text,
  tamano_bytes integer,
  created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE public.solicitudes (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  docente_id uuid,
  curso_id uuid,
  material_id uuid,
  materia text,
  comision text,
  modalidad text,
  vigencia_hasta date,
  tipo text DEFAULT 'solicitud_normalizada'::text,
  version_contrato text DEFAULT '1.0'::text,
  ok boolean NOT NULL DEFAULT false,
  tema text,
  objetivo text,
  nivel text,
  criterios jsonb DEFAULT '[]'::jsonb,
  partes_citadas jsonb DEFAULT '[]'::jsonb,
  faltantes jsonb DEFAULT '[]'::jsonb,
  errores jsonb DEFAULT '[]'::jsonb,
  aportes jsonb DEFAULT '{}'::jsonb,
  pedido_original text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  ultimo_prompt_id uuid
);

| ?column?                                                                                                                                                                                           |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ALTER TABLE public.actividades ADD CONSTRAINT actividades_codigo_actividad_key UNIQUE (codigo_actividad);                                                                                          |
| ALTER TABLE public.actividades ADD CONSTRAINT actividades_pkey PRIMARY KEY (id);                                                                                                                   |
| ALTER TABLE public.actividades ADD CONSTRAINT actividades_aprobado_por_fkey FOREIGN KEY (aprobado_por) REFERENCES docentes(id);                                                                    |
| ALTER TABLE public.actividades ADD CONSTRAINT actividades_curso_id_fkey FOREIGN KEY (curso_id) REFERENCES cursos(id) ON DELETE SET NULL;                                                           |
| ALTER TABLE public.actividades ADD CONSTRAINT actividades_docente_id_fkey FOREIGN KEY (docente_id) REFERENCES docentes(id) ON DELETE SET NULL;                                                     |
| ALTER TABLE public.actividades ADD CONSTRAINT actividades_solicitud_id_fkey FOREIGN KEY (solicitud_id) REFERENCES solicitudes(id) ON DELETE CASCADE;                                               |
| ALTER TABLE public.actividades ADD CONSTRAINT actividades_estado_check CHECK ((estado = ANY (ARRAY['borrador'::text, 'aprobada'::text, 'activada'::text, 'corregida'::text, 'archivada'::text]))); |
| ALTER TABLE public.alumnos_respuestas ADD CONSTRAINT alumnos_respuestas_pkey PRIMARY KEY (id);                                                                                                     |
| ALTER TABLE public.alumnos_respuestas ADD CONSTRAINT alumnos_respuestas_actividad_id_fkey FOREIGN KEY (actividad_id) REFERENCES actividades(id) ON DELETE CASCADE;                                 |
| ALTER TABLE public.cursos ADD CONSTRAINT cursos_pkey PRIMARY KEY (id);                                                                                                                             |
| ALTER TABLE public.cursos ADD CONSTRAINT cursos_docente_id_fkey FOREIGN KEY (docente_id) REFERENCES docentes(id) ON DELETE SET NULL;                                                               |
| ALTER TABLE public.cursos_predeterminados ADD CONSTRAINT cursos_predeterminados_nombre_key UNIQUE (nombre);                                                                                        |
| ALTER TABLE public.cursos_predeterminados ADD CONSTRAINT cursos_predeterminados_pkey PRIMARY KEY (id);                                                                                             |
| ALTER TABLE public.docentes ADD CONSTRAINT docentes_email_key UNIQUE (email);                                                                                                                      |
| ALTER TABLE public.docentes ADD CONSTRAINT docentes_pkey PRIMARY KEY (id);                                                                                                                         |
| ALTER TABLE public.material_partes ADD CONSTRAINT material_partes_material_id_parte_id_key UNIQUE (material_id, parte_id);                                                                         |
| ALTER TABLE public.material_partes ADD CONSTRAINT material_partes_pkey PRIMARY KEY (id);                                                                                                           |
| ALTER TABLE public.material_partes ADD CONSTRAINT material_partes_material_id_fkey FOREIGN KEY (material_id) REFERENCES materiales(id) ON DELETE CASCADE;                                          |
| ALTER TABLE public.materiales ADD CONSTRAINT materiales_material_id_key UNIQUE (material_id);                                                                                                      |
| ALTER TABLE public.materiales ADD CONSTRAINT materiales_pkey PRIMARY KEY (id);                                                                                                                     |
| ALTER TABLE public.materiales ADD CONSTRAINT materiales_curso_id_fkey FOREIGN KEY (curso_id) REFERENCES cursos(id) ON DELETE SET NULL;                                                             |
| ALTER TABLE public.materiales ADD CONSTRAINT materiales_docente_id_fkey FOREIGN KEY (docente_id) REFERENCES docentes(id) ON DELETE SET NULL;                                                       |
| ALTER TABLE public.solicitud_partes_usadas ADD CONSTRAINT solicitud_partes_usadas_solicitud_id_material_parte_id_key UNIQUE (solicitud_id, material_parte_id);                                     |
| ALTER TABLE public.solicitud_partes_usadas ADD CONSTRAINT solicitud_partes_usadas_pkey PRIMARY KEY (id);                                                                                           |
| ALTER TABLE public.solicitud_partes_usadas ADD CONSTRAINT solicitud_partes_usadas_material_parte_id_fkey FOREIGN KEY (material_parte_id) REFERENCES material_partes(id) ON DELETE CASCADE;         |
| ALTER TABLE public.solicitud_partes_usadas ADD CONSTRAINT solicitud_partes_usadas_solicitud_id_fkey FOREIGN KEY (solicitud_id) REFERENCES solicitudes(id) ON DELETE CASCADE;                       |
| ALTER TABLE public.solicitud_prompts ADD CONSTRAINT solicitud_prompts_solicitud_id_version_key UNIQUE (solicitud_id, version);                                                                     |
| ALTER TABLE public.solicitud_prompts ADD CONSTRAINT solicitud_prompts_pkey PRIMARY KEY (id);                                                                                                       |
| ALTER TABLE public.solicitud_prompts ADD CONSTRAINT solicitud_prompts_solicitud_id_fkey FOREIGN KEY (solicitud_id) REFERENCES solicitudes(id) ON DELETE CASCADE;                                   |
| ALTER TABLE public.solicitudes ADD CONSTRAINT solicitudes_pkey PRIMARY KEY (id);                                                                                                                   |
| ALTER TABLE public.solicitudes ADD CONSTRAINT solicitudes_curso_id_fkey FOREIGN KEY (curso_id) REFERENCES cursos(id) ON DELETE SET NULL;                                                           |
| ALTER TABLE public.solicitudes ADD CONSTRAINT solicitudes_docente_id_fkey FOREIGN KEY (docente_id) REFERENCES docentes(id) ON DELETE SET NULL;                                                     |
| ALTER TABLE public.solicitudes ADD CONSTRAINT solicitudes_material_id_fkey FOREIGN KEY (material_id) REFERENCES materiales(id) ON DELETE SET NULL;                                                 |
| ALTER TABLE public.solicitudes ADD CONSTRAINT solicitudes_ultimo_prompt_id_fkey FOREIGN KEY (ultimo_prompt_id) REFERENCES solicitud_prompts(id);                                                   |
| ALTER TABLE public.solicitudes ADD CONSTRAINT solicitudes_modalidad_check CHECK ((modalidad = ANY (ARRAY['online'::text, 'escrita'::text])));                                                      |

| ?column?                                                                                               |
| ------------------------------------------------------------------------------------------------------ |
| CREATE INDEX idx_actividades_codigo ON public.actividades USING btree (codigo_actividad);              |
| CREATE INDEX idx_actividades_estado ON public.actividades USING btree (estado);                        |
| CREATE INDEX idx_alumnos_respuestas_actividad ON public.alumnos_respuestas USING btree (actividad_id); |
| CREATE INDEX idx_material_partes_material ON public.material_partes USING btree (material_id);         |
| CREATE INDEX idx_solicitud_prompts_solicitud ON public.solicitud_prompts USING btree (solicitud_id);   |
| CREATE INDEX idx_solicitudes_created_at ON public.solicitudes USING btree (created_at DESC);           |
| CREATE INDEX idx_solicitudes_docente ON public.solicitudes USING btree (docente_id);                   |
| CREATE INDEX idx_solicitudes_ok ON public.solicitudes USING btree (ok);                                |

| ?column?                                                                                                                                   |
| ------------------------------------------------------------------------------------------------------------------------------------------ |
| CREATE TRIGGER update_docentes_updated_at BEFORE UPDATE ON public.docentes FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();       |
| CREATE TRIGGER update_solicitudes_updated_at BEFORE UPDATE ON public.solicitudes FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); |
| CREATE TRIGGER update_actividades_updated_at BEFORE UPDATE ON public.actividades FOR EACH ROW EXECUTE FUNCTION update_updated_at_column(); |


-- | schemaname | tablename   | policyname                           | cmd    | roles    | qual                      | with_check                |
-- | ---------- | ----------- | ------------------------------------ | ------ | -------- | ------------------------- | ------------------------- |
-- | public     | solicitudes | Docente crea sus propias solicitudes | INSERT | {public} | null                      | (auth.uid() = docente_id) |
-- | public     | solicitudes | Docente ve sus propias solicitudes   | SELECT | {public} | (auth.uid() = docente_id) | null                      |