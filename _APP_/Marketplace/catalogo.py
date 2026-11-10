"""Edição do catálogo de marketplaces sem apagar anúncios antigos."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from _APP_.product_lifecycle import (
    adicionar_marketplace,
    definir_marketplace_ativo,
    listar_marketplaces,
    migracao_concluida,
)


class MarketplaceCatalogDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Marketplaces")
        self.setMinimumWidth(430)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Adicione canais ou desative os que não usa. Desativar mantém "
                "anúncios, estoque e histórico."
            )
        )
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Marketplace", "Ativo"])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setColumnWidth(0, 300)
        self.table.setColumnWidth(1, 70)
        layout.addWidget(self.table)

        add_row = QHBoxLayout()
        self.new_name = QLineEdit()
        self.new_name.setPlaceholderText("Nome do marketplace")
        add_row.addWidget(self.new_name, 1)
        self.add_button = QPushButton("Adicionar")
        self.add_button.clicked.connect(self._adicionar)
        add_row.addWidget(self.add_button)
        layout.addLayout(add_row)

        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._salvar)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._rows: list[tuple[int, QCheckBox]] = []
        self._reload()

    def _reload(self) -> None:
        self.table.setRowCount(0)
        self._rows.clear()
        try:
            marketplaces = listar_marketplaces(incluir_inativos=True)
        except Exception as exc:
            self.status.setText(str(exc))
            return
        for marketplace in marketplaces:
            row = self.table.rowCount()
            self.table.insertRow(row)
            name = str(marketplace["name"])
            cell = QTableWidgetItem(name)
            cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, cell)
            active = QCheckBox()
            active.setChecked(bool(marketplace["active"]))
            self.table.setCellWidget(row, 1, active)
            self._rows.append((int(marketplace["id"]), active))

    def _adicionar(self) -> None:
        nome = self.new_name.text().strip()
        if not nome:
            self.status.setText("Digite um nome antes de adicionar.")
            return
        try:
            adicionar_marketplace(nome)
        except Exception as exc:
            self.status.setText(f"Não foi possível adicionar: {exc}")
            return
        self.new_name.clear()
        self.status.setText(f"{nome} foi adicionado ao catálogo.")
        self._reload()

    def _salvar(self) -> None:
        if not migracao_concluida():
            QMessageBox.warning(
                self,
                "Atualize o banco",
                "Execute primeiro a atualização do banco com backup verificado.",
            )
            return
        try:
            for marketplace_id, checkbox in self._rows:
                definir_marketplace_ativo(
                    marketplace_id,
                    checkbox.isChecked(),
                )
        except Exception as exc:
            QMessageBox.critical(self, "Falha ao salvar", str(exc))
            return
        self.accept()


def abrir_catalogo_marketplaces(parent: QWidget | None = None) -> bool:
    if not migracao_concluida():
        QMessageBox.information(
            parent,
            "Atualize o banco",
            "O catálogo configurável fica disponível depois da atualização "
            "com backup verificado em Configuração > Banco de dados.",
        )
        return False
    dialog = MarketplaceCatalogDialog(parent)
    return dialog.exec() == QDialog.DialogCode.Accepted
