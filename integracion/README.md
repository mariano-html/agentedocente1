# Integración — front del chat con el Agente 1

Conecta el front `Aula IA (1).html` con el Agente 1 de interpretación usando un
**servidor local** (Python estándar, sin dependencias nuevas) y un **puente** en
JavaScript que se inyecta al servir la página. El archivo del front **no se
modifica**.

## Cómo se ejecuta

```powershell
python integracion/servidor.py
```

Luego abrir <http://127.0.0.1:8000>.

El servidor:

- `GET /` → sirve `Aula IA (1).html` e inyecta `<script src="/puente.js">`.
- `GET /puente.js` → sirve el puente.
- `POST /api/interpretar` → recibe la entrada del chat y devuelve el contrato JSON.

La `OPENROUTER_API_KEY` se lee desde `agentes/interpretacion/.env` y **queda del
lado del servidor**: el navegador nunca la ve.

## Flujo

1. El docente escribe su nombre y curso (lo hace el propio front).
2. Escribe el pedido y adjunta el material (PDF).
3. Al enviar, el puente **valida antes de llamar al agente** y muestra un aviso
   (pop-up) sin enviar si: no adjuntó ningún archivo, el archivo no es PDF, o
   adjuntó un archivo pero no escribió el pedido. El texto y los adjuntos se
   conservan, así no hay que reescribir nada.
4. Si la validación pasa, el puente abre un **modal ampliado**: los campos
   obligatorios (`materia`, `comision`, `modalidad`, `vigencia_hasta`) y los
   **opcionales** (`tema`, `objetivo`, `nivel`, `criterios`). Lo que el docente
   complete ahí se envía como `aportes` y el agente lo usa **tal cual**, sin
   volver a deducirlo.
5. El puente convierte los archivos a base64 y hace `POST /api/interpretar`.
6. El servidor extrae el texto de los PDFs, llama a `interpretar(...)` y devuelve
   la `solicitud_normalizada`.
7. El puente muestra un **resumen amigable** en el chat. Si el agente todavía
   necesita algo, lo lista en **"Falta que completes"**; si falta `partes`, avisa
   que no se encontró material para el tema en el PDF.
8. El resumen lista cada parte citada con un **extracto** del material
   (`material_usado`), para que el docente vea a qué texto corresponde cada `F0x`.

## Formato del pedido al servidor

```json
{
  "pedido": "texto del docente",
  "formulario": {
    "materia": "Taller de IA",
    "comision": "5.o John Backus",
    "modalidad": "online|escrita",
    "vigencia_hasta": "2026-11-30"
  },
  "aportes": {
    "tema": "Metodos HTTP",
    "objetivo": "Reconocer y aplicar GET y POST",
    "nivel": "Intermedio",
    "criterios": ["Usa el metodo HTTP correcto", "Explica la estructura usada"]
  },
  "archivos": [
    { "nombre": "clase.pdf", "contenido_base64": "..." }
  ]
}
```

`aportes` es opcional: solo incluye lo que el docente escribió en el modal.

## Notas

- Solo se procesan **PDF con texto seleccionable**. Los escaneos (sin texto)
  devuelven un error claro y los archivos que no son PDF se ignoran con un aviso.
- La validación previa (archivo presente, PDF y pedido escrito) vive en
  `puente.js`; el servidor conserva su propio control como red de seguridad.
- Si no hay material, el contrato vuelve con `ok: false` y la lista `faltantes`.
- La respuesta es el contrato del Agente 1 más dos campos de la demo:
  `material_usado` (extracto de cada parte citada) y `avisos` (archivos ignorados).
- Es una integración de **demo local** (monohilo); para producción se puede
  portar a Streamlit u otro servidor.
