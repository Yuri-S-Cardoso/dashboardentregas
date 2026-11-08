"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { layoutGrafico } = require("../static/js/graficos.js");
const { parametrosPermitidos, iniciarNavegacao } = require("../static/js/navegacao.js");

test("gráficos usam largura disponível de 360, 390, 768 e desktop", () => {
  for (const tela of [360, 390, 768, 1365]) {
    const disponivel = tela < 768 ? tela - 66 : Math.min(760, tela - 100);
    for (const series of [2, 3]) {
      const layout = layoutGrafico(disponivel, series);
      assert.ok(layout.largura <= disponivel);
      assert.equal(layout.compacto, disponivel < 520);
      assert.ok(layout.alturaLinha >= 30 + series * 27);
    }
  }
});
test("modo compacto coloca as séries abaixo do rótulo", () => {
  assert.equal(layoutGrafico(294, 2).esquerda, 0);
  assert.equal(layoutGrafico(760, 2).esquerda, 230);
});
test("memória de filtros não guarda tokens ou parâmetros desconhecidos", () => {
  const query = parametrosPermitidos("?periodo=dia&dia=2026-10-15&csrfmiddlewaretoken=privado&next=evil", ["periodo", "dia"]);
  assert.equal(query, "periodo=dia&dia=2026-10-15");
});
function contexto(armazenamentoBloqueado = false) {
  const memoria = new Map();
  const botao = { hidden: true, attrs: {}, events: {}, setAttribute(k, v) { this.attrs[k] = v; }, addEventListener(k, v) { this.events[k] = v; }, focus() { this.focado = true; } };
  const links = ["/", "/auditoria/", "/entregas/"].map((href) => ({ href, attrs: {}, setAttribute(k, v) { this.attrs[k] = v; } }));
  const menu = { dataset: { aberto: "false" }, querySelectorAll: () => links };
  const documento = {
    getElementById: () => menu, querySelector: () => botao,
    documentElement: { classList: { add() {} } }, events: {},
    addEventListener(k, v) { this.events[k] = v; }, querySelectorAll: () => [],
  };
  const armazenamento = {
    setItem(k, v) { if (armazenamentoBloqueado) throw Error("Bloqueado"); memoria.set(k, v); },
    getItem(k) { return memoria.get(k); },
  };
  return { documento, botao, menu, links, armazenamento, memoria };
}
test("menu abre, fecha por Escape e mantém atributos acessíveis", () => {
  const c = contexto();
  iniciarNavegacao(c.documento, { pathname: "/", search: "", origin: "http://localhost" }, c.armazenamento);
  assert.equal(c.botao.hidden, false);
  c.botao.events.click();
  assert.equal(c.menu.dataset.aberto, "true");
  assert.equal(c.botao.attrs["aria-expanded"], "true");
  c.documento.events.keydown({ key: "Escape" });
  assert.equal(c.menu.dataset.aberto, "false");
  assert.equal(c.botao.focado, true);
});
test("filtro aplicado permanece nos links de painel e auditoria", () => {
  const c = contexto();
  iniciarNavegacao(c.documento, { pathname: "/", search: "?periodo=dia&dia=2026-10-15", origin: "http://localhost" }, c.armazenamento);
  assert.equal(c.links[1].href, "/auditoria/?periodo=dia&dia=2026-10-15");
  assert.equal(c.links[0].attrs["aria-current"], "page");
});
test("menu continua utilizável sem armazenamento do navegador", () => {
  const c = contexto(true);
  assert.doesNotThrow(() => iniciarNavegacao(c.documento, { pathname: "/", search: "", origin: "http://localhost" }, c.armazenamento));
  c.botao.events.click();
  assert.equal(c.menu.dataset.aberto, "true");
});
test("mês padrão calculado no servidor persiste e semana salva usa domingo", () => {
  const c = contexto();
  c.menu.dataset.periodoAplicado = "periodo=mes&mes=10&ano=2026";
  iniciarNavegacao(c.documento, { pathname: "/", search: "", origin: "http://localhost" }, c.armazenamento);
  assert.equal(c.links[1].href, "/auditoria/?periodo=mes&mes=10&ano=2026");
  c.menu.dataset.periodoAplicado = "periodo=semana&semana=2026-10-25";
  iniciarNavegacao(c.documento, { pathname: "/", search: "?periodo=semana&semana=2026-10-29", origin: "http://localhost" }, c.armazenamento);
  assert.equal(c.links[0].href, "/?periodo=semana&semana=2026-10-25");
});
test("folha responsiva mantém rolagem nas tabelas e foco visível", () => {
  const css = fs.readFileSync(path.join(__dirname, "../static/css/responsivo.css"), "utf8");
  assert.ok(css.includes("max-width:767px"));
  assert.ok(css.includes("max-width:1023px"));
  assert.ok(css.includes("min-height:44px"));
  assert.ok(css.includes("max-width:100%"));
  assert.ok(css.includes(":focus-visible"));
  assert.ok(!css.includes("overflow-x:hidden"));
});
