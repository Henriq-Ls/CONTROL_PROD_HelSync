# _ULTILIDADES_/icones.py
"""
Centraliza todos os ícones do projeto.

Usa qtawesome como fonte principal.
Se qtawesome não estiver instalado, retorna QIcon vazio silenciosamente.

Uso:
    from _ULTILIDADES_.icones import icone, icone_colorido

    btn.setIcon(icone("fa5s.folder-open"))
    btn.setIcon(icone_colorido("fa5s.save", "#3a7bd5"))

Referência de ícones: https://fontawesome.com/icons (prefixo fa5s, fa5r, fa5b, mdi, ei)
"""

from PySide6.QtGui import QIcon, QColor
from _CONFIGURA_ import AMARELO, COR_TEXTO, COR_ACENTO, COR_PERIGO, COR_SUCESSO


def icone(nome: str, cor: str = COR_TEXTO) -> QIcon:
    """
    Retorna um QIcon do qtawesome.
    Se qtawesome não estiver disponível, retorna QIcon vazio.

    Args:
        nome: nome do ícone (ex: "fa5s.folder-open", "mdi.content-save")
        cor:  cor hexadecimal (padrão: COR_TEXTO do _CONFIGURA_)
    """
    try:
        import qtawesome as qta
        return qta.icon(nome, color=cor)
    except Exception:
        return QIcon()


def icone_colorido(nome: str, cor: str) -> QIcon:
    """Ícone com cor específica."""
    return icone(nome, cor)


# ── Ícones pré-definidos (expanda conforme o projeto) ────────────────────────
# Importe estes em vez de escrever strings de ícone espalhadas pelo código.

def ico_salvar()    -> QIcon: return icone("fa5s.save",         COR_ACENTO)
def ico_abrir()     -> QIcon: return icone("fa5s.folder-open",  COR_ACENTO)
def ico_novo()      -> QIcon: return icone("fa5s.file",         COR_ACENTO)
def ico_fechar()    -> QIcon: return icone("fa5s.times",        COR_TEXTO)
def ico_config()    -> QIcon: return icone("fa5s.cog",          COR_TEXTO)
def ico_info()      -> QIcon: return icone("fa5s.info-circle",  COR_ACENTO)
def ico_aviso()     -> QIcon: return icone("fa5s.exclamation-triangle", AMARELO)
def ico_erro()      -> QIcon: return icone("fa5s.times-circle", COR_PERIGO)
def ico_ok()        -> QIcon: return icone("fa5s.check-circle", COR_SUCESSO)
def ico_atualizar() -> QIcon: return icone("fa5s.sync-alt",     COR_TEXTO)
def ico_buscar()    -> QIcon: return icone("fa5s.search",       COR_TEXTO)
def ico_lixo()      -> QIcon: return icone("fa5s.trash-alt",    COR_PERIGO)
def ico_adicionar() -> QIcon: return icone("fa5s.plus",         COR_SUCESSO)
