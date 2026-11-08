# Acesso remoto com ngrok

## Uso a partir de um clone

O repositório inclui somente `config/ngrok_online.example.json`, com campos vazios.
Cada instalação precisa preparar sua própria configuração privada, agente e
validação. `.local/`, aprovações e relatórios da instalação original não acompanham
o Git. As observações de “Estado entregue” abaixo registram o histórico daquela
instalação; não significam que um clone novo já tenha acesso remoto autorizado.
Scripts de prova citados em `relatorios/` são evidências locais privadas. A prova
textual do inicializador e os testes de segurança em `tests/` estão versionados.

O modo local mantém `Iniciar_Entregas.bat`, suas configurações e o acesso LAN
anterior. O modo remoto usa **Iniciar_Entregas_Online.bat**, com Waitress somente
em `127.0.0.1:8000` e um túnel HTTPS, sem regra de firewall, roteador ou serviço
Windows. Use apenas um inicializador por vez.

## Estado entregue

**Revisão de segurança 2 — correção do login HTTPS:** o perfil usa agora
`Referrer-Policy: same-origin`. A aprovação anterior foi invalidada; revise
`relatorios/CORRECAO_LOGIN_NGROK.md` e valide novamente antes de autorizar dados
reais. Identificadores da revisão 1 não aprovam a configuração corrigida.

A configuração privada `.local/ngrok_online.json` já contém o domínio e o único
e-mail informados pelo proprietário. A lista é exata, sem liberar o domínio Gmail
inteiro. A política exige Google OAuth antes de qualquer rota e continua exigindo
o login/senha Django para os registros.

O agente aceitou a política no endpoint de prova e seis requisições HTTPS anônimas
foram redirecionadas ao OAuth. A validação posterior do Google está registrada em
`relatorios/VALIDACAO_FINAL_NGROK.md`. A correção de login da revisão 2 também foi
validada com formulário Django no navegador real, incluindo logout/relogin e outra
conta Google negada, em banco novo descartável. **A ativação dos dados reais permanece
bloqueada** até a nova autorização do proprietário após revisar o relatório de correção.

Não inclua authtoken, senha ou segredo no arquivo do projeto. O authtoken continua
na configuração própria do agente ngrok; este sistema apenas verifica sua presença.

## Conferir sem abrir túnel

No PowerShell em `Y:\Entregas`:

```powershell
& '.\Iniciar_Entregas_Online.bat' --verificar
```

Confere Python/.venv, banco existente e íntegro, versão/configuração do ngrok,
domínio, lista e opções do agente. Exibe o identificador da configuração para a
revisão. Não inicia servidor ou túnel e não comprova login Google.

## Validar a proteção externa sem dados reais

Encerre o servidor local antes, se estiver aberto. Execute:

```powershell
& '.\Iniciar_Entregas_Online.bat' --testar-protecao
```

Esse modo serve **somente uma mensagem de prova**, sem carregar Django ou abrir
SQLite. Não são exibidas entregas, relatórios, usuários ou credenciais. Para
limitar o ensaio a dois minutos, acrescente `--duracao-teste 120`.

1. No celular, desligue o Wi-Fi, use dados móveis e abra o HTTPS mostrado.
2. Em janela privada sem sessão Google/ngrok, confirme que aparece a autenticação
   Google antes da mensagem de prova. Possuir somente o link não deve dar acesso.
3. Entre com o e-mail autorizado: a mensagem de validação deve aparecer.
4. Em outra janela privada, com cookies separados, entre com outra conta Google
   que não esteja na lista: deve ser negada, sem alcançar a mensagem.
5. Confira domínio e certificado HTTPS, inclusive ao abrir diretamente caminhos
   como `/entregas/lote/` e `/exportar/csv/`. Nada real existe no modo de prova.
6. Confira no painel da conta ngrok a política ativa, cotas/plano e que **Full
   Capture está desativado**. O agente já usa inspeção desativada, sem UI/API 4040
   e sem logs persistentes do tráfego. Não habilite captura de corpos.
7. Confira os destinos de outros túneis/proxies do computador. Foi encontrado outro
   processo ngrok, preservado, cuja API local não respondeu; seus destinos não
   puderam ser confirmados. Nenhum outro túnel deve encaminhar para a porta 8000
   fora desta política. Um proxy separado que altere Host para localhost poderia
   alcançar a entrada local sem o OAuth desta configuração, ainda exigindo Django.
8. Anote os resultados sem guardar senhas, cookies, URLs OAuth com state ou tokens.
   Ctrl+C encerra servidor e túnel de prova.

Se a conta rejeitar OAuth, a lista ou as opções, mantenha a ativação bloqueada.
Não remova a política e não execute `ngrok http 8000` como alternativa. Será preciso
avaliar uma proteção equivalente ou um plano compatível antes de servir dados.

## Aprovar e usar os dados reais

Somente após revisar os relatórios de acesso e `relatorios/CORRECAO_LOGIN_NGROK.md`,
concluir os testes da configuração atual e autorizar a nova revisão, o proprietário
poderá editar `.local/ngrok_online.json`:

- `revisao_aprovada`: mudar para `true`.
- `validacao_externa_sha256`: preencher com o identificador exibido por
  `--verificar`, referente ao domínio/e-mails/política/versão efetivamente testados.

Esse identificador é uma referência de revisão, não uma credencial. Não preencha
para contornar teste pendente. Alterar domínio, lista, versão de política ou versão
do ngrok invalida a aprovação e exige nova validação.

Depois, dê duplo clique em **Iniciar_Entregas_Online.bat**. A janela mostra:

- Computador: `http://127.0.0.1:8000/`.
- Celular remoto: o domínio HTTPS exato cadastrado.

No celular, faça Google OAuth e depois o login Django. Não basta estar logado no
Google. No computador, o endereço local continua utilizável mesmo se ngrok cair;
as sessões local/online usam cookies separados por host e das sessões do modo local
anterior. Encerrar Django pelo botão Sair não encerra a sessão OAuth Google/ngrok.
Use janela privada ou revogação de sessão no provedor/ngrok quando necessário.

O computador precisa permanecer ligado, com o servidor aberto e internet. Ctrl+C
encerra apenas o agente criado por esse inicializador e seu Waitress; não encerra
outros processos ngrok. Ao voltar ao modo local, use o BAT original normalmente.

## Configuração e limites

O perfil `config.settings_online` usa hosts localhost/127.0.0.1/domínio exato,
origem CSRF HTTPS exata, DEBUG=False e cookies Secure/HttpOnly/SameSite=Lax.
`Referrer-Policy: same-origin` preserva a origem nos formulários do sistema e
omite a referência ao navegar para outros sites. `no-referrer` não deve ser usado
nesse perfil: navegadores podem enviar `Origin: null` no POST, rejeitado pelo CSRF.
Somente o HTTP de loopback validado recebe cookies sem Secure, para permitir o
login local no mesmo servidor. O proxy exige origem de conexão loopback, chave
temporária e e-mail autorizado; remove cabeçalhos encaminhados e produz seu próprio
sinal HTTPS controlado. O Django não confia no X-Forwarded-Proto enviado pelo cliente.

A política ngrok remove cabeçalhos homônimos antes de inserir a chave temporária
e a identidade OAuth, e fixa Host no domínio autorizado. A chave é criada por
execução e fica somente em memória/arquivo temporário no perfil Windows do usuário,
fora do código, BATs e relatórios; o arquivo é removido no encerramento normal.

No modo remoto, o login Django/Admin limita tentativas por usuário e identidade
OAuth: cinco por quinze minutos, com Retry-After. A reserva é atômica entre os
quatro workers; o contador está em memória e reinicia junto com o processo. O modo
local original não foi alterado. Logout, CSRF e permissões anteriores continuam.

A conta aceitou as ações configuradas no ensaio, mas o nome comercial do plano e
as cotas contratadas não são expostos pelo arquivo do agente. Confira-os no painel.
Os [limites Free publicados](https://ngrok.com/docs/pricing-limits/free-plan-limits)
incluem 3 identidades OAuth/OIDC mensais e 5 regras por política; a política usa
3 regras e somente um e-mail autorizado. Esses limites publicados não identificam
automaticamente o plano desta conta. Login de uma conta negada pode consumir cota.

`check --deploy` emite security.W001 porque verifica o caminho literal do middleware
padrão; este perfil usa uma subclasse para a exceção HTTP local. O alerta não foi
silenciado: HSTS, nosniff, Referrer-Policy e HTTPS remoto foram conferidos em respostas
reais locais e testes. É necessário manter a subclasse e a fronteira WSGI juntas.

O ngrok termina TLS e intermedeia o tráfego; mantenha as contas, senhas, computador
e arquivos privados protegidos, e o agente/Django atualizados após testar versões.
OAuth não substitui o login Django nem a revisão dos acessos. Não use um túnel
sem política, wildcard de hosts, DEBUG, abertura de porta ou desativação do firewall.

## Diagnosticar e validar o login em banco descartável

O modo `--testar-protecao` anterior serve somente texto; ele valida a barreira
OAuth/proxy, mas não exercita um formulário Django no navegador. Para o login,
encerre outro servidor e execute:

```powershell
& '.\.venv\Scripts\python.exe' relatorios/correcao_login_prova.py --fase depois --duracao 300
```

Essa prova cria um SQLite **novo e vazio**, com conta sintética preenchida no
formulário, chave Django própria e os mesmos controles OAuth/proxy. Ela não abre
nem copia o SQLite de trabalho. Não digite sua senha real. No domínio autorizado,
abra `/contas/entrar/?next=/`, clique Entrar nos campos preenchidos, confira painel,
saia e autentique novamente. Teste outra conta Google em navegador privado separado.
Ctrl+C encerra a prova e remove o banco; o limite de cinco minutos também encerra.

A janela online registra motivos CSRF por categorias: `origem_nao_confiavel`,
`referer_ausente`, `token_csrf_invalido`, entre outras. Registra somente método,
rota conhecida, host validado, estado HTTPS, classes de Origin/Referer e presença
de cookies. Não registra valores de cookies/tokens/identidade, senha ou cabeçalhos
completos. O diagnóstico bruto padrão CSRF é substituído pelo sanitizado no
perfil online; a página pública continua genérica. Não copie dados do navegador
ou logs de rede contendo credenciais para pedir suporte.

Depois de corrigir/reiniciar, obtenha um GET novo do login (uma nova janela privada
é útil). Formulários antigos podem manter a política antiga ou um token anterior
à rotação feita no login. Não adicione `null` às origens confiáveis e não remova CSRF.
