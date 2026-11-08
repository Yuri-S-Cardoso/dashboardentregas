# Conciliação de entregas e recuperação

Desde 31/10/2026, os sete cards seguem as definições explícitas do proprietário:

- **Total de encomendas**: todos os registros no período, incluindo repetições.
- **Entregas concluídas**: todos os registros de Baixa realizada no período.
- **Total com insucesso**: todos os registros de Insucesso no período, inclusive
  tentativas repetidas e insucessos de encomendas recuperadas depois.
- **Insucessos pendentes**: sem baixa posterior válida registrada; corresponde
  ao indicador técnico Insucesso Real. Não significa que nunca serão entregues.
- **Entregas recuperadas**: tiveram insucesso e uma baixa posterior válida.
- **Taxa de Sucesso**: ocorrências de baixa / (ocorrências de baixa + pendências
  distintas) × 100. Usa base mista, não representa uma taxa por encomendas únicas.
  Com denominador zero fica não informada. A apresentação arredonda duas casas
  com ROUND_HALF_UP; o cálculo mantém precisão Decimal.
- **Faturamento**: receita prevista das baixas nas suas datas efetivas; não é
  pagamento recebido.

A relação dos três primeiros cards é total de registros = baixas registradas +
insucessos registrados. Pendentes e recuperadas contam encomendas distintas.
As relações anteriores por encomendas únicas continuam na auditoria de conciliação,
com suas identidades ambíguas separadas. Baixas repetidas permanecem nos totais
de registros e no numerador da Taxa de Sucesso, inclusive quando houver revisão.

A taxa por tentativa, repetições, detalhes de conciliação e alertas financeiros
ficam em **Auditoria de tentativas e registros**, na Conferência Financeira.
Critérios/alertas continuam recolhidos no painel. Faturamento usa as datas efetivas.
A taxa mista permanece no card. Após o ajuste pontual de 31/10/2026, somente as
tabelas dia/semana/mês usam concluídas distintas / população distinta iniciada
no período, com recuperação verificada no histórico completo até a referência.
Casos em revisão seguem excluídos dessa população. As demais colunas continuam
por data efetiva e o serviço central de conciliação não foi modificado. Semana vai
de domingo a sábado e o acesso sem filtro usa o mês vigente em São Paulo.
O gráfico de conciliação preserva
três grupos exclusivos de encomendas distintas: concluídas sem insucesso,
pendentes e recuperadas. Sua base está identificada e difere dos cards de registros.

## Atualização automática

Cada nova consulta lê o banco e chama a conciliação existente, incluindo o
histórico posterior ao período. Cadastro individual ou confirmação do lote,
edição e exclusão passam a refletir a situação derivada na próxima consulta.
Não há comando manual, classificação persistida ou limpeza do histórico.
Prévia de lote não altera resultados e o reenvio idempotente não duplica baixas.
Painel, conferência e consulta de conciliação enviam Cache-Control com no-store,
no-cache, must-revalidate e private. Não há atualização contínua sem nova consulta.

## Identidade e cronologia

- Código é texto exato. `000123` e `123` não são convertidos em um código único.
- Na ausência de outro identificador, o mesmo código em um histórico aberto é
  tratado como um ciclo candidato. Não se presume unicidade vitalícia do código.
  O proprietário não soube confirmar se há reutilização na transportadora.
- Datas e horários ordenam os eventos. PK só estabiliza a apresentação. No mesmo
  dia, insucesso e baixa exigem horários conhecidos e baixa estritamente posterior.
  Horários iguais não estabelecem uma recuperação. Dias diferentes estabelecem
  ordem mesmo sem horário; NULL permanece desconhecido, nunca vira meia-noite.
- A primeira baixa encerra o ciclo. Outro insucesso em momento posterior abre
  um novo candidato e sinaliza possível reutilização. Todo esse código exige
  revisão; uma baixa anterior não resolve o novo insucesso.
- Várias baixas no mesmo dia, sem insucesso posterior, contam uma conclusão e
  geram alerta financeiro. A data exibida é a primeira baixa válida registrada.
- Baixas em dias diferentes podem representar duplicidade ou reutilização:
  exigem revisão. Situações diferentes sem ordem comprovada no mesmo dia, código
  ausente e situação desconhecida também exigem revisão. Código ausente não agrupa
  registros distintos.
- Casos em revisão não entram em entregas identificadas, recuperadas, Insucesso
  Real ou percentual por encomenda distinta da auditoria. A tela informa quantos
  códigos/ciclos candidatos ficaram separados. Seus registros continuam nos três
  primeiros cards e suas baixas continuam na Taxa de Sucesso de base mista.
- Não há limite arbitrário de dias para recuperar uma entrega. Sem outro campo
  de identidade, uma reutilização que não produz conflito cronológico pode ser
  indistinguível de novas tentativas do mesmo ciclo. A conciliação é uma regra
  auditável sobre os dados disponíveis, não uma certificação externa de identidade.

## Períodos e referência

Dia, semana, mês, quinzena e intervalo filtram os três primeiros cards pela data
efetiva de cada registro. Para pendentes e recuperadas, selecionam ciclos cuja
**primeira tentativa registrada** pertence ao período. O histórico completo é
consultado para verificar baixas posteriores em outra semana, quinzena ou mês.
A referência da conciliação é o último dia disponível no histórico, exibida na tela.
Baixa posterior ao filtro não entra no card de ocorrências daquele período,
mas pode resolver sua pendência. A taxa combina as duas bases conforme a fórmula.

Se o filtro termina antes da referência, também se calcula uma fotografia até
o fim do período, descartando qualquer registro futuro antes de identificar os
ciclos. Essa fotografia não usa o futuro nem para detectar ambiguidades. A tela
mostra quantas conclusões/recuperações atuais ocorreram depois do período.
Conflitos descobertos mais tarde podem modificar o conjunto em revisão entre
as duas fotografias. Histórico incompleto pode omitir uma primeira tentativa.

Exemplo: insucesso em 31/10 e baixa em 01/11. No filtro de outubro a entrega é
recuperada no resultado atual, mas pendente na fotografia até 31/10. A receita
fica exclusivamente em novembro. No filtro de novembro essa baixa continua nas
ocorrências financeiras, mas a entrega não pertence à população iniciada em novembro.

## Consulta e auditoria

No painel, use **Consultar encomendas e histórico**. A tela
`/conciliacao/` mantém os filtros e permite pesquisar código/situação, com 30
ciclos por página. A tabela informa primeira tentativa, primeiro insucesso,
tentativas, baixa posterior válida, situação, alertas, receita e IDs de origem.
No celular, deslize a tabela lateralmente; o contêiner também aceita foco pelo
teclado. Os cards continuam resumindo a população completa do período.

**Baixar tabela de conciliação (CSV)** exporta toda a consulta, além da página
visível, em UTF-8 BOM com ponto e vírgula e proteção contra fórmulas. Para
preservar zeros à esquerda no Excel, importe Código como texto. O XLSX habitual
mantém as cinco abas e inclui a Taxa de Sucesso de base mista no resumo, com
duas casas de apresentação. O percentual antigo da auditoria é identificado como
“Sucesso por encomenda distinta (%)”. O CSV original
de entregas continua exportando ocorrências, sem alteração de formato.

As rotas exigem autenticação Django e só aceitam GET. O perfil online continua
exigindo OAuth e a mesma fronteira WSGI. Nenhum endpoint público foi criado.

## Finanças e persistência

Não há migration nem nova tabela: o serviço `entregas/services/conciliacao.py`
produz uma leitura derivada, comum à tela, exportação e auditoria. Nenhum registro
é excluído, fundido ou reclassificado. Chaves de ciclo são técnicas e derivadas;
não servem como identificadores permanentes de encomenda.

Cada baixa registrada conserva seu preço histórico e receita na sua data. Cada
insucesso continua com receita zero. O ganho médio por baixa continua dividindo
receita por ocorrências de baixa. Recuperação não gera nova receita, espelho ou
pagamento. Múltiplas baixas/identidade em revisão geram alertas para conferência,
sem ajuste monetário automático. Gráficos diários, horas, metas, semanas, meses e
conferência financeira mantêm as ocorrências e valores originais, com rótulos
que distinguem as unidades.
