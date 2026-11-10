"""Abas da área Ferramentas."""

from __future__ import annotations

from PySide6.QtWidgets import QTabWidget, QWidget


class FerramentasWorkspace(QTabWidget):
    """Agrupa as configurações globais e os prompts do aplicativo."""

    def __init__(
        self,
        configuracoes: QWidget,
        prompts: QWidget,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ferramentasWorkspace")
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.addTab(configuracoes, "Configurações")
        self.addTab(prompts, "Prompts")
