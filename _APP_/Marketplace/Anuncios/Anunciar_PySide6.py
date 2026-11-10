"""Vitrine local para revisar e copiar anúncios já preparados."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from _APP_.PySide6_core import (
    carregar_itens_anuncio_marketplace,
    salvar_textos_anuncio_marketplace,
)
from _APP_.Marketplace.catalogo import abrir_catalogo_marketplaces
from _APP_.product_lifecycle import listar_marketplaces
from _ULTILIDADES_.popups import popup_erro, popup_info
from ..Anunciar.Anunciar_Midias_PySide6 import AnunciarMediaPanel
from .Data_Anuncio_PySide6 import (
    ler_entradas_somente_leitura,
    ler_produtos_permanentes_somente_leitura,
    listar_produtos_para_anunciar_somente_leitura,
)


class AnunciarPage(QWidget):
    """Mostra a versão pronta do anúncio e permite editar/copiar seu texto."""

    texto_salvo = Signal(str, str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._loading_products = False
        self._user_selected_product = False
        self._current_product = ""
        self._source_entry: tuple | None = None
        self._commercial_data: dict[str, Any] = {}
        self._listing_by_marketplace: dict[str, dict[str, Any]] = {}
        self._product_folder: Path | None = None
        self._has_marketplace_records = False
        self._saved_title = ""
        self._saved_description = ""
        self._editing = False
        self._loading_marketplaces = False

        self._build_ui()
        self.refresh_products(select_latest=True)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        product_bar = QHBoxLayout()
        product_bar.addWidget(QLabel("Produto pronto:"))
        self.product_combo = QComboBox()
        self.product_combo.setMinimumWidth(240)
        self.product_combo.currentIndexChanged.connect(
            self._on_product_changed
        )
        product_bar.addWidget(self.product_combo, 1)
        self.refresh_button = QPushButton("Atualizar produtos")
        self.refresh_button.clicked.connect(self.refresh_products)
        product_bar.addWidget(self.refresh_button)
        layout.addLayout(product_bar)

        self.status_label = QLabel(
            "O produto mais recente aparece primeiro na lista."
        )
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(8, 4, 8, 8)
        content_layout.setSpacing(10)

        self.product_name_label = QLabel("Selecione um produto")
        self.product_name_label.setStyleSheet(
            "font-size: 18px; font-weight: 600;"
        )
        content_layout.addWidget(self.product_name_label)

        product_row = QHBoxLayout()
        product_row.setSpacing(10)
        self.media_panel = AnunciarMediaPanel(self)
        product_row.addWidget(self.media_panel, 1)
        product_row.addWidget(self._build_listing_panel(), 2)
        content_layout.addLayout(product_row)

        facts_group = QGroupBox("Dados do produto")
        facts_layout = QVBoxLayout(facts_group)
        self.facts_view = QPlainTextEdit()
        self.facts_view.setReadOnly(True)
        self.facts_view.setMaximumHeight(150)
        self.facts_view.setPlaceholderText(
            "Os dados cadastrados do produto aparecem aqui."
        )
        facts_layout.addWidget(self.facts_view)
        content_layout.addWidget(facts_group)

        commercial_group = QGroupBox("Dados comerciais por ID")
        commercial_layout = QVBoxLayout(commercial_group)
        self.items_table = QTableWidget(0, 6)
        self.items_table.setHorizontalHeaderLabels(
            ["ID", "Kit", "Marketplaces", "Venda", "Custo", "Estoque"]
        )
        self.items_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.items_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.items_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.items_table.horizontalHeader().setStretchLastSection(True)
        self.items_table.setMinimumHeight(120)
        commercial_layout.addWidget(self.items_table)
        content_layout.addWidget(commercial_group)

        content_layout.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

    def _build_listing_panel(self) -> QGroupBox:
        panel = QGroupBox("Anúncio pronto para marketplace")
        layout = QVBoxLayout(panel)
        form = QFormLayout()

        marketplace_row = QHBoxLayout()
        self.marketplace_choice = QComboBox()
        self.marketplace_choice.currentIndexChanged.connect(
            self._on_marketplace_changed
        )
        marketplace_row.addWidget(self.marketplace_choice, 1)
        self.manage_marketplaces_button = QPushButton("Marketplaces")
        self.manage_marketplaces_button.clicked.connect(
            self._manage_marketplaces
        )
        marketplace_row.addWidget(self.manage_marketplaces_button)
        form.addRow("Canal:", marketplace_row)

        title_row = QHBoxLayout()
        self.title_edit = QLineEdit()
        self.title_edit.setReadOnly(True)
        self.copy_title_button = QPushButton("Copiar")
        self.copy_title_button.clicked.connect(self._copy_title)
        title_row.addWidget(self.title_edit, 1)
        title_row.addWidget(self.copy_title_button)
        form.addRow("Título:", title_row)

        description_row = QHBoxLayout()
        self.description_edit = QPlainTextEdit()
        self.description_edit.setReadOnly(True)
        self.description_edit.setMinimumHeight(210)
        self.description_edit.setPlaceholderText(
            "A descrição salva do anúncio aparece aqui."
        )
        self.copy_description_button = QPushButton("Copiar")
        self.copy_description_button.clicked.connect(
            self._copy_description
        )
        description_row.addWidget(self.description_edit, 1)
        description_row.addWidget(self.copy_description_button)
        form.addRow("Descrição:", description_row)

        self.category_label = QLabel("Não cadastrada no banco atual.")
        self.category_label.setWordWrap(True)
        form.addRow("Categoria:", self.category_label)
        layout.addLayout(form)

        action_row = QHBoxLayout()
        self.edit_button = QPushButton("Editar anúncio")
        self.edit_button.clicked.connect(self._begin_edit)
        self.save_button = QPushButton("Salvar alterações")
        self.save_button.clicked.connect(self._save_edits)
        self.cancel_button = QPushButton("Cancelar edição")
        self.cancel_button.clicked.connect(self._cancel_edit)
        self.copy_full_button = QPushButton("Copiar ficha completa")
        self.copy_full_button.clicked.connect(self._copy_full_listing)
        self.save_button.hide()
        self.cancel_button.hide()
        action_row.addWidget(self.edit_button)
        action_row.addWidget(self.save_button)
        action_row.addWidget(self.cancel_button)
        layout.addLayout(action_row)
        layout.addWidget(self.copy_full_button)

        self.edit_note = QLabel(
            "Título e descrição são editados aqui. Preço, custo, estoque e "
            "marketplaces continuam configurados em Montar anúncio."
        )
        self.edit_note.setWordWrap(True)
        layout.addWidget(self.edit_note)
        return panel

    def refresh_products(
        self,
        _checked: bool = False,
        select_latest: bool | None = None,
    ) -> None:
        """Atualiza a lista ordenada pela inclusão mais recente em VENDAS."""
        if self._editing:
            self.status_label.setText(
                "Salve ou cancele a edição antes de atualizar os produtos."
            )
            return
        if select_latest is None:
            select_latest = not self._user_selected_product
        previous = str(self.product_combo.currentData() or "")
        try:
            products = [
                str(name).strip()
                for name in listar_produtos_para_anunciar_somente_leitura()
                if str(name or "").strip()
            ]
        except Exception as exc:
            self.status_label.setText(
                f"Não foi possível carregar os produtos: {exc}"
            )
            return

        self._loading_products = True
        self.product_combo.clear()
        for name in products:
            self.product_combo.addItem(name, name)

        if not products:
            self.product_combo.setCurrentIndex(-1)
            selected = ""
        else:
            if select_latest or previous not in products:
                index = 0
            else:
                index = products.index(previous)
            self.product_combo.setCurrentIndex(index)
            selected = products[index]
        self._loading_products = False

        if selected:
            self._load_selected_product()
        else:
            self._clear_product_view()
            self.status_label.setText(
                "Nenhum produto foi encontrado nos dados permanentes ou "
                "nos registros antigos."
            )

    def _on_product_changed(self, _index: int) -> None:
        if self._loading_products:
            return
        self._user_selected_product = True
        self._load_selected_product()

    def _load_selected_product(self) -> None:
        name = str(self.product_combo.currentData() or "").strip()
        if not name:
            self._clear_product_view()
            return
        self.media_panel.stop_video()
        try:
            commercial = carregar_itens_anuncio_marketplace(name)
            entries = ler_produtos_permanentes_somente_leitura()
            pending_entries = ler_entradas_somente_leitura()
        except Exception as exc:
            self._clear_product_view()
            self.status_label.setText(
                f"Não foi possível abrir o anúncio de {name}: {exc}"
            )
            return

        entry = None
        is_pending = False
        for row in entries:
            if str(row[0] or "").strip().casefold() == name.casefold():
                entry = row
                break
        if entry is None:
            for row in pending_entries:
                if str(row[0] or "").strip().casefold() == name.casefold():
                    entry = row
                    is_pending = True
                    break

        self._current_product = name
        self._source_entry = entry
        self._commercial_data = commercial
        self._listing_by_marketplace = {
            str(listing.get("marketplace") or "").casefold(): dict(listing)
            for listing in commercial.get("listings", [])
        }
        self._has_marketplace_records = bool(
            commercial.get("has_marketplace_records")
        )
        folder_text = self._entry_value(entry, 2)
        self._product_folder = (
            Path(folder_text).expanduser() if folder_text else None
        )

        self.product_name_label.setText(name)
        saved_title = str(commercial.get("title") or "").strip()
        saved_description = str(commercial.get("description") or "").strip()
        source_description = self._entry_value(entry, 3)
        self._saved_title = saved_title or name
        self._saved_description = saved_description or source_description
        self.facts_view.setPlainText(self._format_product_facts(entry))
        self.media_panel.set_product_folder(self._product_folder)
        self._render_items(commercial.get("items") or [])
        self._load_marketplace_choices()
        self._set_editing(False)

        if is_pending:
            self.status_label.setText(
                "Este cadastro ainda está em A_ENTRADA. Os registros antigos "
                "foram preservados, mas a conclusão como produto permanente "
                "não consta neste banco."
            )
        elif commercial.get("has_legacy_records"):
            self.status_label.setText(
                "Registro antigo carregado. O estoque é calculado pelos dados "
                "legados; confira a disponibilidade antes de anunciar."
            )
        elif self._has_marketplace_records:
            self.status_label.setText(
                "Anúncio carregado. A categoria não está cadastrada no "
                "banco atual."
            )
        else:
            self.status_label.setText(
                "Produto encontrado, mas ainda sem anúncio comercial salvo. "
                "Confira os IDs e preços em Montar anúncio."
            )

    def _clear_product_view(self) -> None:
        self.media_panel.set_product_folder(None)
        self._current_product = ""
        self._source_entry = None
        self._commercial_data = {}
        self._product_folder = None
        self._has_marketplace_records = False
        self._saved_title = ""
        self._saved_description = ""
        self.product_name_label.setText("Selecione um produto")
        self.title_edit.clear()
        self.description_edit.clear()
        self.facts_view.clear()
        self.items_table.setRowCount(0)
        self.marketplace_choice.clear()
        self._listing_by_marketplace.clear()
        self._set_editing(False)

    def _load_marketplace_choices(self) -> None:
        previous = str(self.marketplace_choice.currentData() or "")
        try:
            marketplaces = [
                item
                for item in listar_marketplaces()
                if bool(item.get("active"))
            ]
        except Exception as exc:
            self.status_label.setText(
                f"Não foi possível carregar marketplaces: {exc}"
            )
            marketplaces = []
        self._loading_marketplaces = True
        self.marketplace_choice.clear()
        for item in marketplaces:
            self.marketplace_choice.addItem(
                str(item.get("name") or ""),
                str(item.get("name") or ""),
            )
        target = previous if any(
            self.marketplace_choice.itemData(index) == previous
            for index in range(self.marketplace_choice.count())
        ) else (
            str(marketplaces[0].get("name") or "")
            if marketplaces
            else ""
        )
        index = self.marketplace_choice.findData(target)
        self.marketplace_choice.setCurrentIndex(index)
        self._loading_marketplaces = False
        self._on_marketplace_changed()

    def _on_marketplace_changed(self, *_args: object) -> None:
        if self._loading_marketplaces or not self._current_product:
            return
        marketplace = str(self.marketplace_choice.currentData() or "")
        listing = self._listing_by_marketplace.get(
            marketplace.casefold(),
            {},
        )
        self._saved_title = str(
            listing.get("title") or self._commercial_data.get("title") or ""
        )
        self._saved_description = str(
            listing.get("description")
            or self._commercial_data.get("description")
            or self._entry_value(self._source_entry, 3)
        )
        self.title_edit.setText(self._saved_title)
        self.description_edit.setPlainText(self._saved_description)
        self._render_items(self._commercial_data.get("items") or [])

    def _manage_marketplaces(self) -> None:
        if abrir_catalogo_marketplaces(self):
            self._load_marketplace_choices()
            owner = self.parentWidget()
            setup = getattr(owner, "marketplace_setup", None)
            if setup is not None:
                setup.refresh_marketplaces()

    @staticmethod
    def _entry_value(entry: tuple | None, index: int) -> str:
        if entry is None or index >= len(entry):
            return ""
        return str(entry[index] or "").strip()

    def _format_product_facts(self, entry: tuple | None) -> str:
        labels = (
            ("Referência", 1),
            ("Descrição de origem", 3),
            ("Uso", 4),
            ("Acompanha", 5),
            ("Acabamento", 6),
            ("Kit", 7),
            ("Observações", 8),
        )
        facts = [
            f"{label}: {value}"
            for label, index in labels
            if (value := self._entry_value(entry, index))
        ]
        return "\n".join(facts) or "Sem dados adicionais cadastrados."

    def stop_video(self) -> None:
        """Para a reprodução ao sair da subaba."""
        self.media_panel.stop_video()

    def _render_items(self, items: list[dict[str, Any]]) -> None:
        self.items_table.setRowCount(len(items))
        for row_index, item in enumerate(items):
            platform_prices = item.get("platform_prices") or {}
            selected_marketplace = str(
                self.marketplace_choice.currentData() or ""
            )
            values = (
                item.get("id", ""),
                item.get("kit", ""),
                item.get("platforms", ""),
                self._format_money(
                    platform_prices.get(
                        selected_marketplace,
                        item.get("sale_price"),
                    )
                ),
                self._format_money(item.get("cost")),
                item.get("stock", 0),
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(
                    str(value if value is not None else "")
                )
                cell.setFlags(
                    cell.flags() & ~Qt.ItemFlag.ItemIsEditable
                )
                self.items_table.setItem(row_index, column, cell)

    @staticmethod
    def _format_money(value: object) -> str:
        try:
            amount = float(value)
        except (TypeError, ValueError):
            return "—"
        formatted = f"{amount:,.2f}".replace(",", "_")
        formatted = formatted.replace(".", ",").replace("_", ".")
        return f"R$ {formatted}"

    def _begin_edit(self) -> None:
        if not self._has_marketplace_records:
            self.status_label.setText(
                "Salve os dados comerciais em Montar anúncio antes de editar."
            )
            return
        self._editing = True
        self.title_edit.setReadOnly(False)
        self.description_edit.setReadOnly(False)
        self.product_combo.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.edit_button.hide()
        self.save_button.show()
        self.cancel_button.show()
        self.status_label.setText(
            "Modo de edição. As alterações só entram no banco após salvar."
        )

    def _set_editing(self, editing: bool) -> None:
        self._editing = editing
        self.title_edit.setReadOnly(not editing)
        self.description_edit.setReadOnly(not editing)
        self.product_combo.setEnabled(not editing)
        self.refresh_button.setEnabled(not editing)
        self.marketplace_choice.setEnabled(not editing)
        self.manage_marketplaces_button.setEnabled(not editing)
        self.edit_button.setEnabled(
            bool(self._current_product and self._has_marketplace_records)
        )
        self.edit_button.setVisible(not editing)
        self.save_button.setVisible(editing)
        self.cancel_button.setVisible(editing)
        self.copy_title_button.setEnabled(bool(self._current_product))
        self.copy_description_button.setEnabled(bool(self._current_product))
        self.copy_full_button.setEnabled(bool(self._current_product))

    def _save_edits(self) -> None:
        title = self.title_edit.text().strip()
        description = self.description_edit.toPlainText().strip()
        if not title:
            popup_erro(
                "Título obrigatório",
                "Informe um título antes de salvar o anúncio.",
                self,
            )
            return
        try:
            updated_ids = salvar_textos_anuncio_marketplace(
                self._current_product,
                title,
                description,
                str(self.marketplace_choice.currentData() or "") or None,
            )
        except Exception as exc:
            self.status_label.setText(
                f"Não foi possível salvar o anúncio: {exc}"
            )
            popup_erro("Não foi possível salvar", str(exc), self)
            return

        self._saved_title = title
        self._saved_description = description
        self._commercial_data["title"] = title
        self._commercial_data["description"] = description
        marketplace = str(self.marketplace_choice.currentData() or "")
        if marketplace:
            self._listing_by_marketplace[marketplace.casefold()] = {
                "marketplace": marketplace,
                "title": title,
                "description": description,
                "active": True,
            }
        self._set_editing(False)
        self.status_label.setText(
            f"Anúncio salvo para {updated_ids} ID(s), sem alterar estoque."
        )
        self.texto_salvo.emit(self._current_product, title, description)
        popup_info(
            "Anúncio salvo",
            "Título e descrição foram atualizados no banco de dados.",
            self,
        )

    def _cancel_edit(self) -> None:
        self.title_edit.setText(self._saved_title)
        self.description_edit.setPlainText(self._saved_description)
        self._set_editing(False)
        self.status_label.setText("Edição cancelada.")

    def _copy_text(self, text: str, label: str) -> None:
        if not text:
            self.status_label.setText(f"Não há {label.lower()} para copiar.")
            return
        QApplication.clipboard().setText(text)
        self.status_label.setText(f"{label} copiado.")

    def _copy_title(self) -> None:
        self._copy_text(self.title_edit.text().strip(), "Título")

    def _copy_description(self) -> None:
        self._copy_text(
            self.description_edit.toPlainText().strip(),
            "Descrição",
        )

    def _copy_full_listing(self) -> None:
        if not self._current_product:
            return
        reference = self._entry_value(self._source_entry, 1) or "Não informada"
        parts = [
            f"Produto: {self._current_product}",
            f"Referência: {reference}",
            "Categoria: não cadastrada no banco atual",
            "",
            "TÍTULO",
            self.title_edit.text().strip(),
            "",
            "DESCRIÇÃO",
            self.description_edit.toPlainText().strip(),
            "",
            "DADOS DO PRODUTO",
            self.facts_view.toPlainText().strip(),
            "",
            "DADOS COMERCIAIS POR ID",
        ]
        for item in self._commercial_data.get("items", []):
            parts.append(
                " | ".join(
                    (
                        f"ID: {item.get('id', '')}",
                        f"Kit: {item.get('kit', '')}",
                        f"Marketplaces: {item.get('platforms', '')}",
                        f"Venda: {self._format_money(item.get('sale_price'))}",
                        f"Custo: {self._format_money(item.get('cost'))}",
                        f"Estoque: {item.get('stock', 0)}",
                    )
                )
            )
        self._copy_text("\n".join(parts).strip(), "Ficha completa")
