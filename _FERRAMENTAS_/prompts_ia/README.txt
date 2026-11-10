CATALOGO DE PROMPTS DA IA
=========================

Este diretorio contem os prompts padrao da aplicacao. Cada entrada possui:

- id estavel;
- nome visivel;
- escopo ou aba;
- finalidade;
- texto enviado ao modelo.

O arquivo geracao_imagem.json mantém separadamente os três modelos editáveis
usados ao preparar prompts de capa, uso e detalhes em Resultados. A cópia
editável fica em:

  PASTA_APPDATA/IAs/prompts/geracao_imagem.json

Os modelos de imagem são independentes do catálogo de prompts do painel de
conversa. Somente “Produto em uso” recebe Serventia e altura, largura e
espessura extraídas do nome da imagem, para manter a escala da cena. Capa e
detalhes usam a aparência e as proporções mostradas na própria imagem. Nenhum
modelo padrão inclui peso, código interno do produto ou nome do arquivo; a foto
anexada é a referência visual e as dimensões não são texto para desenhar.

Na execucao, a copia editavel deve ficar em:

  PASTA_APPDATA/IAs/prompts/catalogo.json

O prompt geral do provedor e diferente do catalogo por escopo. O prompt geral
define regras comuns da IA; o prompt por escopo explica o papel atual da IA em
Cadastro, Producao, Registros ou Prompts.

Nenhum prompt concede acesso direto ao SQLite. Consultas e alteracoes devem
passar por ferramentas controladas da aplicacao.