"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { webcrypto } = require("node:crypto");
const D = require("../static/js/lote_dados.js");
const chave = "09c4c811-0e70-4c46-825f-67605f894d81";

function memoria() {
  const dados = new Map();
  return { getItem: k => dados.get(k) || null, setItem: (k, valor) => dados.set(k, valor), removeItem: k => dados.delete(k) };
}
function rascunho(linhas = [{ codigo: "000123", data: "", horario: "", situacao: D.BAIXA }]) {
  return { chave, data_padrao: "2026-10-22", situacao_padrao: D.BAIXA, linhas, colagem: "" };
}

test("colagem multilinha conserva zeros, texto e códigos repetidos", () => {
  const a = D.analisarColagem("000123\r\n000123\r\n3828807226\n");
  const linhas = D.mapearColagem(a, a.mapa, a.cabecalho, D.BAIXA);
  assert.deepEqual(linhas.map(l => l.codigo), ["000123", "000123", "3828807226"]);
  assert.ok(linhas.every(l => l.situacao === D.BAIXA && l.data === "" && l.horario === ""));
});
test("colagem Excel reconhece cabeçalho, data brasileira, horário e situação", () => {
  const a = D.analisarColagem("Código\tData\tHorário\tSituação\r\n000001\t22/10/2026\t12:34:56\tBaixa realizada\r\n000002\t23/10/2026\t\tInsucesso");
  assert.equal(a.cabecalho, true);
  const linhas = D.mapearColagem(a, a.mapa, true, D.BAIXA);
  assert.deepEqual(linhas, [{ codigo: "000001", data: "2026-10-22", horario: "12:34:56", situacao: D.BAIXA },
    { codigo: "000002", data: "2026-10-23", horario: "", situacao: D.INSUCESSO }]);
});
test("layout original sem cabeçalho e cabeçalhos reordenados", () => {
  const original = D.analisarColagem("000001\t22/10/2026\t00:00\tInsucesso");
  assert.equal(D.mapearColagem(original, original.mapa, false, D.BAIXA)[0].horario, "00:00");
  const a = D.analisarColagem("Situação\tCódigo\tData\nInsucesso\t0003\t22/10/2026");
  assert.equal(D.mapearColagem(a, a.mapa, true, D.BAIXA)[0].codigo, "0003");
});
test("mapeamento simples aceita código e horário em ordem diferente", () => {
  const a = D.analisarColagem("12:30\t00042\tignorar");
  assert.deepEqual(D.mapearColagem(a, ["horario", "codigo", ""], false, D.INSUCESSO),
    [{ codigo: "00042", data: "", horario: "12:30", situacao: D.INSUCESSO }]);
  assert.throws(() => D.mapearColagem(a, ["codigo", "codigo", ""], false, D.BAIXA));
  assert.throws(() => D.mapearColagem(a, ["", "", ""], false, D.BAIXA));
});
test("TSV lida com aspas, células vazias, BOM e linhas em branco", () => {
  assert.deepEqual(D.celulasTSV('\ufeff"00001"\t\t12:00\r\n\r\n"texto ""A"""\t\t'),
    [["00001", "", "12:00"], ['texto "A"', "", ""]]);
  assert.throws(() => D.celulasTSV('"sem fechamento'));
});
test("colagem não converte código para número e conserva dado inválido para correção", () => {
  const a = D.analisarColagem("001e10\t31/02/2026\t25:99\tDesconhecida");
  const linha = D.mapearColagem(a, a.mapa, false, D.BAIXA)[0];
  assert.equal(linha.codigo, "001e10");
  assert.equal(linha.data, "2026-02-31");
  assert.equal(linha.horario, "25:99");
  assert.equal(linha.situacao, "Desconhecida");
});
test("colagem de 50, 100 e 200 códigos conserva ordem e quantidade", () => {
  for (const quantidade of [1, 50, 100, 200]) {
    const codigos = Array.from({ length: quantidade }, (_, i) => String(i).padStart(10, "0"));
    const a = D.analisarColagem(codigos.join("\n"));
    const linhas = D.mapearColagem(a, a.mapa, false, D.BAIXA);
    assert.deepEqual(linhas.map(l => l.codigo), codigos);
    assert.equal(D.contar(linhas, D.BAIXA).preenchidos, quantidade);
  }
});
test("limites rejeitam colagens vazias ou acima de 500 sem truncar registros", () => {
  assert.throws(() => D.analisarColagem("\n\n"));
  const a = D.analisarColagem(Array.from({ length: 501 }, () => "0001").join("\n"));
  assert.throws(() => D.mapearColagem(a, a.mapa, false, D.BAIXA));
  assert.throws(() => D.analisarColagem("x".repeat(250001)));
});
test("contadores ignoram linhas vazias e incluem linhas incompletas para correção", () => {
  const linhas = [{ codigo: "", situacao: D.BAIXA }, { codigo: "a", situacao: D.BAIXA },
    { codigo: "b", situacao: D.INSUCESSO }, { horario: "12:30", situacao: D.BAIXA }];
  assert.deepEqual(D.contar(linhas, D.BAIXA), { preenchidos: 3, baixas: 2, insucessos: 1 });
});
test("Enter avança o código sem enviar e cria uma linha apenas no fim", () => {
  let foco = -1, adicoes = 0, prevenido = 0;
  const linha = i => ({ campos: { codigo: { focus: () => { foco = i; } } } });
  const linhas = [linha(0), linha(1)];
  const evento = { key: "Enter", preventDefault: () => { prevenido++; } };
  const adicionar = () => { adicoes++; linhas.push(linha(linhas.length)); };
  D.avancarComEnter(evento, 0, linhas, adicionar, () => {});
  assert.equal(foco, 1); assert.equal(adicoes, 0);
  D.avancarComEnter(evento, 1, linhas, adicionar, () => {});
  assert.equal(foco, 2); assert.equal(adicoes, 1); assert.equal(prevenido, 2);
});
test("Tab continua nativo e Enter no limite não cria linha fora do lote", () => {
  let prevenido = false, aviso = "";
  D.avancarComEnter({ key: "Tab", preventDefault: () => { prevenido = true; } }, 0, [], () => assert.fail(), () => assert.fail());
  assert.equal(prevenido, false);
  D.avancarComEnter({ key: "Enter", preventDefault: () => {} }, 0, [{}], () => assert.fail(), texto => { aviso = texto; }, 1);
  assert.match(aviso, /Limite/);
});
test("rascunho restaura dados e a mesma chave de reenvio, sem credenciais", () => {
  const armazenamento = memoria();
  const dados = { ...rascunho(), password: "nao guardar", csrfmiddlewaretoken: "nao guardar", sessionid: "nao guardar" };
  assert.equal(D.guardarRascunho(armazenamento, "lote:1", dados), true);
  const bruto = armazenamento.getItem("lote:1");
  assert.ok(!bruto.includes("nao guardar"));
  assert.deepEqual(D.lerRascunho(armazenamento, "lote:1").linhas, dados.linhas);
  assert.equal(D.lerRascunho(armazenamento, "lote:1").chave, chave);
  assert.equal(D.lerRascunho(armazenamento, "lote:2"), null);
});
test("rascunho é tolerante a armazenamento indisponível e dados corrompidos", () => {
  const bloqueado = { getItem() { throw new Error(); }, setItem() { throw new Error(); }, removeItem() { throw new Error(); } };
  assert.equal(D.lerRascunho(bloqueado, "lote"), null);
  assert.equal(D.guardarRascunho(bloqueado, "lote", rascunho()), false);
  assert.equal(D.apagarRascunho(bloqueado, "lote"), false);
  const armazenamento = memoria(); armazenamento.setItem("lote", "invalido");
  assert.equal(D.lerRascunho(armazenamento, "lote"), null);
});
test("sucesso apaga só o rascunho do lote salvo e preserva outro lote da mesma conta", () => {
  const armazenamento = memoria();
  D.guardarRascunho(armazenamento, "lote:1", rascunho());
  D.apagarRascunho(armazenamento, "lote:1", "outro");
  assert.ok(D.lerRascunho(armazenamento, "lote:1"));
  D.apagarRascunho(armazenamento, "lote:1", chave);
  assert.equal(armazenamento.getItem("lote:1"), null);
});
test("descartar gera nova chave de lote válida sem exigir HTTPS na LAN", () => {
  const nova = D.novaChave(webcrypto);
  assert.match(nova, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  assert.notEqual(nova, D.novaChave(webcrypto));
});
test("a confirmação bloqueia reenvio no navegador e recupera os botões ao voltar", () => {
  const eventos = {}, janelaEventos = {}, botoes = [{ disabled: false }];
  const form = { dataset: { previa: "1" }, addEventListener: (nome, fn) => { eventos[nome] = fn; },
    setAttribute() {}, removeAttribute() {}, querySelectorAll: () => botoes };
  const contexto = { document: { getElementById: () => form, querySelector: () => null },
    window: { EntregasLoteDados: D, localStorage: memoria(), setTimeout: fn => fn(), addEventListener: (nome, fn) => { janelaEventos[nome] = fn; } } };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../static/js/lote.js"), "utf8"), contexto);
  let bloqueado = 0;
  eventos.submit({ preventDefault: () => { bloqueado++; } });
  eventos.submit({ preventDefault: () => { bloqueado++; } });
  assert.equal(bloqueado, 1); assert.equal(botoes[0].disabled, true);
  janelaEventos.pageshow(); assert.equal(botoes[0].disabled, false);
});
test("a página de sucesso limpa o rascunho correspondente sem acessar formulários", () => {
  const armazenamento = memoria(); D.guardarRascunho(armazenamento, "lote:1", rascunho());
  const estado = {};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../static/js/lote.js"), "utf8"), {
    document: { querySelector: () => ({ dataset: { loteSalvo: chave, rascunho: "lote:1" } }), getElementById: () => estado },
    window: { EntregasLoteDados: D, localStorage: armazenamento }
  });
  assert.equal(armazenamento.getItem("lote:1"), null);
  assert.match(estado.textContent, /apagado/);
});
