"""Página de revisão manual e impressão de etiquetas."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class AnunciarActionPage(QWidget):
    """Organiza a seleção do produto e as ações manuais do anúncio."""

    def __init__(
        self,
        label_section: QWidget,
        load_products: Callable[[], list[str]],
        current_product: Callable[[], str],
        select_product: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._load_products = load_products
        self._current_product = current_product
        self._select_product = select_product

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.addWidget(
            QLabel(
                "A publicação é manual. Esta área reúne a prévia e a impressão "
                "de etiquetas do anúncio selecionado."
            )
        )

        product_row = QHBoxLayout()
        product_row.addWidget(QLabel("Produto:"))
        self.product_choice = QComboBox()
        self.product_choice.currentIndexChanged.connect(
            self._on_product_changed
        )
        product_row.addWidget(self.product_choice, 1)
        refresh = QPushButton("Atualizar")
        refresh.clicked.connect(self.refresh_products)
        product_row.addWidget(refresh)
        layout.addLayout(product_row)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        layout.addWidget(label_section, 1)

        self.refresh_products()

    def refresh_products(self, *_args: object) -> None:
        previous = str(self.product_choice.currentData() or "")
        current = str(self._current_product() or "").strip()
        try:
            products = self._load_products()
        except Exception as exc:
            self.product_choice.clear()
            self.product_choice.setEnabled(False)
            self.status_label.setText(
                f"Não foi possível carregar os produtos: {exc}"
            )
            return

        self.product_choice.blockSignals(True)
        self.product_choice.clear()
        for product in products:
            self.product_choice.addItem(product, product)
        target = previous if previous in products else (
            current if current in products else (products[0] if products else "")
        )
        self.product_choice.setCurrentIndex(
            self.product_choice.findData(target)
        )
        self.product_choice.setEnabled(bool(products))
        self.product_choice.blockSignals(False)
        if products:
            self.status_label.setText(
                f"{len(products)} produto(s) disponível(is), incluindo "
                "registros antigos de anúncios e estoque."
            )
        else:
            self.status_label.setText(
                "Nenhum produto permanente ou registro antigo de anúncio/"
                "estoque foi encontrado."
            )
        self._on_product_changed()

    def _on_product_changed(self, *_args: object) -> None:
        product = str(self.product_choice.currentData() or "").strip()
        self._select_product(product)
