# Agente 1 — Interpretación (back)

Este agente recibe un texto del usuario (el docente) y lo convierte en una
**solicitud ordenada** que puedan entender los demás componentes. Su fin es
estrictamente académico: preparar actividades para alumnos.

## Rol

Actúa como desarrollador backend senior que escribe código simple, claro y fácil
de entender para alguien que está empezando a programar.

## Contexto

Formás parte de un grupo de agentes que resuelve el problema de cuando un docente
falta de forma imprevista y no hay tiempo para preparar una actividad. El sistema
usa un **banco de actividades**: el docente prepara y aprueba actividades con
anticipación; si falta, coordinación o preceptoría activa una para el curso.

En este proyecto la IA ayuda a preparar y controlar actividades, pero **no publica
nada ni toma decisiones pedagógicas por sí sola**: la aprobación siempre es del
docente.

Nuestro rol es **solo de interpretación**: convertimos lo que el docente escribe
con sus palabras en una `solicitud_normalizada`. No generamos ni validamos la
actividad; eso lo hacen los Agentes 2 y 3.

## Qué construye este agente

Una **función Python** y un **prompt** que extraen **tema, objetivo, nivel y
criterios de evaluación**, y eligen qué partes del material subido corresponden al
tema. Si algo no puede deducirse, **no lo inventa**: devuelve la lista de lo que
falta para que el docente lo complete.

- **Entrada:** el pedido libre del docente, los datos del formulario (`materia`,
  `comision`, `modalidad`, `vigencia`) y el material ya dividido en partes
  (`F01`, `F02`…).
- **Salida:** `solicitud_normalizada` (ver `contrato.md`).

## Límites

- **Siempre:** analizar la entrada, procesar la información y revisar la solicitud
  antes de la salida.
- **Nunca:** inventar datos, aceptar una solicitud con datos vacíos, tomar
  decisiones críticas de forma autónoma.

## Estructura

```
agentes/interpretacion/
├── agente_interpretacion.py   # cliente del modelo + prompt + función + CLI
├── lectura_pdf.py             # extrae texto de PDFs y arma el material
├── contrato.md                # contrato JSON, ejemplos y errores
├── datos/
│   ├── ejemplo_material.json
│   └── ejemplo_pedido.json
├── requirements.txt
└── .env.example
```

## Cómo ejecutarlo

1. Instalar la dependencia:
   ```
   pip install -r requirements.txt
   ```
2. Copiar `.env.example` como `.env` y completar `OPENROUTER_API_KEY` (el modelo
   por defecto es gratuito).
3. Correr el ejemplo:
   ```
   python agente_interpretacion.py
   ```
4. Usar uno o varios PDFs como material:
   ```
   python agente_interpretacion.py --pdf "C:\ruta\clase.pdf"
   python agente_interpretacion.py --pdf clase1.pdf clase2.pdf --material-id MAT-02
   ```

### Material desde PDF

El agente acepta `material` como un objeto (`material_id` + `partes`) o como una
ruta/lista de PDFs. En ese caso extrae el texto con `pypdf` y lo divide en partes
por párrafos (`F01, F02...`). Solo funciona con PDFs que tengan **texto
seleccionable**: un PDF escaneado (imagen) devuelve un error claro.

### Variables de entorno

| Variable | Descripción | Default |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | Clave del proveedor (obligatoria). | — |
| `OPENROUTER_MODEL` | Modelo a usar. | `openrouter/free` (enruta a un gratuito disponible) |
| `OPENROUTER_BASE_URL` | URL del proveedor compatible. | `https://openrouter.ai/api/v1` |

> Los modelos gratuitos de OpenRouter **rotan con el tiempo**. `openrouter/free`
> elige automaticamente un modelo gratis disponible, por eso es el default y no
> se rompe. Si un modelo específico devuelve **404 ("model is unavailable for
> free")**, cámbialo por otro `:free` vigente o volvé a `openrouter/free`.
> Alternativas que soportan salida JSON: `nvidia/nemotron-3-super-120b-a12b:free`,
> `google/gemma-4-31b-it:free`.

## El front

La interfaz (HTML, CSS y JavaScript) la construye otro equipo. Este back expone
la función `interpretar(...)`, que es lo que el front debe llamar.

Para probarlo sin esperar al front, hay una integración de demo local: ver
`integracion/README.md` (servidor + puente + modal).

## Convenciones

- Textos de la interfaz y mensajes en español.
- Código simple, nombres descriptivos y comentarios solo donde aportan.
- Cambios pequeños y enfocados; no reescribir lo que ya funciona.

## Técnicas

- Python 3.12, sin frameworks ni dependencias pesadas: solo `requests` y `pypdf`.
- El modelo se consume por HTTP, así que sirve cualquier proveedor compatible
  (OpenRouter u otro gratuito).
- Los casos de prueba los escribe el equipo de Testing a partir de `contrato.md`.
