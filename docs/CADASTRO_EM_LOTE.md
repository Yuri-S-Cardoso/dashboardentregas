# Cadastro de Entregas em Lote

Em **Minhas Entregas**, escolha **Adicionar Entregas em Lote**. O cadastro
individual continua em **Novo registro**, e **Editar** permite corrigir qualquer
entrega posteriormente.

## Digitar

1. Confira a data, inicialmente hoje no fuso America/Sao_Paulo, e a situação padrão.
2. Digite o primeiro código. Enter avança para o código seguinte; no fim da grade,
   cria outra linha. Tab mantém a navegação normal pelos campos.
3. Horário é opcional: vazio significa não informado. O campo usa o controle
   nativo de horário do navegador (`time`), com separadores automáticos e seletor
   quando disponível. Aceita horas, minutos e segundos; 00:00 é meia-noite real.
4. Cada linha pode ter sua própria situação. **Outra data** permite uma exceção;
   quando vazia, vale a data do lote. Alterar a situação padrão muda as linhas
   ainda vazias e as próximas, preservando situações de entregas já preenchidas.
5. Use **Adicionar Linha** ou **Adicionar 20 Linhas** conforme necessário. Há 20
   linhas iniciais e limite de 500 por lote. Os contadores mostram os preenchidos,
   baixas e insucessos; linhas incompletas serão apontadas na validação.

## Colar códigos

Abra **Colar vários códigos ou células do Excel**, cole um código por linha e
clique em **Ver prévia da colagem**. Exemplo:

```text
000123
000124
000123
```

Confira e clique em **Adicionar à grade**. Serão três entregas: códigos repetidos
não são eliminados. Colar várias linhas diretamente no campo Código também abre
essa prévia. As linhas recebem os padrões escolhidos e nenhum horário é criado.

## Colar do Excel

Copie as células e cole na mesma área. O layout **Código, Data, Horário, Situação**,
separado por tabulações, funciona com ou sem cabeçalho. Cabeçalhos reconhecidos
permitem outra ordem. Se necessário, escolha o campo de cada coluna ou **Ignorar**;
marque se a primeira linha é cabeçalho. Confira a prévia antes de adicionar à grade.
Datas aceitam DD/MM/AAAA ou AAAA-MM-DD; horário aceita HH:MM ou HH:MM:SS.
Valores desconhecidos permanecem para correção, sem transformar ausências em zero.
Se um horário colado/restaurado não couber no controle nativo, ele permanece
visível como texto para correção e validação, sem ser apagado silenciosamente.

O sistema trata códigos como texto. Se o Excel já tiver removido zeros ou
convertido um código em notação científica antes de copiar, a grade não consegue
reconstruir o texto original. Confira o conteúdo na prévia.

## Salvar e corrigir

**Salvar Todos** valida o lote inteiro e abre uma prévia, sem gravar. Confira as
datas, situações, quantidades e horários e use **Confirmar e salvar todos**.
**Voltar à edição** mantém os dados. Erros identificam linha e campo, sem apagar a
digitação; nenhuma linha será salva enquanto o lote tiver erro.

A confirmação grava todas as entregas em uma transação. Se houver falha, tudo é
revertido. Reenviar a mesma solicitação não cria outra cópia do lote. Para repetir
entregas intencionalmente, use **Começar outro lote** depois do sucesso; data e
situação padrão permanecem escolhidas. Repetição de código continua permitida.

As entregas salvas aparecem imediatamente na lista, painel, produtividade,
conferência e exportações existentes. Baixas usam o preço vigente no momento da
gravação, preservado em cada registro; insucessos geram zero. Nenhum histórico é
recalculado.

## Rascunho e celular

O rascunho temporário é salvo no armazenamento local do navegador após a digitação
e restaurado ao retornar à tela. Inclui apenas dados desta grade, texto da colagem
e identificador do lote, sem senha, sessão ou CSRF. Não salva automaticamente no
banco. **Limpar** pede confirmação para descartar a grade/rascunho, sem excluir
entregas já gravadas; depois do sucesso, o rascunho correspondente é apagado.

Se o navegador bloquear o armazenamento, a tela avisa; mantenha a página aberta
até salvar. O rascunho é específico do navegador, da conta e do endereço acessado;
não sincroniza computador e celular. Mantenha apenas uma aba por lote: abas com
rascunhos diferentes na mesma conta/endereço podem substituir o rascunho local.

No celular, as linhas se reorganizam em blocos com Código, Horário, Situação e
Outra data. Campos têm área de toque; o código usa teclado numérico sem conversão
para número. O botão de salvar fica na barra inferior. Use a mesma opção de colar
listas; não é necessário abrir um formulário para cada entrega.

Para abrir o sistema, use o inicializador existente e os endereços que ele mostra.
Esta melhoria não altera rede, firewall ou inicialização.

## Conferência manual pendente

Em uma cópia de teste, confira o uso em computador e celular: digitação de 100
códigos, Enter/Tab, teclado, colagem de 50/100 células, rolagem, botão inferior,
erros por linha, atualizar a página e recuperar o rascunho, Limpar/cancelar e
reenvio após sucesso. Confira larguras 360, 390, 768 px e desktop. O ensaio HTTP e
os testes de JavaScript não substituem esse teste visual e de toque.
