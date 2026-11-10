"""Abas da área Configuração."""

from __future__ import annotations

from PySide6.QtWidgets import QTabWidget, QWidget


class ConfiguracaoWorkspace(QTabWidget):
    """Agrupa as opções e ferramentas de configuração do aplicativo."""

    def __init__(
        self,
        configuracoes: QWidget,
        prompts: QWidget,
        banco_dados: QWidget,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("configuracaoWorkspace")
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.addTab(configuracoes, "Configurações")
        self.addTab(prompts, "Prompts")
        self.addTab(banco_dados, "Banco de dados")
