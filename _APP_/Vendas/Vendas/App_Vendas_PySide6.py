"""Aba PySide6 para registrar vendas e acompanhar as unidades vendidas."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from _APP_.PySide6_core import (
    DB_PATH,
    listar_unidades_disponiveis_para_venda,
    listar_vendas_marketplace_realizadas,
    registrar_venda_marketplace,
)
from _APP_.product_lifecycle import listar_marketplaces
from _LOGS_ import log


def _formatar_moeda(value: object) -> str:
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        amount = 0.0
    formatted = f"{amount:,.2f}"
    formatted = (
        formatted.replace(",", "_")
        .replace(".", ",")
        .replace("_", ".")
    )
    return f"R$ {formatted}"


class VendasTab(QWidget):
    """Registro de compras concluídas sobre o estoque disponível."""

    PLATAFORMAS = ("Shopee", "Mercado Livre", "Amazon", "Site")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._available_products: list[dict[str, Any]] = []
        self._history_records: list[dict[str, Any]] = []
        self._platforms = tuple(
            str(item["name"])
            for item in listar_marketplaces()
            if bool(item["active"])
        ) or self.PLATAFORMAS
        self._build_ui()
        self._load_products()
        self._load_history()

    def refresh_marketplaces(self) -> None:
        current = str(self.platform_combo.currentData() or "")
        self._platforms = tuple(
            str(item["name"])
            for item in listar_marketplaces()
            if bool(item["active"])
        ) or self.PLATAFORMAS
        self.platform_combo.blockSignals(True)
        self.platform_combo.clear()
        self.platform_combo.addItem("Selecione a plataforma", "")
        for platform in self._platforms:
            self.platform_combo.addItem(platform, platform)
        index = self.platform_combo.findData(current)
        self.platform_combo.setCurrentIndex(index if index >= 0 else 0)
        self.platform_combo.blockSignals(False)
        self._update_estimate()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        heading = QLabel("<b>Registrar vendas</b>")
        layout.addWidget(heading)

        self.pages = QTabWidget()
        layout.addWidget(self.pages, 1)

        self._build_register_page()
        self._build_history_page()

    def _build_register_page(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(8)

        product_row = QHBoxLayout()
        product_row.addWidget(QLabel("Produto disponível:"))
        self.product_combo = QComboBox()
        self.product_combo.currentIndexChanged.connect(
            self._on_product_changed
        )
        product_row.addWidget(self.product_combo, 1)
        self.refresh_products_button = QPushButton("Atualizar estoque")
        self.refresh_products_button.clicked.connect(self._load_products)
        product_row.addWidget(self.refresh_products_button)
        layout.addLayout(product_row)

        self.products_status = QLabel()
        self.products_status.setWordWrap(True)
        layout.addWidget(self.products_status)

        product_box = QGroupBox("Produto e estoque")
        product_layout = QHBoxLayout(product_box)
        self.product_image = QLabel("Sem imagem")
        self.product_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.product_image.setFixedSize(80, 80)
        product_layout.addWidget(self.product_image)
        self.product_details = QLabel(
            "Selecione um produto com unidades disponíveis."
        )
        self.product_details.setWordWrap(True)
        product_layout.addWidget(self.product_details, 1)
        layout.addWidget(product_box)

        self.sale_box = QGroupBox("Dados da venda")
        sale_layout = QVBoxLayout(self.sale_box)
        form_row = QHBoxLayout()

        sale_form = QFormLayout()
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 1)
        self.quantity_spin.valueChanged.connect(self._update_estimate)
        sale_form.addRow("Quantidade:", self.quantity_spin)

        self.platform_combo = QComboBox()
        self.platform_combo.addItem("Selecione a plataforma", "")
        for platform in self._platforms:
            self.platform_combo.addItem(platform, platform)
        self.platform_combo.currentIndexChanged.connect(self._update_estimate)
        sale_form.addRow("Plataforma de venda:", self.platform_combo)

        self.fee_spin = QDoubleSpinBox()
        self.fee_spin.setDecimals(2)
        self.fee_spin.setRange(0, 99999999.99)
        self.fee_spin.setPrefix("R$ ")
        self.fee_spin.setMaximumWidth(160)
        self.fee_spin.valueChanged.connect(self._update_estimate)
        sale_form.addRow("Taxa por unidade:", self.fee_spin)
        form_row.addLayout(sale_form, 1)

        customer_form = QFormLayout()
        self.customer_name_edit = QLineEdit()
        self.customer_name_edit.setClearButtonEnabled(True)
        self.customer_name_edit.textChanged.connect(self._update_estimate)
        customer_form.addRow("Nome do cliente *:", self.customer_name_edit)

        self.customer_cpf_edit = QLineEdit()
        self.customer_cpf_edit.setClearButtonEnabled(True)
        customer_form.addRow("CPF:", self.customer_cpf_edit)

        self.customer_phone_edit = QLineEdit()
        self.customer_phone_edit.setClearButtonEnabled(True)
        customer_form.addRow("Telefone:", self.customer_phone_edit)
        form_row.addLayout(customer_form, 2)
        sale_layout.addLayout(form_row)

        self.address_edit = QTextEdit()
        self.address_edit.setPlaceholderText("Endereço de entrega")
        self.address_edit.setFixedHeight(62)
        sale_layout.addWidget(self.address_edit)

        self.estimate_label = QLabel("Selecione um produto para ver o resumo.")
        self.estimate_label.setWordWrap(True)
        sale_layout.addWidget(self.estimate_label)
        layout.addWidget(self.sale_box)

        action_row = QHBoxLayout()
        self.sale_status = QLabel()
        self.sale_status.setWordWrap(True)
        action_row.addWidget(self.sale_status, 1)
        self.register_button = QPushButton("Registrar venda")
        self.register_button.setEnabled(False)
        self.register_button.clicked.connect(self._register_sale)
        action_row.addWidget(self.register_button)
        layout.addLayout(action_row)
        layout.addStretch(1)

        self.pages.addTab(page, "Registrar vendas")

    def _build_history_page(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self.history_status = QLabel()
        self.history_status.setWordWrap(True)
        header.addWidget(self.history_status, 1)
        self.refresh_history_button = QPushButton("Atualizar histórico")
        self.refresh_history_button.clicked.connect(self._load_history)
        header.addWidget(self.refresh_history_button)
        layout.addLayout(header)

        note = QLabel(
            "Cada linha representa uma unidade vendida. O registro legado "
            "não guarda data nem identificador separado da compra."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(
            ["ID", "Produto", "Cliente", "Marketplace", "Venda/un."]
        )
        self.history_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.history_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.history_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.history_table.verticalHeader().setVisible(False)
        history_header = self.history_table.horizontalHeader()
        history_header.setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        history_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        history_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        history_header.setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        history_header.setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        self.history_table.itemSelectionChanged.connect(
            self._show_history_details
        )
        layout.addWidget(self.history_table, 1)

        self.history_details = QLabel(
            "Selecione uma unidade para ver os dados completos do comprador."
        )
        self.history_details.setWordWrap(True)
        self.history_details.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.history_details)

        self.pages.addTab(page, "Histórico")

    def _selected_product(self) -> dict[str, Any] | None:
        index = self.product_combo.currentIndex()
        if 0 <= index < len(self._available_products):
            return self._available_products[index]
        return None

    def _load_products(
        self,
        *_args: object,
        preferred: tuple[str, str] | None = None,
    ) -> None:
        current = self._selected_product()
        preferred_key = preferred
        if preferred_key is None and current:
            preferred_key = (
                str(current.get("ID") or ""),
                str(current.get("NOME_PRODUTO") or ""),
            )

        try:
            products = listar_unidades_disponiveis_para_venda()
        except Exception as exc:
            self._available_products = []
            self.product_combo.blockSignals(True)
            self.product_combo.clear()
            self.product_combo.blockSignals(False)
            self.products_status.setText(
                "Não foi possível carregar o estoque do banco "
                f"{Path(DB_PATH).expanduser().resolve()}: {exc}"
            )
            self.product_combo.setEnabled(False)
            self._on_product_changed()
            log.aviso("Vendas", "_load_products", str(exc))
            return

        self._available_products = products
        self.product_combo.blockSignals(True)
        self.product_combo.clear()
        for item in products:
            name = str(item.get("NOME_PRODUTO") or "").strip()
            item_id = str(item.get("ID") or "").strip()
            stock = int(item.get("ESTOQUE") or 0)
            price = _formatar_moeda(item.get("VALOR_VENDA"))
            self.product_combo.addItem(
                f"{name} · ID {item_id} · {stock} un. · {price}"
            )

        selected_index = 0 if products and preferred_key is None else -1
        if preferred_key:
            for index, item in enumerate(products):
                key = (
                    str(item.get("ID") or ""),
                    str(item.get("NOME_PRODUTO") or ""),
                )
                if key == preferred_key:
                    selected_index = index
                    break
        self.product_combo.setCurrentIndex(selected_index)
        self.product_combo.blockSignals(False)
        self.product_combo.setEnabled(bool(products))

        if products:
            total_units = sum(
                max(0, int(item.get("ESTOQUE") or 0))
                for item in products
            )
            self.products_status.setText(
                f"{len(products)} opção(ões) de produto/ID · "
                f"{total_units} unidade(s) disponíveis. "
                f"Banco: {Path(DB_PATH).expanduser().resolve()}"
            )
        else:
            self.products_status.setText(
                "Nenhuma unidade disponível em MARKET_PLACE. "
                f"Banco consultado: {Path(DB_PATH).expanduser().resolve()}"
            )
        self._on_product_changed()

    def _on_product_changed(self, *_args: object) -> None:
        product = self._selected_product()
        if not product:
            self.product_image.setPixmap(QPixmap())
            self.product_image.setText("Sem estoque")
            self.product_details.setText(
                "Selecione um produto com unidades disponíveis."
            )
            self.quantity_spin.setRange(1, 1)
            self.sale_box.setEnabled(False)
            self._update_estimate()
            return

        stock = max(0, int(product.get("ESTOQUE") or 0))
        self.quantity_spin.setRange(1, max(1, stock))
        self.quantity_spin.setValue(1)
        self.sale_box.setEnabled(True)

        image_path = Path(str(product.get("IMAGEM") or ""))
        pixmap = QPixmap(str(image_path)) if image_path.is_file() else QPixmap()
        if pixmap.isNull():
            self.product_image.setPixmap(QPixmap())
            self.product_image.setText("Sem imagem")
        else:
            self.product_image.setText("")
            self.product_image.setPixmap(
                pixmap.scaled(
                    QSize(76, 76),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        product_name = str(product.get("NOME_PRODUTO") or "").strip()
        item_id = str(product.get("ID") or "").strip()
        kit = str(product.get("KIT") or "").strip() or "—"
        platforms = str(product.get("PLATAFORMAS_POSTADO") or "").strip() or "—"
        prices = product.get("PRECOS_MARKETPLACE") or {}
        price_summary = " · ".join(
            f"{name}: {_formatar_moeda(value)}"
            for name, value in prices.items()
        )
        details = [
            product_name,
            f"ID: {item_id} · Kit: {kit}",
            f"Venda: {_formatar_moeda(product.get('VALOR_VENDA'))} · "
            f"Custo: {_formatar_moeda(product.get('CUSTO_PRODUTO'))}",
        ]
        if price_summary:
            details.append(f"Preços por canal: {price_summary}")
        details.append(
            f"Anunciado em: {platforms} · Disponível: {stock} unidade(s)"
        )
        self.product_details.setText("\n".join(details))
        self._update_estimate()

    def _update_estimate(self, *_args: object) -> None:
        product = self._selected_product()
        if not product:
            self.estimate_label.setText(
                "Selecione um produto para ver o resumo."
            )
            self.register_button.setEnabled(False)
            return

        platform = str(self.platform_combo.currentData() or "")
        prices = product.get("PRECOS_MARKETPLACE") or {}
        if product.get("TEM_ANUNCIOS_NORMALIZADOS"):
            price = float(prices.get(platform, 0) or 0)
        else:
            price = float(product.get("VALOR_VENDA") or 0)
        cost = float(product.get("CUSTO_PRODUTO") or 0)
        quantity = self.quantity_spin.value()
        fee = self.fee_spin.value()
        total = price * quantity
        profit = (price - cost - fee) * quantity
        self.estimate_label.setText(
            f"Total da venda: {_formatar_moeda(total)}  ·  "
            f"Lucro estimado: {_formatar_moeda(profit)} "
            f"(taxa por unidade: {_formatar_moeda(fee)})"
        )
        self.register_button.setEnabled(
            price > 0
            and quantity > 0
            and bool(self.customer_name_edit.text().strip())
            and bool(self.platform_combo.currentData())
        )
        if price <= 0:
            self.sale_status.setText(
                "Este ID não tem preço de venda. Configure-o em Anúncio."
            )
        elif self.sale_status.text().startswith(
            "Este ID não tem preço de venda."
        ):
            self.sale_status.clear()

    def _register_sale(self) -> None:
        product = self._selected_product()
        if not product:
            self.sale_status.setText(
                "Atualize o estoque e selecione um produto disponível."
            )
            return

        try:
            updated = registrar_venda_marketplace(
                item_id=str(product.get("ID") or ""),
                produto=str(product.get("NOME_PRODUTO") or ""),
                quantidade=self.quantity_spin.value(),
                cliente_nome=self.customer_name_edit.text(),
                cliente_cpf=self.customer_cpf_edit.text(),
                cliente_telefone=self.customer_phone_edit.text(),
                endereco=self.address_edit.toPlainText(),
                plataforma_venda=str(self.platform_combo.currentData() or ""),
                taxa_por_unidade=self.fee_spin.value(),
            )
        except ValueError as exc:
            self.sale_status.setText(str(exc))
            self._load_products()
            return
        except Exception as exc:
            self.sale_status.setText(
                f"Não foi possível registrar a venda: {exc}"
            )
            log.erro("Vendas", "_register_sale", str(exc))
            return

        item_id = str(product.get("ID") or "")
        product_name = str(product.get("NOME_PRODUTO") or "")
        customer = self.customer_name_edit.text().strip()
        self.customer_name_edit.clear()
        self.customer_cpf_edit.clear()
        self.customer_phone_edit.clear()
        self.address_edit.clear()
        self.platform_combo.setCurrentIndex(0)
        self.fee_spin.setValue(0)
        self.sale_status.setText(
            f"Venda registrada: {updated} unidade(s) para {customer}. "
            "O estoque disponível foi atualizado."
        )
        self._load_products(preferred=(item_id, product_name))
        self._load_history()
        self._update_estimate()

    def _load_history(self, *_args: object) -> None:
        try:
            records = listar_vendas_marketplace_realizadas()
        except Exception as exc:
            self._history_records = []
            self.history_table.setRowCount(0)
            self.history_status.setText(
                f"Não foi possível carregar o histórico: {exc}"
            )
            log.aviso("Vendas", "_load_history", str(exc))
            return

        self._history_records = records
        self.history_table.setRowCount(0)
        for record in records:
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)
            values = (
                record.get("ID"),
                record.get("NOME_PRODUTO"),
                record.get("CLIENTE_NOME"),
                record.get("PLATAFORMA_VENDA"),
                _formatar_moeda(record.get("VALOR_VENDA")),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value or "—"))
                if column in (0, 4):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                        if column == 0
                        else Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )
                self.history_table.setItem(row, column, item)
            self.history_table.setRowHeight(row, 30)

        count = len(records)
        self.history_status.setText(
            f"{count} unidade(s) vendida(s)."
            if count
            else "Nenhuma venda registrada."
        )
        self.history_details.setText(
            "Selecione uma unidade para ver os dados completos do comprador."
        )

    def _show_history_details(self) -> None:
        row = self.history_table.currentRow()
        if not 0 <= row < len(self._history_records):
            return
        record = self._history_records[row]
        kit = str(record.get("KIT") or "").strip() or "—"
        cpf = str(record.get("CLIENTE_CPF") or "").strip() or "—"
        phone = str(record.get("CLIENTE_TELEFONE") or "").strip() or "—"
        address = str(record.get("ENDERECO") or "").strip() or "—"
        cost = _formatar_moeda(record.get("CUSTO_PRODUTO"))
        fee = _formatar_moeda(record.get("TAXA_PLATAFORMA"))
        profit = _formatar_moeda(record.get("LUCRO"))
        self.history_details.setText(
            f"Kit: {kit}  ·  CPF: {cpf}  ·  Telefone: {phone}  ·  "
            f"Custo/un.: {cost}  ·  Taxa/un.: {fee}  ·  Lucro/un.: {profit}\n"
            f"Endereço: {address}"
        )
