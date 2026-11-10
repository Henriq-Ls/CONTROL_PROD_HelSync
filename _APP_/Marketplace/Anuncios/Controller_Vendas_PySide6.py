"""Configuração de marketplace e etiquetas reaproveitada pela aba Anúncio."""

from __future__ import annotations

import io
import math
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QSize, QThread, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from _APP_.PySide6_core import (
    carregar_itens_anuncio_marketplace,
    salvar_itens_anuncio_marketplace,
)
from _LOGS_ import log
from _APP_.product_lifecycle import listar_marketplaces
from _ULTILIDADES_.popups import popup_info


class _LabelPrintThread(QThread):
    printed = Signal()
    failed = Signal(str)

    def __init__(
        self,
        texts: list[str],
        options: dict[str, Any],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._texts = list(texts)
        self._options = dict(options)

    def run(self) -> None:
        try:
            from _FERRAMENTAS_.Impressora import imprimir_etiquetas_grade_BANCO

            imprimir_etiquetas_grade_BANCO(
                textos=self._texts,
                **self._options,
            )
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.printed.emit()


class VendasController(QWidget):
    """Configura anúncios e estoque por ID; pode ser embutido em Anúncio."""

    PLATAFORMAS = ("Site", "Shopee", "Amazon", "Mercado Livre")

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        embedded: bool = False,
    ) -> None:
        super().__init__(parent)
        self._embedded = embedded
        self._loading_rows = False
        self._current_product = ""
        self._rows: list[dict[str, Any]] = []
        self._drafts: dict[str, dict[str, dict[str, Any]]] = {}
        self._print_thread: _LabelPrintThread | None = None
        self._print_product = ""
        self._platforms = tuple(
            str(item["name"])
            for item in listar_marketplaces()
            if bool(item["active"])
        ) or self.PLATAFORMAS
        self._announcement_text_provider: (
            Callable[[str], dict[str, str]] | None
        ) = None

        self._build_ui()
        self._load_selected_product()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        if self._embedded:
            root = outer
        else:
            self.page_scroll = QScrollArea()
            self.page_scroll.setWidgetResizable(True)
            page = QWidget()
            root = QVBoxLayout(page)
            root.setContentsMargins(12, 12, 12, 12)
            self.page_scroll.setWidget(page)
            outer.addWidget(self.page_scroll)
        root.setSpacing(7)

        heading = QLabel("<b>Preparação do anúncio por ID</b>")
        root.addWidget(heading)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        defaults_box = QGroupBox(
            "Atalho opcional: mesmos valores para vários IDs"
        )
        defaults = QGridLayout(defaults_box)
        defaults.setContentsMargins(8, 8, 8, 8)
        defaults.setHorizontalSpacing(6)
        defaults.setVerticalSpacing(5)
        batch_note = QLabel(
            "Use quando quiser repetir os valores: venda é copiada para todos "
            "os IDs e marketplaces; gasto, para todos os IDs. Para valores "
            "diferentes, edite cada ID na tabela. Este atalho só preenche a "
            "tela; não salva no banco. Campos em R$ 0,00 não são alterados."
        )
        batch_note.setWordWrap(True)
        defaults.addWidget(batch_note, 0, 0, 1, 2)
        defaults.addWidget(QLabel("Venda:"), 1, 0)
        self.all_sale_price_edit = self._money_input()
        defaults.addWidget(self.all_sale_price_edit, 1, 1)
        defaults.addWidget(QLabel("Gasto:"), 2, 0)
        self.all_cost_edit = self._money_input()
        defaults.addWidget(self.all_cost_edit, 2, 1)
        self.apply_defaults_button = QPushButton(
            "Copiar valores para todos os IDs"
        )
        self.apply_defaults_button.setToolTip(
            "Copia a venda para todos os IDs e marketplaces e o gasto para "
            "todos os IDs. Não grava no banco."
        )
        self.apply_defaults_button.clicked.connect(
            self._apply_defaults
        )
        defaults.addWidget(self.apply_defaults_button, 3, 0, 1, 2)
        root.addWidget(defaults_box)

        self.items_table = QTableWidget(0, 5)
        self.items_table.setHorizontalHeaderLabels(
            [
                "ID / kit / disponível",
                "Marketplaces",
                "Preço por canal",
                "Gasto",
                "Qt.",
            ]
        )
        self.items_table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self.items_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.items_table.verticalHeader().setVisible(False)
        header = self.items_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        for column in range(2, 5):
            header.setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
        self.items_table.setMinimumHeight(120)
        self.items_table.setMaximumHeight(270)
        self.items_table.setWordWrap(True)
        root.addWidget(self.items_table)

        safety_note = QLabel(
            "Depois de revisar todos os IDs, “Salvar anúncio e preços no banco” "
            "grava de uma vez o título, a descrição e as configurações comerciais "
            "preenchidas. Salvar não conclui nem tira o produto do Cadastro. "
            "Unidades já vendidas são preservadas."
        )
        safety_note.setWordWrap(True)
        root.addWidget(safety_note)

        save_row = QHBoxLayout()
        self.save_button = QPushButton("Salvar anúncio e preços no banco")
        self.save_button.setToolTip(
            "Grava título, descrição e dados comerciais no SQLite. Para cada "
            "ID, selecione um marketplace e informe venda e gasto maiores que zero."
        )
        self.save_button.clicked.connect(self._save)
        save_row.addWidget(self.save_button)
        self.result_label = QLabel()
        self.result_label.setWordWrap(True)
        save_row.addWidget(self.result_label, 1)
        root.addLayout(save_row)
        self.label_section = self._build_label_section()
        root.addWidget(self.label_section)

    def _build_label_section(self) -> QGroupBox:
        box = QGroupBox("Etiquetas")
        layout = QVBoxLayout(box)
        note = QLabel(
            "Uma por unidade · ID, data, produto e preço · impressora padrão."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        controls = QGridLayout()
        controls.setHorizontalSpacing(6)
        controls.setVerticalSpacing(3)
        controls.addWidget(QLabel("Quebra de linha:"), 0, 0)
        self.label_break_spin = QSpinBox()
        self.label_break_spin.setRange(5, 40)
        self.label_break_spin.setValue(20)
        controls.addWidget(self.label_break_spin, 0, 1)

        controls.addWidget(QLabel("Papel:"), 0, 2)
        self.label_paper_combo = QComboBox()
        self.label_paper_combo.addItem("100 × 150 mm", (100, 150))
        self.label_paper_combo.addItem("50 × 30 mm", (50, 30))
        controls.addWidget(self.label_paper_combo, 0, 3)

        controls.addWidget(QLabel("Tamanho do texto:"), 1, 0)
        self.label_font_combo = QComboBox()
        for size in (5, 10, 15, 20, 25, 30):
            self.label_font_combo.addItem(f"{size}", size)
        self.label_font_combo.setCurrentIndex(2)
        controls.addWidget(self.label_font_combo, 1, 1)

        controls.addWidget(QLabel("Alinhamento:"), 1, 2)
        self.label_alignment_combo = QComboBox()
        for alignment in (
            "topo-esquerda",
            "topo-centro",
            "topo-direita",
            "meio-esquerda",
            "centro",
            "meio-direita",
            "baixo-esquerda",
            "baixo-centro",
            "baixo-direita",
        ):
            self.label_alignment_combo.addItem(alignment, alignment)
        controls.addWidget(self.label_alignment_combo, 1, 3)

        controls.addWidget(QLabel("Rotação:"), 2, 0)
        self.label_rotation_combo = QComboBox()
        for rotation in (0, 90, 180, 270):
            self.label_rotation_combo.addItem(f"{rotation}°", rotation)
        controls.addWidget(self.label_rotation_combo, 2, 1)

        controls.addWidget(QLabel("Colunas:"), 2, 2)
        self.label_columns_spin = QSpinBox()
        self.label_columns_spin.setRange(1, 8)
        self.label_columns_spin.setValue(2)
        controls.addWidget(self.label_columns_spin, 2, 3)

        self.label_border_check = QCheckBox("Borda da etiqueta")
        controls.addWidget(self.label_border_check, 3, 0, 1, 2)
        layout.addLayout(controls)

        self.label_count_label = QLabel("Nenhuma etiqueta para pré-visualizar.")
        self.label_count_label.setWordWrap(True)
        layout.addWidget(self.label_count_label)
        self.label_preview = QLabel("Sem etiquetas.")
        self.label_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_preview.setMinimumSize(160, 80)
        self.label_preview.setMaximumHeight(110)
        self.label_preview.setWordWrap(True)
        layout.addWidget(self.label_preview)

        actions = QHBoxLayout()
        self.label_print_button = QPushButton("Imprimir etiquetas")
        self.label_print_button.setEnabled(False)
        self.label_print_button.clicked.connect(self._print_labels)
        actions.addWidget(self.label_print_button)
        self.label_print_status = QLabel()
        self.label_print_status.setWordWrap(True)
        actions.addWidget(self.label_print_status, 1)
        layout.addLayout(actions)

        for control in (self.label_break_spin, self.label_columns_spin):
            control.valueChanged.connect(self._refresh_label_preview)
        for control in (
            self.label_paper_combo,
            self.label_font_combo,
            self.label_alignment_combo,
            self.label_rotation_combo,
        ):
            control.currentIndexChanged.connect(self._refresh_label_preview)
        self.label_border_check.toggled.connect(self._refresh_label_preview)
        return box

    @staticmethod
    def _money_input() -> QDoubleSpinBox:
        field = QDoubleSpinBox()
        field.setDecimals(2)
        field.setRange(0, 99999999.99)
        field.setPrefix("R$ ")
        field.setMaximumWidth(145)
        return field

    def set_announcement_text_provider(
        self, provider: Callable[[str], dict[str, str]]
    ) -> None:
        """Recebe os rascunhos de título/descrição da aba Anúncio."""
        self._announcement_text_provider = provider

    def set_current_product(self, product: str) -> None:
        self._remember_current_draft()
        self._current_product = str(product or "").strip()
        self._load_selected_product()

    def refresh_marketplaces(self) -> None:
        self._platforms = tuple(
            str(item["name"])
            for item in listar_marketplaces()
            if bool(item["active"])
        ) or self.PLATAFORMAS
        self._load_selected_product()

    def _load_selected_product(self) -> None:
        product = self._current_product
        self._clear_rows()
        self.result_label.clear()
        self.label_print_status.clear()
        if not product:
            self.status_label.setText("Nenhum produto ativo em Criação.")
            self.save_button.setEnabled(False)
            self.apply_defaults_button.setEnabled(False)
            return

        try:
            data = carregar_itens_anuncio_marketplace(product)
        except Exception as exc:
            self.status_label.setText(
                f"Não foi possível carregar os IDs de {product}: {exc}"
            )
            self.save_button.setEnabled(False)
            self.apply_defaults_button.setEnabled(False)
            log.aviso("Anuncio", "_load_selected_product", str(exc))
            return

        items = list(data.get("items") or [])
        if not items:
            self.status_label.setText(
                f"{product} ainda não possui IDs na tabela VENDAS. "
                "Conclua Criação para gerar as linhas."
            )
            self.save_button.setEnabled(False)
            self.apply_defaults_button.setEnabled(False)
            return

        self._populate_items(items)
        self.status_label.setText(
            f"{product} · {len(items)} ID(s) carregado(s)."
        )
        self.save_button.setEnabled(True)
        self.apply_defaults_button.setEnabled(True)

    def _clear_rows(self) -> None:
        self._loading_rows = True
        self.items_table.setRowCount(0)
        self._rows.clear()
        self._loading_rows = False
        self._refresh_label_preview()

    def _populate_items(self, items: list[dict[str, Any]]) -> None:
        self._loading_rows = True
        self.items_table.setRowCount(0)
        self._rows.clear()
        product_drafts = self._drafts.get(self._current_product, {})
        aliases = {
            "amazon": "Amazon",
            "amozon": "Amazon",
            "mercadolivre": "Mercado Livre",
            "mercado livre": "Mercado Livre",
            "site": "Site",
            "shopee": "Shopee",
        }

        for data in items:
            item_id = str(data.get("id") or "").strip()
            if not item_id:
                continue
            draft = product_drafts.get(item_id, {})
            row_index = self.items_table.rowCount()
            self.items_table.insertRow(row_index)

            info_widget = self._build_info_cell(data)
            self.items_table.setCellWidget(row_index, 0, info_widget)

            stored_platforms = {
                aliases.get(raw.strip().casefold().replace(" ", ""), "")
                or aliases.get(raw.strip().casefold(), "")
                for raw in str(data.get("platforms") or "").split(",")
                if raw.strip()
            }
            chosen_platforms = set(
                draft.get("platforms", stored_platforms)
            )
            platform_widget = QWidget()
            platform_grid = QGridLayout(platform_widget)
            platform_grid.setContentsMargins(3, 2, 3, 2)
            platform_grid.setHorizontalSpacing(7)
            platform_grid.setVerticalSpacing(2)
            platform_checks: dict[str, QCheckBox] = {}
            for index, name in enumerate(self._platforms):
                check = QCheckBox(name)
                check.setChecked(name in chosen_platforms)
                platform_grid.addWidget(check, index // 2, index % 2)
                platform_checks[name] = check
            self.items_table.setCellWidget(row_index, 1, platform_widget)

            price_widget = QWidget()
            price_grid = QGridLayout(price_widget)
            price_grid.setContentsMargins(3, 2, 3, 2)
            price_grid.setHorizontalSpacing(4)
            price_grid.setVerticalSpacing(2)
            sale_prices: dict[str, QDoubleSpinBox] = {}
            stored_prices = data.get("platform_prices") or {}
            draft_prices = draft.get("prices") or {}
            fallback_price = float(data.get("sale_price") or 0)
            for index, name in enumerate(self._platforms):
                price_grid.addWidget(QLabel(name), index, 0)
                price = self._money_input()
                price.setMaximumWidth(112)
                price.setValue(
                    max(
                        0.0,
                        float(
                            draft_prices.get(
                                name,
                                stored_prices.get(name, fallback_price),
                            )
                            or 0
                        ),
                    )
                )
                price_grid.addWidget(price, index, 1)
                sale_prices[name] = price
            self.items_table.setCellWidget(row_index, 2, price_widget)

            cost = self._money_input()
            cost.setValue(
                max(0.0, float(draft.get("cost", data.get("cost") or 0)))
            )
            self.items_table.setCellWidget(row_index, 3, cost)

            quantity = QSpinBox()
            quantity.setRange(0, 1_000_000)
            quantity.setValue(
                max(0, int(draft.get("quantity", data.get("quantity", 1))))
            )
            self.items_table.setCellWidget(row_index, 4, quantity)

            row = {
                "id": item_id,
                "date": str(data.get("date") or ""),
                "platforms": platform_checks,
                "sale_prices": sale_prices,
                "cost": cost,
                "quantity": quantity,
            }
            self._rows.append(row)
            for check in platform_checks.values():
                check.toggled.connect(self._remember_current_draft)
            for price in sale_prices.values():
                price.valueChanged.connect(self._remember_current_draft)
                price.valueChanged.connect(self._refresh_label_preview)
            cost.valueChanged.connect(self._remember_current_draft)
            quantity.valueChanged.connect(self._remember_current_draft)
            quantity.valueChanged.connect(self._refresh_label_preview)
            self.items_table.setRowHeight(
                row_index,
                max(54, len(self._platforms) * 28 + 8),
            )

        self._loading_rows = False
        self._refresh_label_preview()

    def _build_info_cell(self, data: dict[str, Any]) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(8)

        path = Path(str(data.get("image") or ""))
        preview = QLabel("Sem imagem")
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setFixedSize(42, 42)
        if path.is_file():
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                preview.setPixmap(
                    pixmap.scaled(
                        QSize(42, 42),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                preview.setText("")
        layout.addWidget(preview)

        id_label = QLabel(str(data.get("id") or ""))
        id_label.setStyleSheet("font-weight: 600;")
        id_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        kit = str(data.get("kit") or "").strip()
        stock = int(data.get("stock") or 0)
        details_parts = [f"Kit: {kit}"] if kit else []
        details_parts.append(f"Disp.: {stock}")
        details = QLabel(" · ".join(details_parts))
        details.setWordWrap(True)
        details.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.addWidget(id_label)
        text_column.addWidget(details)
        layout.addLayout(text_column, 1)
        return cell

    def _remember_current_draft(self, *_args: object) -> None:
        if self._loading_rows or not self._current_product or not self._rows:
            return
        self._drafts[self._current_product] = {
            str(row["id"]): {
                "platforms": [
                    name
                    for name, check in row["platforms"].items()
                    if check.isChecked()
                ],
                "prices": {
                    name: price.value()
                    for name, price in row["sale_prices"].items()
                },
                "cost": row["cost"].value(),
                "quantity": row["quantity"].value(),
            }
            for row in self._rows
        }

    def _apply_defaults(self) -> None:
        sale_price = self.all_sale_price_edit.value()
        cost = self.all_cost_edit.value()
        if sale_price <= 0 and cost <= 0:
            self.result_label.setText(
                "Informe um valor de venda ou gasto maior que zero."
            )
            return
        for row in self._rows:
            if sale_price > 0:
                for price in row["sale_prices"].values():
                    price.setValue(sale_price)
            if cost > 0:
                row["cost"].setValue(cost)
        self.result_label.setText(
            "Valores copiados para todos os IDs e canais; ainda não foram "
            "gravados no banco. Revise os preços por marketplace e clique em "
            "“Salvar anúncio e preços no banco”."
        )

    def _announcement_texts(self) -> tuple[str | None, str | None]:
        if self._announcement_text_provider is None:
            return None, None
        try:
            texts = self._announcement_text_provider(self._current_product)
        except Exception as exc:
            log.aviso("Anuncio", "_announcement_texts", str(exc))
            return None, None
        title = str(texts.get("title") or "").strip() or None
        description = str(texts.get("description") or "").strip() or None
        return title, description

    def _save(self) -> None:
        if not self._current_product or not self._rows:
            self.result_label.setText("Não há IDs carregados para salvar.")
            return
        self._remember_current_draft()
        payload: list[dict[str, Any]] = []
        for row in self._rows:
            platforms = [
                name
                for name, check in row["platforms"].items()
                if check.isChecked()
            ]
            if not platforms:
                self.result_label.setText(
                    f"Selecione pelo menos um marketplace para o ID {row['id']}."
                )
                return
            offers = [
                {
                    "marketplace": name,
                    "sale_price": float(row["sale_prices"][name].value()),
                }
                for name in platforms
            ]
            if any(offer["sale_price"] <= 0 for offer in offers):
                self.result_label.setText(
                    f"Informe um preço maior que zero para cada marketplace "
                    f"selecionado no ID {row['id']}."
                )
                return
            if row["cost"].value() <= 0:
                self.result_label.setText(
                    f"Preencha o gasto maior que zero para o ID {row['id']}."
                )
                return
            payload.append(
                {
                    "id": row["id"],
                    "platforms": platforms,
                    "offers": offers,
                    "sale_price": min(
                        offer["sale_price"] for offer in offers
                    ),
                    "cost": row["cost"].value(),
                    "quantity": row["quantity"].value(),
                }
            )

        title, description = self._announcement_texts()
        try:
            count = salvar_itens_anuncio_marketplace(
                self._current_product,
                title,
                description,
                payload,
            )
            self._drafts.pop(self._current_product, None)
            self._load_selected_product()
            self.result_label.setText(
                f"Dados comerciais salvos para {count} ID(s) de "
                f"{self._current_product}. "
                "Unidades com dados de venda foram preservadas."
            )
            log.info(
                "Anuncio",
                "_save",
                (
                    f"dados comerciais salvos; produto={self._current_product}; "
                    f"ids={count}"
                ),
            )
            popup_info(
                "Dados comerciais salvos",
                (
                    f"Os dados comerciais de {self._current_product} foram "
                    f"salvos com sucesso para {count} ID(s)."
                ),
                self,
            )
        except Exception as exc:
            self.result_label.setText(f"Não foi possível salvar: {exc}")
            log.aviso("Anuncio", "_save", f"falha ao salvar: {exc}")

    def _label_prices_ready(self) -> bool:
        if not self._rows:
            return False
        for row in self._rows:
            selected = [
                name
                for name, check in row["platforms"].items()
                if check.isChecked()
            ]
            if not selected or any(
                row["sale_prices"][name].value() <= 0
                for name in selected
            ):
                return False
        return True

    def _label_texts(self) -> list[str]:
        if not self._current_product or not self._label_prices_ready():
            return []
        from _FERRAMENTAS_.Impressora import quebrar_texto

        break_at = self.label_break_spin.value()
        texts: list[str] = []
        for row in self._rows:
            quantity = max(0, int(row["quantity"].value()))
            selected = [
                name
                for name, check in row["platforms"].items()
                if check.isChecked()
            ]
            price = float(row["sale_prices"][selected[0]].value())
            price_text = f"R$ {price:.2f}" if price > 0 else "R$ --"
            date_text = str(row.get("date") or "").strip() or "—"
            product_text = quebrar_texto(self._current_product, break_at)
            text = f"{row['id']}\n{date_text}\n{product_text}\n{price_text}"
            texts.extend([text] * quantity)
        return texts

    def _label_options(self, count: int) -> dict[str, Any]:
        paper = self.label_paper_combo.currentData()
        width_mm, height_mm = tuple(paper) if paper else (100, 150)
        columns = self.label_columns_spin.value()
        return {
            "largura_folha_mm": int(width_mm),
            "altura_folha_mm": int(height_mm),
            "colunas": columns,
            "linhas": max(1, math.ceil(count / columns)),
            "margem_folha_mm": 5,
            "espaco_entre_mm": 2,
            "tamanho_fonte": int(self.label_font_combo.currentData() or 15),
            "alinhamento": str(
                self.label_alignment_combo.currentData() or "topo-esquerda"
            ),
            "borda": self.label_border_check.isChecked(),
            "rotacao": int(self.label_rotation_combo.currentData() or 0),
        }

    def _refresh_label_preview(self, *_args: object) -> None:
        if not hasattr(self, "label_preview"):
            return
        if self._rows and not self._label_prices_ready():
            self.label_count_label.setText(
                "Preencha o preço de venda de todos os IDs na tabela acima."
            )
            self.label_preview.setPixmap(QPixmap())
            self.label_preview.setText("Preço de venda necessário.")
            self.label_print_button.setEnabled(False)
            return
        try:
            texts = self._label_texts()
            if not texts:
                self.label_count_label.setText(
                    "Nenhuma etiqueta para pré-visualizar."
                )
                self.label_preview.setPixmap(QPixmap())
                self.label_preview.setText(
                    "Nenhum produto ativo para gerar etiquetas."
                )
                self.label_print_button.setEnabled(False)
                return

            options = self._label_options(len(texts))
            from _FERRAMENTAS_.Impressora import gerar_preview

            preview = gerar_preview(
                textos=texts,
                largura_mm=options["largura_folha_mm"],
                altura_mm=options["altura_folha_mm"],
                colunas=options["colunas"],
                linhas=options["linhas"],
                margem_mm=options["margem_folha_mm"],
                espaco_mm=options["espaco_entre_mm"],
                tamanho_fonte=options["tamanho_fonte"],
                alinhamento=options["alinhamento"],
                borda=options["borda"],
                rotacao=options["rotacao"],
            )
            buffer = io.BytesIO()
            preview.save(buffer, format="PNG")
            if buffer.tell() == 0:
                raise RuntimeError("A prévia não pôde ser convertida em PNG.")
            pixmap = QPixmap()
            if not pixmap.loadFromData(buffer.getvalue(), "PNG"):
                raise RuntimeError("A prévia não pôde ser carregada na tela.")
            self.label_preview.setText("")
            self.label_preview.setPixmap(
                pixmap.scaled(
                    QSize(260, 100),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self.label_count_label.setText(
                f"{len(texts)} etiqueta(s) para {self._current_product}."
            )
            self.label_print_button.setEnabled(
                self._print_thread is None and bool(texts)
            )
        except Exception as exc:
            self.label_count_label.setText(
                "Não foi possível gerar a prévia das etiquetas."
            )
            self.label_preview.setPixmap(QPixmap())
            self.label_preview.setText(f"Falha na prévia: {exc}")
            self.label_print_button.setEnabled(False)
            log.aviso(
                "Anuncio",
                "_refresh_label_preview",
                f"falha ao gerar prévia de etiquetas: {exc}",
            )

    def _print_labels(self) -> None:
        if self._print_thread is not None:
            if self._print_thread.isRunning():
                self.label_print_status.setText(
                    "A impressão já está em andamento."
                )
                return
            self.label_print_thread_finished()

        try:
            texts = self._label_texts()
            if not texts:
                if self._rows and not self._label_prices_ready():
                    self.label_print_status.setText(
                        "Informe o preço de venda de todos os IDs acima "
                        "antes de imprimir."
                    )
                else:
                    self.label_print_status.setText(
                        "Não há etiquetas para imprimir."
                    )
                return
            worker = _LabelPrintThread(
                texts,
                self._label_options(len(texts)),
                self,
            )
            worker.printed.connect(self._label_print_succeeded)
            worker.failed.connect(self._label_print_failed)
            worker.finished.connect(self.label_print_thread_finished)
            self._print_thread = worker
            self._print_product = self._current_product
            self.label_print_button.setEnabled(False)
            self.label_print_status.setText(
                f"Enviando {len(texts)} etiqueta(s) à impressora padrão..."
            )
            worker.start()
        except Exception as exc:
            self.label_print_status.setText(
                f"Não foi possível preparar a impressão: {exc}"
            )
            log.aviso("Anuncio", "_print_labels", str(exc))

    def _label_print_succeeded(self) -> None:
        self.label_print_status.setText(
            f"Etiquetas de {self._print_product} enviadas à impressora "
            "padrão do Windows."
        )

    def _label_print_failed(self, error: str) -> None:
        self.label_print_status.setText(
            f"Falha ao imprimir etiquetas de {self._print_product}: {error}"
        )
        log.erro("Anuncio", "_print_labels", error)

    def label_print_thread_finished(self) -> None:
        worker = self._print_thread
        self._print_thread = None
        if worker is not None:
            worker.deleteLater()
        self._print_product = ""
        self._refresh_label_preview()

