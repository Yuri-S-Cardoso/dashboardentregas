# Versionamento e dados privados

O GitHub distribui o código do sistema. Banco, credenciais, arquivos importados,
exportações e evidências da instalação são privados e não acompanham o clone.

## O que versionar

- Aplicativos Django, migrations e comandos de gerenciamento.
- Templates e fontes CSS/JavaScript de `static/`.
- Inicializadores BAT/Python, testes e `requirements.txt`.
- README, documentação e exemplos de configuração sem dados reais.

`config/settings.py` pode ser versionado porque lê a configuração e gera o
segredo local; ele não contém a chave usada pela instalação.
`config/ngrok_online.example.json` tem campos vazios e deve continuar no Git.
Não substitua esse exemplo pela configuração preenchida de `.local/`.

## O que ignorar

| Categoria | Exemplos |
|---|---|
| Ambiente e caches | `.venv/`, `__pycache__/`, `node_modules/`, cobertura |
| Segredos e identidade da instalação | `.local/`, `.env*`, chaves, certificados privados, configuração ngrok preenchida |
| Banco e recuperação | SQLite e seus arquivos de transação, backups, manifestos, dumps |
| Dados operacionais | `referencias/`, `relatorios/`, `media/`, uploads, exportações |
| Arquivos de negócio | XLSX/XLS/ODS, CSV/TSV e comprovantes PDF |
| Saídas geradas | `staticfiles/`, logs, temporários e preferências locais |

Os formatos de negócio são ignorados por padrão também fora dessas pastas para
evitar incluir uma planilha ou exportação arrastada para a raiz. Se for necessário
publicar uma fixture, use somente dados sintéticos, confira seu conteúdo e crie
uma exceção específica no `.gitignore`. Não force inclusão de arquivos reais.
Imagens de interface e código JSON não são ignorados genericamente.

## Conferência antes de publicar

```powershell
git status --short
git diff --check
git diff --stat
git ls-files -ci --exclude-standard
git check-ignore -v --no-index db.sqlite3 .local/ngrok_online.json referencias/origem.xlsx
```

`git ls-files -ci --exclude-standard` identifica arquivos **já rastreados** que
agora correspondem a uma regra de exclusão. Normalmente não deve produzir saída.
`git check-ignore --no-index` explica as regras sem alterar o índice ou os arquivos.
Revise também o conteúdo do diff, sem copiar segredos para logs ou issues.

O `.gitignore` evita novas inclusões acidentais, mas não retira um arquivo do índice
nem apaga versões anteriores. Se um arquivo privado estiver rastreado, remova-o
somente do versionamento preservando a cópia local, após conferir o caminho.
Credenciais já publicadas exigem revogação/rotação; apagar o arquivo no commit
seguinte não elimina o segredo do histórico. Alteração de histórico ou push
forçado deve ser uma ação deliberada, separada da edição desta política.

## Escopo da revisão de 08/11/2026

Foram inspecionados os 180 caminhos rastreados, o índice e os dois commits
disponíveis nas referências locais, incluindo `origin/main` no estado conhecido.
Não havia bancos, `.local/`, planilhas privadas ou relatórios nesses commits.
A busca por padrões comuns de credenciais não encontrou segredo real; os domínios
ngrok encontrados eram exemplos sintéticos dos testes de segurança.

Isso é uma revisão do checkout e do histórico local disponível, não uma garantia
de detecção de todo segredo possível nem uma auditoria de branches, artefatos,
forks ou conteúdo remoto não presente nessas referências. Não houve commit, push,
remoção do índice, mudança de histórico ou alteração da implantação.
Evidências sanitizadas ficam no diretório local `relatorios/`, fora do Git.
