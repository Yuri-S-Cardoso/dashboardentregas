"use strict";

function iniciarMenuPainel(documento) {
  const menu = documento.querySelector("[data-menu-painel]");
  if (!menu) return;
  const resumo = menu.querySelector(":scope > summary");
  const painel = menu.querySelector(".menu-painel-opcoes");
  const botao = menu.querySelector("[data-fechar-painel]");
  const sincronizar = () => resumo.setAttribute("aria-expanded", String(menu.open));
  const fechar = (devolverFoco = true) => {
    menu.open = false;
    sincronizar();
    if (devolverFoco) resumo.focus();
  };
  botao.hidden = false;
  botao.addEventListener("click", () => fechar());
  menu.addEventListener("toggle", sincronizar);
  documento.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && menu.open) { evento.preventDefault(); fechar(); }
  });
  documento.addEventListener("click", (evento) => {
    if (menu.open && evento.target !== resumo && !painel.contains(evento.target)) fechar(false);
  });
  // Popover não modal: Tab pode sair, sem prender o foco atrás da camada.
  documento.addEventListener("focusin", (evento) => {
    if (menu.open && !menu.contains(evento.target)) fechar(false);
  });
  sincronizar();
}
if (typeof module !== "undefined" && module.exports) module.exports = { iniciarMenuPainel };
if (typeof document !== "undefined") iniciarMenuPainel(document);
