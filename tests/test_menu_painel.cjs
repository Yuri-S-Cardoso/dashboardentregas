"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const { iniciarMenuPainel } = require("../static/js/menu_painel.js");

function contexto() {
  const elemento = () => ({ events: {}, attrs: {}, hidden: true,
    addEventListener(k, f) { this.events[k] = f; },
    setAttribute(k, v) { this.attrs[k] = v; }, focus() { this.focado = true; } });
  const resumo = elemento(), botao = elemento(), campo = elemento();
  const painel = { contains: (alvo) => [campo, botao].includes(alvo) };
  const menu = { ...elemento(), open: false, contains: (alvo) => [campo, botao, resumo].includes(alvo),
    querySelector: (seletor) => seletor.includes("summary") ? resumo : seletor.includes("opcoes") ? painel : botao };
  const documento = { ...elemento(), querySelector: () => menu };
  iniciarMenuPainel(documento);
  return { menu, resumo, botao, campo, painel, documento };
}

test("menu usa toggle nativo, informa expansão e mostra fechar", () => {
  const c = contexto();
  assert.equal(c.botao.hidden, false);
  assert.equal(c.resumo.attrs["aria-expanded"], "false");
  c.menu.open = true; c.menu.events.toggle();
  assert.equal(c.resumo.attrs["aria-expanded"], "true");
});
test("Escape fecha e devolve foco ao botão de abertura", () => {
  const c = contexto(); c.menu.open = true;
  let impedido = false;
  c.documento.events.keydown({ key: "Escape", preventDefault() { impedido = true; } });
  assert.equal(c.menu.open, false);
  assert.equal(c.resumo.focado, true);
  assert.equal(impedido, true);
});
test("botão fechar retorna foco e atualiza aria-expanded", () => {
  const c = contexto(); c.menu.open = true; c.botao.events.click();
  assert.equal(c.menu.open, false);
  assert.equal(c.resumo.focado, true);
  assert.equal(c.resumo.attrs["aria-expanded"], "false");
});
test("clique ou toque dentro mantém aberto; fora fecha", () => {
  const c = contexto(); c.menu.open = true;
  for (const target of [c.campo, c.botao, c.resumo]) {
    c.documento.events.click({ target }); assert.equal(c.menu.open, true);
  }
  c.documento.events.click({ target: {} });
  assert.equal(c.menu.open, false);
});
test("Tab pode sair do popover sem sequestrar foco", () => {
  const c = contexto(); c.menu.open = true;
  c.documento.events.focusin({ target: c.campo }); assert.equal(c.menu.open, true);
  c.documento.events.focusin({ target: {} }); assert.equal(c.menu.open, false);
  assert.equal(c.resumo.focado, undefined);
});
test("página sem menu não registra handlers", () => {
  assert.doesNotThrow(() => iniciarMenuPainel({ querySelector: () => null }));
});
test("menu sobreposto, largura contida e rolagem própria em celular", () => {
  const css = fs.readFileSync("static/css/responsivo.css", "utf8");
  const regra = css.match(/\.menu-painel-opcoes \{([^}]+)\}/)[1];
  assert.match(regra, /position:fixed/);
  assert.match(regra, /width:min\(640px,calc\(100% - 32px\)\)/);
  assert.match(regra, /100dvh/);
  assert.match(regra, /overflow-y:auto/);
  const html = fs.readFileSync("templates/painel/menu.html", "utf8");
  assert.match(html, /<summary class="botao secundario" aria-controls="opcoes-painel">/);
  assert.match(html, /aria-labelledby="titulo-menu-painel"/);
});
