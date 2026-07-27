README — Sistema de Cadastro de Produtos HelSync
O que é esse sistema
O sistema de cadastro é o ponto de entrada de um produto novo na plataforma HelSync. Antes de qualquer processamento de imagem acontecer, o usuário define o tipo do produto e associa cada foto às suas medidas. Com base nisso, o sistema organiza os arquivos, gera um produtos.txt e salva a configuração no banco de dados.

Tudo que os módulos posteriores (App_.py, Qtds_Vaviacoes.py, d__Colocar_Medidas.py) precisam saber sobre o produto já está gravado desde o cadastro.

Arquivos envolvidos
Arquivo	Papel
App_Cadastro_Prod.py	Tela de cadastro — coleta tipo, fotos e medidas
_BANCOS_/Banco_Bados.py	Grava o produto no banco (esc_A_ENTRADA)
Tratar_midias/Qtds_Vaviacoes.py	Lê as fotos/txt e gera o prompt de preços para a IA
Tratar_midias/d__Colocar_Medidas.py	Coloca medidas visuais nas imagens
App_.py	Produção — lê o banco e processa as pastas do produto
Os 4 SELECTs do cadastro
O usuário responde 4 perguntas na tela. A combinação das respostas define tudo.

SELECT 1 — Tipo do produto
'Único' = um produto (pode ter variações de tamanho/cor, mas é a mesma peça)
'Kit'   = conjunto de peças diferentes vendidas juntas

SELECT 2 — depende do SELECT 1
Se Único	Se Kit
Quantas variações de tamanho/cor? (1 a 9)	Quantas peças no kit? (2 a 10)
SELECT 3 — depende do SELECT 1
Se Único	Se Kit
Também é vendido em kit? (Sim/Não)	As peças variam em quê? (Tamanho/Cor/Peso...)
SELECT 4 — depende do SELECT 1
Se Único + kit=Sim	Se Kit
Quantas peças no kit?	Quantos grupos de fotos (kits)?
Os 4 cenários de organização das fotos
A combinação dos SELECTs define em qual cenário o produto se encaixa. Cada cenário dita quantas fotos tirar e em que ordem organizá-las.

CENÁRIO A — Único sem variação, sem kit
SELECT 1 = Único
SELECT 2 = 1 variação
SELECT 3 = Não (sem kit)

Organização das fotos: Todas as fotos do produto compartilham 1 único bloco de medidas. Pode tirar quantas fotos quiser — todas terão a mesma altura, largura, espessura e peso.

[foto1] [foto2] [foto3] ... → todas com medida única

Config gravada no banco:

TIPO:ÚNICO|VAR=1|KIT=NO

CENÁRIO B — Único com N variações, sem kit
SELECT 1 = Único
SELECT 2 = N variações (ex: 4 tamanhos diferentes)
SELECT 3 = Não (sem kit)

Organização das fotos: As fotos são divididas em N grupos iguais. Cada grupo tem suas próprias medidas. O sistema divide automaticamente: total de fotos ÷ N variações = fotos por grupo.

[Variação 1: foto1, foto2] → medidas do tamanho P
[Variação 2: foto3, foto4] → medidas do tamanho M
[Variação 3: foto5, foto6] → medidas do tamanho G
[Variação 4: foto7, foto8] → medidas do tamanho GG

Regra para fotografar: tirar o mesmo número de fotos para cada variação. Se tem 4 variações e 8 fotos → 2 fotos por variação. O sistema divide em ordem.

Config gravada no banco:

TIPO:ÚNICO|VAR=4|KIT=NO

CENÁRIO C — Kit de peças diferentes
SELECT 1 = Kit
SELECT 2 = N peças no kit (ex: 3)
SELECT 4 = K grupos de fotos (ex: 2 kits)

Organização das fotos: Para cada kit: 1 foto do kit completo + N fotos individuais (uma por peça). Se tem K kits: total esperado = K × (1 + N) fotos.

Kit 1:
  [📦 foto kit completo]
  [peça 1] [peça 2] [peça 3]
Kit 2:
  [📦 foto kit completo]
  [peça 1] [peça 2] [peça 3]

Regra para fotografar: a primeira foto de cada grupo É o kit completo. As N fotos seguintes são as peças individuais. Cada foto tem suas próprias medidas.

Config gravada no banco:

TIPO:KIT|PECAS=3|VAR=TAMANHO|QTS_KITS=2

CENÁRIO D — Único que também é vendido em kit
SELECT 1 = Único
SELECT 2 = N variações
SELECT 3 = Sim (também kit)
SELECT 4 = M peças no kit

Organização das fotos: Parte 1 — fotos do produto único (com ou sem variações, mesma lógica do A ou B). Parte 2 — fotos dos kits (mesma lógica do C).

O sistema separa automaticamente: as últimas fotos da pasta são os kits.

[fotos do único] → compartilham medidas do único
---
Kit 1:
  [📦 foto kit completo]
  [peça 1] [peça 2] [peça 3]

Regra para fotografar: fotografar o produto único primeiro, depois os kits. A ordem na pasta define tudo.

Config gravada no banco:

TIPO:ÚNICO|VAR=1|KIT=YES|PECAS=3|QTS_KITS=2

O arquivo produtos.txt
Ao clicar em "Processar", o sistema grava um produtos.txt na pasta do produto. Uma linha por foto, no formato:

altxlargxesp,peso

Exemplos:

30x20x3,490gm
40x25x3,620gm
30x20x3,490gm

Esse arquivo é lido depois por Ler_variacoes_txt para exibir o resumo de dimensões.

O renomeio das fotos
Após o processamento, as fotos são renomeadas pelo sistema com as medidas no nome:

REF_altxlargxesp_peso.jpg

Exemplo:

CAS1_30x20x3_490gm.jpg
CAS2_40x25x3_620gm.jpg

Essa convenção de nome é o que permite que montar_variacoes e d__Colocar_Medidas extraiam as medidas automaticamente sem precisar de nenhum input adicional.

A string de configuração (gerar_config_ref)
É o "passaporte" do produto — gerada no cadastro e gravada no banco. Todos os módulos posteriores a leem com _parse_tipo_kit() para saber o que fazer.

Cenário	Config string
Único, 1 variação, sem kit	TIPO:ÚNICO|VAR=1|KIT=NO
Único, 4 variações, sem kit	TIPO:ÚNICO|VAR=4|KIT=NO
Único + kit de 3 peças	TIPO:ÚNICO|VAR=1|KIT=YES|PECAS=3|QTS_KITS=2
Kit de 3 peças, 2 grupos	TIPO:KIT|PECAS=3|VAR=TAMANHO|QTS_KITS=2
Como Qtds_Vaviacoes.py usa isso
A função montar_variacoes(pasta, KIT_OPCOES, TIPO_KIT_UNICO) decide o que fazer baseada no valor de KIT_OPCOES, que é derivado automaticamente do config_str:

Config string	KIT_OPCOES	O que montar_variacoes faz
TIPO:ÚNICO|KIT=NO	'Sem Kit'	Lista cada arquivo com suas medidas individualmente
TIPO:ÚNICO|KIT=YES|PECAS=3	['Peça única', 'Kit: 3']	Repete o produto 1× e 3× mostrando peso total
TIPO:KIT|PECAS=3	None	Agrupa os arquivos em kits de 3 e formata para a IA
O output vai direto para a IA de precificação, que valida os preços respeitando a regra 1:4 da Shopee (variação mais cara ≤ 4× a mais barata).

Regras de fotografia (resumo)
Cenário	Regra
Único sem variação	Tire quantas fotos quiser, todas mesma medida
Único N variações	Mesmo número de fotos por variação, em ordem
Kit	Primeira foto = kit completo, depois as peças individuais
Único + Kit	Fotos do único primeiro, fotos dos kits por último