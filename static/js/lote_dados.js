/* Dados da grade: texto preservado, colagem TSV e rascunho sem credenciais. */
(function (raiz) {
  "use strict";
  const CAMPOS = ["codigo", "data", "horario", "situacao"];
  const BAIXA = "Baixa realizada", INSUCESSO = "Insucesso", LIMITE = 500;
  const texto = valor => typeof valor === "string" ? valor : "";
  const normalizar = valor => texto(valor).normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim().toLowerCase();

  function vazia(linha, situacao) {
    return !["codigo", "data", "horario"].some(campo => texto(linha[campo]).trim()) &&
      ["", situacao].includes(texto(linha.situacao).trim());
  }

  function contar(linhas, situacao) {
    const usadas = linhas.filter(linha => !vazia(linha, situacao));
    return { preenchidos: usadas.length,
      baixas: usadas.filter(linha => (linha.situacao || situacao) === BAIXA).length,
      insucessos: usadas.filter(linha => (linha.situacao || situacao) === INSUCESSO).length };
  }

  function celulasTSV(conteudo) {
    if (conteudo.length > 250000) throw new Error("A colagem é muito grande. Divida em lotes menores.");
    const linhas = []; let linha = [], celula = "", aspas = false;
    const origem = conteudo.replace(/^\ufeff/, "");
    for (let i = 0; i < origem.length; i++) {
      const caractere = origem[i];
      if (caractere === '"' && (aspas || celula === "")) {
        if (aspas && origem[i + 1] === '"') { celula += '"'; i++; }
        else aspas = !aspas;
      } else if (!aspas && caractere === "\t") { linha.push(celula); celula = ""; }
      else if (!aspas && (caractere === "\n" || caractere === "\r")) {
        if (caractere === "\r" && origem[i + 1] === "\n") i++;
        linha.push(celula); linhas.push(linha); linha = []; celula = "";
      } else celula += caractere;
    }
    if (aspas) throw new Error("Há uma célula com aspas sem fechamento. Confira a colagem.");
    linha.push(celula); linhas.push(linha);
    return linhas.filter(item => item.some(valor => valor.trim() !== ""));
  }

  function analisarColagem(conteudo) {
    const linhas = celulasTSV(conteudo);
    if (!linhas.length) throw new Error("Cole pelo menos um código.");
    const colunas = Math.max(...linhas.map(linha => linha.length));
    if (colunas > 12) throw new Error("Selecione somente as colunas das entregas, até 12 colunas.");
    const nomes = { codigo: "codigo", "codigo da entrega": "codigo", data: "data", horario: "horario", hora: "horario", situacao: "situacao", status: "situacao" };
    const cabecalho = linhas[0].some(valor => nomes[normalizar(valor)] === "codigo");
    const mapa = Array.from({ length: colunas }, (_, i) => cabecalho ? (nomes[normalizar(linhas[0][i])] || "") : (CAMPOS[i] || ""));
    return { linhas, colunas, cabecalho, mapa };
  }

  function dataISO(valor) {
    const resultado = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(valor.trim());
    return resultado ? `${resultado[3]}-${resultado[2].padStart(2, "0")}-${resultado[1].padStart(2, "0")}` : valor.trim();
  }

  function mapearColagem(analise, mapa, cabecalho, situacao) {
    if (mapa.filter(campo => campo === "codigo").length !== 1 ||
        CAMPOS.some(campo => mapa.filter(item => item === campo).length > 1)) {
      throw new Error("Selecione uma coluna Código e no máximo uma de cada outro campo.");
    }
    const linhas = analise.linhas.slice(cabecalho ? 1 : 0);
    if (!linhas.length || linhas.length > LIMITE) throw new Error(`A colagem deve conter entre 1 e ${LIMITE} registros.`);
    return linhas.map(celulas => {
      const registro = { codigo: "", data: "", horario: "", situacao };
      mapa.forEach((campo, i) => { if (CAMPOS.includes(campo)) registro[campo] = texto(celulas[i]).trim(); });
      registro.data = dataISO(registro.data);
      registro.situacao = ({ "baixa realizada": BAIXA, insucesso: INSUCESSO })[normalizar(registro.situacao)] || registro.situacao || situacao;
      return registro;
    });
  }

  function criarRascunho(dados) {
    // A lista explícita impede guardar campos do formulário como CSRF ou sessão.
    return { versao: 1, chave: texto(dados.chave), data_padrao: texto(dados.data_padrao),
      situacao_padrao: texto(dados.situacao_padrao),
      linhas: dados.linhas.map(linha => Object.fromEntries(CAMPOS.map(campo => [campo, texto(linha[campo])]))),
      colagem: texto(dados.colagem), atualizado_em: new Date().toISOString() };
  }

  function lerRascunho(armazenamento, chave) {
    try {
      const dados = JSON.parse(armazenamento.getItem(chave));
      if (!dados || dados.versao !== 1 || !/^[0-9a-f-]{36}$/i.test(dados.chave) ||
          typeof dados.data_padrao !== "string" || ![BAIXA, INSUCESSO].includes(dados.situacao_padrao) ||
          !Array.isArray(dados.linhas) || dados.linhas.length > LIMITE ||
          dados.linhas.some(linha => !linha || typeof linha !== "object" || CAMPOS.some(campo => typeof linha[campo] !== "string"))) return null;
      return criarRascunho(dados);
    } catch (_) { return null; }
  }

  function guardarRascunho(armazenamento, chave, dados) {
    try { armazenamento.setItem(chave, JSON.stringify(criarRascunho(dados))); return true; }
    catch (_) { return false; }
  }

  function apagarRascunho(armazenamento, chave, loteSalvo) {
    try {
      const existente = JSON.parse(armazenamento.getItem(chave));
      if (!loteSalvo || (existente && existente.chave === loteSalvo)) armazenamento.removeItem(chave);
      return true;
    } catch (_) { return false; }
  }

  function novaChave(crypto) {
    // getRandomValues funciona também na LAN HTTP; a chave não é uma credencial.
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
    const hex = Array.from(bytes, valor => valor.toString(16).padStart(2, "0")).join("");
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  }

  function avancarComEnter(evento, indice, linhas, adicionar, avisar, limite = LIMITE) {
    if (evento.key !== "Enter" || evento.isComposing) return;
    evento.preventDefault();
    if (indice === linhas.length - 1) {
      if (linhas.length >= limite) { avisar(`Limite de ${limite} linhas atingido.`); return; }
      adicionar();
    }
    linhas[indice + 1].campos.codigo.focus();
  }

  const api = { CAMPOS, BAIXA, INSUCESSO, LIMITE, vazia, contar, celulasTSV, analisarColagem,
    dataISO, mapearColagem, criarRascunho, lerRascunho, guardarRascunho, apagarRascunho, novaChave, avancarComEnter };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else raiz.EntregasLoteDados = api;
})(typeof window !== "undefined" ? window : globalThis);
