# Contrato — Agente 1 (Interpretación)

El Agente 1 convierte el pedido libre de un docente en una **solicitud_normalizada**:
la estructura ordenada que entienden los demás componentes.

- **Produce:** `solicitud_normalizada`
- **No hace:** generar la actividad, validarla ni aprobarla. Solo interpreta.

## Entrada

| Dato | Tipo | Descripción |
| --- | --- | --- |
| `pedido` | texto | Lo que escribe el docente con sus palabras. |
| `formulario` | objeto | `materia`, `comision`, `modalidad`, `vigencia_hasta`. |
| `material` | objeto **o** ruta(s) de PDF | Un objeto `material_id` + lista `partes` con `{id, texto}` (ej. `F01`, `F02`), **o** una ruta (o lista de rutas) de PDFs. |
| `aportes` | objeto (opcional) | Datos que completa el docente (`tema`, `objetivo`, `nivel`, `criterios`). Se usan tal cual y tienen prioridad sobre lo que deduce el modelo. |

Funcion: `interpretar(pedido, formulario, material, llm=None, aportes=None) -> dict`

### Aportes del docente

`aportes` es la vía para que el docente complete lo que el agente no pudo deducir
(por ejemplo, desde el modal del front). Los campos presentes en `aportes` se
cargan en `datos` tal cual y **dejan de figurar en `faltantes`**.

### Material desde PDF

Si `material` es una ruta o una lista de rutas de PDF, el agente extrae el texto
(`lectura_pdf.material_desde_pdf`) y lo divide en partes por parrafos, numeradas
`F01, F02...`.

- Solo funciona con PDF que tengan **texto seleccionable**.
- Un PDF escaneado (imagen) no tiene texto extraible: se devuelve `ok: false`
  con el aviso en `errores`, sin inventar contenido.
- Si se pasa una ruta directamente a `interpretar`, el `material_id` por defecto
  es `MAT-01`. Para elegir otro, usar `material_desde_pdf(ruta, "MAT-XX")` o el
  `--material-id` del CLI.

## Salida

Siempre un objeto con esta forma:

```json
{
  "tipo": "solicitud_normalizada",
  "version_contrato": "1.0",
  "ok": true,
  "datos": {
    "materia": "Taller de IA",
    "comision": "5.o John Backus",
    "tema": "Construccion de prompts con C.O.R.F.",
    "objetivo": "Mejorar un prompt identificando contexto, objetivo, restriccion y formato",
    "nivel": "5.o ano",
    "criterios": ["Identifica el contexto", "Define el objetivo", "Aplica el formato pedido"],
    "modalidad": "online",
    "vigencia_hasta": "2026-11-30",
    "material_id": "MAT-01",
    "partes": ["F02", "F03"]
  },
  "errores": []
}
```

### Campos obligatorios de `datos`

`materia`, `comision`, `tema`, `objetivo`, `nivel`, `criterios`, `modalidad`,
`vigencia_hasta`, `material_id`, `partes`.

Si falta informacion, se agrega la clave `faltantes` dentro de `datos` con la
lista de campos que el docente debe completar.

## Regla de oro: no inventar

- El tema, objetivo, nivel y criterios deben deducirse del pedido y del material.
- Si un dato no se puede deducir, **no se inventa**: se deja vacío y su nombre va
  a `faltantes`.
- `partes` solo puede contener ids que existan en el material.
- Si el tema pedido no está en el material, `partes` queda vacío y el tema se
  marca como faltante.

## Respuestas de error

`ok` es `false` y `errores` explica el motivo en estos casos:

1. **Entrada incompleta**: pedido vacío, falta un dato del formulario o el
   material no tiene partes.

```json
{
  "tipo": "solicitud_normalizada",
  "version_contrato": "1.0",
  "ok": false,
  "datos": {},
  "errores": ["Faltan datos del formulario: objetivo."]
}
```

2. **Información que el docente debe completar** (faltantes):

```json
{
  "tipo": "solicitud_normalizada",
  "version_contrato": "1.0",
  "ok": false,
  "datos": {
    "tema": "Metodos HTTP",
    "objetivo": "",
    "nivel": "",
    "criterios": [],
    "partes": ["F01"],
    "faltantes": ["objetivo", "nivel", "criterios"]
  },
  "errores": ["Falta informacion que el docente debe completar: objetivo, nivel, criterios."]
}
```

3. **El modelo citó una parte que no existe** en el material.

```json
{
  "tipo": "solicitud_normalizada",
  "version_contrato": "1.0",
  "ok": false,
  "datos": { "partes": ["F01"], "faltantes": ["partes"] },
  "errores": ["El modelo cito partes que no existen en el material: F99."]
}
```

4. **Error del modelo**: sin `OPENROUTER_API_KEY`, sin conexión o respuesta sin
   JSON válido. Se devuelve `ok: false` con el detalle en `errores`.

5. **Error de PDF**: la ruta no existe, el archivo no se puede leer o es un
   escaneo sin texto extraible.

```json
{
  "tipo": "solicitud_normalizada",
  "version_contrato": "1.0",
  "ok": false,
  "datos": {},
  "errores": ["El PDF material.pdf no tiene texto extraible (puede ser un escaneo)."]
}
```

## Casos de prueba mínimos (los ejecuta el equipo de Testing)

| Caso | Entrada | Esperado |
| --- | --- | --- |
| Pedido completo | pedido claro + material con el tema | `ok: true`, `partes` válidas |
| Falta el objetivo | pedido sin objetivo deducible | `ok: false`, `objetivo` en `faltantes` |
| Tema no autorizado | tema que no está en el material | `ok: false`, `partes` vacío |
| Cita inexistente | el modelo devuelve una parte que no existe | `ok: false`, error citado |
| Formulario incompleto | falta `materia` u otro campo | `ok: false`, error de formulario |
| Material desde PDF | ruta a un PDF con texto | `partes` `F01...` extraidas del PDF |
| PDF sin texto | PDF escaneado (imagen) o ruta inexistente | `ok: false`, error de PDF |
