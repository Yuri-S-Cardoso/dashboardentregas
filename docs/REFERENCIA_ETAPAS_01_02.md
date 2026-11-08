# Conferência de Entregas — etapas 01 e 02

Sistema Django local para registros de entregas, espelhos da empresa, jornadas,
custos e pagamentos, com indicadores, metas, gráficos e conciliação financeira.
Interface em português, valores em reais, SQLite e fuso
`America/Sao_Paulo`. Sem serviços externos em execução.

## Executar no Windows (PowerShell)

Python **3.13** é obrigatório. O ambiente `.venv` e o banco já foram preparados
nesta entrega. Os primeiros comandos abaixo também permitem recriar o ambiente:

```powershell
Set-Location 'Y:\Entregas'
py -3.13 -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
& '.\.venv\Scripts\python.exe' manage.py migrate
& '.\.venv\Scripts\python.exe' manage.py importar_excel 'referencias/Conferencia_de_Entregas(3).xlsx'
& '.\.venv\Scripts\python.exe' manage.py createsuperuser
& '.\.venv\Scripts\python.exe' manage.py runserver --insecure 127.0.0.1:8000
```

Abra **http://127.0.0.1:8000/** e entre com o usuário criado. A senha é escolhida
interativamente; nenhuma credencial inicial foi criada. O Admin fica em `/admin/`.
`Ctrl+C` encerra o servidor. Não é preciso ativar o ambiente nem alterar a política
de execução do PowerShell.

`DEBUG` vem desativado. `--insecure` permite ao servidor de desenvolvimento servir
o CSS local nessa configuração. Esse servidor destina-se ao computador e à rede
local; não configure encaminhamento de portas ou hospedagem pública.

## Acesso pelo celular na mesma rede

Identifique o IPv4 privado do computador com `ipconfig`. Exemplo, se o IP for
`192.168.1.10`, no mesmo terminal:

```powershell
$env:DJANGO_ALLOWED_HOSTS = 'localhost,127.0.0.1,192.168.1.10'
& '.\.venv\Scripts\python.exe' manage.py runserver --insecure 192.168.1.10:8000
```

Abra `http://192.168.1.10:8000/` no celular conectado ao mesmo Wi-Fi. Substitua o IP
pelo endereço real. Se solicitado pelo Windows, permita acesso somente na rede
privada. O acesso continua exigindo login. A configuração foi preparada; acesso
físico pelo celular e refinamento visual mobile não foram validados nesta etapa.

## Fonte de dados

A pasta inicial estava vazia e o arquivo com sufixo `(3)` não estava disponível.
Foi localizado `Conferencia_de_Entregas.xlsx` na Área de Trabalho do OneDrive
acadêmico, com as quatro abas e todos os números históricos pedidos. Uma cópia
**byte a byte**, com o nome esperado pelo comando, está em `referencias/`.
O original não foi alterado. O caminho exato e o SHA-256 constam no relatório.
Não foi possível comparar com uma versão independente chamada `(3)`.

O banco contém **169 entregas** (154 baixas e 15 insucessos), receita prevista de
**R$ 770,00**, um espelho, quatro jornadas e nenhum pagamento efetivo.
126 datas de agenda sem dados de jornada foram ignoradas. Códigos repetidos foram
mantidos; a posição e a linha original não dependem da ordenação dos horários.

## Regras e importação

- O código de entrega é texto e pode se repetir, inclusive no mesmo dia.
- Somente `Baixa realizada` gera receita. Insucesso gera R$ 0,00.
- Cada entrega guarda o preço por baixa usado no seu cadastro/importação.
  Mudar configurações cria outra versão e não recalcula registros existentes.
  Um cadastro manual, mesmo retroativo, usa a configuração vigente no cadastro.
- Valores opcionais vazios são `NULL`. Zero digitado é preservado como zero.
- Janelas históricas são durações independentes dos horários reais.
- Espelhos com a mesma competência são permitidos. Espelho não é pagamento.
- A importação é transacional. Uma linha inválida cancela toda a operação.
- O SHA-256 identifica uma importação: repetir os mesmos bytes, mesmo renomeados,
  não cria registros e não restaura exclusões nem desfaz edições manuais.
- Mesmo nome com bytes diferentes é bloqueado para revisão, sem substituição
  automática. Arquivos diferentes de nomes diferentes são novas origens;
  não renomeie versões alteradas para contornar a proteção.
- Layout inesperado ou fórmula em um campo de entrada interrompe a importação.
  Fórmulas auxiliares não geram registros e seus caches não são dados de entrada.
- Rastreabilidade por arquivo, hash, aba, linha, ordem, valores e formatos de origem
  fica disponível no Admin. A reimportação mostra o resumo original do lote.

Todos os usuários autenticados são operadores do mesmo acervo local. O Admin exige
usuário de equipe e permissões Django. Não há cadastro público de usuários.

## Verificar

```powershell
& '.\.venv\Scripts\python.exe' manage.py check
& '.\.venv\Scripts\python.exe' manage.py makemigrations --check --dry-run
& '.\.venv\Scripts\python.exe' manage.py test --verbosity 2
& '.\.venv\Scripts\python.exe' -m pip check
```

Os testes usam outro banco, em memória. Cinco testes de histórico leem o Excel
privado original da pasta `referencias/`: são ignorados se ele não estiver presente
em outro checkout. Outros quatro testes históricos foram adicionados na etapa 02.
Os testes sintéticos continuam verificando o importador sem
depender de dados privados. Nesta entrega os testes históricos foram executados.

## Arquivos e conservação

`config/` contém configurações; `core/`, componentes compartilhados e importações;
`entregas/`, registros e importador; `conferencia/`, espelhos e pagamentos;
`jornadas/`, custos; `painel/`, resumo e versões de parâmetros; `templates/` e
`static/`, a interface; `tests/`, testes; `docs/`, documentação técnica.

`db.sqlite3`, `.local/secret_key`, Excel e relatórios são privados e estão no
`.gitignore`. O segredo é gerado aleatoriamente no primeiro uso, fora do código,
ou pode vir de `DJANGO_SECRET_KEY`. Faça cópia de segurança do banco e do Excel
com o servidor parado; preserve também `.local/` para manter as sessões.

Não foi inicializado um repositório Git, pois a pasta não continha um.
Nenhum commit, push ou publicação foi realizado. Os relatórios estão em
`relatorios/ETAPA_01_RELATORIO.md` e `relatorios/ETAPA_02_RELATORIO.md`.
A etapa 03 depende de nova autorização.

## Indicadores e conferência — etapa 02

O Painel Geral (`/`) usa apenas o banco local e reúne produtividade, faturamento,
metas, horas, custos, resultados e sete gráficos em SVG produzidos por JavaScript
local. As legendas permitem alternar séries. As tabelas de valores funcionam também
sem JavaScript. Não há CDN, biblioteca gráfica ou dependência nova de produção.

Os filtros de histórico completo, intervalo, dia, semana ISO, mês/ano e quinzena
valem para indicadores, tabelas e gráficos. O link **Conferência Financeira**
(`/auditoria/`) conserva o mesmo filtro. Se o filtro estiver inválido, o sistema
exibe os erros e não substitui o recorte pelo histórico inteiro.

Regras de cálculo:

- Intervalos: horários em ordem crescente dentro do mesmo dia; apenas diferenças
  positivas entre horários consecutivos conhecidos. Nunca cruza dias nem elimina
  registros de entrega. O resumo pondera a média pelo número de intervalos válidos.
- Horas: par real tem prioridade; se faltar, usa apenas janela histórica existente,
  com origem identificada. Jornadas que cruzam meia-noite somam a virada do dia.
  Não há estimativa automática de jornada. Totais mistos mostram horas reais e
  históricas separadas; lacunas bloqueiam taxas globais por hora.
- Consumo: soma de KM / soma de litros **do mesmo conjunto de jornadas** com
  ambos informados e litros positivos. Em 20/10 não há consumo calculável.
- Custos conhecidos não completam valores ausentes com zero. Resultado parcial
  é previsto menos custos conhecidos; resultado líquido completo exige ambos os
  campos de custo em todas as jornadas e jornadas para todas as datas operacionais.
- Custo por tentativa usa dias com custos conhecidos e as tentativas desses dias.
  Custo por KM usa jornadas com custos e KM; faturamento por KM usa datas com todos
  os odômetros preenchidos. As taxas por subconjunto são explicitamente indicadas.
- Metas usam a configuração vigente, com a versão identificada. Metas semanais e
  mensais são integrais, mesmo num recorte parcial. Preços históricos não mudam.
- Projeção: média de receita nos dias com entregas × dias com entregas do cenário
  informado (padrão: cinco). É um cenário condicional, não uma escala presumida ou
  garantia de faturamento; a quantidade de dias observados fica visível.

A auditoria agrega os documentos por competência. Campos incompletos impedem
conferência definitiva. Referência repetida na mesma competência, ou conteúdo
idêntico sem referência, gera alerta de possível duplicidade. Nenhum registro é
excluído ou descontado automaticamente; valores conhecidos permanecem visíveis
para revisão e não confirmam divergência/saldo enquanto houver dúvida documental.

Diferença = registrado − informado, somente em competências confrontáveis.
Ausência de espelho não é perda confirmada. Em 15/10 a diferença é R$ 0,00;
na segunda quinzena de outubro, R$ 610,00 ficam aguardando espelho.

Pagamentos são vinculados pelo início/fim da competência, mesmo quando recebidos
em outro mês. Ausência aparece como **Sem pagamento registrado** e não comprova
inadimplência. Saldo exige dados completos, pagamento cadastrado e quinzena sem
recorte. Num filtro diário, o pagamento integral da quinzena é identificado e não
é subtraído de uma base parcial. Períodos de pagamento fora do padrão não são
rateados: aparecem para revisão.

O backup anterior às mudanças foi feito por `sqlite3.Connection.backup`, validado
e mantido em `.local/backups/`, fora do Git. A etapa 02 não alterou schema nem
registros reais. Não restaure um backup sobre o banco ativo durante o uso.

Para os testes de JavaScript, se Node estiver instalado no computador de
desenvolvimento (não é necessário para usar a aplicação):

```powershell
node --test tests/test_graficos.cjs
node --check static/js/graficos.js
node --check static/js/filtros.js
```

A execução da etapa 02 aprovou 95 testes Django e oito testes Node. A inspeção
visual em navegador permanece pendente devido à restrição registrada na etapa 01;
foram feitas verificações HTTP autenticadas em cópia descartável do banco e testes
de geração/interação dos SVGs, sem tentar contornar a restrição.

Documentação técnica de referência: [autenticação Django 5.2](https://docs.djangoproject.com/en/5.2/topics/auth/default/)
e [datas numéricas do openpyxl](https://openpyxl.readthedocs.io/en/stable/api/openpyxl.utils.datetime.html).
