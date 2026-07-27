# 📁 _APP_/Html_app.py
from _GERENTE_PROJETO_.Decorar.Cor_Html import Cores
# VARIÁVEIS DE TEMA =========================
# Lista de fontes para campos (inputs, selects, botões) - fontes de programação
FONTES_TEXTO = ["Helvetica", "Arial", "Verdana", "Tahoma", "Times New Roman", "Georgia", "Comic Sans MS",
                "Fira Code", "JetBrains Mono", "Source Code Pro", "Source Sans Pro", "Press Start 2P", "Pixelify Sans",
                "Silkscreen","Share Tech Mono", "Inconsolata", "Consolas", "Courier New", "Monospace"]

COR_WIDGET = Cores("preto_fosco")           # "#1E1E1E" • Widgets • Inputs • Containers
COR_CAMPO = Cores("branco")           # "#FFFFFF" • Campos de entrada
COR_MENU = Cores("laranja_fosco")           # "#C68642" • Botões • Logo • Destaques
PASSR_COR = Cores("cinza")      # "#3A3A3A" • Hover • Seleção • Mouse
THEMA_APP1 = Cores("preto_fosco")           # "#0F0F0F" • Fundo principal do sistema
COR_TEXTO = Cores("verde_fosco")            # "#22C576" • Texto principal
BG_STYLE = Cores("preto")                 # Preto absoluto fundo geral (não tem na função)
SD_STYLE = Cores("cinza_fosco")      # "#181818" • Sidebar cinza carvão
WD_STYLE = Cores("azul_escuro")     # "#1A1A1A" • Fundo widgets internos

# BORDAS  =========================
BORDA = 1
BORDA_STIL = "solid"
RADIO = 6

# FONTES =========================
FONTE_MENU = "JetBrains Mono, monospace"   # Fonte premium interface
FONTE_CAMPO = "Fira Code', monospace"       # Fonte terminal/código

# TAMANHOS =========================
TAM_MENU = 16
TAM_CAMPO = 15

def cor_semelhante(hex_color, fator=20):
    """ Retorna uma cor levemente diferente (mais clara)."""
    hex_color = hex_color.lstrip("#")
    r = min(255, int(hex_color[0:2], 16) + fator)
    g = min(255, int(hex_color[2:4], 16) + fator)
    b = min(255, int(hex_color[4:6], 16) + fator)

    return f"#{r:02x}{g:02x}{b:02x}"

# ⚠️  função grande (502 linhas)
def Carregamento_Temas(st):
    """
    Carrega os temas a partir de uma string fornecida.

    Esta função processa a string de entrada e extrai os temas relevantes, retornando-os em um formato estruturado.

    Args:
        st (str): A string que contém os temas a serem carregados.

    Returns:
        list: Uma lista de temas extraídos da string de entrada.
    """
    #cor_test = st.color_picker('cor')
    """Aplica um tema visual personalizado completo na interface do Streamlit."""
    # --------------------------------------------------------------------- CARREGAMENTO DE CUSTOMIZAÇÃO
    page_bg = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;700&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,400;0,700;1,400;1,700&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Source+Code+Pro:ital,wght@0,400;1,400&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Pixelify+Sans:wght@400;700&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Silkscreen:wght@400;700&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

    [data-testid="stPopoverButton"]{{                                               /* POPOVER */
        background-color: {COR_WIDGET} !important;
        border: {BORDA}px {BORDA_STIL} {COR_CAMPO} !important;
    }}

    .stPopover button {{                                                            /* POPOVER label */
        color: {COR_MENU} !important;
        font-family: {FONTE_MENU} !important;
        font-size: {TAM_MENU}px !important;

    }}
    [data-testid="stMarkdown"] p {{                               /* MARKDOWS E WRITES */
        color: {COR_TEXTO} !important;
        font-size: {TAM_MENU}px !important;
        font-style: italic !important;
    }}

    input {{                                                        /* PARA TODOS OS INPUTS */
        color: {COR_CAMPO} !important;
        font-family: {FONTE_CAMPO} !important;
        font-size: {TAM_MENU}px !important;
    }}

    div[data-testid="stButton"] button {{                               /* Botões */
        color: {COR_MENU} !important;
        min-height: 40px !important;
        border-radius: {RADIO}px !important;
        padding: none !important;
        padding-top: 0% !important;
        padding-bottom: 0% !important;

    }}
    .st-emotion-cache-1kl7f1u p {{                                  /* Botões labal*/
        font-family: {FONTE_MENU} !important;
        font-size: {TAM_MENU}px !important;
        margin: 0 !important;
    }}

    div[data-testid="stButton"] button:hover {{                             /* AO PASSAR O MAUSE */
        background-color: { THEMA_APP1} !important;
        transform: scale(1.02) !important;
    }}

    .stButton[data-testid="stButton"] button[kind="secondary"] {{             /* AO PASSAR O MAUSE kind secondary */
        background-color: {THEMA_APP1} !important;
        border: {BORDA}px {BORDA_STIL} {COR_CAMPO} !important;
    }}

    .stButton[data-testid="stButton"] button[kind="tertiary"] {{             /* AO PASSAR O MAUSE kind tertiary */
        color: {COR_CAMPO} !important;
    }}

    div[data-testid="stButton"] button[kind="primary"] {{                    /* GARANTE COR DO type="primary" */
        background-color: {WD_STYLE} !important;
        border: {BORDA}px solid red !important;
    }}

    div[data-testid="stForm"] {{                                            /* FORM  FORMULARIO */
        background-color: {cor_semelhante(COR_WIDGET)} !important;
        padding: none !important;
        padding-top: 0% !important;
        padding-bottom: 0% !important;

    }}
    [data-testid="stFormSubmitButton"] [data-testid="stBaseButton-primaryFormSubmit"] {{    /* FORM  BOTAO */
       padding-top: 0% !important;
       padding-left: 0% !important;
       padding-right: 0% !important;
       padding-bottom: 0% !important;
        color: {COR_CAMPO} !important;
        border-radius: {RADIO}px !important;
        border: {BORDA}px {BORDA_STIL} {COR_CAMPO} !important;

    }}
    div[data-testid="stColumn"] {{                                            /* COLUNAS st.columns() */
        padding-top: 0% !important;
        padding-left: 0% !important;
        padding-right: 0% !important;
        padding-bottom: 0% !important;

    }}

    [data-testid="stSlider"] p {{                                           /* SLIDER */
        color: {COR_MENU} !important;
        font-size: {TAM_MENU}px !important;
    }}

    [data-testid="stRadio"] p {{                                           /* RADIO */
        color: {COR_MENU} !important;
        font-family: {FONTE_MENU} !important;
        font-size: {TAM_MENU}px !important;
    }}
                                                                                  /* CHECKBOX */
    [data-testid="stCheckbox"] div {{
        font-family: {FONTE_CAMPO} !important;
        font-size: {TAM_CAMPO - 2}px !important;

        text-decoration: underline !important;
        padding: 1px !important;
        color: white !important;

    }}
    .stChatInput textarea {{
        font-family: {FONTE_CAMPO}, sans-serif !important;
        font-size: {TAM_CAMPO}px !important;
        color: {COR_CAMPO} !important;

    }}

    div[data-testid="stCheckbox"] label:hover {{                             /* AO PASSAR O MAUSE CHECKBOX */
        background-color: {PASSR_COR} !important;
        transform: scale(1.05) !important;

    }}

    input[type="checkbox"]:checked + div {{                                 /* checkbox MARCADO */
        background-color: {COR_WIDGET} !important;
    }}

   [data-testid="stColorPicker"] {{                                           /* COLOR PICK */
        color: {COR_MENU} !important;
        font-family: {FONTE_CAMPO} !important;
        font-size: {TAM_CAMPO}px !important;

    }}
    .stColorPicker label p {{                                        /* COLOR labrl */
        font-family: {FONTE_MENU} !important;
    }}

    [data-testid="stNumberInput"]  {{                                            /* NUMBER */
        color: {COR_MENU} !important;
        font-family: {FONTE_MENU} !important;
        font-size: {TAM_MENU}px !important;

    }}

    .stNumberInput label p {{                                                   /* NUMBER labrl */
        font-family: {FONTE_MENU} !important;
    }}

    div[data-testid="stSelectbox"] div[data-baseweb="select"] {{                                         /* SELCTBOX */
        background-color: {COR_WIDGET} !important;
        color: {COR_CAMPO} !important;
        font-family: {FONTE_CAMPO} !important;
        font-size: {TAM_MENU}px !important;
        border-radius: {RADIO}px !important;
        border: {BORDA}px {BORDA_STIL} {COR_CAMPO} !important;
    }}

        [data-testid="stSelectbox"] p{{                           /* LABEL SELCBOX*/
        color: {COR_MENU} !important;
        font-family: {FONTE_MENU} !important;
        font-size: {TAM_MENU}px !important;
    }}

    ul[data-testid="stSelectboxVirtualDropdown"]  {{                                         /* SELCTBOX */
        background-color: {THEMA_APP1} !important;
        color: {COR_CAMPO} !important;
        font-family: {FONTE_CAMPO} !important;
        font-size: {TAM_MENU}px !important;
        border-radius: {RADIO}px !important;
        border: {BORDA}px {BORDA_STIL} {COR_CAMPO} !important;
    }}

    [data-testid="stTextInput"] p{{                                            /* TEXT INPUT */
        color: {COR_MENU} !important;
        font-size: {TAM_MENU}px !important;

    }}
    .stTextInput label .st-emotion-cache-3nb1lh p {{
        font-family: {FONTE_MENU} !important;
        font-size: {TAM_MENU}px !important;

    }}

    [data-testid="stExpander"] {{                                               /* EXPANDER */
        background-color: {BG_STYLE} !important;
        border-radius: 0px !important;
    }}

    .stExpander summary .st-emotion-cache-11fa8fd p {{                          /* EXPANDER lABEL */
        font-family: {FONTE_MENU} !important;
        font-size: {TAM_MENU}px !important;
        color: {COR_MENU} !important;

    }}

    [data-testid="stElementContainerTTTT"] {{                               /* TODOS ELEMENTOSCONTAINER INCLUSOVE SELECT E EXPANDER */
        color: {COR_MENU} !important;
        border-radius: {RADIO}px !important;
        border: {BORDA}px {BORDA_STIL} {COR_CAMPO} !important;
    }}

    header.stAppHeader {{                                               /* HEADER */
        padding-left: 0% !important;
        margin-top: 2% !important;
        left:  83% !important;
        width: 15% !important;
        height: 3% !important;
         /* BACKGROUND TRANSPARENTE */
        background: transparent !important;
        background-color: transparent !important;
        /* Borda transparente também */
        border: none !important;
        box-shadow: none !important;

    }}

    .block-container {{                                                                 /* BLOCO PRINCIPAL BODY*/
        margin-top: -5% !important;
        margin-left: 0px !important;
        padding-left: 5% !important;
        margin-right: 5px !important;
        width: 109% !important;
        max-width: none !important;
        background-color: {BG_STYLE} !important;

    }}

    section[data-testid="stSidebar"] {{                                         /* SIDEBAR */
        background-color: {SD_STYLE} !important;

        width: 400px !important;
        height: 110% !important;
        margin-top: -1% !important;
        margin-left: -0% !important;

        border: {BORDA + 1}px solid  {cor_semelhante(COR_CAMPO)} !important;
    }}

    [data-testid="stSidebarCollapseButton"] {{                                  /* BOTÃO DO SIDEBAR DE CIMA >> */
        margin-top: 3% !important;

        position: fixed !important;
        background-color: {COR_MENU} !important;
        border-radius: {RADIO}px !important;
        border: {BORDA}px {BORDA_STIL}ortant;
    }}

    [data-testid="stExpandSidebarButton"] {{                                    /* BOTÃO DO SIDEBAR DE BAIXO << */
        background-color: {COR_CAMPO} !important;
        position: fixed !important;
        top: 5% !important;
        left: -2px !important;
        height: 11px !important;
        opacity: 1 !important;
        z-index: 9999 !important;
    }}

    div[data-testid="stVerticalBlock"][class*="st-key-Bra-o_Sidebar"] {{ /* MENU de botao POUPAP - AO LADO DO SIDEBAR */
        background-color: {THEMA_APP1} !important;
        position: absolute !important;
        top: 3% !important;  /* Alinha no topo do sidebar */
        left: 70% !important;
        border-radius: {RADIO}px !important;
        border: {BORDA}px {BORDA_STIL} {COR_CAMPO} !important;
        z-index: 9999999999 !important;
        width: 600px; /* Largura fixa do seu bloco */
        transition: transform .001s ease !important; /* Animação suave */
    }}

    /* Container principal para posicionamento correto */
    section[data-testid="stAppViewContainer"] {{
        position: relative !important;
    }}

    /*    stElementContainer
    div[data-testid="stLayoutWrapper"] [class*="stElementContainer element-container st-emotion-cache-3pwa5w e12zf7d51"]{{
        background-color: {THEMA_APP1} !important;
         border-radius: {RADIO}px !important;
        border: {BORDA}px {BORDA_STIL} {COR_CAMPO} !important;

    }}  */

    [data-testid="stBaseButton-pills"] {{                               /* ST.PILLS BOTAO */
        background-color: {COR_WIDGET} !important;
        border: 0px solid {COR_CAMPO} !important;
        margin-bottom: -8% !important;

    }}

    [data-testid="stBaseButton-pillsActive"] {{
        border: 0px solid {COR_CAMPO} !important;
        padding: 2px 8px !important;                                    /* mesma altura */
        margin-bottom: 2px !important;
        border-radius: 0 !important;
        margin-bottom: -4% !important;
        padding-left: -100% !important;
    }}

    [data-testid="stBaseButton-secondary"]:has(kbd[aria-label="Shortcut Ctrl + Entereeeeeee "]){{/* BOTAO RUN */
        margin-top: -11.05% !important;
        background-color: {COR_CAMPO} !important;
        color: {COR_MENU} !important;
        position: fixed !important;
        width: 10% !important;
        right: 45% !important;
        z-index: 9999 !important;
        border: {BORDA}px {BORDA_STIL} {COR_CAMPO} !important;

         /* ✅ SCROLL HABILITADO */
        overflow: visible !important;  /* Permite conteúdo maior */
        max-height: none !important;   /* Remove limitação de altura */
        height: auto !important;       /* Altura dinâmica */
    }}

    [data-testid="stCustomComponentV1 vvvvvv"] {{                                      /* EDITORES DE CODIGOS */
        background-color: {COR_WIDGET} !important;
        border-radius: {RADIO}px !important;
        border: {BORDA}px {BORDA_STIL} {COR_CAMPO} !important;

    }}

    div[data-testid="stButton"][class*="st-key-nome_da_sua_key"] {{                     /* CONTAINERS */
        background-color: {BG_STYLE} !important;
        padding: 0 !important;
        height: 5% !important;
    }}

    [data-testid="stTextarea"][class*="st-dfs___________dd"] {{                         /* nao  ta usando */
        background-color: {COR_WIDGET} !important;
        border-radius: {RADIO + 8}px !important;
        border: {BORDA}px {BORDA_STIL} {COR_CAMPO} !important;
    }}

    [data-baseweb="base-input"] textarea  {{
        background-color: black !important;  /* Fundo do input */
        color: white  !important;             /* Cor do texto */
        border: {BORDA}px {BORDA_STIL} {COR_CAMPO} !important;
    }}

    input[data-baseweb="base-input"] textarea  {{
        background-color: black !important;  /* Fundo do input */
        color: {COR_CAMPO}  !important;             /* Cor do texto */
        border: {BORDA}px {BORDA_STIL} {COR_CAMPO} !important;
        font-family: {FONTE_CAMPO} !important;
        font-size: {TAM_MENU}px !important;
    }}

    div[data-testid="stVerticalBlock"] [class*="st-key-MenuTopo"] {{                        /* CABEÇALHO MENU TOPO */
        background-color: {THEMA_APP1} !important;

        height: 5% !important;
        padding-top: 1% !important;
        padding-bottom: -10% !important;
        position: fixed !important;
        align-items: center !important;

        top: -1.5% !important;
        z-index: 99999 !important;
        border-radius: 0px !important;
        display: flex !important;
        border: {BORDA}px {BORDA_STIL} {COR_CAMPO} !important;

    }}

    [data-baseweb="tab"] p{{
        font-family: {FONTE_MENU} !important;
        font-size: {TAM_MENU}px !important;
    }}

    div[data-testid="stTabs"][class*="st-emotion-cache-8atqhb eh1nhsq0"] {{
        background-color: {WD_STYLE} !important;
        border-radius: {RADIO}px !important;
        padding-left: 0% !important;
    }}

    /* ABAS NÃO-SELECIONADAS - CINZA */
    div[data-testid="stTabs"][class*="st-emotion-cache-8atqhb eh1nhsq0"] [data-baseweb="tab"]:not([aria-selected="true"]) {{
      color: {COR_CAMPO} !important;
      opacity: 0.8 !important;
    }}

    /* ABA ATIVA - SUA COR */
    div[data-testid="stTabs"][class*="st-emotion-cache-8atqhb eh1nhsq0"] [data-baseweb="tab"][aria-selected="true"] {{
      color: {COR_MENU} !important;
    }}

    div[data-testid="stVerticalBlock"][class*="st-key-foot1"] {{         /* */
        background-color: #00000 !important;
        position: fixed !important;
        bottom: 4% !important;
        padding-left:0% !important;
        right: 0% !important;
        z-index: 999 !important;
        display: flex !important;
        justify-content: space-between !important;
        padding: 0px !important;
        width: 100% !important;

    }}

     div[data-testid="stVerticalBlock"][class*="st-key-foot2"] {{       /*  */
        background-color: {BG_STYLE} !important;

        position: fixed !important;
        bottom: 4% !important;
        padding-left:0% !important;
        right: 0% !important;
        z-index: 99999 !important;
        display: flex !important;
        justify-content: space-between !important;
        padding: 0px !important;
        width:80% !important;
    }}

     div[data-testid="stVerticalBlock"][class*="st-key-foot3"] {{       /* */
        background-color: {BG_STYLE} !important;
        position: fixed !important;
        bottom: 4% !important;
        padding-left:0% !important;
        right: 0% !important;
        z-index: 999999 !important;
        display: flex !important;
        justify-content: space-between !important;
        padding: 0px !important;
        width:60% !important;
    }}

     div[data-testid="stVerticalBlock"][class*="st-key-foot4"] {{       /*  */
        background-color: {BG_STYLE} !important;
        position: fixed !important;
        bottom: 4% !important;
        padding-left:0% !important;
        right: 0% !important;
        z-index: 9999999 !important;
        display: flex !important;
        justify-content: space-between !important;
        padding: 0px !important;
        width:40% !important;
    }}

     div[data-testid="stVerticalBlock"][class*="st-key-foot5"] {{       /*  */
        background-color: {BG_STYLE} !important;
        position: fixed !important;
        bottom: 4% !important;
        padding-left:0% !important;
        right: 0% !important;
        z-index: 9999999 !important;
        display: flex !important;
        justify-content: space-between !important;
        padding: 0px !important;
        width:20% !important;
    }}

     div[data-testid="stVerticalBlock"][class*="st-key-Estrutura_Projeto"] {{       /*📊 Estrutura do Projeto */
        background-color: {COR_WIDGET} !important;
        color: gray !important;
        position: fixed !important;
        bottom: 0% !important;
        padding-left:0% !important;
        right: 0% !important;
        z-index: 99999999 !important;
        display: flex !important;
        justify-content: space-between !important;
        padding: 0px !important;
        width:100% !important;
    }}

    .st-key-BtnCatalogar_widget .stButton button > div {{
        justify-content: flex-start !important;
        text-align: left !important;
        margin-left: 20px !important;
        height: 30px !important;

    }}
    div[data-testid="stVerticalBlock"][class*="st-key-menu_lado_sidebar"] {{
    margin-top: -1% !important;
    border-radius: 0px !important;
    background-color: {THEMA_APP1} !important;
    border: {BORDA}px {BORDA_STIL} {COR_CAMPO} !important;

    }}

    </style>"""

    st.markdown(page_bg, unsafe_allow_html=True)

# ✅ IMPORTS NO TOPO (CORRIGIDO)
