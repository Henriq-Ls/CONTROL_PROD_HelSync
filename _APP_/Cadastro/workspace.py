"""Abas da área de cadastro e preparação temporária de produtos."""

from __future__ import annotations

from PySide6.QtWidgets import QTabWidget, QWidget


class CadastroWorkspace(QTabWidget):
    """Agrupa as telas do fluxo que ainda depende da fila de entrada."""

    def __init__(
        self,
        cadastro: QWidget,
        criacao: QWidget,
        resultados: QWidget,
        montar_anuncio: QWidget,
        midias_avulsas: QWidget,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("cadastroWorkspace")
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.addTab(cadastro, "Cadastro")
        self.addTab(criacao, "Criação")
        self.addTab(resultados, "Revisar mídias")
        self.addTab(montar_anuncio, "Montar anúncio")
        self.addTab(midias_avulsas, "Medidas avulsas")
