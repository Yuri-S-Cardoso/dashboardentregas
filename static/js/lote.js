/* Grade local. Somente a confirmação POST grava o lote no servidor. */
(function () {
  "use strict";
  const D = window.EntregasLoteDados;
  const porId = id => document.getElementById(id);
  let armazenamento = null;
  try { armazenamento = window.localStorage; } catch (_) { /* O formulário continua disponível. */ }
  const sucesso = document.querySelector("[data-lote-salvo]");
  if (sucesso) {
    const apagado = D.apagarRascunho(armazenamento, sucesso.dataset.rascunho, sucesso.dataset.loteSalvo);
    porId("estado-rascunho").textContent = apagado ? "O rascunho deste lote foi apagado." : "Lote salvo. O navegador não permitiu limpar o rascunho local; confira antes de reutilizá-lo.";
    return;
  }
  const formulario = porId("lote-form");
  if (!formulario) return;
  let enviando = false;
  function bloquearEnvio(evento) {
    if (enviando) { evento.preventDefault(); return false; }
    enviando = true;
    // Desabilita depois da coleta nativa para conservar name/value do botão acionado.
    window.setTimeout(() => {
      formulario.querySelectorAll('button[type="submit"]').forEach(botao => { botao.disabled = true; });
    }, 0);
    formulario.setAttribute("aria-busy", "true");
    return true;
  }
  window.addEventListener("pageshow", () => {
    enviando = false;
    formulario.removeAttribute("aria-busy");
    formulario.querySelectorAll('button[type="submit"]').forEach(botao => { botao.disabled = false; });
  });
  if (formulario.dataset.previa === "1") { formulario.addEventListener("submit", bloquearEnvio); return; }

  const corpo = porId("grade-linhas"), modelo = porId("modelo-linha");
  const dataPadrao = porId("id_data_padrao"), situacaoPadrao = porId("id_situacao_padrao");
  const chave = porId("id_chave"), areaColagem = porId("texto-colagem");
  const chaveRascunho = formulario.dataset.rascunho, limite = Number(formulario.dataset.limite);
  const linhas = []; let temporizador, analise, coladas = [], anterior = situacaoPadrao.value;
  const dadosLinhas = () => linhas.map(linha => Object.fromEntries(D.CAMPOS.map(campo => [campo, linha.campos[campo].value])));
  function avisar(texto) { porId("aviso-grade").textContent = texto; porId("aviso-grade").hidden = !texto; }
  function atualizarResumo() {
    const resumo = D.contar(dadosLinhas(), situacaoPadrao.value);
    porId("contador-lote").textContent = `${resumo.preenchidos} registro${resumo.preenchidos === 1 ? "" : "s"} preenchido${resumo.preenchidos === 1 ? "" : "s"}`;
    porId("situacoes-lote").textContent = `${resumo.baixas} baixas · ${resumo.insucessos} insucessos`;
  }
  function guardar() {
    window.clearTimeout(temporizador);
    const gravado = D.guardarRascunho(armazenamento, chaveRascunho, { chave: chave.value,
      data_padrao: dataPadrao.value, situacao_padrao: situacaoPadrao.value, linhas: dadosLinhas(), colagem: areaColagem.value });
    porId("estado-rascunho").textContent = gravado ? "Rascunho salvo apenas neste navegador." : "Rascunho local indisponível. Mantenha esta página aberta até salvar o lote.";
  }
  function mudou() { atualizarResumo(); window.clearTimeout(temporizador); temporizador = window.setTimeout(guardar, 300); }
  function renumerar() {
    linhas.forEach((linha, i) => {
      linha.elemento.id = `linha-${i + 1}`;
      linha.elemento.querySelector("[data-numero]").textContent = String(i + 1);
      D.CAMPOS.forEach(campo => linha.campos[campo].setAttribute("aria-label", `${campo === "codigo" ? "Código" : campo === "horario" ? "Horário" : campo === "situacao" ? "Situação" : "Outra data"}, linha ${i + 1}`));
      linha.elemento.querySelector("[data-remover]").setAttribute("aria-label", `Remover linha ${i + 1}`);
    });
  }
  function preencher(linha, dados) {
    D.CAMPOS.forEach(campo => {
      const valor = dados[campo] || (campo === "situacao" ? situacaoPadrao.value : "");
      if (campo === "situacao" && ![D.BAIXA, D.INSUCESSO].includes(valor)) {
        const opcao = document.createElement("option"); opcao.value = valor; opcao.textContent = `Inválida: ${valor}`;
        linha.campos.situacao.appendChild(opcao);
      }
      if (campo === "horario") {
        const entrada = linha.campos.horario;
        entrada.type = "time"; entrada.value = valor;
        // O controle nativo apaga horários inválidos: preserve a colagem/rascunho para correção.
        if (valor && !entrada.value) entrada.type = "text";
      }
      linha.campos[campo].value = valor;
    });
    if (dados.data) linha.campos.data.closest("details").open = true;
  }
  function adicionar(dados = {}, destino = corpo) {
    if (linhas.length >= limite) { avisar(`Limite de ${limite} linhas atingido. Salve este lote antes de continuar.`); return; }
    const elemento = modelo.content.firstElementChild.cloneNode(true);
    const linha = { elemento, campos: Object.fromEntries(D.CAMPOS.map(campo => [campo, elemento.querySelector(`[data-campo="${campo}"]`)])) };
    preencher(linha, dados); linhas.push(linha); destino.appendChild(elemento);
    return linha;
  }
  function adicionarVarias(quantidade) {
    const fragmento = document.createDocumentFragment();
    for (let i = 0; i < quantidade; i++) adicionar({}, fragmento);
    corpo.appendChild(fragmento); renumerar(); mudou();
  }

  let iniciais = JSON.parse(porId("lote-inicial").textContent);
  const rascunho = formulario.dataset.enviado === "0" ? D.lerRascunho(armazenamento, chaveRascunho) : null;
  if (rascunho) {
    chave.value = rascunho.chave; dataPadrao.value = rascunho.data_padrao;
    situacaoPadrao.value = rascunho.situacao_padrao; anterior = situacaoPadrao.value;
    iniciais = rascunho.linhas; areaColagem.value = rascunho.colagem;
    porId("estado-rascunho").textContent = "Rascunho local restaurado. Confira a data e os registros antes de salvar.";
  } else if (!armazenamento) porId("estado-rascunho").textContent = "Rascunho local indisponível. Mantenha esta página aberta até salvar.";
  const fragmento = document.createDocumentFragment();
  (iniciais.length ? iniciais : Array.from({ length: 20 }, () => ({}))).forEach(dados => adicionar(dados, fragmento));
  corpo.appendChild(fragmento); renumerar(); atualizarResumo();
  JSON.parse(porId("lote-erros").textContent).forEach(erro => {
    const linha = linhas[erro.linha - 1]; if (!linha) return;
    linha.elemento.classList.add("linha-erro");
    Object.entries(erro.campos).forEach(([campo, mensagens]) => {
      const entrada = linha.campos[campo]; if (!entrada) return;
      const aviso = document.createElement("span"); aviso.className = "lote-erro-campo";
      aviso.id = `erro-${erro.linha}-${campo}`; aviso.textContent = mensagens.join(" ");
      entrada.setAttribute("aria-invalid", "true"); entrada.setAttribute("aria-describedby", aviso.id);
      entrada.parentNode.appendChild(aviso);
    });
  });
  if (porId("erros-lote")) porId("erros-lote").focus();
  formulario.addEventListener("input", mudou);
  formulario.addEventListener("change", mudou);
  situacaoPadrao.addEventListener("change", () => {
    linhas.forEach(linha => {
      const dados = Object.fromEntries(D.CAMPOS.map(campo => [campo, linha.campos[campo].value]));
      if (D.vazia(dados, anterior)) linha.campos.situacao.value = situacaoPadrao.value;
    });
    anterior = situacaoPadrao.value; mudou();
  });
  corpo.addEventListener("keydown", evento => {
    if (evento.target.dataset.campo !== "codigo") return;
    const indice = linhas.findIndex(linha => linha.campos.codigo === evento.target);
    D.avancarComEnter(evento, indice, linhas, () => { adicionar(); renumerar(); mudou(); }, avisar, limite);
  });
  formulario.addEventListener("keydown", evento => {
    if (evento.key === "Enter" && !evento.isComposing && ["INPUT", "SELECT"].includes(evento.target.tagName)) evento.preventDefault();
  });
  corpo.addEventListener("click", evento => {
    const botao = evento.target.closest("[data-remover]"); if (!botao) return;
    const indice = linhas.findIndex(linha => linha.elemento === botao.closest("tr"));
    const dados = dadosLinhas()[indice];
    if (!D.vazia(dados, situacaoPadrao.value) && !window.confirm("Remover esta linha do lote?")) return;
    linhas[indice].elemento.remove(); linhas.splice(indice, 1);
    if (!linhas.length) adicionar(); renumerar(); mudou();
  });
  porId("adicionar-linha").addEventListener("click", () => adicionarVarias(1));
  porId("adicionar-vinte").addEventListener("click", () => adicionarVarias(20));
  porId("limpar-lote").addEventListener("click", () => {
    if (!window.confirm("Limpar todas as linhas e descartar o rascunho local? Nada será excluído do banco.")) return;
    let nova;
    try { nova = D.novaChave(window.crypto); }
    catch (_) { avisar("Este navegador não permite iniciar outra grade com segurança. Use um navegador atualizado."); return; }
    D.apagarRascunho(armazenamento, chaveRascunho);
    window.clearTimeout(temporizador); corpo.replaceChildren(); linhas.splice(0);
    chave.value = nova; areaColagem.value = ""; coladas = [];
    porId("previa-colagem").hidden = true; avisar(""); adicionarVarias(20); guardar();
  });

  function atualizarColagem() {
    try {
      const mapa = Array.from(porId("mapeamento-colagem").querySelectorAll("select")).map(select => select.value);
      coladas = D.mapearColagem(analise, mapa, porId("colagem-cabecalho").checked, situacaoPadrao.value);
      const destino = porId("linhas-colagem"); destino.replaceChildren();
      const fragmento = document.createDocumentFragment();
      coladas.forEach(linha => {
        const tr = document.createElement("tr");
        [linha.codigo || "Código ausente", linha.data || dataPadrao.value, linha.horario || "Não informado", linha.situacao].forEach(valor => {
          const td = document.createElement("td"); td.textContent = valor; tr.appendChild(td);
        }); fragmento.appendChild(tr);
      });
      destino.appendChild(fragmento);
      const resumo = D.contar(coladas, situacaoPadrao.value);
      porId("resumo-colagem").textContent = `${coladas.length} registros · ${resumo.baixas} baixas · ${resumo.insucessos} insucessos. Confira antes de adicionar à grade.`;
      porId("previa-colagem").hidden = false; avisar("");
    } catch (erro) { coladas = []; porId("previa-colagem").hidden = true; avisar(erro.message); }
  }
  function analisar() {
    try {
      analise = D.analisarColagem(areaColagem.value); porId("colagem-cabecalho").checked = analise.cabecalho;
      const mapeamento = porId("mapeamento-colagem"); mapeamento.replaceChildren();
      analise.mapa.forEach((campo, i) => {
        const label = document.createElement("label"); label.textContent = `Coluna ${i + 1}`;
        const select = document.createElement("select");
        [["", "Ignorar"], ["codigo", "Código"], ["data", "Data"], ["horario", "Horário"], ["situacao", "Situação"]].forEach(([valor, titulo]) => {
          const option = document.createElement("option"); option.value = valor; option.textContent = titulo; select.appendChild(option);
        }); select.value = campo; label.appendChild(select); mapeamento.appendChild(label);
      }); atualizarColagem();
    } catch (erro) { coladas = []; porId("previa-colagem").hidden = true; avisar(erro.message); }
  }
  porId("analisar-colagem").addEventListener("click", analisar);
  [dataPadrao, situacaoPadrao].forEach(campo => campo.addEventListener("change", () => {
    if (analise && !porId("previa-colagem").hidden) atualizarColagem();
  }));
  porId("mapeamento-colagem").addEventListener("change", atualizarColagem);
  porId("colagem-cabecalho").addEventListener("change", () => { if (analise) atualizarColagem(); });
  areaColagem.addEventListener("input", () => { coladas = []; porId("previa-colagem").hidden = true; });
  corpo.addEventListener("paste", evento => {
    if (evento.target.dataset.campo !== "codigo") return;
    const conteudo = evento.clipboardData && evento.clipboardData.getData("text/plain");
    if (!conteudo || !/[\t\r\n]/.test(conteudo)) return;
    evento.preventDefault(); areaColagem.value = conteudo; porId("painel-colagem").open = true;
    analisar(); guardar(); porId("painel-colagem").scrollIntoView({ block: "start" });
  });
  porId("aplicar-colagem").addEventListener("click", () => {
    if (!coladas.length) return;
    const vazias = linhas.filter(linha => D.vazia(Object.fromEntries(D.CAMPOS.map(campo => [campo, linha.campos[campo].value])), situacaoPadrao.value));
    if (linhas.length - vazias.length + coladas.length > limite) { avisar(`O lote ultrapassaria ${limite} linhas. Divida a colagem.`); return; }
    const fragmento = document.createDocumentFragment();
    coladas.forEach((dados, i) => { if (vazias[i]) preencher(vazias[i], dados); else adicionar(dados, fragmento); });
    corpo.appendChild(fragmento); renumerar(); areaColagem.value = ""; coladas = [];
    porId("previa-colagem").hidden = true; porId("painel-colagem").open = false; mudou(); guardar();
  });
  formulario.addEventListener("submit", evento => {
    porId("id_linhas").value = JSON.stringify(dadosLinhas()); guardar(); bloquearEnvio(evento);
  });
  window.addEventListener("beforeunload", evento => {
    if (enviando) return;
    if (D.contar(dadosLinhas(), situacaoPadrao.value).preenchidos || areaColagem.value.trim()) {
      guardar(); evento.preventDefault(); evento.returnValue = "";
    }
  });
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden" && !enviando) guardar();
  });
})();
