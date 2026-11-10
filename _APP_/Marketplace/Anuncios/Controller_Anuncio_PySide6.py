"""Interface da aba Anúncio sincronizada com o produto ativo da Criação."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from PySide6.QtCore import QSize, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QIcon, QImageReader, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from _APP_.PySide6_core import (
    IMAGE_EXTENSIONS,
    _partes_nome_producao,
    carregar_itens_anuncio_marketplace,
    parse_tipo_kit,
)
from .Controller_Vendas_PySide6 import VendasController
from .Anunciar_PySide6 import AnunciarPage
from _FERRAMENTAS_.Prompts import Descrition_entrad
from _LOGS_ import log
from _APP_.product_lifecycle import (
    concluir_produto_pendente,
    migracao_concluida,
)


PASTA_MARKETPLACE = "G_marketplace"


class AnuncioController(QWidget):
    """Edita textos temporários do mesmo cadastro mostrado em Criação/Resultados."""

    ai_context_changed = Signal(dict)
    prompt_requested = Signal(str)
    refresh_requested = Signal()
    product_completed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._drafts: dict[str, dict[str, str]] = {}
        self._draft_keys_by_product: dict[str, str] = {}
        self._current_product: dict[str, Any] | None = None
        self._loading_fields = False
        self._pending_ai_state: dict[str, str] | None = None

        self._build_ui()
        self._render_empty()

    def _build_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        self.inner_pages = QTabWidget(self)
        outer_layout.addWidget(self.inner_pages)
        self.page_scroll = QScrollArea()
        self.page_scroll.setWidgetResizable(True)
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)
        self.page_scroll.setWidget(page)
        self.inner_pages.addTab(self.page_scroll, "Montar anúncio")

        header = QHBoxLayout()
        summary = QVBoxLayout()
        self.product_label = QLabel("Produto atual: nenhum")
        self.product_label.setStyleSheet("font-weight: bold;")
        summary.addWidget(self.product_label)
        self.folder_label = QLabel("Pasta do produto: —\nPasta G: —")
        self.folder_label.setWordWrap(True)
        self.folder_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        summary.addWidget(self.folder_label)
        header.addLayout(summary, 1)

        self.refresh_button = QPushButton("Atualizar produto")
        self.refresh_button.setToolTip(
            "Atualiza o produto atual a partir do mesmo fluxo de Criação/Resultados."
        )
        self.refresh_button.clicked.connect(self._request_refresh)
        header.addWidget(self.refresh_button)

        self.open_folder_button = QPushButton("Abrir pasta")
        self.open_folder_button.setEnabled(False)
        self.open_folder_button.clicked.connect(self._open_product_folder)
        header.addWidget(self.open_folder_button)
        root.addLayout(header)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        facts_box = QGroupBox("Informações do produto — somente leitura")
        facts_layout = QVBoxLayout(facts_box)
        self.facts_view = QPlainTextEdit()
        self.facts_view.setReadOnly(True)
        self.facts_view.setMaximumHeight(132)
        facts_layout.addWidget(self.facts_view)
        root.addWidget(facts_box)

        gallery_box = QGroupBox(
            "Imagens em G — conferência opcional; não enviadas à IA"
        )
        gallery_layout = QVBoxLayout(gallery_box)
        self.gallery_toggle_button = QPushButton("Mostrar imagens de G (0)")
        self.gallery_toggle_button.setCheckable(True)
        self.gallery_toggle_button.toggled.connect(self._toggle_gallery)
        gallery_layout.addWidget(self.gallery_toggle_button)

        self.gallery_content = QWidget()
        gallery_content_layout = QVBoxLayout(self.gallery_content)
        self.gallery_status_label = QLabel()
        self.gallery_status_label.setWordWrap(True)
        gallery_content_layout.addWidget(self.gallery_status_label)
        self.image_list = QListWidget()
        self.image_list.setViewMode(QListView.ViewMode.IconMode)
        self.image_list.setFlow(QListView.Flow.LeftToRight)
        self.image_list.setWrapping(True)
        self.image_list.setResizeMode(QListView.ResizeMode.Adjust)
        self.image_list.setMovement(QListView.Movement.Static)
        self.image_list.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self.image_list.setIconSize(QSize(128, 112))
        self.image_list.setGridSize(QSize(148, 148))
        self.image_list.setMinimumHeight(158)
        self.image_list.setMaximumHeight(178)
        gallery_content_layout.addWidget(self.image_list)
        gallery_layout.addWidget(self.gallery_content)
        self.gallery_content.setVisible(False)
        root.addWidget(gallery_box)

        draft_box = QGroupBox("Texto do anúncio")
        draft_layout = QVBoxLayout(draft_box)
        draft_header = QHBoxLayout()
        draft_header.addWidget(
            QLabel(
                "A resposta aparece no painel de IA; copie e cole nos campos "
                "após revisar."
            )
        )
        draft_header.addStretch(1)
        self.copy_research_prompt_button = QPushButton(
            "Copiar prompt de pesquisa web"
        )
        self.copy_research_prompt_button.setToolTip(
            "Copia o prompt original de anúncio com os dados do Cadastro e a "
            "divisão de venda dos kits. Cole em uma IA externa com busca na web; "
            "este aplicativo não pesquisa preços."
        )
        self.copy_research_prompt_button.clicked.connect(
            self._copy_marketplace_research_prompt
        )
        draft_header.addWidget(self.copy_research_prompt_button)
        self.generate_button = QPushButton("Gerar sugestão no chat")
        self.generate_button.setToolTip(
            "Envia o pedido à IA. A resposta fica no chat; os campos não são "
            "alterados automaticamente."
        )
        self.generate_button.clicked.connect(self._prepare_prompt)
        draft_header.addWidget(self.generate_button)
        draft_layout.addLayout(draft_header)

        fields = QFormLayout()
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Digite ou revise o título")
        self.description_edit = QPlainTextEdit()
        self.description_edit.setPlaceholderText(
            "Digite ou revise a descrição do produto"
        )
        self.description_edit.setMinimumHeight(118)
        self.title_edit.textChanged.connect(self._remember_draft)
        self.description_edit.textChanged.connect(self._remember_draft)
        fields.addRow("Título:", self.title_edit)
        fields.addRow("Descrição:", self.description_edit)
        draft_layout.addLayout(fields)
        root.addWidget(draft_box)

        self.action_status_label = QLabel()
        self.action_status_label.setWordWrap(True)
        root.addWidget(self.action_status_label)

        self.marketplace_setup = VendasController(
            parent=self,
            embedded=True,
        )
        self.marketplace_setup.set_announcement_text_provider(
            self.textos_para_salvar
        )
        root.addWidget(self.marketplace_setup)
        completion_note = QLabel(
            "São duas etapas diferentes: “Salvar anúncio e preços no banco” "
            "grava os dados comerciais, mas mantém o produto no Cadastro. "
            "Depois de salvar e conferir todos os IDs, conclua para copiar o "
            "cadastro para os dados permanentes do Marketplace. Só a linha "
            "deste produto na fila A_ENTRADA é removida após confirmar a cópia; "
            "a tabela, os demais produtos, IDs, estoque, histórico e arquivos "
            "de mídia são preservados."
        )
        completion_note.setWordWrap(True)
        root.addWidget(completion_note)
        self.complete_product_button = QPushButton(
            "Concluir produto e mover para Marketplace"
        )
        self.complete_product_button.setToolTip(
            "Copia o cadastro para os dados permanentes. Após confirmar a cópia, "
            "remove somente a linha deste produto de A_ENTRADA; não apaga a "
            "tabela, os IDs ou os arquivos de mídia."
        )
        self.complete_product_button.clicked.connect(
            self._confirmar_conclusao_produto
        )
        root.addWidget(self.complete_product_button)

        self.anunciar_page = AnunciarPage(self)
        self.anunciar_page.texto_salvo.connect(
            self._sync_saved_listing_text
        )
        self.inner_pages.addTab(self.anunciar_page, "Anunciar")
        self.inner_pages.currentChanged.connect(self._on_inner_page_changed)

    def _on_inner_page_changed(self, index: int) -> None:
        if self.inner_pages.widget(index) is self.anunciar_page:
            self.anunciar_page.refresh_products()
        else:
            self.anunciar_page.stop_video()

    def _sync_saved_listing_text(
        self,
        product_name: str,
        title: str,
        description: str,
    ) -> None:
        product = self._current_product
        if (
            not product
            or str(product.get("name") or "").casefold()
            != str(product_name or "").casefold()
        ):
            return

        draft_key = str(product.get("draft_key") or product["key"])
        self._drafts.pop(draft_key, None)
        commercial_data = dict(product.get("commercial_data") or {})
        commercial_data["title"] = title
        commercial_data["description"] = description
        product["commercial_data"] = commercial_data

        self._loading_fields = True
        self.title_edit.setText(title)
        self.description_edit.setPlainText(description)
        self._loading_fields = False
        self.action_status_label.setText(
            "Título e descrição atualizados pela subaba Anunciar."
        )
        self.ai_context_changed.emit(self.ai_context_snapshot())

    def _toggle_gallery(self, expanded: bool) -> None:
        self.gallery_content.setVisible(expanded)
        self._update_gallery_toggle_label()

    def _update_gallery_toggle_label(self) -> None:
        product = self._current_product
        image_count = len(product["images"]) if product else 0
        action = (
            "Ocultar"
            if self.gallery_toggle_button.isChecked()
            else "Mostrar"
        )
        self.gallery_toggle_button.setText(
            f"{action} imagens de G ({image_count})"
        )

    def _request_refresh(self) -> None:
        log.info(
            "Anuncio",
            "_request_refresh",
            "usuário solicitou atualização do produto ativo",
        )
        self.refresh_requested.emit()

    def set_current_row(self, row: Any) -> None:
        """Recebe exatamente o registro ativo que Criação/Resultados já usa."""
        if not row:
            self._render_empty()
            return

        name = str(row[0] or "").strip() if len(row) > 0 else ""
        reference = str(row[1] or "").strip() if len(row) > 1 else ""
        raw_folder = str(row[2] or "").strip() if len(row) > 2 else ""
        folder = Path(raw_folder).expanduser() if raw_folder else None
        marketplace_folder = folder / PASTA_MARKETPLACE if folder else None

        image_paths: list[Path] = []
        image_extensions = {
            str(extension).casefold() for extension in IMAGE_EXTENSIONS
        }
        if marketplace_folder and marketplace_folder.is_dir():
            try:
                image_paths = sorted(
                    (
                        path
                        for path in marketplace_folder.iterdir()
                        if path.is_file()
                        and path.suffix.casefold() in image_extensions
                        and QImageReader(str(path)).canRead()
                    ),
                    key=lambda path: path.name.casefold(),
                )
            except OSError as exc:
                log.aviso(
                    "Anuncio",
                    "set_current_row",
                    f"não foi possível listar a pasta G: {exc}",
                )

        regras_json = (
            str(row[9] or "").strip()
            if len(row) > 9
            else ""
        )
        try:
            regras_salvas = json.loads(regras_json) if regras_json else []
        except (TypeError, json.JSONDecodeError):
            regras_salvas = []
            log.aviso(
                "Anuncio",
                "set_current_row",
                f"REGRAS_ANUNCIO inválido para o produto {name or '-'}",
            )
        if not isinstance(regras_salvas, list):
            regras_salvas = []
        regras = [
            {
                "id": str(regra.get("id") or ""),
                "titulo": str(regra.get("titulo") or "").strip(),
                "descricao": str(regra.get("descricao") or "").strip(),
            }
            for regra in regras_salvas
            if isinstance(regra, dict)
            and str(regra.get("titulo") or "").strip()
        ]
        product = {
            "key": name,
            "name": name or "(produto sem nome)",
            "reference": reference,
            "folder": folder,
            "marketplace_folder": marketplace_folder,
            "images": image_paths,
            "description": str(row[3] or "").strip() if len(row) > 3 else "",
            "use": str(row[4] or "").strip() if len(row) > 4 else "",
            "includes": str(row[5] or "").strip() if len(row) > 5 else "",
            "finish": str(row[6] or "").strip() if len(row) > 6 else "",
            "kit": str(row[7] or "").strip() if len(row) > 7 else "",
            "observations": str(row[8] or "").strip() if len(row) > 8 else "",
            "rules": regras,
            "rules_json": regras_json,
        }
        product["draft_key"] = self._draft_identity(product)
        self._draft_keys_by_product[
            str(product.get("name") or "").casefold()
        ] = str(product["draft_key"])
        try:
            product["commercial_data"] = carregar_itens_anuncio_marketplace(
                product["name"]
            )
        except Exception as exc:
            product["commercial_data"] = {
                "title": "",
                "description": "",
                "items": [],
            }
            product["commercial_error"] = str(exc)
            log.aviso(
                "Anuncio",
                "set_current_row",
                f"não foi possível carregar dados do marketplace: {exc}",
            )
        self._render_product(product)
        log.info(
            "Anuncio",
            "set_current_row",
            (
                f"produto ativo sincronizado; produto={product['key'] or '-'}; "
                f"imagens_g={len(image_paths)}"
            ),
        )

    @staticmethod
    def _draft_identity(product: dict[str, Any]) -> str:
        """Evita reutilizar rascunho se o cadastro de mesmo nome mudou."""
        identity = [
            str(product.get(field) or "")
            for field in (
                "key",
                "reference",
                "description",
                "use",
                "includes",
                "finish",
                "kit",
                "observations",
                "rules_json",
            )
        ]
        identity.insert(2, str(product.get("folder") or ""))
        return json.dumps(identity, ensure_ascii=False, separators=(",", ":"))

    def _render_product(self, product: dict[str, Any]) -> None:
        self._current_product = product
        self._loading_fields = True

        draft_key = str(product.get("draft_key") or product["key"])
        draft = self._drafts.get(draft_key, {})
        commercial_data = product.get("commercial_data", {})
        self.title_edit.setText(
            draft.get(
                "title",
                str(commercial_data.get("title") or product["name"]),
            )
        )
        self.description_edit.setPlainText(
            draft.get(
                "description",
                str(
                    commercial_data.get("description")
                    or product["description"]
                ),
            )
        )

        folder = product["folder"]
        marketplace_folder = product["marketplace_folder"]
        self.product_label.setText(
            f"Produto atual: {product['name']}"
            + (
                f" · {product['reference']}"
                if product["reference"]
                else ""
            )
        )
        self.folder_label.setText(
            f"Pasta do produto: {folder or 'não informada'}\n"
            f"Pasta G: {marketplace_folder or 'não definida'}"
        )
        self.folder_label.setToolTip(
            str(marketplace_folder or folder or "")
        )

        fact_lines = [
            f"Produto: {product['name']}",
            f"Referência: {product['reference'] or '(não informada)'}",
            f"Pasta do produto: {folder or '(não informada)'}",
            f"Pasta G: {marketplace_folder or '(não definida)'}",
            f"Imagens legíveis em G: {len(product['images'])}",
        ]
        for label, key in (
            ("Descrição de origem", "description"),
            ("Uso", "use"),
            ("O que acompanha", "includes"),
            ("Acabamento", "finish"),
            ("Observações existentes", "observations"),
        ):
            value = product[key]
            if value:
                fact_lines.append(f"{label}: {value}")
        self.facts_view.setPlainText("\n".join(fact_lines))

        self.image_list.clear()
        loaded_count = 0
        for path in product["images"]:
            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                continue
            icon_pixmap = pixmap.scaled(
                self.image_list.iconSize(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            item = QListWidgetItem(QIcon(icon_pixmap), path.name)
            item.setToolTip("Imagem somente para conferência humana.")
            self.image_list.addItem(item)
            loaded_count += 1

        if not marketplace_folder:
            gallery_status = "O caminho de G não está definido neste cadastro."
        elif not marketplace_folder.is_dir():
            gallery_status = (
                f"A pasta G ainda não existe: {marketplace_folder}"
            )
        elif not product["images"]:
            gallery_status = (
                f"A pasta G está disponível, mas ainda não tem imagens "
                f"legíveis: {marketplace_folder}"
            )
        else:
            gallery_status = (
                f"{len(product['images'])} imagem(ns) legível(is) em "
                f"{marketplace_folder}"
            )
        self.gallery_status_label.setText(gallery_status)
        self._update_gallery_toggle_label()
        self.status_label.setText(
            "Este é o mesmo produto ativo em Criação/Resultados. "
            "A lista de imagens não determina qual cadastro aparece aqui."
        )

        self._loading_fields = False
        self.marketplace_setup.set_current_product(product["name"])
        self._set_product_actions_enabled(True)
        self.open_folder_button.setEnabled(folder is not None)
        if loaded_count != len(product["images"]):
            self.action_status_label.setText(
                "Algumas imagens não puderam ser pré-visualizadas. "
                "A IA recebe somente os dados textuais, não os pixels."
            )
        else:
            self.action_status_label.setText(
                "Revise o anúncio e salve a configuração comercial nesta aba. "
                "A IA recebe somente texto."
            )
        self.ai_context_changed.emit(self.ai_context_snapshot())

    def _render_empty(self) -> None:
        self._current_product = None
        self._loading_fields = True
        self.product_label.setText("Produto atual: nenhum")
        self.folder_label.setText("Pasta do produto: —\nPasta G: —")
        self.folder_label.setToolTip("")
        self.status_label.setText(
            "Nenhum cadastro ativo foi encontrado em Criação/Resultados. "
            "Cadastre um produto para preparar o anúncio."
        )
        self.gallery_status_label.setText("Sem produto ativo.")
        self.facts_view.clear()
        self.image_list.clear()
        self.gallery_toggle_button.setChecked(False)
        self._update_gallery_toggle_label()
        self.title_edit.clear()
        self.description_edit.clear()
        self._loading_fields = False
        self.marketplace_setup.set_current_product("")
        self._set_product_actions_enabled(False)
        self.open_folder_button.setEnabled(False)
        self.action_status_label.setText(
            "Cadastre e produza um produto para preparar o rascunho do anúncio."
        )
        self.ai_context_changed.emit({})

    def _set_product_actions_enabled(self, enabled: bool) -> None:
        self.title_edit.setEnabled(enabled)
        self.description_edit.setEnabled(enabled)
        self.gallery_toggle_button.setEnabled(enabled)
        self.generate_button.setEnabled(
            enabled and self._pending_ai_state is None
        )
        self.copy_research_prompt_button.setEnabled(enabled)
        self.complete_product_button.setEnabled(
            enabled and migracao_concluida()
        )

    def _confirmar_conclusao_produto(self) -> None:
        product = self._current_product
        if not product:
            return
        if not migracao_concluida():
            QMessageBox.information(
                self,
                "Banco ainda não atualizado",
                "Abra Configuração > Banco de dados e execute a atualização "
                "com backup verificado antes de concluir produtos.",
            )
            return
        nome = str(product.get("key") or "").strip()
        resposta = QMessageBox.question(
            self,
            "Concluir produto",
            f"Concluir “{nome}” e movê-lo para Marketplace? O cadastro será "
            "copiado para os dados permanentes. Depois de confirmar a cópia, "
            "somente a linha deste produto em A_ENTRADA será removida. A tabela, "
            "os demais produtos, IDs, estoque, histórico e arquivos de mídia "
            "serão preservados.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return
        try:
            concluir_produto_pendente(nome)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Produto não concluído",
                f"O produto continua na fila.\n\n{exc}",
            )
            log.erro("Anuncio", "_confirmar_conclusao_produto", str(exc))
            return
        self.product_completed.emit(nome)

    def _remember_draft(self, *_args: object) -> None:
        if self._loading_fields or not self._current_product:
            return
        self._drafts[
            str(
                self._current_product.get("draft_key")
                or self._current_product["key"]
            )
        ] = {
            "title": self.title_edit.text(),
            "description": self.description_edit.toPlainText(),
        }

    def textos_para_salvar(self, nome_produto: str) -> dict[str, str]:
        """Retorna o rascunho deste produto para a aba Vendas persistir."""
        nome_produto = str(nome_produto or "").strip()
        product = self._current_product
        draft_key = self._draft_keys_by_product.get(nome_produto.casefold())
        if (
            product
            and str(product.get("name") or "").casefold()
            == nome_produto.casefold()
        ):
            draft_key = str(product.get("draft_key") or product["key"])
        draft = self._drafts.get(draft_key or "")
        if draft is not None:
            return {
                "title": draft.get("title", self.title_edit.text()),
                "description": draft.get(
                    "description", self.description_edit.toPlainText()
                ),
            }
        if (
            product
            and str(product.get("name") or "").casefold()
            == nome_produto.casefold()
        ):
            saved = product.get("commercial_data", {})
            return {
                "title": str(saved.get("title") or ""),
                "description": str(saved.get("description") or ""),
            }

        try:
            data = carregar_itens_anuncio_marketplace(nome_produto)
        except Exception as exc:
            log.aviso(
                "Anuncio",
                "textos_para_salvar",
                f"não foi possível carregar textos já salvos: {exc}",
            )
            return {"title": "", "description": ""}
        return {
            "title": str(data.get("title") or ""),
            "description": str(data.get("description") or ""),
        }

    def ai_context_snapshot(self) -> dict[str, Any]:
        """Contexto textual isolado do produto ativo no fluxo de Criação."""
        product = self._current_product
        if not product:
            return {}
        return {
            "memoria_tipo": "produto",
            "produto_id": product["key"],
            "nome": product["name"],
            "referencia": product["reference"],
            "descricao_origem": product["description"],
            "uso": product["use"],
            "acompanha": product["includes"],
            "acabamento": product["finish"],
            "observacoes": product["observations"],
        }

    def _prepare_prompt(self) -> None:
        product = self._current_product
        if not product:
            self.action_status_label.setText(
                "Não há produto ativo para gerar o anúncio."
            )
            return
        if self._pending_ai_state is not None:
            return

        facts = [
            f"Produto: {product['name']}",
            f"Referência: {product['reference'] or '(não informada)'}",
            f"Descrição de origem: {product['description'] or '(não informada)'}",
            f"Uso: {product['use'] or '(não informado)'}",
            f"O que acompanha: {product['includes'] or '(não informado)'}",
            f"Acabamento: {product['finish'] or '(não informado)'}",
        ]
        if product["observations"]:
            facts.append(f"Observações existentes: {product['observations']}")

        current_title = self.title_edit.text().strip() or "(vazio)"
        current_description = (
            self.description_edit.toPlainText().strip() or "(vazia)"
        )
        prompt = "\n".join(
            [
                "Crie ou revise o título e a descrição deste anúncio.",
                "O produto-alvo é exclusivamente o produto identificado nos "
                "fatos deste pedido. Ignore nomes, especificações e usos de "
                "outros produtos mencionados anteriormente na conversa.",
                "Use português do Brasil e apenas os fatos confirmados abaixo. "
                "Não invente medidas, materiais, compatibilidades, certificações, "
                "preços ou benefícios.",
                "Use apenas a composição e as formas de venda explicitamente "
                "registradas abaixo. Se faltar informação, não complete por "
                "inferência.",
                "As linhas de produtos.txt podem ser registros por imagem; "
                "não as trate como produtos ou variações vendáveis.",
                "As imagens de G não foram enviadas para análise visual.",
                "Responda em texto simples e copiável, sem JSON, sem bloco de "
                "código e sem dados técnicos fora do que foi confirmado.",
                "Esta instrução substitui qualquer formato JSON usado em "
                "respostas anteriores desta conversa.",
                "Use exatamente estas seções, com os títulos indicados:",
                "Título sugerido:",
                "[escreva aqui o título final, sem colchetes]",
                "",
                "Descrição do anúncio:",
                "[escreva aqui a descrição final, sem colchetes]",
                "Se faltar um fato importante, diga o que falta em vez de "
                "inventá-lo.",
                "A resposta será revisada e copiada manualmente pelo usuário. "
                "Não tente preencher nem alterar os campos da interface.",
                "",
                "FATOS DO CADASTRO:",
                *facts,
                "",
                "MEDIDAS/PESO DO PRODUTO:",
                self._marketplace_measurements_context(product),
                "",
                self._marketplace_sale_context(
                    product,
                    include_marketplace_pricing=False,
                ),
                "",
                "TÍTULO ATUAL:",
                current_title,
                "",
                "DESCRIÇÃO ATUAL:",
                current_description,
            ]
        )
        self._pending_ai_state = {
            "product_key": product["key"],
            "snapshot_key": str(product.get("draft_key") or product["key"]),
            "title": self.title_edit.text(),
            "description": self.description_edit.toPlainText(),
        }
        self._set_product_actions_enabled(True)
        self.action_status_label.setText(
            "Enviando o pedido à IA. A resposta ficará no painel de conversa "
            "para você revisar e copiar; os campos não serão alterados."
        )
        log.info(
            "Anuncio",
            "_prepare_prompt",
            (
                f"geração solicitada; produto={product['key'] or '-'}; "
                f"imagens_g={len(product['images'])}"
            ),
        )
        self.prompt_requested.emit(prompt)

    def _marketplace_measurements_context(
        self,
        product: dict[str, Any],
    ) -> str:
        folder = product.get("folder")
        measures_file = folder / "produtos.txt" if folder else None
        if not measures_file or not measures_file.is_file():
            return (
                "Medidas e peso: produtos.txt não encontrado na pasta do "
                "produto; não foram informados nesta solicitação."
            )

        try:
            lines = measures_file.read_text(
                encoding="utf-8-sig"
            ).splitlines()
        except (OSError, UnicodeError) as exc:
            log.aviso(
                "Anuncio",
                "_marketplace_measurements_context",
                f"não foi possível ler produtos.txt: {exc}",
            )
            return (
                "Medidas e peso: produtos.txt existe, mas não pôde ser lido; "
                "não foram informados nesta solicitação."
            )

        entries: list[dict[str, Any]] = []
        for line in lines:
            raw = line.strip()
            if not raw:
                continue
            dimensions, separator, weight = raw.partition(",")
            values = [
                value.strip()
                for value in dimensions.replace("×", "x")
                .replace("X", "x")
                .split("x")
            ]
            if len(values) < 3 or not all(values[:3]):
                continue
            weight_raw = weight.strip() if separator else ""
            if not weight_raw:
                weight_text = "(não informado)"
                weight_key = ""
            elif re.search(
                r"(?:quilogramas?|kg|gramas?|grams?|g)\s*$",
                weight_raw,
                flags=re.IGNORECASE,
            ):
                weight_text = weight_raw
                weight_key = re.sub(
                    r"\s+",
                    "",
                    weight_raw.casefold().replace(",", "."),
                )
            else:
                # O formatador legado interpreta peso sem unidade como gramas.
                weight_text = (
                    f"{weight_raw} g (unidade ausente; convenção legada do "
                    "Cadastro)"
                )
                weight_key = re.sub(
                    r"\s+",
                    "",
                    weight_raw.casefold().replace(",", "."),
                ) + "g"

            dimensions = " x ".join(values[:3])
            dimension_key = tuple(
                re.sub(r"\s+", "", value.casefold()).replace("×", "x")
                for value in values[:3]
            )
            entries.append(
                {
                    "dimensions": dimensions,
                    "weight": weight_text,
                    "signature": (dimension_key, weight_key),
                }
            )

        if not entries:
            return (
                "Medidas e peso: produtos.txt não contém registros válidos "
                "no formato esperado."
            )

        grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
        for entry in entries:
            signature = entry["signature"]
            if signature not in grouped:
                grouped[signature] = {"entry": entry, "count": 0}
            grouped[signature]["count"] += 1

        config = parse_tipo_kit(str(product.get("kit") or ""))
        type_value = str(config.get("TIPO") or "").strip().upper()
        try:
            variation_count = int(config.get("VAR") or "0")
        except ValueError:
            variation_count = 0
        kit_value = str(config.get("KIT") or "").strip().upper()
        is_single_configuration = (
            type_value in {"ÚNICO", "UNICO"}
            and variation_count == 1
            and kit_value in {"NO", "NÃO", "NAO", "FALSE", "0"}
        )

        measurement_lines = []
        for item in grouped.values():
            entry = item["entry"]
            repeated = int(item["count"])
            count_note = (
                f" (repetida em {repeated} linhas de imagem)"
                if repeated > 1
                else ""
            )
            measurement_lines.append(
                f"- {entry['dimensions']} cm; peso: {entry['weight']}"
                f"{count_note}"
            )

        if is_single_configuration and len(grouped) == 1:
            return "\n".join(
                [
                    "Configuração vendável confirmada no Cadastro: produto "
                    "único, 1 variação, sem kit.",
                    "Medida da configuração:",
                    measurement_lines[0],
                    f"O arquivo contém {len(entries)} linha(s) válida(s) "
                    "porque o Cadastro registra medidas por imagem. Linhas "
                    "repetidas não são produtos, unidades de estoque nem "
                    "variações adicionais. Essas linhas não correspondem à "
                    "contagem da pasta G_marketplace.",
                ]
            )

        lines = [
            f"Medidas e peso registrados por imagem: {len(entries)} linha(s) "
            f"válida(s), {len(grouped)} combinação(ões) distinta(s).",
            "As repetições indicam linhas de imagem, não quantidade de "
            "produtos ou variações vendáveis.",
            "A contagem dessas linhas não é a contagem de imagens em "
            "G_marketplace.",
            "Não associe uma linha a uma variação ou peça de kit sem uma "
            "identificação explícita; não calcule preço por linha.",
            *measurement_lines,
        ]
        if is_single_configuration:
            lines.insert(
                0,
                "ATENÇÃO: o Cadastro informa 1 variação sem kit, mas as "
                "medidas das linhas não coincidem. Aponte a inconsistência "
                "e não atribua cada medida a uma variação.",
            )
        return "\n".join(lines)

    @staticmethod
    def _marketplace_weight_grams(value: str) -> float | None:
        text = str(value or "").strip().casefold().replace(",", ".")
        match = re.fullmatch(
            r"(\d+(?:\.\d+)?)\s*(kg|quilogramas?|g|gr|gm|gramas?)?",
            text,
        )
        if not match:
            return None
        amount = float(match.group(1))
        return amount * 1000 if match.group(2) == "kg" else amount

    @staticmethod
    def _marketplace_registered_groups(
        product: dict[str, Any],
    ) -> tuple[dict[str, dict[str, Any]], str]:
        """Relaciona cada linha de produtos.txt à imagem/grupo do Cadastro."""
        if not str(product.get("folder") or "").strip():
            return {}, "A pasta do produto não foi informada pelo Cadastro."
        folder = Path(str(product.get("folder") or ""))
        products_file = folder / "produtos.txt"
        order_file = folder / ".ordem_midias.json"
        if not products_file.is_file() or not order_file.is_file():
            return {}, (
                "Não foi possível relacionar produtos.txt aos grupos: falta "
                "produtos.txt ou .ordem_midias.json na pasta do produto."
            )

        try:
            media_order = json.loads(order_file.read_text(encoding="utf-8"))
            if not isinstance(media_order, list):
                raise ValueError(".ordem_midias.json não contém uma lista.")
            image_names = [
                Path(str(name)).name
                for name in media_order
                if Path(str(name)).suffix.lower() in IMAGE_EXTENSIONS
            ]
            product_rows = [
                line.strip()
                for line in products_file.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except (OSError, TypeError, ValueError) as exc:
            return {}, f"Não foi possível ler o mapeamento dos grupos: {exc}"

        if len(image_names) != len(product_rows):
            return {}, (
                "O número de linhas de produtos.txt não confere com as imagens "
                "do manifesto; não associe medidas a peças de um kit."
            )

        groups: dict[str, dict[str, Any]] = {}
        unmapped: list[str] = []
        reference = str(product.get("reference") or "").strip()
        for image_name, row in zip(image_names, product_rows):
            dimensions_raw, separator, weight_raw = row.partition(",")
            dimensions = " x ".join(
                part.strip()
                for part in dimensions_raw.lower().replace("×", "x").split("x")
                if part.strip()
            )
            try:
                group_name, _filename_dimensions, _filename_weight = (
                    _partes_nome_producao(image_name)
                )
            except (TypeError, ValueError) as exc:
                unmapped.append(f"{image_name}: {exc}")
                continue

            group_key = group_name.casefold()
            group_match = (
                re.fullmatch(
                    re.escape(reference) + r"(\d+)",
                    group_name,
                    flags=re.IGNORECASE,
                )
                if reference
                else None
            )
            group_index = int(group_match.group(1)) if group_match else None
            if group_index is None:
                unmapped.append(
                    f"{image_name}: o grupo não corresponde à referência "
                    "salva no Cadastro"
                )
            record = groups.setdefault(
                group_key,
                {
                    "name": group_name,
                    "group_index": group_index,
                    "measurements": [],
                },
            )
            weight = weight_raw.strip() if separator else ""
            signature = (dimensions.casefold(), weight.casefold())
            measurement = next(
                (
                    item
                    for item in record["measurements"]
                    if item["signature"] == signature
                ),
                None,
            )
            if measurement is None:
                record["measurements"].append(
                    {
                        "signature": signature,
                        "dimensions": dimensions or "(não informadas)",
                        "weight": weight,
                        "image_rows": 1,
                        "weight_grams": AnuncioController._marketplace_weight_grams(
                            weight
                        ),
                    }
                )
            else:
                measurement["image_rows"] += 1

        warning = (
            "Não foi possível identificar alguns grupos pelos nomes das "
            "imagens: " + "; ".join(unmapped[:4])
            if unmapped
            else ""
        )
        return groups, warning

    def _marketplace_sale_context(
        self,
        product: dict[str, Any],
        *,
        include_marketplace_pricing: bool = True,
    ) -> str:
        """Expõe formas autorizadas/selecionadas e a composição real dos kits."""
        config_text = str(product.get("kit") or "")
        config = parse_tipo_kit(config_text)
        product_type = str(config.get("TIPO") or "").strip().upper()
        pieces_raw = str(config.get("PECAS") or "").strip()
        try:
            pieces_count = int(pieces_raw)
        except ValueError:
            pieces_count = 0

        allowed_forms: list[str] = []
        if product_type in {"ÚNICO", "UNICO"}:
            allowed_forms.append("Peça única")
            if (
                str(config.get("KIT") or "").strip().upper() == "YES"
                and pieces_count > 0
            ):
                allowed_forms.append(f"Kit: {pieces_count}")
        elif product_type == "KIT" and pieces_count > 0:
            allowed_forms.append(f"Kit: {pieces_count}")

        folder_text = str(product.get("folder") or "").strip()
        forms_file = (
            Path(folder_text) / "formas_venda.json"
            if folder_text
            else None
        )
        selected_forms = list(allowed_forms)
        forms_status = (
            "Formas permitidas pelo Cadastro; a Produção ainda não salvou "
            "uma seleção."
        )
        warnings: list[str] = []
        saved_groups: list[str] = []

        if forms_file is not None and forms_file.is_file():
            try:
                saved = json.loads(forms_file.read_text(encoding="utf-8"))
                same_product = (
                    str(saved.get("produto") or "").strip().casefold()
                    == str(product.get("name") or "").strip().casefold()
                )
                same_config = (
                    str(saved.get("configuracao_cadastro") or "")
                    .strip()
                    .casefold()
                    == config_text.strip().casefold()
                )
                saved_forms = saved.get("formas")
                if not same_product or not same_config:
                    warnings.append(
                        "formas_venda.json não corresponde ao produto e à "
                        "configuração atuais; a seleção salva foi ignorada."
                    )
                else:
                    saved_groups_value = saved.get("grupos")
                    if isinstance(saved_groups_value, list):
                        saved_groups = [
                            str(value).strip()
                            for value in saved_groups_value
                            if str(value).strip()
                        ]
                    if not isinstance(saved_forms, list):
                        warnings.append(
                            "formas_venda.json não contém uma lista válida de formas."
                        )
                    else:
                        requested = [
                            str(value).strip()
                            for value in saved_forms
                            if str(value).strip()
                        ]
                        selected_forms = [
                            value for value in requested if value in allowed_forms
                        ]
                        rejected = [
                            value for value in requested if value not in allowed_forms
                        ]
                        forms_status = (
                            "Formas selecionadas e gravadas pela Produção: "
                            + (", ".join(selected_forms) or "(nenhuma válida)")
                        )
                        if rejected:
                            warnings.append(
                                "O manifesto contém forma(s) não permitida(s) "
                                "pelo Cadastro: " + ", ".join(rejected)
                            )
            except (OSError, TypeError, ValueError, AttributeError) as exc:
                warnings.append(
                    f"Não foi possível validar formas_venda.json: {exc}"
                )
        elif not allowed_forms:
            forms_status = (
                "O Cadastro não informa uma forma de venda/quantidade de "
                "peças que permita montar kits com segurança."
            )

        groups, groups_warning = self._marketplace_registered_groups(product)
        try:
            variation_count = max(1, int(config.get("VAR") or "1"))
        except ValueError:
            variation_count = 1
        try:
            kit_count = max(1, int(config.get("QTS_KITS") or "1"))
        except ValueError:
            kit_count = 1

        role_by_index: dict[int, dict[str, Any]] = {}
        group_index = 0

        def add_group_role(label: str, **details: Any) -> None:
            nonlocal group_index
            group_index += 1
            role_by_index[group_index] = {"label": label, **details}

        if product_type in {"ÚNICO", "UNICO"}:
            if variation_count == 1:
                add_group_role("Produto único", kind="base")
            else:
                for variation_index in range(1, variation_count + 1):
                    add_group_role(
                        f"Variação {variation_index}",
                        kind="base",
                    )

        kit_enabled = (
            product_type == "KIT"
            or str(config.get("KIT") or "").strip().upper() == "YES"
        )
        if kit_enabled and pieces_count > 0:
            for kit_index in range(1, kit_count + 1):
                add_group_role(
                    f"Kit {kit_index} — imagem completa",
                    kind="kit_complete",
                    kit_index=kit_index,
                )
                for piece_index in range(1, pieces_count + 1):
                    add_group_role(
                        f"Kit {kit_index} — peça {piece_index}",
                        kind="kit_piece",
                        kit_index=kit_index,
                        piece_index=piece_index,
                    )

        for record in groups.values():
            record.update(role_by_index.get(record.get("group_index"), {}))

        lines = [
            "FORMAS DE VENDA E COMPOSIÇÃO (usar esta divisão ao sugerir preços):",
            forms_status,
        ]
        if allowed_forms:
            lines.append(
                "Formas autorizadas pelo Cadastro: " + ", ".join(allowed_forms)
            )
        unmapped_groups = [
            record["name"]
            for record in groups.values()
            if not record.get("label")
        ]
        if unmapped_groups:
            lines.append(
                "Grupo(s) de medida sem papel confirmado na configuração: "
                + ", ".join(unmapped_groups)
                + ". Não os atribua a uma peça de kit."
            )
        if saved_groups and (groups_warning or unmapped_groups):
            lines.append("Resumo de grupos gravado pela Produção:")
            lines.extend(f"- {value}" for value in saved_groups)
        if not selected_forms:
            lines.append(
                "Não invente opções de kit; não há forma de venda selecionada "
                "e válida para este produto."
            )

        def describe_group(record: dict[str, Any]) -> str:
            descriptions = []
            for measurement in record["measurements"]:
                weight = measurement["weight"] or "(não informado)"
                if measurement["weight"] and not re.search(
                    r"(?:kg|quilogramas?|g|gr|gm|gramas?)\s*$",
                    measurement["weight"],
                    flags=re.IGNORECASE,
                ):
                    weight += " g (convenção legada do Cadastro)"
                row_note = (
                    f"; repetida em {measurement['image_rows']} linhas de mídia"
                    if measurement["image_rows"] > 1
                    else ""
                )
                descriptions.append(
                    f"{measurement['dimensions']} cm; peso {weight}{row_note}"
                )
            if len(descriptions) > 1:
                return (
                    f"{record.get('label', record['name'])} "
                    f"[{record['name']}]: MEDIDAS/PESOS INCONSISTENTES — "
                    + " | ".join(descriptions)
                )
            label = (
                f"{record.get('label', record['name'])} [{record['name']}]"
            )
            return f"{label}: {descriptions[0]}" if descriptions else (
                f"{label}: medidas/peso não identificados."
            )

        piece_groups: dict[int, dict[int, dict[str, Any]]] = {}
        for record in groups.values():
            if record.get("kind") == "kit_piece":
                kit_index = int(record["kit_index"])
                piece_index = int(record["piece_index"])
                piece_groups.setdefault(kit_index, {})[piece_index] = record

        def append_registered_kit_components(kit_index: int) -> bool:
            components = piece_groups.get(kit_index, {})
            if not components:
                return False
            lines.append(f"Composição registrada do Kit {kit_index}:")
            weights: list[float] = []
            valid_weights = True
            for piece_index, record in sorted(components.items()):
                lines.append(
                    f"- Peça {piece_index}: {describe_group(record)} "
                    "(uma unidade; linhas repetidas são fotos, não peças extras)"
                )
                measurements = record["measurements"]
                if (
                    len(measurements) != 1
                    or measurements[0]["weight_grams"] is None
                ):
                    valid_weights = False
                else:
                    weights.append(float(measurements[0]["weight_grams"]))
            expected_pieces = set(range(1, pieces_count + 1))
            actual_pieces = set(components)
            if pieces_count and actual_pieces != expected_pieces:
                missing = sorted(expected_pieces - actual_pieces)
                unexpected = sorted(actual_pieces - expected_pieces)
                details = []
                if missing:
                    details.append(
                        "faltam peças " + ", ".join(map(str, missing))
                    )
                if unexpected:
                    details.append(
                        "peças não previstas " + ", ".join(map(str, unexpected))
                    )
                lines.append(
                    f"ATENÇÃO: composição divergente do Cadastro "
                    f"({'; '.join(details)})."
                )
                valid_weights = False
            if valid_weights and weights:
                total = sum(weights)
                total_text = (
                    f"{total / 1000:g} kg" if total >= 1000 else f"{total:g} g"
                )
                lines.append(f"Peso total calculado do kit: {total_text}.")
            elif components:
                lines.append(
                    "Peso total do kit não calculado: confira as unidades/pesos "
                    "de todas as peças no Cadastro."
                )
            return True

        for form in selected_forms:
            kit_match = re.fullmatch(r"Kit:\s*(\d+)", form, flags=re.IGNORECASE)
            if not kit_match:
                continue
            if product_type == "KIT":
                registered_kits = sorted(piece_groups)
                if not registered_kits:
                    lines.append(
                        f"{form}: a quantidade foi autorizada pelo Cadastro, "
                        "mas não foi possível mapear os grupos de cada peça. "
                        "Não divida as linhas de produtos.txt como se fossem peças."
                    )
                else:
                    for kit_index in registered_kits:
                        append_registered_kit_components(kit_index)
            else:
                used_registered_components = False
                for kit_index in sorted(piece_groups):
                    used_registered_components = (
                        append_registered_kit_components(kit_index)
                        or used_registered_components
                    )
                if not used_registered_components:
                    base_groups = [
                        record
                        for record in groups.values()
                        if record.get("kind") == "base"
                    ]
                    if base_groups:
                        lines.append(
                            f"{form}: composição do fluxo antigo — "
                            f"{kit_match.group(1)} unidade(s) da mesma variação. "
                            "Separe o preço de cada forma de venda."
                        )
                        for record in base_groups:
                            details = describe_group(record)
                            measurement = (
                                record["measurements"][0]
                                if len(record["measurements"]) == 1
                                else None
                            )
                            total = (
                                float(measurement["weight_grams"])
                                * int(kit_match.group(1))
                                if measurement
                                and measurement["weight_grams"] is not None
                                else None
                            )
                            total_text = (
                                f"; peso total por kit: "
                                f"{total / 1000:g} kg"
                                if total is not None and total >= 1000
                                else (
                                    f"; peso total por kit: {total:g} g"
                                    if total is not None
                                    else "; peso total não calculado"
                                )
                            )
                            lines.append(f"- {details}{total_text}")
                    else:
                        lines.append(
                            f"{form}: composição por peça não mapeada; não "
                            "presuma que as linhas de imagem sejam unidades."
                        )

        if product_type in {"ÚNICO", "UNICO"}:
            base_groups = [
                record
                for record in groups.values()
                if record.get("kind") == "base"
            ]
            if base_groups:
                lines.append("Peça única/variações registradas no Cadastro:")
                lines.extend(f"- {describe_group(record)}" for record in base_groups)
        elif product_type == "KIT" and not piece_groups:
            lines.append(
                "A configuração declara um kit, mas os grupos de peças não "
                "foram mapeados. Não invente a composição nem o peso total."
            )

        if groups_warning:
            lines.append("AVISO DE MAPEAMENTO: " + groups_warning)
        lines.extend("AVISO: " + warning for warning in warnings)
        lines.append(
            "Não associe o grupo 'completo' como uma peça adicional. Cada grupo "
            "de 'peça' representa uma peça; repetições de mídia não aumentam "
            "a quantidade vendida."
        )
        if include_marketplace_pricing:
            lines.append(
                "No fluxo antigo, os preços das variações Shopee eram "
                "organizados pela regra 1:4; valide a regra vigente na consulta "
                "e sinalize se não puder confirmá-la."
            )
        return "\n".join(lines)

    def _copy_marketplace_research_prompt(self) -> None:
        product = self._current_product
        if not product:
            self.action_status_label.setText(
                "Não há produto ativo para preparar o prompt de pesquisa."
            )
            return

        finish = product["finish"]
        finish_context = (
            f"Acabamento informado no Cadastro: {finish}"
            if finish and finish not in ("[]", "()", "None")
            else "Acabamento não informado. Não deduza material, procedência "
            "ou tipo de acabamento."
        )

        facts = [
            f"Referência: {product['reference'] or '(não informada)'}",
            f"Serventia: {product['use'] or '(não informada)'}",
            f"Descrição: {product['description'] or '(não informada)'}",
            f"Acompanha: {product['includes'] or '(não informado)'}",
        ]
        if product["rules"]:
            facts.append(
                "Títulos das regras marcadas: "
                + ", ".join(regra["titulo"] for regra in product["rules"])
            )
        if product["observations"]:
            facts.append(f"Observações: {product['observations']}")

        regras_contexto = ""
        if product["rules"]:
            regras_contexto = (
                "REGRAS DO ANÚNCIO MARCADAS NO CADASTRO:\n"
                + "\n\n".join(
                    f"Título: {regra['titulo']}\n"
                    f"Descrição/instrução do lojista: "
                    f"{regra['descricao'] or '(sem descrição adicional)'}"
                    for regra in product["rules"]
                )
                + "\nUse todas as regras marcadas ao redigir o anúncio, "
                "explicando ao comprador o que cada uma significa. "
                "Não aplique regras que não estejam nesta lista e não "
                "invente detalhes."
            )

        formato_saida = (
            "FORMATO OBRIGATÓRIO DA RESPOSTA:\n"
            "Mantenha a análise comercial fora do anúncio: apresente de "
            "forma concisa as 3 categorias sugeridas, poucas palavras-chave "
            "e uma recomendação principal de preço para cada forma de venda "
            "cadastrada. Não crie faixas alternativas nem kits ou variações "
            "que não estejam autorizados pelo cadastro. Se não houver pesquisa "
            "web verificável, diga isso e identifique o preço como estimativa; "
            "não invente fontes, concorrentes ou preços pesquisados.\n\n"
            "No final, entregue uma seção “ANÚNCIO PRONTO PARA COPIAR” com "
            "exatamente um único bloco de código. Esse bloco deve conter "
            "somente um título otimizado e uma descrição final coesa, pronta "
            "para publicação. Reúna na descrição as informações confirmadas "
            "sobre funções, benefícios, acabamento, medidas, conteúdo da "
            "compra. Inclua todas as regras selecionadas e suas instruções, "
            "sem alterar o sentido delas. Não coloque análise, categorias, "
            "palavras-chave, justificativas de preço, alternativas ou "
            "comentários dentro do bloco. Não crie outros "
            "blocos copiáveis nem repita informações em várias seções.\n\n"
            "Use apenas dados confirmados no cadastro e nas regras marcadas. "
            "Não trate itens vistos em fotos como inclusos sem confirmação. "
            "Não invente prazo de preparação, personalização ou necessidade de "
            "contato com o vendedor se isso não estiver informado no cadastro "
            "ou em uma regra marcada."
        )

        prompt_id = "anuncio_pesquisa_externa"
        prompt_default = Descrition_entrad("").strip()
        prompt_defaults = {prompt_id: prompt_default}
        from _FERRAMENTAS_.ia_prompt_catalogo import (
            carregar_prompts_sistema,
        )

        prompts_sistema = carregar_prompts_sistema(prompt_defaults)
        original_prompt = prompts_sistema.get(prompt_id)
        if not isinstance(original_prompt, str):
            original_prompt = prompt_default
        prompt = "\n\n".join(
            [
                original_prompt,
                "DADOS DO CADASTRO PARA COMPLETAR O PROMPT ORIGINAL:\n"
                + f"Produto: {product['name']}\n"
                + "\n".join(facts),
                "INFORMAÇÃO DE ACABAMENTO:\n" + finish_context,
                regras_contexto,
                "Me dê o preço de cada produto/forma de venda baseado nas "
                "medidas e no peso cadastrados:\n"
                + self._marketplace_measurements_context(product),
                self._marketplace_sale_context(product),
                "O produto-alvo é exclusivamente o produto identificado no "
                "Cadastro acima. Use anúncios da web apenas como comparação; "
                "não transfira para o produto-alvo nomes, características ou "
                "composições de concorrentes. Nenhuma imagem foi enviada para "
                "análise visual. Não invente dados nem afirme pesquisa sem "
                "fontes verificáveis.",
                formato_saida,
            ]
        )
        QApplication.clipboard().setText(prompt)
        self.action_status_label.setText(
            "Prompt de pesquisa copiado. Cole no ChatGPT ou em outra IA com "
            "busca na web; este aplicativo não consulta a internet."
        )
        log.info(
            "Anuncio",
            "_copy_marketplace_research_prompt",
            (
                f"prompt externo copiado; produto={product['key'] or '-'}; "
                f"caracteres={len(prompt)}"
            ),
        )

    def ai_request_rejected(self, reason: str) -> None:
        self._pending_ai_state = None
        self._set_product_actions_enabled(self._current_product is not None)
        self.action_status_label.setText(reason)
        log.aviso("Anuncio", "ai_request_rejected", str(reason))

    def ai_request_failed(self, product_id: str, reason: str) -> None:
        pending = self._pending_ai_state
        current_snapshot_key = (
            str(
                self._current_product.get("draft_key")
                or self._current_product["key"]
            )
            if self._current_product
            else ""
        )
        if (
            pending
            and pending["product_key"] == str(product_id)
            and pending.get("snapshot_key") == current_snapshot_key
        ):
            self.ai_request_rejected(
                f"A IA não concluiu a geração: {reason}"
            )

    def handle_ai_response(self, product_id: str, response: str) -> None:
        pending = self._pending_ai_state
        if not pending:
            log.aviso(
                "Anuncio",
                "handle_ai_response",
                "resposta recebida sem solicitação de Anúncio pendente",
            )
            return

        self._pending_ai_state = None
        self._set_product_actions_enabled(self._current_product is not None)
        product_key = str(product_id)
        if (
            pending["product_key"] != product_key
            or not self._current_product
            or self._current_product["key"] != product_key
            or pending.get("snapshot_key")
            != str(
                self._current_product.get("draft_key")
                or self._current_product["key"]
            )
        ):
            self.action_status_label.setText(
                "A resposta ficou na conversa do painel. O produto ativo mudou; "
                "os campos atuais não foram alterados."
            )
            log.aviso(
                "Anuncio",
                "handle_ai_response",
                "resposta ignorada porque o produto ativo mudou durante a geração",
            )
            return

        if (
            self.title_edit.text() != pending["title"]
            or self.description_edit.toPlainText() != pending["description"]
        ):
            self.action_status_label.setText(
                "A resposta está na conversa do painel. Mantive nos campos o "
                "texto que você editou durante a geração."
            )
            log.aviso(
                "Anuncio",
                "handle_ai_response",
                "resposta não aplicada; os campos foram editados durante a geração",
            )
            return

        if not str(response or "").strip():
            self.action_status_label.setText(
                "A solicitação terminou sem texto de resposta. Os campos foram "
                "mantidos."
            )
            log.aviso(
                "Anuncio",
                "handle_ai_response",
                "resposta vazia; campos mantidos",
            )
            return

        self.action_status_label.setText(
            "Sugestão pronta no painel de IA. Use Copiar na conversa e cole "
            "manualmente nos campos após revisar. Os campos não foram alterados."
        )
        log.info(
            "Anuncio",
            "handle_ai_response",
            (
                f"resposta mantida na conversa para cópia manual; "
                f"produto={product_key}; caracteres={len(str(response))}"
            ),
        )

    def _open_product_folder(self) -> None:
        product = self._current_product
        if not product:
            return
        marketplace_folder = product["marketplace_folder"]
        folder = product["folder"]
        target = (
            marketplace_folder
            if marketplace_folder and marketplace_folder.is_dir()
            else folder
        )
        log.info(
            "Anuncio",
            "_open_product_folder",
            f"usuário solicitou abrir pasta; produto={product['key'] or '-'}",
        )
        if not target or not target.is_dir():
            self.action_status_label.setText(
                f"A pasta do produto não está disponível: {target or '(não informada)'}"
            )
            log.aviso(
                "Anuncio",
                "_open_product_folder",
                "pasta do produto ausente ou inacessível",
            )
            return
        opened = QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(target.resolve()))
        )
        if not opened:
            self.action_status_label.setText(
                f"Não foi possível abrir a pasta: {target}"
            )
            log.erro(
                "Anuncio",
                "_open_product_folder",
                f"falha ao abrir a pasta do produto: {target}",
            )
