# Testes e verificações

## Cards de faturamento mensal/quinzenal — 07/11/2026

Baseline: 303 Django e 41 JavaScript aprovados. Novos 12 Django em
`tests/test_cards_faturamento.py`: meses de 31/30 dias, fevereiro comum/bissexto,
fronteiras 15/16 e meses/anos, soma das quinzenas, preços históricos e repetições,
insucessos, ausência, escopo mensal escolhido pelo proprietário, fuso São Paulo,
ausência de consultas/mutações adicionais, dados anteriores preservados,
reconsulta após gravação, nove cards e exportação restrita ao filtro original.
Três arquivos de testes anteriores tiveram somente as expectativas necessárias
de título/quantidade de cards e mês selecionado atualizadas.

Rodada focada: 67 OK. Suíte final: **315 Django e 41 JavaScript OK**, sem skips.
Check, migrations dry-run e pip check aprovados. HTTP real: 30 respostas e 11
leituras em SQLite novo, Waitress loopback; login/CSRF/lote/exportações/logout
preservados e soma mensal/quinzenas conferida. Servidor e temporário encerrados.
Nove recortes reais em snapshot mode=ro mantiveram todos os campos anteriores,
seis indicadores operacionais, tabelas e filtros iguais. SQL independente confirmou
novembro R$ 620,00 = R$ 620,00 + R$ 0,00 e outubro R$ 3.350,00 = R$ 160,00 + R$ 3.190,00.
CSS coletado e comparado byte a byte; grade existente de três colunas desktop e
duas no celular preservada, removendo somente o span do antigo card único.
Verificação visual física continua pendente; nenhuma captura bloqueada foi repetida.

## Ajuste exclusivo da taxa das tabelas — 31/10/2026

Baseline 287 Django/41 JavaScript aprovados, sem editar testes existentes.
16 novos testes em `tests/test_taxas_tabelas.py`: referências sintéticas 62/64 e
335/345, recuperações em outro dia/semana/mês, corte inclusivo de referência,
tentativas/baixas repetidas, zeros à esquerda, reutilização/ambiguidade, ausência,
interseção de filtro, lote/exclusão e preservação de todos os dados aprovados.
Testes focados: 37 OK. Suíte final: **303 Django e 41 JavaScript OK**, sem skips.
O primeiro ensaio de não mutação comparava ModelState clonado por identidade;
o teste passou a comparar todos os campos concretos, sem alterar código produtivo
para contornar a asserção. Os dois logs foram mantidos.

Seis recortes reais em backup `mode=ro` conservaram o hash de toda a estrutura
anterior do dashboard, sete cards e 434 células que não são taxas. Novas células
confirmadas: dia 22/10 = 96,88%; semana 18–24/10 = 97,10%; mês = 97,20%.
`taxa_tabelas_http.py` validou 30 respostas e 11 leituras em SQLite novo e
Waitress loopback, incluindo outubro com taxa de tabela 100% e card Não informado,
e novembro com tabela Não informado e card 100%, por recuperação em outro mês.
Login/CSRF/lote/exportações/logout preservados. Nenhum ensaio público iniciado.
Check, migrations dry-run e pip check aprovados. Inspeção visual física pendente.

## Reestruturação do painel — 31/10/2026

Baseline: 266 testes Django e 33 JavaScript OK. Final: **287 Django e 41 JavaScript
OK**, sem skips. Os 21 novos Django verificam mês padrão e virada UTC/São Paulo,
histórico explícito, filtros/downloads, menu/colunas/ordem, domingo e limites de
calendário, recuperação posterior, lote/exclusão, taxas e médias, odômetro zero,
horas reais prioritárias, tanque cheio, pares compatíveis, ausência e parcialidade.
Os oito novos JS verificam abertura/fechamento, Escape/foco/saída com Tab,
clique/toque, estrutura CSS responsiva e persistência da consulta canônica.
Expectativas antigas mudaram apenas nos contratos autorizados: calendário, mês
padrão, sétimo card e localização da auditoria. Fixtures históricas solicitam
`periodo=todos` explicitamente, evitando dependência do mês da execução.

Comandos finais: `.venv\Scripts\python.exe manage.py test --noinput` e
`node --test tests/test_graficos.cjs tests/test_mobile.cjs tests/test_lote.cjs tests/test_menu_painel.cjs`.
Check, migrations dry-run, pip check e node --check passaram. Estáticos coletados
e comparados byte a byte. Os testes existentes de login local, WSGI/proxy ngrok,
identidade forjada, cookies seguros e CSRF passaram sem mudar a segurança.

`relatorios/layout_painel_http.py` exercitou 30 respostas HTTP e 11 leituras dos
cards/tabelas em Waitress loopback com SQLite novo. Cobriu login, CSRF inválido/
válido, gravação individual/lote, prévia/reenvio, edição/exclusão, semanas,
exportações e logout. Servidor encerrado e temporário removido. Nenhum túnel
público iniciado; esta etapa não é nova validação interativa do provedor Google.
`relatorios/layout_painel_validar.py` confrontou datas, ocorrências, receita e
domingos com SQL independente sobre backup mode=ro. Inspeção visual física
continua pendente; a restrição anterior de captura não foi contornada.

Execute `python manage.py test --verbosity 2` com o Python do ambiente virtual.

- `test_modelos.py`: duplicados, situações, obrigatoriedade, dinheiro, versões de
  configuração, períodos, odômetros, duração e preservação de nulos.
- `test_importacao.py`: datas/horários numéricos, época 1904, códigos com zeros,
  quatro abas, fórmulas, pagamentos, rollback, reimportação, edições e exclusões.
  Cinco testes leem o Excel real e comparam dados e totais históricos.
- `test_interfaces.py`: autenticação, proteção de GET/POST, CSRF real, login/logout,
  CRUD de entregas, filtros/paginação, formulários, configurações, Admin e erros.

O Excel privado não é versionado. Os cinco testes históricos são explicitamente
ignorados quando o arquivo não estiver disponível. O relatório registra se houve
testes ignorados na execução desta etapa.

Execute também `manage.py check`, `makemigrations --check --dry-run` e `pip check`.
Logs e evidências estão em `relatorios/`, fora do versionamento.

## Etapa 02

Os 45 testes anteriores foram preservados e aprovados. Outros 50 testes Django
foram adicionados em `test_periodos_indicadores.py`, `test_jornadas_calculos.py`,
`test_conferencia_calculos.py`, `test_dashboard_historico.py` e
`test_dashboard_interfaces.py`. Total: 95, sem falhas ou ignorados nesta execução.

Cobrem períodos civis e semanas ISO, fevereiro bissexto, filtros, preço histórico,
metas, projeções, pagamentos parciais e fora do padrão, duplicidades, incompletude,
origem das horas, meia-noite, consumo por conjuntos comparáveis, taxas, ausências,
proibição de lucro definitivo com custos incompletos e regressão autenticada.
Quatro dos novos testes leem o Excel, somando nove testes históricos privados.

`node --test tests/test_graficos.cjs` executa oito testes sem dependência externa:
preservação de nulos/zeros, SVG, rótulos, legendas, vazio, controles de filtro e os
sete gráficos com o payload histórico salvo em `relatorios/`. O último é ignorado
se essa evidência privada não existir em outro checkout. Node é ferramenta de QA,
não requisito de execução da aplicação.

Uma verificação HTTP autenticada em banco descartável exercitou nove caminhos,
incluindo filtros, auditoria e arquivos locais. A captura visual bloqueada na etapa
01 não foi repetida nem contornada. O detalhe e as limitações constam no relatório.

## Etapa 03

Preservados os 95 testes Django e oito JavaScript anteriores. A suíte final Django
possui 127 testes: 14 novos de exportação, nove de backup/recuperação, seis de rede
e três de estáticos/interface. A suíte JavaScript possui 15 testes, incluindo sete
novos de layout, menu, persistência de filtros e armazenamento indisponível.

Executar `node --test tests/test_graficos.cjs tests/test_mobile.cjs` e os comandos
Django já listados. O parser PowerShell também é verificado no Windows, sem executar
alterações de rede. Testes de restauração usam apenas bancos temporários.

`relatorios/etapa03_verificar_http.py` inicia Waitress real com WhiteNoise, conta
aleatória e cópia descartável do banco. Verifica 21 respostas HTTP e quatro
exportações reabertas, sem modificar o acervo real. A aplicação deve executar
`collectstatic` antes do ensaio. Evidências são privadas em `relatorios/`.

Layout em pixels, celular físico, acesso LAN pelo dispositivo e abertura visual no
Excel exigem o roteiro de validação manual; os testes não equivalem a essa aprovação.

## Ajuste da inicialização LAN — 22/10/2026

`tests/test_inicializacao_lan.py` acrescenta 11 testes, totalizando **138 Django**.
Um teste anterior foi atualizado para a seleção automática da interface única.
Cobertura: Ethernet/Wi-Fi física e ativa, perfil Private e IPv4 RFC1918, exclusão
de VPN/virtual/Público, agrupamento por placa, zero/uma/várias interfaces,
escolha inválida, modo local, IP explícito e falhas/timeout na consulta Windows.

Processos Django novos, com inventário de rede simulado e criação de servidor
substituída por mock, conferem os hosts realmente carregados, o endereço escolhido,
uma única criação Waitress e a liberação dos recursos. Outro teste usa Waitress
real em **dois loopbacks**, com uma barreira que exige duas requisições simultâneas
na mesma aplicação/processo; isso não equivale a um teste em celular ou LAN física.

Comandos focados:

```powershell
& '.\.venv\Scripts\python.exe' manage.py test tests.test_backup_rede tests.test_inicializacao_lan --verbosity 2 --noinput
& '.\Iniciar_Entregas.bat' --verificar
```

Resultado: 29 testes focados, 138 Django e 15 JavaScript aprovados, sem ignorados;
check, migrations pendentes de geração e dependências sem problemas. Inicialização
real na porta 8000 e oito respostas HTTP verificadas, incluindo rejeição de hosts
não selecionados. A Ethernet estava Public e o Wi-Fi desconectado: o teste real
confirmou somente loopback. Roteiro e evidências estão em
`relatorios/AJUSTE_INICIALIZACAO_LAN.md`.

## Cadastro em lote — 22/10/2026

Suíte completa: **160 Django** e **32 JavaScript**, sem falhas ou ignorados.
Inclui os 138 Django e 15 JavaScript anteriores, com uma asserção existente de
obrigatoriedade de horário atualizada para o contrato de horário opcional.

`tests/test_lote.py`: 22 testes novos, incluindo lotes de 1/50/100/200, padrões e
exceções de data/situação, horário NULL e meia-noite real, zeros/repetidos, linhas
vazias/incompletas/inválidas, revalidação da prévia, CSRF/autenticação, recibo por
usuário, unicidade persistente, reenvio, conflito de conteúdo, falha após inserir
uma linha com rollback integral e nova tentativa, snapshot de preço, cadastro
individual e integração com indicadores/auditoria/XLSX/CSV. O teste histórico lê
o Excel no banco em memória e compara cada campo das 169 linhas após incluir 100.

`tests/test_lote.cjs`: 17 novos testes sem dependências de produção, cobrindo TSV,
cabeçalhos e mapeamento, 1/50/100/200 códigos, zeros/repetidos, dados inválidos
conservados, Enter/Tab/limite, rascunhos sem credenciais, armazenamento bloqueado,
limpeza correspondente ao lote salvo e bloqueio do duplo envio na confirmação.

`relatorios/lote_verificar_http.py` usa Waitress real e uma cópia temporária do
banco, com conta aleatória apenas nela. Exerceu 23 respostas HTTP, gravou 50 e
100 entregas, repetiu os POSTs sem duplicação e verificou CSRF, painel, auditoria,
downloads e estáticos. Fonte real permaneceu byte a byte igual durante os testes.
Nenhum navegador ou celular físico foi usado; testes de DOM completo, layout,
toque e velocidade percebida permanecem no roteiro manual do guia da grade.

```powershell
& '.\.venv\Scripts\python.exe' manage.py test --verbosity 2 --noinput
node --test tests/test_graficos.cjs tests/test_mobile.cjs tests/test_lote.cjs
```

Detalhes e contagens antes/depois: `relatorios/MELHORIA_CADASTRO_EM_LOTE.md`.

## Acesso ngrok — 22/10/2026

Mantidos os 160 testes Django e 32 JavaScript anteriores. `tests/test_online.py`
acrescenta 31 testes: total **191 Django**, sem falhas ou ignorados. Cobrem domínio/
e-mails exatos, revisão vinculada à configuração, política OAuth com negação,
cabeçalhos/chave/identidade do proxy, cookies/CSRF HTTPS, localhost independente,
login e Admin com limite atômico, acesso autenticado/negado, lote com reenvio,
dashboard, auditoria, exportações e ciclo de vida dos processos. Não abrem túnel.

`relatorios/ngrok_validar_http_local.py` verifica **24 respostas HTTP** em Waitress
real com uma cópia descartável do banco. Emula somente o sinal de um proxy HTTPS
validado: não é um ensaio TLS externo. Confere cadastro individual/lote, cookies,
CSRF, login local, HSTS, arquivos privados e downloads. O `check --deploy` emite
W001 por reconhecer apenas o caminho literal do middleware padrão; a subclasse e
seus headers foram testados, e o aviso não foi silenciado.

`relatorios/ngrok_validar_externo.py` abriu temporariamente o endpoint de **prova
sem Django/SQLite**, com a política real. O serviço aceitou a configuração e seis
requisições HTTPS, inclusive com cabeçalhos forjados, receberam 302 para OAuth.
Certificado TLS verificado, sem seguir login ou registrar cookies/corpos/URLs com
state. A prova foi encerrada. Login Google com conta permitida/negada, dados móveis
e Full Capture no painel aguardam o proprietário; dados reais continuam bloqueados.

Checks locais, migrations e dependências passaram, sem novas dependências/schema.
BAT Online com `--verificar` passou sem abrir túnel. O banco real permaneceu
idêntico em bytes, schema e linhas. Relatório: `MELHORIA_ACESSO_NGROK.md`.

## Correção do login HTTPS — 22/10/2026

`tests/test_login_ngrok.py` acrescenta oito regressões: GET com política adequada
ao navegador, POST válido, Origin null, Referer ausente/externo, token inválido,
cookie ausente, sessão/painel/logout/relogin, acesso local e logs sanitizados.
O teste da configuração online em processo novo também exige `same-origin` e
filtro CSRF seguro. Os 191 testes anteriores continuam: **199 Django aprovados**,
39 focados online/login, **32 JavaScript aprovados**. Checks e dependências passaram.

O QA HTTP acrescenta rejeições de Origin null/token inválido e logout/relogin:
**31 respostas** em Waitress real com cópia descartável, sem túnel, aprovadas.
O aviso de deploy W001 já documentado permanece visível. A regressão de política
falha com no-referrer e passa após a correção; o primeiro ensaio também teve uma
interferência do limitador no teste de múltiplos Referers, corrigida isolando o
limite somente naquele teste, sem alterar o limite de produção.

Para inspecionar cabeçalhos reais do ngrok no navegador, o script
`relatorios/correcao_login_prova.py` cria banco novo vazio e preenche uma conta
sintética no formulário protegido por OAuth. Os eventos JSONL são categorizados,
sem valores de cookies/tokens/senhas/cabeçalhos. Cada fase dura cinco minutos por
padrão; `--duracao 900` permite até quinze minutos para o teste interativo.
Resultados externos efetivamente obtidos e eventuais pendências constam somente
em `relatorios/CORRECAO_LOGIN_NGROK.md`; testes locais não comprovam esse fluxo.

Na rodada interativa, o navegador/ngrok registrou GET 200 e POST 403 com Origin
null antes; após same-origin, registrou POST 302, painel 200 autenticado, logout
e nova autenticação. Chave/identidade/protocolo/Host reais conferiram no wrapper.
O proprietário confirmou a recusa da outra conta antes do formulário Django.

## Horário nativo no lote — 23/10/2026

Executados novamente todos os 199 testes Django e os 32 JavaScript, com sucesso.
`node --check static/js/lote.js` e `manage.py check` passaram. Uma renderização
isolada do template confirmou o campo Horário como `type="time"`, `step="1"`
e opcional. A coleta de estáticos foi concluída e JS/CSS publicados em
`staticfiles` conferem com os arquivos fonte. Não houve ensaio visual em
navegador ou celular nesta alteração.

## Conciliação e Insucesso Real — 29/10/2026

Antes da alteração: 199 testes Django aprovados. `tests/test_conciliacao.py`
acrescenta 33 testes de cronologia, repetições, recuperação após dias/mês/quinzena,
códigos textuais, ausência de horários, possíveis ciclos reutilizados, cortes sem
futuro, taxa final, vazio, filtros, finanças imutáveis, consulta/paginação, acesso,
CSRF e exportações. Rodada completa: **232 Django aprovados** em SQLite de testes;
**32 JavaScript aprovados**. Check Django, migrations em dry-run e pip check OK.

Após o ajuste final de rótulos do XLSX, os **47 testes de conciliação/exportação**
foram repetidos e passaram. A primeira rodada focada teve uma asserção de texto
com redação diferente da interface; corrigida sem alterar a funcionalidade.

`relatorios/insucesso_real_http.py` validou **20 respostas HTTP** em Waitress real,
DEBUG=False, 127.0.0.1 e SQLite novo descartável: login, painel, lote GET,
auditoria, conciliação, consultas, XLSX/CSV, método, CSRF, logout e acesso anônimo.
Servidor encerrado, banco temporário removido, nenhum túnel público iniciado.

Todos os 619 registros foram analisados em backup somente leitura. Conferência
independente aprovou os resultados em histórico, dia, semana, mês, duas quinzenas
e intervalo; XLSX real reaberto e conferido. Tabela completa em
`relatorios/CONCILIACAO_ENTREGAS.csv`. Evidências nos arquivos `insucesso_real_*`.
Validação visual no computador/celular e abertura manual no Excel permanecem
pendentes; não foram substituídas pelos testes HTTP ou pela análise do HTML.

## Dashboard por situação real — 30/10/2026

Suite anterior: **232 Django OK** antes das mudanças. Novos 17 testes em
`tests/test_dashboard_situacao_real.py` exercitam os seis cards, cadastro individual
e em lote com prévia/reenvio, edições de situação/código/data, exclusão da baixa
e do insucesso, reconsulta sem cache, cruzamento de período/quinzena/mês, preços,
duplicidade, revisão, gráfico sem sobreposição e as duas relações dos totais.
Rodada focada: **58 OK**. Suite completa: **249 Django OK** em banco de testes.

Os 32 testes JavaScript anteriores e um novo teste de três séries/cores/legendas
passaram: **33 JS OK**. O cálculo responsivo foi conferido com duas e três séries
nas larguras já cobertas. O teste anterior do primeiro gráfico foi adequado à
nova população por encomenda; as demais séries financeiras são preservadas.
Check Django, makemigrations dry-run, sintaxe JS e pip check passaram.

`relatorios/dashboard_real_http.py`: **27 respostas HTTP e oito leituras atualizadas**
em Waitress/SQLite novo, DEBUG=False, somente loopback. Cadastro, edição de data,
revisão, exclusão, lote/reenvio, CSRF e logout verificados. Temporário removido e
servidor encerrado. CSS/JS coletados e conferidos com as fontes.

Leitura real em backup mode=ro confirmou os seis cards, as duas relações, todos
os filtros e igualdade de todas as séries/resumos financeiros antes/depois.
O backup anterior de 619 registros ainda produz R$2.810; o atual, que já iniciou
com 618 registros, produz R$2.805. Nenhuma alteração monetária automática.
Cabeçalhos de User-Agent, HTML e cálculo de largura foram testados; inspeção
visual em navegador/celular físico continua pendente.

A conferência final de integridade detectou 48 edições concorrentes de data
(29/10 para 28/10) e atualizado_em, IDs 572–619, no banco real. O SHA-256 global
mudou; preços, códigos, situações, contagens, demais tabelas e schema permaneceram
iguais. Essas edições foram conservadas e registradas em comparação de leitura;
foi obtido um segundo backup consistente para o retrato final. Após o relatório
inicial, o proprietário confirmou que estava ajustando essas datas em outra
janela; a pendência de procedência foi encerrada. Não se declara identidade
binária do banco ao fim.

## Definições definitivas dos indicadores — 31/10/2026

Os **249 Django anteriores** passaram antes das mudanças. Novos **17 testes** em
`tests/test_indicadores_definitivos.py` cobrem o cenário 619/562/57/18/33, taxa de
96,90%, baixas repetidas, vários insucessos por encomenda, cadastro individual,
edição/exclusão de baixa, edição da prévia/lote e reenvio, todos os filtros,
recuperações em outra quinzena/mês, zeros à esquerda, ambiguidades e vazio.
Suite final: **266 Django OK**; rodada focada corrigida: **81 OK**;
**33 JavaScript existentes OK**. Check, migrations dry-run e pip check passaram.

A primeira rodada focada encontrou apresentação 96,89% para a fração 562/580,
pois o formatador genérico limita casas sem arredondar. Corrigido apenas o novo
card com arredondamento Decimal ROUND_HALF_UP; o cálculo mantém precisão integral
e o formatador financeiro global permanece igual. Nova linha XLSX usa formato
0.00, mantendo valor preciso e distinguindo o percentual por encomenda da auditoria.
Os testes anteriores de títulos foram adaptados ao novo contrato, preservando
suas verificações de conciliação, finanças e segurança.

`relatorios/indicadores_definitivos_http.py`: **28 respostas HTTP e nove leituras**
em SQLite novo e Waitress loopback, DEBUG=False, com login, CSRF, filtros, revisão,
cadastro/edição/exclusão, prévia editável, lote/reenvio, XLSX/CSV e logout. Banco
temporário removido e servidor encerrado; nenhum túnel iniciado.

Backup real atual e backup anterior de 619 registros foram abertos somente para
leitura, renderizando os seis cards sem gravar HTML/tokens: o atual produz
618/561/57/18/33 e 96,89%; o anterior produz 619/562/57/18/33 e 96,90%.
No recorte 22/10: 65/43/22/2/19 e 95,56%. Valores e gráficos anteriores foram
conferidos com a mesma entrada e continuam iguais. Inspeção visual física pendente.
