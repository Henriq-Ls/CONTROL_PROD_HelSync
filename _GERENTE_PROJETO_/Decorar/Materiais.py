from typing import Optional, Literal

_MATERIAIS = [
    # Alertas e Segurança
    "alerta", "emergencia", "proibido", "escudo", "erro", "aviso", "parar", "perigo", "chama", "inseto",

    # Emoções e Expressões
    "feliz", "triste", "raiva", "chorando", "rindo", "beijo", "olho", "robô", "cerebro",

    # Natureza
    "flor", "rosa", "plantação", "folhas", "arvore", "borboleta", "galinha", "gato", "cachorro", "leão", "peixe",

    # Clima
    "neve", "nuvem", "trovoada", "vento", "arco-iris",

    # Comidas e Bebidas
    "bolo", "café", "cerveja", "hambúrguer", "pizza", "queijo", "refrigerante", "salada", "vinho",

    # Transporte e Viagem
    "avião", "carro", "ônibus", "trator", "foguete",

    # Objetos e Tecnologia
    "computador", "tv", "mouse", "teclado", "celular", "internet", "link", "satélite", "servidor", "terminal",
    "etiqueta", "engrenagem",

    # Escritório
    "escrita", "lápis", "pasta", "caneta", "documento", "papel", "impressora", "prancheta", "trabalho", "calculadora",

    # Código e Depuração
    "detetive", "lupa", "ferramentas", "chave inglesa", "manutenção", "martelo", "extintor", "luz", "lampada",

    # Controle de Versão e Deploy
    "deploy", "pacote", "pergaminho", "atualizar", "reiniciar",

    # Esportes e Atividades
    "bailarina", "bola futebol", "bola basquete", "corrida",

    # Correto e Sucesso
    "correto", "verificado", "positivo", "alvo", "ok",

    # Dinheiro e Riqueza
    "dinheiro", "moeda", "cartão crédito", "diamante", "pagamento", "banco", "gráfico alta", "gráfico queda",
    "maleta dinheiro", "troféu", "carteira", "investimento", "cofrinho",

    # Setas e Direções
    "seta cima", "seta baixo", "seta direita", "seta esquerda",
    "seta circular horária", "seta circular anti-horária",
    "seta atualizar", "seta loop",
    "seta vertical", "seta horizontal",

    # Círculos e Formas
    "circulo", "quadrado", "estrela", "coração",

    # Pessoas e Social
    "pessoa", "grupo", "familia", "criança", "admin", "perfil",

    # Localização
    "mapa", "pin", "casa", "loja", "escola", "hospital", "bandeira",

    # Mídia e Comunicação
    "foto", "câmera", "vídeo", "microfone", "som", "música", "notificação", "email", "mensagem", "chat", "telefone",

    # UI / Interface
    "menu", "busca", "filtro", "configuração", "fechar", "adicionar", "remover", "editar", "salvar", "compartilhar",
    "favorito", "curtir", "bloquear", "info", "ajuda", "voltar", "avançar", "home", "login", "logout", "visível",
    "invisível", "cadeado", "desbloqueado", "download", "upload", "imprimir", "recortar", "copiar", "colar",
    "desfazer", "refazer", "expandir", "recolher", "tela cheia", "minimizar", "modo escuro", "modo claro",

    # Tempo e Data
    "relógio", "calendário", "alarme", "temporizador", "histórico",

    # Gráficos e Dados
    "gráfico barra", "gráfico pizza", "gráfico linha", "tabela", "dados", "dashboard", "relatório",
]

MaterialNome = Literal[
    # Alertas e Segurança
    "alerta", "emergencia", "proibido", "escudo", "erro", "aviso", "parar", "perigo", "chama", "inseto",

    # Emoções e Expressões
    "feliz", "triste", "raiva", "chorando", "rindo", "beijo", "olho", "robô", "cerebro",

    # Natureza
    "flor", "rosa", "plantação", "folhas", "arvore", "borboleta", "galinha", "gato", "cachorro", "leão", "peixe",

    # Clima
    "neve", "nuvem", "trovoada", "vento", "arco-iris",

    # Comidas e Bebidas
    "bolo", "café", "cerveja", "hambúrguer", "pizza", "queijo", "refrigerante", "salada", "vinho",

    # Transporte e Viagem
    "avião", "carro", "ônibus", "trator", "foguete",

    # Objetos e Tecnologia
    "computador", "tv", "mouse", "teclado", "celular", "internet", "link", "satélite", "servidor", "terminal",
    "etiqueta", "engrenagem",

    # Escritório
    "escrita", "lápis", "pasta", "caneta", "documento", "papel", "impressora", "prancheta", "trabalho", "calculadora",

    # Código e Depuração
    "detetive", "lupa", "ferramentas", "chave inglesa", "manutenção", "martelo", "extintor", "luz", "lampada",

    # Controle de Versão e Deploy
    "deploy", "pacote", "pergaminho", "atualizar", "reiniciar",

    # Esportes e Atividades
    "bailarina", "bola futebol", "bola basquete", "corrida",

    # Correto e Sucesso
    "correto", "verificado", "positivo", "alvo", "ok",

    # Dinheiro e Riqueza
    "dinheiro", "moeda", "cartão crédito", "diamante", "pagamento", "banco", "gráfico alta", "gráfico queda",
    "maleta dinheiro", "troféu", "carteira", "investimento", "cofrinho",

    # Setas e Direções
    "seta cima", "seta baixo", "seta direita", "seta esquerda",
    "seta circular horária", "seta circular anti-horária",
    "seta atualizar", "seta loop",
    "seta vertical", "seta horizontal",

    # Círculos e Formas
    "circulo", "quadrado", "estrela", "coração",

    # Pessoas e Social
    "pessoa", "grupo", "familia", "criança", "admin", "perfil",

    # Localização
    "mapa", "pin", "casa", "loja", "escola", "hospital", "bandeira",

    # Mídia e Comunicação
    "foto", "câmera", "vídeo", "microfone", "som", "música", "notificação", "email", "mensagem", "chat", "telefone",

    # UI / Interface
    "menu", "busca", "filtro", "configuração", "fechar", "adicionar", "remover", "editar", "salvar", "compartilhar",
    "favorito", "curtir", "bloquear", "info", "ajuda", "voltar", "avançar", "home", "login", "logout", "visível",
    "invisível", "cadeado", "desbloqueado", "download", "upload", "imprimir", "recortar", "copiar", "colar",
    "desfazer", "refazer", "expandir", "recolher", "tela cheia", "minimizar", "modo escuro", "modo claro",

    # Tempo e Data
    "relógio", "calendário", "alarme", "temporizador", "histórico",

    # Gráficos e Dados
    "gráfico barra", "gráfico pizza", "gráfico linha", "tabela", "dados", "dashboard", "relatório",
]

def Material(
    nome: MaterialNome = "",
    texto: Optional[str] = None,
    quantidade: Optional[int] = None,
    help: Optional[str] = None,
) -> str:
    """
    Gera uma string contendo ícones Material com base nos parâmetros fornecidos.
    Compatível com Streamlit usando a sintaxe :material/nome_icone:

    Args:
        nome (MaterialNome): O nome em português do ícone a ser utilizado.
        texto (str, opcional): Um texto que pode ser adicionado à string de saída.
        quantidade (int, opcional): O número de vezes que o ícone deve ser repetido.
        help (str, opcional): Descrição ou ajuda adicional (não afeta o retorno).

    Returns:
        str: Uma string formatada contendo o(s) ícone(s) Material e o texto, se fornecido.
    """

    icons = {
        # Alertas e Segurança
        "alerta":           ":material/warning:",
        "emergencia":       ":material/emergency:",
        "proibido":         ":material/block:",
        "escudo":           ":material/shield:",
        "erro":             ":material/cancel:",
        "aviso":            ":material/report:",
        "parar":            ":material/stop_circle:",
        "perigo":           ":material/bolt:",
        "chama":            ":material/local_fire_department:",
        "inseto":           ":material/bug_report:",

        # Emoções e Expressões
        "feliz":            ":material/sentiment_satisfied:",
        "triste":           ":material/sentiment_dissatisfied:",
        "raiva":            ":material/sentiment_very_dissatisfied:",
        "chorando":         ":material/mood_bad:",
        "rindo":            ":material/sentiment_very_satisfied:",
        "beijo":            ":material/favorite:",
        "olho":             ":material/visibility:",
        "robô":             ":material/smart_toy:",
        "cerebro":          ":material/psychology:",

        # Natureza
        "flor":             ":material/local_florist:",
        "rosa":             ":material/local_florist:",
        "plantação":        ":material/grass:",
        "folhas":           ":material/eco:",
        "arvore":           ":material/park:",
        "borboleta":        ":material/flutter_dash:",
        "galinha":          ":material/egg:",
        "gato":             ":material/pets:",
        "cachorro":         ":material/pets:",
        "leão":             ":material/cruelty_free:",
        "peixe":            ":material/set_meal:",

        # Clima
        "neve":             ":material/ac_unit:",
        "nuvem":            ":material/cloud:",
        "trovoada":         ":material/thunderstorm:",
        "vento":            ":material/air:",
        "arco-iris":        ":material/filter_drama:",

        # Comidas e Bebidas
        "bolo":             ":material/cake:",
        "café":             ":material/coffee:",
        "cerveja":          ":material/sports_bar:",
        "hambúrguer":       ":material/lunch_dining:",
        "pizza":            ":material/local_pizza:",
        "queijo":           ":material/egg_alt:",
        "refrigerante":     ":material/local_drink:",
        "salada":           ":material/salad:",
        "vinho":            ":material/wine_bar:",

        # Transporte e Viagem
        "avião":            ":material/flight:",
        "carro":            ":material/directions_car:",
        "ônibus":           ":material/directions_bus:",
        "trator":           ":material/agriculture:",
        "foguete":          ":material/rocket_launch:",

        # Objetos e Tecnologia
        "computador":       ":material/computer:",
        "tv":               ":material/tv:",
        "mouse":            ":material/mouse:",
        "teclado":          ":material/keyboard:",
        "celular":          ":material/smartphone:",
        "internet":         ":material/language:",
        "link":             ":material/link:",
        "satélite":         ":material/satellite:",
        "servidor":         ":material/dns:",
        "terminal":         ":material/terminal:",
        "etiqueta":         ":material/label:",
        "engrenagem":       ":material/settings:",

        # Escritório
        "escrita":          ":material/edit_note:",
        "lápis":            ":material/edit:",
        "pasta":            ":material/folder:",
        "caneta":           ":material/draw:",
        "documento":        ":material/description:",
        "papel":            ":material/article:",
        "impressora":       ":material/print:",
        "prancheta":        ":material/assignment:",
        "trabalho":         ":material/work:",
        "calculadora":      ":material/calculate:",

        # Código e Depuração
        "detetive":         ":material/manage_search:",
        "lupa":             ":material/search:",
        "ferramentas":      ":material/build:",
        "chave inglesa":    ":material/handyman:",
        "manutenção":       ":material/construction:",
        "martelo":          ":material/hardware:",
        "extintor":         ":material/fire_extinguisher:",
        "luz":              ":material/lightbulb:",
        "lampada":          ":material/lightbulb:",

        # Controle de Versão e Deploy
        "deploy":           ":material/rocket_launch:",
        "pacote":           ":material/inventory_2:",
        "pergaminho":       ":material/history_edu:",
        "atualizar":        ":material/refresh:",
        "reiniciar":        ":material/restart_alt:",

        # Esportes e Atividades
        "bailarina":        ":material/nightlife:",
        "bola futebol":     ":material/sports_soccer:",
        "bola basquete":    ":material/sports_basketball:",
        "corrida":          ":material/directions_run:",

        # Correto e Sucesso
        "correto":          ":material/check_circle:",
        "verificado":       ":material/verified:",
        "positivo":         ":material/thumb_up:",
        "alvo":             ":material/my_location:",
        "ok":               ":material/done:",

        # Dinheiro e Riqueza
        "dinheiro":         ":material/payments:",
        "moeda":            ":material/monetization_on:",
        "cartão crédito":   ":material/credit_card:",
        "diamante":         ":material/diamond:",
        "pagamento":        ":material/point_of_sale:",
        "banco":            ":material/account_balance:",
        "gráfico alta":     ":material/trending_up:",
        "gráfico queda":    ":material/trending_down:",
        "maleta dinheiro":  ":material/business_center:",
        "troféu":           ":material/emoji_events:",
        "carteira":         ":material/account_balance_wallet:",
        "investimento":     ":material/show_chart:",
        "cofrinho":         ":material/savings:",

        # Setas e Direções
        "seta cima":                    ":material/arrow_upward:",
        "seta baixo":                   ":material/arrow_downward:",
        "seta direita":                 ":material/arrow_forward:",
        "seta esquerda":                ":material/arrow_back:",
        "seta circular horária":        ":material/rotate_right:",
        "seta circular anti-horária":   ":material/rotate_left:",
        "seta atualizar":               ":material/sync:",
        "seta loop":                    ":material/loop:",
        "seta vertical":                ":material/swap_vert:",
        "seta horizontal":              ":material/swap_horiz:",

        # Círculos e Formas
        "circulo":          ":material/circle:",
        "quadrado":         ":material/square:",
        "estrela":          ":material/star:",
        "coração":          ":material/favorite:",

        # Pessoas e Social
        "pessoa":           ":material/person:",
        "grupo":            ":material/group:",
        "familia":          ":material/family_restroom:",
        "criança":          ":material/child_care:",
        "admin":            ":material/admin_panel_settings:",
        "perfil":           ":material/account_circle:",

        # Localização
        "mapa":             ":material/map:",
        "pin":              ":material/location_on:",
        "casa":             ":material/home:",
        "loja":             ":material/store:",
        "escola":           ":material/school:",
        "hospital":         ":material/local_hospital:",
        "bandeira":         ":material/flag:",

        # Mídia e Comunicação
        "foto":             ":material/photo:",
        "câmera":           ":material/camera_alt:",
        "vídeo":            ":material/videocam:",
        "microfone":        ":material/mic:",
        "som":              ":material/volume_up:",
        "música":           ":material/music_note:",
        "notificação":      ":material/notifications:",
        "email":            ":material/email:",
        "mensagem":         ":material/message:",
        "chat":             ":material/chat:",
        "telefone":         ":material/phone:",

        # UI / Interface
        "menu":             ":material/menu:",
        "busca":            ":material/search:",
        "filtro":           ":material/filter_list:",
        "configuração":     ":material/settings:",
        "fechar":           ":material/close:",
        "adicionar":        ":material/add:",
        "remover":          ":material/remove:",
        "editar":           ":material/edit:",
        "salvar":           ":material/save:",
        "compartilhar":     ":material/share:",
        "favorito":         ":material/star:",
        "curtir":           ":material/thumb_up:",
        "bloquear":         ":material/block:",
        "info":             ":material/info:",
        "ajuda":            ":material/help:",
        "voltar":           ":material/arrow_back:",
        "avançar":          ":material/arrow_forward:",
        "home":             ":material/home:",
        "login":            ":material/login:",
        "logout":           ":material/logout:",
        "visível":          ":material/visibility:",
        "invisível":        ":material/visibility_off:",
        "cadeado":          ":material/lock:",
        "desbloqueado":     ":material/lock_open:",
        "download":         ":material/download:",
        "upload":           ":material/upload:",
        "imprimir":         ":material/print:",
        "recortar":         ":material/content_cut:",
        "copiar":           ":material/content_copy:",
        "colar":            ":material/content_paste:",
        "desfazer":         ":material/undo:",
        "refazer":          ":material/redo:",
        "expandir":         ":material/expand_more:",
        "recolher":         ":material/expand_less:",
        "tela cheia":       ":material/fullscreen:",
        "minimizar":        ":material/fullscreen_exit:",
        "modo escuro":      ":material/dark_mode:",
        "modo claro":       ":material/light_mode:",

        # Tempo e Data
        "relógio":          ":material/schedule:",
        "calendário":       ":material/calendar_today:",
        "alarme":           ":material/alarm:",
        "temporizador":     ":material/timer:",
        "histórico":        ":material/history:",

        # Gráficos e Dados
        "gráfico barra":    ":material/bar_chart:",
        "gráfico pizza":    ":material/pie_chart:",
        "gráfico linha":    ":material/show_chart:",
        "tabela":           ":material/table_chart:",
        "dados":            ":material/data_object:",
        "dashboard":        ":material/dashboard:",
        "relatório":        ":material/summarize:",
    }

    ret = []

    if nome in icons:
        icone = icons[nome]
        ret.append(icone)

        if quantidade:
            ret.append((icone + " ") * (quantidade - 1))

    if texto:
        ret.append(f" {texto}")

    return "".join(ret)


def ver_todos_mat(st) -> None:


    # Ordena em ordem alfabética
    ordenado = sorted(_MATERIAIS)

    n_cols = 5
    for i in range(0, len(ordenado), n_cols):
        batch = ordenado[i : i + n_cols]
        cols = st.columns(n_cols)
        for col, nome_pt in zip(cols, batch):
            with col:
                st.markdown(
                    f"{Material(nome_pt)} - {nome_pt}",
                    unsafe_allow_html=True
                )