# _CONFIGURA_/__init__.py
"""
Fonte única de verdade para TODOS os valores fixos do projeto.
Nenhum outro arquivo pode ter cores, atalhos, tamanhos ou qualquer
valor fixo — tudo vem daqui.

SEÇÕES:
    APPDATA
    APLICAÇÃO
    FONTES
    JANELA PRINCIPAL
    ATALHOS
    CORES — paleta base
    CORES — UI escuro
    ESTILOS QSS prontos
"""

import os

# ══════════════════════════════════════════════════════════════════════════════
# MODO DE EXECUÇÃO
# ══════════════════════════════════════════════════════════════════════════════
# True  → desenvolvimento: log em nível DEBUG, erros detalhados
# False → produção: log em nível ERROR apenas, sem stack traces no terminal
MODO_DEV = True

# ══════════════════════════════════════════════════════════════════════════════
# APPDATA — pasta do usuário no sistema operacional
# ══════════════════════════════════════════════════════════════════════════════
# Windows: %APPDATA%\nome_do_projeto
# Linux/Mac: ~/nome_do_projeto
PASTA_APPDATA = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "hen-place-control"
)

# ══════════════════════════════════════════════════════════════════════════════
# APLICAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
VERSAO_APP  = "v1.0.0"
TITULO_APP  = "Hen Place Control"
TEMA_QT     = "Fusion"             # tema base do Qt

# Caminhos absolutos — independentes do CWD de execução
_PROJETO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MIDIAS_DIR  = os.path.join(_PROJETO_DIR, "Midias")
IMAGEM_ICO   = os.path.join(_MIDIAS_DIR, "icone.ico")
IMAGEM_LOGO  = os.path.join(_MIDIAS_DIR, "logo.png")

# ══════════════════════════════════════════════════════════════════════════════
# FONTES
# ══════════════════════════════════════════════════════════════════════════════
FONTE_NOME_UI       = "Segoe UI"
FONTE_TAMANHO_BASE  = 10     # pontos — fonte padrão da QApplication

FONTE_TAMANHO_TITULO  = 13   # px (CSS/QSS)
FONTE_TAMANHO_INFO    = 12
FONTE_TAMANHO_LABEL   = 11
FONTE_TAMANHO_DETALHE = 10
FONTE_TAMANHO_SUTIL   = 9

# ══════════════════════════════════════════════════════════════════════════════
# JANELA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
LARGURA_PADRAO = 1280
ALTURA_PADRAO  = 800
LARGURA_MIN    = 1024
ALTURA_MIN     = 600

# ══════════════════════════════════════════════════════════════════════════════
# ATALHOS
# ══════════════════════════════════════════════════════════════════════════════
ATALHO_SAIR           = "Alt+F4"
ATALHO_SALVAR         = "Ctrl+S"
ATALHO_ABRIR          = "Ctrl+O"
ATALHO_NOVO           = "Ctrl+N"
# Adicione atalhos específicos do projeto abaixo

# ══════════════════════════════════════════════════════════════════════════════
# CORES — paleta base (nomes semânticos)
# ══════════════════════════════════════════════════════════════════════════════
PRETO          = "#0D1726"
PRETO_FOSCO    = "#111D2F"
CINZA_ESCURO   = "#1B2A3D"
BRANCO         = "#F3F6FA"
AMARELO        = "#F5C15C"
AMBAR          = "#D99A2B"
VERDE          = "#35C58A"
TURQUESA       = "#2CB9A7"
AZUL_CLARO     = "#5CA9E6"
AZUL           = "#2878C8"
AZUL_ESCURO    = "#1E4266"
CORAL          = "#EF7474"
VERMELHO       = "#C94B5A"
LARANJA_ESCURO = "#B86E28"

# ══════════════════════════════════════════════════════════════════════════════
# CORES — UI escuro (usadas nos estilos QSS abaixo)
# ══════════════════════════════════════════════════════════════════════════════
COR_BG_APP           = "#101B2B"   # fundo principal
COR_BG_SECUNDARIO    = "#15253A"   # menubar, toolbar, status bar
COR_BG_TERCIARIO     = "#20334B"   # menus, inputs, cards
COR_BG_CAMPO         = "#17283F"   # dialogs, list widgets
COR_BG_ESCURO        = "#0B1421"   # scrollbars, fundos muito escuros
COR_BORDA            = "#2D435D"   # bordas gerais
COR_BORDA_CLARA      = "#46627E"   # bordas de inputs, handles
COR_TEXTO            = "#F3F6FA"   # texto principal
COR_TEXTO_SECUNDARIO = "#B4C2D3"   # labels secundários
COR_TEXTO_SUTIL      = "#8294AA"   # placeholders
COR_TEXTO_INATIVO    = "#6D7E93"   # botões desabilitados
COR_ACENTO           = "#2CB9A7"   # destaque principal / ações
COR_ACENTO_HOVER     = "#45D2C0"
COR_ACENTO_ATIVO     = "#1D7E7A"   # seleção / checked
COR_ACENTO_BORDA     = "#69E2D2"   # borda do item ativo
COR_SUCESSO          = "#35C58A"
COR_SUCESSO_HOVER    = "#55D99C"
COR_PERIGO           = "#D65766"

# ══════════════════════════════════════════════════════════════════════════════
# ESTILOS QSS — prontos para uso direto
# ══════════════════════════════════════════════════════════════════════════════

ESTILO_ESCURO_GLOBAL = f"""
QMainWindow, QWidget {{
    background: {COR_BG_APP};
    color: {COR_TEXTO};
    font-family: "{FONTE_NOME_UI}", Arial, sans-serif;
    font-size: {FONTE_TAMANHO_LABEL}px;
}}
QMainWindow {{ background: {COR_BG_APP}; }}
QFrame {{ background: transparent; }}
QSplitter::handle {{ background: {COR_BORDA}; }}
QSplitter::handle:hover {{ background: {COR_ACENTO}; }}
QGroupBox {{
    background: {COR_BG_SECUNDARIO};
    color: {COR_TEXTO};
    border: 1px solid {COR_BORDA};
    border-radius: 7px;
    margin-top: 12px;
    padding: 12px 8px 8px 8px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {COR_ACENTO};
    background: {COR_BG_SECUNDARIO};
}}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox,
QSpinBox, QDoubleSpinBox, QListWidget, QTreeWidget, QTableWidget {{
    background: {COR_BG_CAMPO};
    color: {COR_TEXTO};
    border: 1px solid {COR_BORDA_CLARA};
    border-radius: 5px;
    padding: 6px 8px;
    selection-background-color: {COR_ACENTO_ATIVO};
    selection-color: {COR_TEXTO};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    background: {COR_BG_TERCIARIO};
    border: 1px solid {COR_ACENTO_BORDA};
}}
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled,
QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
    background: {COR_BG_ESCURO};
    color: {COR_TEXTO_INATIVO};
    border-color: {COR_BORDA};
}}
QComboBox QAbstractItemView {{
    background: {COR_BG_TERCIARIO};
    color: {COR_TEXTO};
    border: 1px solid {COR_BORDA_CLARA};
    selection-background-color: {COR_ACENTO_ATIVO};
    selection-color: {COR_TEXTO};
}}
QPushButton {{
    background: {COR_BG_TERCIARIO};
    color: {COR_TEXTO};
    border: 1px solid {COR_BORDA_CLARA};
    border-radius: 5px;
    padding: 7px 14px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {COR_ACENTO};
    border-color: {COR_ACENTO_BORDA};
    color: {BRANCO};
}}
QPushButton:pressed {{ background: {COR_ACENTO_ATIVO}; }}
QPushButton:disabled {{
    background: {COR_BG_TERCIARIO};
    color: {COR_TEXTO_INATIVO};
    border-color: {COR_BORDA};
}}
QTabWidget::pane {{
    background: {COR_BG_APP};
    border: 1px solid {COR_BORDA};
    border-radius: 5px;
    top: -1px;
}}
QTabBar::tab {{
    background: {COR_BG_SECUNDARIO};
    color: {COR_TEXTO_SECUNDARIO};
    border: 1px solid {COR_BORDA};
    border-bottom: none;
    padding: 8px 16px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: {COR_ACENTO_ATIVO};
    color: {BRANCO};
    border-color: {COR_ACENTO_BORDA};
}}
QTabBar::tab:hover {{ background: {COR_BG_TERCIARIO}; color: {COR_TEXTO}; }}
QScrollArea, QScrollArea > QWidget > QWidget {{
    background: transparent;
    border: none;
}}
QMenuBar {{
    background: {COR_BG_SECUNDARIO};
    color: {COR_TEXTO};
    border-bottom: 1px solid {COR_BORDA};
}}
QMenuBar::item:selected {{ background: {COR_ACENTO}; }}
QMenu {{
    background: {COR_BG_TERCIARIO};
    color: {COR_TEXTO};
    border: 1px solid {COR_BORDA_CLARA};
}}
QMenu::item:selected {{ background: {COR_ACENTO}; }}
QToolBar {{
    background: {COR_BG_SECUNDARIO};
    border-bottom: 1px solid {COR_BORDA};
    spacing: 4px;
    padding: 2px;
}}
QToolButton {{
    background: transparent;
    color: {COR_TEXTO};
    border: none;
    padding: 4px 8px;
    border-radius: 3px;
}}
QToolButton:hover   {{ background: {COR_BG_TERCIARIO}; }}
QToolButton:pressed {{ background: {COR_BG_TERCIARIO}; }}
QCheckBox, QRadioButton {{
    color: {COR_TEXTO};
    spacing: 6px;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 15px;
    height: 15px;
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background: {COR_ACENTO};
    border: 1px solid {COR_ACENTO_BORDA};
}}
QStatusBar {{
    background: {COR_BG_SECUNDARIO};
    color: {COR_TEXTO_SECUNDARIO};
    border-top: 1px solid {COR_BORDA};
    font-size: {FONTE_TAMANHO_DETALHE}px;
}}
QScrollBar:vertical {{
    background: {COR_BG_ESCURO}; width: 10px; border: none;
}}
QScrollBar::handle:vertical {{
    background: {COR_BORDA_CLARA}; border-radius: 5px; min-height: 20px;
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {COR_BG_ESCURO}; height: 10px; border: none;
}}
QScrollBar::handle:horizontal {{
    background: {COR_BORDA_CLARA}; border-radius: 5px; min-width: 20px;
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{ width: 0; }}
QProgressBar {{
    background: {COR_BG_CAMPO};
    border: 1px solid {COR_BORDA_CLARA};
    border-radius: 5px;
    text-align: center;
    color: {COR_TEXTO};
}}
QProgressBar::chunk {{
    background: {COR_ACENTO};
    border-radius: 4px;
}}
QToolTip {{
    background: {COR_BG_TERCIARIO};
    color: {COR_TEXTO};
    border: 1px solid {COR_BORDA_CLARA};
    padding: 5px;
}}
"""

ESTILO_DIALOGO_ESCURO = f"""
QDialog    {{ background: {COR_BG_APP}; color: {COR_TEXTO}; }}
QLabel     {{ color: {COR_TEXTO_SECUNDARIO}; }}
QGroupBox  {{
    background: {COR_BG_SECUNDARIO};
    color: {COR_TEXTO};
    border: 1px solid {COR_BORDA};
    border-radius: 7px;
    margin-top: 12px;
    padding: 10px 8px 8px 8px;
    font-size: {FONTE_TAMANHO_LABEL}px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: {COR_ACENTO};
    background: {COR_BG_SECUNDARIO};
}}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
QListWidget {{
    background: {COR_BG_CAMPO};
    color: {COR_TEXTO};
    border: 1px solid {COR_BORDA_CLARA};
    border-radius: 5px;
    padding: 6px 8px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
    background: {COR_BG_TERCIARIO};
    border-color: {COR_ACENTO_BORDA};
}}
QPushButton {{
    background: {COR_ACENTO};
    color: {BRANCO};
    border: 1px solid {COR_ACENTO_BORDA};
    border-radius: 5px;
    padding: 7px 14px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {COR_ACENTO_HOVER}; }}
QDialogButtonBox QPushButton {{
    min-width: 90px;
}}
"""

ESTILO_BTN_PRIMARIO = f"""
QPushButton {{
    background: {COR_ACENTO};
    color: {BRANCO};
    border: none;
    padding: 8px 20px;
    border-radius: 4px;
    font-size: {FONTE_TAMANHO_INFO}px;
    font-weight: bold;
}}
QPushButton:hover    {{ background: {COR_ACENTO_HOVER}; }}
QPushButton:disabled {{ background: {COR_BG_TERCIARIO}; color: {COR_TEXTO_INATIVO}; }}
"""

ESTILO_BTN_CANCELAR = f"""
QPushButton {{
    background: {COR_BORDA_CLARA};
    color: {COR_TEXTO_SECUNDARIO};
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
}}
QPushButton:hover {{ background: {COR_TEXTO_SUTIL}; }}
"""

ESTILO_LIST_WIDGET = f"""
QListWidget {{
    background: {COR_BG_APP};
    border: none;
    color: {COR_TEXTO};
}}
QListWidget::item {{ padding: 4px; border-bottom: 1px solid {COR_BORDA}; }}
QListWidget::item:selected {{ background: {COR_ACENTO_ATIVO}; }}
QListWidget::item:hover    {{ background: {COR_BG_TERCIARIO}; }}
"""

ESTILO_PROGRESSBAR = f"""
QProgressBar {{
    background: {COR_BG_TERCIARIO};
    border: 1px solid {COR_BORDA_CLARA};
    border-radius: 3px;
}}
QProgressBar::chunk {{
    background: {COR_ACENTO};
    border-radius: 2px;
}}
"""
