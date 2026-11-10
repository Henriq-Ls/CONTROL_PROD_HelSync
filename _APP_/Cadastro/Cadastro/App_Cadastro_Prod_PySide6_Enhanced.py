"""Entrada limpa para a tela de cadastro com galeria de mídias aprimorada.

O módulo original foi mantido como referência. Esta camada reaproveita toda a
regra de cadastro existente e ativa a galeria adicionada ao final dele.
"""

from __future__ import annotations

import re
import json
from contextvars import ContextVar
from typing import Any, Callable
from pathlib import Path

from PySide6.QtCore import QMimeData, QPoint, QTimer, QSize, Qt, Signal
from PySide6.QtGui import QDrag, QPixmap, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from _APP_ import PySide6_core as core
from _APP_.PySide6_core import gerar_referencia
from . import App_Cadastro_Prod_PySide6 as legacy
from .catalogo import (
    carregar_catalogo_cadastro,
    regras_por_ids,
)
from _CONFIGURA_ import (
    BRANCO,
    COR_ACENTO,
    COR_ACENTO_HOVER,
    COR_SUCESSO,
    COR_SUCESSO_HOVER,
)
from _LOGS_ import log


_MEDIA_MIME_TYPE = "application/x-hen-place-media"


def _instalar_persistencia_regras():
    if getattr(core, "_regras_anuncio_instaladas", False):
        return core.salvar_cadastro_task

    salvar_entrada_base = core.salvar_entrada
    salvar_cadastro_base = core.salvar_cadastro_task
    init_database_base = core.init_database
    regras_da_tarefa: ContextVar[str | None] = ContextVar(
        "regras_anuncio_do_cadastro",
        default=None,
    )
    proporcao_da_tarefa: ContextVar[str | None] = ContextVar(
        "proporcao_do_cadastro",
        default=None,
    )

    def init_database_com_regras() -> None:
        init_database_base()
        with core.sqlite3.connect(core.DB_PATH) as conexao:
            colunas = {
                str(linha[1])
                for linha in conexao.execute("PRAGMA table_info(A_ENTRADA)")
            }
            if "REGRAS_ANUNCIO" not in colunas:
                conexao.execute(
                    "ALTER TABLE A_ENTRADA ADD COLUMN REGRAS_ANUNCIO TEXT"
                )
            if "PROPORCAO" not in colunas:
                conexao.execute(
                    "ALTER TABLE A_ENTRADA ADD COLUMN PROPORCAO TEXT"
                )

    def salvar_entrada_com_regras(
        produto: str,
        referencia: str,
        diretorio: str,
        descricao: str,
        serventia: str,
        acompanha: str,
        acabamento: str,
        kit: str,
        regras_anuncio: str = "[]",
        proporcao: str | None = None,
    ) -> None:
        regra_em_contexto = regras_da_tarefa.get()
        if regra_em_contexto is not None and regras_anuncio == "[]":
            regras_anuncio = regra_em_contexto
        proporcao_em_contexto = proporcao_da_tarefa.get()
        if proporcao_em_contexto is not None:
            proporcao = proporcao_em_contexto
        init_database_com_regras()
        salvar_entrada_base(
            produto,
            referencia,
            diretorio,
            descricao,
            serventia,
            acompanha,
            acabamento,
            kit,
        )
        with core.sqlite3.connect(core.DB_PATH) as conexao:
            if proporcao is None:
                conexao.execute(
                    "UPDATE A_ENTRADA SET REGRAS_ANUNCIO = ? WHERE PRODUTO = ?",
                    (regras_anuncio, produto),
                )
            else:
                conexao.execute(
                    """
                    UPDATE A_ENTRADA
                    SET REGRAS_ANUNCIO = ?, PROPORCAO = ?
                    WHERE PRODUTO = ?
                    """,
                    (
                        regras_anuncio,
                        str(proporcao or "").strip(),
                        produto,
                    ),
                )

    def salvar_cadastro_com_regras(
        pasta_origem: str,
        pasta_destino: str,
        arquivos: list[str],
        dados: list[tuple[str, str, str, str, str]],
        produto: str,
        descricao: str,
        serventia: str,
        acompanha: str,
        acabamento: str,
        tipo: str,
        qt_variacoes: int,
        tem_kit_tambem: str,
        qt_kit_tambem: int,
        qt_pecas_kit: int,
        tipo_var_kit: str,
        qt_kits: int,
        proporcao: str,
        progress: Callable[[str], None] | None = None,
        nomes_destino: list[str] | None = None,
        regras_anuncio: list[dict[str, str]] | None = None,
    ) -> str:
        token = regras_da_tarefa.set(
            json.dumps(regras_anuncio or [], ensure_ascii=False)
        )
        token_proporcao = proporcao_da_tarefa.set(
            str(proporcao or "").strip()
        )
        try:
            return salvar_cadastro_base(
                pasta_origem,
                pasta_destino,
                arquivos,
                dados,
                produto,
                descricao,
                serventia,
                acompanha,
                acabamento,
                tipo,
                qt_variacoes,
                tem_kit_tambem,
                qt_kit_tambem,
                qt_pecas_kit,
                tipo_var_kit,
                qt_kits,
                proporcao,
                progress=progress,
                nomes_destino=nomes_destino,
            )
        finally:
            proporcao_da_tarefa.reset(token_proporcao)
            regras_da_tarefa.reset(token)

    core.init_database = init_database_com_regras
    core.salvar_entrada = salvar_entrada_com_regras
    core.salvar_cadastro_task = salvar_cadastro_com_regras
    core._regras_anuncio_instaladas = True
    return salvar_cadastro_com_regras


salvar_cadastro_task = _instalar_persistencia_regras()


class _MeasurementOnlyRow(QWidget):
    """Linha compacta de medidas, sem miniatura ou lista de arquivos."""

    def __init__(self, title: str):
        super().__init__()
        self.filename = title

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        for attribute, placeholder in (
            ("altura", "Altura (cm)"),
            ("largura", "Largura (cm)"),
            ("espessura", "Espessura (cm)"),
            ("peso", "Peso (g ou kg)"),
        ):
            field = QLineEdit()
            field.setPlaceholderText(placeholder)
            field.setMinimumWidth(78)
            field.setMaximumWidth(130)
            if attribute == "peso":
                field.setToolTip(
                    "Informe a unidade (por exemplo, 100 g ou 0,1 kg). "
                    "Se informar apenas um número, a convenção legada é "
                    "interpretá-lo como gramas."
                )
            else:
                field.setToolTip(
                    f"{placeholder} do produto. Informe apenas o número em "
                    "centímetros; a unidade será enviada junto ao prompt."
                )
            setattr(self, attribute, field)
            layout.addWidget(field, 1)

    def values(self) -> tuple[str, str, str, str, str]:
        return (
            self.filename,
            self.altura.text().strip(),
            self.largura.text().strip(),
            self.espessura.text().strip(),
            self.peso.text().strip(),
        )


class _DraggableMediaTile(QWidget):
    """Miniatura que inicia um arraste para um grupo de medidas."""

    def __init__(self, path: Path, name: str):
        super().__init__()
        self.name = name
        self._drag_start: QPoint | None = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        preview = QLabel()
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setFixedSize(112, 120)
        preview.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        if path.suffix.lower() in legacy.IMAGE_EXTENSIONS:
            pixmap = legacy._load_oriented_pixmap(path)
            if not pixmap.isNull():
                preview.setPixmap(
                    pixmap.scaled(
                        108,
                        116,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                preview.setText("Imagem")
        else:
            preview.setText(path.suffix.upper().lstrip(".") or "MÍDIA")

        name_label = QLabel(name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        name_label.setToolTip(name)
        name_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        layout.addWidget(preview)
        layout.addWidget(name_label)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_start is None:
            return
        distance = (
            event.position().toPoint() - self._drag_start
        ).manhattanLength()
        if distance < 8:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(_MEDIA_MIME_TYPE, self.name.encode("utf-8"))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)
        self._drag_start = None


class _VideoPreviewTile(QWidget):
    """Vídeo identificado por uma prévia clicável e um botão de reprodução."""

    def __init__(self, path: Path, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)

        play_button = QPushButton("▶\nVÍDEO")
        play_button.setFixedSize(100, 58)
        play_button.setToolTip(f"Clique para assistir: {path.name}")
        play_button.clicked.connect(self._open_video)
        layout.addWidget(play_button, alignment=Qt.AlignmentFlag.AlignCenter)

        name_label = QLabel(path.name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        name_label.setToolTip(path.name)
        layout.addWidget(name_label)
        self._path = path
        self.setFixedWidth(106)

    def _open_video(self, _checked: bool = False) -> None:
        dialog = legacy._VideoPlayerDialog(self._path, self)
        dialog.exec()


class _AssignedMediaTile(QWidget):
    """Miniatura de uma imagem já associada a uma área do grupo."""

    def __init__(self, path: Path, name: str):
        super().__init__()
        self.setFixedWidth(100)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        preview = QLabel()
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setFixedSize(94, 76)
        preview.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        pixmap = legacy._load_oriented_pixmap(path)
        if pixmap.isNull():
            preview.setText("Sem prévia")
        else:
            preview.setPixmap(
                pixmap.scaled(
                    90,
                    72,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        name_label = QLabel(name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        name_label.setToolTip(name)
        name_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        layout.addWidget(preview)
        layout.addWidget(name_label)


class _DropScrollArea(QScrollArea):
    """Repassa arrastes feitos sobre a faixa de miniaturas ao seu dono."""

    def __init__(self, owner: "_MediaDropArea"):
        super().__init__()
        self.owner = owner
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event) -> None:
        self.owner._drag_enter(event)

    def dragMoveEvent(self, event) -> None:
        self.owner._drag_enter(event)

    def dropEvent(self, event) -> None:
        self.owner._drop(event)


class _MediaDropArea(QFrame):
    mediaDropped = Signal(str)

    def __init__(
        self,
        assigned: list[str],
        source_dir: Path,
        title: str,
        multiple: bool,
    ):
        super().__init__()
        self._assigned = list(assigned)
        self._source_dir = source_dir
        self._title = title
        self._multiple = multiple
        self.setAcceptDrops(True)
        self.setFrameStyle(
            QFrame.Shape.StyledPanel | QFrame.Shadow.Plain
        )
        self.setMinimumHeight(122)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 4, 5, 4)
        layout.setSpacing(3)

        title_label = QLabel(f"<b>{title}</b>")
        title_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        layout.addWidget(title_label)

        self.scroll = _DropScrollArea(self)
        self.scroll.setWidgetResizable(False)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.content = QWidget()
        self.content.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self.content_layout = QHBoxLayout(self.content)
        self.content_layout.setContentsMargins(2, 2, 2, 2)
        self.content_layout.setSpacing(4)
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll, 1)
        self._render()

    def set_assigned(self, assigned: list[str]) -> None:
        self._assigned = list(assigned)
        self._render()

    def _render(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if self._assigned:
            for name in self._assigned:
                self.content_layout.addWidget(
                    _AssignedMediaTile(self._source_dir / name, name)
                )
        else:
            empty = QLabel(
                "Arraste uma imagem aqui"
                if self._multiple
                else "Arraste uma imagem"
            )
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setWordWrap(True)
            empty.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
            )
            self.content_layout.addWidget(empty, 1)
        self.content_layout.addStretch()
        self.content.adjustSize()
        self.content.setMinimumWidth(max(110, self.content.sizeHint().width()))
        self.content.resize(self.content.sizeHint())

    def dragEnterEvent(self, event) -> None:
        self._drag_enter(event)

    def _drag_enter(self, event) -> None:
        if event.mimeData().hasFormat(_MEDIA_MIME_TYPE):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        self._drop(event)

    def _drop(self, event) -> None:
        if not event.mimeData().hasFormat(_MEDIA_MIME_TYPE):
            return
        name = bytes(event.mimeData().data(_MEDIA_MIME_TYPE)).decode(
            "utf-8", errors="ignore"
        )
        if name:
            self.mediaDropped.emit(name)
            event.acceptProposedAction()


class _MeasurementGroupBox(QGroupBox):
    """Grupo com uma capa, fotos de ângulo e imagem de medidas."""

    mediaDropped = Signal(str, str)

    def __init__(
        self,
        title: str,
        row: _MeasurementOnlyRow,
        assigned: dict[str, object],
        source_dir: Path,
    ):
        super().__init__(title)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        cover = _MediaDropArea(
            self._as_names(assigned.get("cover")),
            source_dir,
            "CAPA",
            multiple=False,
        )
        angles = _MediaDropArea(
            self._as_names(assigned.get("angles")),
            source_dir,
            "FOTOS DE ÂNGULO",
            multiple=True,
        )
        measures = _MediaDropArea(
            self._as_names(assigned.get("measures")),
            source_dir,
            "MEDIDAS",
            multiple=False,
        )
        self.cover_area = cover
        self.angles_area = angles
        self.measures_area = measures

        top = QHBoxLayout()
        top.setSpacing(6)
        top.addWidget(row, 1)
        top.addWidget(cover)
        layout.addLayout(top)

        bottom = QHBoxLayout()
        bottom.setSpacing(6)
        bottom.addWidget(angles, 1)
        bottom.addWidget(measures)
        layout.addLayout(bottom)

        for role, area in (
            ("cover", cover),
            ("angles", angles),
            ("measures", measures),
        ):
            area.mediaDropped.connect(
                lambda name, current_role=role: self.mediaDropped.emit(
                    current_role, name
                )
            )

    @staticmethod
    def _as_names(value: object) -> list[str]:
        if isinstance(value, str):
            return [value] if value else []
        if isinstance(value, list):
            return [name for name in value if isinstance(name, str)]
        return []


class _ManualMediaGallery(QWidget):
    """Galeria de origem com todas as imagens disponíveis para associação."""

    filesChanged = Signal(list)

    def __init__(self, title: str = "Imagens encontradas"):
        super().__init__()
        self.source_dir = Path()
        self.files: list[str] = []
        self._source_item: QTreeWidgetItem | None = None
        self._assigned: set[str] = set()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        heading = QHBoxLayout()
        heading.addWidget(QLabel(f"<b>{title}</b>"))
        heading.addStretch()
        root.addLayout(heading)

        self.order_label = QLabel(
            "Arraste uma mídia daqui para o grupo correspondente."
        )
        self.order_label.setWordWrap(True)
        self.order_label.hide()
        root.addWidget(self.order_label)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(18)
        self.tree.setMinimumWidth(270)
        self.tree.setColumnWidth(0, 250)
        self.tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Fixed
        )
        self.tree.setIconSize(QPixmap(76, 58).size())
        self.tree.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        root.addWidget(self.tree, 1)

    def clear(self) -> None:
        self.tree.clear()
        self._source_item = None

    def show_empty(self) -> None:
        self.clear()
        self.order_label.setText(
            "Nenhuma imagem encontrada. Escolha uma pasta de origem."
        )

    def update_files(self, files: list[str], source_dir: str) -> None:
        self.source_dir = Path(source_dir)
        # Vídeos continuam pertencendo ao cadastro, mas ficam fora da área
        # arrastável. Apenas imagens podem receber grupo e medidas.
        self.files = [
            name
            for name in files
            if name.lower().endswith(legacy.IMAGE_EXTENSIONS)
        ]
        self._assigned.intersection_update(self.files)
        self._render_available()

    def set_assigned(self, assigned: set[str]) -> None:
        # A mesma imagem pode ser capa de vários grupos. A galeria de origem
        # nunca esconde uma imagem depois que ela é associada.
        self._assigned = set()
        self._render_available()

    def _render_available(self) -> None:
        self.tree.blockSignals(True)
        self.clear()
        available = list(self.files)
        if not self.files:
            self.tree.blockSignals(False)
            self.show_empty()
            return
        source = self._create_source()
        for name in available:
            self._add_file(source, name)
        source.setExpanded(True)
        self.tree.blockSignals(False)
        self._update_label()

    def _create_source(self) -> QTreeWidgetItem:
        source = QTreeWidgetItem(["Mídias encontradas"])
        source.setData(0, Qt.ItemDataRole.UserRole, "source")
        source.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsDropEnabled
        )
        self.tree.addTopLevelItem(source)
        self._source_item = source
        return source

    def _add_file(self, group: QTreeWidgetItem, name: str) -> None:
        item = QTreeWidgetItem([""])
        item.setData(0, Qt.ItemDataRole.UserRole, name)
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
        )
        path = self.source_dir / name
        tile = _DraggableMediaTile(path, name)
        item.setSizeHint(0, QSize(128, 156))
        group.addChild(item)
        self.tree.setItemWidget(item, 0, tile)

    def _update_label(self) -> None:
        available_count = (
            self._source_item.childCount()
            if self._source_item is not None
            else 0
        )
        self.order_label.setText(
            f"{available_count} mídia(s) disponível(is). "
            "Arraste para um grupo."
        )


# O módulo histórico possui cópias antigas da tela. A implementação aprimorada
# foi declarada no final dele e fica disponível com este nome.
legacy.MediaGallery = _ManualMediaGallery

CadastroTab = legacy.CadastroTab
_legacy_init = legacy.CadastroTab.__init__
_legacy_build_ui = legacy.CadastroTab.build_ui
_legacy_rebuild_measurements = legacy.CadastroTab.rebuild_measurements
_legacy_save_finished = legacy.CadastroTab.save_finished


def _checkable_set_items(self, items: list[object]) -> None:
    selecionados = set(self.checked_values())
    model = QStandardItemModel(self)
    for valor in items:
        if isinstance(valor, dict):
            texto = str(valor.get("label") or "")
            dado = valor.get("value", texto)
        else:
            texto = str(valor or "")
            dado = texto
        if not texto:
            continue
        item = QStandardItem(texto)
        item.setFlags(
            item.flags()
            | Qt.ItemFlag.ItemIsUserCheckable
            | Qt.ItemFlag.ItemIsEnabled
        )
        item.setData(dado, Qt.ItemDataRole.UserRole)
        item.setCheckState(
            Qt.CheckState.Checked
            if dado in selecionados
            else Qt.CheckState.Unchecked
        )
        model.appendRow(item)
    self.setModel(model)
    self._refresh_text()


def _checkable_init(
    self,
    items: list[object],
    placeholder: str = "Selecione opções",
) -> None:
    QComboBox.__init__(self)
    self.setEditable(True)
    self.lineEdit().setReadOnly(True)
    self.lineEdit().setPlaceholderText(placeholder)
    _checkable_set_items(self, items)
    self.view().pressed.connect(self._toggle_item)


def _checkable_values(self) -> list[object]:
    return [
        self.model().item(indice).data(Qt.ItemDataRole.UserRole)
        for indice in range(self.model().rowCount())
        if self.model().item(indice).checkState() == Qt.CheckState.Checked
    ]


legacy.CheckableComboBox.__init__ = _checkable_init
legacy.CheckableComboBox.set_items = _checkable_set_items
legacy.CheckableComboBox.checked_values = _checkable_values


def _find_layout_with_widget(layout, target):
    for indice in range(layout.count()):
        item = layout.itemAt(indice)
        if item.widget() is target:
            return layout, indice
        child_layout = item.layout()
        if child_layout is not None:
            encontrado = _find_layout_with_widget(child_layout, target)
            if encontrado is not None:
                return encontrado
    return None


def _install_catalog_widgets(self) -> None:
    catalogo = carregar_catalogo_cadastro()
    self.catalogo_cadastro = catalogo

    antigo_acompanha = self.accompanies
    self.accompanies = legacy.CheckableComboBox(
        list(catalogo["acompanha"]),
        "Selecione o que acompanha",
    )
    self.accompanies.setToolTip(
        "Selecione uma ou mais opções cadastradas em Configurações."
    )
    encontrado = _find_layout_with_widget(
        antigo_acompanha.parentWidget().layout(),
        antigo_acompanha,
    )
    if encontrado is None:
        raise RuntimeError("Não foi possível localizar o campo Acompanha.")
    encontrado[0].replaceWidget(antigo_acompanha, self.accompanies)
    antigo_acompanha.deleteLater()

    self.finish.set_items(list(catalogo["acabamentos"]))
    self.finish.setToolTip(
        "Selecione um ou mais acabamentos cadastrados em Configurações."
    )
    self.ad_rules = legacy.CheckableComboBox(
        [
            {"label": regra["titulo"], "value": regra["id"]}
            for regra in catalogo["regras_anuncio"]
        ],
        "Selecione regras do anúncio",
    )
    self.ad_rules.setToolTip(
        "Selecione as regras deste produto. Os títulos entram na descrição "
        "e as descrições acompanham o prompt do anúncio."
    )
    basic_layout = self.finish.parentWidget().layout()
    linha_acabamento = next(
        (
            indice
            for indice in range(basic_layout.count())
            if basic_layout.itemAt(indice).layout() is not None
            and basic_layout.itemAt(indice).layout().indexOf(self.finish) >= 0
        ),
        None,
    )
    if linha_acabamento is None:
        raise RuntimeError("Não foi possível localizar o campo Acabamento.")
    basic_layout.insertWidget(linha_acabamento + 1, QLabel("Regras do anúncio"))
    linha_regras = QHBoxLayout()
    linha_regras.addWidget(self.ad_rules, 1)
    basic_layout.insertLayout(linha_acabamento + 2, linha_regras)


def _build_ui(self) -> None:
    _legacy_build_ui(self)
    _install_catalog_widgets(self)


CadastroTab.build_ui = _build_ui


def _refresh_files(self) -> None:
    source = Path(self.source_dir.text().strip())
    self._manual_assignments = {}
    if not source.exists():
        self.files = []
        self.media_gallery.update_files([], str(source))
        self.files_label.setText("Nenhuma pasta selecionada")
        _update_video_reference(self, [])
        _update_txt_reference(self)
        self.rebuild_measurements()
        return

    # Esta é a ordem inicial da pasta. A atribuição aos grupos é feita
    # manualmente arrastando somente as imagens.
    self.files = [
        item.name
        for item in source.iterdir()
        if item.is_file()
        and item.suffix.lower()
        in legacy.IMAGE_EXTENSIONS + legacy.VIDEO_EXTENSIONS
    ]
    image_files = [
        name
        for name in self.files
        if name.lower().endswith(legacy.IMAGE_EXTENSIONS)
    ]
    video_files = [
        name
        for name in self.files
        if name.lower().endswith(legacy.VIDEO_EXTENSIONS)
    ]
    self.media_gallery.update_files(image_files, str(source))
    self.files_label.setText(
        f"{len(image_files)} imagem(ns) disponível(is) para organização. "
        "Arraste para o grupo correspondente."
    )
    _update_video_reference(self, video_files)
    _update_txt_reference(self, source)
    self.rebuild_measurements()


def _update_txt_reference(self, source: Path | None = None) -> None:
    """Atualiza apenas a medida visível do TXT, sem associá-la às imagens."""
    from _APP_.PySide6_core import encontrar_arquivo_txt

    text_view = getattr(self, "_txt_reference_view", None)
    if text_view is None:
        return

    source_text = self.source_dir.text().strip()
    if source is None:
        source = Path(source_text) if source_text else None

    arquivo_txt = (
        encontrar_arquivo_txt(source)
        if source is not None and source.is_dir()
        else None
    )
    if arquivo_txt is None:
        text_view.setPlainText("Nenhuma medida encontrada no TXT.")
    else:
        try:
            texto = arquivo_txt.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            text_view.setPlainText("Não foi possível ler a medida do TXT.")
        else:
            text_view.setPlainText(texto.strip())


def _create_txt_reference_panel(self) -> QWidget:
    """Cria o painel compacto de medida do TXT, sem título redundante."""
    panel = QWidget()
    panel.setObjectName("txtReferencePanel")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(8, 6, 8, 6)
    layout.setSpacing(4)

    text_view = QPlainTextEdit()
    text_view.setReadOnly(True)
    text_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    text_view.setPlaceholderText(
        "A medida do TXT aparecerá aqui."
    )
    text_view.setMinimumHeight(58)
    text_view.setMaximumHeight(92)
    layout.addWidget(text_view)

    self._txt_reference_view = text_view
    return panel


def _create_video_reference_panel(self) -> QWidget:
    """Cria a área separada para vídeos, fora das imagens arrastáveis."""
    panel = QWidget()
    panel.setObjectName("videoReferencePanel")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(8, 4, 8, 4)
    layout.setSpacing(3)

    title = QLabel("<b>Vídeos</b>")
    title.setToolTip(
        "Vídeos são copiados para o produto, mas não recebem medidas nem grupos."
    )
    layout.addWidget(title)
    self._video_reference_title = title

    scroll = QScrollArea()
    scroll.setWidgetResizable(False)
    scroll.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )
    scroll.setVerticalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    container = QWidget()
    video_layout = QHBoxLayout(container)
    video_layout.setContentsMargins(2, 2, 2, 2)
    video_layout.setSpacing(6)
    scroll.setWidget(container)
    scroll.setMinimumHeight(94)
    scroll.setMaximumHeight(106)
    layout.addWidget(scroll)
    panel.setMinimumHeight(116)
    panel.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Fixed,
    )

    self._video_reference_view = container
    self._video_reference_layout = video_layout
    self._video_reference_scroll = scroll
    return panel


def _update_video_reference(self, videos: list[str]) -> None:
    container = getattr(self, "_video_reference_view", None)
    video_layout = getattr(self, "_video_reference_layout", None)
    if container is None or video_layout is None:
        return
    title = getattr(self, "_video_reference_title", None)
    if title is not None:
        title.setText(
            f"<b>Vídeos ({len(videos)})</b>" if videos else "<b>Vídeos</b>"
        )

    while video_layout.count():
        item = video_layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()

    if videos:
        source = Path(self.source_dir.text().strip())
        for name in videos:
            video_layout.addWidget(_VideoPreviewTile(source / name, container))
    else:
        video_layout.addWidget(QLabel("Nenhum vídeo encontrado."))
    video_layout.addStretch()
    container.adjustSize()
    container.setMinimumWidth(max(150, len(videos) * 112 + 10))
    container.resize(container.sizeHint())


def _ler_txt_da_origem(source: Path) -> tuple[str, str]:
    """Lê o TXT da origem para a IA conhecer o material já anexado."""
    if not source.exists() or not source.is_dir():
        return "", ""
    try:
        from _APP_.PySide6_core import encontrar_arquivo_txt

        arquivo_txt = encontrar_arquivo_txt(source)
        if arquivo_txt is None:
            return "", ""
        texto = arquivo_txt.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return "", ""
    limite = 20000
    if len(texto) > limite:
        texto = texto[:limite] + "\n[TXT truncado para o contexto da IA]"
    return arquivo_txt.name, texto


def _indices_representativos(self) -> list[int]:
    """Retorna os índices do TXT usados pelos cartões de medidas da tela."""
    imagens = [
        nome
        for nome in self.files
        if nome.lower().endswith(legacy.IMAGE_EXTENSIONS)
    ]
    tipo = self.product_type.currentText()
    variacoes = int(self.variations.currentText())
    kit_pieces = int(self.kit_pieces.currentText())
    kit_count = int(self.kit_count.currentText())
    indices: list[int] = []

    if tipo == "Único" and self.also_kit.currentText() == "Não":
        if variacoes == 1:
            return [0] if imagens else []
        por_grupo = max(1, len(imagens) // variacoes)
        for grupo in range(variacoes):
            inicio = grupo * por_grupo
            fim = len(imagens) if grupo == variacoes - 1 else inicio + por_grupo
            if inicio < fim:
                indices.append(inicio)
        return indices

    if tipo == "Kit":
        esperado = (1 + kit_pieces) * kit_count
        return list(range(min(len(imagens), esperado)))

    tamanho_kit = (1 + kit_pieces) * kit_count
    imagens_unicas = (
        imagens[:-tamanho_kit] if len(imagens) > tamanho_kit else []
    )
    imagens_kit = imagens[-tamanho_kit:] if len(imagens) >= tamanho_kit else []
    if variacoes == 1:
        if imagens_unicas:
            indices.append(0)
    else:
        por_grupo = max(1, len(imagens_unicas) // variacoes)
        for grupo in range(variacoes):
            inicio = grupo * por_grupo
            fim = (
                len(imagens_unicas)
                if grupo == variacoes - 1
                else inicio + por_grupo
            )
            if inicio < fim:
                indices.append(inicio)
    indices.extend(
        range(len(imagens_unicas), len(imagens_unicas) + len(imagens_kit))
    )
    return indices


def _order_changed(self, files: list[str]) -> None:
    self.files = list(files)
    self.files_label.setText(
        f"{len(self.files)} arquivo(s), na ordem escolhida para o cadastro."
    )
    self.rebuild_measurements()


def _groups_changed(self) -> None:
    self.rebuild_measurements()


def _classification_group_specs(self) -> list[tuple[str, str]]:
    """Cria os grupos de destino a partir da classificação atual."""
    tipo = self.product_type.currentText()
    variacoes = int(self.variations.currentText())
    kit_pieces = int(self.kit_pieces.currentText())
    kit_count = int(self.kit_count.currentText())
    specs: list[tuple[str, str]] = []

    if tipo == "Único":
        if variacoes == 1:
            specs.append(("produto", "Produto único"))
        else:
            specs.extend(
                (f"variacao:{index}", f"Variação {index}")
                for index in range(1, variacoes + 1)
            )

    if tipo == "Único" and self.also_kit.currentText() == "Não":
        return specs

    for kit_index in range(1, kit_count + 1):
        specs.append(
            (
                f"kit:{kit_index}:completo",
                f"Kit completo {kit_index}",
            )
        )
        specs.extend(
            (
                f"kit:{kit_index}:peca:{piece_index}",
                f"Kit {kit_index} - peça {piece_index}",
            )
            for piece_index in range(1, kit_pieces + 1)
        )
    return specs


def _empty_media_assignment() -> dict[str, object]:
    return {
        "cover": None,
        "angles": [],
        "measures": None,
    }


def _normalize_media_assignment(
    value: object,
    available_files: set[str],
) -> dict[str, object]:
    """Converte associações antigas para as três áreas explícitas do grupo."""
    result = _empty_media_assignment()
    if isinstance(value, dict):
        cover = value.get("cover")
        measures = value.get("measures")
        angles = value.get("angles")
        if isinstance(cover, str) and cover in available_files:
            result["cover"] = cover
        if isinstance(measures, str) and measures in available_files:
            result["measures"] = measures
        if isinstance(angles, list):
            result["angles"] = [
                name
                for name in angles
                if isinstance(name, str)
                and name in available_files
                and name not in (result["cover"], result["measures"])
            ]
        return result

    # Compatibilidade com a lista usada antes desta separação visual:
    # primeira imagem era capa, última era medida e o meio eram ângulos.
    if isinstance(value, list):
        names = [
            name
            for name in value
            if isinstance(name, str) and name in available_files
        ]
        if names:
            result["cover"] = names[0]
            if len(names) > 1:
                result["measures"] = names[-1]
                result["angles"] = names[1:-1]
    return result


def _assignment_names(assignment: dict[str, object]) -> list[str]:
    result: list[str] = []
    cover = assignment.get("cover")
    angles = assignment.get("angles")
    measures = assignment.get("measures")
    if isinstance(cover, str):
        result.append(cover)
    if isinstance(angles, list):
        result.extend(name for name in angles if isinstance(name, str))
    if isinstance(measures, str):
        result.append(measures)
    return result


def _assign_media(self, group_id: str, role: str, name: str) -> None:
    """Preenche uma área do grupo sem remover a imagem da galeria."""
    if (
        name not in self.files
        or not name.lower().endswith(legacy.IMAGE_EXTENSIONS)
        or role not in {"cover", "angles", "measures"}
    ):
        return

    assignments = getattr(self, "_manual_assignments", {})
    assignment = _normalize_media_assignment(
        assignments.get(group_id),
        {
            current
            for current in self.files
            if current.lower().endswith(legacy.IMAGE_EXTENSIONS)
        },
    )
    # Uma imagem pode ser reutilizada em outros grupos, mas não ocupa duas
    # funções dentro do mesmo grupo.
    for current_role in ("cover", "angles", "measures"):
        if current_role == role:
            continue
        current_value = assignment[current_role]
        if current_role == "angles" and isinstance(current_value, list):
            assignment[current_role] = [
                current for current in current_value if current != name
            ]
        elif current_value == name:
            assignment[current_role] = None

    if role == "angles":
        angles = assignment["angles"]
        if not isinstance(angles, list):
            angles = []
        if name not in angles:
            angles.append(name)
        assignment["angles"] = angles
    else:
        assignment[role] = name

    assignments[group_id] = assignment
    self._manual_assignments = assignments
    self.rebuild_measurements()


def _manual_rebuild_measurements(self) -> None:
    """Recria os cartões conforme a classificação e preserva as medidas."""
    previous_values: dict[str, tuple[str, str, str, str]] = {}
    for row in self.measurement_rows:
        group_id = getattr(row, "_group_id", "")
        if group_id:
            previous_values[group_id] = row.values()[1:]

    self.clear_measurements()
    specs = _classification_group_specs(self)
    available_files = set(self.files)
    assignments = getattr(self, "_manual_assignments", {})
    normalized: dict[str, dict[str, object]] = {}
    for group_id, _title in specs:
        normalized[group_id] = _normalize_media_assignment(
            assignments.get(group_id),
            available_files,
        )
    self._manual_assignments = normalized
    self.media_gallery.set_assigned(set())

    for group_id, title in specs:
        row = _MeasurementOnlyRow(title)
        row._group_id = group_id
        old_values = previous_values.get(group_id)
        if old_values is not None:
            for widget, value in zip(
                (row.altura, row.largura, row.espessura, row.peso),
                old_values,
            ):
                widget.setText(value)
        self.measurement_rows.append(row)
        box = _MeasurementGroupBox(
            title,
            row,
            normalized[group_id],
            Path(self.source_dir.text().strip()),
        )
        box.mediaDropped.connect(
            lambda role, name, current_id=group_id: _assign_media(
                self, current_id, role, name
            )
        )
        self.measurement_layout.addWidget(box)

    self.summary.setText(
        f"Classificação: {self.product_type.currentText()} · "
        f"{len(specs)} grupo(s) gerado(s). "
        "Arraste cada mídia para o grupo correspondente."
    )


def _manual_collect_data(self) -> list[tuple[str, str, str, str, str]]:
    """Expande cada cartão na ordem capa, ângulos e medidas."""
    result: list[tuple[str, str, str, str, str]] = []
    assignments = getattr(self, "_manual_assignments", {})
    for row in self.measurement_rows:
        assignment = _normalize_media_assignment(
            assignments.get(getattr(row, "_group_id", "")),
            {
                name
                for name in self.files
                if name.lower().endswith(legacy.IMAGE_EXTENSIONS)
            },
        )
        names = _assignment_names(assignment)
        image_names = [
            name for name in names if name.lower().endswith(legacy.IMAGE_EXTENSIONS)
        ]
        if not image_names:
            continue
        values = row.values()[1:]
        result.extend((name, *values) for name in image_names)
    return result


def _safe_media_name_part(value: str) -> str:
    """Mantém medidas legíveis no nome e remove caracteres de caminho."""
    text = str(value).strip().replace(",", ".")
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[^0-9A-Za-z.-]", "", text)
    return text or "0"


def _group_assignments(self) -> list[tuple[str, dict[str, object]]]:
    available = {
        name
        for name in self.files
        if name.lower().endswith(legacy.IMAGE_EXTENSIONS)
    }
    assignments = getattr(self, "_manual_assignments", {})
    return [
        (
            getattr(row, "_group_id", ""),
            _normalize_media_assignment(
                assignments.get(getattr(row, "_group_id", "")),
                available,
            ),
        )
        for row in self.measurement_rows
    ]


def _validate_before_save(self, produto: str, origem: str, descricao: str) -> list[str]:
    errors: list[str] = []
    if not produto:
        errors.append("Informe o nome do produto.")
    if not origem or not Path(origem).is_dir():
        errors.append("Escolha uma pasta de origem válida.")
    if not descricao:
        errors.append("Preencha a descrição.")
    if not self.measurement_rows:
        errors.append("Nenhum grupo de variação ou kit foi criado.")

    specs = _classification_group_specs(self)
    titles = {
        group_id: title
        for group_id, title in specs
    }
    for row, (group_id, assignment) in zip(
        self.measurement_rows,
        _group_assignments(self),
    ):
        title = titles.get(group_id, "Grupo")
        values = row.values()[1:]
        missing_fields = [
            label
            for label, value in zip(
                ("altura", "largura", "espessura", "peso"),
                values,
            )
            if not str(value).strip()
        ]
        if missing_fields:
            errors.append(
                f"{title}: preencha {', '.join(missing_fields)}."
            )

        missing_media: list[str] = []
        if not isinstance(assignment.get("cover"), str):
            missing_media.append("capa")
        angles = assignment.get("angles")
        if not isinstance(angles, list) or not angles:
            missing_media.append("pelo menos uma foto de ângulo")
        if not isinstance(assignment.get("measures"), str):
            missing_media.append("imagem de medidas")
        if missing_media:
            errors.append(
                f"{title}: adicione {', '.join(missing_media)}."
            )
    return errors


def _build_destination_names(
    self,
    produto: str,
) -> list[str]:
    """Cria nomes únicos por grupo com as medidas no final do arquivo."""
    referencia = gerar_referencia(produto).upper()
    result: list[str] = []
    for group_index, row in enumerate(self.measurement_rows, start=1):
        assignment = _normalize_media_assignment(
            getattr(self, "_manual_assignments", {}).get(
                getattr(row, "_group_id", "")
            ),
            {
                name
                for name in self.files
                if name.lower().endswith(legacy.IMAGE_EXTENSIONS)
            },
        )
        names = _assignment_names(assignment)
        altura, largura, espessura, peso = row.values()[1:]
        medida = (
            f"{_safe_media_name_part(altura)}x"
            f"{_safe_media_name_part(largura)}x"
            f"{_safe_media_name_part(espessura)}_"
            f"{_safe_media_name_part(peso)}"
        )
        group_prefix = f"{referencia}{group_index}"
        for image_index, source_name in enumerate(names, start=1):
            suffix = Path(source_name).suffix.lower() or ".jpg"
            sequence = (
                f"_{image_index:02d}"
                if len(names) > 1
                else ""
            )
            result.append(f"{group_prefix}{sequence}_{medida}{suffix}")
    return result


def _save_product(self) -> None:
    produto = self.product_name.text().strip()
    origem = self.source_dir.text().strip()
    descricao = self.description.toPlainText().strip()

    if not self.files and Path(origem).is_dir():
        self.refresh_files()

    errors = _validate_before_save(self, produto, origem, descricao)
    if errors:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.warning(
            self,
            "Cadastro incompleto",
            "\n".join(f"• {error}" for error in errors),
        )
        return

    dados = _manual_collect_data(self)
    nomes_destino = _build_destination_names(self, produto)
    if len(dados) != len(nomes_destino):
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.critical(
            self,
            "Erro na organização das mídias",
            "A quantidade de imagens e nomes de destino não coincide. "
            "Revise os grupos antes de salvar.",
        )
        return

    destino = Path(self.products_dir.text().strip()) / produto.upper()
    catalogo = getattr(self, "catalogo_cadastro", None)
    if catalogo is None:
        catalogo = carregar_catalogo_cadastro()
    ids_regras = [
        str(regra_id)
        for regra_id in self.ad_rules.checked_values()
        if str(regra_id).strip()
    ]
    regras = regras_por_ids(catalogo, ids_regras)
    descricao = _adicionar_titulos_regras(descricao, regras)
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
        self.accompanies.checked_text(),
        self.finish.checked_text(),
        self.product_type.currentText(),
        int(self.variations.currentText()),
        self.also_kit.currentText(),
        int(self.kit_pieces.currentText()),
        int(self.kit_pieces.currentText()),
        self.kit_variation.currentText(),
        int(self.kit_count.currentText()),
        self.proportion.currentText(),
        nomes_destino=nomes_destino,
        regras_anuncio=regras,
        on_done=self.save_finished,
        on_error=self.save_failed,
    )


def _refresh_product_options(self) -> None:
    catalogo = carregar_catalogo_cadastro()
    self.catalogo_cadastro = catalogo
    self.accompanies.set_items(list(catalogo["acompanha"]))
    self.finish.set_items(list(catalogo["acabamentos"]))
    self.ad_rules.set_items(
        [
            {"label": regra["titulo"], "value": regra["id"]}
            for regra in catalogo["regras_anuncio"]
        ]
    )
    if hasattr(self, "_ai_context_timer"):
        _connect_catalog_model_signals(self)
    self._schedule_ai_context()


def _adicionar_titulos_regras(
    descricao: str,
    regras: list[dict[str, str]],
) -> str:
    """Inclui os títulos selecionados na descrição gravada do produto."""
    linhas_existentes = {
        linha.strip().casefold()
        for linha in descricao.splitlines()
        if linha.strip()
    }
    novos_titulos = [
        regra["titulo"]
        for regra in regras
        if regra["titulo"].strip().casefold() not in linhas_existentes
    ]
    if not novos_titulos:
        return descricao
    base = descricao.rstrip()
    sufixo = "\n".join(novos_titulos)
    return f"{base}\n{sufixo}" if base else sufixo


def _connect_catalog_model_signals(self) -> None:
    for widget in (self.finish, self.accompanies, self.ad_rules):
        widget.model().dataChanged.connect(
            lambda *_args, cadastro=self: cadastro._schedule_ai_context()
        )


def _setup_ai_context(self) -> None:
    self._ai_context_callback: Callable[[dict[str, object]], None] | None = None
    self._produto_salvo_id = ""
    self._ai_context_timer = QTimer(self)
    self._ai_context_timer.setSingleShot(True)
    self._ai_context_timer.timeout.connect(self._publish_ai_context)

    for widget in (
        self.product_name,
        self.source_dir,
        self.description,
        self.usage,
        self.products_dir,
    ):
        widget.textChanged.connect(self._schedule_ai_context)
    for widget in (
        self.proportion,
        self.product_type,
        self.variations,
        self.also_kit,
        self.kit_pieces,
        self.kit_variation,
        self.kit_count,
    ):
        widget.currentTextChanged.connect(self._schedule_ai_context)
    _connect_catalog_model_signals(self)
    self.media_gallery.filesChanged.connect(
        lambda *_args: self._schedule_ai_context()
    )
    self._schedule_ai_context()


def _set_ai_context_callback(
    self,
    callback: Callable[[dict[str, object]], None] | None,
) -> None:
    self._ai_context_callback = callback
    self._publish_ai_context()


def _schedule_ai_context(self, *_args: object) -> None:
    callback = getattr(self, "_ai_context_callback", None)
    timer = getattr(self, "_ai_context_timer", None)
    if callback is not None and timer is not None:
        timer.start(250)


def _snapshot_ai_context(self) -> dict[str, object]:
    produto = self.product_name.text().strip()
    produto_id = produto.title() if produto else ""
    salvo_no_banco = produto_id == self._produto_salvo_id and bool(produto_id)
    memoria_id = f"produto:{produto_id}" if salvo_no_banco else ""
    destino = (
        str(Path(self.products_dir.text().strip()) / produto.upper())
        if produto
        else ""
    )
    referencia = gerar_referencia(produto).lower() if produto else ""
    arquivo_txt_origem, texto_txt_origem = _ler_txt_da_origem(
        Path(self.source_dir.text().strip())
    )
    catalogo = getattr(self, "catalogo_cadastro", None)
    if catalogo is None:
        catalogo = carregar_catalogo_cadastro()
    regras = regras_por_ids(
        catalogo,
        [str(regra_id) for regra_id in self.ad_rules.checked_values()],
    )
    descricao_com_regras = _adicionar_titulos_regras(
        self.description.toPlainText().strip(),
        regras,
    )
    return {
        "produto_id": produto_id if salvo_no_banco else "",
        "memoria_id": memoria_id,
        "memoria_tipo": "produto" if salvo_no_banco else "rascunho",
        "id_origem": "A_ENTRADA.PRODUTO",
        "nome": produto,
        "nome_legado": produto_id,
        "referencia": referencia,
        "diretorio": destino,
        "diretorio_base": self.products_dir.text().strip(),
        "origem_midias": self.source_dir.text().strip(),
        "descricao": self.description.toPlainText().strip(),
        "serventia": self.usage.toPlainText().strip(),
        "acompanha": self.accompanies.checked_text(),
        "acabamento": self.finish.checked_text(),
        "regras_anuncio": regras,
        "proporcao": self.proportion.currentText(),
        "tipo": self.product_type.currentText(),
        "variacoes": self.variations.currentText(),
        "tambem_em_kit": self.also_kit.currentText(),
        "pecas_no_kit": self.kit_pieces.currentText(),
        "variacao_do_kit": self.kit_variation.currentText(),
        "quantidade_de_kits": self.kit_count.currentText(),
        "arquivos": list(self.files),
        "quantidade_arquivos": len(self.files),
        "medidas": [list(row.values()) for row in self.measurement_rows],
        "arquivo_txt_origem": arquivo_txt_origem,
        "texto_txt_origem": texto_txt_origem,
        "registro_banco": {
            "tabela": "A_ENTRADA",
            "chave": "PRODUTO",
            "valor_chave": produto_id,
            "campos": {
                "PRODUTO": produto_id,
                "REFERENCIA": referencia,
                "DIRETORIO": destino,
                "DESCRITION": descricao_com_regras,
                "SERVENTIA": self.usage.toPlainText().strip(),
                "ACOMPANHA": self.accompanies.checked_text(),
                "ACABAMENTO": self.finish.checked_text(),
                "PROPORCAO": self.proportion.currentText(),
                "REGRAS_ANUNCIO": json.dumps(
                    regras,
                    ensure_ascii=False,
                ),
            },
        },
        "salvo_no_banco": salvo_no_banco,
    }


def _publish_ai_context(self) -> None:
    callback = getattr(self, "_ai_context_callback", None)
    if callback is None:
        return
    try:
        callback(_snapshot_ai_context(self))
    except Exception as exc:
        log.erro("Cadastro", "_publish_ai_context", str(exc))


def _rebuild_measurements(self) -> None:
    _manual_rebuild_measurements(self)
    self._schedule_ai_context()


def _save_finished(self, result: object) -> None:
    self._produto_salvo_id = self.product_name.text().strip().title()
    _legacy_save_finished(self, result)
    self._publish_ai_context()


def _organizar_painel_central(self) -> None:
    """Divide mídias e medidas em dois painéis verticais ajustáveis."""
    if getattr(self, "_central_vertical_splitter", None) is not None:
        return

    right = self.media_gallery.parentWidget()
    right_layout = right.layout() if right is not None else None
    if right is None or right_layout is None:
        return

    settings_scroll = next(
        (
            scroll
            for scroll in self.findChildren(QScrollArea)
            if scroll.widget() is not None
            and self.product_name in scroll.widget().findChildren(QWidget)
        ),
        None,
    )
    if settings_scroll is not None:
        settings = settings_scroll.widget()
        settings.setMinimumWidth(300)
        settings_scroll.setMinimumWidth(300)
        settings_scroll.setMaximumWidth(390)
        outer_splitter = settings_scroll.parentWidget()
        if isinstance(outer_splitter, QSplitter):
            outer_splitter.setSizes([350, 1020])

    classification = getattr(self, "classification", None)
    if classification is None and settings_scroll is not None:
        classification = next(
            (
                group
                for group in settings_scroll.widget().findChildren(QGroupBox)
                if group.title() == "Classificação"
            ),
            None,
        )
    if classification is not None:
        classification_layout = classification.parentWidget().layout()
        if classification_layout is not None:
            classification_layout.removeWidget(classification)
        classification.setParent(right)
        classification.setMinimumWidth(0)
        classification.setMaximumWidth(16777215)
        classification.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

    refresh_button = next(
        (
            button
            for button in self.findChildren(QPushButton)
            if button.text().strip() == "Atualizar mídias"
        ),
        None,
    )
    save_button = next(
        (
            button
            for button in self.findChildren(QPushButton)
            if button.text().strip() == "Processar cadastro"
        ),
        None,
    )
    prompt_button = next(
        (
            button
            for button in self.findChildren(QPushButton)
            if button.text().strip() == "Prompts"
        ),
        None,
    )
    actions = getattr(self, "_cadastro_actions", None)
    settings_layout = settings_scroll.widget().layout() if settings_scroll else None
    basic = self.product_name.parentWidget()
    basic_layout = basic.layout() if basic is not None else None
    if actions is None and settings_layout is not None:
        for index in range(settings_layout.count()):
            item = settings_layout.itemAt(index)
            candidate = item.layout()
            if candidate is None:
                continue
            widgets = [
                candidate.itemAt(child_index).widget()
                for child_index in range(candidate.count())
            ]
            if refresh_button in widgets or save_button in widgets:
                actions = candidate
                settings_layout.removeItem(actions)
                break

    if actions is not None:
        if settings_layout is not None:
            settings_layout.removeItem(actions)
        while actions.count():
            item = actions.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        if prompt_button is not None:
            prompt_button.hide()
            prompt_button.setParent(None)

        if refresh_button is not None:
            refresh_button.setToolTip(
                "Ler novamente a pasta de origem e montar um grupo inicial. "
                "Depois, arraste as mídias entre os grupos."
            )
            refresh_button.setObjectName("refreshMediaButton")
            refresh_button.setMinimumSize(150, 34)
            refresh_button.setMaximumWidth(180)
            refresh_button.setStyleSheet(
                f"""
                QPushButton#refreshMediaButton {{
                    background-color: {COR_ACENTO};
                    color: {BRANCO};
                    border: 1px solid {COR_ACENTO_HOVER};
                    border-radius: 5px;
                    padding: 7px 14px;
                    font-weight: 600;
                }}
                QPushButton#refreshMediaButton:hover {{
                    background-color: {COR_ACENTO_HOVER};
                }}
                """
            )
        if save_button is not None:
            save_button.setObjectName("saveProductButton")
            save_button.setMinimumSize(205, 42)
            save_button.setMaximumWidth(240)
            save_button.setStyleSheet(
                f"""
                QPushButton#saveProductButton {{
                    background-color: {COR_SUCESSO};
                    color: {BRANCO};
                    border: 1px solid {COR_SUCESSO_HOVER};
                    border-radius: 5px;
                    padding: 9px 18px;
                    font-size: 11px;
                    font-weight: 700;
                }}
                QPushButton#saveProductButton:hover {{
                    background-color: {COR_SUCESSO_HOVER};
                }}
                """
            )
        actions.setContentsMargins(0, 6, 0, 6)
        actions.setSpacing(10)
        if refresh_button is not None:
            actions.addWidget(refresh_button)
        if save_button is not None:
            actions.addWidget(save_button)
        actions.addStretch()
        if basic_layout is not None:
            basic_layout.addLayout(actions)

    if actions is not None:
        self._cadastro_actions = actions

    measures_label = next(
        (
            label
            for label in right.findChildren(QWidget)
            if getattr(label, "text", lambda: "")()
            == "<b>Grupos de variações, kits e medidas</b>"
        ),
        None,
    )
    if measures_label is not None:
        measures_label.setToolTip(
            "A classificação cria os grupos automaticamente. "
            "Cada grupo recebe uma única linha de medidas."
        )
    measurement_scroll = next(
        (
            scroll
            for scroll in right.findChildren(QScrollArea)
            if scroll.widget() is self.measurement_container
        ),
        None,
    )
    if measures_label is None or measurement_scroll is None:
        return

    while right_layout.count():
        item = right_layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)

    txt_panel = _create_txt_reference_panel(self)
    video_panel = _create_video_reference_panel(self)

    left_column = QWidget(right)
    left_layout = QVBoxLayout(left_column)
    left_layout.setContentsMargins(0, 0, 6, 0)

    media_panel = QWidget(right)
    media_layout = QVBoxLayout(media_panel)
    media_layout.setContentsMargins(0, 0, 0, 0)
    media_layout.addWidget(self.files_label)
    media_layout.addWidget(self.media_gallery, 1)
    left_layout.addWidget(txt_panel)
    left_layout.addWidget(media_panel, 1)
    left_layout.addWidget(video_panel)

    right_column = QWidget(right)
    right_layout_inner = QVBoxLayout(right_column)
    right_layout_inner.setContentsMargins(6, 0, 0, 0)

    measures_panel = QWidget(right)
    measures_layout = QVBoxLayout(measures_panel)
    measures_layout.setContentsMargins(0, 0, 0, 0)
    measures_layout.addWidget(measures_label)
    measures_layout.addWidget(measurement_scroll, 1)
    if classification is not None:
        right_layout_inner.addWidget(classification)
    right_layout_inner.addWidget(measures_panel, 1)

    splitter = QSplitter(Qt.Orientation.Horizontal, right)
    splitter.setChildrenCollapsible(False)
    splitter.addWidget(left_column)
    splitter.addWidget(right_column)
    splitter.setStretchFactor(0, 1)
    splitter.setStretchFactor(1, 2)
    splitter.setSizes([300, 720])
    right_layout.addWidget(splitter, 1)
    self._central_vertical_splitter = splitter


def _init(
    self,
    on_saved,
    on_open_prompts=None,
) -> None:
    # A inicialização original procura MediaGallery no namespace do módulo
    # legado em tempo de execução, portanto a substituição acima é suficiente
    # para montar a galeria nova sem duplicar a tela inteira.
    self._manual_assignments: dict[str, dict[str, object]] = {}
    _legacy_init(self, on_saved, on_open_prompts)
    _organizar_painel_central(self)
    _update_video_reference(
        self,
        [
            name
            for name in self.files
            if name.lower().endswith(legacy.VIDEO_EXTENSIONS)
        ],
    )
    _update_txt_reference(self)
    _refresh_product_options(self)
    _setup_ai_context(self)


# O módulo legado já pode ter recebido uma versão parcial destes métodos.
# Sobrescrevemos explicitamente para manter apenas este comportamento.
CadastroTab.__init__ = _init
CadastroTab.refresh_files = _refresh_files
CadastroTab.refresh_product_options = _refresh_product_options
CadastroTab.set_ai_context_callback = _set_ai_context_callback
CadastroTab._schedule_ai_context = _schedule_ai_context
CadastroTab._snapshot_ai_context = _snapshot_ai_context
CadastroTab._publish_ai_context = _publish_ai_context
CadastroTab.rebuild_measurements = _rebuild_measurements
CadastroTab.collect_data = _manual_collect_data
CadastroTab.save_product = _save_product
CadastroTab.save_finished = _save_finished
