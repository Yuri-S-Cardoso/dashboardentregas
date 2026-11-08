# Visão geral

## Painel vigente — 07/11/2026

O painel abre no mês corrente de São Paulo, com nove cards, incluindo Faturamento
Mensal e as duas quinzenas, usando o mês completo escolhido ou o vigente quando
o filtro atravessa meses/histórico. Mantém
menu sobreposto e tabelas por dia, semana domingo–sábado e mês. O card preserva
a taxa operacional; só as tabelas usam a conclusão da população distinta iniciada
no período. Recuperações usam o histórico completo sem mover
receita nem regravar entregas. [Guia atual](PAINEL_GERAL.md). Os textos das etapas
abaixo permanecem como histórico do projeto.

Etapa 01 de um sistema local, em Django 5.2 LTS e Python 3.13, para preservar os
registros da planilha de entregas e permitir cadastros básicos autenticados.
SQLite, HTML e CSS; sem Docker, APIs pagas, telemetria ou serviços externos.

Há um acervo compartilhado pelos operadores autenticados. O banco inicial contém
169 entregas, um espelho e quatro jornadas. Não existem pagamentos preenchidos na
planilha. A inicialização, a criação de usuário e o acesso pela LAN estão no README.

Na etapa 01, auditoria e gráficos ficaram reservados para autorização posterior.
A etapa 02 agora implementa indicadores, filtros globais, metas, projeções,
conciliação por competência/quinzena e gráficos locais. O refinamento mobile
completo permanece reservado à etapa 03, ainda não iniciada.

## Finalização — etapa 03

Agora estão disponíveis apresentação responsiva, menu móvel, gráficos adaptáveis,
inicialização por duplo clique com Waitress/WhiteNoise, exportações XLSX/CSV e
comandos de backup e restauração interativa. Dados e regras financeiras foram
preservados. A aceitação definitiva depende da inspeção visual e do celular físico.
O histórico acima descreve o estado das etapas anteriores.

Desde 29/10/2026, o painel também concilia resultados por código/ciclo candidato:
conclusões distintas, recuperações, Insucesso Real e taxa final. Métricas por
tentativa e finanças continuam separadas, sem alteração dos registros. A consulta
autenticada e suas limitações de identidade estão em `CONCILIACAO_ENTREGAS.md`.

Em 30/10/2026 o painel foi reorganizado para seis resultados por encomenda, com
atualização na próxima consulta após cadastro, lote, edição ou exclusão. Ocorrências
ficam em auditoria recolhida; finanças continuam visíveis. O gráfico de situação
usa categorias exclusivas e as páginas de resultado impedem cache HTTP.

Em 31/10/2026, por definição explícita do proprietário, os três primeiros cards
passam a contar todos os registros, baixas e insucessos do período. Pendentes e
recuperadas permanecem conciliados por encomenda. A Taxa de Sucesso combina
ocorrências de baixa e pendências distintas; a auditoria conserva as métricas por
encomenda única, identificadas separadamente.
