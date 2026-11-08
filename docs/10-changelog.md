# Histórico de alterações

## 08/11/2026 — apresentação do repositório e política de versionamento

README reescrito com apresentação, funcionalidades atuais, fórmulas de card/tabelas,
cards financeiros, instalação nova, uso local/LAN/remoto, importação/exportação,
backup/restauração, testes e arquitetura. `.gitignore` ampliado para bancos/cópias/
manifestos, arquivos operacionais, segredos ngrok e artefatos de desenvolvimento,
mantendo fontes, migrations e exemplos públicos. Criado `docs/VERSIONAMENTO.md`.
Índice/guias ajustados para distinguir relatórios privados da documentação no Git.
Revisados arquivos e histórico local; não houve commit, push, remoção do índice,
alteração de histórico ou mudança no banco, aplicação ou implantação.

## 07/11/2026 — cards de faturamento mensal e quinzenal

Card Faturamento renomeado para Faturamento Mensal e acrescido de Faturamento
1ª Quinzena e Faturamento 2ª Quinzena, consecutivos na grade responsiva existente.
1–15 e 16–último dia civil, com preços históricos e totalizador preservados.
Escolha explícita do proprietário: mês completo do filtro quando nele houver
um único mês; histórico/múltiplos meses usam mês vigente em São Paulo. Referência
visível, demais indicadores e tabelas/filtros/exportações iguais. Novo namespace
de apresentação, sem alterar modelo, banco, conciliação ou segurança.
315 Django/41 JavaScript aprovados; inspeção visual física pendente.
Relatório: AJUSTE_CARDS_FATURAMENTO_QUINZENAL.md.

## 31/10/2026 — taxa exclusiva das tabelas

Somente Taxa de Sucesso nas tabelas diária/semanal/mensal passa a usar concluídas
distintas / população distinta iniciada no intervalo, com recuperações até a
referência no histórico completo. Novo adaptador da conciliação existente;
campo separado `taxa_sucesso_tabela`. Preservados cards/fórmula operacional,
demais colunas, layout, calendário, filtros, menu, cadastros, gráficos, exportações,
segurança e dados reais. Backup verificável anterior; 303 Django/41 JavaScript
aprovados. Relatório: AJUSTE_TAXA_SUCESSO_TABELAS.md. Revisão visual pendente.

## 31/10/2026 — reestruturação definitiva do Painel Geral

Sete cards com Faturamento integrado; mês vigente em São Paulo; Menu do Painel
com filtro, exportações e conferência; tabelas diária/semanal/mensal reestruturadas
em 9/12/12 colunas. Semanas domingo–sábado no filtro, tabelas e gráficos. Taxa
operacional B/(B+P) comum e pendências por primeira tentativa com histórico global.
Média por dias com registros, cobertura explícita e consumo por pares comparáveis.
Retirados os blocos Finanças do período e Horas e produtividade; ganho médio e
auditoria detalhada disponíveis na conferência. Sete gráficos existentes mantidos.
Backup verificável anterior, 287 Django/41 JavaScript aprovados, HTTP em banco
novo e conferência SQL do snapshot somente leitura. Não alterados dados reais,
preços, modelos, OAuth/CSRF, inicializadores ou firewall; sem commit/publicação.
Inspeção visual física pendente. Relatório: AJUSTE_LAYOUT_PAINEL_GERAL.md.

## 21/10/2026 — etapa 01

Criado projeto Django local, modelos, migrations, dados iniciais, importação das
quatro abas, interface autenticada, formulários, Admin, testes e documentação.
Importados 169 registros de entrega, um espelho e quatro jornadas. Nenhum pagamento
estava preenchido. Códigos repetidos, ordem, horários, valores e ausências preservados.

Nenhuma etapa posterior, commit, push ou publicação foi executada.

## 21/10/2026 — etapa 02

Adicionados indicadores operacionais e financeiros, filtros globais, metas e
cenários de projeção, horas com origem, custos parciais, consumo comparável e
conferência diária/quinzenal com revisão de documentos. Sete gráficos locais em
SVG, com legendas interativas e tabelas de valores.

Backup seguro do SQLite antes das mudanças. Schema e registros reais conservados;
nenhuma reimportação. Os 45 testes anteriores e 50 novos testes Django passaram,
assim como oito testes JavaScript e verificações HTTP autenticadas em cópia
descartável. Inspeção visual permanece pendente, conforme restrição anterior.

A etapa 03 não foi iniciada. Nenhum commit, push, publicação ou mudança de rede.

## 21/10/2026 — etapa 03

Finalizados recursos técnicos de operação: interface responsiva, menu acessível,
gráficos adaptáveis, inicializador BAT/Python com Waitress/WhiteNoise, exportações
XLSX/CSV, backups verificados e restauração interativa. Regras financeiras, dados,
migrations e testes anteriores foram preservados. README de uso diário e guia rápido
foram criados; o README anterior foi arquivado integralmente como referência.

A rede física estava no perfil Público: não foi alterada e não houve teste em
celular físico. Validação visual, Excel visual e LAN dependem do proprietário.
Nenhum firewall, roteador, serviço permanente, commit ou publicação foi alterado.

## 22/10/2026 — ajuste da inicialização LAN

Mantidos BAT e inicializador Python. Uma única Ethernet/Wi-Fi física, ativa,
com IPv4 privado e perfil Private passa a ser selecionada automaticamente.
Com várias interfaces, há escolha; sem nenhuma ou em falha de consulta, há
explicação e início somente em localhost. Um único Waitress mantém os dois
endereços explícitos, com ALLOWED_HOSTS restrito aos endereços selecionados.

Adicionados testes de seleção, falha de consulta, configuração do inicializador
e duas requisições simultâneas em sockets locais de um Waitress real. Sem novas
dependências, migrations, regras financeiras ou mudanças de firewall/rede.
Resultado e roteiro: `relatorios/AJUSTE_INICIALIZACAO_LAN.md`.

## 22/10/2026 — cadastro de entregas em lote

Adicionada grade acessível pela lista, preservando cadastro individual. Até 500
linhas por lote, Enter/Tab, padrões de data/situação e exceções por linha, colagem
de códigos/TSV com prévia e mapeamento, contadores e rascunho local. Salvamento
autenticado/CSRF com confirmação, validação integral e recibo persistente para
evitar reenvios. Gravação atômica usa o preço vigente e os modelos existentes.

Backup anterior verificado. Migração permite horário vazio sem inventá-lo e cria
a tabela de recibos; as 170 entregas existentes e demais registros de negócio
permanecem idênticos. CSV e apresentação admitem horário não informado. Nenhuma
mudança em rede, inicializador, pagamentos ou fórmulas financeiras. Não há novas
dependências de produção, commits ou publicação. Testes: 160 Django e 32 JavaScript
aprovados; HTTP em cópia descartável com lotes de 50/100. Visual e toque pendentes.
Relatório: `relatorios/MELHORIA_CADASTRO_EM_LOTE.md`.

## 22/10/2026 — acesso remoto com ngrok

Criados BAT e perfil online separados, Waitress apenas em 127.0.0.1:8000, domínio
e e-mail explicitamente autorizados, política Google OAuth com negação de outras
identidades e login Django mantido. Proxy WSGI valida chave efêmera/identidade/host,
descarta headers forjados e sinaliza HTTPS; cookies, CSRF, headers e limites de login
aplicados somente no perfil online. Nenhuma dependência, migration ou cálculo novo.

Backup verificado antes das alterações; 170 entregas e todo o banco permanecem
idênticos. Testes: 191 Django e 32 JavaScript aprovados; 24 respostas HTTP em cópia
isolada, seis HTTPS reais para prova sem SQLite com redirecionamento OAuth. A conta
aceitou a política. Ativação real segue bloqueada até login permitido/negado,
revisão e demais testes manuais. Não há novo túnel ativo ao finalizar. Firewall,
roteador, interfaces e inicializador local não foram alterados. Sem commit ou
publicação do código. Relatório: `relatorios/MELHORIA_ACESSO_NGROK.md`.

## 22/10/2026 — correção do POST de login HTTPS

Perfil online passa de Referrer-Policy no-referrer para same-origin, mantendo
CSRF, OAuth/lista exata, proxy autenticado, cookies seguros e localhost. Diagnóstico
CSRF no console usa apenas categorias e estado técnico sanitizado. Revisão de
segurança 2 invalida a aprovação anterior e requer nova validação/autorização.

Adicionados oito testes e QA de navegador com SQLite novo descartável. Testes:
199 Django, 32 JavaScript e 31 respostas HTTP locais aprovados. Backup prévio
verificado; nenhuma mudança de modelos, cálculos ou dependências. Resultados
externos e instruções: `relatorios/CORRECAO_LOGIN_NGROK.md`. Sem commit/firewall.

Reprodução real confirmou Origin null no POST antigo com HTTPS/identidade válidos.
O navegador validou a correção em banco novo: login, painel, logout/relogin e
outra conta Google negada. Túnel encerrado; autorização para dados reais pendente.

## 23/10/2026 — horário na grade de entregas em lote

Campo Horário passa a usar `type="time"`, com separadores nativos, preenchimento
opcional e precisão de segundos. Coluna ampliada para acomodar o controle.
Horários colados ou restaurados que o navegador não aceita permanecem em texto
para correção, sem descarte silencioso. Backend e regras financeiras preservados.

Validação: 199 testes Django, 32 JavaScript, sintaxe JavaScript e `manage.py check`
aprovados. HTML renderizado confirma o campo opcional com `step="1"`; arquivos
estáticos coletados e conferidos. Conferência visual no navegador fica para o uso
do proprietário. Nenhum servidor ou túnel foi iniciado para esta alteração.

## 29/10/2026 — conciliação, recuperação e Insucesso Real

Serviço de conciliação derivada por código textual e ciclo candidato, preservando
o histórico. Cards distinguem 561 entregas concluídas de 562 ocorrências de baixa,
33 recuperadas e 18 sem baixa posterior no retrato de 619 registros/579 códigos.
Taxa final 96,89%; sucesso por tentativa 90,79% e receita R$ 2.810,00 preservados.
Baixa repetida gera alerta financeiro, sem correção automática.

População pela primeira tentativa no intervalo, com histórico posterior e
fotografia até o fim do período. Ambiguidades de identidade/horário ficam em
revisão fora da taxa. Consulta autenticada e paginada, CSV próprio, resumo XLSX
ampliado nas cinco abas existentes, rótulos operacionais explícitos.

Backup SQLite verificado antes das alterações; sem migration, autenticação,
ngrok, firewall ou regras financeiras novas. Validação: 199 anteriores + 33 novos
= 232 Django, 32 JavaScript, 47 conciliação/exportação repetidos após rótulos,
20 respostas HTTP em banco novo e conferência independente dos períodos reais.
Relatório: `relatorios/MELHORIA_INSUCESSO_REAL.md`. Validação visual pendente.

## 30/10/2026 — dashboard automático por situação real

Seis cards por encomenda substituem a mistura de ocorrências no topo. Auditoria
recolhida conserva tentativas, produtividade, repetições e alertas financeiros;
finanças continuam visíveis. Gráfico de situação usa concluídas sem insucesso,
pendentes e recuperadas, sem sobreposição. Never_cache impede cache HTTP das
páginas de resultado; a conciliação existente segue sendo chamada em cada consulta.

Valores reais: 579 encomendas, 561 concluídas, 51 com insucesso, 18 pendentes,
33 recuperadas, 96,89%. O banco já começou com 618 registros e R$2.805 após
exclusão prévia de uma baixa repetida; esse estado foi preservado. O backup de
619 registros ainda resulta em R$2.810, sem deduplicação monetária pelo código.

Backup prévio verificado; 232 anteriores + 17 novos = 249 Django, 33 JS, 58 focados,
27 respostas HTTP e oito leituras atualizadas aprovadas. Sem migration, alteração
de regras de conciliação/finanças, autenticação, ngrok, rede ou commits.
Relatório: `relatorios/CORRECAO_DASHBOARD_SITUACAO_REAL.md`. Visual físico pendente.

## 31/10/2026 — definições definitivas dos seis indicadores

Aplicadas as definições explícitas do proprietário: total de registros, ocorrências
de baixa e de insucesso nos três primeiros cards; pendentes/recuperadas por
conciliação distinta. Taxa de Sucesso = baixas registradas / (baixas registradas +
pendências distintas) × 100. Bases e referência separadas na interface; cronologia,
possível reutilização, alertas, atualização por consulta e finanças preservados.

Namespace próprio evita alterar totais financeiros e métricas da auditoria.
Arredondamento apenas da nova taxa corrige o formatador que cortava casas:
562/(562+18) aparece como 96,90%. XLSX preserva cinco abas/finanças e distingue
Taxa de Sucesso da taxa por encomenda distinta; CSV permanece igual.

Validado o histórico de referência com 619 registros, sem reinseri-los no banco
atual de 618 registros/R$2.805. Suite: 249 anteriores + 17 novos = 266 Django,
81 focados, 33 JS e 28 respostas HTTP/nove leituras em banco novo aprovados.
Relatório: `relatorios/CORRECAO_DEFINITIVA_INDICADORES.md`. Visual físico pendente.
