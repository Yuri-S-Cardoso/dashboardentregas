# Painel Geral — apresentação vigente em 07/11/2026

Sem filtro explícito, o painel abre no mês vigente de **America/Sao_Paulo**.
Não utiliza o histórico completo como padrão. **Menu do Painel** contém Filtrar
período, Exportar relatórios e Conferência Financeira. O menu abre sobre a página,
com rolagem própria, aceita teclado/toque e fecha por Escape, botão, clique fora
ou saída do foco. Sem JavaScript, a abertura nativa por resumo continua disponível.
Os filtros inválidos são mostrados no menu aberto; não liberam o histórico inteiro.

Os nove cards são total de registros, ocorrências de baixa, ocorrências de
insucesso, pendências distintas, recuperações distintas, Taxa de Sucesso,
Faturamento Mensal, Faturamento 1ª Quinzena e Faturamento 2ª Quinzena.
Faturamento continua sendo **receita prevista**, não pagamento.
O painel recalcula os dados em cada consulta; uma aba já aberta precisa ser
recarregada após gravação em outra janela.

## Cards de faturamento — 07/11/2026

Conforme a escolha explícita do proprietário, os três cards mostram **o mês
completo do filtro quando início/fim pertencem a um único mês**. Isso vale também
para filtro diário, semanal ou quinzenal contido nesse mês. Histórico ou intervalo
que atravesse meses utiliza o mês vigente de America/Sao_Paulo. A referência
MM/AAAA e as datas das quinzenas aparecem nos cards.

Mensal soma a receita prevista das baixas nas datas efetivas do mês. A primeira
quinzena vai de 1 a 15; a segunda, de 16 ao último dia civil, incluindo fevereiro
bissexto. Mensal = primeira + segunda. Repetições e preços históricos seguem o
totalizador existente. Os seis indicadores operacionais e as tabelas/exportações
continuam usando o filtro original; só os três cards têm esta referência mensal.
No desktop, os três ficam na mesma linha. No celular, a grade permite quebra.

## Calendário, navegação e exportação

- Diário: escolha a data. Mensal/quinzenal: mês e ano. Personalizado: início/fim.
- Semanal: escolha **uma data da semana**, no controle de data. A semana começa
  domingo e termina sábado. 29/10/2026 pertence a 25/10–31/10/2026; 01/11 inicia
  01/11–07/11. Meses e anos podem ser atravessados sem duplicar registros.
- A consulta canônica semanal guarda o domingo em `semana=AAAA-MM-DD`. Links
  antigos `semana=AAAA-Wss` ficam inválidos: abra o menu e selecione uma data.
  Não há conversão silenciosa de semana ISO para outro intervalo.
- `?periodo=todos` é a opção explícita **Todo o histórico**. Sem `periodo`, usa-se
  o mês vigente, também na conferência, consulta e downloads.
- Links preservam o filtro válido. Durante a navegação na mesma aba, o menu
  principal lembra somente parâmetros de calendário permitidos em sessionStorage.
  Links entre painel e conferência também preservam o período sem armazenamento.
- Excel/CSV do período usam o filtro atual; Excel/CSV completo adicionam
  `periodo=todos`. Os downloads continuam privados e exigem login.

## Fórmula operacional do card principal

**Taxa de Sucesso do card = B / (B + P) × 100**, preservada integralmente.

`B` conta todas as ocorrências de baixa na data efetiva, incluindo repetições.
`P` conta ciclos válidos distintos iniciados no período e ainda sem baixa
posterior válida até a referência conhecida. A conciliação consulta o histórico
completo **antes** de distribuir os resultados pelos períodos. Cada pendência
pertence uma única vez à data da primeira tentativa. Casos ambíguos seguem para
revisão; uma baixa anterior não resolve um insucesso posterior.

Esta é uma base mista de ocorrências e pendências distintas, não um percentual
de encomendas únicas. Denominador zero resulta em **Não informado**. Percentual
mantém Decimal e arredonda a apresentação a duas casas com ROUND_HALF_UP.

## Taxa exclusiva das tabelas — ajuste pontual de 31/10/2026

Nas tabelas dia/semana/mês, **Taxa de Sucesso = encomendas distintas concluídas /
encomendas distintas identificadas cuja primeira tentativa ocorreu no período × 100**.
O denominador é concluídas + pendentes da mesma população, conforme a conciliação
existente. Recuperações posteriores até a referência contam como conclusão no
período inicial. Múltiplas tentativas ou baixas do mesmo ciclo não multiplicam
a população; ambiguidades seguem fora do cálculo, sem alterar suas regras.

`painel.taxas_tabelas.calcular_taxa_sucesso_tabela(inicio, fim, referencia)`
consulta o serviço de conciliação com todo o histórico. O dashboard fornece a
lista que já leu na transação, sem consulta adicional por linha. Sem população
válida, mostra Não informado; exibição arredonda duas casas com ROUND_HALF_UP.
Recortes semanais/mensais continuam respeitando a interseção do filtro aplicado.
Não se calcula média das taxas diárias para obter a taxa semanal/mensal.

Somente a taxa usa essa população. Quantidades, baixas, insucessos e faturamento
continuam nas datas efetivas, e as outras colunas ficam iguais. O card principal
conserva a fórmula operacional mista acima. O ajuste não muda filtros, menu,
calendário, jornadas, gráficos, exportações ou autenticação.

Exemplos: I na segunda e B na terça conserva o I na segunda, resolve a pendência
e atribui a receita à terça. I segunda, I terça e B quarta gera dois insucessos
históricos e uma recuperação. A mesma regra vale se a baixa acontecer em outra
semana ou mês; nenhum registro ou preço é regravado pela conciliação.

## Tabelas e medidas

Ordem: cards → Entregas por dia → Semanas → Meses → sete gráficos existentes →
critérios/alertas e acessos operacionais. Não há os antigos blocos Finanças do
período, Horas e produtividade ou tabelas de metas. Os gráficos existentes de
metas e produtividade são preservados como gráficos, após as novas tabelas.
Ganho médio por baixa e a auditoria detalhada ficam na Conferência Financeira;
as jornadas continuam na área Jornada e Custos. Os serviços antigos permanecem.

Tabela diária tem nove colunas; semanal/mensal têm doze, na ordem da especificação.
A média de receita divide o faturamento por **dias distintos com algum registro
de entrega**, inclusive dias apenas com insucessos. Dia somente com jornada não
entra no divisor; não se presume trabalho nos dias sem registros. O novo valor
monetário médio é arredondado a centavos só na apresentação; a razão exata e os
totais históricos são preservados.

Horas são decimais. Real tem prioridade sobre janela histórica da mesma jornada.
Odômetro inicial zero é válido. Distância = final − inicial. Pelo método tanque
cheio a tanque cheio, litros repostos no mesmo nível representam o consumo.
Combustível é o **total efetivamente pago**; não se multiplica por preço presumido.
KM/L agregado = soma das distâncias / soma dos litros **das mesmas jornadas** com
ambos conhecidos e litros positivos; não é média simples dos índices diários.
Zero litro não permite dividir; quilômetros sem litros ou litros sem quilômetros
não entram na razão. Medidas ausentes mostram Não informado; conhecidas com
cobertura incompleta mostram Parcial. Recortes de semanas/meses são sinalizados.

Tabela longa tem foco e rolagem lateral dentro do componente. O teste visual em
telas físicas deve seguir [VALIDACAO_MANUAL.md](VALIDACAO_MANUAL.md). Evidências,
backup e resultados ficam no relatório local `relatorios/AJUSTE_LAYOUT_PAINEL_GERAL.md`,
fora do Git por conter evidências da instalação.
