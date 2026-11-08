# Rotas HTTP

Desde 31/10/2026, as páginas analíticas e downloads sem `periodo` selecionam o
mês vigente em America/Sao_Paulo. Histórico completo exige `periodo=todos`.
Filtro semanal usa `periodo=semana&semana=2026-10-29`, resolvido como
25/10/2026 a 31/10/2026; links canônicos guardam o domingo 2026-10-25.
AAAA-Wss não é mais aceito: selecione uma data. Rotas e exigência de login
permanecem iguais; nenhum endpoint público foi criado.

No perfil online, os formulários recebem `Referrer-Policy: same-origin`; POSTs
com `Origin: null`, token inválido ou referência externa permanecem rejeitados.
As rejeições CSRF produzem diagnóstico sanitizado no console, preservando a resposta
pública genérica. Nenhuma rota, view de autenticação ou exigência OAuth foi removida.

Não existe API pública ou JSON nesta etapa. Todas as rotas de dados exigem login.

| Caminho | Operação |
| --- | --- |
| `/` | Resumo de entregas |
| `/auditoria/` | Conferência por competência e quinzena, GET autenticado |
| `/conciliacao/` | Resultados por código/ciclo, filtros e paginação, GET autenticado |
| `/conciliacao/csv/` | Tabela derivada de toda a consulta, download CSV privado, GET autenticado |
| `/exportar/excel/` | XLSX com cinco abas, GET autenticado e filtros globais |
| `/exportar/csv/` | Entregas em UTF-8 BOM e ponto e vírgula, GET autenticado |
| `/contas/entrar/` | Login GET/POST |
| `/contas/sair/` | Logout POST |
| `/entregas/` | Lista GET, filtros `data` e `situacao` |
| `/entregas/nova/` | Cadastro GET/POST |
| `/entregas/<id>/editar/` | Edição GET/POST |
| `/entregas/<id>/excluir/` | Confirmação GET, exclusão POST |
| `/espelho/` | Lista de espelhos |
| `/espelho/novo/` e `/espelho/<id>/editar/` | Formulários GET/POST |
| `/espelho/pagamentos/` | Lista de pagamentos |
| `/espelho/pagamentos/novo/` e `/espelho/pagamentos/<id>/editar/` | Formulários GET/POST |
| `/jornadas/` | Lista de jornadas |
| `/jornadas/nova/` e `/jornadas/<id>/editar/` | Formulários GET/POST |
| `/configuracoes/` | Parâmetros GET, nova versão POST |
| `/admin/` | Administração Django com permissões |

GET nunca cria, altera ou exclui registros operacionais. Formulários POST exigem CSRF.

## Filtros de indicadores e auditoria

`/` e `/auditoria/` aceitam os mesmos parâmetros GET:

| `periodo` | Parâmetros necessários |
| --- | --- |
| `todos` ou ausente | Nenhum |
| `intervalo` | `inicio` e `fim`, AAAA-MM-DD |
| `dia` | `dia`, AAAA-MM-DD |
| `semana` | `semana`, AAAA-MM-DD: uma data da semana de domingo a sábado |
| `mes` | `mes` (1–12) e `ano` |
| `quinzena` | `mes`, `ano` e `quinzena` (1 ou 2) |

`dias_projecao` (1–366, padrão cinco) define apenas o cenário, sem filtrar dados.
Filtros inválidos exibem erros, sem retorno silencioso ao histórico completo.
O JSON das sete séries está embutido apenas na página autenticada pelo mecanismo
`json_script`, que escapa conteúdo para o contexto de script.

Exportações usam os mesmos filtros, retornam 400 quando inválidos e nunca
substituem esse erro pelo histórico completo. Respostas são downloads privados,
sem cache. Não há URLs públicas ou arquivos de backup expostos por HTTP.

## Lotes de entregas

- `GET /entregas/lote/`: grade autenticada, sem gravação; `data` e `situacao` podem
  preencher os padrões de um novo lote.
- `POST /entregas/lote/`: CSRF obrigatório; campos `chave` UUID, `data_padrao`,
  `situacao_padrao`, `linhas` JSON (até 500 objetos de strings, campos codigo/data/
  horario/situacao), `acao` e, na confirmação, `comprovante` da prévia assinada.
  `acao=prever` valida e mostra a prévia sem gravar; `editar` retorna à grade;
  `salvar` confirma a prévia e grava atomicamente, com redirecionamento no sucesso.
- `GET /entregas/lote/salvo/<pk>/`: recibo acessível apenas ao usuário do lote.

Erros de entrada retornam 400, chave já utilizada com conteúdo diferente retorna
409 e falha de gravação retorna 503 com dados preservados. Repetição idêntica
retorna o mesmo recibo, sem novas entregas. Nenhum preço é aceito do navegador.

## Fronteira do acesso online

As rotas são as mesmas, com OAuth e lista de e-mails no ngrok antes da aplicação.
A fronteira WSGI rejeita host desconhecido com 400 e proxy/identidade inválidos com
403, inclusive antes dos estáticos. Não existe rota pública de dados nem download
do SQLite ou arquivos privados. POST segue exigindo CSRF, mesmo após OAuth/login.
Login e Admin no perfil online têm limite de tentativas com 429 e Retry-After.
O modo de prova serve apenas texto constante e não encaminha rotas ao Django.

Conciliação usa os mesmos filtros de período e acrescenta `codigo` (trecho textual,
até 100 caracteres), `situacao_conciliacao` (vazio, `recuperada`, `insucesso_real`,
`concluida`, `revisao`) e `pagina` (30 ciclos por página). Consulta inválida não
mostra registros; CSV inválido retorna 400. O download inclui todas as páginas
da consulta. Nenhuma dessas rotas aceita escrita ou modifica o histórico.

Desde 30/10/2026, `/`, `/auditoria/` e `/conciliacao/` retornam Cache-Control
com no-store/no-cache/must-revalidate/private. Cada GET válido recompõe dados do
banco, refletindo gravações anteriores sem comando manual de conciliação.
Nenhuma rota de cadastro, autenticação ou exportação foi alterada nessa correção.

Em 31/10/2026, os cards de `/` passam a usar o namespace interno
`indicadores_principais`: três contagens de registros do período, pendentes e
recuperadas conciliadas e taxa mista. Não há novo endpoint. XLSX mantém cinco
abas; seu resumo distingue a Taxa de Sucesso da taxa por encomenda da auditoria.
