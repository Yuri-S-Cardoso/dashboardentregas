# Banco de dados

Reestruturação do painel em 31/10/2026: **nenhuma alteração de modelos, schema ou
migrations**. Todas as novas medidas são derivadas somente de leitura. Backup
SQLite verificável foi criado antes da edição; análise real usa esse snapshot
com mode=ro e ensaio HTTP usa banco novo descartável. Não se registram filtros
ou resultados calculados no banco. Evidências no relatório do layout.

Conciliação de entregas (29/10/2026) não altera modelos/schema. Ciclos são derivados
em memória de código textual, data, hora e situação; o banco não possui um ID
externo de encomenda/ciclo. Ambiguidades de reutilização permanecem para revisão,
sem fusão física, deduplicação ou reclassificação de registros financeiros.

SQLite em `db.sqlite3`, privado e ignorado pelo Git. Testes usam SQLite em memória.

| Modelo | Campos de negócio |
| --- | --- |
| Entrega | código, data, horário, situação, ordem original, preço por baixa preservado |
| EspelhoEmpresa | competência, baixas pagas, insucessos, valor empresa, vencimento, documento, observações |
| Jornada | data, início/fim real, odômetros, litros, combustível, outros custos, janela histórica |
| Pagamento | data de pagamento, início/fim da quinzena, valor recebido, comprovante, observações |
| Configuracao | preço por baixa, metas diária/semanal/mensal, criação da versão |
| Importacao | arquivo, caminho, SHA-256 único, criação, resumo e avisos |

Os quatro modelos operacionais herdam importação opcional, aba, linha, snapshot
dos valores e formatos de origem, criação e atualização. A referência à importação
usa PROTECT; o lote não pode ser removido no Admin. Unicidade por lote/aba/linha
impede duplicação de origem, sem limitar códigos de entrega.

Dinheiro possui duas casas; distâncias e litros possuem três. Campos opcionais
preservam NULL. Constraints impedem valores negativos, situações inválidas,
odômetros invertidos e períodos de pagamento invertidos. Os modelos e formulários
completam a validação com mensagens legíveis.

As seis migrations próprias incluem esquema dos cinco aplicativos e parâmetros
iniciais 5/300/1500/6000. Execute `manage.py migrate` para criar ou atualizar o banco.

## Conservação na etapa 02

Nenhum modelo ou migration foi alterado. Indicadores são calculados em leitura e
não gravam totais derivados. Antes de modificar o código foi feito backup via
`sqlite3.Connection.backup` em `.local/backups/`, com `PRAGMA integrity_check` e
comparação de contagens/hashes lógicos de todas as tabelas. A evidência antes/depois
está em `relatorios/etapa02_backup_antes.json` e `etapa02_integridade_depois.json`.

Testes Django usam SQLite em memória. O smoke HTTP autenticado usa outra cópia
descartável e conta aleatória somente nessa cópia. Não cria usuário real e não
modifica entregas, importações, preços ou rastreabilidade do acervo original.

## Finalização

Etapa 03 também não altera schema. Novo backup anterior ao código está em
`.local/backups/etapa03_antes_20261021_232223.sqlite3`, com evidência em
`relatorios/etapa03_backup_antes.json`. O comando `backup_local` cria outros nomes
únicos, verifica integridade e grava tamanho/SHA-256 em JSON adjacente. Cópias
anteriores são conservadas.

`restaurar_backup` verifica o arquivo, abre uma cópia isolada e preserva o banco
atual antes de pedir RESTAURAR. Usa a trava do servidor e recusa arquivos de
transação pendentes. Fechar todos os acessos é responsabilidade explícita do
proprietário; não se deve apagar WAL/SHM/journal manualmente. O procedimento e
retenção conservadora estão no README. A recuperação foi ensaiada em isolamento,
sem substituir o banco real.

## Migração do cadastro em lote

`entregas.0002_cadastro_lote_horario_opcional` altera somente a nulabilidade do
horário de Entrega e cria `LoteEntrega` (usuário, UUID, hash do conteúdo, quantidade,
padrões e criação), com unicidade usuário/UUID. O modelo anterior exigia horário;
NULL é necessário para cadastrar códigos sem inventá-lo. O recibo persistente é
necessário para impedir reenvios mesmo após reiniciar o servidor ou trocar sessão,
e participa da mesma transação das entregas. Não há unicidade de código.

Backup verificável anterior: `relatorios/lote_antes.json` identifica arquivo e
manifesto. Os testes não modificaram o banco real; depois deles, a migração foi
aplicada com a trava existente do servidor. Permaneceram **170 entregas** (as 169
históricas e uma adicional que já existia), um espelho, quatro jornadas e nenhum
pagamento. Todos os campos e registros anteriores foram preservados. Apenas
metadados Django ganharam uma migration, um content type e quatro permissões;
o novo recibo permanece vazio. SQLite reposiciona a coluna alterada: a comparação
de integridade alinha nomes de colunas, em vez de comparar posições de SELECT *.

## Conservação no acesso ngrok

Backup verificável anterior está identificado em `relatorios/ngrok_antes.json`.
Não há migration ou modelo novo. Testes Django usam memória; HTTP do perfil online
usa cópia temporária, e o endpoint externo de prova não abre SQLite. As 170 entregas
e todas as demais linhas, schema e bytes do banco real são comparados antes/depois.
Contadores de tentativa de login remoto ficam em memória, sem alterar o acervo.
