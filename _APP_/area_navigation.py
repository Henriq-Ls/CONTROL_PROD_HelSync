"""Barra vertical de navegação das áreas principais."""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from _CONFIGURA_ import IMAGEM_ICO, IMAGEM_LOGO


class AreaNavigation(QWidget):
    area_selected = Signal(str)

    AREAS = (
        ("cadastro", "Cadastro"),
        ("marketplace", "Marketplace"),
        ("vendas", "Vendas"),
        ("configuracao", "Configuração"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("areaNavigation")
        self.setFixedWidth(128)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(8)

        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setToolTip("Hen Place Control")
        product_logo = (
            QPixmap(IMAGEM_LOGO) if os.path.isfile(IMAGEM_LOGO) else QPixmap()
        )
        icon = QIcon(IMAGEM_ICO) if os.path.isfile(IMAGEM_ICO) else QIcon()
        if not product_logo.isNull():
            logo.setPixmap(
                product_logo.scaled(
                    76,
                    54,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            logo.setAccessibleName("Logo Hen Place Control")
        elif not icon.isNull():
            logo.setPixmap(icon.pixmap(44, 44))
            logo.setAccessibleName("Ícone Hen Place Control")
        else:
            logo.setText("HEN\nPLACE")
            logo.setStyleSheet(
                "font-size: 13px; font-weight: 700; color: #5de0cc;"
            )
            logo.setAccessibleName("Hen Place Control")
        logo.setMinimumHeight(58)
        layout.addWidget(logo)
        layout.addSpacing(10)

        self.buttons: dict[str, QPushButton] = {}
        for area_id, label in self.AREAS:
            button = QPushButton(label)
            button.setCheckable(True)
            button.setMinimumHeight(46)
            button.setAccessibleName(label)
            button.clicked.connect(
                lambda _checked=False, key=area_id: self.area_selected.emit(key)
            )
            self.buttons[area_id] = button
            layout.addWidget(button)
        layout.addStretch(1)
        self.setStyleSheet(
            """
            QWidget#areaNavigation {
                background: #15253A;
                border-right: 1px solid #2D435D;
            }
            QPushButton {
                text-align: center;
                padding: 6px;
                border: 1px solid #2D435D;
                border-radius: 6px;
                background: #20334B;
            }
            QPushButton:checked {
                background: #1D7E7A;
                border-color: #69E2D2;
                font-weight: 700;
            }
            """
        )
        self.set_active_area("cadastro")

    def set_active_area(self, area_id: str) -> None:
        for key, button in self.buttons.items():
            button.setChecked(key == area_id)
