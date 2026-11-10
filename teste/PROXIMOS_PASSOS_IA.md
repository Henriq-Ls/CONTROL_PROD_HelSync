# Próximos passos para testar e evoluir a IA

## Objetivo

Documentar e validar quais informações de aba e produto o painel envia à IA e
como o histórico persistente deve se comportar ao alternar entre áreas. Fazer a
validação do código e da simulação sem abrir o aplicativo neste ambiente.

## Estado atual

- O teste offline está em `teste/simular_chat_ia.py`.
- A suíte anterior passou em dez testes em 2026-10-12. Além dos cenários de streaming,
  erro, descarte de resposta e exclusão, percorre o roteamento real de MainWindow,
  verifica as mensagens antes de chegarem ao worker e simula o booleano enviado
  por `QPushButton.clicked` para garantir que o botão Enviar use o texto digitado.
- Os cenários verificam os contextos das oito abas, a distinção de instrução entre
  Criação e Resultados, Cadastro em rascunho sem identidade antiga e isolamento
  entre produtos diferentes.
- A nova etapa separa o histórico por produto e aba, inclusive Criação e Resultados
  que compartilham o escopo lógico `Producao`. Foram acrescentados testes offline
  para alternância de abas, conversas globais, exclusão somente da conversa ativa
  e preservação do legado; a suíte passou em 17 testes em 2026-10-12.
- Embora o histórico mostrado permaneça próprio de cada aba, mensagens recentes
  das outras abas do mesmo produto são incluídas como contexto privado da IA.
  Outros produtos ficam excluídos. O legado misto de `Producao` é incluído com
  identificação explícita de que sua subaba de origem é desconhecida.
- A simulação usa o serviço real com respostas SSE falsas e um worker falso:
  não acessa a internet, não usa credenciais e não inicia PySide6.
- O ajuste de altura das bolhas depende do layout Qt e não é validado pelo
  simulador offline; precisa de confirmação visual no desktop.
- As correções anteriores também aumentaram o limite de saída de
  `openrouter/free` para 4096 e passaram a processar o stream incrementalmente.
- O painel é único; cada histórico é salvo no AppData por produto e chave da aba.
  “Apagar” remove somente as mensagens da conversa ativa; em abas sem produto,
  remove somente a memória global da aba ativa.
- Cadastro ainda não salvo usa um rascunho separado. Ao salvar o produto, o
  histórico do rascunho é promovido para a conversa persistente do produto.

## Proteções para a próxima implementação

- Trabalhar somente no aplicativo desktop existente. Não criar outro app, trocar
  provedores, instalar dependências ou reestruturar módulos que não participam
  da memória da conversa.
- Fazer a menor alteração necessária para separar o carregamento/gravação do
  histórico por produto e aba. Manter separado o escopo lógico dos prompts e a
  chave de armazenamento do histórico.
- Preservar e cobrir com regressões: envio pelo botão (incluindo o booleano do
  `clicked` do Qt), limpeza do campo, contexto das oito abas, rascunho e promoção,
  streaming, erros, descarte de resposta pendente e altura dinâmica das bolhas.
- Não apagar nem sobrescrever dados do produto, dados comerciais ou conversas
  antigas. Preservar o histórico misto legado de `Producao`; não atribuir suas
  mensagens a Criação ou Resultados sem metadados que comprovem a origem.
- Manter a suíte existente e acrescentar testes específicos para histórico por
  aba e exclusão somente da conversa ativa. Não declarar a aparência validada
  sem conferir no desktop Windows.

## Decisão de projeto: contexto compartilhado, histórico separado

**Decisão:** cada área de trabalho terá seu próprio histórico por produto e por
aba. Os fatos atuais do produto continuam disponíveis em cada aba por meio do
snapshot/contexto ativo. Mensagens recentes das outras conversas do mesmo produto
também são fornecidas como memória de referência, mas não aparecem como mensagens
da conversa atual nem são tratadas como pedidos ativos.

- A interface e o provedor continuam sendo o mesmo painel de IA. O histórico
  visível continua separado; o modelo também recebe contexto de conversas recentes
  de outras abas do mesmo produto.
- Cadastro salvo, Criação, Resultados e Anúncio mantêm históricos separados para
  o mesmo produto.
- Criação e Resultados serão separados entre si, embora continuem usando o mesmo
  escopo lógico `Producao` e o snapshot atual do produto. O escopo de instruções
  do modelo não deve ser confundido com a chave usada para persistir o histórico.
- Ao voltar à mesma combinação de produto e aba, o histórico daquela combinação
  será restaurado. Ao trocar de aba, só essa conversa aparece na interface, mas
  a IA pode consultar mensagens recentes das outras abas daquele mesmo produto.
  Ao trocar de produto, nenhuma conversa do produto anterior entra no contexto.
- A memória compartilhada se limita às mensagens recentes das outras abas,
  exclui a aba atual e outros produtos, e tem limite de 16.000 caracteres. O
  legado misto é identificado como tal, sem atribuição a Criação ou Resultados.
  O snapshot ativo é a fonte de fatos atuais; conversas antigas servem para
  continuidade, não como instruções para executar ações.
- Vendas, Registros, Prompts e Configurações continuam com históricos globais
  independentes por aba enquanto não houver vínculo de produto confirmado e
  autorizado. Uma aba global sem mensagens anteriores aparecer vazia é esperado.
- “Apagar conversa” deve apagar apenas o histórico da aba e do produto ativos;
  não deve apagar os dados do produto nem as conversas de outras abas. Nas abas
  globais, apaga somente o histórico global da própria aba. A confirmação deve
  informar claramente esse alcance e preservar o descarte de respostas pendentes.

**Por que esta decisão:** o snapshot fornece os fatos atuais do produto sem
precisar reutilizar instruções e mensagens de outro fluxo. Isso evita que uma
conversa de Cadastro, Criação, Resultados ou Anúncio influencie indevidamente a
aba atual e atende ao caso de teste que pede não herdar contexto da aba anterior.

### Histórico antigo e migração segura

- Hoje o histórico persistente é carregado por produto, reunindo todos os arquivos
  de escopo da conversa. Criação e Resultados usam `Producao` e a mesma conversa.
- As mensagens antigas de Produção não guardam a subaba Criação/Resultados em
  cada registro. Não é seguro adivinhar a qual tela cada mensagem pertence.
- Não apagar nem copiar automaticamente esse histórico para as duas novas abas.
  Mantê-lo preservado sem atribuição a uma subaba. Ele pode entrar como referência
  compartilhada do mesmo produto, sempre identificado como legado com subaba
  desconhecida.

## Verificação da separação e do contexto entre conversas

**Histórico separado e contexto entre conversas implementados no código.** A
simulação offline verifica que as conversas continuam separadas na interface,
mas mensagens de outras abas do mesmo produto chegam ao modelo como referência.
Também cobre isolamento entre produtos, identificação do legado e limite de memória.
A validação visual no desktop Windows fica para o usuário.

| Aba/fluxo | O que a IA deve receber e demonstrar |
| --- | --- |
| Cadastro | Se não houver produto selecionado, não inventar um; pedir o nome ou a seleção. Se o formulário tiver dados parciais, identificar que são parciais. |
| Criação | Receber a identidade do produto ativo e saber que está no fluxo de criação, sem confundir com outro produto aberto anteriormente. |
| Resultados | Receber o produto ativo e saber que a pessoa está revisando os resultados gerados. |
| Anúncio | Receber o produto ativo e saber que o objetivo é criar ou revisar um anúncio de marketplace. |
| Vendas | Saber que a aba trata de vendas concluídas, sem alegar acesso aos dados de vendas/estoque nem tratar uma venda como anúncio ou criação. |
| Registros | Saber que a aba mostra registros, sem alegar que consultou linhas nem confundi-los com vendas ou resultados. |
| Prompts | Confirmar que a IA reconhece a área de prompts/configuração de instruções, sem inventar um produto ativo. |
| Configurações | Confirmar que a área trata de configurações do aplicativo/IA, não de criar um anúncio ou concluir uma venda. |

As linhas descrevem o comportamento esperado. Os testes offline confirmam a
montagem do contexto por aba e da memória compartilhada do mesmo produto; não
provam que um modelo real sempre seguirá as instruções.

## Verificações automatizadas da implementação

1. Manter os testes existentes de contexto por aba, produto ativo, rascunho,
   botão Enviar, streaming, erro e descarte de resposta após apagar.
2. Confirmar, com o mesmo produto, isolamento e restauração de Criação, Resultados,
   Anúncio e Cadastro salvo ao alternar entre as abas.
3. Confirmar que a persistência real usa a chave da aba sem mudar o escopo lógico
   enviado ao prompt do modelo.
4. Confirmar que a exclusão da conversa ativa preserva outras abas, os dados do
   produto e o histórico legado misto de Produção.
5. Confirmar que o histórico misto legado pode ser consultado separadamente e
   aparece na memória compartilhada com o rótulo de origem desconhecida, sem ser
   atribuído a Criação ou Resultados.
6. Confirmar que Vendas e Registros continuam com memórias globais independentes
   e não recebem dados comerciais ou históricos de produto.

### Arquivos principais para essa alteração

- `_APP_/main_window.py` — seleção da aba e publicação do contexto ativo.
- `_IAS_/Painel_IA_PySide6.py` — carregamento, gravação e exclusão do histórico.
- `_IAS_/ia_memory_appdata.py` — persistência em AppData por produto/escopo.
- `_IAS_/_STATUS_IAS.txt` — estado atual do módulo.
- `teste/simular_chat_ia.py` — regressões offline do roteamento e da conversa.

## Critério de aprovação

“A IA sabe” significa que o pedido real contém o snapshot ativo, o histórico
visível da aba atual e mensagens de referência das outras abas do mesmo produto,
sem conteúdo de outros produtos. Os testes verificam a construção desse contexto
e as regras locais do chat; um provedor falso não garante a resposta semântica de
um modelo real.

Se o contexto estiver ausente ou incorreto, corrigir sua montagem no fluxo real
do painel e acrescentar uma regressão offline. Se o contexto estiver correto,
mas a resposta do modelo não respeitar as instruções, registrar o exemplo e
ajustar o prompt com uma expectativa verificável.

## Limites e execução

- Não iniciar a janela PySide6, workflow, servidor ou build neste ambiente.
- Não chamar OpenRouter ou outro serviço real nos testes automatizados.
- Não usar, imprimir ou salvar credenciais de verdade; todas as respostas e
  produtos do teste devem ser fictícios.
- Executar a suíte na pasta `hen-place-control` com:

  ```text
  python teste/simular_chat_ia.py
  ```

- A verificação visual e a confirmação com um modelo real continuam sendo
  validações separadas no desktop Windows e devem ser identificadas como tal.

## Pendências preservadas para validação ou decisão posterior

- Validar no desktop Windows a restauração do histórico por produto/aba, a
  exclusão somente da conversa ativa e a consulta somente leitura do legado.
- Validar no desktop Windows que cada aba restaura seu próprio histórico, que
  Criação e Resultados não misturam mensagens, e que “Apagar” afeta somente a
  conversa ativa.
- Enviar mensagens longas de usuário e receber respostas longas; confirmar que
  ambas as bolhas crescem, quebram linha e não cortam o texto durante nem após o
  streaming.
- Confirmar a relação entre `A_ENTRADA.PRODUTO` e os identificadores de vendas,
  marketplace, estoque, prateleira e nota antes de conectar dados comerciais à IA.
- Definir retenção das conversas globais e projetar resumos de produto somente
  depois de validar identidade e isolamento; manter esses dados no AppData.
- Não expandir consultas de Vendas/Registros, ferramentas de escrita ou envio de
  imagens a provedores até haver contrato, autorização e validação específicos.
