# 📁 _FERRAMENTAS_/Prompts.py

from _FERRAMENTAS_.Functions import extrair_medidas

def Prompt_Analisador_Produtos():

    return '''Você é um especialista em análise de produtos e copywriting de alto nível.

Analise com extrema atenção a imagem do produto que eu vou te enviar.

Forneça uma resposta completa, organizada e detalhada com as seguintes seções:

**1. Descrição Completa do Produto**
- Nome oficial ou mais adequado do produto
- Para que ele serve exatamente
- Qual é sua função principal e funções secundárias
- Design, formato, tamanho aproximado, cores e acabamento
- Todos os detalhes visíveis na imagem

**2. Material e Construção**
- De que material é feito (tecidos, plásticos, metais, madeira, etc.)
- Qualidade aparente do material
- Textura, resistência, flexibilidade e características do material
- Se tiver partes diferentes, descreva cada uma

**3. O que vem incluso / Conteúdo da Embalagem**
- Liste tudo que acompanha o produto (acessórios, manual, cabos, peças extras, etc.)
- Qualquer detalhe que aparecer na imagem

**4. Usabilidade e Aplicação Prática**
- Para que tipo de pessoa ou público esse produto é ideal
- Em quais situações, ambientes e cenários ele deve ser usado
- Onde guardar ou posicionar (casa, escritório, academia, viagem, carro, etc.)
- Tipos de cenas e contextos onde ele fica mais atrativo (ex: sala de estar, quarto, cozinha, área externa, etc.)
- Dicas de uso real e melhores formas de aproveitar o produto

**5. Observações Adicionais**
- Qualquer detalhe importante, vantagens, possíveis usos criativos ou pontos de atenção

Seja extremamente objetivo, use linguagem clara e natural, como se estivesse explicando para um cliente que vai comprar. Evite enrolação e fluff. Se não tiver certeza de algo, diga que é uma suposição baseada na imagem.

Agora analise a imagem que enviei e responda seguindo exatamente essa estrutura.
'''

def Foto_Profissional_Marketplace(): # Melhora a qualidade da foto do produto deixando ela nítida, com cores vibrantes e fundo limpo

    return '''Melhore significativamente a qualidade geral da imagem, aumentando a nitidez e realçando as cores e texturas do produto para que pareça ter sido tirado com uma câmera profissional.

Clareie e limpe o fundo (padrão marketplace). REGRA ABSOLUTA: proporção da foto original 3:4. A estrutura e a posição do produto devem ficar 100% originais, apenas aplique as melhorias de cor, nitidez e iluminação.
'''

def Remover_Sombras_Fundo_Branco():

    return '''Coloque um fundo completamente branco puro (#FFFFFF), remova todas as sombras e reflexos.

Mantenha a proporção exata 3:4 da imagem original.

Regra mais importante:
- Deixe um espaçamento generoso de fundo branco ao redor de todo o produto (nas laterais, acima e abaixo).
- O produto NÃO pode ficar colado nas bordas da imagem.
- Centralize o produto com margem branca em todos os lados para ficar com visual profissional de marketplace.

Não corte nenhuma parte do produto. Mantenha o produto inteiro, na mesma posição e ângulo original, apenas limpe o fundo, remova sombras e adicione o espaçamento branco adequado.'''

# ⚠️  função grande (62 linhas)
def Descrition_entrad(nome_pro):

    return f'''{nome_pro}

Quero que você atue como especialista em e-commerce, marketplace e copywriting de vendas.
Pesquise na internet, principalmente na Shopee, Amazon, Mercado Livre, produtos parecidos com o meu para entender:

como esse tipo de produto é apresentado;

quais usos reais ele pode ter;

como os concorrentes costumam posicionar o item;

qual faixa de preço faz mais sentido;

quais palavras e argumentos ajudam a vender melhor.

Depois disso, quero que você crie uma ficha completa de produto para marketplace, com linguagem profissional, persuasiva, clara e pronta para copiar e colar.

Objetivo
Transformar a informação bruta que eu te passar em um anúncio forte, bonito e vendedor, sem inventar dados técnicos.

Regras importantes
Use apenas as informações que eu fornecer como base técnica.

Se faltar alguma informação importante, primeiro liste exatamente o que está faltando.

Se o produto for de madeira ou material natural, sugira usos reais e plausíveis, sem exagerar.

Use referências de produtos semelhantes para ajustar o texto, o posicionamento e a faixa de preço.

Não copie textos de concorrentes; apenas use como referência.

O texto final precisa estar pronto para vender em marketplace, principalmente na Shopee.

Entregue exatamente nesta ordem:
Título otimizado para marketplace e SEO.

3 categorias ideais para o produto:

Descrição completa e bem escrita, com foco em conversão:

Para que serve o produto e como usar o produto no dia a dia  e Benefícios principais:

Acabamento ou estado da peça, se for natural, lixado, pintado, envernizado, cru etc:

O que está incluso na compra, observações importantes para o cliente, se necessário:

Especificações técnicas organizadas de forma clara:
"Crie um texto curto de instruções personalizadas para marketplace, definindo o tom da marca, público-alvo, estilo da comunicação e os principais pontos que devem ser destacados no anúncio."

Palavras-chave relevantes para vender melhor.

Sugestão de preço com base em produtos parecidos no mercado.

Estilo da resposta
Seja direto, claro e profissional.
Deixe o texto organizado e bonito.
Escreva de forma persuasiva, mas sem exageros.
Faça parecer um anúncio de alta conversão.

'''

def Description_Foot(opc):
    if opc == []:
        acabamento = """Peça natural limpa, sem verniz. Pode haver variações com o tempo, umidade, tinta ou produtos químicos.
A proposta é manter a cor e a aparência natural da madeira, sem esconder suas marcas.
O acabamento é rústico: apenas corte e leve lixamento para remover partes mais ásperas.

Marcas naturais, rachaduras, nós e diferenças de cor fazem parte da madeira.
Cada peça é única. Você receberá exatamente a peça mostrada nas fotos.

As fotos são reais, sem edição que altere a aparência do produto."""

    else:
        acabamento = f"""Essas peças receberam o seguinte acabamento:
{opc}"""

    return f"""Sobre as peças da Só Rústico

As peças são feitas com madeira natural reaproveitada de árvores que já caíram ou foram retiradas na roça.

{acabamento}
"""

def Criar_Fundo_img_MOSTRA():

    return f'''Crie um fundo fotográfico profissional, ultra-realista e minimalista para destacar ao máximo o produto principal da imagem enviada, e ajustando a nova cena de fundo a imagem enviada!

- Uma superfície ampla e vazia de madeira envelhecida em tom médio-claro (cinza desgastado, bege-acinzentado ou marrom claro envelhecido), com textura bem sutil: veios leves e naturais e rústico.
- Iluminação natural suave e difusa (Imagem de referência para anexar:luz de janela ampla ou dia nublado), sombras mínimas e orgânicas que realçam apenas o produto sem criar drama excessivo.
- Fundo neutro e levemente desfocado: parede lisa em tom claro branco envelhecido rústico, sem elementos chamativos ou decorativos. Atmosfera rústica clean e minimalista, estilo estúdio brasileiro simples para venda online.

Composição horizontal 1:1, alta resolução 4K, estilo foto de produto para e-commerce, espaço central generoso e limpo para posicionar mercadorias. NENHUM objeto extra, sem pessoas, sem logos, sem distrações visíveis. O produto da imagem original deve ser o elemento mais destacado, mais texturizado e mais escuro/contrastado da composição inteira — o fundo precisa ficar visivelmente mais claro, discreto e sem competir pela atenção.
'''

def gerar_prompt_shopee_(imagens, descricao):
    prompts = {}

    for i, imagem in enumerate(imagens, start=1):

        dados = extrair_medidas(imagem)

        medidas_texto = ""

        if dados:
            medidas_texto = f"""
Referência: {dados['referencia']}
Altura: {dados['altura']} cm
Largura: {dados['largura']} cm
Espessura: {dados['espessura']} cm
Peso: {dados['peso']}
"""

        base_prompt = f"""
Crie uma capa profissional de produto para marketplace (Shopee).

Produto: {descricao}

Informações do Produto:
{medidas_texto}

Requisitos:
- Fundo limpo e comercial
- Iluminação profissional de estúdio
- Destaque total no produto
- Estilo realista e vendedor
- Alta conversão visual
- Textos Portugues Brasil.
"""

        if i == 1:
            complemento = "Capa principal com produto centralizado."

        elif i == 2:
            complemento = "Mostrar o produto em uso real."

        else:
            complemento = "Close em detalhes e textura do produto."

        prompts[f"prompt_{i}"] = base_prompt + "\n" + complemento

    return prompts

# ⚠️  função grande (56 linhas)
def gerar_prompt_shopee(imagens, descricao):
    """
    Gera prompts otimizados para capas de produto na Shopee.
    Mantém o produto fiel à imagem original, sem exageros da IA,
    mas com estilização profissional no fundo e iluminação.
    """
    prompts = {}

    for i, imagem in enumerate(imagens, start=1):
        dados = extrair_medidas(imagem)
        medidas_texto = ""

        if dados:
            medidas_texto = f"""
Referência: {dados['referencia']}
Altura: {dados['altura']} cm
Largura: {dados['largura']} cm
Espessura: {dados['espessura']} cm
Peso: {dados['peso']}
"""

        # Base com ênfase em fidelidade à imagem original
        base_prompt = f"""
Crie uma capa profissional de produto para marketplace (Shopee), baseada ESTRICTAMENTE na imagem fornecida como referência principal.

Produto: {descricao}

Informações do Produto:
{medidas_texto}

IMPORTANTE - Fidelidade ao produto:
- Use a imagem fornecida como referência EXATA para o produto: mantenha cores, texturas, proporções, imperfeições e aparência realista sem embelezar, idealizar ou alterar o produto de forma alguma.
- Fotorealista exato da imagem original, sem brilho excessivo, sem suavizar defeitos, sem tornar mais bonito que o real.
- O produto deve parecer idêntico ao original para evitar decepção do cliente.

Requisitos gerais:
- Fundo limpo, branco ou neutro comercial (estilo Shopee).
- Iluminação profissional de estúdio, suave e natural, destacando o produto sem exageros.
- Destaque total no produto centralizado.
- Estilo vendedor e de alta conversão, textos em Português do Brasil.
- Alta resolução, realista.
"""

        # Complementos por imagem, mantendo foco em realismo
        if i == 1:
            complemento = "Capa principal: produto centralizado na imagem original, frente e central, sem mudanças no produto."

        elif i == 2:
            complemento = "Mostrar o produto em uso realista, mantendo aparência exata da imagem original em contexto cotidiano simples."

        else:
            complemento = "Close-up em detalhes e texturas da imagem original, sem alterar ou melhorar o produto."

        prompts[f"prompt_{i}"] = base_prompt + "\n" + complemento + "\n\nPrompt negativo: idealizado, embelezado, perfeito demais, brilho excessivo, cores alteradas, low quality, deformed."

    return prompts

def Prompts(st):
    st1, st2, st3 = st.columns(3)
    with st1.container(border=True):
        st.text('Prompt Analisador de Produtos:', help='Mando uma foto pta IA e madar descrevro Produto!')
        st.code(Prompt_Analisador_Produtos(), height=100)

    with st2.container(border=True):
        st.text('Remover Fundo e Sombras:', help='roca o fundo por branco puro, remove todas as sombras e mantém a proporção 3:4')
        st.code(Remover_Sombras_Fundo_Branco(), height=100)

    with st3.container(border=True):
        st.text('Foto Profissional Marketplace:', help='Melhora a qualidade da foto do produto deixando ela nítida, com cores vibrantes e fundo limpo')
        st.code(Foto_Profissional_Marketplace(), height=100)
