"""Aba para tratar imagens e vídeos sem executar a Criação completa."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from _APP_.PySide6_core import BackgroundMixin
from _APP_.product_lifecycle import listar_produtos_para_midias_avulsas
from _APPDATA_ import appdata
from .processor import (
    MEASURE_TYPES,
    VIDEO_EXTENSIONS,
    converter_video_avulso,
    processar_imagens_avulsas,
)


class MidiasAvulsasTab(QWidget, BackgroundMixin):
    """Executa o tratamento avulso sem mexer no manifesto ou no banco."""

    def __init__(self, parent=None) -> None:
        QWidget.__init__(self, parent)
        BackgroundMixin.__init__(self)
        appdata.inicializar()
        self._processing = False
        self._build_ui()
        self.refresh_destinations()
        self.refresh_resources()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        root.addWidget(
            QLabel(
                "<b>Processamento avulso</b> · trate imagens ou vídeos "
                "sem iniciar a Criação completa."
            )
        )

        destination_box = QGroupBox("Destino das cópias")
        destination_form = QFormLayout(destination_box)
        self.product_destination = QComboBox()
        self.product_destination.currentIndexChanged.connect(
            self._product_destination_changed
        )
        destination_form.addRow("Produto cadastrado (opcional):", self.product_destination)

        destination_row = QHBoxLayout()
        self.destination_path = QLineEdit()
        self.destination_path.setPlaceholderText(
            "Selecione um produto ou uma pasta de destino"
        )
        self.destination_path.setReadOnly(True)
        choose_destination = QPushButton("Escolher pasta…")
        choose_destination.clicked.connect(self._choose_destination)
        refresh_products = QPushButton("Atualizar lista")
        refresh_products.clicked.connect(self.refresh_destinations)
        destination_row.addWidget(self.destination_path, 1)
        destination_row.addWidget(choose_destination)
        destination_row.addWidget(refresh_products)
        destination_form.addRow("Pasta:", destination_row)
        note = QLabel(
            "Os resultados ficam separados em H_Arq_avulsas, dentro desta pasta. "
            "O Cadastro, .ordem_midias.json e produtos.txt não serão alterados."
        )
        note.setWordWrap(True)
        destination_form.addRow(note)
        root.addWidget(destination_box)

        image_box = QGroupBox("Imagens")
        image_layout = QVBoxLayout(image_box)
        image_layout.addWidget(
            QLabel(
                "Adicione uma ou mais imagens do mesmo produto. A aba melhora "
                "a imagem, remove o fundo, cria uma cópia em branco e desenha "
                "as medidas informadas. Todas as imagens de uma rodada usam "
                "as mesmas medidas."
            )
        )
        self.image_list = QListWidget()
        self.image_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        self.image_list.setMinimumHeight(76)
        image_layout.addWidget(self.image_list)
        image_actions = QHBoxLayout()
        add_images = QPushButton("Adicionar imagens…")
        add_images.clicked.connect(self._add_images)
        remove_images = QPushButton("Remover selecionadas")
        remove_images.clicked.connect(self._remove_selected_images)
        clear_images = QPushButton("Limpar lista")
        clear_images.clicked.connect(self.image_list.clear)
        image_actions.addWidget(add_images)
        image_actions.addWidget(remove_images)
        image_actions.addWidget(clear_images)
        image_actions.addStretch()
        image_layout.addLayout(image_actions)

        measurements = QGroupBox("Medidas do produto")
        measure_form = QFormLayout(measurements)
        self.measure_type = QComboBox()
        self.measure_type.addItems(MEASURE_TYPES)
        self.measure_type.currentTextChanged.connect(
            self._measure_type_changed
        )
        self.height_input = QLineEdit()
        self.height_input.setPlaceholderText("Ex.: 7")
        self.width_input = QLineEdit()
        self.width_input.setPlaceholderText("Ex.: 5")
        self.width_label = QLabel("Largura (cm):")
        self.third_dimension_input = QLineEdit()
        self.third_dimension_input.setPlaceholderText("Ex.: 2")
        self.third_dimension_label = QLabel("Espessura (cm):")
        self.weight_input = QLineEdit()
        self.weight_input.setPlaceholderText("Opcional; em gramas")
        self.measure_background = QComboBox()
        self.measure_background.addItem("Branco puro", "")
        measure_form.addRow("Tipo de medida:", self.measure_type)
        measure_form.addRow("Altura (cm):", self.height_input)
        measure_form.addRow(self.width_label, self.width_input)
        measure_form.addRow(
            self.third_dimension_label,
            self.third_dimension_input,
        )
        measure_form.addRow("Peso (g):", self.weight_input)
        measure_form.addRow("Fundo das medidas:", self.measure_background)
        image_layout.addWidget(measurements)

        self.process_images_button = QPushButton("Processar imagens")
        self.process_images_button.clicked.connect(self._process_images)
        image_layout.addWidget(self.process_images_button, 0, Qt.AlignmentFlag.AlignRight)
        root.addWidget(image_box)

        video_box = QGroupBox("Vídeo")
        video_layout = QVBoxLayout(video_box)
        video_row = QHBoxLayout()
        self.video_path = QLineEdit()
        self.video_path.setReadOnly(True)
        self.video_path.setPlaceholderText("Selecione um vídeo")
        choose_video = QPushButton("Escolher vídeo…")
        choose_video.clicked.connect(self._choose_video)
        video_row.addWidget(self.video_path, 1)
        video_row.addWidget(choose_video)
        video_layout.addLayout(video_row)

        video_form = QFormLayout()
        self.music_choice = QComboBox()
        self.music_choice.currentIndexChanged.connect(
            self._music_selection_changed
        )
        self.music_volume = QComboBox()
        self.music_volume.addItems(["0", "0.15", "0.25", "0.55", "0.80"])
        self.music_volume.setCurrentText("0.25")
        video_form.addRow("Música:", self.music_choice)
        video_form.addRow("Volume:", self.music_volume)
        video_layout.addLayout(video_form)
        self.convert_video_button = QPushButton("Converter vídeo")
        self.convert_video_button.clicked.connect(self._convert_video)
        video_layout.addWidget(
            self.convert_video_button,
            0,
            Qt.AlignmentFlag.AlignRight,
        )
        root.addWidget(video_box)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFormat("Processando…")
        self.progress.hide()
        root.addWidget(self.progress)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("O andamento e os arquivos gerados aparecerão aqui.")
        root.addWidget(self.log, 1)

        self._measure_type_changed(self.measure_type.currentText())

    def refresh_destinations(self) -> None:
        selected_path = self.destination_path.text().strip()
        self.product_destination.blockSignals(True)
        self.product_destination.clear()
        self.product_destination.addItem("Selecione um produto cadastrado…", "")
        try:
            rows = listar_produtos_para_midias_avulsas()
        except FileNotFoundError:
            rows = []
        except Exception as exc:
            rows = []
            self.log.appendPlainText(
                f"Não foi possível carregar os produtos cadastrados: {exc}"
            )
        for row in rows:
            product = str(row[0] or "").strip()
            path = str(row[2] or "").strip()
            if product and path:
                self.product_destination.addItem(product, path)
        self.product_destination.blockSignals(False)
        if selected_path:
            index = self.product_destination.findData(selected_path)
            if index >= 0:
                self.product_destination.setCurrentIndex(index)

    def refresh_resources(self) -> None:
        selected_background = self.measure_background.currentData()
        self.measure_background.clear()
        self.measure_background.addItem("Branco puro", "")
        for name in appdata.listar_midias("fundo_medida"):
            path = str(Path(appdata.pasta_midia_categoria("fundo_medida")) / name)
            self.measure_background.addItem(name, path)
        background_index = self.measure_background.findData(selected_background)
        if background_index >= 0:
            self.measure_background.setCurrentIndex(background_index)

        selected_music = self.music_choice.currentData()
        self.music_choice.clear()
        self.music_choice.addItem("Sem música", "")
        for name in appdata.listar_midias("musica"):
            path = str(Path(appdata.pasta_midia_categoria("musica")) / name)
            self.music_choice.addItem(name, path)
        music_index = self.music_choice.findData(selected_music)
        if music_index >= 0:
            self.music_choice.setCurrentIndex(music_index)
        elif self.music_choice.count() > 1:
            self.music_choice.setCurrentIndex(1)
        self._music_selection_changed(self.music_choice.currentIndex())

    def _product_destination_changed(self, index: int) -> None:
        path = str(self.product_destination.itemData(index) or "").strip()
        if path:
            self.destination_path.setText(path)

    def _choose_destination(self) -> None:
        current = self.destination_path.text().strip()
        folder = QFileDialog.getExistingDirectory(
            self,
            "Escolher pasta de destino",
            current or str(Path.home()),
        )
        if folder:
            self.destination_path.setText(folder)

    def _add_images(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Selecionar imagens",
            str(Path.home()),
            "Imagens (*.jpg *.jpeg *.png *.webp)",
        )
        existing = {
            str(self.image_list.item(index).data(Qt.ItemDataRole.UserRole))
            for index in range(self.image_list.count())
        }
        for path in paths:
            if path in existing:
                continue
            item = QListWidgetItem(path)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.image_list.addItem(item)
            existing.add(path)

    def _remove_selected_images(self) -> None:
        for item in self.image_list.selectedItems():
            self.image_list.takeItem(self.image_list.row(item))

    def _measure_type_changed(self, value: str) -> None:
        diameter = "diam" in str(value).casefold()
        self.width_label.setText(
            "Diâmetro (cm):" if diameter else "Largura (cm):"
        )
        needs_third = value != "alt x diam"
        self.third_dimension_label.setVisible(needs_third)
        self.third_dimension_input.setVisible(needs_third)
        self.third_dimension_input.setEnabled(needs_third)
        if value == "alt x larg x comp":
            self.third_dimension_label.setText("Comprimento (cm):")
        else:
            self.third_dimension_label.setText("Espessura (cm):")

    def _music_selection_changed(self, _index: int) -> None:
        has_music = bool(self.music_choice.currentData())
        self.music_volume.setEnabled(has_music)
        if not has_music:
            self.music_volume.setCurrentText("0")
        elif self.music_volume.currentText() == "0":
            self.music_volume.setCurrentText("0.25")

    def _destination(self) -> str | None:
        path = self.destination_path.text().strip()
        if not path:
            QMessageBox.warning(
                self,
                "Destino necessário",
                "Escolha um produto cadastrado ou uma pasta de destino.",
            )
            return None
        return path

    def _set_processing(self, processing: bool) -> None:
        self._processing = processing
        self.process_images_button.setEnabled(not processing)
        self.convert_video_button.setEnabled(not processing)
        self.progress.setVisible(processing)

    def _process_images(self) -> None:
        destination = self._destination()
        if destination is None:
            return
        image_paths = [
            str(self.image_list.item(index).data(Qt.ItemDataRole.UserRole))
            for index in range(self.image_list.count())
        ]
        if not image_paths:
            QMessageBox.warning(
                self,
                "Imagens necessárias",
                "Adicione pelo menos uma imagem para processar.",
            )
            return
        self._set_processing(True)
        self.log.appendPlainText(
            f"Iniciando tratamento de {len(image_paths)} imagem(ns)…"
        )
        self.start_task(
            processar_imagens_avulsas,
            image_paths,
            destination,
            self.height_input.text().strip(),
            self.width_input.text().strip(),
            self.third_dimension_input.text().strip(),
            self.weight_input.text().strip(),
            self.measure_type.currentText(),
            str(self.measure_background.currentData() or ""),
            on_done=self._task_done,
            on_error=self._task_failed,
        )

    def _choose_video(self) -> None:
        filters = " ".join(f"*{extension}" for extension in VIDEO_EXTENSIONS)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar vídeo",
            str(Path.home()),
            f"Vídeos ({filters})",
        )
        if path:
            self.video_path.setText(path)

    def _convert_video(self) -> None:
        destination = self._destination()
        if destination is None:
            return
        video = self.video_path.text().strip()
        if not video:
            QMessageBox.warning(
                self,
                "Vídeo necessário",
                "Escolha um vídeo para converter.",
            )
            return
        self._set_processing(True)
        self.log.appendPlainText(f"Iniciando conversão de {Path(video).name}…")
        self.start_task(
            converter_video_avulso,
            video,
            destination,
            str(self.music_choice.currentData() or ""),
            float(self.music_volume.currentText()),
            on_done=self._task_done,
            on_error=self._task_failed,
        )

    def show_log(self, message: str) -> None:
        text = str(message).strip()
        if text:
            self.log.appendPlainText(text)
            self.log.ensureCursorVisible()
        super().show_log(text)

    def _task_done(self, result: object) -> None:
        self._set_processing(False)
        if isinstance(result, list):
            summary = "\n".join(str(path) for path in result)
        else:
            summary = str(result)
        self.log.appendPlainText(f"Concluído:\n{summary}")

    def _task_failed(self, error: str) -> None:
        self._set_processing(False)
        self.log.appendPlainText(str(error))
        QMessageBox.critical(
            self,
            "Falha no processamento",
            "O processamento não foi concluído. Confira o terminal da aba "
            "para ver os detalhes.",
        )
