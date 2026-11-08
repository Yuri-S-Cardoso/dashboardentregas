"use strict";

// Decimal permanece no servidor; Number serve somente para coordenadas do SVG.
function prepararGrafico(dados) {
  const series = dados.series.map((serie) => ({
    nome: serie.nome,
    valores: serie.valores.map((valor) => {
      if (valor === null || valor === undefined || valor === "") return null;
      const numero = Number(valor);
      return Number.isFinite(numero) && numero >= 0 ? numero : null;
    }),
  }));
  return { ...dados, series, possuiDados: series.some((serie) => serie.valores.some((valor) => valor !== null)) };
}

function layoutGrafico(largura, quantidadeSeries) {
  const larguraSvg = Math.max(280, Math.min(760, largura || 760));
  const compacto = larguraSvg < 520;
  return { largura: larguraSvg, compacto, esquerda: compacto ? 0 : 230, alturaLinha: (compacto ? 40 : 30) + quantidadeSeries * 27 };
}

function montarGraficos(documento) {
  const elemento = documento.getElementById("dados-graficos");
  if (!elemento) return;
  const cores = ["#21627b", "#b96928", "#2b7351"];
  const numero = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
  const reais = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
  function no(tag, texto, classe) {
    const item = documento.createElement(tag);
    if (texto !== undefined) item.textContent = texto;
    if (classe) item.className = classe;
    return item;
  }
  function svgNo(tag, atributos, texto) {
    const item = documento.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.entries(atributos).forEach(([chave, valor]) => item.setAttribute(chave, String(valor)));
    if (texto !== undefined) item.textContent = texto;
    return item;
  }
  JSON.parse(elemento.textContent).forEach((origem) => {
    const dados = prepararGrafico(origem);
    const recipiente = documento.querySelector(`[data-grafico="${dados.id}"]`);
    if (!recipiente) return;
    recipiente.replaceChildren();
    const formatar = (valor) => valor === null ? "Não informado" : (dados.unidade === "reais" ? reais : numero).format(valor);
    const legenda = no("div", undefined, "legenda-grafico");
    const desenho = no("div");
    const ativas = new Set(dados.series.map((_, i) => i));
    function desenhar() {
      desenho.replaceChildren();
      const visiveis = dados.series.map((serie, i) => ({ ...serie, indice: i })).filter((s) => ativas.has(s.indice));
      if (!visiveis.length) { desenho.append(no("p", "Selecione uma série na legenda.")); return; }
      if (!dados.possuiDados || !visiveis.some((s) => s.valores.some((v) => v !== null))) {
        desenho.append(no("p", "Sem valores informados neste recorte.", "ajuda")); return;
      }
      const layout = layoutGrafico(recipiente.clientWidth, visiveis.length);
      const alturaLinha = layout.alturaLinha;
      const altura = Math.max(90, dados.rotulos.length * alturaLinha + 20);
      const svg = svgNo("svg", { viewBox: `0 0 ${layout.largura} ${altura}`, role: "img", "aria-label": dados.titulo, class: "grafico-svg" });
      const maximo = Math.max(1, ...visiveis.flatMap((s) => s.valores.filter((v) => v !== null)));
      const reservaValor = Math.max(105, ...visiveis.flatMap((s) => s.valores.filter((v) => v !== null).map((v) => formatar(v).length * 8)));
      const larguraMaxima = Math.max(30, layout.largura - layout.esquerda - reservaValor - 10);
      dados.rotulos.forEach((rotulo, i) => {
        const topo = i * alturaLinha + 20;
        svg.append(svgNo("text", { x: 0, y: topo + 15, class: "grafico-rotulo" }, rotulo));
        visiveis.forEach((serie, j) => {
          const valor = serie.valores[i];
          const y = topo + (layout.compacto ? 25 : 0) + j * 27;
          if (valor === null || valor === undefined) {
            svg.append(svgNo("text", { x: layout.esquerda, y: y + 15, class: "grafico-ausente" }, "Não informado"));
            return;
          }
          const largura = valor / maximo * larguraMaxima;
          const barra = svgNo("rect", { x: layout.esquerda, y, width: largura, height: 17, rx: 3, fill: cores[serie.indice % cores.length] });
          barra.append(svgNo("title", {}, `${rotulo} · ${serie.nome}: ${formatar(valor)}`));
          svg.append(barra, svgNo("text", { x: layout.esquerda + 8 + largura, y: y + 14, class: "grafico-valor" }, formatar(valor)));
        });
      });
      desenho.append(svg);
    }
    dados.series.forEach((serie, i) => {
      const botao = no("button", serie.nome, "serie-grafico secundario");
      botao.type = "button";
      botao.style.borderLeft = `5px solid ${cores[i % cores.length]}`;
      botao.setAttribute("aria-pressed", "true");
      botao.addEventListener("click", () => {
        if (ativas.has(i)) ativas.delete(i); else ativas.add(i);
        botao.setAttribute("aria-pressed", String(ativas.has(i)));
        desenhar();
      });
      legenda.append(botao);
    });
    recipiente.append(legenda, desenho);
    desenhar();
    if (typeof ResizeObserver !== "undefined") new ResizeObserver(desenhar).observe(recipiente);
  });
}

if (typeof module !== "undefined" && module.exports) module.exports = { prepararGrafico, montarGraficos, layoutGrafico };
if (typeof document !== "undefined") montarGraficos(document);
