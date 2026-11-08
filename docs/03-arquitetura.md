# Arquitetura

Em 07/11/2026, `painel/faturamento.py` passa a compor exclusivamente os três
cards financeiros, no namespace `faturamento_quinzenal`. Recebe o histórico já
carregado e o filtro e reutiliza `totalizar_entregas` e `periodo_mes`. O mês é
resolvido pela escolha do proprietário: mês completo de recorte único ou vigente
se houver histórico/múltiplos meses. Nenhum campo aprovado de indicadores/tabelas
é regravado ou substituído; exportações continuam usando os campos anteriores.

Ajuste pontual posterior de 31/10/2026: `painel/taxas_tabelas.py` chama a
conciliação existente para calcular apenas a taxa exibida nas três tabelas.
O resultado fica em `taxa_sucesso_tabela`, sem mutar `indicadores_principais`
ou os campos anteriores das linhas. Recebe o histórico já carregado e a referência
da mesma transação. Templates trocam apenas a fonte da célula e a explicação da
metodologia; o serviço central, cards, gráficos e exportações continuam iguais.

## Composição do painel — 31/10/2026

`FiltroPainelForm` resolve o mês local padrão, data da semana civil e query
canônica restrita. Views de leitura e exportação compartilham esse contrato.
`core.periodos.periodo_semana` centraliza domingo–sábado, também usado nos gráficos.
`montar_dashboard` mantém a conciliação global e distribui pendências/recuperações
por primeira tentativa com Counter, sem repetir a conciliação por linha nem
mutar o histórico. `indicadores_principais` fornece a mesma razão B/(B+P) em cada
agrupamento; média de receita usa dias com registros. `consolidar_jornadas` só
ganha indicadores de cobertura para litros, combustível e consumo; fórmulas
financeiras e seleção de pares comparáveis continuam iguais.
Menu nativo details com CSS fixo e JS local é não modal e aceita saída de foco.
Templates compartilham células de taxa/medida e as tabelas semanal/mensal.
Não houve alteração de settings, proxy WSGI, autenticação, banco ou inicializadores.

Correção do perfil online em 22/10/2026: `Referrer-Policy: same-origin` mantém
formulários HTTPS compatíveis com CSRF. `core.online_diagnostico` filtra o logger
CSRF em categorias sem cabeçalhos/corpos/segredos; não altera sua decisão. Revisão
de segurança 2 invalida identificadores anteriores. A prova de login em
`relatorios/correcao_login_prova.py` usa banco novo temporário e a autenticação
Django, separada da prova textual do inicializador. Detalhes no relatório de correção.

URLs em `config/` encaminham requisições às views de cada aplicativo. Views
protegidas usam formulários Django para validação e modelos para persistência.
Templates compartilhados evitam duplicar layout, formulários e paginação.

`core` oferece rastreabilidade e views comuns. `entregas/services/conversoes.py`
converte tipos do Excel. `importacao.py` valida o layout, lê entradas e executa uma
transação única; não grava no workbook. `painel/services.py` calcula apenas os
quatro indicadores básicos pedidos. SQLite atende um uso local de poucos operadores.

Na etapa 02, `painel/dashboard.py` compõe uma fotografia transacional somente de
leitura dos serviços `entregas/services/indicadores.py`, `jornadas/services.py`,
`conferencia/services.py` e `painel/metas.py`. Views do painel e auditoria usam a
mesma composição. `core/calculos.py` centraliza Decimal e ausência;
`core/periodos.py` centraliza períodos inclusivos. O resumo da etapa 01 continua
disponível em `painel/services.py` para compatibilidade.

`painel/graficos.py` fornece séries para `json_script`, dentro da página
autenticada. JavaScript local gera SVG e alterna séries. Não existe endpoint JSON
público nem biblioteca externa. As tabelas de valores são renderizadas no servidor.

O uso diário utiliza Waitress nos endereços selecionados pelo inicializador.
O fuso do host não determina a apresentação de datas.

## Operação diária

`Iniciar_Entregas.bat` chama `scripts/iniciar_sistema.py` com o Python da `.venv`.
`config/rede.py` valida hosts, interfaces e porta. O inicializador coleta estáticos
quando necessário e inicia uma instância Waitress em `127.0.0.1` e no IPv4 privado
selecionado, com um pool compartilhado de workers. A consulta Windows somente lê
adaptadores físicos Ethernet/Wi-Fi ativos, IPv4 Preferred e perfil Private.
`config/rede.py` reaplica os critérios, exclui VPN/virtuais e escolhe um IPv4 por
índice de interface, preferindo o endereço sem SkipAsSource. Uma interface é
selecionada automaticamente; várias exigem escolha; nenhuma ou falha na consulta
mantém somente loopback e mostra a razão. `ALLOWED_HOSTS` recebe somente localhost,
127.0.0.1 e o IPv4 escolhido, sem manter outros hosts do ambiente.
WhiteNoise fica após SecurityMiddleware e serve apenas STATIC_ROOT.
CompressedStaticFilesStorage mantém URLs anteriores, compressão e atualização sem
cache duradouro, evitando incompatibilidade com a interface existente.

`painel/exportacao.py` lê os modelos e reutiliza os indicadores aprovados. Exporta
somente dados de negócio, sem credenciais ou snapshots. `core/backups.py` coordena
backup/validação pela API SQLite; comandos ficam em `core/management/commands/`.
`core/locks.py` coordena o inicializador e a restauração, com trava entre processos.

A camada responsiva é `static/css/responsivo.css`; `navegacao.js` controla menu e
memória de filtros permitidos. Não há CDN ou framework de interface.

## Cadastro em lote

`entregas/lote_views.py` coordena edição, prévia e confirmação; `lote_forms.py`
valida transporte JSON e cada linha, mantendo números e dados inválidos. Uma prévia
assinada vincula usuário, chave e conteúdo normalizado; a confirmação revalida tudo.
`entregas/services/lote.py` cria recibo `LoteEntrega` e entregas na mesma transação.
Usa `valor_baixa_atual`, valida os modelos e grava com bulk_create. Nenhum indicador
ou regra financeira alternativo foi criado.

`static/js/lote_dados.js` concentra TSV, contadores, navegação Enter e rascunhos
com uma lista explícita de campos; `lote.js` controla a grade e a prévia da colagem.
Os campos da grade não são enviados individualmente: um campo JSON evita o limite
de quantidade de campos POST com 200 ou mais registros, sem mudar settings.
O CSS da tela reorganiza as linhas no celular e mantém a barra de salvar acessível.

## Perfil online

`scripts/iniciar_online.py` valida o ambiente/configuração e supervisiona somente
seu agente ngrok e seu Waitress. `scripts/ngrok_processos.py` inspeciona o agente,
fixa flags e filtra eventos em memória, sem log bruto. A política é gerada por
`config/acesso_online.py`: OAuth Google, negação de e-mails fora da lista e
remoção/inserção de cabeçalhos controlados. Nenhum domínio é aprendido do tráfego.

`config/proxy_online.py` envolve toda a aplicação WSGI, inclusive estáticos: exige
loopback, host exato, chave temporária e e-mail da lista para o acesso remoto. Só
depois produz o sinal HTTPS confiado pelo perfil separado `settings_online`.
`core/online_middleware.py` aplica cookies, headers e limite de login; preserva HTTP
local através de uma marca WSGI que o cliente não controla. O perfil local original
e seu inicializador permanecem byte a byte iguais.

O modo `--testar-protecao` atende apenas texto fixo, sem Django ou SQLite, com a
mesma política. Aprovação manual é vinculada ao domínio/lista/política/versão. A
queda do ngrok deixa o Waitress local ativo. Ctrl+C fecha o túnel antes do servidor
e remove os arquivos temporários da credencial do proxy no perfil do usuário.

## Conciliação derivada — 29/10/2026

`entregas/services/conciliacao.py` é um serviço sem consultas/gravações próprias:
recebe registros, filtro de população e corte opcional de referência. Produz
`CicloConciliado` imutável, totais e alertas; não altera o serviço operacional.
`painel/dashboard.py` lê o histórico na mesma transação e separa ocorrências por
data dos resultados por primeira tentativa. O corte histórico é calculado sem
consultar o futuro. `Conciliacao` oferece consulta autenticada/paginada; a
exportação CSV própria reutiliza a mesma conciliação e neutralização de fórmulas.
O XLSX existente mantém suas cinco abas. Regras em `CONCILIACAO_ENTREGAS.md`.

Em 30/10/2026, `Inicio.dispatch` recebe never_cache, herdado por Auditoria e
Conciliacao. A composição já lê dados novos em cada GET; não foi criado cache,
signal ou atualização persistida. `encomendas_resumo.html` apresenta os seis
resultados; `auditoria_operacional.html` recolhe as ocorrências. Gráfico de situação
agrupa ciclos válidos por primeira tentativa em três categorias exclusivas,
reutilizando a conciliação sem alterar suas verificações ou totalizadores financeiros.

`painel.dashboard.indicadores_principais()` (31/10/2026) compõe um namespace próprio
para os seis cards usando o resumo operacional e a conciliação, sem mutá-los.
Mantém taxa mista Decimal e uma versão arredondada para apresentação; o formatador
financeiro global permanece igual. O XLSX inclui essa taxa e identifica o percentual
por encomenda da auditoria separadamente. Nenhum modelo, sinal ou cache novo.
