# Validação manual pelo proprietário

## Painel Geral reestruturado — 31/10/2026

Roteiro de inspeção visual ainda pendente, sem gravar dados fictícios no banco:

1. Reinicie pelo inicializador já utilizado, atualize com Ctrl+F5 e abra `/` sem
   query. Deve selecionar o mês vigente de São Paulo, nunca histórico automático.
2. Confira sete cards, Faturamento em linha própria e ausência dos blocos
   Finanças do período e Horas e produtividade; Ganho médio fica na conferência.
3. Em Menu do Painel, teste mouse/toque, Enter/Espaço, Tab, Escape, Fechar menu
   e clique fora. A página não deve deslocar ao abrir; o menu tem rolagem própria.
4. Selecione 29/10/2026 no filtro semanal: 25/10–31/10; depois 01/11/2026:
   01/11–07/11. Links para conferência e downloads devem preservar a seleção.
5. Confira tabelas na ordem dia/semana/mês, com 9/12/12 colunas. Em 360/390 px,
   role somente a tabela lateralmente e confira todas as colunas e notas Parcial.
6. Inspecione também 768 px e desktop, zoom 200%, foco visível e os sete gráficos.
7. Exportação do período deve coincidir com o filtro; histórico completo é
   explícito. Não é necessário criar nem alterar entregas para testar o visual.

Os roteiros antigos abaixo descrevem versões anteriores. Regras atuais em
[PAINEL_GERAL.md](PAINEL_GERAL.md).

Este roteiro ainda não foi aprovado em um navegador/dispositivo físico pelo agente.
Os testes automatizados não substituem sua conferência visual.

| Tela | 360 px | 390 px | 768 px | Desktop |
| --- | --- | --- | --- | --- |
| Login, mensagens e erros | Pendente | Pendente | Pendente | Pendente |
| Menu, foco e logout | Pendente | Pendente | Pendente | Pendente |
| Painel, filtros e cards | Pendente | Pendente | Pendente | Pendente |
| Entregas e formulários | Pendente | Pendente | Pendente | Pendente |
| Espelhos e pagamentos | Pendente | Pendente | Pendente | Pendente |
| Conferência financeira | Pendente | Pendente | Pendente | Pendente |
| Jornadas e configurações | Pendente | Pendente | Pendente | Pendente |
| Sete gráficos e tabelas | Pendente | Pendente | Pendente | Pendente |

1. Inicie por duplo clique; confira endereço e entre com seu usuário.
2. No celular, confirme menu, área de toque, teclado e campos sem zoom involuntário.
3. Confira foco por teclado no computador e fechamento do menu com Escape.
4. Role as tabelas para os lados; todas as colunas financeiras devem estar acessíveis.
   A página inteira não deve exigir rolagem lateral.
5. Aplique filtros e navegue pelo menu; ao voltar, o recorte deve permanecer.
6. Compare o histórico: 169 tentativas, 154 baixas, 15 insucessos, R$ 770,00.
   15/10 deve conferir; R$ 610,00 da segunda quinzena aguardam espelho.
7. Veja os rótulos de ausências, origem de horas e custos/resultados parciais.
8. Alterne as sete legendas de gráficos e abra as tabelas auxiliares.
9. Em uma conta de teste/cópia do banco, exercite cadastro, edição e confirmação de
   exclusão, espelhos, pagamentos, jornadas e configurações. Não é necessário
   alterar dados históricos reais apenas para validar aparência.
10. Baixe XLSX/CSV completo e filtrado. Abra-os no Excel e confira cinco abas,
    datas, códigos textuais, totais e acentos. XLSX é recomendado para zeros à esquerda.
11. Teste acesso em celular físico somente após confirmar rede privada confiável e
    autorizar manualmente eventual regra de firewall limitada, conforme README.
12. Confirme Ctrl+C, backup e verificação do arquivo. Não restaure sobre dados reais
    só para testar; o roteiro técnico já exercitou recuperação em banco isolado.

Registre data, navegador e aparelho usados, problemas observados e aprovação.
HTTP não criptografa dados. Não exponha o sistema na internet para fazer esses testes.

## Conciliação — validação visual pendente (29/10/2026)

Após reiniciar pelo inicializador habitual e atualizar a página, conferir no
computador e no celular: cards, explicação das duas populações, data de referência,
consulta de recuperadas/Insucesso Real, paginação e rolagem lateral da tabela.
No retrato do backup de 29/10: 579 identificadas, 561 concluídas, 33 recuperadas,
18 sem baixa posterior, sucesso final 96,89%; receita preservada R$ 2.810,00.
Filtrar 22/10 deve mostrar recuperações posteriores sem antecipar suas receitas.
Conferir o alerta do código 3831680909 e os downloads. Não alterar registros reais
apenas para testar. Números podem mudar com novos cadastros legítimos.

## Dashboard por situação real — visual pendente (30/10/2026)

Reinicie pelo inicializador habitual e atualize com Ctrl+F5. Conferir desktop e
celular: seis cards, explicação das baixas posteriores, finanças visíveis,
expansão da auditoria, tabela e gráfico com três cores/legendas. Recuperadas são
parte das concluídas; não somar categorias sobrepostas. Conferir a seção
“Necessita revisão” somente em uma cópia de testes com histórico ambíguo.
O retrato atual tem 579/561/51/18/33 e 96,89%; são 618 registros e R$2.805,
pois a baixa repetida foi excluída antes desta correção. Não restaurar R$2.810
artificialmente. Para testar novas operações, use banco descartável e o roteiro
HTTP documentado; não criar dados fictícios no banco real.

## Definições definitivas — visual pendente (31/10/2026)

Após reiniciar e atualizar a página, conferir os seis nomes, a distinção entre
registros e encomendas conciliadas, referência e casas decimais da Taxa de Sucesso.
No banco atual capturado antes da correção: 618 registros, 561 baixas, 57 insucessos,
18 pendentes, 33 recuperadas, taxa 96,89% e R$2.805. No cenário de referência com
619/562/57/18/33, a taxa é 96,90%; esse cenário foi validado em teste e backup
anterior somente leitura, sem reinserção de registros no banco real.
Conferir desktop/celular, filtros, gráfico de conciliação com sua base própria e
XLSX com os dois percentuais identificados. Não usar a antiga relação de total
único como regra dos três primeiros cards. Novas operações somente em banco de teste.
