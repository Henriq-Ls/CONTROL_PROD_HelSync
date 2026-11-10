"""Controlador da aba Criação do aplicativo desktop PySide6."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import QFile, QUrl, QSize, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QScrollArea,
)

from _APP_.PySide6_core import (
    BackgroundMixin,
    IMAGE_EXTENSIONS,
    PASTA_FUNDO_BRANCO,
    PASTA_FUNDO_CAPA,
    PASTA_MEDIDAS,
    PASTA_SEM_FUNDO,
    PASTA_VIDEO_CONVERTIDO,
    PASTA_VIDEO_LEGADO,
    _partes_nome_producao,
    _ler_ordem_midias_producao,
    _separar_imagens_por_papel,
    apagar_entrada,
    ler_entradas,
    ler_proporcao,
    parse_tipo_kit,
)
from _APP_.producao.pipeline import (
    executar_producao,
    preparar_imagens_marketplace,
)
from _APP_.Cadastro.Resultados import build_results_page
from _APPDATA_ import appdata
from _FERRAMENTAS_.ia_prompt_catalogo import carregar_prompts_imagem
from _ULTILIDADES_.loading_overlay import LoadingOverlay

PASTA_PRE_CAPAS = "pre_capas"
PASTA_CAPAS = "f_capas"
PASTA_PRE_MARKETPLACE = "F_pre_marketplace"
PASTA_MARKETPLACE = "G_marketplace"
CAPA_SLOTS = (
    ("capa_principal", "Capa principal", "capa"),
    ("produto_em_uso", "Produto em uso", "uso"),
    ("detalhes", "Detalhes do produto", "detalhe"),
)


def _path_contains(parent: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(parent)
    except ValueError:
        return False
    return True


class CreationController(QWidget, BackgroundMixin):
    """Controla a criação do produto e fornece ações para Resultados."""

    ai_context_changed = Signal(dict)
    results_requested = Signal()

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        BackgroundMixin.__init__(self)
        self.current_row: tuple | None = None
        self._production_overlay: LoadingOverlay | None = None
        self._cover_sources: list[tuple[str, Path]] = []
        self._cover_source_choices: dict[str, QComboBox] = {}
        self._cover_source_previews: dict[str, QLabel] = {}
        self._cover_result_previews: dict[str, QLabel] = {}
        self._cover_slot_status: dict[str, QLabel] = {}
        self._cover_prepare_buttons: dict[str, QPushButton] = {}
        self._cover_import_buttons: dict[str, QPushButton] = {}
        self._configured_measure_background: str | None = None
        self._marketplace_processing = False
        self._marketplace_preview_cache: OrderedDict[
            tuple[object, ...], QPixmap
        ] = OrderedDict()
        self._marketplace_preview_dialog_versions: dict[int, int] = {}
        self.build_ui()
        self.refresh()

    def build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        controls = QGroupBox("Cadastro atual · resumo e mídias")
        controls.setMaximumHeight(142)
        control_layout = QVBoxLayout(controls)
        control_layout.setContentsMargins(8, 5, 8, 5)
        control_layout.setSpacing(3)
        header = QHBoxLayout()
        header.setSpacing(6)
        self.product_label = QLabel("Nenhum cadastro encontrado.")
        self.path_label = QLabel("-")
        self.path_label.setWordWrap(False)
        self.config_label = QLabel("-")
        self.product_label.setToolTip("Nome do produto carregado do último cadastro.")
        self.path_label.setToolTip("Pasta completa do produto. Use Abrir pasta para acessá-la.")
        self.config_label.setToolTip(
            "Configuração de tipo, variações e kits salva pelo Cadastro."
        )
        self.open_folder_button = QPushButton("Abrir pasta")
        self.open_folder_button.setToolTip(
            "Abre a pasta do produto no explorador de arquivos do sistema."
        )
        self.open_folder_button.clicked.connect(self.open_product_folder)
        self.delete_button = QPushButton("Apagar A_ENTRADA")
        self.delete_button.setToolTip(
            "Apaga o cadastro atual da tabela A_ENTRADA. Os arquivos da pasta não são apagados."
        )
        self.delete_button.clicked.connect(self.delete_current)
        self.delete_folder_button = QPushButton("Apagar pasta + cadastro")
        self.delete_folder_button.setToolTip(
            "Envia a pasta inteira para a Lixeira e apaga o cadastro A_ENTRADA. "
            "A exclusão depende do suporte à Lixeira do sistema."
        )
        self.delete_folder_button.clicked.connect(
            self.delete_folder_and_entry
        )
        header.addWidget(QLabel("Produto:"))
        header.addWidget(self.product_label, 2)
        header.addWidget(QLabel("Pasta:"))
        header.addWidget(self.path_label, 4)
        header.addWidget(QLabel("Config.:"))
        header.addWidget(self.config_label, 2)
        header.addWidget(self.open_folder_button)
        header.addWidget(self.delete_button)
        header.addWidget(self.delete_folder_button)
        control_layout.addLayout(header)

        media_info_row = QHBoxLayout()
        media_info_row.setSpacing(6)
        self.media_status = QLabel("Nenhuma mídia carregada.")
        self.media_status.setWordWrap(True)
        self.media_status.setMaximumWidth(150)
        self.media_status.setToolTip(
            "Quantidade de imagens, vídeos e mídias ausentes no manifesto."
        )
        media_info_row.addWidget(self.media_status)
        self.media_scroll = QScrollArea()
        self.media_scroll.setWidgetResizable(True)
        self.media_scroll.setFixedHeight(74)
        self.media_scroll.setToolTip(
            "A ordem exibida aqui é a mesma usada pela Produção."
        )
        self.media_container = QWidget()
        self.media_layout = QHBoxLayout(self.media_container)
        self.media_layout.setContentsMargins(4, 4, 4, 4)
        self.media_layout.setSpacing(8)
        self.media_scroll.setWidget(self.media_container)
        media_info_row.addWidget(self.media_scroll, 1)
        control_layout.addLayout(media_info_row)
        root.addWidget(controls)

        resources = QLabel(
            "Clique numa imagem para escolher logo, endereço, @ e texto no "
            "pop-up. Nada é aplicado automaticamente."
        )
        resources.setWordWrap(True)
        self.logo_choice = QComboBox()
        self.capa_choice = QComboBox()
        self.logo_preview = QLabel()
        self.capa_preview = QLabel()
        for preview in (self.logo_preview, self.capa_preview):
            preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            preview.setFixedSize(88, 50)
            preview.setWordWrap(True)
        self.logo_choice.setToolTip(
            "Logo usada pela Criação normal. Para F→G, escolha a logo no "
            "pop-up de cada imagem; ela não é aplicada automaticamente."
        )
        self.capa_choice.setToolTip(
            "Fundo aplicado às imagens de E_fundo_capa com a sombra configurada."
        )
        self.logo_choice.currentIndexChanged.connect(self._visual_selection_changed)
        self.capa_choice.currentIndexChanged.connect(
            self._visual_selection_changed
        )
        options = QGroupBox("Configuração da criação")
        options.setMaximumHeight(238)
        options.setToolTip(
            "Ajustes do processamento, incluindo o fundo aplicado na etapa E, "
            "e seleção das formas comerciais elegíveis pelo Cadastro."
        )
        options_layout = QGridLayout(options)
        options_layout.setContentsMargins(8, 5, 8, 5)
        options_layout.setVerticalSpacing(3)
        self.shadow = QComboBox()
        self.shadow.addItems(["2.0", "0.5", "1.5", "2.5", "40"])
        self.shadow.setToolTip(
            "Altura relativa da sombra projetada atrás do produto. Valores maiores aproximam a sombra da base."
        )
        self.music = QComboBox()
        self.music.addItems(["0", "0.15", "0.25", "0.55", "0.80"])
        self.music.setToolTip(
            "Volume da música usada no vídeo convertido. Zero desativa o volume."
        )
        self.music_track_choice = QComboBox()
        self.music_track_choice.setToolTip(
            "Faixa cadastrada em Configurações. Selecione “Sem música” "
            "para não adicionar trilha ao vídeo."
        )
        self.music_preview_button = QPushButton("Ouvir música")
        self.music_preview_button.setEnabled(False)
        self.music_preview_button.setToolTip(
            "Reproduz a faixa selecionada para você conferir antes da Criação."
        )
        self.music_preview_status = QLabel("Selecione uma faixa cadastrada.")
        self.music_preview_status.setWordWrap(True)
        self.music_preview_status.setMaximumHeight(34)
        self.music_preview_player = QMediaPlayer(self)
        self.music_preview_audio = QAudioOutput(self)
        self.music_preview_audio.setVolume(1.0)
        self.music_preview_player.setAudioOutput(self.music_preview_audio)
        self.music_preview_player.playbackStateChanged.connect(
            self._music_playback_state_changed
        )
        self.music_preview_player.errorOccurred.connect(self._music_preview_error)
        self.music_preview_button.clicked.connect(self.toggle_music_preview)
        self.music_track_choice.currentIndexChanged.connect(
            self._update_music_preview
        )
        self.measure_type = QComboBox()
        self.measure_type.addItems(
            [
                "",
                "alt x larg x esp",
                "alt x larg x comp",
                "alt x diam x esp",
                "alt x diam",
            ]
        )
        self.measure_type.setToolTip(
            "Define como altura, largura, comprimento, diâmetro e espessura serão desenhados."
        )
        self.kit_options = QListWidget()
        self.kit_options.setFixedHeight(58)
        self.kit_options.setToolTip(
            "As opções vêm do tipo/kit salvo no Cadastro. Marque as formas que "
            "quer registrar nesta produção. Hoje essa escolha é gravada em "
            "formas_venda.json; não altera as imagens nem o vídeo."
        )

        options_layout.addWidget(QLabel("Altura da sombra"), 0, 0)
        options_layout.addWidget(self.shadow, 0, 1)
        options_layout.addWidget(QLabel("Volume da música"), 1, 0)
        options_layout.addWidget(self.music, 1, 1)
        options_layout.addWidget(QLabel("Tipo de medidas"), 2, 0)
        options_layout.addWidget(self.measure_type, 2, 1)
        options_layout.addWidget(QLabel("Formas de venda"), 0, 2, 1, 2)
        options_layout.addWidget(self.kit_options, 1, 2, 2, 2)
        options_layout.addWidget(QLabel("Faixa de música"), 3, 0)
        options_layout.addWidget(self.music_track_choice, 3, 1)
        options_layout.addWidget(self.music_preview_button, 3, 2)
        options_layout.addWidget(self.music_preview_status, 3, 3)
        options_layout.addWidget(QLabel("Fundo da capa (E)"), 4, 0)
        options_layout.addWidget(self.capa_choice, 4, 1)
        options_layout.addWidget(self.capa_preview, 4, 2, 1, 2)
        options_layout.addWidget(QLabel("Logo da criação"), 5, 0)
        options_layout.addWidget(self.logo_choice, 5, 1)
        options_layout.addWidget(self.logo_preview, 5, 2, 1, 2)
        options_layout.setColumnStretch(3, 1)

        root.addWidget(options)

        actions = QHBoxLayout()
        actions.setSpacing(6)
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.setToolTip(
            "Recarrega o último cadastro e atualiza mídias e recursos visuais."
        )
        self.refresh_button.clicked.connect(self.refresh)
        self.run_button = QPushButton("Iniciar criação")
        self.run_button.setToolTip(
            "Valida o cadastro e inicia o tratamento das imagens e vídeos em segundo plano."
        )
        self.run_button.clicked.connect(self.run_production)
        actions.addWidget(self.refresh_button)
        actions.addWidget(self.run_button)
        actions.addStretch()
        root.addLayout(actions)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFormat("Criando...")
        self.progress.setToolTip("A Criação está sendo executada em segundo plano.")
        self.progress.hide()
        root.addWidget(self.progress)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(130)
        self.log.setToolTip(
            "Terminal com validações, etapas concluídas e erros da criação."
        )
        self.results_page = self._build_results_page(resources)
        root.addWidget(self.log, 1)

    def _new_gallery(self, wrapping: bool = False) -> QListWidget:
        gallery = QListWidget()
        gallery.setFrameShape(QFrame.Shape.NoFrame)
        gallery.setViewMode(QListWidget.ViewMode.IconMode)
        gallery.setFlow(QListWidget.Flow.LeftToRight)
        gallery.setWrapping(wrapping)
        gallery.setMovement(QListWidget.Movement.Static)
        gallery.setResizeMode(QListWidget.ResizeMode.Adjust)
        gallery.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        gallery.setIconSize(QSize(140, 92))
        gallery.setGridSize(QSize(176, 150))
        gallery.setSpacing(3)
        gallery.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        gallery.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        gallery.setToolTip(
            "Miniaturas dos arquivos encontrados na pasta de saída."
        )
        return gallery

    def _new_source_gallery(self) -> QListWidget:
        gallery = QListWidget()
        gallery.setFrameShape(QFrame.Shape.NoFrame)
        gallery.setViewMode(QListWidget.ViewMode.IconMode)
        gallery.setFlow(QListWidget.Flow.LeftToRight)
        gallery.setWrapping(True)
        gallery.setMovement(QListWidget.Movement.Static)
        gallery.setResizeMode(QListWidget.ResizeMode.Adjust)
        gallery.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        gallery.setIconSize(QSize(154, 98))
        gallery.setGridSize(QSize(220, 228))
        gallery.setSpacing(8)
        gallery.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        gallery.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        return gallery

    def _build_cover_stage(self) -> QGroupBox:
        section = QGroupBox("Capas do anúncio · pre_capas → f_capas")
        layout = QVBoxLayout(section)
        layout.addWidget(
            QLabel(
                "Escolha uma imagem de referência para cada função. Prepare o "
                "prompt para uso manual no CapCut e importe o resultado em cada "
                "posição."
            )
        )

        slots_layout = QHBoxLayout()
        for slug, title, variant in CAPA_SLOTS:
            slot = QGroupBox(title)
            slot_layout = QVBoxLayout(slot)
            source_choice = QComboBox()
            source_choice.addItem("Selecione uma imagem de referência", None)
            source_choice.setMinimumContentsLength(10)
            source_choice.setSizeAdjustPolicy(
                QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )
            source_choice.currentIndexChanged.connect(
                lambda _index, key=slug: self._cover_source_changed(key)
            )
            self._cover_source_choices[slug] = source_choice
            slot_layout.addWidget(source_choice)

            previews_layout = QHBoxLayout()
            source_column = QVBoxLayout()
            source_caption = QLabel("Imagem escolhida")
            source_caption.setWordWrap(True)
            source_caption.setFixedWidth(80)
            source_column.addWidget(source_caption)
            source_preview = QLabel("Selecione uma imagem")
            source_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            source_preview.setFixedSize(80, 62)
            self._cover_source_previews[slug] = source_preview
            source_column.addWidget(source_preview)
            previews_layout.addLayout(source_column)

            result_column = QVBoxLayout()
            result_caption = QLabel("Resultado importado")
            result_caption.setWordWrap(True)
            result_caption.setFixedWidth(80)
            result_column.addWidget(result_caption)
            result_preview = QLabel("Ainda não importado")
            result_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            result_preview.setFixedSize(80, 62)
            self._cover_result_previews[slug] = result_preview
            result_column.addWidget(result_preview)
            previews_layout.addLayout(result_column)
            slot_layout.addLayout(previews_layout)

            status = QLabel("Aguardando imagem.")
            status.setWordWrap(True)
            self._cover_slot_status[slug] = status
            slot_layout.addWidget(status)

            prepare_button = QPushButton("Preparar para CapCut")
            prepare_button.setEnabled(False)
            prepare_button.clicked.connect(
                lambda _checked=False, key=slug, role=variant: (
                    self._prepare_cover_slot_for_capcut(key, role)
                )
            )
            self._cover_prepare_buttons[slug] = prepare_button
            slot_layout.addWidget(prepare_button)

            import_button = QPushButton("Importar imagem pronta")
            import_button.setEnabled(False)
            import_button.clicked.connect(
                lambda _checked=False, key=slug: self._import_cover_result(key)
            )
            self._cover_import_buttons[slug] = import_button
            slot_layout.addWidget(import_button)
            slots_layout.addWidget(slot, 1)

        layout.addLayout(slots_layout)
        self.cover_stage_status = QLabel(
            "As imagens importadas ficam em pre_capas até concluir o conjunto."
        )
        self.cover_stage_status.setWordWrap(True)
        layout.addWidget(self.cover_stage_status)

        actions = QHBoxLayout()
        self.finish_covers_button = QPushButton("Concluir trio em f_capas")
        self.finish_covers_button.setEnabled(False)
        self.finish_covers_button.clicked.connect(self._finish_cover_set)
        actions.addWidget(self.finish_covers_button)

        self.open_pre_covers_button = QPushButton("Abrir pre_capas")
        self.open_pre_covers_button.setEnabled(False)
        self.open_pre_covers_button.clicked.connect(
            lambda _checked=False: self._open_cover_folder(PASTA_PRE_CAPAS)
        )
        actions.addWidget(self.open_pre_covers_button)

        self.open_final_covers_button = QPushButton("Abrir f_capas")
        self.open_final_covers_button.setEnabled(False)
        self.open_final_covers_button.clicked.connect(
            lambda _checked=False: self._open_cover_folder(PASTA_CAPAS)
        )
        actions.addWidget(self.open_final_covers_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.legacy_covers_group = QGroupBox(
            "Imagens legadas · _Capas / Pre_Capas (somente leitura)"
        )
        legacy_layout = QVBoxLayout(self.legacy_covers_group)
        self.legacy_covers_status = QLabel("")
        self.legacy_covers_status.setWordWrap(True)
        legacy_layout.addWidget(self.legacy_covers_status)
        self.legacy_covers_gallery = self._new_gallery()
        self.legacy_covers_gallery.setFixedHeight(116)
        legacy_layout.addWidget(self.legacy_covers_gallery)
        self.legacy_covers_group.setVisible(False)
        layout.addWidget(self.legacy_covers_group)
        return section

    def _build_results_page(self, resources: QWidget) -> QWidget:
        return build_results_page(self, resources)

    def refresh(self) -> None:
        self._refresh_visual_resources()
        entradas = ler_entradas()
        self.current_row = entradas[-1] if entradas else None
        self.ai_context_changed.emit(self.ai_context_snapshot())
        if not self.current_row:
            self.product_label.setText("Nenhum cadastro encontrado.")
            self.path_label.setText("-")
            self.config_label.setText("-")
            self.run_button.setEnabled(False)
            self.open_folder_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.delete_folder_button.setEnabled(False)
            self._update_resource_previews()
            self._refresh_media_panel()
            self._configure_sale_options()
            self._refresh_result_gallery()
            return

        self.product_label.setText(str(self.current_row[0]))
        self.path_label.setText(str(self.current_row[2]))
        self.config_label.setText(str(self.current_row[7]))
        self.run_button.setEnabled(True)
        self.open_folder_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self.delete_folder_button.setEnabled(True)
        self._refresh_media_panel()
        self._configure_sale_options()
        self._refresh_result_gallery(Path(str(self.current_row[2])))
        self._update_resource_previews()

    def ai_context_snapshot(self) -> dict:
        linha = self.current_row
        if not linha:
            return {}
        produto_id = str(linha[0]).strip()
        return {
            "produto_id": produto_id,
            "memoria_id": f"produto:{produto_id}",
            "memoria_tipo": "produto",
            "escopo": "Producao",
            "nome": produto_id,
            "referencia": str(linha[1] or ""),
            "proporcao": ler_proporcao(produto_id),
            "diretorio": str(linha[2] or ""),
            "descricao": str(linha[3] or ""),
            "serventia": str(linha[4] or ""),
            "acompanha": str(linha[5] or ""),
            "acabamento": str(linha[6] or ""),
            "kit": str(linha[7] or ""),
            "observacoes": str(linha[8] or ""),
        }

    def _refresh_visual_resources(self) -> None:
        """Carrega do AppData os recursos globais cadastrados pelo usuário."""
        configuracoes = (
            (self.logo_choice, "logo"),
            (self.capa_choice, "fundo_capa"),
        )
        for combo, prefixo in configuracoes:
            anterior = combo.currentData()
            primeira_carga = combo.count() == 0
            arquivos = appdata.listar_midias(prefixo)
            combo.blockSignals(True)
            combo.clear()
            if prefixo == "logo":
                combo.addItem("Sem logo", None)
            else:
                combo.addItem("Sem fundo selecionado (pular geração)", None)
            if arquivos:
                for arquivo in arquivos:
                    combo.addItem(arquivo, arquivo)
                if anterior in arquivos:
                    combo.setCurrentIndex(combo.findData(anterior))
                elif prefixo == "logo" and primeira_carga:
                    combo.setCurrentIndex(1 if prefixo == "logo" else 0)
                combo.setEnabled(True)
            else:
                combo.setEnabled(True)
            combo.blockSignals(False)

        arquivos_medida = appdata.listar_midias("fundo_medida")
        configuracao = appdata.ler_config()
        producao = configuracao.get("producao", {})
        if not isinstance(producao, dict):
            producao = {}
        salvo = producao.get("fundo_medida")
        self._configured_measure_background = (
            salvo
            if salvo in arquivos_medida
            else (arquivos_medida[0] if arquivos_medida else None)
        )

        faixa_anterior = self.music_track_choice.currentData()
        primeira_carga = self.music_track_choice.count() == 0
        faixas = appdata.listar_midias("musica")
        self.music_track_choice.blockSignals(True)
        self.music_track_choice.clear()
        self.music_track_choice.addItem("Sem música", None)
        for faixa in faixas:
            self.music_track_choice.addItem(faixa, faixa)
        if faixa_anterior in faixas:
            self.music_track_choice.setCurrentIndex(
                self.music_track_choice.findData(faixa_anterior)
            )
        elif primeira_carga and faixas:
            self.music_track_choice.setCurrentIndex(1)
        self.music_track_choice.setEnabled(True)
        self.music_track_choice.blockSignals(False)
        self._update_resource_previews()

    def refresh_visual_resources_from_settings(self) -> None:
        anteriores = (
            self._selected_resource(self.logo_choice),
            self._selected_resource(self.capa_choice),
            self._configured_measure_background,
        )
        self._refresh_visual_resources()
        atuais = (
            self._selected_resource(self.logo_choice),
            self._selected_resource(self.capa_choice),
            self._configured_measure_background,
        )
        if anteriores != atuais:
            self._visual_selection_changed()

    def _update_resource_previews(self) -> None:
        logo_nome = self._selected_resource(self.logo_choice)
        logo_path = (
            Path(appdata.pasta_midia_categoria("logo")) / logo_nome
            if logo_nome
            else None
        )
        self._set_resource_preview(
            self.logo_preview,
            logo_path,
            "Sem logo selecionada.",
        )
        fundo_nome = self._selected_resource(self.capa_choice)
        fundo_path = (
            Path(appdata.pasta_midia_categoria("fundo_capa")) / fundo_nome
            if fundo_nome
            else None
        )
        self._set_resource_preview(
            self.capa_preview,
            fundo_path,
            "Selecione o fundo usado em E.",
        )
        self._update_music_preview()

    @staticmethod
    def _set_resource_preview(
        label: QLabel,
        caminho: Path | None,
        texto_vazio: str,
    ) -> None:
        pixmap = QPixmap(str(caminho)) if caminho and caminho.is_file() else None
        if pixmap is None or pixmap.isNull():
            label.setText(texto_vazio)
            label.setPixmap(QPixmap())
            return
        label.setText("")
        label.setPixmap(
            pixmap.scaled(
                label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _visual_selection_changed(self, *_args) -> None:
        self._update_resource_previews()

    def _update_music_preview(self, *_args) -> None:
        nome = self.music_track_choice.currentData()
        caminho = (
            Path(appdata.pasta_midia_categoria("musica")) / str(nome)
            if nome
            else None
        )
        self.music_preview_player.stop()
        if caminho is None or not caminho.is_file():
            self.music_preview_player.setSource(QUrl())
            self.music_preview_button.setEnabled(False)
            self.music_preview_button.setText("Ouvir música")
            self.music_preview_status.setText("Selecione uma faixa cadastrada.")
            return

        self.music_preview_player.setSource(
            QUrl.fromLocalFile(str(caminho.resolve()))
        )
        self.music_preview_button.setEnabled(True)
        self.music_preview_button.setText("Ouvir música")
        self.music_preview_status.setText(caminho.name)

    def toggle_music_preview(self, _checked: bool = False) -> None:
        if not self.music_preview_button.isEnabled():
            return
        if (
            self.music_preview_player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
        ):
            self.music_preview_player.pause()
            return
        self.music_preview_player.play()

    def _music_playback_state_changed(self, state) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.music_preview_button.setText("Pausar")
            self.music_preview_status.setText("Reproduzindo a faixa selecionada.")
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.music_preview_button.setText("Continuar")
            self.music_preview_status.setText("Reprodução pausada.")
        else:
            self.music_preview_button.setText("Ouvir música")

    def _music_preview_error(self, _error, mensagem: str) -> None:
        detalhe = str(mensagem or "").strip()
        self.music_preview_status.setText(
            f"Não foi possível reproduzir a faixa: {detalhe or 'formato não compatível.'}"
        )

    @staticmethod
    def _selected_resource(combo: QComboBox) -> str | None:
        if not combo.isEnabled():
            return None
        value = combo.currentData()
        return str(value) if value else None

    def _selected_cover_source_path(self) -> Path | None:
        combo = self._cover_source_choices.get(CAPA_SLOTS[0][0])
        value = combo.currentData() if combo else None
        path = Path(str(value)) if value else None
        return path if path and path.is_file() else None

    def _show_production_overlay(self) -> None:
        """Mostra o bloqueio visual enquanto a tarefa roda fora da UI."""
        if self._production_overlay is not None:
            return

        parent = self.window()
        self._production_overlay = LoadingOverlay(
            parent if isinstance(parent, QWidget) else self,
            mensagem="Preparando produção...",
        )
        self._production_overlay.show()
        self._production_overlay.raise_()
        QApplication.processEvents()

    def _close_production_overlay(self) -> None:
        """Fecha o overlay sempre na thread principal e libera a janela."""
        overlay = self._production_overlay
        self._production_overlay = None
        if overlay is not None:
            overlay.fechar()
            overlay.deleteLater()

    def _clear_media_panel(self) -> None:
        while self.media_layout.count():
            item = self.media_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _refresh_media_panel(self) -> None:
        """Mostra as imagens na ordem oficial salva pelo Cadastro."""
        self._clear_media_panel()
        if not self.current_row:
            self.media_status.setText("Nenhum produto selecionado.")
            return

        pasta = Path(str(self.current_row[2]))
        manifesto = pasta / ".ordem_midias.json"
        if not manifesto.exists():
            self.media_status.setText(
                "Manifesto de mídias não encontrado. Salve o Cadastro novamente."
            )
            return

        try:
            valores = json.loads(manifesto.read_text(encoding="utf-8"))
            if not isinstance(valores, list):
                raise ValueError("o manifesto não contém uma lista")
            arquivos = {
                caminho.name.casefold(): caminho
                for caminho in pasta.iterdir()
                if caminho.is_file()
            }
        except (OSError, TypeError, ValueError) as exc:
            self.media_status.setText(f"Não foi possível carregar as mídias: {exc}")
            return

        imagens: list[Path] = []
        videos = 0
        ausentes = 0
        extensoes_imagem = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
        extensoes_video = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
        for valor in valores:
            nome = Path(str(valor)).name
            caminho = arquivos.get(nome.casefold())
            if caminho is None:
                ausentes += 1
                continue
            if caminho.suffix.lower() in extensoes_imagem:
                imagens.append(caminho)
            elif caminho.suffix.lower() in extensoes_video:
                videos += 1

        for indice, caminho in enumerate(imagens):
            card = QWidget()
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(0, 0, 0, 0)
            preview = QLabel()
            preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            preview.setFixedSize(72, 42)
            pixmap = QPixmap(str(caminho))
            if pixmap.isNull():
                preview.setText("Prévia\nindisponível")
            else:
                preview.setPixmap(
                    pixmap.scaled(
                        preview.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            preview.setToolTip(str(caminho))
            name_label = QLabel(f"{indice + 1}. {caminho.name}")
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_label.setWordWrap(False)
            name_label.setFixedWidth(82)
            name_label.setMaximumHeight(18)
            name_label.setToolTip(str(caminho))
            card_layout.addWidget(preview)
            card_layout.addWidget(name_label)
            self.media_layout.addWidget(card)

        self.media_layout.addStretch()
        status = f"{len(imagens)} imagem(ns) na ordem do Cadastro"
        if videos:
            status += f" • {videos} vídeo(s)"
        if ausentes:
            status += f" • {ausentes} mídia(s) ausente(s)"
        self.media_status.setText(status)

    @staticmethod
    def _images_in(folder: Path) -> list[Path]:
        if not folder.is_dir():
            return []
        return sorted(
            (
                path
                for path in folder.iterdir()
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
            ),
            key=lambda path: path.name.casefold(),
        )

    def _fill_gallery(
        self,
        gallery: QListWidget,
        paths: list[Path],
        empty_message: str,
    ) -> None:
        previous_block_state = gallery.blockSignals(True)
        try:
            gallery.clear()
            if not paths:
                empty_item = QListWidgetItem(empty_message)
                empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
                gallery.addItem(empty_item)
                return

            for path in paths:
                item = QListWidgetItem(QIcon(str(path)), path.name)
                item.setData(Qt.ItemDataRole.UserRole, str(path))
                item.setToolTip(str(path))
                item.setSizeHint(QSize(176, 150))
                gallery.addItem(item)
        finally:
            gallery.blockSignals(previous_block_state)

    def _fill_pre_marketplace_gallery(self, paths: list[Path]) -> None:
        previous_block_state = self.pre_marketplace_gallery.blockSignals(True)
        try:
            self.pre_marketplace_gallery.clear()
            if not paths:
                empty = QListWidgetItem(
                    "Sem imagens em F. Adicione arquivos ou use as ações acima."
                )
                empty.setFlags(Qt.ItemFlag.NoItemFlags)
                self.pre_marketplace_gallery.addItem(empty)
                self._pre_marketplace_selection_changed()
                return
            for path in paths:
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, str(path))
                item.setToolTip(str(path))
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                item.setSizeHint(QSize(176, 180))
                self.pre_marketplace_gallery.addItem(item)
                card = QWidget(self.pre_marketplace_gallery)
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(2, 2, 2, 2)
                card_layout.setSpacing(2)

                selection = QCheckBox("Selecionar")
                selection.setToolTip(
                    "Marque para copiar a versão final para G usando os "
                    "ajustes salvos especificamente para esta imagem."
                )
                selection.toggled.connect(
                    self._pre_marketplace_selection_changed
                )
                card_layout.addWidget(selection)

                preview_button = QPushButton()
                preview_button.setToolTip(
                    "Clique para abrir a prévia e configurar logo, endereço, "
                    "@ e texto. O original em F não é alterado."
                )
                preview_button.setAccessibleName(
                    f"Visualizar ajustes de {path.name}"
                )
                preview_button.setFixedSize(164, 108)
                preview_button.setIcon(QIcon(str(path)))
                preview_button.setIconSize(QSize(156, 100))
                preview_button.clicked.connect(
                    lambda _checked=False, image_path=path: (
                        self.preview_premarketplace_image(image_path)
                    )
                )
                card_layout.addWidget(
                    preview_button,
                    0,
                    Qt.AlignmentFlag.AlignHCenter,
                )

                name = QLabel(path.name)
                name.setWordWrap(True)
                name.setMaximumHeight(34)
                name.setToolTip(str(path))
                card_layout.addWidget(name)
                self.pre_marketplace_gallery.setItemWidget(item, card)
        finally:
            self.pre_marketplace_gallery.blockSignals(previous_block_state)
        self._pre_marketplace_selection_changed()

    def _fill_sample_gallery(
        self,
        paths: list[Path],
    ) -> None:
        self._fill_source_gallery(
            self.sample_gallery,
            paths,
            "Nenhuma imagem sem fundo encontrada.",
        )

    def _fill_source_gallery(
        self,
        gallery: QListWidget,
        paths: list[Path],
        empty_message: str,
        with_actions: bool = True,
        with_prompt_actions: bool = True,
    ) -> None:
        previous_block_state = gallery.blockSignals(True)
        try:
            gallery.clear()
            if not paths:
                empty = QListWidgetItem(empty_message)
                empty.setFlags(Qt.ItemFlag.NoItemFlags)
                gallery.addItem(empty)
                return

            for path in paths:
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, str(path))
                item.setToolTip(str(path))
                altura_cartao = (
                    220
                    if with_actions and with_prompt_actions
                    else 200
                    if with_actions
                    else 180
                )
                item.setSizeHint(QSize(210, altura_cartao))
                gallery.addItem(item)

                card = QWidget(gallery)
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(5, 4, 5, 4)
                card_layout.setSpacing(5)

                preview = QLabel()
                preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
                preview.setFixedSize(180, 108)
                pixmap = QPixmap(str(path))
                if pixmap.isNull():
                    preview.setText("Prévia indisponível")
                else:
                    preview.setPixmap(
                        pixmap.scaled(
                            preview.size(),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                preview.setToolTip(str(path))
                card_layout.addWidget(preview, 0, Qt.AlignmentFlag.AlignHCenter)

                name = QLabel(path.name)
                name.setWordWrap(True)
                name.setMaximumHeight(38)
                name.setToolTip(str(path))
                card_layout.addWidget(name)

                if with_actions:
                    actions = QHBoxLayout()
                    actions.setContentsMargins(0, 2, 0, 0)
                    actions.setSpacing(4)

                    add_button = QPushButton("Add")
                    add_button.setToolTip(
                        "Adiciona uma cópia desta imagem à pasta F."
                    )
                    add_button.setAccessibleName("Adicionar imagem à pasta F")
                    add_button.clicked.connect(
                        lambda _checked=False, source=path: (
                            self._add_image_to_premarketplace(source)
                        )
                    )
                    actions.addWidget(add_button)

                    if with_prompt_actions:
                        for label, tooltip, role in (
                            (
                                "Capa",
                                "Preparar o prompt de capa principal para esta imagem.",
                                "capa",
                            ),
                            (
                                "Uso",
                                "Preparar o prompt de produto em uso para esta imagem.",
                                "uso",
                            ),
                            (
                                "Detalhe",
                                "Preparar o prompt de detalhes do produto para esta imagem.",
                                "detalhe",
                            ),
                        ):
                            prompt_button = QPushButton(label)
                            prompt_button.setToolTip(tooltip)
                            prompt_button.setAccessibleName(tooltip)
                            prompt_button.clicked.connect(
                                lambda _checked=False, source=path, variant=role: (
                                    self._prepare_image_prompt(source, variant)
                                )
                            )
                            actions.addWidget(prompt_button)

                    for button_index in range(actions.count()):
                        button = actions.itemAt(button_index).widget()
                        if button is not None:
                            button.setFixedWidth(46)
                            button.setMaximumHeight(25)
                            button.setStyleSheet(
                                "QPushButton { padding: 1px 2px; font-size: 9px; }"
                            )
                    card_layout.addLayout(actions)
                gallery.setItemWidget(item, card)
        finally:
            gallery.blockSignals(previous_block_state)

    @staticmethod
    def _cover_role_files(folder: Path, slug: str) -> list[Path]:
        if not folder.is_dir():
            return []
        return sorted(
            (
                path
                for path in folder.iterdir()
                if path.is_file()
                and path.suffix.lower() in IMAGE_EXTENSIONS
                and path.stem.casefold() == slug.casefold()
            ),
            key=lambda path: path.name.casefold(),
        )

    @classmethod
    def _cover_image_for_role(cls, folder: Path, slug: str) -> Path | None:
        matches = cls._cover_role_files(folder, slug)
        return matches[0] if matches else None

    @staticmethod
    def _copy_image_atomically(source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix=f".{destination.stem}.",
                suffix=".tmp",
                dir=destination.parent,
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
            shutil.copy2(source, temporary)
            temporary.replace(destination)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    @staticmethod
    def _available_copy_path(folder: Path, source: Path) -> Path:
        destination = folder / source.name
        index = 2
        while destination.exists():
            destination = folder / f"{source.stem}_{index}{source.suffix}"
            index += 1
        return destination

    def _copy_into_premarketplace(self, source: Path) -> Path:
        if not source.is_file() or source.suffix.lower() not in IMAGE_EXTENSIONS:
            raise FileNotFoundError(f"Imagem indisponível: {source}")
        folder = self._cover_product_folder()
        if folder is None:
            raise RuntimeError("Selecione um produto antes de adicionar imagens.")
        destination_folder = folder / PASTA_PRE_MARKETPLACE
        destination_folder.mkdir(parents=True, exist_ok=True)
        try:
            if source.resolve().parent == destination_folder.resolve():
                return source
        except OSError:
            pass
        destination = self._available_copy_path(destination_folder, source)
        self._copy_image_atomically(source, destination)
        return destination

    def _add_image_to_premarketplace(self, image_path: Path) -> None:
        try:
            destino = self._copy_into_premarketplace(image_path)
        except (OSError, RuntimeError) as erro:
            QMessageBox.warning(self, "Pré-marketplace", str(erro))
            return
        folder = self._cover_product_folder()
        if folder is not None:
            self._refresh_result_gallery(folder)
        self.pre_marketplace_status.setText(
            f"Cópia adicionada a F: {destino.name}"
        )

    def import_images_to_premarketplace(self) -> None:
        if self._cover_product_folder() is None:
            QMessageBox.warning(
                self,
                "Pré-marketplace",
                "Selecione um cadastro antes de adicionar imagens.",
            )
            return
        caminhos, _filtro = QFileDialog.getOpenFileNames(
            self,
            "Adicionar imagens a F · Pré-marketplace",
            "",
            "Imagens (*.jpg *.jpeg *.png *.webp)",
        )
        if not caminhos:
            return
        adicionadas: list[Path] = []
        erros: list[str] = []
        for caminho in caminhos:
            try:
                adicionadas.append(
                    self._copy_into_premarketplace(Path(caminho))
                )
            except (OSError, RuntimeError) as erro:
                erros.append(str(erro))
        folder = self._cover_product_folder()
        if folder is not None:
            self._refresh_result_gallery(folder)
        if erros:
            self.pre_marketplace_status.setText(
                f"{len(adicionadas)} imagem(ns) adicionada(s); "
                f"{len(erros)} falha(s). Confira o log."
            )
            self.show_log("\n".join(erros))
        else:
            self.pre_marketplace_status.setText(
                f"{len(adicionadas)} imagem(ns) copiada(s) para F. "
                "Os arquivos escolhidos permanecem no local original."
            )

    def _open_marketplace_folder(self, nome: str) -> None:
        folder = self._cover_product_folder()
        if folder is None:
            QMessageBox.information(
                self,
                "Marketplace",
                "Selecione um cadastro para abrir a pasta.",
            )
            return
        target = folder / nome
        target.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target.resolve())))

    def _pre_marketplace_item_selected(self, item: QListWidgetItem) -> bool:
        card = self.pre_marketplace_gallery.itemWidget(item)
        checkbox = card.findChild(QCheckBox) if card is not None else None
        return checkbox.isChecked() if checkbox is not None else False

    def _set_pre_marketplace_checks(self, checked: bool) -> None:
        if self._marketplace_processing:
            return
        for index in range(self.pre_marketplace_gallery.count()):
            item = self.pre_marketplace_gallery.item(index)
            card = self.pre_marketplace_gallery.itemWidget(item)
            checkbox = card.findChild(QCheckBox) if card is not None else None
            if checkbox is None:
                continue
            previous_block_state = checkbox.blockSignals(True)
            checkbox.setChecked(checked)
            checkbox.blockSignals(previous_block_state)
        self._pre_marketplace_selection_changed()

    def remove_selected_from_premarketplace(self) -> None:
        if self._marketplace_processing:
            return
        folder = self._cover_product_folder()
        if folder is None:
            QMessageBox.information(
                self,
                "Pré-marketplace",
                "Selecione um cadastro antes de remover imagens.",
            )
            return

        pre_folder = (folder / PASTA_PRE_MARKETPLACE).resolve()
        selected: list[Path] = []
        for index in range(self.pre_marketplace_gallery.count()):
            item = self.pre_marketplace_gallery.item(index)
            if not self._pre_marketplace_item_selected(item):
                continue
            try:
                path = Path(str(item.data(Qt.ItemDataRole.UserRole))).resolve()
                path.relative_to(pre_folder)
            except (OSError, ValueError):
                continue
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                selected.append(path)

        if not selected:
            QMessageBox.information(
                self,
                "Pré-marketplace",
                "Marque ao menos uma cópia da pasta F para remover.",
            )
            return

        resposta = QMessageBox.question(
            self,
            "Remover imagens de F?",
            f"Remover {len(selected)} imagem(ns) selecionada(s) de "
            f"{PASTA_PRE_MARKETPLACE}?\n\n"
            "Os arquivos selecionados dentro de F serão apagados. Arquivos "
            "originais fora de F e imagens já gravadas em G não serão alterados.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        removidas = 0
        caminhos_removidos: list[Path] = []
        erros: list[str] = []
        for path in selected:
            try:
                path.unlink()
                removidas += 1
                caminhos_removidos.append(path)
            except OSError as erro:
                erros.append(f"{path.name}: {erro}")

        if removidas:
            try:
                receitas = self._read_marketplace_recipes(pre_folder)
                for path in caminhos_removidos:
                    receitas.pop(path.name, None)
                self._write_marketplace_recipes(pre_folder, receitas)
            except (OSError, ValueError) as erro:
                erros.append(f"Ajustes salvos das imagens removidas: {erro}")

        self._refresh_result_gallery(folder)
        self.pre_marketplace_status.setText(
            f"{removidas} arquivo(s) removido(s) de F; fontes fora de F preservadas."
        )
        if erros:
            self.show_log(
                "Não foi possível remover algumas imagens de F:\n"
                + "\n".join(erros)
            )

    def _pre_marketplace_selection_changed(self, *_args) -> None:
        selecionadas = sum(
            self._pre_marketplace_item_selected(
                self.pre_marketplace_gallery.item(index)
            )
            for index in range(self.pre_marketplace_gallery.count())
        )
        self.remove_pre_selected_button.setEnabled(
            selecionadas > 0 and not self._marketplace_processing
        )
        self.finish_marketplace_button.setEnabled(
            selecionadas > 0 and not self._marketplace_processing
        )
        self.pre_marketplace_gallery.setEnabled(not self._marketplace_processing)
        if selecionadas:
            self.pre_marketplace_status.setText(
                f"{selecionadas} imagem(ns) selecionada(s) para concluir em G."
            )
        else:
            self.pre_marketplace_status.setText(
                "Clique numa imagem para configurar e pré-visualizar os "
                "recursos. Marque as imagens que deseja concluir em G."
            )

    @staticmethod
    def _empty_marketplace_recipe() -> dict[str, object]:
        return {
            "logo_enabled": False,
            "logo_name": "",
            "include_profile": False,
            "include_url": False,
            "include_custom": False,
            "custom_text": "",
        }

    @staticmethod
    def _marketplace_recipe_file(pre_folder: Path) -> Path:
        return pre_folder / ".hen-marketplace-edits.json"

    def _read_marketplace_recipes(
        self,
        pre_folder: Path,
    ) -> dict[str, dict[str, object]]:
        path = self._marketplace_recipe_file(pre_folder)
        if not path.is_file():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError) as erro:
            raise ValueError(
                f"Não foi possível ler os ajustes salvos de F: {erro}"
            ) from erro
        if not isinstance(data, dict) or not isinstance(data.get("images"), dict):
            raise ValueError(
                "O arquivo de ajustes de F tem formato inválido e não foi "
                "sobrescrito."
            )
        return {
            str(nome): dict(receita)
            for nome, receita in data["images"].items()
            if (
                isinstance(nome, str)
                and Path(nome).name == nome
                and isinstance(receita, dict)
            )
        }

    def _write_marketplace_recipes(
        self,
        pre_folder: Path,
        recipes: dict[str, dict[str, object]],
    ) -> None:
        path = self._marketplace_recipe_file(pre_folder)
        if not recipes:
            path.unlink(missing_ok=True)
            return
        pre_folder.mkdir(parents=True, exist_ok=True)
        temporario = path.with_suffix(".json.tmp")
        temporario.write_text(
            json.dumps(
                {"version": 1, "images": recipes},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        temporario.replace(path)

    def _selected_premarketplace_paths(self, pre_folder: Path) -> list[Path]:
        selecionadas: list[Path] = []
        pre_folder = pre_folder.resolve()
        for index in range(self.pre_marketplace_gallery.count()):
            item = self.pre_marketplace_gallery.item(index)
            if not self._pre_marketplace_item_selected(item):
                continue
            try:
                path = Path(
                    str(item.data(Qt.ItemDataRole.UserRole))
                ).resolve()
                path.relative_to(pre_folder)
            except (OSError, ValueError):
                continue
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                selecionadas.append(path)
        return selecionadas

    @staticmethod
    def _marketplace_brand_settings() -> dict[str, str]:
        configuracao = appdata.ler_config()
        marca = configuracao.get("marca", {})
        if not isinstance(marca, dict):
            return {"perfil_social": "", "url_loja": ""}
        return {
            "perfil_social": str(marca.get("perfil_social") or "").strip(),
            "url_loja": str(marca.get("url_loja") or "").strip(),
        }

    def _marketplace_overlay_data(
        self,
        recipe: dict[str, object],
        *,
        validate: bool = False,
    ) -> dict[str, object]:
        marca = self._marketplace_brand_settings()
        logo_name = (
            str(recipe.get("logo_name") or "").strip()
            if recipe.get("logo_enabled")
            else ""
        )
        logo_path: Path | None = None
        if logo_name:
            if Path(logo_name).name != logo_name:
                if validate:
                    raise ValueError("A logo salva tem um nome de arquivo inválido.")
                logo_name = ""
            else:
                logo_path = Path(appdata.pasta_midia_categoria("logo")) / logo_name
            if logo_name and (logo_path is None or not logo_path.is_file()):
                if validate:
                    raise ValueError(
                        f"A logo escolhida não está mais disponível: {logo_name}"
                    )
                logo_path = None
        elif validate and recipe.get("logo_enabled"):
            raise ValueError("Escolha uma logo ou desative a opção de logo.")

        perfil = marca["perfil_social"]
        url = marca["url_loja"]
        custom_text = str(recipe.get("custom_text") or "").strip()
        if validate and recipe.get("include_profile") and not perfil:
            raise ValueError(
                "Cadastre o @ do perfil em Configurações antes de aplicá-lo."
            )
        if validate and recipe.get("include_url") and not url:
            raise ValueError(
                "Cadastre o endereço da loja em Configurações antes de aplicá-lo."
            )
        if validate and recipe.get("include_custom") and not custom_text:
            raise ValueError(
                "Digite o texto personalizado ou desative essa opção."
            )

        textos = {
            "superior_direita": (
                perfil if recipe.get("include_profile") else ""
            ),
            "inferior_esquerda": url if recipe.get("include_url") else "",
            "inferior_direita": (
                custom_text if recipe.get("include_custom") else ""
            ),
        }
        return {
            "logo_path": str(logo_path) if logo_path is not None else "",
            "textos": {
                posicao: texto
                for posicao, texto in textos.items()
                if texto
            },
        }

    @staticmethod
    def _marketplace_preview_key(
        source: Path,
        overlays: dict[str, object],
    ) -> tuple[object, ...]:
        source = source.resolve()
        source_stat = source.stat()
        logo_value = str(overlays.get("logo_path") or "").strip()
        logo_resolved = Path(logo_value).resolve() if logo_value else None
        logo_stat = (
            logo_resolved.stat()
            if logo_resolved is not None and logo_resolved.is_file()
            else None
        )
        textos = overlays.get("textos", {})
        textos_key = (
            tuple(sorted((str(key), str(value)) for key, value in textos.items()))
            if isinstance(textos, dict)
            else ()
        )
        return (
            str(source),
            source_stat.st_size,
            source_stat.st_mtime_ns,
            str(logo_resolved) if logo_resolved is not None else None,
            logo_stat.st_size if logo_stat is not None else None,
            logo_stat.st_mtime_ns if logo_stat is not None else None,
            textos_key,
        )

    def preview_premarketplace_image(self, image_path: Path) -> None:
        """Abre a edição por imagem, com prévia e recursos explicitamente opcionais."""
        if self._marketplace_processing:
            return
        folder = self._cover_product_folder()
        if folder is None:
            QMessageBox.information(
                self,
                "Pré-marketplace",
                "Selecione um cadastro para visualizar os ajustes.",
            )
            return

        source = Path(image_path)
        pre_folder = (folder / PASTA_PRE_MARKETPLACE).resolve()
        try:
            source = source.resolve()
            source.relative_to(pre_folder)
            if (
                not source.is_file()
                or source.suffix.lower() not in IMAGE_EXTENSIONS
            ):
                raise FileNotFoundError(source)
            recipes = self._read_marketplace_recipes(pre_folder)
            recipe = dict(
                recipes.get(source.name, self._empty_marketplace_recipe())
            )
        except (OSError, ValueError) as erro:
            QMessageBox.warning(
                self,
                "Pré-marketplace",
                f"Não foi possível abrir os ajustes desta imagem de F:\n\n{erro}",
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Ajustar imagem para o marketplace · {source.name}")
        dialog.resize(1020, 700)
        root = QVBoxLayout(dialog)
        instructions = QLabel(
            "Ajustes salvos por imagem. A prévia não altera F; somente "
            "“Concluir e enviar para G” grava a cópia final e reduz o tamanho."
        )
        instructions.setWordWrap(True)
        root.addWidget(instructions)

        columns = QHBoxLayout()
        preview_image = QLabel()
        preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_image.setMinimumSize(600, 500)
        preview_image.setPixmap(
            QPixmap(str(source)).scaled(
                QSize(600, 500),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        columns.addWidget(preview_image, 3)

        controls = QGroupBox("Recursos desta imagem")
        controls.setMinimumWidth(300)
        controls_layout = QVBoxLayout(controls)
        positions = QLabel(
            "Posições: logo no alto à esquerda; @ no alto à direita; "
            "endereço embaixo à esquerda; texto personalizado embaixo à direita."
        )
        positions.setWordWrap(True)
        controls_layout.addWidget(positions)
        brands = self._marketplace_brand_settings()

        logo_enabled = QCheckBox("Adicionar logo")
        logo_enabled.setChecked(bool(recipe.get("logo_enabled")))
        logo_choice = QComboBox()
        logo_choice.addItem("Escolher logo…", None)
        logos = appdata.listar_midias("logo")
        for logo in logos:
            logo_choice.addItem(logo, logo)
        saved_logo = str(recipe.get("logo_name") or "")
        if saved_logo:
            index_logo = logo_choice.findData(saved_logo)
            if index_logo >= 0:
                logo_choice.setCurrentIndex(index_logo)
        logo_choice.setEnabled(logo_enabled.isChecked())
        logo_enabled.toggled.connect(logo_choice.setEnabled)
        controls_layout.addWidget(logo_enabled)
        controls_layout.addWidget(logo_choice)

        profile_enabled = QCheckBox("Adicionar @ do perfil")
        profile_enabled.setChecked(bool(recipe.get("include_profile")))
        profile_value = QLabel(
            f"Configurações: {brands['perfil_social'] or 'não cadastrado'}"
        )
        profile_value.setWordWrap(True)
        controls_layout.addWidget(profile_enabled)
        controls_layout.addWidget(profile_value)

        url_enabled = QCheckBox("Adicionar endereço da loja")
        url_enabled.setChecked(bool(recipe.get("include_url")))
        url_value = QLabel(
            f"Configurações: {brands['url_loja'] or 'não cadastrado'}"
        )
        url_value.setWordWrap(True)
        controls_layout.addWidget(url_enabled)
        controls_layout.addWidget(url_value)

        custom_enabled = QCheckBox("Adicionar texto personalizado")
        custom_enabled.setChecked(bool(recipe.get("include_custom")))
        custom_input = QLineEdit()
        custom_input.setPlaceholderText("Digite o texto")
        custom_input.setText(str(recipe.get("custom_text") or ""))
        custom_input.setEnabled(custom_enabled.isChecked())
        custom_enabled.toggled.connect(custom_input.setEnabled)
        controls_layout.addWidget(custom_enabled)
        controls_layout.addWidget(custom_input)
        controls_layout.addStretch(1)

        render_status = QLabel()
        render_status.setWordWrap(True)
        controls_layout.addWidget(render_status)
        columns.addWidget(controls, 1)
        root.addLayout(columns, 1)

        def recipe_atual() -> dict[str, object]:
            return {
                "logo_enabled": logo_enabled.isChecked(),
                "logo_name": str(logo_choice.currentData() or ""),
                "include_profile": profile_enabled.isChecked(),
                "include_url": url_enabled.isChecked(),
                "include_custom": custom_enabled.isChecked(),
                "custom_text": custom_input.text().strip(),
            }

        def request_preview(*_args) -> None:
            recipe_now = recipe_atual()
            warnings: list[str] = []
            if recipe_now["logo_enabled"] and not recipe_now["logo_name"]:
                warnings.append("Escolha uma logo.")
            elif recipe_now["logo_enabled"]:
                logo_file = (
                    Path(appdata.pasta_midia_categoria("logo"))
                    / str(recipe_now["logo_name"])
                )
                if not logo_file.is_file():
                    warnings.append("A logo escolhida não está disponível.")
            if recipe_now["include_profile"] and not brands["perfil_social"]:
                warnings.append("@ não cadastrado em Configurações.")
            if recipe_now["include_url"] and not brands["url_loja"]:
                warnings.append("Endereço não cadastrado em Configurações.")
            if recipe_now["include_custom"] and not recipe_now["custom_text"]:
                warnings.append("Digite o texto personalizado.")
            render_status.setText(" ".join(warnings))
            self._queue_marketplace_preview(
                dialog,
                source,
                recipe_now,
                preview_image,
                render_status,
            )

        preview_timer = QTimer(dialog)
        preview_timer.setSingleShot(True)
        preview_timer.setInterval(220)
        preview_timer.timeout.connect(request_preview)
        for signal in (
            logo_enabled.toggled,
            logo_choice.currentIndexChanged,
            profile_enabled.toggled,
            url_enabled.toggled,
            custom_enabled.toggled,
            custom_input.textChanged,
        ):
            signal.connect(lambda *_args: preview_timer.start())

        actions = QHBoxLayout()
        save_one = QPushButton("OK · só esta imagem")
        save_selected = QPushButton("Aplicar às marcadas")
        selected_paths = self._selected_premarketplace_paths(pre_folder)
        save_selected.setText(
            f"Aplicar às marcadas ({len(selected_paths)})"
        )
        save_selected.setEnabled(bool(selected_paths))
        save_all = QPushButton("Aplicar em todas de F")
        cancel = QPushButton("Cancelar")
        save_one.clicked.connect(
            lambda _checked=False: self._save_marketplace_recipe(
                dialog, pre_folder, [source], recipe_atual()
            )
        )
        save_selected.clicked.connect(
            lambda _checked=False: self._save_marketplace_recipe(
                dialog, pre_folder, selected_paths, recipe_atual()
            )
        )
        save_all.clicked.connect(
            lambda _checked=False: self._save_marketplace_recipe(
                dialog,
                pre_folder,
                self._images_in(pre_folder),
                recipe_atual(),
            )
        )
        cancel.clicked.connect(dialog.reject)
        for button in (save_one, save_selected, save_all, cancel):
            actions.addWidget(button)
        root.addLayout(actions)

        dialog_key = id(dialog)
        dialog.finished.connect(
            lambda _result, key=dialog_key: (
                self._marketplace_preview_dialog_versions.pop(key, None)
            )
        )
        request_preview()
        dialog.exec()

    def _save_marketplace_recipe(
        self,
        dialog: QDialog,
        pre_folder: Path,
        targets: list[Path],
        recipe: dict[str, object],
    ) -> None:
        if not targets:
            QMessageBox.information(
                dialog,
                "Pré-marketplace",
                "Não há imagens para receber esses ajustes.",
            )
            return
        try:
            self._marketplace_overlay_data(recipe, validate=True)
            receitas = self._read_marketplace_recipes(pre_folder)
            pasta_validada = pre_folder.resolve()
            for target in targets:
                caminho = target.resolve()
                caminho.relative_to(pasta_validada)
                if caminho.is_file() and caminho.suffix.lower() in IMAGE_EXTENSIONS:
                    receitas[caminho.name] = dict(recipe)
            self._write_marketplace_recipes(pre_folder, receitas)
        except (OSError, ValueError) as erro:
            QMessageBox.warning(
                dialog,
                "Não foi possível salvar os ajustes",
                str(erro),
            )
            return

        quantidade = sum(
            1
            for target in targets
            if target.is_file() and target.suffix.lower() in IMAGE_EXTENSIONS
        )
        self.pre_marketplace_status.setText(
            f"Ajustes salvos para {quantidade} imagem(ns). "
            "Os arquivos de F continuam intactos; conclua em G para gerar "
            "as cópias finais."
        )
        dialog.accept()

    def _queue_marketplace_preview(
        self,
        dialog: QDialog,
        source: Path,
        recipe: dict[str, object],
        image_label: QLabel,
        status_label: QLabel,
    ) -> None:
        dialog_key = id(dialog)
        request_id = self._marketplace_preview_dialog_versions.get(
            dialog_key, 0
        ) + 1
        self._marketplace_preview_dialog_versions[dialog_key] = request_id
        try:
            overlays = self._marketplace_overlay_data(recipe)
            cache_key = self._marketplace_preview_key(source, overlays)
        except (OSError, ValueError) as erro:
            status_label.setText(str(erro))
            return

        cached = self._marketplace_preview_cache.get(cache_key)
        if cached is not None:
            self._marketplace_preview_cache.move_to_end(cache_key)
            self._set_marketplace_preview_image(image_label, cached)
            if not status_label.text():
                status_label.setText("Prévia pronta. F permanece intacta.")
            return

        textos = overlays.get("textos", {})
        tem_recursos = bool(overlays.get("logo_path")) or bool(textos)
        if not tem_recursos:
            self._set_marketplace_preview_image(
                image_label,
                QPixmap(str(source)),
            )
            if not status_label.text():
                status_label.setText(
                    "Nenhum recurso aplicado. O original em F permanece intacto."
                )
            return

        status_label.setText("Gerando prévia dos recursos selecionados…")
        pasta_preview = Path(
            tempfile.mkdtemp(prefix="hen-place-marketplace-preview-")
        )
        try:
            self.start_task(
                preparar_imagens_marketplace,
                [str(source)],
                str(pasta_preview),
                recursos_por_imagem={str(source.resolve()): overlays},
                reduzir_para_marketplace=False,
                on_done=lambda resultados, key=cache_key, pasta=pasta_preview, dialog_id=dialog_key, token=request_id, dlg=dialog, label=image_label, status=status_label: (
                    self._marketplace_dialog_preview_ready(
                        key,
                        pasta,
                        dialog_id,
                        token,
                        dlg,
                        label,
                        status,
                        resultados,
                    )
                ),
                on_error=lambda erro, pasta=pasta_preview, dialog_id=dialog_key, token=request_id, dlg=dialog, status=status_label: (
                    self._marketplace_dialog_preview_failed(
                        pasta,
                        dialog_id,
                        token,
                        dlg,
                        status,
                        erro,
                    )
                ),
            )
        except Exception as erro:
            shutil.rmtree(pasta_preview, ignore_errors=True)
            status_label.setText(f"Falha ao gerar prévia: {erro}")

    @staticmethod
    def _set_marketplace_preview_image(
        image_label: QLabel,
        pixmap: QPixmap,
    ) -> None:
        if pixmap.isNull():
            image_label.setText("Prévia indisponível.")
            image_label.setPixmap(QPixmap())
            return
        image_label.setText("")
        image_label.setPixmap(
            pixmap.scaled(
                image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _marketplace_dialog_preview_ready(
        self,
        cache_key: tuple[object, ...],
        pasta_preview: Path,
        dialog_key: int,
        request_id: int,
        dialog: QDialog,
        image_label: QLabel,
        status_label: QLabel,
        resultados: object,
    ) -> None:
        caminhos = (
            [Path(caminho) for caminho in resultados]
            if isinstance(resultados, list)
            else []
        )
        pixmap = QPixmap(str(caminhos[0])) if caminhos else QPixmap()
        shutil.rmtree(pasta_preview, ignore_errors=True)
        if pixmap.isNull():
            if self._marketplace_preview_dialog_versions.get(dialog_key) == request_id:
                status_label.setText("Não foi possível carregar a prévia.")
            return

        self._marketplace_preview_cache[cache_key] = pixmap
        self._marketplace_preview_cache.move_to_end(cache_key)
        while len(self._marketplace_preview_cache) > 8:
            self._marketplace_preview_cache.popitem(last=False)
        if (
            self._marketplace_preview_dialog_versions.get(dialog_key)
            != request_id
            or not dialog.isVisible()
        ):
            return
        self._set_marketplace_preview_image(image_label, pixmap)
        status_label.setText("Prévia pronta. F permanece intacta.")

    def _marketplace_dialog_preview_failed(
        self,
        pasta_preview: Path,
        dialog_key: int,
        request_id: int,
        dialog: QDialog,
        status_label: QLabel,
        erro: str,
    ) -> None:
        shutil.rmtree(pasta_preview, ignore_errors=True)
        if (
            self._marketplace_preview_dialog_versions.get(dialog_key)
            == request_id
            and dialog.isVisible()
        ):
            status_label.setText(f"Falha ao gerar prévia: {erro}")
        self.show_log(f"Falha na prévia de marketplace:\n{erro}")

    def finalize_marketplace_edits(self) -> None:
        if self._marketplace_processing:
            return
        folder = self._cover_product_folder()
        if folder is None:
            QMessageBox.warning(
                self, "Marketplace", "Selecione um cadastro."
            )
            return
        pre_folder = (folder / PASTA_PRE_MARKETPLACE).resolve()
        selecionadas = self._selected_premarketplace_paths(pre_folder)
        if not selecionadas:
            QMessageBox.information(
                self,
                "Marketplace",
                "Marque ao menos uma imagem válida dentro de F.",
            )
            return

        try:
            receitas = self._read_marketplace_recipes(pre_folder)
            recursos_por_imagem: dict[str, dict[str, object]] = {}
            for image_path in selecionadas:
                recipe = dict(
                    receitas.get(
                        image_path.name,
                        self._empty_marketplace_recipe(),
                    )
                )
                recursos_por_imagem[str(image_path.resolve())] = (
                    self._marketplace_overlay_data(recipe, validate=True)
                )
        except (OSError, ValueError) as erro:
            QMessageBox.warning(
                self,
                "Ajustes do pré-marketplace",
                f"Revise os ajustes salvos antes de concluir:\n\n{erro}",
            )
            return
        imagens = [str(image_path) for image_path in selecionadas]

        self._marketplace_processing = True
        self.remove_pre_selected_button.setEnabled(False)
        self.finish_marketplace_button.setText("Preparando para G…")
        self.finish_marketplace_button.setEnabled(False)
        self.pre_marketplace_gallery.setEnabled(False)
        self.pre_marketplace_status.setText(
            "Aplicando os ajustes de cada imagem e reduzindo as cópias para G..."
        )
        pasta_final = Path(
            tempfile.mkdtemp(prefix="hen-place-marketplace-final-")
        )
        try:
            self.start_task(
                preparar_imagens_marketplace,
                imagens,
                str(pasta_final),
                recursos_por_imagem=recursos_por_imagem,
                reduzir_para_marketplace=True,
                on_done=lambda resultados, product_folder=folder, temp_dir=pasta_final: (
                    self._marketplace_delivery_ready(
                        product_folder,
                        temp_dir,
                        resultados,
                    )
                ),
                on_error=lambda erro, product_folder=folder, temp_dir=pasta_final: (
                    self._marketplace_delivery_failed(
                        product_folder,
                        temp_dir,
                        erro,
                    )
                )
            )
        except Exception as erro:
            self._marketplace_processing = False
            self.pre_marketplace_gallery.setEnabled(True)
            self.finish_marketplace_button.setText("Concluir e enviar para G")
            shutil.rmtree(pasta_final, ignore_errors=True)
            self._pre_marketplace_selection_changed()
            self.show_log(f"Falha ao iniciar a preparação para G: {erro}")
            QMessageBox.warning(
                self,
                "Falha ao iniciar",
                f"Não foi possível iniciar a conclusão das imagens.\n\n{erro}",
            )

    def _marketplace_delivery_ready(
        self,
        folder: Path,
        pasta_final: Path,
        resultados: object,
    ) -> None:
        caminhos = (
            [Path(caminho) for caminho in resultados]
            if isinstance(resultados, list)
            else []
        )
        caminhos = [caminho for caminho in caminhos if caminho.is_file()]
        if not caminhos:
            self._marketplace_delivery_failed(
                folder,
                pasta_final,
                "Nenhuma imagem final foi gerada.",
            )
            return

        copied: list[Path] = []
        erro_copia: Exception | None = None
        try:
            destino = folder / PASTA_MARKETPLACE
            destino.mkdir(parents=True, exist_ok=True)
            for caminho in caminhos:
                if caminho.stat().st_size > 2_000_000:
                    raise ValueError(
                        f"{caminho.name} ainda excede 2.000.000 bytes."
                    )
                novo_caminho = self._available_copy_path(destino, caminho)
                self._copy_image_atomically(caminho, novo_caminho)
                copied.append(novo_caminho)
        except Exception as erro:
            erro_copia = erro
            for caminho in copied:
                try:
                    caminho.unlink(missing_ok=True)
                except OSError as erro_remocao:
                    self.show_log(
                        f"Falha ao reverter cópia parcial {caminho}: "
                        f"{erro_remocao}"
                    )
        finally:
            shutil.rmtree(pasta_final, ignore_errors=True)
            self._marketplace_processing = False
            self.pre_marketplace_gallery.setEnabled(True)
            self.finish_marketplace_button.setText("Concluir e enviar para G")

        if erro_copia is not None:
            self._pre_marketplace_selection_changed()
            self.pre_marketplace_status.setText(
                "Não foi possível concluir a cópia para G. As imagens de F "
                "permanecem intactas."
            )
            self.show_log(f"Falha ao copiar imagens finais para G: {erro_copia}")
            QMessageBox.warning(
                self,
                "Falha ao gravar em G",
                f"As imagens não foram concluídas em G.\n\n{erro_copia}",
            )
            return

        self._refresh_result_gallery(folder)
        self.pre_marketplace_status.setText(
            f"{len(copied)} imagem(ns) concluída(s) e copiada(s) para G. "
            "F e as imagens originais permanecem intactas."
        )

    def _marketplace_delivery_failed(
        self,
        folder: Path,
        pasta_final: Path,
        erro: str,
    ) -> None:
        shutil.rmtree(pasta_final, ignore_errors=True)
        self._marketplace_processing = False
        self.pre_marketplace_gallery.setEnabled(True)
        self.finish_marketplace_button.setText("Concluir e enviar para G")
        self._pre_marketplace_selection_changed()
        self.pre_marketplace_status.setText(
            "Falha ao preparar as imagens. F e as originais permanecem intactas."
        )
        self.show_log(f"Falha ao preparar imagens para G:\n{erro}")
        QMessageBox.warning(
            self,
            "Falha na preparação",
            "Não foi possível preparar as imagens para G.\n\n" + str(erro),
        )

    def _cover_product_folder(self) -> Path | None:
        if self._result_folder is not None:
            return self._result_folder
        if self.current_row:
            return Path(str(self.current_row[2]))
        return None

    def _cover_source_changed(self, slug: str) -> None:
        combo = self._cover_source_choices.get(slug)
        preview = self._cover_source_previews.get(slug)
        path_value = combo.currentData() if combo else None
        path = Path(str(path_value)) if path_value else None
        if preview is not None:
            self._set_resource_preview(
                preview,
                path,
                "Selecione uma imagem",
            )
        button = self._cover_prepare_buttons.get(slug)
        if button is not None:
            button.setEnabled(bool(path and path.is_file()))
        if slug == CAPA_SLOTS[0][0]:
            self._visual_selection_changed()

    def _refresh_cover_source_choices(
        self,
        sources: list[tuple[str, Path]],
        default_cover_source: Path | None,
    ) -> None:
        self._cover_sources = sources
        for slug, _title, _variant in CAPA_SLOTS:
            combo = self._cover_source_choices[slug]
            previous = combo.currentData()
            previous_block_state = combo.blockSignals(True)
            try:
                combo.clear()
                combo.addItem("Selecione uma imagem de referência", None)
                for category, path in sources:
                    combo.addItem(f"{category} · {path.name}", str(path))
                    combo.setItemData(
                        combo.count() - 1,
                        str(path),
                        Qt.ItemDataRole.ToolTipRole,
                    )
                index = combo.findData(previous)
                if index < 0 and slug == CAPA_SLOTS[0][0] and default_cover_source:
                    index = combo.findData(str(default_cover_source))
                combo.setCurrentIndex(max(0, index))
            finally:
                combo.blockSignals(previous_block_state)
            self._cover_source_changed(slug)

    def _refresh_cover_stage_outputs(self, folder: Path | None = None) -> None:
        if folder is None:
            folder = self._cover_product_folder()
        if folder is None:
            pre_folder = final_folder = None
        else:
            pre_folder = folder / PASTA_PRE_CAPAS
            final_folder = folder / PASTA_CAPAS

        staged: dict[str, Path | None] = {}
        final: dict[str, Path | None] = {}
        for slug, _title, _variant in CAPA_SLOTS:
            staged[slug] = (
                self._cover_image_for_role(pre_folder, slug)
                if pre_folder is not None
                else None
            )
            final[slug] = (
                self._cover_image_for_role(final_folder, slug)
                if final_folder is not None
                else None
            )

            self._cover_import_buttons[slug].setEnabled(
                folder is not None and folder.is_dir()
            )
            pending = staged[slug]
            completed = final[slug]
            display_path = pending or completed
            self._set_resource_preview(
                self._cover_result_previews[slug],
                display_path,
                "Ainda não importado",
            )
            if pending and completed:
                status = (
                    f"Nova imagem em {PASTA_PRE_CAPAS}: {pending.name}; "
                    f"a versão atual permanece em {PASTA_CAPAS}."
                )
            elif pending:
                status = f"Importada em {PASTA_PRE_CAPAS}: {pending.name}"
            elif completed:
                status = f"Concluída em {PASTA_CAPAS}: {completed.name}"
            else:
                status = "Aguardando imagem pronta."
            self._cover_slot_status[slug].setText(status)

        complete = all(staged[slug] or final[slug] for slug, _, _ in CAPA_SLOTS)
        has_pending = any(staged.values())
        self.finish_covers_button.setEnabled(
            folder is not None
            and folder.is_dir()
            and complete
            and has_pending
        )
        missing = [
            title
            for slug, title, _variant in CAPA_SLOTS
            if not (staged[slug] or final[slug])
        ]
        if folder is None:
            self.cover_stage_status.setText(
                "Selecione um cadastro para montar o conjunto de capas."
            )
        elif missing:
            self.cover_stage_status.setText(
                "Faltam imagens para: " + ", ".join(missing) + "."
            )
        elif has_pending:
            self.cover_stage_status.setText(
                "Trio completo. Concluir copia somente as funções com novas "
                f"imagens de {PASTA_PRE_CAPAS} para {PASTA_CAPAS}."
            )
        else:
            self.cover_stage_status.setText(
                f"Trio concluído em {PASTA_CAPAS}; nenhuma atualização pendente."
            )

        self.open_pre_covers_button.setEnabled(
            pre_folder is not None and pre_folder.is_dir()
        )
        self.open_final_covers_button.setEnabled(
            final_folder is not None and final_folder.is_dir()
        )

        legacy_paths: list[Path] = []
        if folder is not None:
            legacy_paths.extend(self._images_in(folder / "_Capas"))
            legacy_pre = folder / "Pre_Capas"
            if (
                legacy_pre.is_dir()
                and (pre_folder is None or legacy_pre.resolve() != pre_folder.resolve())
            ):
                legacy_paths.extend(self._images_in(legacy_pre))
        unique_legacy = list(dict.fromkeys(legacy_paths))
        self._fill_gallery(
            self.legacy_covers_gallery,
            unique_legacy,
            "Nenhuma pasta legada de capas encontrada.",
        )
        self.legacy_covers_group.setVisible(bool(unique_legacy))
        if unique_legacy:
            self.legacy_covers_status.setText(
                "Esses arquivos antigos não serão renomeados, movidos nem "
                "apagados. Se precisar, selecione-os como referência acima."
            )

    def _prepare_cover_slot_for_capcut(self, slug: str, variant: str) -> None:
        combo = self._cover_source_choices.get(slug)
        value = combo.currentData() if combo else None
        if not value:
            QMessageBox.information(
                self,
                "Selecione uma imagem",
                "Escolha a imagem de referência desta função antes de preparar "
                "o prompt para o CapCut.",
            )
            return
        self._prepare_image_prompt(Path(str(value)), variant)

    def _import_cover_result(self, slug: str) -> None:
        folder = self._cover_product_folder()
        if folder is None:
            return
        if not folder.is_dir():
            QMessageBox.warning(
                self,
                "Pasta do produto não encontrada",
                f"Não é possível importar a imagem porque a pasta não existe:\n{folder}",
            )
            return
        titles = {role_slug: title for role_slug, title, _variant in CAPA_SLOTS}
        source_name, _selected_filter = QFileDialog.getOpenFileName(
            self,
            f"Importar resultado · {titles.get(slug, slug)}",
            "",
            "Imagens (*.png *.jpg *.jpeg *.webp)",
        )
        if not source_name:
            return
        source = Path(source_name)
        if source.suffix.lower() not in IMAGE_EXTENSIONS or not source.is_file():
            QMessageBox.warning(
                self,
                "Arquivo inválido",
                "Escolha um arquivo PNG, JPG, JPEG ou WEBP existente.",
            )
            return

        destination_folder = folder / PASTA_PRE_CAPAS
        destination = destination_folder / f"{slug}{source.suffix.lower()}"
        previous = self._cover_image_for_role(destination_folder, slug)
        if previous is not None:
            answer = QMessageBox.question(
                self,
                "Substituir imagem em pre_capas?",
                "Já existe uma imagem importada para esta função. "
                "Substituí-la não altera a versão que está em f_capas.",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        if source.resolve() == destination.resolve():
            self._refresh_cover_stage_outputs(folder)
            return

        try:
            destination_folder.mkdir(parents=True, exist_ok=True)
            self._copy_image_atomically(source, destination)
            if previous is not None and previous != destination:
                previous.unlink(missing_ok=True)
        except OSError as exc:
            QMessageBox.warning(
                self,
                "Falha ao importar imagem",
                f"Não foi possível copiar a imagem para {destination_folder}:\n{exc}",
            )
            return

        self._refresh_cover_stage_outputs(folder)

    def _finish_cover_set(self) -> None:
        folder = self._cover_product_folder()
        if folder is None:
            return
        pre_folder = folder / PASTA_PRE_CAPAS
        final_folder = folder / PASTA_CAPAS
        staged = {
            slug: self._cover_image_for_role(pre_folder, slug)
            for slug, _title, _variant in CAPA_SLOTS
        }
        existing = {
            slug: self._cover_image_for_role(final_folder, slug)
            for slug, _title, _variant in CAPA_SLOTS
        }
        missing = [
            title
            for slug, title, _variant in CAPA_SLOTS
            if not (staged[slug] or existing[slug])
        ]
        if missing:
            QMessageBox.warning(
                self,
                "Trio incompleto",
                "Importe as imagens que faltam antes de concluir: "
                + ", ".join(missing),
            )
            return

        updates = [slug for slug, _title, _variant in CAPA_SLOTS if staged[slug]]
        if not updates:
            return
        replacing = [slug for slug in updates if existing[slug]]
        if replacing:
            replacing_titles = [
                title
                for slug, title, _variant in CAPA_SLOTS
                if slug in replacing
            ]
            answer = QMessageBox.question(
                self,
                "Atualizar f_capas?",
                "Isto substituirá apenas estas funções em f_capas: "
                + ", ".join(replacing_titles)
                + ". As imagens em pre_capas serão preservadas.",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        pending_by_role: dict[str, Path] = {}
        try:
            final_folder.mkdir(parents=True, exist_ok=True)
            copied_by_role: dict[str, Path] = {}
            for slug in updates:
                source = staged[slug]
                if source is None:
                    continue
                with tempfile.NamedTemporaryFile(
                    prefix=f".{slug}.",
                    suffix=".tmp",
                    dir=final_folder,
                    delete=False,
                ) as handle:
                    pending = Path(handle.name)
                pending_by_role[slug] = pending
                shutil.copy2(source, pending)

            for slug in updates:
                source = staged[slug]
                pending = pending_by_role.get(slug)
                if source is None or pending is None:
                    continue
                destination = final_folder / f"{slug}{source.suffix.lower()}"
                pending.replace(destination)
                copied_by_role[slug] = destination

            for slug in updates:
                destination = copied_by_role.get(slug)
                if destination is None:
                    continue
                for old_path in self._cover_role_files(final_folder, slug):
                    if old_path != destination:
                        old_path.unlink(missing_ok=True)
        except OSError as exc:
            QMessageBox.warning(
                self,
                "Falha ao concluir capas",
                "Não foi possível concluir todas as cópias. Os arquivos já "
                f"importados em pre_capas foram preservados.\n\n{exc}",
            )
            self._refresh_cover_stage_outputs(folder)
            return
        finally:
            for pending in pending_by_role.values():
                pending.unlink(missing_ok=True)

        self._refresh_cover_stage_outputs(folder)
        self._refresh_result_summary_covers()

    def _refresh_result_summary_covers(self) -> None:
        folder = self._cover_product_folder()
        if folder is None:
            return
        ready = sum(
            self._cover_image_for_role(folder / PASTA_CAPAS, slug) is not None
            for slug, _title, _variant in CAPA_SLOTS
        )
        current = self.result_summary.text().split(" • Capas:")[0]
        self.result_summary.setText(f"{current} • Capas: {ready}/3 em {PASTA_CAPAS}")

    def _open_cover_folder(self, folder_name: str) -> None:
        folder = self._cover_product_folder()
        if folder is None:
            return
        target = folder / folder_name
        if target.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target.resolve())))

    def _refresh_result_gallery(self, folder: Path | None = None) -> None:
        if folder is None and self.current_row:
            folder = Path(str(self.current_row[2]))
        if folder is None:
            self._result_folder = None
            samples: list[Path] = []
            white_samples: list[Path] = []
            measures: list[Path] = []
            cover_backgrounds: list[Path] = []
            video = None
        else:
            self._result_folder = folder

            def pasta_resultado(nome: str, *legados: str) -> Path:
                caminhos = [folder / candidato for candidato in (nome, *legados)]
                for caminho in caminhos:
                    if caminho.is_dir() and self._images_in(caminho):
                        return caminho
                for caminho in caminhos:
                    if caminho.is_dir():
                        return caminho
                return folder / nome

            nomes_amostra: set[str] = set()
            try:
                ordem_imagens, _videos = _ler_ordem_midias_producao(folder)
                nomes, _medidas, _resumo = _separar_imagens_por_papel(
                    ordem_imagens
                )
                nomes_amostra = {
                    Path(nome).stem.casefold()
                    for nome in nomes
                }
            except (OSError, ValueError, TypeError):
                nomes_amostra = set()
            samples = [
                caminho
                for caminho in self._images_in(
                    pasta_resultado(PASTA_SEM_FUNDO, "B_SemFundo", "a_Sem_Fundo")
                )
                if caminho.stem.casefold() in nomes_amostra
            ]
            white_samples = [
                caminho
                for caminho in self._images_in(
                    pasta_resultado(
                        PASTA_FUNDO_BRANCO,
                        "C_FundoBranco",
                        "Fundo_Banco",
                    )
                )
                if caminho.stem.casefold() in nomes_amostra
            ]
            measures = self._images_in(
                pasta_resultado(PASTA_MEDIDAS, "D_Medidas", "d_Medida_COM_LOGO")
            )
            cover_backgrounds = self._images_in(
                pasta_resultado(PASTA_FUNDO_CAPA)
            )
            videos = [
                video
                for nome_pasta in (
                    PASTA_VIDEO_CONVERTIDO,
                    PASTA_VIDEO_LEGADO,
                    "Video_shopee_convertido",
                )
                for video in sorted((folder / nome_pasta).glob("*.mp4"))
            ]
            video = videos[0] if videos else None

        self._fill_sample_gallery(samples)
        self._fill_source_gallery(
            self.white_gallery,
            white_samples,
            "Nenhuma imagem com fundo branco encontrada.",
        )
        self._fill_source_gallery(
            self.measure_gallery,
            measures,
            "Nenhuma imagem final de medida encontrada.",
            with_actions=True,
            with_prompt_actions=False,
        )
        self._fill_source_gallery(
            self.cover_background_gallery,
            cover_backgrounds,
            "Nenhuma imagem com fundo de capa encontrada.",
        )
        if folder is not None:
            self._fill_pre_marketplace_gallery(
                self._images_in(folder / PASTA_PRE_MARKETPLACE)
            )
            self._fill_gallery(
                self.marketplace_gallery,
                self._images_in(folder / PASTA_MARKETPLACE),
                "Nenhuma imagem pronta em G.",
            )
            self.pre_marketplace_status.setText(
                "Clique em uma imagem para conferir logo/texto. Marque as "
                "imagens que deseja concluir e copiar para G."
            )
            self.open_pre_marketplace_button.setEnabled(True)
            self.open_marketplace_button.setEnabled(True)
        else:
            self._fill_pre_marketplace_gallery([])
            self._fill_gallery(
                self.marketplace_gallery,
                [],
                "Nenhuma imagem pronta em G.",
            )
            self.pre_marketplace_status.setText(
                "Selecione um cadastro para usar o pré-marketplace."
            )
            self.open_pre_marketplace_button.setEnabled(False)
            self.open_marketplace_button.setEnabled(False)
        self.video_output_path = video
        self.video_preview_player.stop()
        self.play_video_button.setText("Reproduzir")
        self.open_video_button.setEnabled(video is not None)
        self.play_video_button.setEnabled(video is not None)
        if video is None:
            self.video_preview_player.setSource(QUrl())
            self.video_status.setText("Nenhum vídeo disponível.")
        else:
            self.video_preview_player.setSource(
                QUrl.fromLocalFile(str(video.resolve()))
            )
            self.video_status.setText(f"Pronto · {video.name}")

        self.result_summary.setText(
            f"Sem fundo: {len(samples)} • Fundo branco: {len(white_samples)} "
            f"• Medidas: {len(measures)} • Fundo capa: {len(cover_backgrounds)} "
            f"• Vídeo Shopee: {'pronto' if video is not None else 'não encontrado'}"
        )
        self.result_summary.setToolTip(
            f"Pasta de saída: {folder}" if folder is not None else "Sem produto carregado."
        )

    def _build_image_prompt(self, image_path: Path, variant: str) -> str:
        row = self.current_row or ()

        def campo(indice: int) -> str:
            return str(row[indice] or "").strip() if len(row) > indice else ""

        if variant not in {"capa", "uso", "detalhe"}:
            raise ValueError(f"Tipo de imagem desconhecido: {variant}")

        try:
            templates = carregar_prompts_imagem()
        except (OSError, TypeError, ValueError) as exc:
            raise ValueError(
                f"Não foi possível carregar o modelo de imagem: {exc}"
            ) from exc

        template = str(templates.get(variant) or "").strip()
        if not template:
            raise ValueError(
                f"Não há um modelo editável configurado para “{variant}”."
            )

        substituicoes = {
            "[[PRODUTO]]": campo(0),
            "[[REFERENCIA]]": campo(1),
            "[[DESCRICAO]]": campo(3),
            "[[SERVENTIA]]": campo(4),
            "[[ACABAMENTO]]": campo(6),
            "[[IMAGEM_REFERENCIA]]": image_path.name,
        }

        marcadores_dados_fisicos = (
            "[[ALTURA]]",
            "[[LARGURA]]",
            "[[ESPESSURA]]",
            "[[PESO]]",
        )
        if any(marcador in template for marcador in marcadores_dados_fisicos):
            try:
                _, medidas, peso = _partes_nome_producao(image_path.name)
            except (TypeError, ValueError):
                # O módulo antigo só incluía as medidas quando conseguia
                # extraí-las do nome da imagem; a falta delas não bloqueava
                # a preparação do prompt.
                for marcador in marcadores_dados_fisicos:
                    template = re.sub(
                        rf"(?m)^[^\n]*{re.escape(marcador)}[^\n]*(?:\n|$)",
                        "",
                        template,
                    )
            else:
                partes_medidas = medidas.split("x")
                dimensoes = []
                for indice in range(3):
                    if indice < len(partes_medidas) and partes_medidas[indice]:
                        dimensoes.append(f"{partes_medidas[indice]} cm")
                    else:
                        dimensoes.append("não informada no nome da imagem")
                substituicoes.update(
                    {
                        "[[ALTURA]]": dimensoes[0],
                        "[[LARGURA]]": dimensoes[1],
                        "[[ESPESSURA]]": dimensoes[2],
                        "[[PESO]]": peso or "não informado no nome da imagem",
                    }
                )

        for marcador, valor in substituicoes.items():
            if valor:
                template = template.replace(marcador, valor)
            else:
                template = re.sub(
                    rf"(?m)^[^\n]*{re.escape(marcador)}[^\n]*(?:\n|$)",
                    "",
                    template,
                )

        marcadores_nao_reconhecidos = re.findall(
            r"\[\[[A-Z_]+\]\]",
            template,
        )
        if marcadores_nao_reconhecidos:
            raise ValueError(
                "O modelo contém marcador(es) sem dado correspondente: "
                + ", ".join(sorted(set(marcadores_nao_reconhecidos)))
            )

        template = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", template)
        proporcao = ler_proporcao(campo(0))
        if proporcao not in {"3:4", "1:1", "4:5", "9:16", "16:9"}:
            proporcao = ""
        if proporcao:
            return (
                f"{template.strip()}\n\n"
                f"Proporção escolhida no Cadastro: {proporcao}."
            )
        return template.strip()

    def _prepare_image_prompt(self, image_path: Path, variant: str) -> None:
        if not image_path.is_file():
            QMessageBox.warning(
                self,
                "Imagem indisponível",
                "O arquivo de imagem selecionado não está mais disponível.",
            )
            return

        try:
            prompt = self._build_image_prompt(image_path, variant)
        except (OSError, TypeError, ValueError) as exc:
            QMessageBox.warning(
                self,
                "Prompt de imagem indisponível",
                str(exc),
            )
            return
        nomes_variantes = {
            "capa": "capa principal",
            "uso": "produto em uso",
            "detalhe": "detalhes do produto",
        }
        finalidade = nomes_variantes.get(variant, "capa principal")
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Prompt · {finalidade}")
        dialog.resize(720, 700)

        layout = QVBoxLayout(dialog)
        preview = QLabel()
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setMinimumHeight(250)
        preview.setMaximumHeight(360)
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            preview.setText("Prévia da imagem indisponível.")
        else:
            preview.setPixmap(
                pixmap.scaled(
                    QSize(680, 300),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        layout.addWidget(preview)

        prompt_field = QPlainTextEdit()
        prompt_field.setPlainText(prompt)
        prompt_field.setMinimumHeight(220)
        prompt_field.setToolTip("Prompt preenchido com os dados disponíveis do produto.")
        layout.addWidget(prompt_field, 1)

        actions = QHBoxLayout()
        copy_prompt_button = QPushButton("Copiar prompt")
        copy_prompt_button.setToolTip("Copia o texto do prompt.")

        def copy_prompt(_checked: bool = False) -> None:
            QApplication.clipboard().setText(prompt_field.toPlainText())

        copy_prompt_button.clicked.connect(copy_prompt)

        copy_image_button = QPushButton("Copiar imagem")
        copy_image_button.setToolTip(
            "Copia a imagem para colar em outro aplicativo."
        )

        def copy_image(_checked: bool = False) -> None:
            if pixmap.isNull():
                return
            QApplication.clipboard().setPixmap(pixmap)

        copy_image_button.clicked.connect(copy_image)
        copy_image_button.setEnabled(not pixmap.isNull())

        copy_directory_button = QPushButton("Copiar diretório")
        copy_directory_button.setToolTip(
            "Copia somente a pasta da imagem, sem o nome do arquivo."
        )

        def copy_directory(_checked: bool = False) -> None:
            QApplication.clipboard().setText(
                str(image_path.resolve().parent)
            )

        copy_directory_button.clicked.connect(copy_directory)

        close_button = QPushButton("Fechar")
        close_button.clicked.connect(
            lambda _checked=False: dialog.accept()
        )
        actions.addWidget(copy_prompt_button)
        actions.addWidget(copy_image_button)
        actions.addWidget(copy_directory_button)
        actions.addStretch(1)
        actions.addWidget(close_button)
        layout.addLayout(actions)
        dialog.exec()

    @Slot()
    def open_produced_video(self) -> None:
        video = getattr(self, "video_output_path", None)
        if video and video.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(video.resolve())))

    def _video_preview_state_changed(self, state) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_video_button.setText("Pausar")
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.play_video_button.setText("Continuar")
        else:
            self.play_video_button.setText("Reproduzir")

    def _video_preview_error(self, _error, error_text: str) -> None:
        self.video_status.setText("Não foi possível reproduzir a prévia.")
        self.play_video_button.setText("Reproduzir")
        if error_text:
            self.show_log(f"Falha na prévia do vídeo: {error_text}")

    def toggle_video_preview(self) -> None:
        video = getattr(self, "video_output_path", None)
        if not video or not video.is_file():
            self.video_status.setText("Nenhum vídeo disponível.")
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

    def _allowed_sale_options(self) -> list[str]:
        if not self.current_row:
            return []
        config = parse_tipo_kit(str(self.current_row[7]))
        tipo = config.get("TIPO", "").upper()
        if tipo == "KIT":
            pecas = config.get("PECAS", "")
            return [f"Kit: {pecas}"] if pecas else []

        allowed = ["Peça única"]
        if config.get("KIT", "NO").upper() == "YES":
            pecas = config.get("PECAS", "")
            if pecas:
                allowed.append(f"Kit: {pecas}")
        return allowed

    def _configure_sale_options(self) -> None:
        permitidas = self._allowed_sale_options()
        marcadas_antes = {
            self.kit_options.item(index).text():
            self.kit_options.item(index).checkState() == Qt.CheckState.Checked
            for index in range(self.kit_options.count())
        }
        self.kit_options.clear()
        for forma in permitidas:
            item = QListWidgetItem(forma)
            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
            )
            item.setCheckState(
                Qt.CheckState.Checked
                if marcadas_antes.get(forma, True)
                else Qt.CheckState.Unchecked
            )
            self.kit_options.addItem(item)

    def selected_kit_options(self) -> list[str]:
        return [
            self.kit_options.item(index).text()
            for index in range(self.kit_options.count())
            if self.kit_options.item(index).checkState()
            == Qt.CheckState.Checked
        ]

    def open_product_folder(self) -> None:
        if not self.current_row:
            return

        pasta = Path(str(self.current_row[2]))
        if not pasta.exists():
            QMessageBox.warning(
                self,
                "Pasta não encontrada",
                f"A pasta do produto não existe:\n{pasta}",
            )
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(pasta.resolve())))

    def delete_current(self) -> None:
        if not self.current_row:
            return

        resposta = QMessageBox.question(
            self,
            "Confirmar",
            f"Apagar o cadastro de {self.current_row[0]}?\n\n"
            "A pasta e os arquivos continuarão no disco.",
        )
        if resposta == QMessageBox.StandardButton.Yes:
            apagar_entrada(str(self.current_row[0]))
            self.refresh()

    def delete_folder_and_entry(self) -> None:
        if not self.current_row:
            return

        produto = str(self.current_row[0] or "").strip()
        caminho = str(self.current_row[2] or "").strip()
        if not produto or not caminho:
            QMessageBox.warning(
                self,
                "Caminho inválido",
                "O cadastro não tem um caminho de pasta válido. "
                "Nada foi apagado.",
            )
            return

        caminho_bruto = Path(caminho).expanduser()
        if not caminho_bruto.is_absolute():
            QMessageBox.warning(
                self,
                "Caminho inválido",
                "O caminho registrado não é absoluto. Nada foi apagado.",
            )
            return
        if caminho_bruto.is_symlink():
            QMessageBox.warning(
                self,
                "Pasta protegida",
                "O caminho registrado é um link simbólico. "
                "Por segurança, nada foi apagado.",
            )
            return

        try:
            pasta = caminho_bruto.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            QMessageBox.warning(
                self,
                "Pasta não encontrada",
                f"Não foi possível localizar a pasta:\n{caminho}\n\n{exc}",
            )
            return
        if not pasta.is_dir():
            QMessageBox.warning(
                self,
                "Pasta inválida",
                f"O caminho não aponta para uma pasta:\n{pasta}\n\n"
                "Nada foi apagado.",
            )
            return
        if pasta == Path(pasta.anchor).resolve() or pasta.is_mount():
            QMessageBox.warning(
                self,
                "Pasta protegida",
                "Não é permitido apagar uma raiz ou ponto de montagem. "
                "Nada foi apagado.",
            )
            return

        home = Path.home().resolve()
        app_root = Path(__file__).resolve().parents[2]
        appdata_root = Path(str(appdata.pasta_raiz)).expanduser().resolve()
        if (
            _path_contains(pasta, home)
            or _path_contains(pasta, app_root)
            or _path_contains(app_root, pasta)
            or _path_contains(pasta, appdata_root)
            or _path_contains(appdata_root, pasta)
        ):
            QMessageBox.warning(
                self,
                "Pasta protegida",
                "O caminho coincide com, contém ou está dentro de uma pasta "
                "protegida do usuário ou do aplicativo. Nada foi apagado.",
            )
            return

        try:
            outras_entradas = ler_entradas()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Não foi possível verificar os cadastros",
                "Não consegui conferir se outros produtos usam essa pasta. "
                f"Nada foi apagado.\n\n{exc}",
            )
            return
        for entrada in outras_entradas:
            if str(entrada[0] or "").strip() == produto:
                continue
            outro_caminho = str(entrada[2] or "").strip()
            if not outro_caminho:
                continue
            try:
                outra_pasta = Path(outro_caminho).expanduser().resolve()
            except (OSError, RuntimeError):
                continue
            if outra_pasta == pasta or _path_contains(pasta, outra_pasta):
                QMessageBox.warning(
                    self,
                    "Pasta compartilhada",
                    "A pasta contém o caminho registrado para outro produto "
                    f"({entrada[0]}). Nada foi apagado.",
                )
                return

        mover_para_lixeira = getattr(QFile, "moveToTrash", None)
        if not callable(mover_para_lixeira):
            QMessageBox.warning(
                self,
                "Lixeira indisponível",
                "Esta instalação não oferece a função de enviar pastas à "
                "Lixeira. Nenhum arquivo ou cadastro foi apagado.",
            )
            return

        resposta = QMessageBox.question(
            self,
            "Apagar pasta e cadastro?",
            (
                f"Produto: {produto}\n"
                f"Pasta: {pasta}\n\n"
                "A pasta inteira e tudo que estiver dentro dela serão "
                "enviados à Lixeira. O cadastro também será removido de "
                "A_ENTRADA. Esta ação não apaga permanentemente, mas os "
                "arquivos deixarão o local atual.\n\n"
                "Deseja continuar?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        try:
            resultado_lixeira = mover_para_lixeira(str(pasta))
            if isinstance(resultado_lixeira, (tuple, list)):
                movida = (
                    bool(resultado_lixeira[0])
                    if resultado_lixeira
                    else False
                )
            else:
                movida = bool(resultado_lixeira)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Não foi possível enviar à Lixeira",
                "A pasta e o cadastro foram mantidos.\n\n"
                f"Detalhes: {exc}",
            )
            return
        if not movida:
            QMessageBox.warning(
                self,
                "Não foi possível enviar à Lixeira",
                "A pasta e o cadastro foram mantidos. Nenhum arquivo foi "
                "apagado permanentemente.",
            )
            return

        try:
            apagar_entrada(produto)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Cadastro não removido",
                "A pasta foi enviada à Lixeira, mas não foi possível remover "
                "o cadastro. Não esvazie a Lixeira até resolver a situação.\n\n"
                f"Detalhes: {exc}",
            )
            self.refresh()
            return
        self.refresh()

    def run_production(self) -> None:
        if not self.current_row:
            return

        formas_venda = self.selected_kit_options()
        if not formas_venda:
            QMessageBox.warning(
                self,
                "Formas de venda",
                "Marque ao menos uma forma de venda permitida pelo Cadastro.",
            )
            return

        self.run_button.setEnabled(False)
        self.progress.show()
        self._show_production_overlay()
        self.show_log(
            f"Preparando criação de {self.current_row[0]} "
            f"na pasta {self.current_row[2]}"
        )
        configuracao = appdata.ler_config()
        marca = configuracao.get("marca", {})
        if not isinstance(marca, dict):
            marca = {}
        self.start_task(
            executar_producao,
            self.current_row,
            float(self.shadow.currentText()),
            float(self.music.currentText()),
            "manifesto do cadastro",
            self.measure_type.currentText(),
            formas_venda,
            logo_nome=self._selected_resource(self.logo_choice),
            fundo_capa_nome=self._selected_resource(self.capa_choice),
            fundo_medida_nome=self._configured_measure_background,
            musica_nome=self._selected_resource(self.music_track_choice),
            perfil_social=str(marca.get("perfil_social") or "").strip(),
            url_loja=str(marca.get("url_loja") or "").strip(),
            on_done=self.production_done,
            on_error=self.production_failed,
            on_cancel=self.production_cancelled,
        )

    def show_log(self, message: str) -> None:
        texto = str(message).strip()
        if not texto:
            return
        if self._production_overlay is not None:
            self._production_overlay.set_mensagem(texto)
        self.log.appendPlainText(texto)
        self.log.ensureCursorVisible()
        super().show_log(texto)

    def production_done(self, result: object) -> None:
        self._close_production_overlay()
        self.run_button.setEnabled(True)
        self.progress.hide()
        self._refresh_result_gallery()
        self.log.appendPlainText(f"Produção concluída: {result}")
        self.results_requested.emit()

    def production_failed(self, error: str) -> None:
        self._close_production_overlay()
        self.run_button.setEnabled(True)
        self.progress.hide()
        self.log.appendPlainText(error)
        QMessageBox.critical(self, "Erro na produção", error)

    def production_cancelled(self, message: str) -> None:
        self._close_production_overlay()
        self.run_button.setEnabled(True)
        self.progress.hide()
        self.log.appendPlainText(message)
        QMessageBox.warning(self, "Produção cancelada", message)


# Compatibilidade para módulos históricos que ainda importam ProductionTab.
ProductionTab = CreationController