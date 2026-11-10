"""Montagem visual independente para a aba Resultados do aplicativo."""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from _APP_.Configuracao.Prompts.App_Prompts_PySide6 import (
    IMAGE_PROMPT_SPECS,
    ImagePromptEditor,
)
from _FERRAMENTAS_.ia_prompt_catalogo import (
    carregar_prompts_imagem,
    carregar_prompts_imagem_padrao,
)

PASTA_PRE_MARKETPLACE = "F_pre_marketplace"
PASTA_MARKETPLACE = "G_marketplace"

RESULTS_STYLE = """
QWidget#resultsContent {
    font-size: 12px;
}
QFrame#resultsPanel {
    background: #15253A;
    border: 1px solid #2D435D;
    border-radius: 5px;
}
QFrame#resultsPanel QLabel {
    background: transparent;
    border: none;
}
QFrame#resultsPanel QListWidget {
    background: #17283F;
    border: none;
    padding: 0;
}
QFrame#resultsPanel QPushButton {
    min-height: 24px;
    padding: 3px 8px;
}
QWidget#resultsContent QComboBox {
    min-height: 24px;
    padding: 3px 24px 3px 7px;
    background: #17283F;
    border: 1px solid #46627E;
    border-radius: 4px;
}
QWidget#resultsContent QComboBox::drop-down {
    width: 22px;
    background: #2B415B;
    border: none;
    border-left: 1px solid #46627E;
    border-top-right-radius: 3px;
    border-bottom-right-radius: 3px;
}
QWidget#resultsContent QComboBox::drop-down:hover {
    background: #365471;
}
QWidget#resultsContent QComboBox QAbstractItemView {
    background: #20334B;
    color: #F3F6FA;
    border: 1px solid #46627E;
    selection-background-color: #1D7E7A;
    selection-color: #F3F6FA;
}
QWidget#resultsContent QPushButton::menu-indicator {
    image: none;
    width: 0;
}
QWidget#resultsContent QMenu {
    background: #20334B;
    color: #F3F6FA;
    border: 1px solid #46627E;
}
QWidget#resultsContent QMenu::item:selected {
    background: #1D7E7A;
}
"""


def _open_image_prompt_editor(parent: QWidget) -> None:
    """Abre os três modelos de imagem com o mesmo editor usado em Prompts."""
    try:
        defaults = carregar_prompts_imagem_padrao()
    except (OSError, TypeError, ValueError) as exc:
        QMessageBox.warning(
            parent,
            "Prompts de imagem indisponíveis",
            f"Não foi possível carregar os modelos padrão:\n{exc}",
        )
        return

    load_error = ""
    try:
        prompts = carregar_prompts_imagem()
    except (OSError, TypeError, ValueError) as exc:
        prompts = dict(defaults)
        load_error = (
            "Não foi possível carregar os modelos personalizados. "
            f"Os padrões estão sendo exibidos: {exc}"
        )

    dialog = QDialog(parent)
    dialog.setWindowTitle("Editar prompts das imagens")
    dialog.setMinimumSize(680, 460)
    dialog.resize(840, 580)
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(8)

    note = QLabel(
        "Edite Capa principal, Produto em uso e Detalhes do produto. "
        "Salve cada modelo pelo botão de disquete; ele ficará no AppData e "
        "também será usado pela aba Prompts."
    )
    note.setWordWrap(True)
    layout.addWidget(note)

    tabs = QTabWidget()
    for prompt_id, title in IMAGE_PROMPT_SPECS:
        editor = ImagePromptEditor(
            prompt_id,
            title,
            prompts.get(prompt_id, defaults[prompt_id]),
            defaults[prompt_id],
            load_error,
        )
        tabs.addTab(editor, title)
    layout.addWidget(tabs, 1)

    close_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    close_button = close_buttons.button(QDialogButtonBox.StandardButton.Close)
    if close_button is not None:
        close_button.clicked.connect(dialog.accept)
    layout.addWidget(close_buttons)
    dialog.exec()


def build_results_page(controller, resources: QWidget) -> QWidget:
    """Cria a página de saídas usando o controlador de Criação para as ações."""
    page = QScrollArea()
    page.setWidgetResizable(True)
    page.setFrameShape(QFrame.Shape.NoFrame)

    content = QWidget()
    content.setObjectName("resultsContent")
    content.setStyleSheet(RESULTS_STYLE)
    layout = QVBoxLayout(content)
    layout.setContentsMargins(8, 6, 8, 8)
    layout.setSpacing(10)

    controller.result_summary = QLabel(
        "Os arquivos existentes ou recém-produzidos aparecerão aqui."
    )
    controller.result_summary.setWordWrap(True)
    layout.addWidget(controller.result_summary)

    # Galeria única: o seletor mostra apenas uma das quatro pastas por vez.
    controller.sample_gallery = controller._new_source_gallery()
    controller.white_gallery = controller._new_source_gallery()
    controller.cover_background_gallery = controller._new_source_gallery()
    controller.measure_gallery = controller._new_source_gallery()
    image_galleries = (
        ("Sem fundo", controller.sample_gallery),
        ("Fundo branco", controller.white_gallery),
        ("Fundo capa", controller.cover_background_gallery),
        ("Medidas", controller.measure_gallery),
    )
    for _title, gallery in image_galleries:
        gallery.setGridSize(QSize(220, 228))
        gallery.setMinimumHeight(252)
        gallery.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

    gallery_panel = QFrame()
    gallery_panel.setObjectName("resultsPanel")
    gallery_panel.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Expanding,
    )
    gallery_layout = QVBoxLayout(gallery_panel)
    gallery_layout.setContentsMargins(9, 8, 9, 8)
    gallery_layout.setSpacing(6)

    gallery_toolbar = QHBoxLayout()
    gallery_toolbar.setContentsMargins(0, 0, 0, 0)
    gallery_toolbar.setSpacing(7)
    gallery_heading = QLabel("Imagens da produção")
    gallery_heading.setStyleSheet("font-weight: 600;")
    gallery_toolbar.addWidget(gallery_heading)

    controller.result_gallery_selector = QComboBox()
    controller.result_gallery_selector.setAccessibleName(
        "Selecionar pasta de imagens"
    )
    controller.result_gallery_selector.setToolTip(
        "Escolha qual pasta de imagens mostrar."
    )
    for title, _gallery in image_galleries:
        controller.result_gallery_selector.addItem(title)
    gallery_toolbar.addWidget(controller.result_gallery_selector, 1)

    controller.edit_image_prompts_button = QPushButton("Editar prompts")
    controller.edit_image_prompts_button.setToolTip(
        "Editar Capa, Produto em uso e Detalhes do produto."
    )
    controller.edit_image_prompts_button.clicked.connect(
        lambda _checked=False: _open_image_prompt_editor(content)
    )
    gallery_toolbar.addWidget(controller.edit_image_prompts_button)
    gallery_layout.addLayout(gallery_toolbar)

    controller.result_gallery_stack = QStackedWidget()
    controller.result_gallery_stack.setMinimumHeight(252)
    controller.result_gallery_stack.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Expanding,
    )
    for _title, gallery in image_galleries:
        controller.result_gallery_stack.addWidget(gallery)
    controller.result_gallery_selector.currentIndexChanged.connect(
        controller.result_gallery_stack.setCurrentIndex
    )
    gallery_layout.addWidget(controller.result_gallery_stack, 1)

    # A prévia de vídeo fica ao lado da galeria sem competir com as miniaturas.
    video_section = QFrame()
    video_section.setObjectName("resultsPanel")
    video_section.setMinimumWidth(180)
    video_section.setMaximumWidth(230)
    video_layout = QVBoxLayout(video_section)
    video_layout.setContentsMargins(9, 8, 9, 8)
    video_layout.setSpacing(4)
    video_heading = QLabel("Vídeo Shopee")
    video_heading.setStyleSheet("font-weight: 600;")
    video_layout.addWidget(video_heading)

    controller.video_preview = QVideoWidget()
    controller.video_preview.setMinimumSize(160, 90)
    controller.video_preview.setMaximumHeight(112)
    controller.video_preview.setToolTip(
        "Prévia do vídeo convertido. Use Reproduzir para assistir."
    )
    controller.video_preview_player = QMediaPlayer(controller)
    controller.video_preview_audio = QAudioOutput(controller)
    controller.video_preview_audio.setVolume(0.35)
    controller.video_preview_player.setAudioOutput(
        controller.video_preview_audio
    )
    controller.video_preview_player.setVideoOutput(controller.video_preview)
    controller.video_preview_player.playbackStateChanged.connect(
        controller._video_preview_state_changed
    )
    controller.video_preview_player.errorOccurred.connect(
        controller._video_preview_error
    )
    video_layout.addWidget(controller.video_preview)

    controller.video_status = QLabel("Nenhum vídeo disponível.")
    controller.video_status.setWordWrap(True)
    controller.video_status.setMaximumHeight(34)
    video_layout.addWidget(controller.video_status)

    video_actions = QHBoxLayout()
    video_actions.setSpacing(4)
    controller.play_video_button = QPushButton("Reproduzir")
    controller.play_video_button.setEnabled(False)
    controller.play_video_button.clicked.connect(
        controller.toggle_video_preview
    )
    controller.open_video_button = QPushButton("Abrir")
    controller.open_video_button.setEnabled(False)
    controller.open_video_button.setToolTip(
        "Abre o vídeo no reprodutor padrão do sistema."
    )
    controller.open_video_button.clicked.connect(controller.open_produced_video)
    video_actions.addWidget(controller.play_video_button, 1)
    video_actions.addWidget(controller.open_video_button)
    video_layout.addLayout(video_actions)

    media_row = QHBoxLayout()
    media_row.setContentsMargins(0, 0, 0, 0)
    media_row.setSpacing(10)
    media_row.addWidget(gallery_panel, 1)
    media_row.addWidget(video_section)
    layout.addLayout(media_row)

    # Faixa final: preparação F e cópias aprovadas G lado a lado.
    workflow = QHBoxLayout()
    workflow.setContentsMargins(0, 0, 0, 0)
    workflow.setSpacing(16)

    pre_section = QFrame()
    pre_section.setObjectName("resultsPanel")
    pre_layout = QVBoxLayout(pre_section)
    pre_layout.setContentsMargins(9, 8, 9, 8)
    pre_layout.setSpacing(6)
    pre_heading = QLabel("F · Pré-marketplace")
    pre_heading.setStyleSheet("font-weight: 600;")
    pre_layout.addWidget(pre_heading)

    pre_actions = QHBoxLayout()
    pre_actions.setSpacing(5)
    controller.add_images_to_pre_button = QPushButton("Adicionar")
    controller.add_images_to_pre_button.setToolTip(
        "Adicionar imagens do computador à pasta F."
    )
    controller.add_images_to_pre_button.clicked.connect(
        controller.import_images_to_premarketplace
    )
    controller.open_pre_marketplace_button = QPushButton("Abrir F")
    controller.open_pre_marketplace_button.setToolTip(
        "Abre a pasta F no Explorador de Arquivos."
    )
    controller.open_pre_marketplace_button.clicked.connect(
        lambda _checked=False: controller._open_marketplace_folder(
            PASTA_PRE_MARKETPLACE
        )
    )
    controller.pre_selection_menu_button = QPushButton("Seleção  ▾")
    selection_menu = QMenu(controller.pre_selection_menu_button)
    select_all_action = selection_menu.addAction("Selecionar todas")
    select_all_action.triggered.connect(
        lambda _checked=False: controller._set_pre_marketplace_checks(True)
    )
    clear_selection_action = selection_menu.addAction("Limpar seleção")
    clear_selection_action.triggered.connect(
        lambda _checked=False: controller._set_pre_marketplace_checks(False)
    )
    controller.pre_selection_menu_button.setMenu(selection_menu)
    controller.remove_pre_selected_button = QPushButton("Remover")
    controller.remove_pre_selected_button.setEnabled(False)
    controller.remove_pre_selected_button.setToolTip(
        "Remove os arquivos marcados em F; não altera fontes fora de F nem G."
    )
    controller.remove_pre_selected_button.clicked.connect(
        controller.remove_selected_from_premarketplace
    )
    for button in (
        controller.add_images_to_pre_button,
        controller.open_pre_marketplace_button,
        controller.pre_selection_menu_button,
        controller.remove_pre_selected_button,
    ):
        pre_actions.addWidget(button)
    pre_actions.addStretch(1)
    pre_layout.addLayout(pre_actions)

    resources_heading = QLabel("Recursos da imagem")
    resources_heading.setStyleSheet("font-weight: 600;")
    pre_layout.addWidget(resources_heading)
    pre_layout.addWidget(resources)

    for combo in (controller.logo_choice,):
        combo.setMinimumWidth(0)
        combo.setMinimumContentsLength(8)
        combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )

    controller.pre_marketplace_gallery = controller._new_gallery(wrapping=True)
    controller.pre_marketplace_gallery.setSelectionMode(
        QAbstractItemView.SelectionMode.NoSelection
    )
    controller.pre_marketplace_gallery.setGridSize(QSize(176, 180))
    controller.pre_marketplace_gallery.setMinimumHeight(190)
    pre_layout.addWidget(controller.pre_marketplace_gallery)

    controller.pre_marketplace_status = QLabel(
        "Clique na imagem para configurar os recursos no pop-up. Marque as "
        "imagens que deseja concluir em G."
    )
    controller.pre_marketplace_status.setWordWrap(True)
    pre_layout.addWidget(controller.pre_marketplace_status)
    controller.finish_marketplace_button = QPushButton(
        "Concluir e enviar para G"
    )
    controller.finish_marketplace_button.setToolTip(
        "Usa os ajustes salvos para cada imagem, reduz as cópias para no "
        "máximo 2.000.000 bytes por imagem e grava os arquivos finais em G."
    )
    controller.finish_marketplace_button.clicked.connect(
        controller.finalize_marketplace_edits
    )
    controller.finish_marketplace_button.setEnabled(False)
    pre_layout.addWidget(controller.finish_marketplace_button)
    workflow.addWidget(pre_section, 3)

    final_section = QFrame()
    final_section.setObjectName("resultsPanel")
    final_layout = QVBoxLayout(final_section)
    final_layout.setContentsMargins(9, 8, 9, 8)
    final_layout.setSpacing(6)
    final_heading = QLabel("G · Marketplace pronto")
    final_heading.setStyleSheet("font-weight: 600;")
    final_layout.addWidget(final_heading)

    final_actions = QHBoxLayout()
    controller.open_marketplace_button = QPushButton("Abrir G")
    controller.open_marketplace_button.clicked.connect(
        lambda _checked=False: controller._open_marketplace_folder(
            PASTA_MARKETPLACE
        )
    )
    final_actions.addWidget(controller.open_marketplace_button)
    final_actions.addStretch(1)
    final_layout.addLayout(final_actions)

    controller.marketplace_gallery = controller._new_gallery(wrapping=True)
    controller.marketplace_gallery.setGridSize(QSize(176, 150))
    controller.marketplace_gallery.setMinimumHeight(190)
    final_layout.addWidget(controller.marketplace_gallery)
    final_layout.addWidget(
        QLabel(
            "G guarda cópias finais. Nenhum envio ou publicação externa é feito."
        )
    )
    workflow.addWidget(final_section, 2)
    layout.addLayout(workflow)

    page.setWidget(content)
    return page
