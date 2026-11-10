"""Tela de cadastro de produtos da aplicação desktop PySide6."""


from pathlib import Path
from threading import Event
from time import monotonic
from typing import Callable

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtGui import (
    QDesktopServices,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from _APP_.PySide6_core import (
    BackgroundMixin,
    DEFAULT_PRODUCTS_DIR,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    listar_imagens,
    reconhecer_microfone as _legacy_reconhecer_microfone,
    salvar_cadastro_task,
)
from .Microfone_PySide6 import reconhecer_microfone
from _CONFIGURA_ import COR_ACENTO_BORDA, COR_BORDA_CLARA
from _LOGS_ import log


class CheckableComboBox(QComboBox):
    """QComboBox com seleção múltipla, equivalente ao multiselect do Streamlit."""

    def __init__(self, items: list[str]):
        super().__init__()
        model = QStandardItemModel(self)
        for text in items:
            item = QStandardItem(text)
            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
            )
            item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
            model.appendRow(item)
        self.setModel(model)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setPlaceholderText("Selecione os acabamentos")
        self.view().pressed.connect(self._toggle_item)
        self._refresh_text()

    def _toggle_item(self, index) -> None:
        item = self.model().itemFromIndex(index)
        state = (
            Qt.CheckState.Unchecked
            if item.checkState() == Qt.CheckState.Checked
            else Qt.CheckState.Checked
        )
        item.setCheckState(state)
        self._refresh_text()

    def _refresh_text(self) -> None:
        self.lineEdit().setText(", ".join(self.checked_items()))

    def checked_items(self) -> list[str]:
        return [
            self.model().item(index).text()
            for index in range(self.model().rowCount())
            if self.model().item(index).checkState() == Qt.CheckState.Checked
        ]

    def checked_text(self) -> str:
        return ", ".join(self.checked_items())


class MediaGallery(QWidget):
    """Galeria horizontal com todas as imagens e vídeos encontrados."""

    def __init__(self, title: str = "Mídias encontradas"):
        super().__init__()
        self.source_dir = Path()
        self.setMinimumHeight(185)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(QLabel(f"<b>{title}</b>"))

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.container = QWidget()
        self.container.setMinimumHeight(145)
        self.layout = QHBoxLayout(self.container)
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(8)
        self.scroll.setWidget(self.container)
        self.scroll.setMinimumHeight(150)
        root.addWidget(self.scroll)
        self.show_empty()

    def clear(self) -> None:
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def show_empty(self) -> None:
        self.clear()
        self.layout.addWidget(QLabel("Nenhuma imagem ou vídeo encontrado."))
        self.layout.addStretch()
        self.container.adjustSize()

    def update_files(self, files: list[str], source_dir: str) -> None:
        self.clear()
        self.source_dir = Path(source_dir)
        if not files:
            self.show_empty()
            return

        for name in files:
            path = self.source_dir / name
            card = QWidget()
            card.setFixedSize(160, 140)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(2, 2, 2, 2)
            card_layout.setSpacing(2)
            if path.suffix.lower() in VIDEO_EXTENSIONS:
                preview = QPushButton(f"▶\nVÍDEO\n{name}")
                preview.setToolTip(f"Abrir vídeo: {name}")
                preview.setFixedSize(150, 105)
                preview.clicked.connect(
                    lambda checked=False, file_path=path: QDesktopServices.openUrl(
                        QUrl.fromLocalFile(str(file_path))
                    )
                )
            else:
                preview = QLabel()
                preview.setFixedSize(150, 105)
                preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
                pixmap = QPixmap(str(path))
                if pixmap.isNull():
                    preview.setText("sem prévia")
                else:
                    preview.setPixmap(
                        pixmap.scaled(
                            145,
                            100,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
            card_layout.addWidget(preview)
            caption = QLabel(name)
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            caption.setWordWrap(True)
            caption.setFixedWidth(150)
            card_layout.addWidget(caption)
            self.layout.addWidget(card)
        self.layout.addStretch()
        self.container.adjustSize()
        self.container.setMinimumWidth(max(180, len(files) * 168 + 12))
        self.container.resize(self.container.sizeHint())


class MeasurementRow(QWidget):
    def __init__(self, filename: str, image_path: Path, title: str = ""):
        super().__init__()
        self.filename = filename
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        preview = QLabel()
        preview.setFixedSize(96, 76)
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = _load_oriented_pixmap(image_path)
        if not pixmap.isNull():
            preview.setPixmap(
                pixmap.scaled(
                    88,
                    68,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            preview.setText("sem prévia")
        layout.addWidget(preview)

        info = QVBoxLayout()
        label = QLabel(f"{title}\n{filename}" if title else filename)
        label.setWordWrap(True)
        label.setToolTip(
            "Arquivo usado neste grupo de medidas. As medidas serão gravadas no produtos.txt."
        )
        info.addWidget(label)
        inputs = QHBoxLayout()
        self.altura = QLineEdit()
        self.largura = QLineEdit()
        self.espessura = QLineEdit()
        self.peso = QLineEdit()
        for widget, placeholder in (
            (self.altura, "Altura"),
            (self.largura, "Largura"),
            (self.espessura, "Espessura"),
            (self.peso, "Peso"),
        ):
            widget.setPlaceholderText(placeholder)
            widget.setMaximumWidth(100)
            widget.setToolTip(
                f"{placeholder} do produto. Informe o valor que será usado no cadastro."
            )
            inputs.addWidget(widget)
        info.addLayout(inputs)
        layout.addLayout(info, 1)

    def values(self) -> tuple[str, str, str, str, str]:
        return (
            self.filename,
            self.altura.text().strip(),
            self.largura.text().strip(),
            self.espessura.text().strip(),
            self.peso.text().strip(),
        )


class CadastroTab(QWidget, BackgroundMixin):
    """Cadastro com configurações à esquerda e mídias/medidas à direita."""

    def __init__(
        self,
        on_saved: Callable[[], None],
        on_open_prompts: Callable[[], None] | None = None,
    ):
        QWidget.__init__(self)
        BackgroundMixin.__init__(self)
        self.on_saved = on_saved
        self.on_open_prompts = on_open_prompts
        self.measurement_rows: list[MeasurementRow] = []
        self.files: list[str] = []
        self.setObjectName("CadastroTab")
        self.build_ui()

    def build_ui(self) -> None:
        root = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        settings = QWidget()
        settings_layout = QVBoxLayout(settings)
        settings_layout.setContentsMargins(4, 4, 8, 4)

        basic = QGroupBox("Configurações do produto")
        basic_layout = QVBoxLayout(basic)
        basic_layout.setContentsMargins(8, 8, 8, 8)
        basic_layout.setSpacing(4)
        self.product_name = QLineEdit()
        self.product_name.setToolTip("Nome usado para criar o cadastro do produto.")
        self.source_dir = QLineEdit()
        self.source_dir.setToolTip(
            "Pasta que contém as imagens e os vídeos do produto."
        )
        self.description = QTextEdit()
        self.description.setFixedHeight(170)
        self.description.setToolTip(
            "Descrição do produto. Você pode escrever várias linhas ou usar o microfone."
        )
        self.usage = QTextEdit()
        self.usage.setFixedHeight(170)
        self.usage.setToolTip(
            "Explique como o produto pode ser usado. Você pode escrever várias linhas ou usar o microfone."
        )
        self.accompanies = QLineEdit()
        self.accompanies.setToolTip(
            "Informe o que acompanha o produto. Este campo é texto livre no cadastro original."
        )
        self.finish = CheckableComboBox(
            [
                "lixado",
                "lavado",
                "Vernizado",
                "Impressão a Laiser",
                "Pode ser Estilizado pelo Cliente",
            ]
        )
        self.finish.setToolTip(
            "Selecione um ou mais acabamentos ou trabalhos possíveis para o produto."
        )
        self.proportion = QComboBox()
        self.proportion.addItems(["3:4", "1:1", "4:5", "9:16", "16:9"])
        self.proportion.setToolTip("Proporção usada no processamento das imagens.")
        self.products_dir = QLineEdit(str(DEFAULT_PRODUCTS_DIR))
        self.products_dir.setToolTip(
            "Pasta onde será criada a pasta final do produto cadastrado."
        )

        browse_source = QPushButton("Escolher")
        browse_source.setMaximumWidth(86)
        browse_source.setToolTip("Escolher a pasta que contém as mídias do produto.")
        browse_source.clicked.connect(self.choose_source)
        browse_products = QPushButton("Escolher")
        browse_products.setMaximumWidth(86)
        browse_products.setToolTip("Escolher a pasta de destino do cadastro.")
        browse_products.clicked.connect(self.choose_products_dir)

        def add_labeled_field(
            label: str,
            widget: QWidget,
            button: QPushButton | None = None,
        ) -> None:
            basic_layout.addWidget(QLabel(label))
            row = QHBoxLayout()
            row.addWidget(widget, 1)
            if button:
                row.addWidget(button)
            basic_layout.addLayout(row)

        add_labeled_field("Nome", self.product_name)
        add_labeled_field("Origem", self.source_dir, browse_source)
        add_labeled_field("Destino", self.products_dir, browse_products)
        add_labeled_field("Proporção", self.proportion)
        add_labeled_field("Acompanha", self.accompanies)
        add_labeled_field("Acabamento", self.finish)

        self.usage_mic_button = QPushButton("🎤 Gravar")
        self.usage_mic_button.setMinimumHeight(30)
        self.usage_mic_button.setToolTip(
            "Gravar e transformar em texto o campo 'Como pode ser usado'."
        )
        self.usage_status = QLabel("Pronto para gravar")
        self.usage_mic_button.clicked.connect(
            lambda: self.start_dictation(
                self.usage,
                self.usage_mic_button,
                self.usage_status,
            )
        )
        usage_controls = QHBoxLayout()
        usage_controls.addWidget(self.usage_mic_button)
        usage_controls.addWidget(self.usage_status, 1)
        usage_controls.addStretch()
        usage_row = QVBoxLayout()
        usage_row.addWidget(self.usage)
        usage_row.addLayout(usage_controls)
        usage_label = QLabel("Como pode ser usado:")
        usage_label.setToolTip(self.usage.toolTip())
        basic_layout.addWidget(usage_label)
        basic_layout.addLayout(usage_row)

        self.description_mic_button = QPushButton("🎤 Gravar")
        self.description_mic_button.setMinimumHeight(30)
        self.description_mic_button.setToolTip(
            "Gravar e transformar em texto o campo 'Descrição'."
        )
        self.description_status = QLabel("Pronto para gravar")
        self.description_mic_button.clicked.connect(
            lambda: self.start_dictation(
                self.description,
                self.description_mic_button,
                self.description_status,
            )
        )
        description_controls = QHBoxLayout()
        description_controls.addWidget(self.description_mic_button)
        description_controls.addWidget(self.description_status, 1)
        description_controls.addStretch()
        description_row = QVBoxLayout()
        description_row.addWidget(self.description)
        description_row.addLayout(description_controls)
        description_label = QLabel("Descrição:")
        description_label.setToolTip(self.description.toolTip())
        basic_layout.addWidget(description_label)
        basic_layout.addLayout(description_row)
        settings_layout.addWidget(basic)

        classification = QGroupBox("Classificação")
        classification_layout = QGridLayout(classification)
        self.product_type = QComboBox()
        self.product_type.addItems(["Único", "Kit"])
        self.product_type.setToolTip(
            "Único = um produto com possíveis variações. Kit = conjunto de peças."
        )
        self.variations = QComboBox()
        self.variations.addItems([str(value) for value in range(1, 10)])
        self.variations.setToolTip(
            "1 = todas as fotos compartilham as mesmas medidas. "
            "2 ou mais = cada variação terá seu grupo de medidas."
        )
        self.also_kit = QComboBox()
        self.also_kit.addItems(["Não", "Sim"])
        self.also_kit.setToolTip(
            "O produto único também será vendido como conjunto?"
        )
        self.kit_pieces = QComboBox()
        self.kit_pieces.addItems([str(value) for value in range(2, 11)])
        self.kit_pieces.setToolTip(
            "Quantidade de fotos de peças individuais esperadas em cada kit."
        )
        self.kit_variation = QComboBox()
        self.kit_variation.addItems(
            ["Sem variação", "Tamanho", "Cor", "Peso", "Mista"]
        )
        self.kit_variation.setToolTip(
            "Indicação organizacional da variação das peças do kit. "
            "Não altera a quantidade de campos."
        )
        self.kit_count = QComboBox()
        self.kit_count.addItems([str(value) for value in range(1, 11)])
        self.kit_count.setToolTip(
            "Quantidade de grupos completos de fotos do kit."
        )
        self.variation_label = QLabel("Variações")
        self.also_kit_label = QLabel("Também em kit")
        self.kit_pieces_label = QLabel("Peças no kit")
        self.kit_variation_label = QLabel("Variação do kit")
        self.kit_count_label = QLabel("Quantidade de kits")
        fields = [
            ("Tipo", self.product_type),
            (self.variation_label, self.variations),
            (self.also_kit_label, self.also_kit),
            (self.kit_pieces_label, self.kit_pieces),
            (self.kit_variation_label, self.kit_variation),
            (self.kit_count_label, self.kit_count),
        ]
        for index, (label, widget) in enumerate(fields):
            row = index // 2
            column = (index % 2) * 2
            classification_layout.addWidget(
                QLabel(label) if isinstance(label, str) else label,
                row,
                column,
            )
            classification_layout.addWidget(widget, row, column + 1)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        classification_layout.addWidget(self.summary, 3, 0, 1, 4)
        settings_layout.addWidget(classification)

        for widget in (
            self.product_type,
            self.also_kit,
            self.kit_variation,
        ):
            widget.currentTextChanged.connect(self.rebuild_measurements)
        for widget in (self.variations, self.kit_pieces, self.kit_count):
            widget.currentTextChanged.connect(self.rebuild_measurements)
        self.product_type.currentTextChanged.connect(
            self.update_classification_visibility
        )
        self.also_kit.currentTextChanged.connect(
            self.update_classification_visibility
        )
        self.update_classification_visibility()

        actions = QHBoxLayout()
        self.refresh_button = QPushButton("Atualizar mídias")
        self.refresh_button.setMaximumWidth(130)
        self.refresh_button.setToolTip(
            "Ler novamente a pasta de origem, ordenar as mídias e reconstruir os grupos."
        )
        self.refresh_button.clicked.connect(self.refresh_files)
        self.save_button = QPushButton("Processar cadastro")
        self.save_button.setMaximumWidth(145)
        self.save_button.setToolTip(
            "Copiar as mídias, salvar as medidas e gerar o produtos.txt do cadastro."
        )
        self.save_button.clicked.connect(self.save_product)
        actions.addWidget(self.refresh_button)
        actions.addWidget(self.save_button)
        if self.on_open_prompts:
            prompts_button = QPushButton("Prompts")
            prompts_button.setMaximumWidth(82)
            prompts_button.setToolTip(
                "Abrir os prompts pré-configurados usados no cadastro e na produção."
            )
            prompts_button.clicked.connect(self.on_open_prompts)
            actions.addWidget(prompts_button)
        actions.addStretch()
        settings_layout.addLayout(actions)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(1000)
        self.log.setFixedHeight(0)
        self.log.hide()
        self.log.setToolTip("Mensagens do processamento e erros do cadastro.")
        settings_layout.addWidget(self.log)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 4, 4, 4)
        self.files_label = QLabel("Nenhuma pasta selecionada")
        self.files_label.setWordWrap(True)
        right_layout.addWidget(self.files_label)
        self.media_gallery = MediaGallery()
        right_layout.addWidget(self.media_gallery)

        measures_label = QLabel("<b>Grupos de variações, kits e medidas</b>")
        measures_label.setToolTip(
            "Cada grupo corresponde às fotos que compartilharão o mesmo conjunto de medidas."
        )
        right_layout.addWidget(measures_label)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.measurement_container = QWidget()
        self.measurement_layout = QVBoxLayout(self.measurement_container)
        self.measurement_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.measurement_container)
        right_layout.addWidget(scroll, 1)

        settings.setMinimumWidth(500)
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        settings_scroll.setWidget(settings)
        splitter.addWidget(settings_scroll)
        splitter.addWidget(right)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([520, 850])

    def choose_source(self) -> None:
        initial_dir = self.source_dir.text().strip() or str(Path.home() / "Downloads")
        if not Path(initial_dir).is_dir():
            initial_dir = str(Path.home() / "Downloads")
        folder = QFileDialog.getExistingDirectory(
            self,
            "Pasta de origem",
            initial_dir,
        )
        if folder:
            self.source_dir.setText(folder)
            self.refresh_files()

    def choose_products_dir(self) -> None:
        initial_dir = self.products_dir.text().strip() or str(Path.home() / "Downloads")
        if not Path(initial_dir).is_dir():
            initial_dir = str(Path.home() / "Downloads")
        folder = QFileDialog.getExistingDirectory(
            self,
            "Pasta de destino",
            initial_dir,
        )
        if folder:
            self.products_dir.setText(folder)

    def start_dictation(
        self,
        target: QTextEdit,
        button: QPushButton,
        status: QLabel | None = None,
    ) -> None:
        cancel_event = getattr(self, "_dictation_cancel_event", None)
        if cancel_event is not None:
            cancel_event.set()
            button.setEnabled(False)
            button.setText("Parando...")
            if status is not None:
                status.setText("Encerrando a gravação...")
            return

        self._dictation_cancel_event = Event()
        self._dictation_phase = 0
        self._dictation_timer = QTimer(self)
        self._dictation_timer.timeout.connect(
            lambda: self._animate_dictation(button, status)
        )
        self._dictation_timer.start(350)
        button.setEnabled(True)
        button.setText("■ Parar gravação")
        if status is not None:
            status.setText("Gravando... fale agora")
        self.start_task(
            reconhecer_microfone,
            cancel_event=self._dictation_cancel_event,
            on_done=lambda text: self.dictation_finished(target, button, text, status),
            on_error=lambda error: self.dictation_failed(button, error, status),
        )

    def _animate_dictation(
        self,
        button: QPushButton,
        status: QLabel | None,
    ) -> None:
        if status is None:
            return
        phase = getattr(self, "_dictation_phase", 0)
        status.setText(f"Gravando{'.' * (phase % 4)} fale agora")
        self._dictation_phase = phase + 1

    def _finish_dictation_ui(
        self,
        button: QPushButton,
        status: QLabel | None,
    ) -> None:
        timer = getattr(self, "_dictation_timer", None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()
            self._dictation_timer = None
        self._dictation_cancel_event = None
        button.setEnabled(True)
        button.setText("🎤 Gravar")
        if status is not None:
            status.setText("Pronto para gravar")

    def dictation_finished(
        self,
        target: QTextEdit,
        button: QPushButton,
        text: object,
        status: QLabel | None = None,
    ) -> None:
        self._finish_dictation_ui(button, status)
        atual = target.toPlainText().strip()
        transcricao = str(text).strip()
        target.setPlainText(
            f"{atual} {transcricao}".strip() if atual else transcricao
        )
        if status is not None:
            status.setText("Texto inserido no campo.")

    def dictation_failed(
        self,
        button: QPushButton,
        error: str,
        status: QLabel | None = None,
    ) -> None:
        self._finish_dictation_ui(button, status)
        self.log.appendPlainText(error)
        from PySide6.QtWidgets import QMessageBox

        linhas = [linha.strip() for linha in error.splitlines() if linha.strip()]
        detalhe = linhas[-1] if linhas else "Não foi possível usar o microfone."
        if "cancelada" in detalhe.lower():
            if status is not None:
                status.setText("Gravação cancelada.")
            return
        if status is not None:
            status.setText(f"Erro: {detalhe}")
        QMessageBox.warning(self, "Microfone", detalhe)

    def update_classification_visibility(self) -> None:
        is_unique = self.product_type.currentText() == "Único"
        has_kit = self.also_kit.currentText() == "Sim"
        self.variation_label.setVisible(is_unique)
        self.variations.setVisible(is_unique)
        self.also_kit_label.setVisible(is_unique)
        self.also_kit.setVisible(is_unique)
        show_kit_fields = not is_unique or has_kit
        self.kit_pieces_label.setVisible(show_kit_fields)
        self.kit_pieces.setVisible(show_kit_fields)
        self.kit_variation_label.setVisible(not is_unique)
        self.kit_variation.setVisible(not is_unique)
        self.kit_count_label.setVisible(show_kit_fields)
        self.kit_count.setVisible(show_kit_fields)

    def refresh_files(self) -> None:
        self.files = listar_imagens(self.source_dir.text().strip())
        if not self.files:
            self.files_label.setText("Nenhuma imagem ou vídeo encontrado.")
        else:
            self.files_label.setText(
                f"{len(self.files)} arquivo(s), ordenados por nome."
            )
        self.media_gallery.update_files(
            self.files,
            self.source_dir.text().strip(),
        )
        self.rebuild_measurements()

    def clear_measurements(self) -> None:
        self.measurement_rows.clear()
        while self.measurement_layout.count():
            item = self.measurement_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def rebuild_measurements(self) -> None:
        self.clear_measurements()
        images = [
            nome
            for nome in self.files
            if nome.lower().endswith(IMAGE_EXTENSIONS)
        ]
        tipo = self.product_type.currentText()
        variations = int(self.variations.currentText())
        also_kit = self.also_kit.currentText()
        kit_pieces = int(self.kit_pieces.currentText())
        kit_count = int(self.kit_count.currentText())

        groups: list[tuple[str, list[str]]] = []
        if tipo == "Único" and variations == 1 and also_kit == "Não":
            groups.append(("Produto único", images))
        elif tipo == "Único" and also_kit == "Não":
            per_group = max(1, len(images) // variations)
            for index in range(variations):
                start = index * per_group
                end = len(images) if index == variations - 1 else start + per_group
                groups.append((f"Variação {index + 1}", images[start:end]))
        elif tipo == "Kit":
            per_kit = 1 + kit_pieces
            expected = per_kit * kit_count
            for index, name in enumerate(images[:expected]):
                inside = index % per_kit
                title = (
                    f"Kit completo {index // per_kit + 1}"
                    if inside == 0
                    else f"Kit {index // per_kit + 1} - peça {inside}"
                )
                groups.append((title, [name]))
        else:
            per_kit = 1 + kit_pieces
            total_kit = per_kit * kit_count
            unique_images = images[:-total_kit] if len(images) > total_kit else []
            kit_images = images[-total_kit:] if len(images) >= total_kit else []
            if variations == 1:
                groups.append(("Produto único", unique_images))
            else:
                per_group = max(1, len(unique_images) // variations)
                for index in range(variations):
                    start = index * per_group
                    end = len(unique_images) if index == variations - 1 else start + per_group
                    groups.append((f"Variação {index + 1}", unique_images[start:end]))
            for index, name in enumerate(kit_images):
                inside = index % per_kit
                title = (
                    f"Kit completo {index // per_kit + 1}"
                    if inside == 0
                    else f"Kit {index // per_kit + 1} - peça {inside}"
                )
                groups.append((title, [name]))

        source = Path(self.source_dir.text().strip())
        for title, group in groups:
            if not group:
                continue
            box = QGroupBox(title)
            box_layout = QVBoxLayout(box)
            if len(group) == 1:
                row = MeasurementRow(group[0], source / group[0])
                self.measurement_rows.append(row)
                box_layout.addWidget(row)
            else:
                shared = MeasurementRow(
                    f"{len(group)} imagens compartilham estas medidas",
                    source / group[0],
                    title,
                )
                self.measurement_rows.append(shared)
                box_layout.addWidget(shared)
                names = QLabel("Arquivos: " + ", ".join(group))
                names.setWordWrap(True)
                box_layout.addWidget(names)
            self.measurement_layout.addWidget(box)
        self.update_summary()

    def update_summary(self) -> None:
        variations = int(self.variations.currentText())
        kit_pieces = int(self.kit_pieces.currentText())
        kit_count = int(self.kit_count.currentText())
        if self.product_type.currentText() == "Kit":
            total = (1 + kit_pieces) * kit_count
            text = (
                f"Kit de {kit_pieces} peças: "
                f"{kit_count} grupo(s), {total} fotos esperadas."
            )
        elif self.also_kit.currentText() == "Sim":
            text = (
                f"Produto único com {variations} variação(ões) "
                f"e kits de {kit_pieces} peças."
            )
        else:
            text = f"Produto único com {variations} bloco(s) de medidas."
        self.summary.setText(text)

    def collect_data(self) -> list[tuple[str, str, str, str, str]]:
        data: list[tuple[str, str, str, str, str]] = []
        for row in self.measurement_rows:
            values = row.values()
            filename = values[0]
            if filename not in self.files:
                continue
            data.append(values)

        images = [
            name
            for name in self.files
            if name.lower().endswith(IMAGE_EXTENSIONS)
        ]
        variations = int(self.variations.currentText())
        kit_pieces = int(self.kit_pieces.currentText())
        kit_count = int(self.kit_count.currentText())
        if self.product_type.currentText() == "Único" and self.also_kit.currentText() == "Não":
            if variations == 1 and self.measurement_rows:
                values = self.measurement_rows[0].values()[1:]
                return [(name, *values) for name in images]
            expanded: list[tuple[str, str, str, str, str]] = []
            per_group = max(1, len(images) // variations)
            for index in range(variations):
                start = index * per_group
                end = len(images) if index == variations - 1 else start + per_group
                if index >= len(self.measurement_rows):
                    break
                values = self.measurement_rows[index].values()[1:]
                expanded.extend((name, *values) for name in images[start:end])
            return expanded

        if self.product_type.currentText() == "Único" and self.also_kit.currentText() == "Sim":
            kit_size = (1 + kit_pieces) * kit_count
            unique_images = images[:-kit_size] if len(images) > kit_size else []
            kit_images = images[-kit_size:] if len(images) >= kit_size else []
            result: list[tuple[str, str, str, str, str]] = []
            cursor = 0
            if variations == 1 and self.measurement_rows:
                values = self.measurement_rows[cursor].values()[1:]
                cursor += 1
                result.extend((name, *values) for name in unique_images)
            else:
                per_group = max(1, len(unique_images) // variations)
                for index in range(variations):
                    start = index * per_group
                    end = len(unique_images) if index == variations - 1 else start + per_group
                    if cursor >= len(self.measurement_rows):
                        break
                    values = self.measurement_rows[cursor].values()[1:]
                    cursor += 1
                    result.extend((name, *values) for name in unique_images[start:end])
            for name in kit_images:
                if cursor >= len(self.measurement_rows):
                    break
                result.append((name, *self.measurement_rows[cursor].values()[1:]))
                cursor += 1
            return result

        return data

    def save_product(self) -> None:
        produto = self.product_name.text().strip()
        origem = self.source_dir.text().strip()
        descricao = self.description.toPlainText().strip()
        if not produto or not origem or not descricao:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self,
                "Dados incompletos",
                "Preencha nome, pasta de origem e descrição.",
            )
            return
        if not self.files:
            self.refresh_files()
        dados = self.collect_data()
        if not dados:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "Sem imagens", "Nenhuma imagem para processar.")
            return
        destino = Path(self.products_dir.text().strip()) / produto.upper()
        self.save_button.setEnabled(False)
        self.start_task(
            salvar_cadastro_task,
            origem,
            str(destino),
            self.files,
            dados,
            produto,
            descricao,
            self.usage.toPlainText().strip(),
            self.accompanies.text().strip(),
            self.finish.checked_text(),
            self.product_type.currentText(),
            int(self.variations.currentText()),
            self.also_kit.currentText(),
            int(self.kit_pieces.currentText()),
            int(self.kit_pieces.currentText()),
            self.kit_variation.currentText(),
            int(self.kit_count.currentText()),
            self.proportion.currentText(),
            on_done=self.save_finished,
            on_error=self.save_failed,
        )

    def save_finished(self, result: object) -> None:
        from PySide6.QtWidgets import QMessageBox

        self.save_button.setEnabled(True)
        self.log.appendPlainText(f"Produto salvo em: {result}")
        self.on_saved()
        QMessageBox.information(self, "Concluído", "Cadastro salvo com sucesso.")

    def save_failed(self, error: str) -> None:
        from PySide6.QtWidgets import QMessageBox

        self.save_button.setEnabled(True)
        self.log.appendPlainText(error)
        QMessageBox.critical(self, "Erro no cadastro", error)


def _dictation_failed_visible(
    self: CadastroTab,
    button: QPushButton,
    error: str,
) -> None:
    """Mostra a causa do erro de áudio mesmo com o log fora da área visível."""
    from PySide6.QtWidgets import QMessageBox

    button.setEnabled(True)
    button.setText("Microfone")
    self.log.appendPlainText(error)
    linhas = [linha.strip() for linha in error.splitlines() if linha.strip()]
    detalhe = linhas[-1] if linhas else "Não foi possível usar o microfone."
    QMessageBox.warning(self, "Microfone", detalhe)


# A última cópia de CadastroTab é a implementação carregada pelo módulo.
CadastroTab.dictation_failed = _dictation_failed_visible


# ---------------------------------------------------------------------------
# Galeria de mídias aprimorada
#
# O arquivo histórico desta tela contém versões antigas concatenadas. As
# classes abaixo ficam no final para substituir somente a implementação que o
# módulo efetivamente expõe, sem alterar as regras de cadastro já existentes.
# ---------------------------------------------------------------------------

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QIcon, QImageReader, QPainter, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QSlider,
)


class _VideoPlayerDialog(QDialog):
    """Reproduz um vídeo dentro da aplicação, sem abrir navegador externo."""

    def __init__(self, video_path: Path, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"Visualizar vídeo — {video_path.name}")
        self.resize(820, 560)

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.video = QVideoWidget(self)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)

        self.play_button = QPushButton("Pausar")
        self.play_button.clicked.connect(self.toggle_playback)
        self.position = QSlider(Qt.Orientation.Horizontal)
        self.position.setRange(0, 0)
        self.position.sliderMoved.connect(self.player.setPosition)

        self.status = QLabel("Carregando vídeo...")
        self.status.setWordWrap(True)
        close_button = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_button.rejected.connect(self.reject)

        controls = QHBoxLayout()
        controls.addWidget(self.play_button)
        controls.addWidget(self.position, 1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.video, 1)
        layout.addLayout(controls)
        layout.addWidget(self.status)
        layout.addWidget(close_button)

        self.player.positionChanged.connect(self.position.setValue)
        self.player.durationChanged.connect(self.position.setMaximum)
        self.player.playbackStateChanged.connect(self._state_changed)
        self.player.errorOccurred.connect(self._player_error)
        self.player.setSource(QUrl.fromLocalFile(str(video_path)))
        self.player.play()

    def toggle_playback(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        self.play_button.setText(
            "Pausar"
            if state == QMediaPlayer.PlaybackState.PlayingState
            else "Reproduzir"
        )

    def _player_error(self, error: QMediaPlayer.Error, message: str) -> None:
        if message:
            self.status.setText(f"Não foi possível reproduzir este vídeo: {message}")

    def closeEvent(self, event) -> None:
        self.player.stop()
        super().closeEvent(event)


def _load_oriented_pixmap(path: Path) -> QPixmap:
    """Carrega a imagem respeitando a orientação EXIF do celular."""
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    image = reader.read()
    return QPixmap.fromImage(image) if not image.isNull() else QPixmap()


class _EnhancedMediaGallery(QWidget):
    """Galeria com ordenação, seleção, reordenação manual e vídeo integrado."""

    filesChanged = Signal(list)

    def __init__(self, title: str = "Mídias encontradas"):
        super().__init__()
        self.source_dir = Path()
        self.files: list[str] = []
        self.selected_name: str | None = None
        self.cards: dict[str, QWidget] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        heading = QHBoxLayout()
        heading.addWidget(QLabel(f"<b>{title}</b>"))
        heading.addStretch()
        heading.addWidget(QLabel("Ordenar:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(
            [
                "Nome (A-Z)",
                "Nome (Z-A)",
                "Data (mais recente)",
                "Data (mais antiga)",
                "Ordem manual",
            ]
        )
        self.sort_combo.setToolTip(
            "Escolha como as mídias serão organizadas. A ordem exibida será "
            "usada na associação com as medidas."
        )
        self.sort_combo.currentTextChanged.connect(self._sort_changed)
        heading.addWidget(self.sort_combo)

        self.up_button = QPushButton("↑ Subir")
        self.up_button.setToolTip(
            "Mover a mídia selecionada uma posição para cima."
        )
        self.up_button.clicked.connect(self._move_selected_up)
        heading.addWidget(self.up_button)

        self.down_button = QPushButton("↓ Descer")
        self.down_button.setToolTip(
            "Mover a mídia selecionada uma posição para baixo."
        )
        self.down_button.clicked.connect(self._move_selected_down)
        heading.addWidget(self.down_button)
        root.addLayout(heading)

        self.order_label = QLabel(
            "Clique em uma mídia para selecioná-la; use Subir/Descer para ajustar."
        )
        self.order_label.setWordWrap(True)
        root.addWidget(self.order_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.container = QWidget()
        self.container.setMinimumHeight(145)
        self.layout = QHBoxLayout(self.container)
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(8)
        self.scroll.setWidget(self.container)
        self.scroll.setMinimumHeight(150)
        root.addWidget(self.scroll)
        self.show_empty()

    def clear(self) -> None:
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.cards.clear()

    def show_empty(self) -> None:
        self.clear()
        self.layout.addWidget(QLabel("Nenhuma imagem ou vídeo encontrado."))
        self.layout.addStretch()
        self.container.adjustSize()
        self.order_label.setText(
            "Clique em uma mídia para selecioná-la; use Subir/Descer para ajustar."
        )

    def update_files(self, files: list[str], source_dir: str) -> None:
        self.source_dir = Path(source_dir)
        self.files = list(files)
        self._apply_sort(emit=False)

    def _apply_sort(self, emit: bool = True) -> None:
        mode = self.sort_combo.currentText()
        if mode == "Nome (A-Z)":
            self.files.sort(key=str.casefold)
        elif mode == "Nome (Z-A)":
            self.files.sort(key=str.casefold, reverse=True)
        elif mode == "Data (mais antiga)":
            self.files.sort(
                key=lambda name: (self.source_dir / name).stat().st_mtime
                if (self.source_dir / name).exists()
                else 0
            )
        elif mode == "Data (mais recente)":
            self.files.sort(
                key=lambda name: (self.source_dir / name).stat().st_mtime
                if (self.source_dir / name).exists()
                else 0,
                reverse=True,
            )
        self._render()
        if emit:
            self.filesChanged.emit(list(self.files))

    def _sort_changed(self, mode: str) -> None:
        if mode == "Ordem manual":
            self._render()
            self.filesChanged.emit(list(self.files))
            return
        self._apply_sort()

    def _select(self, name: str) -> None:
        self.selected_name = name
        self._update_selection_style()
        try:
            position = self.files.index(name) + 1
            self.order_label.setText(
                f"Mídia selecionada: posição {position} de {len(self.files)} — "
                f"{name}. Use Subir/Descer para alterar a ordem."
            )
        except ValueError:
            pass

    def _update_selection_style(self) -> None:
        for name, card in self.cards.items():
            border = (
                f"2px solid {COR_ACENTO_BORDA}"
                if name == self.selected_name
                else f"1px solid {COR_BORDA_CLARA}"
            )
            card.setStyleSheet(
                f"QWidget {{ border: {border}; border-radius: 4px; }}"
            )

    def _move_selected_up(self) -> None:
        self._move_selected(-1)

    def _move_selected_down(self) -> None:
        self._move_selected(1)

    def _move_selected(self, step: int) -> None:
        if self.selected_name not in self.files:
            self.order_label.setText(
                "Selecione uma imagem ou vídeo antes de mudar a posição."
            )
            return
        index = self.files.index(self.selected_name)
        target = index + step
        if target < 0 or target >= len(self.files):
            return
        self.files[index], self.files[target] = (
            self.files[target],
            self.files[index],
        )
        self.sort_combo.blockSignals(True)
        self.sort_combo.setCurrentText("Ordem manual")
        self.sort_combo.blockSignals(False)
        self._render()
        self._select(self.selected_name)
        self.filesChanged.emit(list(self.files))

    def _video_icon(self) -> QIcon:
        pixmap = QPixmap(150, 100)
        pixmap.fill(Qt.GlobalColor.darkGray)
        painter = QPainter(pixmap)
        painter.setPen(Qt.GlobalColor.white)
        painter.drawText(
            pixmap.rect(),
            Qt.AlignmentFlag.AlignCenter,
            "▶\nVÍDEO",
        )
        painter.end()
        return QIcon(pixmap)

    def _open_video(self, path: Path) -> None:
        self._select(path.name)
        dialog = _VideoPlayerDialog(path, self)
        dialog.exec()

    def _render(self) -> None:
        self.clear()
        if not self.files:
            self.show_empty()
            return

        for index, name in enumerate(self.files, start=1):
            path = self.source_dir / name
            card = QWidget()
            card.setFixedSize(160, 154)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(2, 2, 2, 2)
            card_layout.setSpacing(2)
            self.cards[name] = card

            if path.suffix.lower() in VIDEO_EXTENSIONS:
                preview = QPushButton()
                preview.setIcon(self._video_icon())
                preview.setIconSize(QPixmap(150, 100).size())
                preview.setFixedSize(150, 100)
                preview.setToolTip(
                    f"Clique para assistir dentro do programa: {name}"
                )
                preview.clicked.connect(
                    lambda checked=False, file_path=path: self._open_video(
                        file_path
                    )
                )
            else:
                preview = QPushButton()
                preview.setFixedSize(150, 100)
                preview.setFlat(True)
                preview.setToolTip(
                    f"Clique para selecionar esta mídia: {name}"
                )
                pixmap = _load_oriented_pixmap(path)
                if pixmap.isNull():
                    preview.setText("sem prévia")
                else:
                    preview.setIcon(QIcon(pixmap))
                    preview.setIconSize(pixmap.scaled(
                        145,
                        95,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    ).size())
                preview.clicked.connect(
                    lambda checked=False, file_name=name: self._select(file_name)
                )

            card_layout.addWidget(preview)
            caption = QLabel(f"{index}. {name}")
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            caption.setWordWrap(True)
            caption.setFixedWidth(150)
            card_layout.addWidget(caption)
            self.layout.addWidget(card)

        self.layout.addStretch()
        self.container.setMinimumWidth(max(180, len(self.files) * 168 + 12))
        self.container.resize(self.container.sizeHint())
        self._update_selection_style()
        selected = (
            f"Selecionada: {self.selected_name}"
            if self.selected_name in self.files
            else "Clique em uma mídia para selecioná-la; use Subir/Descer para ajustar."
        )
        self.order_label.setText(
            f"{len(self.files)} arquivo(s) — {self.sort_combo.currentText()}. {selected}"
        )


_LegacyMediaGallery = MediaGallery
MediaGallery = _EnhancedMediaGallery

_legacy_cadastro_init = CadastroTab.__init__


def _enhanced_cadastro_init(
    self,
    on_saved: Callable[[], None],
    on_open_prompts: Callable[[], None] | None = None,
) -> None:
    _legacy_cadastro_init(self, on_saved, on_open_prompts)
    self.media_gallery.filesChanged.connect(
        lambda files: _media_order_changed(self, files)
    )


def _media_order_changed(self, files: list[str]) -> None:
    self.files = list(files)
    self.files_label.setText(
        f"{len(self.files)} arquivo(s), na ordem escolhida para o cadastro."
    )
    self.rebuild_measurements()


def _enhanced_refresh_files(self) -> None:
    source = Path(self.source_dir.text().strip())
    if not source.exists():
        self.files = []
        self.media_gallery.update_files([], str(source))
        self.files_label.setText("Nenhuma pasta selecionada")
        self.rebuild_measurements()
        return

    # Mantém a ordem entregue pelo sistema de arquivos para permitir ao usuário
    # começar da sequência da pasta e depois ajustar manualmente.
    self.files = [
        item.name
        for item in source.iterdir()
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS + VIDEO_EXTENSIONS
    ]
    self.media_gallery.update_files(self.files, str(source))
    self.files_label.setText(
        f"{len(self.files)} arquivo(s), na ordem escolhida para o cadastro."
    )
    self.rebuild_measurements()


CadastroTab.__init__ = _enhanced_cadastro_init
CadastroTab.refresh_files = _enhanced_refresh_files

"""Tela de cadastro de produtos da aplicação desktop PySide6."""

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import (
    QDesktopServices,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from _APP_.PySide6_core import (
    BackgroundMixin,
    DEFAULT_PRODUCTS_DIR,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    listar_imagens,
    reconhecer_microfone as _legacy_reconhecer_microfone,
    salvar_cadastro_task,
)


class CheckableComboBox(QComboBox):
    """QComboBox com seleção múltipla, equivalente ao multiselect do Streamlit."""

    def __init__(self, items: list[str]):
        super().__init__()
        model = QStandardItemModel(self)
        for text in items:
            item = QStandardItem(text)
            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
            )
            item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
            model.appendRow(item)
        self.setModel(model)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setPlaceholderText("Selecione os acabamentos")
        self.view().pressed.connect(self._toggle_item)
        self._refresh_text()

    def _toggle_item(self, index) -> None:
        item = self.model().itemFromIndex(index)
        state = (
            Qt.CheckState.Unchecked
            if item.checkState() == Qt.CheckState.Checked
            else Qt.CheckState.Checked
        )
        item.setCheckState(state)
        self._refresh_text()

    def _refresh_text(self) -> None:
        self.lineEdit().setText(", ".join(self.checked_items()))

    def checked_items(self) -> list[str]:
        return [
            self.model().item(index).text()
            for index in range(self.model().rowCount())
            if self.model().item(index).checkState() == Qt.CheckState.Checked
        ]

    def checked_text(self) -> str:
        return ", ".join(self.checked_items())


class MediaGallery(QWidget):
    """Galeria horizontal com todas as imagens e vídeos encontrados."""

    def __init__(self, title: str = "Mídias encontradas"):
        super().__init__()
        self.source_dir = Path()
        self.setMinimumHeight(185)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(QLabel(f"<b>{title}</b>"))

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.container = QWidget()
        self.container.setMinimumHeight(145)
        self.layout = QHBoxLayout(self.container)
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(8)
        self.scroll.setWidget(self.container)
        self.scroll.setMinimumHeight(150)
        root.addWidget(self.scroll)
        self.show_empty()

    def clear(self) -> None:
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def show_empty(self) -> None:
        self.clear()
        self.layout.addWidget(QLabel("Nenhuma imagem ou vídeo encontrado."))
        self.layout.addStretch()
        self.container.adjustSize()

    def update_files(self, files: list[str], source_dir: str) -> None:
        self.clear()
        self.source_dir = Path(source_dir)
        if not files:
            self.show_empty()
            return

        for name in files:
            path = self.source_dir / name
            card = QWidget()
            card.setFixedSize(160, 140)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(2, 2, 2, 2)
            card_layout.setSpacing(2)
            if path.suffix.lower() in VIDEO_EXTENSIONS:
                preview = QPushButton(f"▶\nVÍDEO\n{name}")
                preview.setToolTip(f"Abrir vídeo: {name}")
                preview.setFixedSize(150, 105)
                preview.clicked.connect(
                    lambda checked=False, file_path=path: QDesktopServices.openUrl(
                        QUrl.fromLocalFile(str(file_path))
                    )
                )
            else:
                preview = QLabel()
                preview.setFixedSize(150, 105)
                preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
                pixmap = QPixmap(str(path))
                if pixmap.isNull():
                    preview.setText("sem prévia")
                else:
                    preview.setPixmap(
                        pixmap.scaled(
                            145,
                            100,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
            card_layout.addWidget(preview)
            caption = QLabel(name)
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            caption.setWordWrap(True)
            caption.setFixedWidth(150)
            card_layout.addWidget(caption)
            self.layout.addWidget(card)
        self.layout.addStretch()
        self.container.adjustSize()
        self.container.setMinimumWidth(max(180, len(files) * 168 + 12))
        self.container.resize(self.container.sizeHint())


class MeasurementRow(QWidget):
    def __init__(self, filename: str, image_path: Path, title: str = ""):
        super().__init__()
        self.filename = filename
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        preview = QLabel()
        preview.setFixedSize(96, 76)
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = _load_oriented_pixmap(image_path)
        if not pixmap.isNull():
            preview.setPixmap(
                pixmap.scaled(
                    88,
                    68,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            preview.setText("sem prévia")
        layout.addWidget(preview)

        info = QVBoxLayout()
        label = QLabel(f"{title}\n{filename}" if title else filename)
        label.setWordWrap(True)
        label.setToolTip(
            "Arquivo usado neste grupo de medidas. As medidas serão gravadas no produtos.txt."
        )
        info.addWidget(label)
        inputs = QHBoxLayout()
        self.altura = QLineEdit()
        self.largura = QLineEdit()
        self.espessura = QLineEdit()
        self.peso = QLineEdit()
        for widget, placeholder in (
            (self.altura, "Altura"),
            (self.largura, "Largura"),
            (self.espessura, "Espessura"),
            (self.peso, "Peso"),
        ):
            widget.setPlaceholderText(placeholder)
            widget.setMaximumWidth(100)
            widget.setToolTip(
                f"{placeholder} do produto. Informe o valor que será usado no cadastro."
            )
            inputs.addWidget(widget)
        info.addLayout(inputs)
        layout.addLayout(info, 1)

    def values(self) -> tuple[str, str, str, str, str]:
        return (
            self.filename,
            self.altura.text().strip(),
            self.largura.text().strip(),
            self.espessura.text().strip(),
            self.peso.text().strip(),
        )


class CadastroTab(QWidget, BackgroundMixin):
    """Cadastro com configurações à esquerda e mídias/medidas à direita."""

    def __init__(
        self,
        on_saved: Callable[[], None],
        on_open_prompts: Callable[[], None] | None = None,
    ):
        QWidget.__init__(self)
        BackgroundMixin.__init__(self)
        self.on_saved = on_saved
        self.on_open_prompts = on_open_prompts
        self.measurement_rows: list[MeasurementRow] = []
        self.files: list[str] = []
        self.setObjectName("CadastroTab")
        self.build_ui()

    def build_ui(self) -> None:
        root = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        settings = QWidget()
        settings_layout = QVBoxLayout(settings)
        settings_layout.setContentsMargins(4, 4, 8, 4)

        basic = QGroupBox("Configurações do produto")
        basic_layout = QVBoxLayout(basic)
        self.product_name = QLineEdit()
        self.product_name.setToolTip("Nome usado para criar o cadastro do produto.")
        self.source_dir = QLineEdit()
        self.source_dir.setToolTip(
            "Pasta que contém as imagens e os vídeos do produto."
        )
        self.description = QTextEdit()
        self.description.setFixedHeight(150)
        self.description.setToolTip(
            "Descrição do produto. Você pode escrever várias linhas ou usar o microfone."
        )
        self.usage = QTextEdit()
        self.usage.setFixedHeight(150)
        self.usage.setToolTip(
            "Explique como o produto pode ser usado. Você pode escrever várias linhas ou usar o microfone."
        )
        self.accompanies = QLineEdit()
        self.accompanies.setToolTip(
            "Informe o que acompanha o produto. Este campo é texto livre no cadastro original."
        )
        self.finish = CheckableComboBox(
            [
                "lixado",
                "lavado",
                "Vernizado",
                "Impressão a Laiser",
                "Pode ser Estilizado pelo Cliente",
            ]
        )
        self.finish.setToolTip(
            "Selecione um ou mais acabamentos ou trabalhos possíveis para o produto."
        )
        self.proportion = QComboBox()
        self.proportion.addItems(["3:4", "1:1", "4:5", "9:16", "16:9"])
        self.proportion.setToolTip("Proporção usada no processamento das imagens.")
        self.products_dir = QLineEdit(str(DEFAULT_PRODUCTS_DIR))
        self.products_dir.setToolTip(
            "Pasta onde será criada a pasta final do produto cadastrado."
        )

        browse_source = QPushButton("Escolher")
        browse_source.setMaximumWidth(86)
        browse_source.setToolTip("Escolher a pasta que contém as mídias do produto.")
        browse_source.clicked.connect(self.choose_source)
        browse_products = QPushButton("Escolher")
        browse_products.setMaximumWidth(86)
        browse_products.setToolTip("Escolher a pasta de destino do cadastro.")
        browse_products.clicked.connect(self.choose_products_dir)

        def add_labeled_field(
            label: str,
            widget: QWidget,
            button: QPushButton | None = None,
        ) -> None:
            basic_layout.addWidget(QLabel(label))
            row = QHBoxLayout()
            row.addWidget(widget, 1)
            if button:
                row.addWidget(button)
            basic_layout.addLayout(row)

        add_labeled_field("Nome", self.product_name)
        add_labeled_field("Origem", self.source_dir, browse_source)
        add_labeled_field("Destino", self.products_dir, browse_products)
        add_labeled_field("Proporção", self.proportion)
        add_labeled_field("Acompanha", self.accompanies)
        add_labeled_field("Acabamento", self.finish)

        self.usage_mic_button = QPushButton("🎤 Gravar")
        self.usage_mic_button.setMinimumHeight(30)
        self.usage_mic_button.setToolTip(
            "Gravar e transformar em texto o campo 'Como pode ser usado'."
        )
        self.usage_status = QLabel("Pronto para gravar")
        self.usage_mic_button.clicked.connect(
            lambda: self.start_dictation(
                self.usage,
                self.usage_mic_button,
                self.usage_status,
            )
        )
        usage_controls = QHBoxLayout()
        usage_controls.addWidget(self.usage_mic_button)
        usage_controls.addWidget(self.usage_status, 1)
        usage_controls.addStretch()
        usage_row = QVBoxLayout()
        usage_row.addWidget(self.usage)
        usage_row.addLayout(usage_controls)
        usage_label = QLabel("Como pode ser usado:")
        usage_label.setToolTip(self.usage.toolTip())
        basic_layout.addWidget(usage_label)
        basic_layout.addLayout(usage_row)

        self.description_mic_button = QPushButton("🎤 Gravar")
        self.description_mic_button.setMinimumHeight(30)
        self.description_mic_button.setToolTip(
            "Gravar e transformar em texto o campo 'Descrição'."
        )
        self.description_status = QLabel("Pronto para gravar")
        self.description_mic_button.clicked.connect(
            lambda: self.start_dictation(
                self.description,
                self.description_mic_button,
                self.description_status,
            )
        )
        description_controls = QHBoxLayout()
        description_controls.addWidget(self.description_mic_button)
        description_controls.addWidget(self.description_status, 1)
        description_controls.addStretch()
        description_row = QVBoxLayout()
        description_row.addWidget(self.description)
        description_row.addLayout(description_controls)
        description_label = QLabel("Descrição:")
        description_label.setToolTip(self.description.toolTip())
        basic_layout.addWidget(description_label)
        basic_layout.addLayout(description_row)
        settings_layout.addWidget(basic)

        classification = QGroupBox("Classificação")
        classification_layout = QGridLayout(classification)
        self.product_type = QComboBox()
        self.product_type.addItems(["Único", "Kit"])
        self.product_type.setToolTip(
            "Único = um produto com possíveis variações. Kit = conjunto de peças."
        )
        self.variations = QComboBox()
        self.variations.addItems([str(value) for value in range(1, 10)])
        self.variations.setToolTip(
            "1 = todas as fotos compartilham as mesmas medidas. "
            "2 ou mais = cada variação terá seu grupo de medidas."
        )
        self.also_kit = QComboBox()
        self.also_kit.addItems(["Não", "Sim"])
        self.also_kit.setToolTip(
            "O produto único também será vendido como conjunto?"
        )
        self.kit_pieces = QComboBox()
        self.kit_pieces.addItems([str(value) for value in range(2, 11)])
        self.kit_pieces.setToolTip(
            "Quantidade de fotos de peças individuais esperadas em cada kit."
        )
        self.kit_variation = QComboBox()
        self.kit_variation.addItems(
            ["Sem variação", "Tamanho", "Cor", "Peso", "Mista"]
        )
        self.kit_variation.setToolTip(
            "Indicação organizacional da variação das peças do kit. "
            "Não altera a quantidade de campos."
        )
        self.kit_count = QComboBox()
        self.kit_count.addItems([str(value) for value in range(1, 11)])
        self.kit_count.setToolTip(
            "Quantidade de grupos completos de fotos do kit."
        )
        self.variation_label = QLabel("Variações")
        self.also_kit_label = QLabel("Também em kit")
        self.kit_pieces_label = QLabel("Peças no kit")
        self.kit_variation_label = QLabel("Variação do kit")
        self.kit_count_label = QLabel("Quantidade de kits")
        fields = [
            ("Tipo", self.product_type),
            (self.variation_label, self.variations),
            (self.also_kit_label, self.also_kit),
            (self.kit_pieces_label, self.kit_pieces),
            (self.kit_variation_label, self.kit_variation),
            (self.kit_count_label, self.kit_count),
        ]
        for index, (label, widget) in enumerate(fields):
            row = index // 2
            column = (index % 2) * 2
            classification_layout.addWidget(
                QLabel(label) if isinstance(label, str) else label,
                row,
                column,
            )
            classification_layout.addWidget(widget, row, column + 1)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        classification_layout.addWidget(self.summary, 3, 0, 1, 4)
        settings_layout.addWidget(classification)

        for widget in (
            self.product_type,
            self.also_kit,
            self.kit_variation,
        ):
            widget.currentTextChanged.connect(self.rebuild_measurements)
        for widget in (self.variations, self.kit_pieces, self.kit_count):
            widget.currentTextChanged.connect(self.rebuild_measurements)
        self.product_type.currentTextChanged.connect(
            self.update_classification_visibility
        )
        self.also_kit.currentTextChanged.connect(
            self.update_classification_visibility
        )
        self.update_classification_visibility()

        actions = QHBoxLayout()
        self.refresh_button = QPushButton("Atualizar mídias")
        self.refresh_button.setMaximumWidth(130)
        self.refresh_button.setToolTip(
            "Ler novamente a pasta de origem, ordenar as mídias e reconstruir os grupos."
        )
        self.refresh_button.clicked.connect(self.refresh_files)
        self.save_button = QPushButton("Processar cadastro")
        self.save_button.setMaximumWidth(145)
        self.save_button.setToolTip(
            "Copiar as mídias, salvar as medidas e gerar o produtos.txt do cadastro."
        )
        self.save_button.clicked.connect(self.save_product)
        actions.addWidget(self.refresh_button)
        actions.addWidget(self.save_button)
        if self.on_open_prompts:
            prompts_button = QPushButton("Prompts")
            prompts_button.setMaximumWidth(82)
            prompts_button.setToolTip(
                "Abrir os prompts pré-configurados usados no cadastro e na produção."
            )
            prompts_button.clicked.connect(self.on_open_prompts)
            actions.addWidget(prompts_button)
        actions.addStretch()
        settings_layout.addLayout(actions)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(1000)
        self.log.setFixedHeight(0)
        self.log.hide()
        self.log.setToolTip("Mensagens do processamento e erros do cadastro.")
        settings_layout.addWidget(self.log)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 4, 4, 4)
        self.files_label = QLabel("Nenhuma pasta selecionada")
        self.files_label.setWordWrap(True)
        right_layout.addWidget(self.files_label)
        self.media_gallery = MediaGallery()
        right_layout.addWidget(self.media_gallery)

        measures_label = QLabel("<b>Grupos de variações, kits e medidas</b>")
        measures_label.setToolTip(
            "Cada grupo corresponde às fotos que compartilharão o mesmo conjunto de medidas."
        )
        right_layout.addWidget(measures_label)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.measurement_container = QWidget()
        self.measurement_layout = QVBoxLayout(self.measurement_container)
        self.measurement_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.measurement_container)
        right_layout.addWidget(scroll, 1)

        settings.setMinimumWidth(500)
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        settings_scroll.setWidget(settings)
        splitter.addWidget(settings_scroll)
        splitter.addWidget(right)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([520, 850])

    def choose_source(self) -> None:
        initial_dir = self.source_dir.text().strip() or str(Path.home() / "Downloads")
        if not Path(initial_dir).is_dir():
            initial_dir = str(Path.home() / "Downloads")
        folder = QFileDialog.getExistingDirectory(
            self,
            "Pasta de origem",
            initial_dir,
        )
        if folder:
            self.source_dir.setText(folder)
            self.refresh_files()

    def choose_products_dir(self) -> None:
        initial_dir = self.products_dir.text().strip() or str(Path.home() / "Downloads")
        if not Path(initial_dir).is_dir():
            initial_dir = str(Path.home() / "Downloads")
        folder = QFileDialog.getExistingDirectory(
            self,
            "Pasta de destino",
            initial_dir,
        )
        if folder:
            self.products_dir.setText(folder)

    def start_dictation(
        self,
        target: QTextEdit,
        button: QPushButton,
        status: QLabel | None = None,
    ) -> None:
        cancel_event = getattr(self, "_dictation_cancel_event", None)
        if cancel_event is not None:
            cancel_event.set()
            button.setEnabled(False)
            button.setText("Parando...")
            if status is not None:
                status.setText("Encerrando a gravação...")
            return

        self._dictation_cancel_event = Event()
        self._dictation_phase = 0
        self._dictation_timer = QTimer(self)
        self._dictation_timer.timeout.connect(
            lambda: self._animate_dictation(button, status)
        )
        self._dictation_timer.start(350)
        button.setEnabled(True)
        button.setText("■ Parar gravação")
        if status is not None:
            status.setText("Gravando... fale agora")
        self.start_task(
            reconhecer_microfone,
            cancel_event=self._dictation_cancel_event,
            on_done=lambda text: self.dictation_finished(
                target,
                button,
                text,
                status,
            ),
            on_error=lambda error: self.dictation_failed(button, error, status),
            on_cancel=lambda message: self.dictation_cancelled(
                button,
                status,
                message,
            ),
        )

    def _animate_dictation(
        self,
        button: QPushButton,
        status: QLabel | None,
    ) -> None:
        if status is None:
            return
        phase = getattr(self, "_dictation_phase", 0)
        status.setText(f"Gravando{'.' * (phase % 4)} fale agora")
        self._dictation_phase = phase + 1

    def _finish_dictation_ui(
        self,
        button: QPushButton,
        status: QLabel | None,
    ) -> None:
        timer = getattr(self, "_dictation_timer", None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()
            self._dictation_timer = None
        self._dictation_cancel_event = None
        button.setEnabled(True)
        button.setText("🎤 Gravar")
        if status is not None:
            status.setText("Pronto para gravar")

    def dictation_finished(
        self,
        target: QTextEdit,
        button: QPushButton,
        text: object,
        status: QLabel | None = None,
    ) -> None:
        self._finish_dictation_ui(button, status)
        atual = target.toPlainText().strip()
        transcricao = str(text).strip()
        target.setPlainText(
            f"{atual} {transcricao}".strip() if atual else transcricao
        )
        if status is not None:
            status.setText("Texto inserido no campo.")

    def dictation_failed(
        self,
        button: QPushButton,
        error: str,
        status: QLabel | None = None,
    ) -> None:
        self._finish_dictation_ui(button, status)
        self.log.appendPlainText(error)
        from PySide6.QtWidgets import QMessageBox

        linhas = [linha.strip() for linha in error.splitlines() if linha.strip()]
        detalhe = linhas[-1] if linhas else "Não foi possível usar o microfone."
        if "cancelada" in detalhe.lower():
            if status is not None:
                status.setText("Gravação cancelada.")
            return
        if status is not None:
            status.setText(f"Erro: {detalhe}")
        QMessageBox.warning(self, "Microfone", detalhe)

    def update_classification_visibility(self) -> None:
        is_unique = self.product_type.currentText() == "Único"
        has_kit = self.also_kit.currentText() == "Sim"
        self.variation_label.setVisible(is_unique)
        self.variations.setVisible(is_unique)
        self.also_kit_label.setVisible(is_unique)
        self.also_kit.setVisible(is_unique)
        show_kit_fields = not is_unique or has_kit
        self.kit_pieces_label.setVisible(show_kit_fields)
        self.kit_pieces.setVisible(show_kit_fields)
        self.kit_variation_label.setVisible(not is_unique)
        self.kit_variation.setVisible(not is_unique)
        self.kit_count_label.setVisible(show_kit_fields)
        self.kit_count.setVisible(show_kit_fields)

    def refresh_files(self) -> None:
        self.files = listar_imagens(self.source_dir.text().strip())
        if not self.files:
            self.files_label.setText("Nenhuma imagem ou vídeo encontrado.")
        else:
            self.files_label.setText(
                f"{len(self.files)} arquivo(s), ordenados por nome."
            )
        self.media_gallery.update_files(
            self.files,
            self.source_dir.text().strip(),
        )
        self.rebuild_measurements()

    def clear_measurements(self) -> None:
        self.measurement_rows.clear()
        while self.measurement_layout.count():
            item = self.measurement_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def rebuild_measurements(self) -> None:
        self.clear_measurements()
        images = [
            nome
            for nome in self.files
            if nome.lower().endswith(IMAGE_EXTENSIONS)
        ]
        tipo = self.product_type.currentText()
        variations = int(self.variations.currentText())
        also_kit = self.also_kit.currentText()
        kit_pieces = int(self.kit_pieces.currentText())
        kit_count = int(self.kit_count.currentText())

        groups: list[tuple[str, list[str]]] = []
        if tipo == "Único" and variations == 1 and also_kit == "Não":
            groups.append(("Produto único", images))
        elif tipo == "Único" and also_kit == "Não":
            per_group = max(1, len(images) // variations)
            for index in range(variations):
                start = index * per_group
                end = len(images) if index == variations - 1 else start + per_group
                groups.append((f"Variação {index + 1}", images[start:end]))
        elif tipo == "Kit":
            per_kit = 1 + kit_pieces
            expected = per_kit * kit_count
            for index, name in enumerate(images[:expected]):
                inside = index % per_kit
                title = (
                    f"Kit completo {index // per_kit + 1}"
                    if inside == 0
                    else f"Kit {index // per_kit + 1} - peça {inside}"
                )
                groups.append((title, [name]))
        else:
            per_kit = 1 + kit_pieces
            total_kit = per_kit * kit_count
            unique_images = images[:-total_kit] if len(images) > total_kit else []
            kit_images = images[-total_kit:] if len(images) >= total_kit else []
            if variations == 1:
                groups.append(("Produto único", unique_images))
            else:
                per_group = max(1, len(unique_images) // variations)
                for index in range(variations):
                    start = index * per_group
                    end = len(unique_images) if index == variations - 1 else start + per_group
                    groups.append((f"Variação {index + 1}", unique_images[start:end]))
            for index, name in enumerate(kit_images):
                inside = index % per_kit
                title = (
                    f"Kit completo {index // per_kit + 1}"
                    if inside == 0
                    else f"Kit {index // per_kit + 1} - peça {inside}"
                )
                groups.append((title, [name]))

        source = Path(self.source_dir.text().strip())
        for title, group in groups:
            if not group:
                continue
            box = QGroupBox(title)
            box_layout = QVBoxLayout(box)
            if len(group) == 1:
                row = MeasurementRow(group[0], source / group[0])
                self.measurement_rows.append(row)
                box_layout.addWidget(row)
            else:
                shared = MeasurementRow(
                    f"{len(group)} imagens compartilham estas medidas",
                    source / group[0],
                    title,
                )
                self.measurement_rows.append(shared)
                box_layout.addWidget(shared)
                names = QLabel("Arquivos: " + ", ".join(group))
                names.setWordWrap(True)
                box_layout.addWidget(names)
            self.measurement_layout.addWidget(box)
        self.update_summary()

    def update_summary(self) -> None:
        variations = int(self.variations.currentText())
        kit_pieces = int(self.kit_pieces.currentText())
        kit_count = int(self.kit_count.currentText())
        if self.product_type.currentText() == "Kit":
            total = (1 + kit_pieces) * kit_count
            text = (
                f"Kit de {kit_pieces} peças: "
                f"{kit_count} grupo(s), {total} fotos esperadas."
            )
        elif self.also_kit.currentText() == "Sim":
            text = (
                f"Produto único com {variations} variação(ões) "
                f"e kits de {kit_pieces} peças."
            )
        else:
            text = f"Produto único com {variations} bloco(s) de medidas."
        self.summary.setText(text)

    def collect_data(self) -> list[tuple[str, str, str, str, str]]:
        data: list[tuple[str, str, str, str, str]] = []
        for row in self.measurement_rows:
            values = row.values()
            filename = values[0]
            if filename not in self.files:
                continue
            data.append(values)

        images = [
            name
            for name in self.files
            if name.lower().endswith(IMAGE_EXTENSIONS)
        ]
        variations = int(self.variations.currentText())
        kit_pieces = int(self.kit_pieces.currentText())
        kit_count = int(self.kit_count.currentText())
        if self.product_type.currentText() == "Único" and self.also_kit.currentText() == "Não":
            if variations == 1 and self.measurement_rows:
                values = self.measurement_rows[0].values()[1:]
                return [(name, *values) for name in images]
            expanded: list[tuple[str, str, str, str, str]] = []
            per_group = max(1, len(images) // variations)
            for index in range(variations):
                start = index * per_group
                end = len(images) if index == variations - 1 else start + per_group
                if index >= len(self.measurement_rows):
                    break
                values = self.measurement_rows[index].values()[1:]
                expanded.extend((name, *values) for name in images[start:end])
            return expanded

        if self.product_type.currentText() == "Único" and self.also_kit.currentText() == "Sim":
            kit_size = (1 + kit_pieces) * kit_count
            unique_images = images[:-kit_size] if len(images) > kit_size else []
            kit_images = images[-kit_size:] if len(images) >= kit_size else []
            result: list[tuple[str, str, str, str, str]] = []
            cursor = 0
            if variations == 1 and self.measurement_rows:
                values = self.measurement_rows[cursor].values()[1:]
                cursor += 1
                result.extend((name, *values) for name in unique_images)
            else:
                per_group = max(1, len(unique_images) // variations)
                for index in range(variations):
                    start = index * per_group
                    end = len(unique_images) if index == variations - 1 else start + per_group
                    if cursor >= len(self.measurement_rows):
                        break
                    values = self.measurement_rows[cursor].values()[1:]
                    cursor += 1
                    result.extend((name, *values) for name in unique_images[start:end])
            for name in kit_images:
                if cursor >= len(self.measurement_rows):
                    break
                result.append((name, *self.measurement_rows[cursor].values()[1:]))
                cursor += 1
            return result

        return data

    def save_product(self) -> None:
        produto = self.product_name.text().strip()
        origem = self.source_dir.text().strip()
        descricao = self.description.toPlainText().strip()
        if not produto or not origem or not descricao:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self,
                "Dados incompletos",
                "Preencha nome, pasta de origem e descrição.",
            )
            return
        if not self.files:
            self.refresh_files()
        dados = self.collect_data()
        if not dados:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "Sem imagens", "Nenhuma imagem para processar.")
            return
        destino = Path(self.products_dir.text().strip()) / produto.upper()
        self.save_button.setEnabled(False)
        self.start_task(
            salvar_cadastro_task,
            origem,
            str(destino),
            self.files,
            dados,
            produto,
            descricao,
            self.usage.toPlainText().strip(),
            self.accompanies.text().strip(),
            self.finish.checked_text(),
            self.product_type.currentText(),
            int(self.variations.currentText()),
            self.also_kit.currentText(),
            int(self.kit_pieces.currentText()),
            int(self.kit_pieces.currentText()),
            self.kit_variation.currentText(),
            int(self.kit_count.currentText()),
            self.proportion.currentText(),
            on_done=self.save_finished,
            on_error=self.save_failed,
        )

    def save_finished(self, result: object) -> None:
        from PySide6.QtWidgets import QMessageBox

        self.save_button.setEnabled(True)
        self.log.appendPlainText(f"Produto salvo em: {result}")
        self.on_saved()
        QMessageBox.information(self, "Concluído", "Cadastro salvo com sucesso.")

    def save_failed(self, error: str) -> None:
        from PySide6.QtWidgets import QMessageBox

        self.save_button.setEnabled(True)
        self.log.appendPlainText(error)
        QMessageBox.critical(self, "Erro no cadastro", error)

"""Tela de cadastro de produtos da aplicação desktop PySide6."""


from pathlib import Path
from typing import Callable

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import (
    QDesktopServices,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from _APP_.PySide6_core import (
    BackgroundMixin,
    DEFAULT_PRODUCTS_DIR,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    listar_imagens,
    reconhecer_microfone as _legacy_reconhecer_microfone,
    salvar_cadastro_task,
)


class CheckableComboBox(QComboBox):
    """QComboBox com seleção múltipla, equivalente ao multiselect do Streamlit."""

    def __init__(self, items: list[str]):
        super().__init__()
        model = QStandardItemModel(self)
        for text in items:
            item = QStandardItem(text)
            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
            )
            item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
            model.appendRow(item)
        self.setModel(model)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setPlaceholderText("Selecione os acabamentos")
        self.view().pressed.connect(self._toggle_item)
        self._refresh_text()

    def _toggle_item(self, index) -> None:
        item = self.model().itemFromIndex(index)
        state = (
            Qt.CheckState.Unchecked
            if item.checkState() == Qt.CheckState.Checked
            else Qt.CheckState.Checked
        )
        item.setCheckState(state)
        self._refresh_text()

    def _refresh_text(self) -> None:
        self.lineEdit().setText(", ".join(self.checked_items()))

    def checked_items(self) -> list[str]:
        return [
            self.model().item(index).text()
            for index in range(self.model().rowCount())
            if self.model().item(index).checkState() == Qt.CheckState.Checked
        ]

    def checked_text(self) -> str:
        return ", ".join(self.checked_items())


class MediaGallery(QWidget):
    """Galeria horizontal com todas as imagens e vídeos encontrados."""

    def __init__(self, title: str = "Mídias encontradas"):
        super().__init__()
        self.source_dir = Path()
        self.setMinimumHeight(185)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(QLabel(f"<b>{title}</b>"))

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.container = QWidget()
        self.container.setMinimumHeight(145)
        self.layout = QHBoxLayout(self.container)
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(8)
        self.scroll.setWidget(self.container)
        self.scroll.setMinimumHeight(150)
        root.addWidget(self.scroll)
        self.show_empty()

    def clear(self) -> None:
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def show_empty(self) -> None:
        self.clear()
        self.layout.addWidget(QLabel("Nenhuma imagem ou vídeo encontrado."))
        self.layout.addStretch()
        self.container.adjustSize()

    def update_files(self, files: list[str], source_dir: str) -> None:
        self.clear()
        self.source_dir = Path(source_dir)
        if not files:
            self.show_empty()
            return

        for name in files:
            path = self.source_dir / name
            card = QWidget()
            card.setFixedSize(160, 140)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(2, 2, 2, 2)
            card_layout.setSpacing(2)
            if path.suffix.lower() in VIDEO_EXTENSIONS:
                preview = QPushButton(f"▶\nVÍDEO\n{name}")
                preview.setToolTip(f"Abrir vídeo: {name}")
                preview.setFixedSize(150, 105)
                preview.clicked.connect(
                    lambda checked=False, file_path=path: QDesktopServices.openUrl(
                        QUrl.fromLocalFile(str(file_path))
                    )
                )
            else:
                preview = QLabel()
                preview.setFixedSize(150, 105)
                preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
                pixmap = QPixmap(str(path))
                if pixmap.isNull():
                    preview.setText("sem prévia")
                else:
                    preview.setPixmap(
                        pixmap.scaled(
                            145,
                            100,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
            card_layout.addWidget(preview)
            caption = QLabel(name)
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            caption.setWordWrap(True)
            caption.setFixedWidth(150)
            card_layout.addWidget(caption)
            self.layout.addWidget(card)
        self.layout.addStretch()
        self.container.adjustSize()
        self.container.setMinimumWidth(max(180, len(files) * 168 + 12))
        self.container.resize(self.container.sizeHint())


class MeasurementRow(QWidget):
    def __init__(self, filename: str, image_path: Path, title: str = ""):
        super().__init__()
        self.filename = filename
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        preview = QLabel()
        preview.setFixedSize(96, 76)
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = _load_oriented_pixmap(image_path)
        if not pixmap.isNull():
            preview.setPixmap(
                pixmap.scaled(
                    88,
                    68,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            preview.setText("sem prévia")
        layout.addWidget(preview)

        info = QVBoxLayout()
        label = QLabel(f"{title}\n{filename}" if title else filename)
        label.setWordWrap(True)
        label.setToolTip(
            "Arquivo usado neste grupo de medidas. As medidas serão gravadas no produtos.txt."
        )
        info.addWidget(label)
        inputs = QHBoxLayout()
        self.altura = QLineEdit()
        self.largura = QLineEdit()
        self.espessura = QLineEdit()
        self.peso = QLineEdit()
        for widget, placeholder in (
            (self.altura, "Altura"),
            (self.largura, "Largura"),
            (self.espessura, "Espessura"),
            (self.peso, "Peso"),
        ):
            widget.setPlaceholderText(placeholder)
            widget.setMaximumWidth(100)
            widget.setToolTip(
                f"{placeholder} do produto. Informe o valor que será usado no cadastro."
            )
            inputs.addWidget(widget)
        info.addLayout(inputs)
        layout.addLayout(info, 1)

    def values(self) -> tuple[str, str, str, str, str]:
        return (
            self.filename,
            self.altura.text().strip(),
            self.largura.text().strip(),
            self.espessura.text().strip(),
            self.peso.text().strip(),
        )


class CadastroTab(QWidget, BackgroundMixin):
    """Cadastro com configurações à esquerda e mídias/medidas à direita."""

    def __init__(
        self,
        on_saved: Callable[[], None],
        on_open_prompts: Callable[[], None] | None = None,
    ):
        QWidget.__init__(self)
        BackgroundMixin.__init__(self)
        self.on_saved = on_saved
        self.on_open_prompts = on_open_prompts
        self.measurement_rows: list[MeasurementRow] = []
        self.files: list[str] = []
        self.setObjectName("CadastroTab")
        self.build_ui()

    def build_ui(self) -> None:
        root = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        settings = QWidget()
        settings_layout = QVBoxLayout(settings)
        settings_layout.setContentsMargins(4, 4, 8, 4)

        basic = QGroupBox("Configurações do produto")
        basic_layout = QVBoxLayout(basic)
        self.product_name = QLineEdit()
        self.product_name.setToolTip("Nome usado para criar o cadastro do produto.")
        self.source_dir = QLineEdit()
        self.source_dir.setToolTip(
            "Pasta que contém as imagens e os vídeos do produto."
        )
        self.description = QTextEdit()
        self.description.setFixedHeight(150)
        self.description.setToolTip(
            "Descrição do produto. Você pode escrever várias linhas ou usar o microfone."
        )
        self.usage = QTextEdit()
        self.usage.setFixedHeight(150)
        self.usage.setToolTip(
            "Explique como o produto pode ser usado. Você pode escrever várias linhas ou usar o microfone."
        )
        self.accompanies = QLineEdit()
        self.accompanies.setToolTip(
            "Informe o que acompanha o produto. Este campo é texto livre no cadastro original."
        )
        self.finish = CheckableComboBox(
            [
                "lixado",
                "lavado",
                "Vernizado",
                "Impressão a Laiser",
                "Pode ser Estilizado pelo Cliente",
            ]
        )
        self.finish.setToolTip(
            "Selecione um ou mais acabamentos ou trabalhos possíveis para o produto."
        )
        self.proportion = QComboBox()
        self.proportion.addItems(["3:4", "1:1", "4:5", "9:16", "16:9"])
        self.proportion.setToolTip("Proporção usada no processamento das imagens.")
        self.products_dir = QLineEdit(str(DEFAULT_PRODUCTS_DIR))
        self.products_dir.setToolTip(
            "Pasta onde será criada a pasta final do produto cadastrado."
        )

        browse_source = QPushButton("Escolher")
        browse_source.setMaximumWidth(86)
        browse_source.setToolTip("Escolher a pasta que contém as mídias do produto.")
        browse_source.clicked.connect(self.choose_source)
        browse_products = QPushButton("Escolher")
        browse_products.setMaximumWidth(86)
        browse_products.setToolTip("Escolher a pasta de destino do cadastro.")
        browse_products.clicked.connect(self.choose_products_dir)

        def add_labeled_field(
            label: str,
            widget: QWidget,
            button: QPushButton | None = None,
        ) -> None:
            basic_layout.addWidget(QLabel(label))
            row = QHBoxLayout()
            row.addWidget(widget, 1)
            if button:
                row.addWidget(button)
            basic_layout.addLayout(row)

        add_labeled_field("Nome", self.product_name)
        add_labeled_field("Origem", self.source_dir, browse_source)
        add_labeled_field("Destino", self.products_dir, browse_products)
        add_labeled_field("Proporção", self.proportion)
        add_labeled_field("Acompanha", self.accompanies)
        add_labeled_field("Acabamento", self.finish)

        self.usage_mic_button = QPushButton("🎤 Gravar")
        self.usage_mic_button.setMinimumHeight(30)
        self.usage_mic_button.setToolTip(
            "Gravar e transformar em texto o campo 'Como pode ser usado'."
        )
        self.usage_status = QLabel("Pronto para gravar")
        self.usage_mic_button.clicked.connect(
            lambda: self.start_dictation(
                self.usage,
                self.usage_mic_button,
                self.usage_status,
            )
        )
        usage_controls = QHBoxLayout()
        usage_controls.addWidget(self.usage_mic_button)
        usage_controls.addWidget(self.usage_status, 1)
        usage_controls.addStretch()
        usage_row = QVBoxLayout()
        usage_row.addWidget(self.usage)
        usage_row.addLayout(usage_controls)
        usage_label = QLabel("Como pode ser usado:")
        usage_label.setToolTip(self.usage.toolTip())
        basic_layout.addWidget(usage_label)
        basic_layout.addLayout(usage_row)

        self.description_mic_button = QPushButton("🎤 Gravar")
        self.description_mic_button.setMinimumHeight(30)
        self.description_mic_button.setToolTip(
            "Gravar e transformar em texto o campo 'Descrição'."
        )
        self.description_status = QLabel("Pronto para gravar")
        self.description_mic_button.clicked.connect(
            lambda: self.start_dictation(
                self.description,
                self.description_mic_button,
                self.description_status,
            )
        )
        description_controls = QHBoxLayout()
        description_controls.addWidget(self.description_mic_button)
        description_controls.addWidget(self.description_status, 1)
        description_controls.addStretch()
        description_row = QVBoxLayout()
        description_row.addWidget(self.description)
        description_row.addLayout(description_controls)
        description_label = QLabel("Descrição:")
        description_label.setToolTip(self.description.toolTip())
        basic_layout.addWidget(description_label)
        basic_layout.addLayout(description_row)
        settings_layout.addWidget(basic)

        classification = QGroupBox("Classificação")
        classification_layout = QGridLayout(classification)
        self.product_type = QComboBox()
        self.product_type.addItems(["Único", "Kit"])
        self.product_type.setToolTip(
            "Único = um produto com possíveis variações. Kit = conjunto de peças."
        )
        self.variations = QComboBox()
        self.variations.addItems([str(value) for value in range(1, 10)])
        self.variations.setToolTip(
            "1 = todas as fotos compartilham as mesmas medidas. "
            "2 ou mais = cada variação terá seu grupo de medidas."
        )
        self.also_kit = QComboBox()
        self.also_kit.addItems(["Não", "Sim"])
        self.also_kit.setToolTip(
            "O produto único também será vendido como conjunto?"
        )
        self.kit_pieces = QComboBox()
        self.kit_pieces.addItems([str(value) for value in range(2, 11)])
        self.kit_pieces.setToolTip(
            "Quantidade de fotos de peças individuais esperadas em cada kit."
        )
        self.kit_variation = QComboBox()
        self.kit_variation.addItems(
            ["Sem variação", "Tamanho", "Cor", "Peso", "Mista"]
        )
        self.kit_variation.setToolTip(
            "Indicação organizacional da variação das peças do kit. "
            "Não altera a quantidade de campos."
        )
        self.kit_count = QComboBox()
        self.kit_count.addItems([str(value) for value in range(1, 11)])
        self.kit_count.setToolTip(
            "Quantidade de grupos completos de fotos do kit."
        )
        self.variation_label = QLabel("Variações")
        self.also_kit_label = QLabel("Também em kit")
        self.kit_pieces_label = QLabel("Peças no kit")
        self.kit_variation_label = QLabel("Variação do kit")
        self.kit_count_label = QLabel("Quantidade de kits")
        fields = [
            ("Tipo", self.product_type),
            (self.variation_label, self.variations),
            (self.also_kit_label, self.also_kit),
            (self.kit_pieces_label, self.kit_pieces),
            (self.kit_variation_label, self.kit_variation),
            (self.kit_count_label, self.kit_count),
        ]
        for index, (label, widget) in enumerate(fields):
            row = index // 2
            column = (index % 2) * 2
            classification_layout.addWidget(
                QLabel(label) if isinstance(label, str) else label,
                row,
                column,
            )
            classification_layout.addWidget(widget, row, column + 1)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        classification_layout.addWidget(self.summary, 3, 0, 1, 4)
        settings_layout.addWidget(classification)

        for widget in (
            self.product_type,
            self.also_kit,
            self.kit_variation,
        ):
            widget.currentTextChanged.connect(self.rebuild_measurements)
        for widget in (self.variations, self.kit_pieces, self.kit_count):
            widget.currentTextChanged.connect(self.rebuild_measurements)
        self.product_type.currentTextChanged.connect(
            self.update_classification_visibility
        )
        self.also_kit.currentTextChanged.connect(
            self.update_classification_visibility
        )
        self.update_classification_visibility()

        actions = QHBoxLayout()
        self.refresh_button = QPushButton("Atualizar mídias")
        self.refresh_button.setMaximumWidth(130)
        self.refresh_button.setToolTip(
            "Ler novamente a pasta de origem, ordenar as mídias e reconstruir os grupos."
        )
        self.refresh_button.clicked.connect(self.refresh_files)
        self.save_button = QPushButton("Processar cadastro")
        self.save_button.setMaximumWidth(145)
        self.save_button.setToolTip(
            "Copiar as mídias, salvar as medidas e gerar o produtos.txt do cadastro."
        )
        self.save_button.clicked.connect(self.save_product)
        actions.addWidget(self.refresh_button)
        actions.addWidget(self.save_button)
        if self.on_open_prompts:
            prompts_button = QPushButton("Prompts")
            prompts_button.setMaximumWidth(82)
            prompts_button.setToolTip(
                "Abrir os prompts pré-configurados usados no cadastro e na produção."
            )
            prompts_button.clicked.connect(self.on_open_prompts)
            actions.addWidget(prompts_button)
        actions.addStretch()
        settings_layout.addLayout(actions)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 4, 4, 4)
        self.files_label = QLabel("Nenhuma pasta selecionada")
        self.files_label.setWordWrap(True)
        right_layout.addWidget(self.files_label)
        self.media_gallery = MediaGallery()
        right_layout.addWidget(self.media_gallery)

        measures_label = QLabel("<b>Grupos de variações, kits e medidas</b>")
        measures_label.setToolTip(
            "Cada grupo corresponde às fotos que compartilharão o mesmo conjunto de medidas."
        )
        right_layout.addWidget(measures_label)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.measurement_container = QWidget()
        self.measurement_layout = QVBoxLayout(self.measurement_container)
        self.measurement_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.measurement_container)
        right_layout.addWidget(scroll, 1)

        settings.setMinimumWidth(500)
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        settings_scroll.setWidget(settings)
        splitter.addWidget(settings_scroll)
        splitter.addWidget(right)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([520, 850])

    def choose_source(self) -> None:
        initial_dir = self.source_dir.text().strip() or str(Path.home() / "Downloads")
        if not Path(initial_dir).is_dir():
            initial_dir = str(Path.home() / "Downloads")
        folder = QFileDialog.getExistingDirectory(
            self,
            "Pasta de origem",
            initial_dir,
        )
        if folder:
            self.source_dir.setText(folder)
            self.refresh_files()

    def choose_products_dir(self) -> None:
        initial_dir = self.products_dir.text().strip() or str(Path.home() / "Downloads")
        if not Path(initial_dir).is_dir():
            initial_dir = str(Path.home() / "Downloads")
        folder = QFileDialog.getExistingDirectory(
            self,
            "Pasta de destino",
            initial_dir,
        )
        if folder:
            self.products_dir.setText(folder)

    def start_dictation(
        self,
        target: QTextEdit,
        button: QPushButton,
        status: QLabel | None = None,
    ) -> None:
        cancel_event = getattr(self, "_dictation_cancel_event", None)
        if cancel_event is not None:
            cancel_event.set()
            button.setEnabled(False)
            button.setText("Parando...")
            if status is not None:
                status.setText("Encerrando a gravação...")
            return

        self._dictation_cancel_event = Event()
        self._dictation_phase = 0
        self._dictation_timer = QTimer(self)
        self._dictation_timer.timeout.connect(
            lambda: self._animate_dictation(button, status)
        )
        self._dictation_timer.start(350)
        button.setEnabled(True)
        button.setText("■ Parar gravação")
        if status is not None:
            status.setText("Gravando... fale agora")
        self.start_task(
            reconhecer_microfone,
            cancel_event=self._dictation_cancel_event,
            on_done=lambda text: self.dictation_finished(
                target,
                button,
                text,
                status,
            ),
            on_error=lambda error: self.dictation_failed(button, error, status),
            on_cancel=lambda message: self.dictation_cancelled(
                button,
                status,
                message,
            ),
        )

    def _animate_dictation(
        self,
        button: QPushButton,
        status: QLabel | None,
    ) -> None:
        if status is None:
            return
        phase = getattr(self, "_dictation_phase", 0)
        status.setText(f"Gravando{'.' * (phase % 4)} fale agora")
        self._dictation_phase = phase + 1

    def _finish_dictation_ui(
        self,
        button: QPushButton,
        status: QLabel | None,
    ) -> None:
        timer = getattr(self, "_dictation_timer", None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()
            self._dictation_timer = None
        self._dictation_cancel_event = None
        button.setEnabled(True)
        button.setText("🎤 Gravar")
        if status is not None:
            status.setText("Pronto para gravar")

    def dictation_finished(
        self,
        target: QTextEdit,
        button: QPushButton,
        text: object,
    ) -> None:
        atual = target.toPlainText().strip()
        transcricao = str(text).strip()
        target.setPlainText(
            f"{atual} {transcricao}".strip() if atual else transcricao
        )
        button.setEnabled(True)
        button.setText("Microfone")

    def dictation_failed(self, button: QPushButton, error: str) -> None:
        button.setEnabled(True)
        button.setText("Microfone")
        self.log.appendPlainText(error)
        from PySide6.QtWidgets import QMessageBox

        mensagem = error.strip().splitlines()[-1] if error.strip() else (
            "Não foi possível usar o microfone."
        )
        QMessageBox.warning(self, "Microfone", mensagem)
        from PySide6.QtWidgets import QMessageBox

        mensagem = error.strip().splitlines()[-1] if error.strip() else (
            "Não foi possível usar o microfone."
        )
        QMessageBox.warning(self, "Microfone", mensagem)

    def update_classification_visibility(self) -> None:
        is_unique = self.product_type.currentText() == "Único"
        has_kit = self.also_kit.currentText() == "Sim"
        self.variation_label.setVisible(is_unique)
        self.variations.setVisible(is_unique)
        self.also_kit_label.setVisible(is_unique)
        self.also_kit.setVisible(is_unique)
        show_kit_fields = not is_unique or has_kit
        self.kit_pieces_label.setVisible(show_kit_fields)
        self.kit_pieces.setVisible(show_kit_fields)
        self.kit_variation_label.setVisible(not is_unique)
        self.kit_variation.setVisible(not is_unique)
        self.kit_count_label.setVisible(show_kit_fields)
        self.kit_count.setVisible(show_kit_fields)

    def refresh_files(self) -> None:
        self.files = listar_imagens(self.source_dir.text().strip())
        if not self.files:
            self.files_label.setText("Nenhuma imagem ou vídeo encontrado.")
        else:
            self.files_label.setText(
                f"{len(self.files)} arquivo(s), ordenados por nome."
            )
        self.media_gallery.update_files(
            self.files,
            self.source_dir.text().strip(),
        )
        self.rebuild_measurements()

    def clear_measurements(self) -> None:
        self.measurement_rows.clear()
        while self.measurement_layout.count():
            item = self.measurement_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def rebuild_measurements(self) -> None:
        self.clear_measurements()
        images = [
            nome
            for nome in self.files
            if nome.lower().endswith(IMAGE_EXTENSIONS)
        ]
        tipo = self.product_type.currentText()
        variations = int(self.variations.currentText())
        also_kit = self.also_kit.currentText()
        kit_pieces = int(self.kit_pieces.currentText())
        kit_count = int(self.kit_count.currentText())

        groups: list[tuple[str, list[str]]] = []
        if tipo == "Único" and variations == 1 and also_kit == "Não":
            groups.append(("Produto único", images))
        elif tipo == "Único" and also_kit == "Não":
            per_group = max(1, len(images) // variations)
            for index in range(variations):
                start = index * per_group
                end = len(images) if index == variations - 1 else start + per_group
                groups.append((f"Variação {index + 1}", images[start:end]))
        elif tipo == "Kit":
            per_kit = 1 + kit_pieces
            expected = per_kit * kit_count
            for index, name in enumerate(images[:expected]):
                inside = index % per_kit
                title = (
                    f"Kit completo {index // per_kit + 1}"
                    if inside == 0
                    else f"Kit {index // per_kit + 1} - peça {inside}"
                )
                groups.append((title, [name]))
        else:
            per_kit = 1 + kit_pieces
            total_kit = per_kit * kit_count
            unique_images = images[:-total_kit] if len(images) > total_kit else []
            kit_images = images[-total_kit:] if len(images) >= total_kit else []
            if variations == 1:
                groups.append(("Produto único", unique_images))
            else:
                per_group = max(1, len(unique_images) // variations)
                for index in range(variations):
                    start = index * per_group
                    end = len(unique_images) if index == variations - 1 else start + per_group
                    groups.append((f"Variação {index + 1}", unique_images[start:end]))
            for index, name in enumerate(kit_images):
                inside = index % per_kit
                title = (
                    f"Kit completo {index // per_kit + 1}"
                    if inside == 0
                    else f"Kit {index // per_kit + 1} - peça {inside}"
                )
                groups.append((title, [name]))

        source = Path(self.source_dir.text().strip())
        for title, group in groups:
            if not group:
                continue
            box = QGroupBox(title)
            box_layout = QVBoxLayout(box)
            if len(group) == 1:
                row = MeasurementRow(group[0], source / group[0])
                self.measurement_rows.append(row)
                box_layout.addWidget(row)
            else:
                shared = MeasurementRow(
                    f"{len(group)} imagens compartilham estas medidas",
                    source / group[0],
                    title,
                )
                self.measurement_rows.append(shared)
                box_layout.addWidget(shared)
                names = QLabel("Arquivos: " + ", ".join(group))
                names.setWordWrap(True)
                box_layout.addWidget(names)
            self.measurement_layout.addWidget(box)
        self.update_summary()

    def update_summary(self) -> None:
        variations = int(self.variations.currentText())
        kit_pieces = int(self.kit_pieces.currentText())
        kit_count = int(self.kit_count.currentText())
        if self.product_type.currentText() == "Kit":
            total = (1 + kit_pieces) * kit_count
            text = (
                f"Kit de {kit_pieces} peças: "
                f"{kit_count} grupo(s), {total} fotos esperadas."
            )
        elif self.also_kit.currentText() == "Sim":
            text = (
                f"Produto único com {variations} variação(ões) "
                f"e kits de {kit_pieces} peças."
            )
        else:
            text = f"Produto único com {variations} bloco(s) de medidas."
        self.summary.setText(text)

    def collect_data(self) -> list[tuple[str, str, str, str, str]]:
        data: list[tuple[str, str, str, str, str]] = []
        for row in self.measurement_rows:
            values = row.values()
            filename = values[0]
            if filename not in self.files:
                continue
            data.append(values)

        images = [
            name
            for name in self.files
            if name.lower().endswith(IMAGE_EXTENSIONS)
        ]
        variations = int(self.variations.currentText())
        kit_pieces = int(self.kit_pieces.currentText())
        kit_count = int(self.kit_count.currentText())
        if self.product_type.currentText() == "Único" and self.also_kit.currentText() == "Não":
            if variations == 1 and self.measurement_rows:
                values = self.measurement_rows[0].values()[1:]
                return [(name, *values) for name in images]
            expanded: list[tuple[str, str, str, str, str]] = []
            per_group = max(1, len(images) // variations)
            for index in range(variations):
                start = index * per_group
                end = len(images) if index == variations - 1 else start + per_group
                if index >= len(self.measurement_rows):
                    break
                values = self.measurement_rows[index].values()[1:]
                expanded.extend((name, *values) for name in images[start:end])
            return expanded

        if self.product_type.currentText() == "Único" and self.also_kit.currentText() == "Sim":
            kit_size = (1 + kit_pieces) * kit_count
            unique_images = images[:-kit_size] if len(images) > kit_size else []
            kit_images = images[-kit_size:] if len(images) >= kit_size else []
            result: list[tuple[str, str, str, str, str]] = []
            cursor = 0
            if variations == 1 and self.measurement_rows:
                values = self.measurement_rows[cursor].values()[1:]
                cursor += 1
                result.extend((name, *values) for name in unique_images)
            else:
                per_group = max(1, len(unique_images) // variations)
                for index in range(variations):
                    start = index * per_group
                    end = len(unique_images) if index == variations - 1 else start + per_group
                    if cursor >= len(self.measurement_rows):
                        break
                    values = self.measurement_rows[cursor].values()[1:]
                    cursor += 1
                    result.extend((name, *values) for name in unique_images[start:end])
            for name in kit_images:
                if cursor >= len(self.measurement_rows):
                    break
                result.append((name, *self.measurement_rows[cursor].values()[1:]))
                cursor += 1
            return result

        return data

    def save_product(self) -> None:
        produto = self.product_name.text().strip()
        origem = self.source_dir.text().strip()
        descricao = self.description.toPlainText().strip()
        if not produto or not origem or not descricao:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self,
                "Dados incompletos",
                "Preencha nome, pasta de origem e descrição.",
            )
            return
        if not self.files:
            self.refresh_files()
        dados = self.collect_data()
        if not dados:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "Sem imagens", "Nenhuma imagem para processar.")
            return
        destino = Path(self.products_dir.text().strip()) / produto.upper()
        self.save_button.setEnabled(False)
        self.start_task(
            salvar_cadastro_task,
            origem,
            str(destino),
            self.files,
            dados,
            produto,
            descricao,
            self.usage.toPlainText().strip(),
            self.accompanies.text().strip(),
            self.finish.checked_text(),
            self.product_type.currentText(),
            int(self.variations.currentText()),
            self.also_kit.currentText(),
            int(self.kit_pieces.currentText()),
            int(self.kit_pieces.currentText()),
            self.kit_variation.currentText(),
            int(self.kit_count.currentText()),
            self.proportion.currentText(),
            on_done=self.save_finished,
            on_error=self.save_failed,
        )

    def save_finished(self, result: object) -> None:
        from PySide6.QtWidgets import QMessageBox

        self.save_button.setEnabled(True)
        self.log.appendPlainText(f"Produto salvo em: {result}")
        self.on_saved()
        QMessageBox.information(self, "Concluído", "Cadastro salvo com sucesso.")

    def save_failed(self, error: str) -> None:
        from PySide6.QtWidgets import QMessageBox

        self.save_button.setEnabled(True)
        self.log.appendPlainText(error)
        QMessageBox.critical(self, "Erro no cadastro", error)

"""Tela de cadastro de produtos da aplicação desktop PySide6."""

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import (
    QDesktopServices,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from _APP_.PySide6_core import (
    BackgroundMixin,
    DEFAULT_PRODUCTS_DIR,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    listar_imagens,
    reconhecer_microfone as _legacy_reconhecer_microfone,
    salvar_cadastro_task,
)


class CheckableComboBox(QComboBox):
    """QComboBox com seleção múltipla, equivalente ao multiselect do Streamlit."""

    def __init__(self, items: list[str]):
        super().__init__()
        model = QStandardItemModel(self)
        for text in items:
            item = QStandardItem(text)
            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
            )
            item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
            model.appendRow(item)
        self.setModel(model)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setPlaceholderText("Selecione os acabamentos")
        self.view().pressed.connect(self._toggle_item)
        self._refresh_text()

    def _toggle_item(self, index) -> None:
        item = self.model().itemFromIndex(index)
        state = (
            Qt.CheckState.Unchecked
            if item.checkState() == Qt.CheckState.Checked
            else Qt.CheckState.Checked
        )
        item.setCheckState(state)
        self._refresh_text()

    def _refresh_text(self) -> None:
        self.lineEdit().setText(", ".join(self.checked_items()))

    def checked_items(self) -> list[str]:
        return [
            self.model().item(index).text()
            for index in range(self.model().rowCount())
            if self.model().item(index).checkState() == Qt.CheckState.Checked
        ]

    def checked_text(self) -> str:
        return ", ".join(self.checked_items())


class MediaGallery(QWidget):
    """Galeria horizontal com todas as imagens e vídeos encontrados."""

    def __init__(self, title: str = "Mídias encontradas"):
        super().__init__()
        self.source_dir = Path()
        self.setMinimumHeight(185)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(QLabel(f"<b>{title}</b>"))

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.container = QWidget()
        self.container.setMinimumHeight(145)
        self.layout = QHBoxLayout(self.container)
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(8)
        self.scroll.setWidget(self.container)
        self.scroll.setMinimumHeight(150)
        root.addWidget(self.scroll)
        self.show_empty()

    def clear(self) -> None:
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def show_empty(self) -> None:
        self.clear()
        self.layout.addWidget(QLabel("Nenhuma imagem ou vídeo encontrado."))
        self.layout.addStretch()
        self.container.adjustSize()

    def update_files(self, files: list[str], source_dir: str) -> None:
        self.clear()
        self.source_dir = Path(source_dir)
        if not files:
            self.show_empty()
            return

        for name in files:
            path = self.source_dir / name
            card = QWidget()
            card.setFixedSize(160, 140)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(2, 2, 2, 2)
            card_layout.setSpacing(2)
            if path.suffix.lower() in VIDEO_EXTENSIONS:
                preview = QPushButton(f"▶\nVÍDEO\n{name}")
                preview.setToolTip(f"Abrir vídeo: {name}")
                preview.setFixedSize(150, 105)
                preview.clicked.connect(
                    lambda checked=False, file_path=path: QDesktopServices.openUrl(
                        QUrl.fromLocalFile(str(file_path))
                    )
                )
            else:
                preview = QLabel()
                preview.setFixedSize(150, 105)
                preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
                pixmap = QPixmap(str(path))
                if pixmap.isNull():
                    preview.setText("sem prévia")
                else:
                    preview.setPixmap(
                        pixmap.scaled(
                            145,
                            100,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
            card_layout.addWidget(preview)
            caption = QLabel(name)
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            caption.setWordWrap(True)
            caption.setFixedWidth(150)
            card_layout.addWidget(caption)
            self.layout.addWidget(card)
        self.layout.addStretch()
        self.container.adjustSize()
        self.container.setMinimumWidth(max(180, len(files) * 168 + 12))
        self.container.resize(self.container.sizeHint())


class MeasurementRow(QWidget):
    def __init__(self, filename: str, image_path: Path, title: str = ""):
        super().__init__()
        self.filename = filename
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        preview = QLabel()
        preview.setFixedSize(96, 76)
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = _load_oriented_pixmap(image_path)
        if not pixmap.isNull():
            preview.setPixmap(
                pixmap.scaled(
                    88,
                    68,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            preview.setText("sem prévia")
        layout.addWidget(preview)

        info = QVBoxLayout()
        label = QLabel(f"{title}\n{filename}" if title else filename)
        label.setWordWrap(True)
        label.setToolTip(
            "Arquivo usado neste grupo de medidas. As medidas serão gravadas no produtos.txt."
        )
        info.addWidget(label)
        inputs = QHBoxLayout()
        self.altura = QLineEdit()
        self.largura = QLineEdit()
        self.espessura = QLineEdit()
        self.peso = QLineEdit()
        for widget, placeholder in (
            (self.altura, "Altura"),
            (self.largura, "Largura"),
            (self.espessura, "Espessura"),
            (self.peso, "Peso"),
        ):
            widget.setPlaceholderText(placeholder)
            widget.setMaximumWidth(100)
            widget.setToolTip(
                f"{placeholder} do produto. Informe o valor que será usado no cadastro."
            )
            inputs.addWidget(widget)
        info.addLayout(inputs)
        layout.addLayout(info, 1)

    def values(self) -> tuple[str, str, str, str, str]:
        return (
            self.filename,
            self.altura.text().strip(),
            self.largura.text().strip(),
            self.espessura.text().strip(),
            self.peso.text().strip(),
        )


class CadastroTab(QWidget, BackgroundMixin):
    """Cadastro com configurações à esquerda e mídias/medidas à direita."""

    def __init__(
        self,
        on_saved: Callable[[], None],
        on_open_prompts: Callable[[], None] | None = None,
    ):
        QWidget.__init__(self)
        BackgroundMixin.__init__(self)
        self.on_saved = on_saved
        self.on_open_prompts = on_open_prompts
        self.measurement_rows: list[MeasurementRow] = []
        self.files: list[str] = []
        self.setObjectName("CadastroTab")
        self.build_ui()

    def build_ui(self) -> None:
        root = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        settings = QWidget()
        settings_layout = QVBoxLayout(settings)
        settings_layout.setContentsMargins(4, 4, 8, 4)

        basic = QGroupBox("Configurações do produto")
        basic_layout = QVBoxLayout(basic)
        self.product_name = QLineEdit()
        self.product_name.setToolTip("Nome usado para criar o cadastro do produto.")
        self.source_dir = QLineEdit()
        self.source_dir.setToolTip(
            "Pasta que contém as imagens e os vídeos do produto."
        )
        self.description = QTextEdit()
        self.description.setFixedHeight(150)
        self.description.setToolTip(
            "Descrição do produto. Você pode escrever várias linhas ou usar o microfone."
        )
        self.usage = QTextEdit()
        self.usage.setFixedHeight(150)
        self.usage.setToolTip(
            "Explique como o produto pode ser usado. Você pode escrever várias linhas ou usar o microfone."
        )
        self.accompanies = QLineEdit()
        self.accompanies.setToolTip(
            "Informe o que acompanha o produto. Este campo é texto livre no cadastro original."
        )
        self.finish = CheckableComboBox(
            [
                "lixado",
                "lavado",
                "Vernizado",
                "Impressão a Laiser",
                "Pode ser Estilizado pelo Cliente",
            ]
        )
        self.finish.setToolTip(
            "Selecione um ou mais acabamentos ou trabalhos possíveis para o produto."
        )
        self.proportion = QComboBox()
        self.proportion.addItems(["3:4", "1:1", "4:5", "9:16", "16:9"])
        self.proportion.setToolTip("Proporção usada no processamento das imagens.")
        self.products_dir = QLineEdit(str(DEFAULT_PRODUCTS_DIR))
        self.products_dir.setToolTip(
            "Pasta onde será criada a pasta final do produto cadastrado."
        )

        browse_source = QPushButton("Escolher")
        browse_source.setMaximumWidth(86)
        browse_source.setToolTip("Escolher a pasta que contém as mídias do produto.")
        browse_source.clicked.connect(self.choose_source)
        browse_products = QPushButton("Escolher")
        browse_products.setMaximumWidth(86)
        browse_products.setToolTip("Escolher a pasta de destino do cadastro.")
        browse_products.clicked.connect(self.choose_products_dir)

        def add_labeled_field(
            label: str,
            widget: QWidget,
            button: QPushButton | None = None,
        ) -> None:
            basic_layout.addWidget(QLabel(label))
            row = QHBoxLayout()
            row.addWidget(widget, 1)
            if button:
                row.addWidget(button)
            basic_layout.addLayout(row)

        add_labeled_field("Nome", self.product_name)
        add_labeled_field("Origem", self.source_dir, browse_source)
        add_labeled_field("Destino", self.products_dir, browse_products)
        add_labeled_field("Proporção", self.proportion)
        add_labeled_field("Acompanha", self.accompanies)
        add_labeled_field("Acabamento", self.finish)

        self.usage_mic_button = QPushButton("🎤 Gravar")
        self.usage_mic_button.setMinimumHeight(30)
        self.usage_mic_button.setToolTip(
            "Gravar e transformar em texto o campo 'Como pode ser usado'."
        )
        self.usage_status = QLabel("Pronto para gravar")
        self.usage_mic_button.clicked.connect(
            lambda: self.start_dictation(
                self.usage,
                self.usage_mic_button,
                self.usage_status,
            )
        )
        usage_label = QLabel("Como pode ser usado:")
        usage_label.setToolTip(self.usage.toolTip())
        usage_controls = QHBoxLayout()
        usage_controls.setContentsMargins(0, 0, 0, 0)
        usage_controls.setSpacing(4)
        usage_controls.addWidget(usage_label)
        usage_controls.addWidget(self.usage_mic_button)
        usage_controls.addWidget(self.usage_status, 1)
        usage_row = QVBoxLayout()
        usage_row.setContentsMargins(0, 0, 0, 0)
        usage_row.setSpacing(2)
        usage_row.addLayout(usage_controls)
        usage_row.addWidget(self.usage)
        basic_layout.addLayout(usage_row)

        self.description_mic_button = QPushButton("🎤 Gravar")
        self.description_mic_button.setMinimumHeight(30)
        self.description_mic_button.setToolTip(
            "Gravar e transformar em texto o campo 'Descrição'."
        )
        self.description_status = QLabel("Pronto para gravar")
        self.description_mic_button.clicked.connect(
            lambda: self.start_dictation(
                self.description,
                self.description_mic_button,
                self.description_status,
            )
        )
        description_label = QLabel("Descrição:")
        description_label.setToolTip(self.description.toolTip())
        description_controls = QHBoxLayout()
        description_controls.setContentsMargins(0, 0, 0, 0)
        description_controls.setSpacing(4)
        description_controls.addWidget(description_label)
        description_controls.addWidget(self.description_mic_button)
        description_controls.addWidget(self.description_status, 1)
        description_row = QVBoxLayout()
        description_row.setContentsMargins(0, 0, 0, 0)
        description_row.setSpacing(2)
        description_row.addLayout(description_controls)
        description_row.addWidget(self.description)
        basic_layout.addLayout(description_row)
        settings_layout.addWidget(basic)

        classification = QGroupBox("Classificação")
        self.classification = classification
        classification_layout = QVBoxLayout(classification)
        classification_layout.setContentsMargins(10, 8, 10, 6)
        classification_layout.setSpacing(4)
        self.product_type = QComboBox()
        self.product_type.addItems(["Único", "Kit"])
        self.product_type.setToolTip(
            "Único = um produto com possíveis variações. Kit = conjunto de peças."
        )
        self.variations = QComboBox()
        self.variations.addItems([str(value) for value in range(1, 10)])
        self.variations.setToolTip(
            "1 = todas as fotos compartilham as mesmas medidas. "
            "2 ou mais = cada variação terá seu grupo de medidas."
        )
        self.also_kit = QComboBox()
        self.also_kit.addItems(["Não", "Sim"])
        self.also_kit.setToolTip(
            "O produto único também será vendido como conjunto?"
        )
        self.kit_pieces = QComboBox()
        self.kit_pieces.addItems([str(value) for value in range(2, 11)])
        self.kit_pieces.setToolTip(
            "Quantidade de fotos de peças individuais esperadas em cada kit."
        )
        self.kit_variation = QComboBox()
        self.kit_variation.addItems(
            ["Sem variação", "Tamanho", "Cor", "Peso", "Mista"]
        )
        self.kit_variation.setToolTip(
            "Indicação organizacional da variação das peças do kit. "
            "Não altera a quantidade de campos."
        )
        self.kit_count = QComboBox()
        self.kit_count.addItems([str(value) for value in range(1, 11)])
        self.kit_count.setToolTip(
            "Quantidade de grupos completos de fotos do kit."
        )
        self.variation_label = QLabel("Variações")
        self.also_kit_label = QLabel("Também em kit")
        self.kit_pieces_label = QLabel("Peças no kit")
        self.kit_variation_label = QLabel("Variação do kit")
        self.kit_count_label = QLabel("Quantidade de kits")
        fields = [
            ("Tipo", self.product_type),
            (self.variation_label, self.variations),
            (self.also_kit_label, self.also_kit),
            (self.kit_pieces_label, self.kit_pieces),
            (self.kit_variation_label, self.kit_variation),
            (self.kit_count_label, self.kit_count),
        ]
        classification_controls = QHBoxLayout()
        classification_controls.setContentsMargins(0, 0, 0, 0)
        classification_controls.setSpacing(5)
        for label, widget in fields:
            label_widget = QLabel(label) if isinstance(label, str) else label
            classification_controls.addWidget(label_widget)
            widget.setMinimumWidth(58)
            classification_controls.addWidget(widget, 1)
        classification_layout.addLayout(classification_controls)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        classification_layout.addWidget(self.summary)
        settings_layout.addWidget(classification)

        for widget in (
            self.product_type,
            self.also_kit,
            self.kit_variation,
        ):
            widget.currentTextChanged.connect(self.rebuild_measurements)
        for widget in (self.variations, self.kit_pieces, self.kit_count):
            widget.currentTextChanged.connect(self.rebuild_measurements)
        self.product_type.currentTextChanged.connect(
            self.update_classification_visibility
        )
        self.also_kit.currentTextChanged.connect(
            self.update_classification_visibility
        )
        self.update_classification_visibility()

        actions = QHBoxLayout()
        self.refresh_button = QPushButton("Atualizar mídias")
        self.refresh_button.setMaximumWidth(130)
        self.refresh_button.setToolTip(
            "Ler novamente a pasta de origem, ordenar as mídias e reconstruir os grupos."
        )
        self.refresh_button.clicked.connect(self.refresh_files)
        self.save_button = QPushButton("Processar cadastro")
        self.save_button.setMaximumWidth(145)
        self.save_button.setToolTip(
            "Copiar as mídias, salvar as medidas e gerar o produtos.txt do cadastro."
        )
        self.save_button.clicked.connect(self.save_product)
        actions.addWidget(self.refresh_button)
        actions.addWidget(self.save_button)
        if self.on_open_prompts:
            prompts_button = QPushButton("Prompts")
            prompts_button.setMaximumWidth(82)
            prompts_button.setToolTip(
                "Abrir os prompts pré-configurados usados no cadastro e na produção."
            )
            prompts_button.clicked.connect(self.on_open_prompts)
            actions.addWidget(prompts_button)
        actions.addStretch()
        settings_layout.addLayout(actions)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(1000)
        self.log.setFixedHeight(0)
        self.log.hide()
        self.log.setToolTip("Mensagens do processamento e erros do cadastro.")
        settings_layout.addWidget(self.log)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 4, 4, 4)
        self.files_label = QLabel("Nenhuma pasta selecionada")
        self.files_label.setWordWrap(True)
        right_layout.addWidget(self.files_label)
        self.media_gallery = MediaGallery()
        right_layout.addWidget(self.media_gallery)

        measures_label = QLabel("<b>Grupos de variações, kits e medidas</b>")
        measures_label.setToolTip(
            "Cada grupo corresponde às fotos que compartilharão o mesmo conjunto de medidas."
        )
        right_layout.addWidget(measures_label)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.measurement_container = QWidget()
        self.measurement_layout = QVBoxLayout(self.measurement_container)
        self.measurement_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.measurement_container)
        right_layout.addWidget(scroll, 1)

        settings.setMinimumWidth(500)
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        settings_scroll.setWidget(settings)
        splitter.addWidget(settings_scroll)
        splitter.addWidget(right)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([520, 850])

    def choose_source(self) -> None:
        initial_dir = self.source_dir.text().strip() or str(Path.home() / "Downloads")
        if not Path(initial_dir).is_dir():
            initial_dir = str(Path.home() / "Downloads")
        folder = QFileDialog.getExistingDirectory(
            self,
            "Pasta de origem",
            initial_dir,
        )
        if folder:
            self.source_dir.setText(folder)
            self.refresh_files()

    def choose_products_dir(self) -> None:
        initial_dir = self.products_dir.text().strip() or str(Path.home() / "Downloads")
        if not Path(initial_dir).is_dir():
            initial_dir = str(Path.home() / "Downloads")
        folder = QFileDialog.getExistingDirectory(
            self,
            "Pasta de destino",
            initial_dir,
        )
        if folder:
            self.products_dir.setText(folder)

    def _ao_clicar_microfone_uso(self) -> None:
        self.start_dictation(
            self.usage,
            self.usage_mic_button,
            self.usage_status,
        )

    def _ao_clicar_microfone_descricao(self) -> None:
        self.start_dictation(
            self.description,
            self.description_mic_button,
            self.description_status,
        )

    def start_dictation(
        self,
        target: QTextEdit,
        button: QPushButton,
        status: QLabel,
    ) -> None:
        campo = "uso" if target is self.usage else "descrição"
        agora = monotonic()
        log.info(
            "Cadastro",
            "start_dictation",
            f"clique recebido no botão de microfone; campo={campo}; "
            f"botão='{button.text()}'",
        )
        cancel_event = getattr(self, "_dictation_cancel_event", None)
        if cancel_event is not None:
            active_button = getattr(self, "_dictation_button", None)
            if active_button is not None and button is not active_button:
                log.aviso(
                    "Cadastro",
                    "start_dictation",
                    f"tentativa de iniciar o campo {campo} enquanto "
                    "outro campo ainda está gravando",
                )
                return
            cancel_event.set()
            inicio = getattr(self, "_dictation_started_at", agora)
            duracao_ms = int((agora - inicio) * 1000)
            timer = getattr(self, "_dictation_timer", None)
            if timer is not None:
                timer.stop()
            button.setEnabled(False)
            button.setText("Processando...")
            status.setText("Processando a fala...")
            log.info(
                "Cadastro",
                "start_dictation",
                f"parada solicitada para transcrever o áudio; campo={campo}; "
                f"tempo_desde_inicio={duracao_ms}ms; event_set=True",
            )
            return

        log.info(
            "Cadastro",
            "start_dictation",
            f"iniciando microfone no campo {campo}; "
            "digitação manual permanece disponível",
        )
        self._dictation_cancel_event = Event()
        self._dictation_button = button
        self._dictation_started_at = agora
        self._dictation_phase = 0
        self._dictation_timer = QTimer(self)
        self._dictation_timer.timeout.connect(
            lambda: self._animate_dictation(button, status)
        )
        self._dictation_timer.start(350)
        button.setEnabled(True)
        button.setText("■ Parar gravação")
        status.setText("Gravando... clique novamente para parar")
        self.start_task(
            reconhecer_microfone,
            cancel_event=self._dictation_cancel_event,
            on_done=lambda text: self.dictation_finished(
                target,
                button,
                text,
                status,
            ),
            on_error=lambda error: self.dictation_failed(button, error, status),
            on_cancel=lambda message: self.dictation_cancelled(
                button,
                status,
                message,
            ),
        )
        log.info(
            "Cadastro",
            "start_dictation",
            f"gravação iniciada; campo={campo}; "
            f"tempo_desde_clique={int((monotonic() - agora) * 1000)}ms",
        )

    def _animate_dictation(
        self,
        button: QPushButton,
        status: QLabel,
    ) -> None:
        phase = getattr(self, "_dictation_phase", 0)
        status.setText(
            f"Gravando{'.' * (phase % 4)} clique novamente para parar"
        )
        self._dictation_phase = phase + 1

    def _finish_dictation_ui(
        self,
        button: QPushButton,
        status: QLabel,
    ) -> None:
        timer = getattr(self, "_dictation_timer", None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()
            self._dictation_timer = None
        self._dictation_cancel_event = None
        if getattr(self, "_dictation_button", None) is button:
            self._dictation_button = None
        inicio = getattr(self, "_dictation_started_at", None)
        if inicio is not None:
            duracao_ms = int((monotonic() - inicio) * 1000)
            log.info(
                "Cadastro",
                "_finish_dictation_ui",
                f"interface do microfone liberada; duração_total={duracao_ms}ms",
            )
        self._dictation_started_at = None
        button.setEnabled(True)
        button.setText("🎤 Gravar")
        status.setText("Pronto para gravar")

    def dictation_finished(
        self,
        target: QTextEdit,
        button: QPushButton,
        text: object,
        status: QLabel | None = None,
    ) -> None:
        self._finish_dictation_ui(button, status)
        atual = target.toPlainText().strip()
        transcricao = str(text).strip()
        campo = "uso" if target is self.usage else "descrição"
        log.info(
            "Cadastro",
            "dictation_finished",
            f"transcrição recebida para o campo {campo}: "
            f"{len(transcricao)} caracteres",
        )
        if not transcricao:
            log.aviso(
                "Cadastro",
                "dictation_finished",
                f"transcrição vazia no campo {campo}",
            )
            if status is not None:
                status.setText("Nenhum texto foi reconhecido.")
            return
        target.setPlainText(
            f"{atual} {transcricao}".strip() if atual else transcricao
        )
        if status is not None:
            status.setText("Texto inserido no campo.")

    def dictation_failed(
        self,
        button: QPushButton,
        error: str,
        status: QLabel | None = None,
    ) -> None:
        self._finish_dictation_ui(button, status)
        log.erro(
            "Cadastro",
            "dictation_failed",
            f"falha no microfone: {error.strip()}",
        )
        from PySide6.QtWidgets import QMessageBox

        detalhe = self._mensagem_microfone(error)
        if status is not None:
            status.setText(detalhe)
        QMessageBox.warning(self, "Microfone", detalhe)

    def dictation_cancelled(
        self,
        button: QPushButton,
        status: QLabel | None = None,
        message: str = "Gravação cancelada.",
    ) -> None:
        self._finish_dictation_ui(button, status)
        log.aviso(
            "Cadastro",
            "dictation_cancelled",
            f"cancelamento normal solicitado pelo usuário: {message}",
        )
        if status is not None:
            status.setText("Gravação cancelada.")

    @staticmethod
    def _mensagem_microfone(error: str) -> str:
        """Converte detalhes técnicos do log em uma mensagem curta para a UI."""
        texto = error.lower()
        if "speechrecognition" in texto or "pyaudio" in texto:
            return (
                "Não foi possível iniciar o microfone. "
                "Verifique o suporte de áudio instalado."
            )
        if "serviço de reconhecimento" in texto:
            return "O serviço de reconhecimento de voz não respondeu."
        if "não foi possível entender" in texto:
            return "Não foi possível entender o áudio."
        if "nenhuma fala" in texto:
            return "Nenhuma fala foi capturada."
        if "dispositivo" in texto or "permiss" in texto:
            return (
                "Não foi possível acessar o microfone. "
                "Verifique o dispositivo e as permissões do Windows."
            )
        return (
            "Não foi possível usar o microfone. "
            "Verifique o dispositivo e as permissões do Windows."
        )
    def update_classification_visibility(self) -> None:
        is_unique = self.product_type.currentText() == "Único"
        has_kit = self.also_kit.currentText() == "Sim"
        self.variation_label.setVisible(is_unique)
        self.variations.setVisible(is_unique)
        self.also_kit_label.setVisible(is_unique)
        self.also_kit.setVisible(is_unique)
        show_kit_fields = not is_unique or has_kit
        self.kit_pieces_label.setVisible(show_kit_fields)
        self.kit_pieces.setVisible(show_kit_fields)
        self.kit_variation_label.setVisible(not is_unique)
        self.kit_variation.setVisible(not is_unique)
        self.kit_count_label.setVisible(show_kit_fields)
        self.kit_count.setVisible(show_kit_fields)

    def refresh_files(self) -> None:
        self.files = listar_imagens(self.source_dir.text().strip())
        if not self.files:
            self.files_label.setText("Nenhuma imagem ou vídeo encontrado.")
        else:
            self.files_label.setText(
                f"{len(self.files)} arquivo(s), ordenados por nome."
            )
        self.media_gallery.update_files(
            self.files,
            self.source_dir.text().strip(),
        )
        self.rebuild_measurements()

    def clear_measurements(self) -> None:
        self.measurement_rows.clear()
        while self.measurement_layout.count():
            item = self.measurement_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def rebuild_measurements(self) -> None:
        self.clear_measurements()
        images = [
            nome
            for nome in self.files
            if nome.lower().endswith(IMAGE_EXTENSIONS)
        ]
        tipo = self.product_type.currentText()
        variations = int(self.variations.currentText())
        also_kit = self.also_kit.currentText()
        kit_pieces = int(self.kit_pieces.currentText())
        kit_count = int(self.kit_count.currentText())

        groups: list[tuple[str, list[str]]] = []
        if tipo == "Único" and variations == 1 and also_kit == "Não":
            groups.append(("Produto único", images))
        elif tipo == "Único" and also_kit == "Não":
            per_group = max(1, len(images) // variations)
            for index in range(variations):
                start = index * per_group
                end = len(images) if index == variations - 1 else start + per_group
                groups.append((f"Variação {index + 1}", images[start:end]))
        elif tipo == "Kit":
            per_kit = 1 + kit_pieces
            expected = per_kit * kit_count
            for index, name in enumerate(images[:expected]):
                inside = index % per_kit
                title = (
                    f"Kit completo {index // per_kit + 1}"
                    if inside == 0
                    else f"Kit {index // per_kit + 1} - peça {inside}"
                )
                groups.append((title, [name]))
        else:
            per_kit = 1 + kit_pieces
            total_kit = per_kit * kit_count
            unique_images = images[:-total_kit] if len(images) > total_kit else []
            kit_images = images[-total_kit:] if len(images) >= total_kit else []
            if variations == 1:
                groups.append(("Produto único", unique_images))
            else:
                per_group = max(1, len(unique_images) // variations)
                for index in range(variations):
                    start = index * per_group
                    end = len(unique_images) if index == variations - 1 else start + per_group
                    groups.append((f"Variação {index + 1}", unique_images[start:end]))
            for index, name in enumerate(kit_images):
                inside = index % per_kit
                title = (
                    f"Kit completo {index // per_kit + 1}"
                    if inside == 0
                    else f"Kit {index // per_kit + 1} - peça {inside}"
                )
                groups.append((title, [name]))

        source = Path(self.source_dir.text().strip())
        for title, group in groups:
            if not group:
                continue
            box = QGroupBox(title)
            box_layout = QVBoxLayout(box)
            if len(group) == 1:
                row = MeasurementRow(group[0], source / group[0])
                self.measurement_rows.append(row)
                box_layout.addWidget(row)
            else:
                shared = MeasurementRow(
                    f"{len(group)} imagens compartilham estas medidas",
                    source / group[0],
                    title,
                )
                self.measurement_rows.append(shared)
                box_layout.addWidget(shared)
                names = QLabel("Arquivos: " + ", ".join(group))
                names.setWordWrap(True)
                box_layout.addWidget(names)
            self.measurement_layout.addWidget(box)
        self.update_summary()

    def update_summary(self) -> None:
        variations = int(self.variations.currentText())
        kit_pieces = int(self.kit_pieces.currentText())
        kit_count = int(self.kit_count.currentText())
        if self.product_type.currentText() == "Kit":
            total = (1 + kit_pieces) * kit_count
            text = (
                f"Kit de {kit_pieces} peças: "
                f"{kit_count} grupo(s), {total} fotos esperadas."
            )
        elif self.also_kit.currentText() == "Sim":
            text = (
                f"Produto único com {variations} variação(ões) "
                f"e kits de {kit_pieces} peças."
            )
        else:
            text = f"Produto único com {variations} bloco(s) de medidas."
        self.summary.setText(text)

    def collect_data(self) -> list[tuple[str, str, str, str, str]]:
        data: list[tuple[str, str, str, str, str]] = []
        for row in self.measurement_rows:
            values = row.values()
            filename = values[0]
            if filename not in self.files:
                continue
            data.append(values)

        images = [
            name
            for name in self.files
            if name.lower().endswith(IMAGE_EXTENSIONS)
        ]
        variations = int(self.variations.currentText())
        kit_pieces = int(self.kit_pieces.currentText())
        kit_count = int(self.kit_count.currentText())
        if self.product_type.currentText() == "Único" and self.also_kit.currentText() == "Não":
            if variations == 1 and self.measurement_rows:
                values = self.measurement_rows[0].values()[1:]
                return [(name, *values) for name in images]
            expanded: list[tuple[str, str, str, str, str]] = []
            per_group = max(1, len(images) // variations)
            for index in range(variations):
                start = index * per_group
                end = len(images) if index == variations - 1 else start + per_group
                if index >= len(self.measurement_rows):
                    break
                values = self.measurement_rows[index].values()[1:]
                expanded.extend((name, *values) for name in images[start:end])
            return expanded

        if self.product_type.currentText() == "Único" and self.also_kit.currentText() == "Sim":
            kit_size = (1 + kit_pieces) * kit_count
            unique_images = images[:-kit_size] if len(images) > kit_size else []
            kit_images = images[-kit_size:] if len(images) >= kit_size else []
            result: list[tuple[str, str, str, str, str]] = []
            cursor = 0
            if variations == 1 and self.measurement_rows:
                values = self.measurement_rows[cursor].values()[1:]
                cursor += 1
                result.extend((name, *values) for name in unique_images)
            else:
                per_group = max(1, len(unique_images) // variations)
                for index in range(variations):
                    start = index * per_group
                    end = len(unique_images) if index == variations - 1 else start + per_group
                    if cursor >= len(self.measurement_rows):
                        break
                    values = self.measurement_rows[cursor].values()[1:]
                    cursor += 1
                    result.extend((name, *values) for name in unique_images[start:end])
            for name in kit_images:
                if cursor >= len(self.measurement_rows):
                    break
                result.append((name, *self.measurement_rows[cursor].values()[1:]))
                cursor += 1
            return result

        return data

    def save_product(self) -> None:
        produto = self.product_name.text().strip()
        origem = self.source_dir.text().strip()
        descricao = self.description.toPlainText().strip()
        if not produto or not origem or not descricao:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self,
                "Dados incompletos",
                "Preencha nome, pasta de origem e descrição.",
            )
            return
        if not self.files:
            self.refresh_files()
        dados = self.collect_data()
        if not dados:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "Sem imagens", "Nenhuma imagem para processar.")
            return
        destino = Path(self.products_dir.text().strip()) / produto.upper()
        self.save_button.setEnabled(False)
        self.start_task(
            salvar_cadastro_task,
            origem,
            str(destino),
            self.files,
            dados,
            produto,
            descricao,
            self.usage.toPlainText().strip(),
            self.accompanies.text().strip(),
            self.finish.checked_text(),
            self.product_type.currentText(),
            int(self.variations.currentText()),
            self.also_kit.currentText(),
            int(self.kit_pieces.currentText()),
            int(self.kit_pieces.currentText()),
            self.kit_variation.currentText(),
            int(self.kit_count.currentText()),
            self.proportion.currentText(),
            on_done=self.save_finished,
            on_error=self.save_failed,
        )

    def save_finished(self, result: object) -> None:
        from PySide6.QtWidgets import QMessageBox

        self.save_button.setEnabled(True)
        log.info("Cadastro", "save_finished", f"produto salvo em: {result}")
        self.on_saved()
        QMessageBox.information(self, "Concluído", "Cadastro salvo com sucesso.")

    def save_failed(self, error: str) -> None:
        from PySide6.QtWidgets import QMessageBox

        self.save_button.setEnabled(True)
        log.erro("Cadastro", "save_failed", error.strip())
        QMessageBox.critical(
            self,
            "Erro no cadastro",
            "Não foi possível salvar o cadastro. Consulte o arquivo de log.",
        )