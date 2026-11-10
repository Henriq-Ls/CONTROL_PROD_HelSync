"""Página de migração explícita com backup verificado do SQLite."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from _APP_.product_lifecycle import criar_backup_e_migrar, migracao_concluida


class DatabaseMigrationPage(QWidget):
    migration_completed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        layout.addWidget(QLabel("<b>Atualização do banco local</b>"))
        self.description = QLabel(
            "A atualização cria tabelas para produtos permanentes, anúncios "
            "por marketplace e preços por ID/canal. Ela não importa "
            "automaticamente os registros antigos de A_ENTRADA, VENDAS ou "
            "MARKET_PLACE para as tabelas novas. Os registros antigos são "
            "preservados; produtos pendentes precisam ser concluídos para "
            "aparecer nas telas operacionais."
        )
        self.description.setWordWrap(True)
        layout.addWidget(self.description)

        self.backup_note = QLabel(
            "Antes de alterar o esquema, o app cria uma cópia do arquivo "
            "SQLite em _BANCOS_/backups e verifica a integridade dessa cópia."
        )
        self.backup_note.setWordWrap(True)
        layout.addWidget(self.backup_note)

        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.migrate_button = QPushButton("Atualizar banco com backup")
        self.migrate_button.clicked.connect(self._confirmar_migracao)
        layout.addWidget(self.migrate_button)
        layout.addStretch(1)
        self._atualizar_status()

    def _atualizar_status(self) -> None:
        pronto = migracao_concluida()
        self.migrate_button.setEnabled(not pronto)
        self.status.setText(
            "O novo esquema já está instalado."
            if pronto
            else "O esquema novo ainda não foi instalado. Nenhuma alteração "
            "será feita até você confirmar a migração."
        )

    def _confirmar_migracao(self) -> None:
        resposta = QMessageBox.question(
            self,
            "Atualizar banco com backup",
            "O app vai criar e validar uma cópia de segurança antes de "
            "acrescentar as novas tabelas. A_ENTRADA, VENDAS e MARKET_PLACE "
            "serão preservadas. Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return
        self.migrate_button.setEnabled(False)
        try:
            backup = criar_backup_e_migrar(confirmado=True)
        except Exception as exc:
            self.status.setText(f"Falha na atualização: {exc}")
            QMessageBox.critical(
                self,
                "Atualização não concluída",
                f"Nenhuma tabela antiga foi apagada.\n\n{exc}",
            )
            self._atualizar_status()
            return
        self.status.setText(
            f"Atualização concluída. Cópia verificada: {backup}"
        )
        QMessageBox.information(
            self,
            "Banco atualizado",
            f"Esquema atualizado com sucesso.\nCópia verificada:\n{backup}",
        )
        self.migration_completed.emit()
        self._atualizar_status()
