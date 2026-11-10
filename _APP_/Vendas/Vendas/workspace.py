"""Workspace de vendas realizado com registro e histórico."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from .App_Vendas_PySide6 import VendasTab


class VendasWorkspace(VendasTab):
    """Agrupa as abas de registrar vendas e consultar o histórico."""

    currentChanged = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.pages.currentChanged.connect(self.currentChanged.emit)

    def indexOf(self, widget: QWidget) -> int:
        return self.pages.indexOf(widget)

    def currentWidget(self) -> QWidget | None:
        return self.pages.currentWidget()

    def setCurrentWidget(self, widget: QWidget) -> None:
        self.pages.setCurrentWidget(widget)
