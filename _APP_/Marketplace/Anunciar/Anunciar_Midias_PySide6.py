"""Galeria e prévia de vídeo da vitrine de anúncios."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, QUrl, Qt
from PySide6.QtGui import (
    QDesktopServices,
    QIcon,
    QImageReader,
    QPixmap,
)
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from _APP_.PySide6_core import (
    IMAGE_EXTENSIONS,
    PASTA_VIDEO_CONVERTIDO,
    VIDEO_EXTENSIONS,
)


class AnunciarMediaPanel(QGroupBox):
    """Exibe imagens de G e o vídeo pronto para o marketplace."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Mídias do anúncio", parent)
        self._product_folder: Path | None = None
        self._media_folder: Path | None = None
        self._image_paths: list[Path] = []
        self._video_paths: list[Path] = []
        self._current_video: Path | None = None

        self._build_ui()
        self.video_player = QMediaPlayer(self)
        self.video_audio = QAudioOutput(self)
        self.video_audio.setVolume(0.35)
        self.video_player.setAudioOutput(self.video_audio)
        self.video_player.setVideoOutput(self.video_preview)
        self.video_player.playbackStateChanged.connect(
            self._video_state_changed
        )
        self.video_player.errorOccurred.connect(self._video_error)
        self.set_product_folder(None)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.image_preview = QLabel("Nenhuma imagem disponível")
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setMinimumSize(280, 210)
        self.image_preview.setMaximumHeight(280)
        self.image_preview.setStyleSheet(
            "background-color: #101a27; border: 1px solid #344255;"
        )
        layout.addWidget(self.image_preview)

        self.image_list = QListWidget()
        self.image_list.setViewMode(QListView.ViewMode.IconMode)
        self.image_list.setFlow(QListView.Flow.LeftToRight)
        self.image_list.setWrapping(False)
        self.image_list.setIconSize(QSize(68, 58))
        self.image_list.setGridSize(QSize(82, 78))
        self.image_list.setMaximumHeight(92)
        self.image_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.image_list.currentRowChanged.connect(self._show_image)
        layout.addWidget(self.image_list)

        video_group = QGroupBox("Vídeo pronto")
        video_layout = QVBoxLayout(video_group)
        self.video_preview = QVideoWidget()
        self.video_preview.setMinimumSize(260, 146)
        self.video_preview.setMaximumHeight(210)
        video_layout.addWidget(self.video_preview)
        self.video_combo = QComboBox()
        self.video_combo.currentIndexChanged.connect(
            self._on_video_changed
        )
        video_layout.addWidget(self.video_combo)
        self.video_status = QLabel("Nenhum vídeo disponível.")
        self.video_status.setWordWrap(True)
        video_layout.addWidget(self.video_status)
        video_actions = QHBoxLayout()
        self.play_video_button = QPushButton("Reproduzir")
        self.play_video_button.setEnabled(False)
        self.play_video_button.clicked.connect(self._toggle_video)
        self.open_video_button = QPushButton("Abrir arquivo")
        self.open_video_button.setEnabled(False)
        self.open_video_button.clicked.connect(self._open_video)
        self.open_media_folder_button = QPushButton("Abrir pasta de mídias")
        self.open_media_folder_button.setEnabled(False)
        self.open_media_folder_button.clicked.connect(
            self._open_media_folder
        )
        video_actions.addWidget(self.play_video_button)
        video_actions.addWidget(self.open_video_button)
        video_layout.addLayout(video_actions)
        layout.addWidget(video_group)
        layout.addWidget(self.open_media_folder_button)

    def set_product_folder(self, folder: Path | None) -> None:
        self._stop_video()
        self._product_folder = folder
        self._media_folder = (
            folder / "G_marketplace" if folder is not None else None
        )
        self._render_images()
        self._render_videos()

    def _render_images(self) -> None:
        self._image_paths = []
        self.image_list.clear()
        self.image_preview.setPixmap(QPixmap())
        self.image_preview.setText("Nenhuma imagem disponível")
        self.image_preview.setToolTip("")
        folder = self._media_folder
        self.open_media_folder_button.setEnabled(
            bool(folder and folder.is_dir())
            or bool(self._product_folder and self._product_folder.is_dir())
        )
        if folder is None or not folder.is_dir():
            return

        try:
            paths = sorted(
                folder.iterdir(),
                key=lambda item: item.name.casefold(),
            )
        except OSError as exc:
            self.image_preview.setText("Não foi possível ler as imagens.")
            self.image_preview.setToolTip(str(exc))
            return

        for path in paths:
            if (
                not path.is_file()
                or path.suffix.lower() not in IMAGE_EXTENSIONS
            ):
                continue
            reader = QImageReader(str(path))
            reader.setAutoTransform(True)
            if not reader.canRead():
                continue
            size = reader.size()
            if size.isValid():
                reader.setScaledSize(
                    size.scaled(
                        QSize(520, 380),
                        Qt.AspectRatioMode.KeepAspectRatio,
                    )
                )
            image = reader.read()
            if image.isNull():
                continue
            self._image_paths.append(path)
            thumbnail = QPixmap.fromImage(image).scaled(
                QSize(68, 58),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            item = QListWidgetItem(QIcon(thumbnail), path.name)
            item.setToolTip(str(path))
            self.image_list.addItem(item)

        if self._image_paths:
            self.image_list.setCurrentRow(0)
            self._show_image(0)
        else:
            self.image_preview.setText("A pasta G não contém imagens.")

    def _show_image(self, index: int) -> None:
        if index < 0 or index >= len(self._image_paths):
            return
        path = self._image_paths[index]
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        size = reader.size()
        if size.isValid():
            reader.setScaledSize(
                size.scaled(
                    QSize(520, 380),
                    Qt.AspectRatioMode.KeepAspectRatio,
                )
            )
        image = reader.read()
        if image.isNull():
            self.image_preview.setPixmap(QPixmap())
            self.image_preview.setText("Prévia indisponível")
            return
        pixmap = QPixmap.fromImage(image).scaled(
            self.image_preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_preview.setText("")
        self.image_preview.setPixmap(pixmap)

    def _find_video_paths(self) -> list[Path]:
        folder = self._product_folder
        if folder is None or not folder.is_dir():
            return []
        for directory_name in (
            PASTA_VIDEO_CONVERTIDO,
            "Video_shopee_convertido",
            "e_video_shopee_convertido",
        ):
            directory = folder / directory_name
            if directory.is_dir():
                try:
                    videos = sorted(
                        (
                            path
                            for path in directory.iterdir()
                            if path.is_file()
                            and path.suffix.lower() in VIDEO_EXTENSIONS
                        ),
                        key=lambda path: path.name.casefold(),
                    )
                except OSError:
                    continue
                if videos:
                    return videos
        try:
            return sorted(
                (
                    path
                    for path in folder.iterdir()
                    if path.is_file()
                    and path.suffix.lower() in VIDEO_EXTENSIONS
                ),
                key=lambda path: path.name.casefold(),
            )
        except OSError:
            return []

    def _render_videos(self) -> None:
        self.video_player.stop()
        self.video_player.setSource(QUrl())
        self._current_video = None
        self._video_paths = self._find_video_paths()
        self.video_combo.blockSignals(True)
        self.video_combo.clear()
        for path in self._video_paths:
            self.video_combo.addItem(path.name, str(path))
        self.video_combo.blockSignals(False)

        has_video = bool(self._video_paths)
        self.video_combo.setEnabled(has_video)
        self.play_video_button.setEnabled(has_video)
        self.open_video_button.setEnabled(has_video)
        if not has_video:
            self.video_status.setText("Nenhum vídeo disponível.")
            self.play_video_button.setText("Reproduzir")
            return
        self.video_combo.setCurrentIndex(0)
        self._set_video_source(self._video_paths[0])

    def _on_video_changed(self, index: int) -> None:
        if 0 <= index < len(self._video_paths):
            self._set_video_source(self._video_paths[index])

    def _set_video_source(self, path: Path) -> None:
        self.video_player.stop()
        self._current_video = path
        self.video_player.setSource(QUrl.fromLocalFile(str(path.resolve())))
        self.video_status.setText(f"Vídeo pronto: {path.name}")
        self.play_video_button.setText("Reproduzir")

    def _video_state_changed(
        self,
        state: QMediaPlayer.PlaybackState,
    ) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_video_button.setText("Pausar")
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.play_video_button.setText("Continuar")
        else:
            self.play_video_button.setText("Reproduzir")

    def _video_error(
        self,
        _error: QMediaPlayer.Error,
        _error_text: str,
    ) -> None:
        if self._current_video is not None:
            self.video_status.setText(
                "Não foi possível reproduzir este vídeo nesta prévia."
            )

    def _toggle_video(self) -> None:
        if self._current_video is None:
            return
        if (
            self.video_player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
        ):
            self.video_player.pause()
            return
        if (
            self.video_player.duration() > 0
            and self.video_player.position() >= self.video_player.duration()
        ):
            self.video_player.setPosition(0)
        self.video_player.play()

    def _stop_video(self) -> None:
        self.video_player.stop()
        self.video_player.setSource(QUrl())

    def stop_video(self) -> None:
        """Para a reprodução ao sair da subaba."""
        self._stop_video()

    def _open_video(self) -> None:
        if self._current_video is None:
            return
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(self._current_video.resolve()))
        )

    def _open_media_folder(self) -> None:
        folder = self._media_folder
        if folder is None or not folder.is_dir():
            folder = self._product_folder
        if folder is not None and folder.is_dir():
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(folder.resolve()))
            )
