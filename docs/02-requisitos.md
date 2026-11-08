# Requisitos da etapa 01

## Cards de faturamento — 07/11/2026

Card Faturamento renomeado para Faturamento Mensal e acrescido de duas quinzenas:
1–15 e 16–último dia civil. Mesmo estilo e grade responsiva, sem alterar preços
históricos, dados ou regras financeiras. O proprietário escolheu mês completo
do filtro quando nele houver um único mês; histórico/múltiplos meses usam o mês
vigente em São Paulo. Demais indicadores, filtros, tabelas/exportações, cadastro,
conciliação e autenticação permanecem iguais. Detalhes em PAINEL_GERAL.md.

## Reestruturação do Painel Geral — 31/10/2026

Implementados os sete cards, mês vigente em America/Sao_Paulo, filtro/menu
acessível, exportações do período ou histórico explícito, tabelas 9/12/12 colunas
e semanas domingo–sábado. Ajuste pontual posterior: B/(B+P) preservada no card;
somente a taxa das tabelas usa concluídas distintas / população distinta iniciada
no período, conforme a conciliação existente. Demais colunas por data efetiva,
com histórico completo para recuperações. Sem estimativas
de jornada/consumo e sem mudança de preços, schema, segurança ou dados reais.
Blocos Finanças do período e Horas e produtividade removidos do painel; gráficos
existentes mantidos após as tabelas. [Contrato detalhado](PAINEL_GERAL.md).

Implementados: modelos e validações; importação atômica e idempotente das quatro
abas; rastreabilidade; duplicados preservados; login/logout; CRUD de entregas com
confirmação; filtros por data e situação; formulários de espelho, pagamentos e
jornadas; parâmetros versionados; Admin; resumo inicial e erros 403/404/500.

Valores monetários usam DecimalField. Ausência é distinta de zero. Datas são
DateField; horários reais são TimeField; janelas são DurationField. Locale pt-br,
fuso America/Sao_Paulo. CSRF permanece ativo e nenhuma senha inicial foi criada.

Ressalva: foi usada cópia do Excel localizado sem sufixo `(3)`, com dados que
conferem integralmente com as referências pedidas. O arquivo exato com esse sufixo
não estava disponível para comparação independente.

## Etapa 02

Implementados: produtividade por dia/semana/mês, sucesso, intervalos cronológicos,
horas com origem, taxas por hora, melhor dia, metas, projeção condicional, sete
gráficos locais e auditoria por competência e quinzena. Filtros de período são
compartilhados entre painel e conferência. Jornadas, consumo e custos preservam
ausências e identificam resultados parciais.

Os 169 registros foram conservados sem nova importação. Backup seguro do SQLite
foi feito antes das alterações. Não houve mudança de schema ou de configuração
de rede. A inspeção visual continua pendente; testes Django, Node e HTTP foram
executados sem contornar o bloqueio anterior de navegador.

## Etapa 03

Implementados ajustes de interface a partir de 360 px, menu com foco e estado
acessíveis, rolagem contida de tabelas, SVG adaptável e memória de filtros na aba.
Waitress e WhiteNoise substituem o servidor de desenvolvimento no uso diário.
O inicializador valida Python/.venv, banco, migrations, porta e estáticos; só
oferece interfaces físicas RFC1918 no perfil Privado, excluindo VPN/virtuais.

Exportações autenticadas possuem cinco abas XLSX ou cinco colunas CSV, proteção de
fórmulas, filtros e totais. Backup usa API SQLite com verificação e manifesto.
Restauração exige servidor encerrado, ensaio isolado, backup atual e confirmação.
Não houve alteração de schema, reimportação ou restauração no banco real.

## Cadastro em lote — 22/10/2026

Grade de até 500 linhas com padrões de data/situação, exceções por linha, Enter,
colagem TSV com prévia/mapeamento, contadores e rascunho local. POST autenticado e
CSRF valida o lote inteiro, exige prévia confirmada e grava em transação única.
Recibo por usuário/chave impede duplicação por reenvio sem restringir códigos.
Horário passa a admitir NULL, necessário para listas sem horário; não há horário
inventado. O formulário individual, consultas e regras financeiras são mantidos.

## Acesso remoto opt-in — 22/10/2026

Inicializador Online separado, Waitress somente em loopback, domínio ngrok e
e-mails explícitos, OAuth anterior ao login Django, hosts/origem exatos, cookies
HTTPS e controle de tentativas. Prova externa não carrega Django/SQLite; os dados
reais só podem ser ativados após testes interativos e revisão registrada. Sem
mudança de rede, firewall, schema, regras financeiras ou publicação do código.

## Conciliação de entregas — 29/10/2026

Resultados distintos por primeira tentativa no período, com consulta ao histórico
posterior e fotografia até o fim do filtro. Insucesso Total preserva ocorrências;
Insucesso Real exige ausência de baixa posterior válida; taxa final usa resultados
distintos. Consulta por código/situação, paginação e CSV de auditoria. Códigos com
possível reutilização ou cronologia indeterminada ficam separados para revisão.
Nenhuma escrita no banco real, mudança financeira, autenticação ou configuração ngrok.

## Dashboard por situação real — 30/10/2026

Seis cards principais: total de encomendas, concluídas, total com insucesso,
pendentes, recuperadas e sucesso final. A próxima consulta reflete operações
individuais/em lote, edições e exclusões sem comando manual; respostas sem cache.
Auditoria preserva ocorrências/repetições e os indicadores financeiros continuam
visíveis. Gráfico de situação usa grupos exclusivos da mesma população dos cards.

## Definições definitivas dos indicadores — 31/10/2026

Substituídas as definições dos seis cards: total de registros, registros de baixa,
registros de insucesso, pendências distintas, recuperadas distintas e Taxa de
Sucesso = baixas registradas / (baixas registradas + pendências distintas) × 100.
Os três primeiros usam datas efetivas; conciliação usa população pela primeira
tentativa e histórico posterior. Descrições distinguem essas bases. Repetições
não são removidas dos totais ou das finanças. Rótulos anteriores por encomenda
única permanecem na auditoria; o gráfico de conciliação mantém sua base própria.
