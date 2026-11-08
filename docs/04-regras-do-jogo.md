# Regras operacionais e financeiras

**Apresentação vigente:** [PAINEL_GERAL.md](PAINEL_GERAL.md). A fórmula operacional
do card abaixo permanece aprovada. Exclusivamente nas tabelas dia/semana/mês,
a taxa usa concluídas distintas / população distinta iniciada no período, com
histórico completo até a referência e ambiguidades excluídas pela conciliação.
Quantidades e receitas continuam por data efetiva. Pendências são atribuídas uma
vez à primeira tentativa; a referência consulta todo o histórico. Média de receita
usa dias com registros, não dias presumidos. Denominador ausente não vira zero.
Tanque cheio a tanque cheio: odômetro inicial 0 é válido, litros repostos no mesmo
nível representam consumo e combustível é o total pago. KM/L agregado usa
somente pares da mesma jornada; real prevalece sobre histórico para horas.

**Definição atual dos cards, 31/10/2026:** total de encomendas conta registros;
entregas concluídas conta registros de baixa; total com insucesso conta registros
de insucesso. Pendentes e recuperadas contam encomendas distintas conciliadas.
Taxa de Sucesso = ocorrências de baixa / (ocorrências de baixa + pendências
distintas) × 100. Não é um percentual por encomendas únicas. Detalhes e filtros
em `CONCILIACAO_ENTREGAS.md`; as definições por encomenda das etapas abaixo são
mantidas como histórico e para a auditoria, sem substituir esta regra dos cards.

Baixa realizada gera o preço por baixa preservado no registro; insucesso gera zero.
No cadastro em lote, o mesmo preço vigente é lido na gravação e preservado em cada
entrega. Horário ausente permanece NULL, inclusive nas exportações; não é meia-noite
ou horário estimado. Os intervalos existentes já ignoram horários não informados.
Não há unicidade por código ou por competência de espelho. Ordem de origem é
preservada mesmo quando os horários não são crescentes.

Configurações são versões imutáveis na aplicação. Novas entregas manuais usam o
preço vigente no cadastro; importadas usam o preço do Excel. Não há nova política
de preços por vigência temporal nem recálculo retroativo.

Odômetro final não pode ser menor que o inicial. KM fica ausente se faltar um dos
dois. Horários podem atravessar meia-noite. Janela histórica não preenche horários
reais. Campos opcionais não têm zero como padrão. Valores negativos são inválidos.

## Indicadores autorizados na etapa 02

Intervalos usam ordenação cronológica no mesmo dia e diferenças estritamente
positivas; a média do período pondera cada intervalo. É uma mudança expressamente
solicitada em relação ao ABS entre linhas consecutivas da planilha. A ordem
importada permanece intacta no banco.

Duração real: fim menos início; se o resultado for negativo, acrescenta 24 horas.
Horários iguais significam duração zero, sem divisão por zero. Só na ausência do
par real se usa janela histórica. Não se estima duração a partir de entregas.
Totais informam horas reais/históricas separadas e cobertura. Se faltar duração
em uma data operacional, a taxa global fica ausente.

Consumo = KM/litros do mesmo conjunto elegível, com litros positivos. O total de
litros do período continua disponível, mas não entra automaticamente no denominador
quando faltam KM. Custos conhecidos e resultado com esses custos são parciais
quando houver campos ausentes. Resultado líquido e margem completos exigem
combustível e outros custos preenchidos em todas as jornadas, com cobertura de
todas as datas operacionais. Zero precisa estar explicitamente cadastrado.

Custo por tentativa usa as tentativas dos dias com custos. Taxas por KM usam
apenas conjuntos comparáveis descritos na interface. A receita de uma data não é
multiplicada pelo número de jornadas dessa data.

Metas usam a versão vigente, identificada na tela; não alteram preço histórico.
Metas integrais não são rateadas em filtros parciais. Projeção é um cenário de
receita média por dia com entregas × quantidade de dias com entregas escolhida;
o padrão de cinco dias não presume uma escala semanal de trabalho.

## Auditoria e pagamentos

Confrontável exige entregas, todos os campos de espelho e ausência de alerta de
duplicidade. Documentos são somados por competência. Mesma referência normalizada
na mesma data, ou conteúdo idêntico sem referência, pede revisão; nada é excluído.
Campos incompletos não viram zero. Diferença = registrado − informado.

Quinzenas são 01–15 e 16–último dia civil. Diferença quinzenal soma somente dias
confrontáveis. Dias sem espelho e com divergências são listados separadamente.
Sem pagamentos, o status é “Sem pagamento registrado”, sem presumir inadimplência.
Pagamentos usam sua competência, não sua data de recebimento, para o vínculo.

Saldo do informado = informado − recebido, somente com conferência completa,
pagamento cadastrado e recorte integral da quinzena. Saldo negativo sinaliza valor
recebido acima do informado. Pagamentos de períodos fora do padrão ficam para
revisão, sem rateio ou atribuição duplicada. O corte diário não subtrai pagamento
integral de uma base parcial.

Espelho não comprova recebimento. Pagamentos usam exclusivamente T–Y da aba da
empresa, quando preenchidos. Fim do período não pode ser anterior ao início.

O importador ignora fórmulas auxiliares e datas isoladas da agenda, mantém zeros
explícitos e rejeita entradas inválidas sem gravar parte do arquivo.

## Relatórios e conservação — etapa 03

Exportações não modificam preços, totais, ausências ou regras de conferência.
Os cinco conjuntos de dados são exportados em transação somente de leitura.
Pagamentos continuam vinculados pela competência sobreposta, sem rateio.
O resumo distingue previsto/informado/recebido e resultado parcial/completo.

XLSX força todo texto como string, sem fórmulas. CSV neutraliza prefixos perigosos
com apóstrofo e usa UTF-8 BOM/ponto e vírgula. Os relatórios não incluem snapshots,
senhas, tokens ou sessões, e não são entrada automática do importador original.

Backup real usa API SQLite, integridade e SHA-256. Não há retenção destrutiva.
Restauração só ocorre com servidor encerrado, cópia isolada testada, preservação do
estado atual e confirmação explícita. Nenhuma restauração real foi executada.

## Resultados finais de entregas — 29/10/2026

Baixas realizadas no card final são conclusões distintas; Insucesso Real significa
sem baixa posterior registrada. Taxa final = conclusões / (conclusões + Insucesso
Real) × 100. Insucesso Total e sucesso por tentativa preservam ocorrências.
População pela primeira tentativa no filtro, resultado pelo histórico disponível,
com corte histórico separado. Ambiguidades ficam visíveis e fora da taxa final.
Não se usa baixa anterior, PK, empate ou hora ausente no mesmo dia para comprovar
recuperação. Preços/receitas permanecem nas datas e registros originais, inclusive
quando há baixas repetidas; nesse caso há alerta, sem correção monetária.
Detalhes e limitações de identidade em `CONCILIACAO_ENTREGAS.md`.

Desde 30/10, os nomes principais são Total de encomendas, Entregas concluídas,
Total com insucesso, Insucessos pendentes, Entregas recuperadas e Taxa de sucesso
final. Total com insucesso conta encomendas distintas; tentativas fracassadas
continuam disponíveis na auditoria. Concluídas já incluem recuperadas, portanto
o gráfico separa concluídas sem insucesso, recuperadas e pendentes.
