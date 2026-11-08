# Interface

O Painel Geral abre no mês vigente de America/Sao_Paulo e destaca nove cards:
Total de encomendas (registros), Entregas
concluídas (ocorrências de baixa), Total com insucesso (ocorrências de insucesso),
Insucessos pendentes (distintas), Entregas recuperadas (distintas), Taxa de Sucesso
e três cards de receita prevista: Faturamento Mensal, Faturamento 1ª Quinzena
e Faturamento 2ª Quinzena. Estes mostram o mês completo do filtro quando ele
estiver num único mês; no histórico/múltiplos meses, o mês vigente. Referência
e limites civis aparecem nos cards. Não representam pagamento recebido.
A taxa usa baixas registradas / (baixas registradas + pendências distintas), com
duas casas arredondadas. Referência e diferenças entre as populações são explícitas.
Somente a coluna Taxa de Sucesso das tabelas dia/semana/mês usa conclusão das
encomendas distintas iniciadas no período, incluindo recuperações posteriores.
O card mantém sua fórmula operacional; as demais colunas e o layout estão iguais.
Taxa por tentativa e auditoria detalhada ficam na Conferência Financeira; critérios
e alertas continuam recolhidos no painel. Casos de identidade/cronologia ambígua mostram “Necessita revisão”
separadamente dos totais conciliados, sem classificação arbitrária. Os registros
permanecem nos três primeiros cards e suas baixas no numerador da taxa mista.
Referência e baixas posteriores ao período são informadas acima dos cards.
A consulta `/conciliacao/` permite filtrar códigos/situação, paginar e baixar CSV.
Tabela com foco e rolagem lateral reutiliza o layout responsivo, sem dependências.

O gráfico principal usa concluídas sem insucesso, pendentes e recuperadas, com
três cores e legendas independentes. Mostra o resultado atual por data da primeira
tentativa, com base explicitamente diferente dos três primeiros cards.
Receitas continuam por data efetiva. Grade principal: três colunas no
desktop/tablet e duas no celular. Os três cards de faturamento são consecutivos,
na mesma linha quando houver espaço, com quebra na grade móvel. O antigo
span de largura inteira do card único foi removido.
Menu do Painel reúne filtro, exportações e Conferência Financeira em popover
com posição fixa, teclado, Escape, clique fora e fechamento ao sair com Tab.
Details nativo funciona sem JavaScript. Tabelas diária (9 colunas), semanal e
mensal (12) precedem os gráficos. Semana e filtro vão de domingo a sábado.
Os blocos Finanças do período e Horas e produtividade foram removidos. Metas
saem das três tabelas; os sete gráficos já existentes são mantidos. Regras e
comportamento detalhados em [PAINEL_GERAL.md](PAINEL_GERAL.md).

Na grade de entregas em lote, Horário usa `input type="time"`, com separadores e
seletor nativos, mantendo o preenchimento opcional e a precisão de segundos.
Horários importados incompatíveis permanecem como texto para correção, sem perda.

Menu: Painel Geral, Minhas Entregas, Espelho da Empresa, Jornada e Custos,
Configurações; Administração para usuários de equipe. Pagamentos são acessíveis
pelo Painel e pela seção de espelhos.

Login usa autenticação Django. Logout é um formulário POST com CSRF. Exclusão de
entrega exige abrir a confirmação e enviar POST. Listas têm 50 registros por página.
Filtros de entrega preservam data e situação na paginação e exibem erros de entrada.

Formulários aceitam datas do seletor HTML e decimais brasileiros. Moeda usa R$ e
vírgula decimal. Campos ausentes aparecem como “Não informado”. O layout usa CSS
local e sem imagens externas. Na etapa 01 não existiam gráficos ou JavaScript.

Na etapa 02, o menu ganhou Conferência Financeira. Painel e conferência compartilham
filtros, com links que preservam os parâmetros. Cards e tabelas identificam origem
das horas, cobertura, custos parciais, bases dos índices e metodologia da projeção.

Sete gráficos SVG locais possuem legendas para alternar séries e tabelas de valores
renderizadas no servidor. Ausência não vira barra de zero. A única interatividade
adicionada é JavaScript puro, local; não exige CDN ou conexão externa. O layout
mantém a base anterior; otimização mobile completa não foi iniciada.

## Apresentação da etapa 03

O estado acima descreve a etapa 02. Agora a camada responsiva cobre 360/390 px,
tablet 768 px e desktop. O menu compacto tem botão, aria-expanded e fechamento
por Escape. Sem JavaScript, o menu permanece visível. Campos usam fonte de 16 px,
controles têm área de toque mínima de 44 px e foco visível. Dados parciais e
ausentes não são escondidos. Tabelas são regiões de rolagem horizontal, sem rolagem
obrigatória da página inteira. SVG reorganiza rótulos e barras conforme a largura;
legendas e tabelas de valores permanecem disponíveis.

Filtros permitidos são lembrados em sessionStorage apenas na aba; não se guardam
tokens. O menu continua funcionando quando o armazenamento é bloqueado.
Painel e auditoria oferecem downloads completos e filtrados em sessão autenticada.
Inspeção visual e teste em dispositivo físico permanecem pendentes de validação
manual; não se simulou aprovação por testes de código.

## Grade de entregas

Minhas Entregas oferece Adicionar Entregas em Lote e mantém Novo registro/Editar.
Grade começa com 20 linhas, aceita até 500 e permite Enter no código, Tab nos
campos, colagem com prévia e mapeamento, data individual recolhida e horário vazio.
Salvar Todos abre prévia no servidor; a confirmação grava. Erros têm número da
linha, descrição por campo e foco no resumo. Limpar exige confirmação. Rascunho
local usa somente os campos da tela e é removido ao salvar o lote correspondente.
No celular, linhas viram blocos, com controles de 44 px ou mais e barra inferior
para salvar. Visual, teclado móvel e desempenho percebido exigem teste manual.

## Acesso remoto

Após validação/aprovação, o domínio online pede Google OAuth apenas aos e-mails
autorizados e depois mantém a tela de login Django existente. Dados, formulários
e navegação não mudaram. Excesso de tentativas de login/Admin no perfil remoto
recebe 429 com orientação para aguardar. O modo de prova exibe somente uma mensagem,
sem usar nenhuma tela ou registro real. Roteiro: `ACESSO_NGROK.md`.
