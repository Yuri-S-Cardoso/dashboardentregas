# Guia rápido — Conferência de Entregas

**Indicadores:** os três primeiros cards contam todos os registros, baixas e
insucessos do período. Pendentes e recuperadas contam encomendas distintas pela
primeira tentativa no período, consultando baixas posteriores. A Taxa de Sucesso
combina ocorrências de baixa e pendências distintas. Após salvar/editar/excluir, consulte
novamente o painel: os resultados são recalculados automaticamente. “Consultar
encomendas e histórico” abre a auditoria por código/situação e CSV. Receita
continua na data efetiva. Os três últimos cards mostram Faturamento Mensal e das
duas quinzenas, sempre previstos, não recebidos. Usam o mês completo do filtro
quando ele estiver em um único mês; histórico/múltiplos meses usam o mês vigente.
O mês de referência fica visível e os outros indicadores mantêm o filtro aplicado.
“Critérios e alertas da conciliação” expande explicações; a auditoria detalhada
está em Conferência Financeira. [Painel atual](PAINEL_GERAL.md).

1. **Abrir:** dê duplo clique em `Y:\Entregas\Iniciar_Entregas.bat`. Uma única
   Ethernet/Wi-Fi física, ativa, com IPv4 privado e perfil Privado é usada
   automaticamente. Com várias, escolha uma ou 0 para somente computador; sem
   nenhuma, o sistema explica e inicia em localhost. Abra o endereço exibido e
   faça login. Se faltar usuário, siga a seção 3 do README.
2. **Celular:** conecte à mesma rede confiável e use o endereço indicado pelo
   inicializador; computador e celular usam o mesmo servidor. Se não aparecer,
   use o modo computador e confira o README.
   Firewall e perfil de rede só podem ser ajustados manualmente pelo proprietário.
3. **Entregas:** Minhas Entregas → Adicionar Entregas em Lote. Escolha os padrões,
   digite códigos e use Enter; também pode colar códigos ou células do Excel.
   Salvar Todos abre a prévia; confirme para gravar. Horário é opcional. Novo
   registro e Editar continuam disponíveis. [Guia da grade](CADASTRO_EM_LOTE.md).
4. **Espelhos:** registre cada documento e sua competência. **Pagamento recebido**
   é um registro separado, acessível na seção de espelhos e no painel.
5. **Jornadas:** informe horários, KM, litros e custos conhecidos. Não preencha
   ausências com zero. Horas reais têm prioridade sobre a janela histórica.
6. **Conferir:** escolha a quinzena em Conferência Financeira. Sem espelho é
   pendência; sem pagamento cadastrado não comprova inadimplência.
7. **Interpretar:** previsto é receita das baixas; informado vem do espelho;
   recebido vem do pagamento. Resultado parcial não é lucro definitivo.
8. **Filtrar:** Menu do Painel → Filtrar período. Sem seleção explícita, abre
   o mês vigente em São Paulo. Semana: escolha uma data, de domingo a sábado.
   Todo o histórico exige seleção explícita. O menu lembra o filtro na mesma aba.
   Role tabelas lateralmente no celular; todas as colunas continuam disponíveis.
9. **Exportar:** Painel/Conferência → Exportar relatórios → período ou histórico.
   Prefira XLSX para códigos com zeros à esquerda. CSV usa ponto e vírgula.
10. **Backup:** no PowerShell da pasta, execute
    `& '.\.venv\Scripts\python.exe' manage.py backup_local`.
    Confira a mensagem de integridade, tamanho e SHA-256. Não apague cópias anteriores.
11. **Restaurar:** primeiro encerre o servidor e siga a seção 13 do README.
    A restauração cria cópia de segurança e pede **RESTAURAR** antes de substituir.
12. **Encerrar:** Ctrl+C na janela do servidor. Fechar só o navegador não encerra.
13. **Acesso remoto opcional:** use o inicializador Online somente após conferir
    OAuth permitido/negado e aprovar a configuração. O inicializador local continua
    independente. Leia [Acesso ngrok](ACESSO_NGROK.md) antes de ativar dados reais.

**Segurança:** HTTP não criptografa dados; use apenas rede privada confiável.
Não abra portas no roteador, não use túneis e não desative o firewall.
Nunca trate XLSX/CSV como backup do banco ou entrada automática do importador.

**Conferência inicial esperada:** 169 tentativas, 154 baixas, 15 insucessos,
R$ 770,00 previstos. 15/10 conferido; segunda quinzena R$ 610,00 aguardando espelho.
