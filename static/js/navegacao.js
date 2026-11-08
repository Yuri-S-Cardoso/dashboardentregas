"use strict";

function parametrosPermitidos(busca, campos) {
  const origem = new URLSearchParams(busca);
  const saida = new URLSearchParams();
  campos.forEach((campo) => { if (origem.has(campo)) saida.set(campo, origem.get(campo)); });
  return saida.toString();
}

function iniciarNavegacao(documento, localizacao, armazenamento) {
  const menu = documento.getElementById("menu-principal");
  if (!menu) return;
  const botao = documento.querySelector("[data-menu]");
  documento.documentElement.classList.add("js");
  botao.hidden = false;
  const alternar = (aberto) => {
    menu.dataset.aberto = String(aberto);
    botao.setAttribute("aria-expanded", String(aberto));
  };
  botao.addEventListener("click", () => alternar(menu.dataset.aberto !== "true"));
  documento.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && menu.dataset.aberto === "true") { alternar(false); botao.focus(); }
  });
  const analiticos = ["periodo", "inicio", "fim", "dia", "semana", "mes", "ano", "quinzena", "dias_projecao"];
  try {
    if (["/", "/auditoria/", "/conciliacao/"].includes(localizacao.pathname)) {
      const aplicado = menu.dataset.periodoAplicado;
      armazenamento.setItem("entregas:filtro-painel", parametrosPermitidos(aplicado === undefined ? localizacao.search : aplicado, analiticos));
    }
    if (localizacao.pathname === "/entregas/") armazenamento.setItem("entregas:filtro-lista", parametrosPermitidos(localizacao.search, ["data", "situacao"]));
    menu.querySelectorAll("a").forEach((link) => {
      const url = new URL(link.href, localizacao.origin);
      if (["/", "/auditoria/", "/conciliacao/"].includes(url.pathname)) url.search = parametrosPermitidos(armazenamento.getItem("entregas:filtro-painel") || "", analiticos);
      if (url.pathname === "/entregas/") url.search = armazenamento.getItem("entregas:filtro-lista") || "";
      link.href = url.pathname + url.search;
      if (url.pathname === localizacao.pathname) link.setAttribute("aria-current", "page");
    });
  } catch (_) { /* O menu funciona mesmo quando o navegador bloqueia sessionStorage. */ }
  documento.querySelectorAll(".tabela").forEach((tabela) => {
    tabela.tabIndex = 0;
    tabela.setAttribute("role", "region");
    if (!tabela.hasAttribute("aria-labelledby")) tabela.setAttribute("aria-label", "Tabela com todas as colunas; role horizontalmente quando necessário");
  });
}
if (typeof module !== "undefined" && module.exports) module.exports = { parametrosPermitidos, iniciarNavegacao };
if (typeof document !== "undefined") {
  let armazenamento;
  try { armazenamento = window.sessionStorage; } catch (_) { /* Navegação continua sem persistência. */ }
  iniciarNavegacao(document, window.location, armazenamento);
}
