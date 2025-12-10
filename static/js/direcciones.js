// =========================================================
//   BARRIOS POR CIUDAD (Puedes expandirlo cuando quieras)
// =========================================================
const BARRIOS_POR_CIUDAD = {
  "Bogotá": [
    "Chapinero",
    "Usaquén",
    "Suba",
    "Kennedy",
    "Engativá",
    "Fontibón"
  ],
  "Medellín": [
    "El Poblado",
    "Laureles",
    "Bello",
    "Envigado",
    "Itagüí"
  ],
  "Cali": [
    "San Fernando",
    "Granada",
    "Ciudad Jardín"
  ],
  "Barranquilla": [
    "El Prado",
    "Alto Prado",
    "Riomar"
  ]
};

document.addEventListener("DOMContentLoaded", function () {
  // =========================================================
  //   SELECTORES FORMULARIO
  // =========================================================
  const direccionForm = document.getElementById("direccion-form");
  const actionInput = document.getElementById("direccion_form_action");
  const direccionIdInput = document.getElementById("direccion_id");

  const nombreInput = document.getElementById("id_nombre_contacto");
  const telefonoInput = document.getElementById("id_telefono_contacto");
  const ciudadSelect = document.getElementById("id_ciudad");
  const barrioSelect = document.getElementById("id_barrio");
  const complementoInput = document.getElementById("id_complemento");
  const principalCheckbox = direccionForm
    ? direccionForm.querySelector('input[name="esPrincipal"]')
    : null;

  // Si no estamos en la página de direcciones, salimos
  if (!direccionForm || !ciudadSelect || !barrioSelect) {
    return;
  }

  // =========================================================
  //   FUNCIÓN PARA RELLENAR BARRIOS
  // =========================================================
  function poblarBarrios(ciudad, barrioSeleccionado) {
    barrioSelect.innerHTML = "";

    if (!ciudad || !BARRIOS_POR_CIUDAD[ciudad]) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "Primero selecciona una ciudad";
      barrioSelect.appendChild(opt);
      barrioSelect.disabled = true;
      return;
    }

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Selecciona un barrio";
    barrioSelect.appendChild(placeholder);

    BARRIOS_POR_CIUDAD[ciudad].forEach((barrio) => {
      const opt = document.createElement("option");
      opt.value = barrio;
      opt.textContent = barrio;
      barrioSelect.appendChild(opt);
    });

    barrioSelect.disabled = false;

    if (barrioSeleccionado) {
      barrioSelect.value = barrioSeleccionado;
    }
  }

  // Estado inicial
  barrioSelect.disabled = true;

  ciudadSelect.addEventListener("change", (e) => {
    poblarBarrios(e.target.value);
  });

  // =========================================================
  //   MODO CREAR / EDITAR
  // =========================================================

  // Botones de editar en la lista
  const editButtons = document.querySelectorAll(".direccion-edit-btn");

  editButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const data = btn.dataset;

      // Pasar formulario a modo "actualizar"
      if (actionInput) actionInput.value = "actualizar";
      if (direccionIdInput) direccionIdInput.value = data.id || "";

      if (nombreInput) nombreInput.value = data.nombre || "";
      if (telefonoInput) telefonoInput.value = data.telefono || "";
      if (complementoInput) complementoInput.value = data.complemento || "";

      if (ciudadSelect) {
        const ciudad = data.ciudad || "";
        ciudadSelect.value = ciudad;
        poblarBarrios(ciudad, data.barrio || "");
      }

      if (principalCheckbox) {
        principalCheckbox.checked = data.esPrincipal === "1";
      }

      // Opcional: cambiar texto del título
      const titulo = document.querySelector(".perfil-block-title");
      if (titulo) {
        titulo.textContent = "Editar dirección";
      }

      // Hacer scroll al formulario
      direccionForm.scrollIntoView({
        behavior: "smooth",
        block: "start"
      });
    });
  });

  // Si quisieras, podrías añadir un botón "Cancelar edición"
  // que devuelva action="crear" y limpie el formulario.
});
