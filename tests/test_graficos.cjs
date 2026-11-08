"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { prepararGrafico, montarGraficos } = require("../static/js/graficos.js");

// Objetos mínimos de teste para verificar a árvore SVG e as interações, sem navegador.
class NoTeste {
  constructor(tag) { this.tag = tag; this.children = []; this.attrs = {}; this.style = {}; this.events = {}; }
  setAttribute(chave, valor) { this.attrs[chave] = valor; }
  append(...filhos) { this.children.push(...filhos); }
  replaceChildren(...filhos) { this.children = filhos; }
  addEventListener(nome, callback) { this.events[nome] = callback; }
  descendentes(tag) { return this.children.flatMap((f) => [ ...(f.tag === tag ? [f] : []), ...f.descendentes(tag)]); }
}
class DocumentoTeste {
  constructor(graficos) {
    this.dados = { textContent: JSON.stringify(graficos) };
    this.recipientes = new Map(graficos.map((g) => [g.id, new NoTeste("div")]));
  }
  getElementById() { return this.dados; }
  querySelector(seletor) { return this.recipientes.get(seletor.match(/data-grafico="([^"]+)"/)[1]); }
  createElement(tag) { return new NoTeste(tag); }
  createElementNS(ns, tag) { assert.equal(ns, "http://www.w3.org/2000/svg"); return new NoTeste(tag); }
}
const grafico = (valores = ["160.00", null, "0"]) => ({ id: "teste", titulo: "Teste", unidade: "reais", rotulos: ["15/10", "16/10", "19/10"], series: [{ nome: "Valores", valores }] });

test("ausência e zero continuam distintos na preparação", () => {
  const resultado = prepararGrafico(grafico([null, "0", "13.54"]));
  assert.deepEqual(resultado.series[0].valores, [null, 0, 13.54]);
  assert.equal(resultado.possuiDados, true);
});
test("valores não finitos ou inválidos não produzem coordenadas", () => {
  assert.deepEqual(prepararGrafico(grafico(["NaN", "Infinity", ""])).series[0].valores, [null, null, null]);
});
test("renderização produz barras, rótulos brasileiros e ausência explícita", () => {
  const documento = new DocumentoTeste([grafico()]);
  montarGraficos(documento);
  const recipiente = documento.recipientes.get("teste");
  assert.equal(recipiente.descendentes("svg").length, 1);
  assert.equal(recipiente.descendentes("rect").length, 2);
  assert.equal(recipiente.descendentes("rect")[1].attrs.width, "0");
  assert.ok(recipiente.descendentes("text").some((n) => n.textContent.includes("Não informado")));
  assert.ok(recipiente.descendentes("text").some((n) => n.textContent.includes("160,00")));
});
test("legendas alternam a série sem modificar os dados de origem", () => {
  const dados = grafico();
  const antes = JSON.stringify(dados);
  const documento = new DocumentoTeste([dados]);
  montarGraficos(documento);
  const recipiente = documento.recipientes.get("teste");
  const botao = recipiente.descendentes("button")[0];
  botao.events.click();
  assert.equal(botao.attrs["aria-pressed"], "false");
  assert.equal(recipiente.descendentes("rect").length, 0);
  botao.events.click();
  assert.equal(recipiente.descendentes("rect").length, 2);
  assert.equal(JSON.stringify(dados), antes);
});
test("gráfico sem valores não inventa barras", () => {
  const documento = new DocumentoTeste([grafico([null, null, null])]);
  montarGraficos(documento);
  const recipiente = documento.recipientes.get("teste");
  assert.equal(recipiente.descendentes("svg").length, 0);
  assert.ok(recipiente.descendentes("p").some((n) => n.textContent.includes("Sem valores")));
});
test("página sem payload não executa renderização", () => {
  assert.doesNotThrow(() => montarGraficos({ getElementById: () => null }));
});

test("situações distintas têm três cores e legendas independentes", () => {
  const dados = { id: "situacoes", titulo: "Encomendas", unidade: "numero", rotulos: ["20/10"],
    series: ["Concluídas sem insucesso", "Pendentes", "Recuperadas"].map((nome) => ({ nome, valores: [1] })) };
  const documento = new DocumentoTeste([dados]);
  montarGraficos(documento);
  const recipiente = documento.recipientes.get("situacoes");
  assert.equal(new Set(recipiente.descendentes("rect").map((barra) => barra.attrs.fill)).size, 3);
  const botoes = recipiente.descendentes("button");
  assert.equal(botoes.length, 3);
  botoes[2].events.click();
  assert.equal(recipiente.descendentes("rect").length, 2);
  assert.equal(botoes[0].attrs["aria-pressed"], "true");
  botoes[2].events.click();
  assert.equal(recipiente.descendentes("rect").length, 3);
});
test("filtros ativam apenas os campos do período escolhido", () => {
  const seletor = new NoTeste("select"); seletor.value = "dia";
  const grupos = ["dia", "semana", "mes quinzena"].map((tipos) => {
    const campo = {};
    return { dataset: { periodos: tipos }, campo, querySelectorAll: () => [campo] };
  });
  const formulario = { querySelector: () => seletor, querySelectorAll: () => grupos };
  const contexto = { document: { querySelectorAll: () => [formulario] } };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../static/js/filtros.js"), "utf8"), contexto);
  assert.equal(grupos[0].campo.disabled, false);
  assert.equal(grupos[1].hidden, true);
  seletor.value = "quinzena";
  seletor.events.change();
  assert.equal(grupos[0].hidden, true);
  assert.equal(grupos[2].campo.disabled, false);
});
const arquivoReal = path.join(__dirname, "../relatorios/etapa02_graficos_dados.json");
test("sete gráficos gerados com dados históricos renderizam SVG", { skip: !fs.existsSync(arquivoReal) }, () => {
  const dados = JSON.parse(fs.readFileSync(arquivoReal, "utf8"));
  assert.equal(dados.length, 7);
  const documento = new DocumentoTeste(dados);
  montarGraficos(documento);
  for (const recipiente of documento.recipientes.values()) assert.equal(recipiente.descendentes("svg").length, 1);
});
