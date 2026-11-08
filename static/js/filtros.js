"use strict";

document.querySelectorAll("[data-filtro-periodo]").forEach((formulario) => {
  const seletor = formulario.querySelector('[name="periodo"]');
  function atualizar() {
    formulario.querySelectorAll("[data-periodos]").forEach((grupo) => {
      const ativo = grupo.dataset.periodos.split(" ").includes(seletor.value);
      grupo.hidden = !ativo;
      grupo.querySelectorAll("input, select").forEach((campo) => { campo.disabled = !ativo; });
    });
  }
  seletor.addEventListener("change", atualizar);
  atualizar();
});
