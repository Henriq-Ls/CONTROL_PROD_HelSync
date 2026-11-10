"""Consulta de vendas e registros de estoque do Marketplace."""

from __future__ import annotations

import sqlite3

from PySide6.QtWidgets import QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from _APP_.PySide6_core import DB_PATH, init_database


class RecordsTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        self.refresh_button = QPushButton("Atualizar registros")
        self.refresh_button.clicked.connect(self.refresh)
        root.addWidget(self.refresh_button)
        self.table = QPlainTextEdit()
        self.table.setReadOnly(True)
        root.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        init_database()
        with sqlite3.connect(DB_PATH) as conn:
            vendas = conn.execute(
                "SELECT ID, DATA, NOME_PRODUTO, KIT, OBSERVACOES FROM VENDAS"
            ).fetchall()
            marketplace = conn.execute(
                "SELECT ID, NOME_PRODUTO, IMAGEM, TITULO FROM MARKET_PLACE"
            ).fetchall()
        linhas = ["VENDAS"]
        linhas.extend(
            " | ".join(str(valor or "") for valor in row) for row in vendas
        )
        linhas.append("\nMARKET_PLACE")
        linhas.extend(
            " | ".join(str(valor or "") for valor in row)
            for row in marketplace
        )
        self.table.setPlainText("\n".join(linhas))
