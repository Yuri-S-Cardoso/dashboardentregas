# Conferência de Entregas — uso diário no Windows

O sistema funciona no computador e, havendo uma rede privada confiável elegível, no
celular conectado à mesma rede. Os dados ficam no próprio computador. Não há
publicação na internet no modo local. [Guia rápido](docs/GUIA_RAPIDO.md).

O modo remoto opcional tem inicializador separado, **Iniciar_Entregas_Online.bat**,
com OAuth por e-mail e login Django. Está configurado, com ativação dos dados reais
pendente de testes interativos e revisão. [Guia do acesso ngrok](docs/ACESSO_NGROK.md).

## 1. Iniciar com duplo clique

Abra **`Y:\Entregas\Iniciar_Entregas.bat`**. Mantenha a janela aberta durante o uso.
O inicializador confere o ambiente, o banco, a porta e os arquivos de aparência.
Se houver **uma** Ethernet ou Wi-Fi física, ativa, com IPv4 privado e perfil
**Privado**, ela será selecionada automaticamente. Se houver **várias**, escolha
o número da conexão usada pelo celular, ou **0** para somente computador.
Sem conexão elegível, o sistema explica o motivo e inicia somente em localhost.
VPNs, interfaces virtuais, desconectadas e redes Públicas não são selecionadas.

Abra o endereço mostrado na janela, normalmente **http://127.0.0.1:8000/**.
Se houver erro, a janela mostra a mensagem e permanece aberta para leitura.
Não é necessário executar como administrador. Não há serviço permanente ou
inicialização automática com o Windows.

## 2. Encerrar

Na janela do servidor, pressione **Ctrl+C** e aguarde a mensagem de encerramento.
Se o Windows perguntar se deseja encerrar o arquivo em lotes, confirme. Fechar a
aba do navegador não encerra o servidor.

## 3. Criar o primeiro usuário

Nenhuma senha padrão foi criada. Abra PowerShell na pasta do projeto e execute:

```powershell
Set-Location 'Y:\Entregas'
& '.\.venv\Scripts\python.exe' manage.py createsuperuser
```

Escolha nome de usuário e senha. A senha não aparece enquanto é digitada.
Use esse acesso na tela de login. O botão **Sair** encerra sua sessão.

## 4. Encontrar o endereço para o celular

Ao iniciar, a única conexão elegível é selecionada automaticamente; com várias,
escolha uma. A janela mostrará dois endereços atendidos pelo **mesmo Waitress**:
um para o computador e outro para o celular, por exemplo
`http://192.168.0.100:8000/`. Use o endereço realmente exibido; ele pode mudar
quando o roteador distribuir outro IP. Computador e celular devem estar na mesma
rede doméstica/confiável, mesmo se o computador estiver ligado por cabo.

## 5. Rede atualmente identificada

Na verificação desta entrega, Ethernet tinha IPv4 privado, mas o perfil do Windows
estava **Público**. A outra conexão ativa era VPN. Por segurança, nenhuma era
elegível para o celular. O modo somente computador foi validado.

Se for de fato sua rede confiável, o proprietário poderá abrir as Configurações
do Windows, em Rede e Internet → propriedades da conexão, e escolher **Privada**.
Depois, reinicie o inicializador; uma única interface elegível será usada
automaticamente. Essa alteração
não foi feita automaticamente. Não mude o perfil em redes de terceiros.

## 6. Se o celular não conseguir acessar

- Confirme que a janela do servidor está aberta e mostra um endereço para celular.
- Use esse endereço completo, incluindo `http://` e a porta `:8000`.
- Confirme que o celular está no mesmo Wi-Fi/rede do computador; redes de
  convidados podem impedir comunicação entre dispositivos.
- Confira o perfil **Privado** da conexão física e se o IP não mudou.
- VPNs, isolamento do roteador e regras locais podem impedir acesso. Não use
  túnel, não abra portas no roteador e não desative o firewall para resolver.

Se for necessária uma exceção no Windows Defender Firewall, o proprietário deverá
decidir aprová-la e executá-la manualmente. O exemplo abaixo é apenas instrução;
**não foi executado**. Substitua o IP/interface/porta pelos valores selecionados e
abra PowerShell como administrador somente para essa ação manual:

```powershell
New-NetFirewallRule -DisplayName 'Entregas - rede privada' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 -LocalAddress 192.168.0.100 -RemoteAddress LocalSubnet -Profile Private -InterfaceAlias 'Ethernet' -Program 'Y:\Entregas\.venv\Scripts\python.exe'
```

A regra limita perfil, endereço, porta, interface, programa e sub-rede local.
Não habilite acesso no perfil Público. Se o computador for administrado por outra
pessoa, siga a política do responsável em vez de contornar restrições.

## 7. Cadastrar entregas

Para o uso diário, abra **Minhas Entregas → Adicionar Entregas em Lote**. Escolha a
data e a situação padrão, digite os códigos usando Enter para avançar, ou cole uma
lista/intervalo de células do Excel. Use **Salvar Todos**, confira a prévia e
clique em **Confirmar e salvar todos**. A grade começa com 20 linhas e aceita até
500 por lote. Códigos repetidos e zeros à esquerda são preservados.

O rascunho fica apenas neste navegador e é apagado após o sucesso. **Limpar** pede
confirmação. [Guia completo da grade e da colagem](docs/CADASTRO_EM_LOTE.md).

Para um lançamento isolado, use **Novo registro**. Preencha código, data e situação;
o horário é opcional e não será inventado quando estiver vazio.
**Baixa realizada** gera o valor por baixa preservado; **Insucesso** não gera receita.
Códigos repetidos são permitidos. Para corrigir, use **Editar**. **Excluir** abre
uma confirmação e remove somente aquele registro após confirmar.

Os filtros da lista são por data e situação. No celular, role a tabela para os
lados para ver todas as colunas. Nenhuma coluna financeira foi escondida.

## 8. Registrar espelhos e pagamentos

Em **Espelho da Empresa**, cadastre competência, quantidades, valor, documento e
demais campos disponíveis. Mais de um documento por competência é permitido.
O link **Pagamentos recebidos** registra o valor efetivamente recebido, comprovante
e início/fim da quinzena. Um espelho não comprova pagamento.

Em **Jornada e Custos**, informe apenas o que conhece: horários reais, odômetros,
litros e despesas. Campo vazio significa **não informado**; use zero somente
quando esse for o valor real. Janela histórica não substitui o par real preenchido.

## 9. Conferir quinzenas

Abra **Conferência Financeira** e selecione mês, ano e quinzena: 01–15 ou 16–fim do
mês. Confira os documentos, diferenças e datas pendentes. Em 15/10/2026, os dados
históricos conferem com diferença zero. Na segunda quinzena, R$ 610,00 estão
**aguardando espelho**, sem perda confirmada.

Um alerta de duplicidade pede revisão; não exclui documentos sozinho. **Sem
pagamento registrado** não comprova inadimplência. Saldo só aparece com dados
suficientes e quinzena integral; um filtro diário não rateia pagamento.

## 10. Interpretar os indicadores

- **Previsto:** receita das baixas, pelos preços históricos.
- **Informado:** valores dos espelhos da empresa.
- **Recebido:** pagamentos efetivamente cadastrados.
- **Parcial:** há valores conhecidos, mas faltam informações necessárias.
- **Não informado:** faltam dados; não equivale a zero.

Horas reais e históricas são identificadas separadamente. Consumo usa somente KM
e litros comparáveis. Resultado com custos conhecidos é parcial quando há lacunas;
o líquido completo fica ausente. Metas usam a versão vigente sem alterar preços
anteriores. Projeção é um cenário baseado nos dias com entregas, sem garantia.

O painel e a conferência compartilham filtros. O menu lembra os filtros durante
a navegação na mesma aba, quando o navegador permite armazenamento da sessão.
Use **Todo o histórico** para limpar. As legendas dos sete gráficos alternam séries;
**Ver tabela de valores** mantém os valores disponíveis, inclusive sem JavaScript.

## 11. Exportar

No Painel ou na Conferência, abra **Exportar relatórios**. Escolha Excel ou CSV do
período filtrado, ou histórico completo. Faça login antes de baixar.

O Excel contém cinco abas: entregas, espelhos, jornadas/custos, pagamentos e resumo.
Conserva códigos textuais, datas, horários, campos vazios e formatos financeiros.
O CSV contém as cinco colunas de entregas, usa UTF-8 com BOM e ponto e vírgula.
Textos potencialmente interpretados como fórmulas são protegidos. No CSV, essa
proteção pode acrescentar apóstrofo; o Excel também pode inferir números ao abrir.
Para preservar automaticamente zeros à esquerda, prefira XLSX ou importe a coluna
Código do CSV como **Texto**. Caracteres XML não suportados são representados por
`�`; campos acima de 32.767 caracteres impedem a exportação XLSX, sem alterar dados.

Exportações são relatórios de saída, **não são backups** e **não são automaticamente
compatíveis com o importador original**. Não contêm senhas, tokens ou snapshots
técnicos privados. Guarde os downloads como documentos privados.

## 12. Fazer backup

Pode ser feito com o sistema em uso. No PowerShell:

```powershell
Set-Location 'Y:\Entregas'
& '.\.venv\Scripts\python.exe' manage.py backup_local
```

O comando mostra o arquivo em `.local/backups/`, tamanho e SHA-256 após verificar
a integridade. Um arquivo JSON adjacente guarda esses dados. Usa a API segura do
SQLite, e não uma cópia direta do banco aberto. Backups anteriores não são apagados.

Retenção conservadora: mantenha as cópias das etapas e várias gerações recentes;
copie backups verificados e seus JSONs para outra unidade. Confira o espaço livre
periodicamente. O comando exige pelo menos duas vezes o tamanho do banco e 10 MB
livres. Qualquer descarte de cópias antigas deve ser uma decisão manual, após
confirmar outra cópia íntegra. Preserve também `.local/secret_key` separadamente,
com acesso restrito, para manter as sessões; o banco pode funcionar com nova chave,
mas os usuários precisarão entrar novamente.

## 13. Recuperar o banco com segurança

**Encerre o servidor com Ctrl+C e feche outros acessos ao SQLite.** Escolha a cópia
pelo nome, data e tamanho na pasta `.local/backups/`. Não renomeie o arquivo JSON
separadamente. Execute, substituindo o nome pelo backup selecionado:

```powershell
& '.\.venv\Scripts\python.exe' manage.py restaurar_backup '.local\backups\NOME_DO_BACKUP.sqlite3'
```

O comando verifica integridade, tamanho/hash do JSON quando disponível e tabelas
do sistema. Abre uma cópia isolada e cria outro backup do estado atual. Mostra os
caminhos antes de pedir que você digite exatamente **RESTAURAR**. Qualquer outra
resposta cancela a substituição. Não há opção de confirmação automática.

O inicializador e a restauração usam uma trava para impedir operação simultânea.
Se aparecer aviso de arquivos de transação, feche todos os acessos e procure ajuda;
**não apague arquivos `-wal`, `-shm` ou `-journal` manualmente**. Ao concluir,
inicie o sistema e confira os registros. Nenhuma restauração foi feita no banco
real durante esta entrega; a recuperação foi testada em ambiente isolado.

## 14. Atualizar dependências sem perder dados

Encerre o servidor e faça backup antes de atualizar. Não apague `db.sqlite3`,
`.local/`, planilha ou relatórios. Para instalar as versões fixadas desta entrega:

```powershell
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
& '.\.venv\Scripts\python.exe' manage.py check
& '.\.venv\Scripts\python.exe' manage.py migrate --check
& '.\.venv\Scripts\python.exe' manage.py collectstatic --noinput
```

Se alguma atualização futura exigir migration, revise as instruções dessa versão
e mantenha o backup antes de executá-la. Esta etapa não alterou schema nem exigiu
nova migration. Não faça reimportação ou reinicialização para atualizar aparência.

## 15. Segurança e limitações

HTTP **não criptografa o tráfego**, inclusive o login. Use somente rede privada
confiável. Não abra o sistema à internet, não configure redirecionamento de portas
ou túneis, não use curingas nos hosts e não desative o firewall. O servidor diário
usa Waitress, WhiteNoise e DEBUG=False. Não usa `runserver --insecure`.

Testes automatizados e HTTP foram executados. A inspeção visual em 360, 390, 768 px
e desktop, a abertura visual dos relatórios no Excel e o acesso em celular físico
ficam **pendentes da validação manual pelo proprietário**. O bloqueio anterior do
navegador não foi repetido nem contornado.

## Referência técnica

Inicialização pelo terminal: `& '.\.venv\Scripts\python.exe' scripts/iniciar_sistema.py`.
Somente computador: acrescente `--local`. Verificação sem servidor: `--local --verificar`.
Outra porta: `--porta 8001`. Um `--ip` só é aceito se corresponder à interface física
elegível selecionada explicitamente. O inicializador coleta estáticos quando preciso.

Testes: `manage.py test --verbosity 2` e `node --test tests/test_graficos.cjs tests/test_mobile.cjs`.
Node é apenas ferramenta de teste. [Documentação](docs/00-indice.md),
[referência histórica das etapas anteriores](docs/REFERENCIA_ETAPAS_01_02.md) e
relatórios em `relatorios/ETAPA_01_RELATORIO.md`, `ETAPA_02_RELATORIO.md` e
`ETAPA_03_RELATORIO.md`. O diretório não contém repositório Git; não houve commit
ou publicação. A aceitação definitiva depende da revisão e validação do proprietário.
