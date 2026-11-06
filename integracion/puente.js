/* Puente entre el front (Aula IA) y el Agente 1 de interpretacion.
   Lo inyecta integracion/servidor.py. No modifica el HTML original. */
(function () {
  "use strict";

  var API = "/api/interpretar";

  /* ---------- Estilos del modal ---------- */
  var estilo = document.createElement("style");
  estilo.textContent = [
    ".ag-modal{position:fixed;inset:0;z-index:60;display:grid;place-items:center;padding:16px;background:rgba(0,0,0,.82)}",
    ".ag-modal[hidden]{display:none}",
    ".ag-card{width:min(30rem,100%);max-height:100%;overflow:auto;border-radius:20px;border:1.5px solid transparent;background:linear-gradient(var(--surface),var(--surface)) padding-box,var(--grad) border-box;color:var(--text);font-family:var(--font-body)}",
    ".ag-head{padding:14px 18px;border-bottom:1px solid var(--line);font-family:var(--font-display);font-weight:700;font-size:1.1rem}",
    ".ag-body{padding:16px 18px;display:flex;flex-direction:column;gap:12px}",
    ".ag-field{display:flex;flex-direction:column;gap:5px;font-size:.86rem;color:var(--dim)}",
    ".ag-field input,.ag-field select,.ag-field textarea{background:var(--surface-2);border:1px solid var(--line);color:var(--text);border-radius:12px;padding:9px 12px;font:inherit;font-size:.95rem}",
    ".ag-field textarea{resize:vertical}",
    ".ag-field input:focus,.ag-field select:focus,.ag-field textarea:focus{outline:2px solid var(--g1);outline-offset:1px}",
    ".ag-sep{margin-top:4px;padding-top:12px;border-top:1px solid var(--line);font-size:.76rem;color:var(--dim);text-transform:uppercase;letter-spacing:.05em}",
    ".ag-pedido{margin:0;font-size:.82rem;color:var(--dim)}",
    ".ag-pedido b{color:var(--text);font-weight:600}",
    ".ag-aviso{margin:0;font-size:.8rem;color:var(--danger);min-height:1em}",
    ".ag-foot{display:flex;justify-content:flex-end;gap:8px;padding:14px 18px;border-top:1px solid var(--line)}",
    ".ag-foot button{font:inherit;font-size:.9rem;cursor:pointer;border-radius:999px;padding:8px 18px;border:1px solid var(--line);background:none;color:var(--dim)}",
    ".ag-foot .ag-ok{color:#14121c;background:var(--grad);border-color:transparent;font-weight:600}",
    "#toast.ag-error{border-color:var(--danger);color:var(--danger);font-weight:600}"
  ].join("");
  document.head.appendChild(estilo);

  /* ---------- Modal ---------- */
  var modal = document.createElement("div");
  modal.className = "ag-modal";
  modal.hidden = true;
  modal.innerHTML =
    '<form class="ag-card" novalidate>' +
      '<div class="ag-head">Datos de la actividad</div>' +
      '<div class="ag-body">' +
        '<label class="ag-field">Materia<input name="materia" type="text" placeholder="Taller de IA"></label>' +
        '<label class="ag-field">Comision<select name="comision"><option value="">Selecciona un curso</option></select></label>' +
        '<label class="ag-field">Modalidad<select name="modalidad"><option value="online">online</option><option value="escrita">escrita</option></select></label>' +
        '<label class="ag-field">Vigencia hasta<input name="vigencia_hasta" type="date"></label>' +
        '<label class="ag-field">Nivel<select name="nivel">' +
          '<option value="">Selecciona un nivel</option>' +
          '<option value="Basico">Basico</option>' +
          '<option value="Intermedio">Intermedio</option>' +
          '<option value="Avanzado">Avanzado</option>' +
        '</select></label>' +
        '<div class="ag-sep">Opcional: si lo dejas vacio, el agente lo deduce del pedido y el material</div>' +
        '<label class="ag-field">Tema<input name="tema" type="text" placeholder="(lo deduce el agente)"></label>' +
        '<label class="ag-field">Objetivo<input name="objetivo" type="text" placeholder="(lo deduce el agente)"></label>' +
        '<label class="ag-field">Criterios (uno por linea)<textarea name="criterios" rows="3" placeholder="(los deduce el agente)"></textarea></label>' +
        '<p class="ag-pedido"></p>' +
        '<p class="ag-aviso"></p>' +
      '</div>' +
      '<div class="ag-foot">' +
        '<button type="button" class="ag-cancel">Cancelar</button>' +
        '<button type="submit" class="ag-ok">Interpretar</button>' +
      '</div>' +
    '</form>';
  document.body.appendChild(modal);

  var formEl = modal.querySelector("form");
  var pedidoEl = modal.querySelector(".ag-pedido");
  var avisoEl = modal.querySelector(".ag-aviso");
  var pendiente = null;
  var cursosCargados = false;

  var CURSOS_FALLBACK = [
    "1er Año - M. Curie", "1er Año - R. Favaloro", "1er Año - C. Milstein",
    "2do Año - C. Grierson", "2do Año - B. Houssay", "2do Año - A. Moreau de Justo",
    "3er Año - E. Bachofen", "3er Año - F. Leloir", "3er Año - A. Perez Esquivel",
    "4to Año - I. Lehmann", "4to Año - A. Lovelace", "4to Año - M. Sadosky",
    "5to Año - J. Backus", "5to Año - C. Berdichevski", "5to Año - E. Mortola"
  ];

  function cargarCursos() {
    if (cursosCargados) return Promise.resolve();
    var sel = f("comision");
    return fetch("/api/cursos").then(function (r) { return r.json(); }).then(function (data) {
      var lista = (data && data.cursos) ? data.cursos : [];
      poblarCursos(lista.length ? lista.map(function (c) { return c.nombre || c; }) : CURSOS_FALLBACK);
      cursosCargados = true;
    }).catch(function () {
      poblarCursos(CURSOS_FALLBACK);
      cursosCargados = true;
    });
  }

  function poblarCursos(nombres) {
    var sel = f("comision");
    if (!sel) return;
    var actual = sel.value;
    sel.innerHTML = '<option value="">Selecciona un curso</option>';
    nombres.forEach(function (nombre) {
      var opt = document.createElement("option");
      opt.value = nombre;
      opt.textContent = nombre;
      sel.appendChild(opt);
    });
    if (actual) sel.value = actual;
  }

  function f(nombre) { return formEl.elements[nombre]; }

  function fechaPorDefecto() {
    var d = new Date();
    d.setDate(d.getDate() + 30);
    return d.toISOString().slice(0, 10);
  }

  function escapar(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function abrir(mensaje) {
    pendiente = mensaje;
    if (!f("vigencia_hasta").value) f("vigencia_hasta").value = fechaPorDefecto();
    cargarCursos().then(function () {
      if (mensaje && mensaje.course && f("comision") && !f("comision").value) {
        f("comision").value = mensaje.course;
      }
    });
    pedidoEl.innerHTML = "Pedido: <b>" + escapar(mensaje.text || "(sin texto)") + "</b>";
    avisoEl.textContent = "";
    modal.hidden = false;
    f("materia").focus();
  }

  function cerrar() {
    modal.hidden = true;
    pendiente = null;
  }

  modal.querySelector(".ag-cancel").addEventListener("click", cerrar);
  // No cerrar al hacer clic fuera del modal (evita perder datos por accidente)
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !modal.hidden) cerrar();
  });

  formEl.addEventListener("submit", function (e) {
    e.preventDefault();
    var formulario = {
      materia: f("materia").value.trim(),
      comision: f("comision").value.trim(),
      modalidad: f("modalidad").value,
      vigencia_hasta: f("vigencia_hasta").value
    };
    var faltan = [];
    if (!formulario.materia) faltan.push("materia");
    if (!formulario.comision) faltan.push("comision");
    if (!formulario.vigencia_hasta) faltan.push("vigencia");
    if (!f("nivel").value) faltan.push("nivel");
    if (faltan.length) {
      avisoEl.textContent = "Completa: " + faltan.join(", ") + ".";
      return;
    }

    var aportes = {};
    var tema = f("tema").value.trim();
    var objetivo = f("objetivo").value.trim();
    var nivel = f("nivel").value;
    var criterios = f("criterios").value.split("\n").map(function (l) { return l.trim(); })
                                                       .filter(Boolean);
    if (tema) aportes.tema = tema;
    if (objetivo) aportes.objetivo = objetivo;
    if (nivel) aportes.nivel = nivel;
    if (criterios.length) aportes.criterios = criterios;

    var mensaje = pendiente;
    cerrar();
    enviar(mensaje, formulario, aportes);
  });

  /* ---------- Envio al agente ---------- */
  function enviar(mensaje, formulario, aportes) {
    var archivos = mensaje.files || [];
    Promise.all(archivos.map(aBase64)).then(function (convertidos) {
      var cuerpo = {
        pedido: mensaje.text || "",
        docente: (mensaje && mensaje.teacher) || "",
        curso: (mensaje && mensaje.course) || "",
        formulario: formulario,
        aportes: aportes || {},
        archivos: convertidos.filter(Boolean)
      };
      window.aulaIA.thinking(true);
      fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cuerpo)
      }).then(function (r) { return r.json(); }).then(function (datos) {
        window.aulaIA.thinking(false);
        window.aulaIA.reply(resumen(datos));
      }).catch(function (error) {
        window.aulaIA.thinking(false);
        window.aulaIA.reply("No pude contactar con el agente.\n\n" + String(error));
      });
    });
  }

  function aBase64(file) {
    return new Promise(function (resolver) {
      var lector = new FileReader();
      lector.onload = function () {
        var s = String(lector.result);
        resolver({ nombre: file.name, contenido_base64: s.slice(s.indexOf(",") + 1) });
      };
      lector.onerror = function () { resolver(null); };
      lector.readAsDataURL(file);
    });
  }

  /* ---------- Resumen amigable ---------- */
  function resumen(r) {
    if (!r || typeof r !== "object") return "El agente no devolvio una respuesta valida.";
    var d = r.datos || {};
    var lineas = [];
    if (r.ok) {
      lineas.push("**Actividad interpretada**", "");
      lineas.push("- **Tema:** " + (d.tema || "(sin tema)"));
      if (d.objetivo) lineas.push("- **Objetivo:** " + d.objetivo);
      if (d.nivel) lineas.push("- **Nivel:** " + d.nivel);
      if (d.criterios && d.criterios.length) lineas.push("- **Criterios:** " + d.criterios.join("; "));
      lineas.push("- **Material usado:**");
      var usados = r.material_usado || [];
      if (usados.length) {
        usados.forEach(function (u) {
          lineas.push("- **" + u.id + ":** " + (u.extracto || "(sin texto)"));
        });
      } else if (d.partes && d.partes.length) {
        lineas.push("- " + d.partes.join(", "));
      } else {
        lineas.push("- (ninguna parte)");
      }
      lineas.push("", "Ya tengo la solicitud ordenada, lista para los siguientes pasos.");
      if (r.prompt && r.prompt.guardado) {
        lineas.push("- **Prompt del Agente 2:** " + (r.prompt.nombre_archivo || "actividad.txt") + " (guardado en Storage)");
      }
    } else {
      lineas.push("No pude completar la solicitud todavia.", "");
      var faltantes = d.faltantes || [];
      var otros = faltantes.filter(function (c) { return c !== "partes"; });
      if (otros.length) lineas.push("- **Falta que completes:** " + otros.join(", ") + ".");
      if (faltantes.indexOf("partes") !== -1) {
        lineas.push("- **Material:** no encontre material relacionado con el tema en el PDF. " +
                    "Revisa que el PDF tenga texto seleccionable y trate el tema, o ajusta el pedido.");
      }
      var errores = (r.errores || []).filter(function (e) { return e.indexOf("Falta informacion") !== 0; });
      if (errores.length) lineas.push("- **Detalle:** " + errores.join(" "));
    }
    if (r.avisos && r.avisos.length) lineas.push("", "- **Aviso:** " + r.avisos.join(" "));
    if (pendiente && (pendiente.teacher || pendiente.course)) {
      lineas.push("", "---");
      lineas.push("**Docente:** " + (pendiente.teacher || "-"));
      lineas.push("**Curso:** " + (pendiente.course || "-"));
    }
    return lineas.join("\n");
  }

  /* ---------- Validacion previa al envio ---------- */
  var avisoTimer = 0;

  function avisar(texto) {
    var t = document.getElementById("toast");
    if (!t) return;
    t.textContent = texto;
    t.hidden = false;
    t.classList.add("ag-error");
    clearTimeout(avisoTimer);
    avisoTimer = setTimeout(function () {
      t.hidden = true;
      t.classList.remove("ag-error");
    }, 4000);
  }

  function enPasoActividad() {
    var boton = document.getElementById("attach");
    return !!boton && !boton.disabled;
  }

  function adjuntos() {
    return Array.prototype.map.call(
      document.querySelectorAll("#attached .fname"),
      function (nodo) { return nodo.textContent || ""; }
    );
  }

  function esPdf(nombre) { return /\.pdf$/i.test(nombre); }

  function guardarEnvio(e) {
    var formFront = document.getElementById("form");
    if (!formFront || e.target !== formFront) return;
    if (!enPasoActividad()) return;

    var nombres = adjuntos();
    var entrada = document.getElementById("input");
    var texto = entrada ? entrada.value.trim() : "";
    var aviso = "";

    if (!nombres.length) {
      aviso = "Adjuntá el material de la clase (PDF) antes de enviar.";
    } else if (!nombres.some(esPdf)) {
      aviso = "El material tiene que ser un PDF con texto seleccionable.";
    } else if (!texto) {
      aviso = "Escribí qué actividad querés armar.";
    }
    if (!aviso) return;

    e.preventDefault();
    e.stopPropagation();
    avisar(aviso);
  }

  function protegerEnvio() {
    if (protegerEnvio.listo) return;
    protegerEnvio.listo = true;
    document.addEventListener("submit", guardarEnvio, true);
  }

  /* ---------- Enganche ---------- */
  function iniciar() {
    if (!window.aulaIA) { setTimeout(iniciar, 30); return; }
    window.aulaIA.onSend = function (mensaje) { abrir(mensaje); };
    protegerEnvio();
    poblarCursos(CURSOS_FALLBACK);
    cargarCursos();
  }
  iniciar();
})();
