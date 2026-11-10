"""Abas da área Marketplace."""

from __future__ import annotations

from PySide6.QtWidgets import QTabWidget, QWidget


class MarketplaceWorkspace(QTabWidget):
    """Agrupa anúncios concluídos e as telas operacionais relacionadas."""

    def __init__(
        self,
        anuncios: QWidget,
        anunciar: QWidget,
        sociais: QWidget,
        registros: QWidget,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("marketplaceWorkspace")
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.addTab(anuncios, "Anúncios")
        self.addTab(anunciar, "Anunciar")
        self.addTab(sociais, "Sociais")
        self.addTab(registros, "Registros")
