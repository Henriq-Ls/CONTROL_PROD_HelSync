"""Controlador da preparação de conteúdo manual para redes sociais."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QSize, Qt, Signal, QUrl
from PySide6.QtGui import QImageReader, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from _APP_.PySide6_core import (
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    carregar_itens_anuncio_marketplace,
)
from _APP_.product_lifecycle import (
    contar_produtos_pendentes,
    listar_produtos_permanentes,
)
from _LOGS_ import log


MEDIA_EXTENSIONS = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS

PLATFORM_CONFIGS: dict[str, dict[str, str]] = {
    "pinterest": {
        "name": "Pinterest",
        "media_guidance": "Mídia permitida neste card: imagem ou vídeo.",
        "guidance": (
            "O Pin usa Título e Descrição; Link é opcional e o usuário escolhe "
            "o board. O título aceita até 100 caracteres e a descrição até "
            "800. Inclua termos de busca naturalmente na descrição. Sugira "
            "até 5 tópicos relacionados para o campo de tópicos do Pinterest; "
            "eles não são hashtags. Não crie uma lista separada de palavras-"
            "chave ou hashtags, nem invente um link."
        ),
        "output_format": (
            "Título (até 100 caracteres):\n"
            "Descrição para colar (até 800 caracteres):\n"
            "Tópicos relacionados para pesquisar/selecionar no Pinterest "
            "(até 5, sem #):"
        ),
    },
    "instagram": {
        "name": "Instagram",
        "media_guidance": "Mídia permitida neste card: imagem ou vídeo.",
        "guidance": (
            "O campo principal é a legenda, não um título nem uma lista "
            "separada de palavras-chave. Use termos de busca naturalmente na "
            "legenda e inclua no máximo 5 hashtags relevantes no final dela."
        ),
        "output_format": (
            "Legenda pronta para colar (com até 5 hashtags relevantes "
            "no final):"
        ),
    },
    "facebook": {
        "name": "Facebook",
        "media_guidance": "Mídia permitida neste card: imagem ou vídeo.",
        "guidance": (
            "Para uma publicação comum, use um único texto de publicação; "
            "não crie título nem lista separada de palavras-chave. Hashtags "
            "são opcionais e devem aparecer no mesmo texto somente se forem "
            "realmente úteis para este produto."
        ),
        "output_format": (
            "Texto da publicação (hashtags opcionais no próprio texto):"
        ),
    },
    "tiktok": {
        "name": "TikTok",
        "media_guidance": "Mídia permitida neste card: imagem ou vídeo.",
        "guidance": (
            "O editor permite adicionar Descrição e Hashtags. Não crie título "
            "nem lista separada de palavras-chave. Faça uma descrição curta e "
            "natural e sugira hashtags diretamente relacionadas ao produto, "
            "sem tendências inventadas."
        ),
        "output_format": (
            "Descrição para colar:\n"
            "Hashtags para adicionar no passo próprio do TikTok "
            "(somente as relevantes):"
        ),
    },
    "youtube_shorts": {
        "name": "YouTube Shorts",
        "media_guidance": "Mídia permitida neste card: vídeo.",
        "guidance": (
            "O envio usa Título (até 100 caracteres) e Descrição (até 5.000). "
            "Hashtags entram no Título ou na Descrição; sugira no máximo 3 "
            "relevantes no fim da Descrição. Tags do YouTube Studio são outro "
            "campo, opcional e de efeito pequeno: só sugira variantes de "
            "grafia realmente úteis; caso contrário, diga que não são "
            "necessárias. Não crie uma lista genérica de palavras-chave."
        ),
        "output_format": (
            "Título (até 100 caracteres):\n"
            "Descrição para colar (até 5.000 caracteres, com até 3 hashtags "
            "relevantes no final):\n"
            "Tags opcionais do YouTube Studio (somente variantes de grafia "
            "úteis; se não houver, escreva “Não necessárias”):"
        ),
    },
}


class SocialNetworkCard(QGroupBox):
    """Um card independente de texto e mídia para uma rede."""

    generate_requested = Signal(str)
    content_changed = Signal(str, str)
    media_changed = Signal(str, str)

    def __init__(
        self,
        platform_id: str,
        config: dict[str, str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(config["name"], parent)
        self.platform_id = platform_id
        self.config = config
        self._product_folder: Path | None = None
        self._selected_media: Path | None = None
        self._has_product = False
        self._generation_busy = False
        self._build_ui()

    @property
    def selected_media(self) -> Path | None:
        return self._selected_media

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(7)

        guidance = QLabel(self.config["guidance"])
        guidance.setWordWrap(True)
        layout.addWidget(guidance)
        media_guidance = QLabel(self.config["media_guidance"])
        media_guidance.setWordWrap(True)
        layout.addWidget(media_guidance)

        media_row = QHBoxLayout()
        self.media_preview_stack = QStackedWidget()
        self.preview = QLabel("Nenhuma mídia escolhida")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setFixedSize(QSize(176, 108))
        self.preview.setStyleSheet("border: 1px solid #536172;")
        self.media_preview_stack.addWidget(self.preview)

        self.video_preview = QVideoWidget()
        self.video_preview.setFixedSize(QSize(176, 108))
        self.video_preview.setToolTip(
            "Prévia do vídeo dentro do card Sociais."
        )
        self.media_preview_stack.addWidget(self.video_preview)
        media_row.addWidget(
            self.media_preview_stack,
            0,
            Qt.AlignmentFlag.AlignTop,
        )

        self.video_preview_player = QMediaPlayer(self)
        self.video_preview_audio = QAudioOutput(self)
        self.video_preview_audio.setVolume(0.35)
        self.video_preview_player.setAudioOutput(self.video_preview_audio)
        self.video_preview_player.setVideoOutput(self.video_preview)
        self.video_preview_player.playbackStateChanged.connect(
            self._video_preview_state_changed
        )
        self.video_preview_player.errorOccurred.connect(
            self._video_preview_error
        )

        media_controls = QVBoxLayout()
        self.media_label = QLabel("Selecione uma imagem ou um vídeo.")
        self.media_label.setWordWrap(True)
        self.media_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        media_controls.addWidget(self.media_label)
        self.media_preview_status = QLabel()
        self.media_preview_status.setWordWrap(True)
        self.media_preview_status.hide()
        media_controls.addWidget(self.media_preview_status)

        media_buttons = QHBoxLayout()
        self.choose_media_button = QPushButton("Escolher mídia")
        self.choose_media_button.setToolTip(
            "Abre o seletor de arquivos na pasta do produto. "
            "O arquivo não é enviado nem alterado."
        )
        self.choose_media_button.clicked.connect(self._choose_media)
        media_buttons.addWidget(self.choose_media_button)

        self.play_video_button = QPushButton("Reproduzir")
        self.play_video_button.setToolTip(
            "Reproduz ou pausa o vídeo dentro desta prévia."
        )
        self.play_video_button.clicked.connect(self._toggle_video_preview)
        self.play_video_button.setEnabled(False)
        self.play_video_button.hide()
        media_buttons.addWidget(self.play_video_button)

        self.clear_media_button = QPushButton("Limpar")
        self.clear_media_button.clicked.connect(self._clear_media)
        media_buttons.addWidget(self.clear_media_button)
        media_buttons.addStretch(1)
        media_controls.addLayout(media_buttons)
        media_row.addLayout(media_controls, 1)
        layout.addLayout(media_row)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText(
            "O texto gerado para esta rede aparecerá aqui. "
            "Você pode revisar e editar antes de copiar."
        )
        self.text_edit.setMinimumHeight(126)
        self.text_edit.textChanged.connect(self._emit_content_changed)
        layout.addWidget(self.text_edit)

        actions = QHBoxLayout()
        self.generate_button = QPushButton("Gerar texto com IA")
        self.generate_button.setToolTip(
            "Pede à IA do projeto um texto específico para esta rede. "
            "Nenhuma imagem ou vídeo é enviado à IA."
        )
        self.generate_button.clicked.connect(
            lambda: self.generate_requested.emit(self.platform_id)
        )
        actions.addWidget(self.generate_button)

        self.copy_button = QPushButton("Copiar bloco")
        self.copy_button.setToolTip(
            "Copia o texto revisado para colar manualmente na rede social."
        )
        self.copy_button.clicked.connect(self._copy_text)
        actions.addWidget(self.copy_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self._refresh_controls()

    def _emit_content_changed(self) -> None:
        self.copy_button.setEnabled(bool(self.text_edit.toPlainText().strip()))
        self.content_changed.emit(
            self.platform_id,
            self.text_edit.toPlainText(),
        )

    def _copy_text(self) -> None:
        text = self.text_edit.toPlainText().strip()
        if not text:
            return
        QApplication.clipboard().setText(text)
        self.status_label.setText("Bloco copiado. Cole-o manualmente na rede.")

    def _choose_media(self) -> None:
        folder = self._product_folder
        if not self._has_product or folder is None or not folder.is_dir():
            QMessageBox.information(
                self,
                "Pasta do produto indisponível",
                "Este cadastro não tem uma pasta válida para procurar mídias.",
            )
            return

        allowed_extensions = self._allowed_media_extensions()
        patterns = " ".join(
            f"*{extension}" for extension in allowed_extensions
        )
        selected, _ = QFileDialog.getOpenFileName(
            self,
            f"Escolher mídia para {self.config['name']}",
            str(folder),
            f"Imagens e vídeos ({patterns});;Todos os arquivos (*)",
        )
        if not selected:
            return

        media_path = Path(selected)
        if media_path.suffix.lower() not in allowed_extensions:
            QMessageBox.warning(
                self,
                "Formato não reconhecido",
                (
                    "Escolha um vídeo em um formato reconhecido pelo Cadastro."
                    if self.platform_id == "youtube_shorts"
                    else "Escolha uma imagem ou um vídeo em um formato "
                    "reconhecido pelo Cadastro."
                ),
            )
            return

        try:
            media_path.resolve().relative_to(folder.resolve())
        except (OSError, ValueError):
            QMessageBox.warning(
                self,
                "Arquivo fora da pasta do produto",
                "Escolha uma mídia dentro da pasta deste produto.",
            )
            return

        self.set_media(media_path)
        self.media_changed.emit(self.platform_id, str(media_path))

    def _allowed_media_extensions(self) -> tuple[str, ...]:
        if self.platform_id == "youtube_shorts":
            return VIDEO_EXTENSIONS
        return MEDIA_EXTENSIONS

    def set_media(self, path: str | Path | None) -> None:
        media_path = Path(path) if path else None
        if media_path is not None and not media_path.is_file():
            media_path = None
        self._selected_media = media_path
        self._render_media()
        self.clear_media_button.setEnabled(media_path is not None)

    def _render_media(self) -> None:
        path = self._selected_media
        self.video_preview_player.stop()
        self.video_preview_player.setSource(QUrl())
        self.play_video_button.setText("Reproduzir")
        self.play_video_button.setEnabled(False)
        self.play_video_button.hide()
        self.media_preview_status.clear()
        self.media_preview_status.hide()

        if path is None:
            self.media_preview_stack.setCurrentWidget(self.preview)
            self.preview.setPixmap(QPixmap())
            self.preview.setText("Nenhuma mídia escolhida")
            self.media_label.setText("Selecione uma imagem ou um vídeo.")
            self.media_label.setToolTip("")
            return

        self.media_label.setText(f"{path.name} ({path.suffix.lower()})")
        self.media_label.setToolTip(str(path))
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            self.preview.setPixmap(QPixmap())
            self.preview.setText("")
            self.media_preview_stack.setCurrentWidget(self.video_preview)
            self.video_preview_player.setSource(
                QUrl.fromLocalFile(str(path.resolve()))
            )
            self.media_preview_status.setText(
                "Prévia pronta. Use Reproduzir para assistir aqui."
            )
            self.media_preview_status.show()
            self.play_video_button.setEnabled(True)
            self.play_video_button.show()
            return

        self.media_preview_stack.setCurrentWidget(self.preview)
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        original_size = reader.size()
        if original_size.isValid():
            reader.setScaledSize(
                original_size.scaled(
                    self.preview.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                )
            )
        image = reader.read()
        if image.isNull():
            self.preview.setPixmap(QPixmap())
            self.preview.setText("Prévia indisponível")
            return
        pixmap = QPixmap.fromImage(image)
        self.preview.setText("")
        self.preview.setPixmap(
            pixmap.scaled(
                self.preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _video_preview_state_changed(
        self,
        state: QMediaPlayer.PlaybackState,
    ) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_video_button.setText("Pausar")
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.play_video_button.setText("Continuar")
        else:
            self.play_video_button.setText("Reproduzir")

    def _video_preview_error(
        self,
        _error: QMediaPlayer.Error,
        _error_text: str,
    ) -> None:
        if (
            self._selected_media is None
            or self._selected_media.suffix.lower() not in VIDEO_EXTENSIONS
        ):
            return
        self.media_preview_status.setText(
            "Não foi possível reproduzir este vídeo nesta prévia."
        )
        self.play_video_button.setText("Reproduzir")

    def _toggle_video_preview(self) -> None:
        path = self._selected_media
        if path is None or path.suffix.lower() not in VIDEO_EXTENSIONS:
            return
        if (
            self.video_preview_player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
        ):
            self.video_preview_player.pause()
            return
        if (
            self.video_preview_player.duration() > 0
            and self.video_preview_player.position()
            >= self.video_preview_player.duration()
        ):
            self.video_preview_player.setPosition(0)
        self.video_preview_player.play()

    def _clear_media(self) -> None:
        self.set_media(None)
        self.media_changed.emit(self.platform_id, "")
        self.status_label.setText("Mídia removida deste rascunho.")

    def set_product_folder(self, folder: Path | None) -> None:
        self._product_folder = folder
        self._has_product = folder is not None
        self._refresh_controls()

    def set_product_available(self, available: bool) -> None:
        self._has_product = available
        self._refresh_controls()

    def set_generation_busy(self, busy: bool) -> None:
        self._generation_busy = busy
        self._refresh_controls()

    def set_generation_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_content(self, text: str) -> None:
        self.text_edit.blockSignals(True)
        self.text_edit.setPlainText(text)
        self.text_edit.blockSignals(False)
        self.copy_button.setEnabled(bool(text.strip()))

    def _refresh_controls(self) -> None:
        self.choose_media_button.setEnabled(
            self._has_product and self._product_folder is not None
        )
        self.generate_button.setEnabled(
            self._has_product and not self._generation_busy
        )


class SociaisController(QWidget):
    """Seleciona qualquer produto cadastrado e prepara blocos copiáveis."""

    ai_context_changed = Signal(dict)
    prompt_requested = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows_by_name: dict[str, tuple] = {}
        self._current_row: tuple | None = None
        self._active_product_name = ""
        self._drafts_by_product: dict[str, dict[str, dict[str, str]]] = {}
        self._loading_product = False
        self._pending_request: tuple[str, str] | None = None
        self._build_ui()
        self.refresh_products()

    def _build_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        self.page_scroll = QScrollArea()
        self.page_scroll.setWidgetResizable(True)
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(9)
        self.page_scroll.setWidget(page)
        outer_layout.addWidget(self.page_scroll)

        header = QHBoxLayout()
        header.addWidget(QLabel("Produto:"))
        self.product_choice = QComboBox()
        self.product_choice.setMinimumWidth(280)
        self.product_choice.currentIndexChanged.connect(
            self._on_product_changed
        )
        header.addWidget(self.product_choice, 1)

        self.refresh_button = QPushButton("Atualizar produtos")
        self.refresh_button.setToolTip(
            "Relê os produtos cadastrados no SQLite sem alterar o banco."
        )
        self.refresh_button.clicked.connect(self.refresh_products)
        header.addWidget(self.refresh_button)
        root.addLayout(header)

        self.product_status = QLabel(
            "Escolha um produto para preparar o conteúdo social."
        )
        self.product_status.setWordWrap(True)
        root.addWidget(self.product_status)

        self.manual_notice = QLabel(
            "A IA usa os fatos do Cadastro e, quando houver, o título e a "
            "descrição mais recentes salvos em Anúncio. Depois de salvar uma "
            "alteração, gere o texto social novamente. Você revisa e copia "
            "cada bloco; a escolha e o envio da mídia são manuais. "
            "O aplicativo não publica nas redes."
        )
        self.manual_notice.setWordWrap(True)
        root.addWidget(self.manual_notice)

        self.cards: dict[str, SocialNetworkCard] = {}
        for platform_id, config in PLATFORM_CONFIGS.items():
            card = SocialNetworkCard(platform_id, config)
            card.generate_requested.connect(self._generate_for_platform)
            card.content_changed.connect(self._remember_content)
            card.media_changed.connect(self._remember_media)
            self.cards[platform_id] = card
            root.addWidget(card)
        root.addStretch(1)

    def refresh_products(self, *_args: object) -> None:
        preferred = (
            self._active_product_name
            or str(self.product_choice.currentData() or "")
        )
        self._save_current_product_state()
        try:
            rows = list(listar_produtos_permanentes())
        except Exception as exc:
            log.erro("Sociais", "refresh_products", str(exc))
            self._rows_by_name = {}
            self._current_row = None
            self._active_product_name = ""
            self.product_choice.blockSignals(True)
            self.product_choice.clear()
            self.product_choice.blockSignals(False)
            self.product_choice.setEnabled(False)
            self.product_status.setText(
                f"Não foi possível carregar os produtos: {exc}"
            )
            self._load_product_into_cards(None)
            self.ai_context_changed.emit({})
            return

        self._rows_by_name = {
            str(row[0]).strip(): row
            for row in rows
            if row and str(row[0] or "").strip()
        }
        self.product_choice.blockSignals(True)
        self.product_choice.clear()
        for row in rows:
            name = str(row[0] or "").strip()
            if not name:
                continue
            reference = str(row[1] or "").strip() if len(row) > 1 else ""
            label = f"{name} · {reference}" if reference else name
            self.product_choice.addItem(label, name)
        self.product_choice.setEnabled(bool(self._rows_by_name))

        selected_name = preferred if preferred in self._rows_by_name else ""
        if not selected_name and rows:
            selected_name = str(rows[0][0] or "").strip()
        index = self.product_choice.findData(selected_name)
        if index < 0 and self.product_choice.count():
            index = 0
        self.product_choice.setCurrentIndex(index)
        self.product_choice.blockSignals(False)
        self._on_product_changed()

    def _on_product_changed(self, *_args: object) -> None:
        if self._loading_product:
            return
        self._save_current_product_state()
        product_name = str(self.product_choice.currentData() or "").strip()
        self._current_row = self._rows_by_name.get(product_name)
        self._active_product_name = product_name if self._current_row else ""
        self._load_product_into_cards(self._current_row)
        self.ai_context_changed.emit(self.ai_context_snapshot())

    def _load_product_into_cards(self, row: tuple | None) -> None:
        self._loading_product = True
        state = self._drafts_by_product.get(self._active_product_name, {})
        folder = (
            Path(str(row[2])).expanduser()
            if row and len(row) > 2 and str(row[2] or "").strip()
            else None
        )
        for platform_id, card in self.cards.items():
            platform_state = state.get(platform_id, {})
            card.set_product_folder(folder)
            card.set_product_available(row is not None)
            card.set_media(platform_state.get("media") or None)
            card.set_content(platform_state.get("text", ""))
            card.set_generation_status("")
        self._loading_product = False

        if row is None:
            try:
                pendentes = contar_produtos_pendentes()
            except Exception as exc:
                log.aviso(
                    "Sociais",
                    "_load_product_into_cards",
                    f"não foi possível contar produtos pendentes: {exc}",
                )
                pendentes = 0
            if pendentes:
                self.product_status.setText(
                    "Nenhum produto concluído está disponível em Sociais. "
                    f"Há {pendentes} produto(s) pendente(s) em Cadastro. "
                    "Finalize cada produto em Cadastro > Montar anúncio "
                    "para liberá-lo no Marketplace."
                )
            else:
                self.product_status.setText(
                    "Nenhum produto concluído está disponível em Sociais. "
                    "Salve e conclua um produto em Cadastro > Montar anúncio, "
                    "depois clique em Atualizar produtos."
                )
            return

        name = str(row[0] or "")
        reference = str(row[1] or "").strip() if len(row) > 1 else ""
        directory = str(row[2] or "").strip() if len(row) > 2 else ""
        self.product_status.setText(
            f"Produto selecionado: {name}"
            + (f" · Referência: {reference}" if reference else "")
            + f"\nPasta das mídias: {directory or 'não informada'}"
        )
        self.product_status.setToolTip(directory)

    def ai_context_snapshot(self) -> dict[str, Any]:
        row = self._current_row
        if not row:
            return {}
        product_id = str(row[0] or "").strip()
        try:
            saved_announcement = self._load_saved_announcement_texts(product_id)
        except Exception as exc:
            log.erro(
                "Sociais",
                "ai_context_snapshot",
                f"não foi possível carregar o anúncio salvo: {exc}",
            )
            saved_announcement = {"title": "", "description": ""}
        return {
            "produto_id": product_id,
            "memoria_id": f"produto:{product_id}",
            "memoria_tipo": "produto",
            "escopo": "Sociais",
            "nome": product_id,
            "referencia": str(row[1] or ""),
            "diretorio": str(row[2] or ""),
            "descricao": str(row[3] or ""),
            "serventia": str(row[4] or ""),
            "acompanha": str(row[5] or ""),
            "acabamento": str(row[6] or ""),
            "kit": str(row[7] or ""),
            "observacoes": str(row[8] or "") if len(row) > 8 else "",
            "titulo_anuncio_salvo": saved_announcement["title"],
            "descricao_anuncio_salva": saved_announcement["description"],
        }

    @staticmethod
    def _load_saved_announcement_texts(product_name: str) -> dict[str, str]:
        saved = carregar_itens_anuncio_marketplace(product_name)
        return {
            "title": str(saved.get("title") or "").strip(),
            "description": str(saved.get("description") or "").strip(),
        }

    def _remember_content(self, platform_id: str, text: str) -> None:
        if self._loading_product or not self._active_product_name:
            return
        state = self._drafts_by_product.setdefault(
            self._active_product_name,
            {},
        )
        state.setdefault(platform_id, {})["text"] = text

    def _remember_media(self, platform_id: str, path: str) -> None:
        if self._loading_product or not self._active_product_name:
            return
        state = self._drafts_by_product.setdefault(
            self._active_product_name,
            {},
        )
        state.setdefault(platform_id, {})["media"] = path

    def _save_current_product_state(self) -> None:
        if not self._active_product_name or not self.cards:
            return
        state = self._drafts_by_product.setdefault(
            self._active_product_name,
            {},
        )
        for platform_id, card in self.cards.items():
            platform_state = state.setdefault(platform_id, {})
            platform_state["text"] = card.text_edit.toPlainText()
            platform_state["media"] = (
                str(card.selected_media) if card.selected_media else ""
            )

    def _generate_for_platform(self, platform_id: str) -> None:
        if not self._current_row or platform_id not in PLATFORM_CONFIGS:
            return
        if self._pending_request is not None:
            self.cards[platform_id].set_generation_status(
                "Aguarde a geração que já está em andamento."
            )
            return

        product_name = str(self._current_row[0] or "").strip()
        try:
            saved_announcement = self._load_saved_announcement_texts(
                product_name
            )
        except Exception as exc:
            self.cards[platform_id].set_generation_status(
                "Não foi possível carregar o texto salvo em Anúncio. "
                "Confira a conexão com o banco e tente novamente."
            )
            log.erro(
                "Sociais",
                "_generate_for_platform",
                f"falha ao carregar anúncio salvo para {product_name}: {exc}",
            )
            return
        prompt = self._build_prompt(
            platform_id,
            self._current_row,
            saved_announcement,
        )
        self._pending_request = (product_name, platform_id)
        self._set_generation_busy(True)
        self.cards[platform_id].set_generation_status(
            "Enviando o pedido à IA do projeto..."
        )
        self.prompt_requested.emit(platform_id, prompt)

    @staticmethod
    def _build_prompt(
        platform_id: str,
        row: tuple,
        saved_announcement: dict[str, str] | None = None,
    ) -> str:
        config = PLATFORM_CONFIGS[platform_id]
        name = str(row[0] or "").strip()
        saved_announcement = saved_announcement or {}
        saved_title = str(saved_announcement.get("title") or "").strip()
        saved_description = str(
            saved_announcement.get("description") or ""
        ).strip()
        facts = [
            f"Produto: {name}",
            f"Referência: {str(row[1] or '').strip() or 'não informada'}",
            f"Descrição cadastrada: {str(row[3] or '').strip() or 'não informada'}",
            f"Uso: {str(row[4] or '').strip() or 'não informado'}",
            f"O que acompanha: {str(row[5] or '').strip() or 'não informado'}",
            f"Acabamento: {str(row[6] or '').strip() or 'não informado'}",
            f"Configuração de kit: {str(row[7] or '').strip() or 'não informada'}",
            (
                f"Observações: {str(row[8] or '').strip() or 'nenhuma informada'}"
                if len(row) > 8
                else "Observações: nenhuma informada"
            ),
        ]
        return "\n".join(
            (
                f"Crie conteúdo em português do Brasil para {config['name']}.",
                config["guidance"],
                "Use o título e a descrição salvos em Anúncio como referência "
                "da apresentação mais recente, quando estiverem disponíveis. "
                "Os fatos do Cadastro são a fonte factual; em caso de conflito, "
                "priorize o Cadastro.",
                "Não invente materiais, medidas, compatibilidades, benefícios, "
                "certificações, preços ou resultados. A IA não recebeu nem "
                "analisou imagens ou vídeos.",
                "Faça texto natural e específico para esta rede. Não crie "
                "seções ou campos que não estejam no formato solicitado. "
                "Não use JSON, tabelas ou bloco de código. Se algum dado "
                "importante não estiver informado, não o presuma.",
                "Responda usando exatamente este formato, sem acrescentar "
                "introdução ou conclusão:",
                config["output_format"],
                "",
                "TEXTO MAIS RECENTE SALVO EM ANÚNCIO:",
                f"Título: {saved_title or '(não informado)'}",
                f"Descrição: {saved_description or '(não informada)'}",
                "",
                "FATOS DO CADASTRO:",
                *facts,
            )
        )

    def _set_generation_busy(self, busy: bool) -> None:
        for card in self.cards.values():
            card.set_generation_busy(busy)

    def ai_request_rejected(self, platform_id: str, message: str) -> None:
        if self._pending_request and self._pending_request[1] == platform_id:
            self._pending_request = None
            self._set_generation_busy(False)
        card = self.cards.get(platform_id)
        if card:
            card.set_generation_status(message or "A IA não aceitou o pedido.")

    def handle_ai_response(
        self,
        product_id: str,
        platform_id: str,
        response: str,
    ) -> None:
        card = self.cards.get(platform_id)
        if card is None:
            return
        product_id = str(product_id or "").strip()
        state = self._drafts_by_product.setdefault(product_id, {})
        state.setdefault(platform_id, {})["text"] = str(response)
        if product_id == self._active_product_name:
            card.set_content(str(response))
            card.set_generation_status(
                "Texto recebido. Revise e ajuste antes de copiar."
            )
        if self._pending_request == (product_id, platform_id):
            self._pending_request = None
            self._set_generation_busy(False)

    def ai_request_failed(
        self,
        product_id: str,
        platform_id: str,
        _error: str,
    ) -> None:
        normalized_product_id = str(product_id or "").strip()
        if self._pending_request == (normalized_product_id, platform_id):
            self._pending_request = None
            self._set_generation_busy(False)
        card = self.cards.get(platform_id)
        if card and normalized_product_id == self._active_product_name:
            card.set_generation_status(
                "A IA não concluiu a geração. Confira o painel de IA e tente "
                "novamente."
            )
        log.aviso(
            "Sociais",
            "ai_request_failed",
            (
                f"produto={normalized_product_id or '-'}; "
                f"rede={platform_id}; solicitação falhou"
            ),
        )
