# Conferência de Entregas

Sistema web em Django para acompanhar entregas, registrar tentativas e conferir
o faturamento previsto com os documentos e pagamentos da transportadora.
Reúne cadastro em lote, conciliação por código, indicadores, jornadas, custos e
relatórios em uma interface responsiva para computador e celular.

Os dados ficam em um banco SQLite da instalação. Um único servidor atende o
computador e os dispositivos da rede privada. Há também um modo remoto opcional
com HTTPS, Google OAuth no ngrok e autenticação Django.

**Python 3.13 · Django 5.2 LTS · SQLite · Waitress · WhiteNoise · JavaScript puro**

## Conteúdo

- [Funcionalidades](#funcionalidades)
- [Regras dos indicadores](#regras-dos-indicadores)
- [Instalação no Windows](#instalação-no-windows)
- [Uso diário e rede local](#uso-diário-e-rede-local)
- [Acesso remoto com ngrok](#acesso-remoto-com-ngrok)
- [Importação e exportação](#importação-e-exportação)
- [Backup e restauração](#backup-e-restauração)
- [Configurações e administração](#configurações-e-administração)
- [Testes](#testes)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Versionamento e dados privados](#versionamento-e-dados-privados)
- [Documentação](#documentação)

## Funcionalidades

### Cadastro de entregas

- Cadastro individual, edição e exclusão com confirmação.
- Situações **Baixa realizada** e **Insucesso**.
- Código tratado como texto, preservando zeros à esquerda e repetições.
- Data efetiva e horário opcional; horário vazio não vira meia-noite.
- Lista com filtros por data/situação e paginação.
- Preço por baixa preservado no registro, sem recálculo retroativo.

### Cadastro em lote no estilo planilha

Grade com 20 linhas iniciais e até 500 registros por lote. Permite digitação
com Enter/Tab, inclusão de linhas, colagem de códigos e colagem de células do
Excel com mapeamento de colunas.

Data e situação podem ter padrões do lote e exceções por linha. O horário usa
controle nativo de hora, com preenchimento opcional. Antes da gravação, o sistema
valida todas as linhas e apresenta uma prévia para confirmação.

A gravação é atômica: falha em qualquer registro cancela o lote inteiro.
O recibo da operação impede duplicação por reenvio da mesma solicitação,
preservando as repetições de código que foram cadastradas intencionalmente.
Há rascunho temporário no navegador, sem senha, sessão ou token CSRF; ele não
substitui a confirmação para gravar no banco.

[Guia do cadastro em lote](docs/CADASTRO_EM_LOTE.md).

### Painel Geral

O painel abre no mês vigente de **America/Sao_Paulo** e apresenta:

| Indicador | O que representa |
|---|---|
| Total de encomendas | Todos os registros de entrega do período, inclusive repetições |
| Entregas concluídas | Ocorrências de Baixa realizada nas datas efetivas do período |
| Total com insucesso | Ocorrências de Insucesso no período |
| Insucessos pendentes | Encomendas/ciclos distintos iniciados no período e ainda sem baixa posterior válida |
| Entregas recuperadas | Encomendas/ciclos distintos iniciados no período com insucesso e baixa posterior válida |
| Taxa de Sucesso | Fórmula operacional do card, explicada abaixo |
| Faturamento Mensal | Receita prevista do mês de referência completo |
| Faturamento 1ª Quinzena | Receita prevista dos dias 1 a 15 desse mês |
| Faturamento 2ª Quinzena | Receita prevista dos dias 16 ao último dia civil desse mês |

Os três cards financeiros usam o **mês completo do filtro quando ele está contido
em um único mês**. No histórico ou em intervalos que atravessam meses, usam o mês
vigente. O mês fica visível nos cards. A soma das duas quinzenas corresponde ao
mensal, incluindo fevereiro de 28/29 dias. Os outros indicadores, tabelas e
exportações continuam seguindo o período filtrado.

O **Menu do Painel** reúne filtros, exportações e Conferência Financeira.
Estão disponíveis dia, semana, mês/ano, quinzena, intervalo personalizado e
histórico completo explícito. A semana começa **domingo** e termina **sábado**.

As tabelas **Entregas por dia**, **Semanas** e **Meses** mostram faturamento,
taxa de sucesso, ocorrências e medidas de jornada/consumo, conforme cada tabela.
A média de receita semanal/mensal usa somente dias com registros de entrega.
Valores ausentes aparecem como **Não informado**; cobertura incompleta, como
**Parcial**.

Sete gráficos locais apresentam situação das encomendas, faturamento diário,
semanal e mensal, metas, custos e produtividade. As legendas permitem alternar
séries, e as tabelas de valores continuam disponíveis sem JavaScript.

Após um cadastro, lote, edição ou exclusão, a próxima consulta recalcula os
indicadores. Uma aba já aberta precisa ser recarregada.

[Guia do painel](docs/PAINEL_GERAL.md).

### Conciliação de entregas

A conciliação analisa o histórico por código e ciclo candidato para identificar
conclusões, recuperações, pendências e casos que exigem revisão.

Uma recuperação posterior pode resolver a pendência de um período anterior,
sem apagar os insucessos registrados nem deslocar a receita da data da baixa.
Tentativas repetidas do mesmo ciclo não criam novas encomendas na população
conciliada.

Códigos potencialmente reutilizados, cronologia conflitante e situações sem
ordem comprovada ficam separados para revisão. Uma baixa anterior não resolve
um insucesso posterior. A consulta permite filtrar código/situação, paginar e
exportar a conciliação em CSV.

[Critérios de conciliação](docs/CONCILIACAO_ENTREGAS.md).

### Conferência financeira

- Cadastro e edição de espelhos da empresa por competência.
- Quantidades de baixas/insucessos, valor informado, referência textual do documento, vencimento e observações.
- Cadastro separado dos pagamentos recebidos, com competência quinzenal e referência textual do comprovante.
- Comparação entre registros próprios e documentos da empresa por data e quinzena.
- Diferenças financeiras e de quantidade, datas sem espelho e alertas de duplicidade.
- Separação entre **previsto**, **informado** e **recebido**.
- Saldo calculado apenas quando os dados e o recorte permitem uma comparação válida.
- Auditoria de tentativas, ganho médio por baixa e projeção condicional.

Ausência de espelho é pendência de conferência. Ausência de pagamento cadastrado
não comprova inadimplência. O sistema não elimina documentos ou ajusta receitas
automaticamente ao encontrar divergências.

### Jornadas, custos e consumo

Registro de horários reais, duração histórica, odômetros, litros consumidos,
combustível e outros custos.

- Horas reais têm prioridade sobre a duração histórica da mesma jornada.
- Horários podem atravessar a meia-noite.
- Distância = odômetro final − inicial; odômetro inicial zero é válido.
- No método tanque cheio a tanque cheio, os litros repostos ao mesmo nível
  representam o consumo do percurso.
- Combustível é o **valor total pago**, não um preço unitário presumido.
- KM/L agregado usa distância e litros das mesmas jornadas com dados válidos.
- Custos, resultados e margens identificam lacunas e cobertura parcial.

Campos vazios continuam ausentes, sem estimativa de horas, quilômetros ou despesas.

## Regras dos indicadores

O card e as tabelas têm **populações diferentes**, por definição operacional:

```text
Card Taxa de Sucesso =
ocorrências de baixa / (ocorrências de baixa + pendências distintas) × 100

Taxa de Sucesso das tabelas =
encomendas distintas concluídas / encomendas distintas identificadas
cuja primeira tentativa ocorreu no período da linha × 100
```

Nas tabelas, a população válida é concluídas + pendentes do mesmo período de
início. Recuperações posteriores até a referência conhecida são consideradas;
ambiguidades seguem os critérios da conciliação e ficam fora dessa população.
Sem denominador válido, o resultado é **Não informado**.

As outras colunas das tabelas continuam contando ocorrências nas datas efetivas.
**Receita prevista não é pagamento recebido**. Uma baixa gera o preço histórico
do registro; um insucesso gera receita zero. Alterar a configuração de preço
não modifica entregas antigas.

## Instalação no Windows

### Requisitos

- Python **3.13**, disponível pelo comando `py -3.13`.
- Git para clonar o repositório.
- Navegador atualizado.
- Node.js apenas para executar os testes JavaScript.
- Agente e conta ngrok apenas se for utilizar o modo remoto.

As versões Python estão fixadas em [requirements.txt](requirements.txt).
Não é necessário Docker, framework de frontend, CDN nem executar como administrador.

### Nova instalação

O GitHub contém o código e as migrations. Banco, usuários, planilhas,
relatórios privados, ambiente virtual e configurações locais **não acompanham o clone**.

No PowerShell:

```powershell
git clone https://github.com/Yuri-S-Cardoso/dashboardentregas.git
Set-Location .\dashboardentregas

py -3.13 -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt

& '.\.venv\Scripts\python.exe' manage.py migrate
& '.\.venv\Scripts\python.exe' manage.py createsuperuser
& '.\.venv\Scripts\python.exe' manage.py collectstatic --noinput

& '.\Iniciar_Entregas.bat'
```

`migrate` prepara um banco novo, sem entregas reais, e a configuração inicial.
`createsuperuser` pede nome e senha; não há credencial padrão.
O segredo Django é gerado e mantido privadamente em `.local/`.

Os comandos usam o Python do ambiente diretamente; não exigem ativar
`Activate.ps1`. Se o projeto já está em `Y:\Entregas`, abra essa pasta em vez
de criar outra instalação sobre os seus dados.

Para uma instalação já utilizada, preserve `db.sqlite3` e `.local/` e faça backup
antes de atualizar. Não execute nova importação para atualizar o código ou o visual.

## Uso diário e rede local

Dê duplo clique em **Iniciar_Entregas.bat** e mantenha a janela aberta.

O inicializador verifica ambiente, banco existente, migrations, porta e estáticos.
Uma Ethernet/Wi-Fi física, ativa, com IPv4 privado e perfil Windows **Privado**
é escolhida automaticamente. Havendo várias elegíveis, solicita escolha.
Sem interface elegível, informa o motivo e inicia apenas em localhost.

O mesmo processo Waitress atende:

- Computador: `http://127.0.0.1:8000/`.
- Celular: o IPv4 privado específico mostrado na janela, na mesma rede confiável.

O inicializador não usa escuta genérica, não muda o firewall e não exige
administração do Windows. HTTP local/LAN não criptografa o tráfego; utilize
somente rede privada confiável.

Se o celular não acessar, confira IP/porta, rede compartilhada, perfil Privado e
isolamento da rede de convidados. Não desative o firewall nem abra portas do
roteador para resolver. Acesso remoto deve utilizar o modo protegido próprio.

Opções pelo terminal:

```powershell
# Apenas este computador.
& '.\.venv\Scripts\python.exe' scripts/iniciar_sistema.py --local

# Verificação sem iniciar o servidor.
& '.\.venv\Scripts\python.exe' scripts/iniciar_sistema.py --local --verificar

# Porta alternativa.
& '.\.venv\Scripts\python.exe' scripts/iniciar_sistema.py --local --porta 8001
```

Para encerrar, pressione **Ctrl+C** na janela do servidor e aguarde.
Fechar a aba do navegador não encerra o processo.

## Acesso remoto com ngrok

O modo opcional **Iniciar_Entregas_Online.bat** mantém o Waitress exclusivamente
em `127.0.0.1:8000` e encaminha o domínio HTTPS exato configurado no ngrok.

A proteção combina Google OAuth com lista explícita de e-mails autorizados,
validação da identidade na fronteira do proxy e login obrigatório do Django.
O perfil online mantém DEBUG=False, hosts/origem CSRF restritos e cookies seguros.
Não publica o código-fonte nem abre uma porta no roteador.

Cada instalação precisa de agente/conta compatível, configuração privada e
validação dos controles antes de autorizar dados reais. O modelo público é
[config/ngrok_online.example.json](config/ngrok_online.example.json);
a configuração preenchida fica em `.local/ngrok_online.json`, fora do Git.
O authtoken fica na configuração privada do agente ngrok.

```powershell
# Inspeciona a configuração sem abrir túnel.
& '.\Iniciar_Entregas_Online.bat' --verificar

# Serve apenas uma mensagem de prova, sem Django ou banco.
& '.\Iniciar_Entregas_Online.bat' --testar-protecao
```

OAuth permitido/negado e HTTPS precisam ser conferidos na configuração real
antes da aprovação privada. Não substitua esse fluxo por um túnel sem as
proteções. Use **um inicializador por vez**.

[Guia do modo remoto](docs/ACESSO_NGROK.md).

## Importação e exportação

### Importar a planilha original

A importação é um comando administrativo para um layout específico, com as abas
**Painel Geral**, **Minhas Entregas**, **Espelho da Empresa** e **Jornada e Custos**:

```powershell
& '.\.venv\Scripts\python.exe' manage.py importar_excel 'C:\dados-privados\planilha.xlsx'
```

O importador valida o layout, preserva códigos, duplicados, preços, campos
ausentes e rastreabilidade por aba/linha. Grava tudo em uma transação e identifica
o arquivo por SHA-256. Reimportar o mesmo arquivo não recria nem sobrescreve
registros já tratados. Ele não modifica a planilha de origem.

### Exportar relatórios

No Menu do Painel ou na Conferência Financeira, escolha o período ou histórico:

| Formato | Conteúdo |
|---|---|
| Excel | Cinco abas: entregas, espelhos, jornadas/custos, pagamentos e resumo de indicadores |
| CSV de entregas | Código, data, horário, situação e valor previsto; UTF-8 com BOM e ponto e vírgula |
| CSV da conciliação | Resultados derivados dos códigos/ciclos da consulta |

Os downloads exigem login e preservam campos ausentes e valores históricos.
Textos potencialmente interpretados como fórmulas recebem proteção.
Para códigos com zeros à esquerda, prefira XLSX ou importe a coluna CSV como texto.

**Exportação não é backup.** O XLSX de saída também não é entrada automática do
importador do layout original.

## Backup e restauração

Backup consistente e verificável:

```powershell
& '.\.venv\Scripts\python.exe' manage.py backup_local
```

O comando usa a API SQLite e cria arquivo com nome único em `.local/backups/`,
acompanhado de manifesto com tamanho e SHA-256, após verificar a integridade.
Mantenha cópias privadas em outro local seguro; Git/GitHub não substituem backup.

Para restaurar, encerre **todos** os servidores/acessos ao banco e execute:

```powershell
& '.\.venv\Scripts\python.exe' manage.py restaurar_backup '.\.local\backups\SEU_BACKUP.sqlite3'
```

O comando testa uma cópia isolada, preserva um backup do banco atual e exige a
confirmação **RESTAURAR** antes da substituição. Não remova arquivos SQLite
`-wal`, `-shm` ou `-journal` manualmente.

## Configurações e administração

Configurações mantém versões do preço por baixa e metas diária, semanal e mensal.
Novos registros usam o preço vigente; registros antigos conservam seus preços.
Metas não reescrevem o histórico e a projeção é um cenário condicional, sem
garantia de faturamento.

A administração Django em `/admin/` permite a usuários de equipe autorizados
gerenciar cadastros, usuários, grupos e registros de importação conforme permissões.
As páginas operacionais exigem autenticação e utilizam o acervo compartilhado da
instalação; não há separação automática por operador.

## Testes

Os testes usam banco isolado e geram dados sintéticos. Node.js é ferramenta de
verificação, não uma dependência de execução do servidor.

```powershell
& '.\.venv\Scripts\python.exe' manage.py check
& '.\.venv\Scripts\python.exe' manage.py test --noinput
node --test tests/test_graficos.cjs tests/test_mobile.cjs tests/test_lote.cjs tests/test_menu_painel.cjs
```

A suíte cobre importação, modelos, regras financeiras, períodos, conciliação,
cards, jornadas/consumo, lote, exportações, backup/restauração, inicialização,
login, CSRF e fronteira de segurança do ngrok.

Alguns testes históricos dependem de uma planilha privada em `referencias/`
ou de evidência local em `relatorios/`; são ignorados quando esses arquivos não
estão disponíveis. Eles não devem ser publicados para eliminar esses skips.

[Roteiros e resultados de testes](docs/08-testes.md).
A inspeção visual em computador/celular físico continua sendo uma verificação
manual distinta dos testes automatizados.

## Estrutura do projeto

```text
config/       Configurações, rotas, WSGI e proteção do modo online
core/         Regras comuns, períodos, backup, locks e segurança
entregas/     Cadastro, lote, importação e conciliação de entregas
painel/       Dashboard, cards, gráficos, filtros e exportações
conferencia/  Espelhos, pagamentos e conferência financeira
jornadas/     Horas, distância, consumo e custos
templates/    Interface HTML e componentes compartilhados
static/       CSS e JavaScript locais
scripts/      Inicializadores Waitress e processo ngrok
tests/        Testes Django e JavaScript
docs/         Guias, arquitetura e regras do sistema
```

## Versionamento e dados privados

O repositório deve conter código, migrations, templates, `static/`, testes,
documentação, dependências fixadas e exemplos **sem credenciais**.

O [.gitignore](.gitignore) mantém fora do versionamento:

- `.venv/`, caches e artefatos de ferramentas.
- `.local/`, segredos, configuração preenchida e credenciais do ngrok.
- Bancos SQLite, arquivos de transação, cópias e manifestos.
- Planilhas, CSV/TSV, comprovantes PDF e outros arquivos operacionais.
- `referencias/`, `relatorios/`, uploads, exportações e backups privados.
- `staticfiles/`, gerado por `collectstatic`, logs e temporários.

`static/` e `staticfiles/` têm funções diferentes: a primeira contém fontes e
é versionada; a segunda é saída gerada e não é versionada.
Exemplos de configuração e `requirements.txt` permanecem no Git.
Arquivos de dados sintéticos nesses formatos precisam de revisão e exceção
explícita antes de serem incluídos.

Adicionar um caminho ao `.gitignore` **não remove arquivos já rastreados nem
conteúdo do histórico**. Confira o índice e o diff antes de publicar.
Se uma credencial real tiver sido publicada, tratá-la exige revogação/rotação;
somente ignorar o arquivo depois não resolve.

[Política de versionamento](docs/VERSIONAMENTO.md).

## Documentação

- [Índice da documentação](docs/00-indice.md)
- [Guia de uso diário](docs/GUIA_RAPIDO.md)
- [Painel e cards financeiros](docs/PAINEL_GERAL.md)
- [Cadastro em lote](docs/CADASTRO_EM_LOTE.md)
- [Conciliação e recuperação](docs/CONCILIACAO_ENTREGAS.md)
- [Acesso remoto protegido](docs/ACESSO_NGROK.md)
- [Arquitetura](docs/03-arquitetura.md)
- [Regras financeiras](docs/04-regras-do-jogo.md)

Relatórios de execução e evidências da instalação ficam em `relatorios/`,
intencionalmente fora do Git. Referências a esses arquivos na documentação
histórica são locais e não acompanham o clone.
