"""Resumo funcional do aplicativo e de cada escopo enviado ao modelo."""

from __future__ import annotations


_CONTEXTO_GERAL = (
    "Hen Place Control é um aplicativo desktop PySide6 para cadastrar produtos, "
    "criar e revisar mídias, preparar anúncios e acompanhar dados comerciais. "
    "A aplicação mantém o SQLite para dados comerciais e salva a memória da IA "
    "em arquivos do AppData. O painel recebe somente o contexto publicado pela "
    "aba ativa; ele não recebe o código-fonte, o banco inteiro nem acesso direto "
    "ao sistema operacional. Caminhos locais e a proporção de processamento não "
    "são enviados ao modelo."
)

_CONTEXTOS_ABA = {
    "Cadastro": (
        "Aba Cadastro: organiza os dados do produto, grupos, variações, medidas "
        "e mídias. O painel recebe um snapshot do formulário. Ferramentas "
        "controladas podem ler o formulário e preparar propostas para Nome, "
        "Descrição ou Como pode ser usado; qualquer escrita depende de "
        "confirmação visual. Não altere Origem, Destino, Proporção nem campos de "
        "seleção. Se o snapshot indicar rascunho ou não trouxer um identificador "
        "de produto salvo, use somente o formulário atual, não herde a identidade "
        "nem o histórico de outro produto e peça esclarecimento quando faltarem "
        "dados para identificar o produto."
    ),
    "Producao": (
        "Escopo Criação/Resultados: acompanha a preparação e a saída do fluxo de "
        "mídias. O painel recebe apenas o snapshot textual publicado pela "
        "interface; não presume que viu imagens, vídeos, arquivos ou etapas que "
        "não estejam nesse snapshot. Não inicia nem altera a pipeline."
    ),
    "Anuncio": (
        "Aba Anúncio: prepara e revisa texto comercial do produto. O painel "
        "recebe fatos textuais; imagens não são enviadas. A resposta é uma "
        "sugestão para revisão e cópia manual, não publica nem preenche os "
        "editores."
    ),
    "Sociais": (
        "Aba Sociais: prepara rascunhos copiáveis para publicação manual. O "
        "snapshot pode incluir fatos do Cadastro e o título e a descrição mais "
        "recentes salvos em MARKET_PLACE. Use o texto do anúncio como referência "
        "de apresentação, mas trate o Cadastro como fonte factual quando houver "
        "conflito. Imagens e vídeos não são enviados à IA e o aplicativo não "
        "publica nas redes."
    ),
    "Vendas": (
        "Aba Vendas: registra vendas concluídas de unidades e afeta a "
        "disponibilidade do estoque. Atualmente esta conversa não recebe os "
        "dados das vendas nem do estoque e não tem ferramenta de leitura ou "
        "escrita nessa aba; não afirme que consultou ou alterou vendas, "
        "marketplace ou estoque."
    ),
    "Registros": (
        "Aba Registros: exibe dados comerciais de VENDAS e MARKET_PLACE. "
        "Atualmente esta conversa não recebe essas linhas nem consulta o banco; "
        "analise somente dados apresentados pelo usuário ou incluídos no "
        "contexto."
    ),
    "Prompts": (
        "Aba Prompts: apresenta o catálogo editável de instruções por escopo e "
        "textos históricos de referência. O snapshot pode incluir esses textos. "
        "Diferencie instruções ativas de referências históricas; o painel não "
        "edita o catálogo por conta própria."
    ),
    "Configuracoes": (
        "Aba Configurações: mantém opções da loja e recursos visuais. O painel "
        "não recebe os valores dessa tela nem pode alterá-los; peça ao usuário "
        "que informe os dados relevantes."
    ),
}


def resumo_aba_ia(escopo: str, area_ativa: str = "") -> str:
    """Retorna a orientação estável do projeto e da aba atualmente ativa."""
    nome = str(escopo or "").strip()
    descricao = _CONTEXTOS_ABA.get(
        nome,
        "O escopo ativo não está descrito neste mapa. Não presuma quais dados ou "
        "ações estão disponíveis; use apenas o snapshot e as ferramentas "
        "explicitamente fornecidos pela aplicação.",
    )
    area = str(area_ativa or "").strip()
    if nome == "Producao" and area == "Criação":
        descricao += (
            " Tela ativa: Criação. A pessoa está acompanhando e preparando o "
            "processamento do produto; não afirme que a execução terminou sem "
            "um resultado explícito no snapshot."
        )
    elif nome == "Producao" and area == "Resultados":
        descricao += (
            " Tela ativa: Resultados. A pessoa está revisando os resultados "
            "gerados; não confunda esta revisão com a configuração ou o início "
            "de uma nova criação."
        )
    return f"{_CONTEXTO_GERAL}\n\n{descricao}"
