"""Janela principal e telas que não pertencem ao cadastro."""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from _FERRAMENTAS_.Prompts import (
    Criar_Fundo_img_MOSTRA,
    Descrition_entrad,
    Foto_Profissional_Marketplace,
    Prompt_Analisador_Produtos,
    Remover_Sombras_Fundo_Branco,
)
from _FERRAMENTAS_.ia_prompt_catalogo import carregar_catalogo, salvar_prompt
from _APP_.Cadastro.Cadastro.App_Cadastro_Prod_PySide6_Enhanced import CadastroTab
from _APP_.Cadastro.Criacao.App_Criacao_PySide6 import CreationTab as ModularProductionTab
from _APP_.Configuracao.Prompts import CatalogPromptsTab
from _APP_.Marketplace.Registros import RecordsTab
from _APP_.PySide6_core import (
    BackgroundMixin,
    DB_PATH,
    apagar_entrada,
    executar_producao,
    init_database,
    ler_entradas,
    parse_tipo_kit,
)


class PromptCard(QGroupBox):
    """Cartão com texto somente leitura e ação de cópia."""

    def __init__(self, title: str, text: str):
        super().__init__(title)
        layout = QVBoxLayout(self)
        self.editor = QPlainTextEdit()
        self.editor.setPlainText(text.strip())
        self.editor.setReadOnly(True)
        self.editor.setMinimumHeight(150)
        layout.addWidget(self.editor)
        self.copy_button = QPushButton("Copiar prompt")
        self.copy_button.clicked.connect(self.copy_prompt)
        layout.addWidget(self.copy_button)

    def copy_prompt(self) -> None:
        QApplication.clipboard().setText(self.editor.toPlainText())
        self.copy_button.setText("Copiado")

    def set_text(self, text: str) -> None:
        self.editor.setPlainText(text.strip())


class PromptCatalogCard(QGroupBox):
    """Editor de um prompt documentado por finalidade e escopo."""

    prompt_saved = Signal()

    def __init__(self, item: dict[str, object]):
        nome = str(item.get("nome") or item.get("id") or "Prompt")
        escopo = str(item.get("escopo") or "Geral")
        super().__init__(f"{nome} · {escopo}")
        self.item = dict(item)
        layout = QVBoxLayout(self)

        finalidade = QLabel(str(item.get("finalidade") or "Sem finalidade documentada."))
        finalidade.setWordWrap(True)
        layout.addWidget(finalidade)

        self.editor = QPlainTextEdit()
        self.editor.setPlainText(str(item.get("texto") or ""))
        self.editor.setMinimumHeight(150)
        layout.addWidget(self.editor)

        self.save_button = QPushButton("Salvar prompt no AppData")
        self.save_button.clicked.connect(self.save_prompt)
        layout.addWidget(self.save_button)

    def save_prompt(self) -> None:
        self.item["texto"] = self.editor.toPlainText()
        salvar_prompt(self.item)
        self.save_button.setText("Prompt salvo")
        self.prompt_saved.emit()


class PromptsTab(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.addWidget(
            QLabel(
                "<b>Prompts pré-configurados</b><br>"
                "Use o botão de cada cartão para copiar e colar na IA."
            )
        )

        product_row = QHBoxLayout()
        product_row.addWidget(QLabel("Produto para o prompt de marketplace:"))
        self.product_name = QLineEdit()
        self.product_name.setPlaceholderText("Nome do produto")
        product_row.addWidget(self.product_name, 1)
        update_button = QPushButton("Atualizar prompt")
        update_button.clicked.connect(self.update_marketplace_prompt)
        product_row.addWidget(update_button)
        root.addLayout(product_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cards = QWidget()
        cards_layout = QVBoxLayout(cards)
        catalogo = carregar_catalogo()
        for item in catalogo:
            cards_layout.addWidget(PromptCatalogCard(item))

        self.marketplace_card = PromptCard(
            "Descrição de Marketplace",
            Descrition_entrad(""),
        )
        cards_layout.addWidget(
            QLabel(
                "<b>Prompts históricos</b><br>"
                "Estes prompts continuam disponíveis como referência enquanto "
                "são migrados para o catálogo editável."
            )
        )
        for card in (
            PromptCard("Prompt Analisador de Produtos", Prompt_Analisador_Produtos()),
            PromptCard("Remover Fundo e Sombras", Remover_Sombras_Fundo_Branco()),
            PromptCard("Foto Profissional Marketplace", Foto_Profissional_Marketplace()),
            PromptCard("Criar Fundo para Mostrar o Produto", Criar_Fundo_img_MOSTRA()),
            self.marketplace_card,
        ):
            cards_layout.addWidget(card)
        cards_layout.addStretch()
        scroll.setWidget(cards)
        root.addWidget(scroll, 1)

    def update_marketplace_prompt(self) -> None:
        self.marketplace_card.set_text(
            Descrition_entrad(self.product_name.text().strip())
        )


class ProductionTab(QWidget, BackgroundMixin):
    def __init__(self):
        QWidget.__init__(self)
        BackgroundMixin.__init__(self)
        self.current_row: tuple | None = None
        self.build_ui()
        self.refresh()

    def build_ui(self) -> None:
        root = QVBoxLayout(self)
        controls = QGroupBox("Produto mais recente")
        form = QFormLayout(controls)
        self.product_label = QLabel("Nenhum cadastro encontrado.")
        self.path_label = QLabel("-")
        self.path_label.setWordWrap(True)
        self.config_label = QLabel("-")
        self.delete_button = QPushButton("Apagar cadastro")
        self.delete_button.clicked.connect(self.delete_current)
        form.addRow("Produto", self.product_label)
        form.addRow("Pasta", self.path_label)
        form.addRow("Configuração", self.config_label)
        form.addRow(self.delete_button)
        root.addWidget(controls)

        options = QGroupBox("Configuração da produção")
        options_layout = QGridLayout(options)
        self.shadow = QComboBox()
        self.shadow.addItems(["2.0", "0.5", "1.5", "2.5", "40"])
        self.music = QComboBox()
        self.music.addItems(["0", "0.15", "0.25", "0.55", "0.80"])
        self.order = QComboBox()
        self.order.addItems(["", "Crescente", "Decrescente"])
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
        self.kit_options = QListWidget()
        for value in (
            "Peça única",
            "Kit: 2",
            "Kit: 3",
            "Kit: 4",
            "Kit: 5",
            "Kit: 6",
            "Kit: 8",
            "Kit: 10",
        ):
            item = QListWidgetItem(value)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.kit_options.addItem(item)
        options_layout.addWidget(QLabel("Altura da sombra"), 0, 0)
        options_layout.addWidget(self.shadow, 0, 1)
        options_layout.addWidget(QLabel("Volume da música"), 1, 0)
        options_layout.addWidget(self.music, 1, 1)
        options_layout.addWidget(QLabel("Ordem das imagens"), 2, 0)
        options_layout.addWidget(self.order, 2, 1)
        options_layout.addWidget(QLabel("Tipo de medidas"), 3, 0)
        options_layout.addWidget(self.measure_type, 3, 1)
        options_layout.addWidget(QLabel("Formas de venda"), 0, 2)
        options_layout.addWidget(self.kit_options, 0, 3, 4, 1)
        options_layout.setColumnStretch(3, 1)
        root.addWidget(options)

        actions = QHBoxLayout()
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.refresh)
        self.run_button = QPushButton("Iniciar produção")
        self.run_button.clicked.connect(self.run_production)
        actions.addWidget(self.refresh_button)
        actions.addWidget(self.run_button)
        actions.addStretch()
        root.addLayout(actions)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        root.addWidget(self.progress)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(150)
        root.addWidget(self.log, 1)

    def refresh(self) -> None:
        entradas = ler_entradas()
        self.current_row = entradas[-1] if entradas else None
        if not self.current_row:
            self.product_label.setText("Nenhum cadastro encontrado.")
            self.path_label.setText("-")
            self.config_label.setText("-")
            self.run_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            return
        self.product_label.setText(str(self.current_row[0]))
        self.path_label.setText(str(self.current_row[2]))
        self.config_label.setText(str(self.current_row[7]))
        self.run_button.setEnabled(True)
        self.delete_button.setEnabled(True)

    def selected_kit_options(self) -> list[str] | str | None:
        selecionados = [
            self.kit_options.item(index).text()
            for index in range(self.kit_options.count())
            if self.kit_options.item(index).checkState()
            == Qt.CheckState.Checked
        ]
        if selecionados:
            return selecionados
        config = parse_tipo_kit(str(self.current_row[7])) if self.current_row else {}
        if config.get("TIPO") in ("ÚNICO", "UNICO"):
            return "Sem Kit"
        return None

    def delete_current(self) -> None:
        if not self.current_row:
            return
        resposta = QMessageBox.question(
            self,
            "Confirmar",
            f"Apagar o cadastro de {self.current_row[0]}?",
        )
        if resposta == QMessageBox.StandardButton.Yes:
            apagar_entrada(str(self.current_row[0]))
            self.refresh()

    def run_production(self) -> None:
        if not self.current_row:
            return
        self.run_button.setEnabled(False)
        self.progress.show()
        self.start_task(
            executar_producao,
            self.current_row,
            float(self.shadow.currentText()),
            float(self.music.currentText()),
            self.order.currentText().lower(),
            self.measure_type.currentText(),
            self.selected_kit_options(),
            on_done=self.production_done,
            on_error=self.production_failed,
        )

    def production_done(self, result: object) -> None:
        self.run_button.setEnabled(True)
        self.progress.hide()
        QMessageBox.information(self, "Concluído", f"Produção concluída:\n{result}")

    def production_failed(self, error: str) -> None:
        self.run_button.setEnabled(True)
        self.progress.hide()
        self.log.appendPlainText(error)
        QMessageBox.critical(self, "Erro na produção", error)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Controle de Produtos")
        self.resize(1400, 900)
        self.setStyleSheet(
            """
            QWidget { font-size: 14px; }
            QGroupBox { font-weight: bold; margin-top: 10px; }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
            QPushButton { padding: 7px 12px; }
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
                padding: 5px;
            }
            """
        )
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        # A aba ativa usa a implementação modular. As ProductionTab acima
        # permanecem apenas como referência histórica neste arquivo.
        self.production_tab = ModularProductionTab()
        self.records_tab = RecordsTab()
        self.prompts_tab = PromptsTab()
        self.cadastro_tab = CadastroTab(
            self.production_tab.refresh,
            self.show_prompts,
        )
        self.tabs.addTab(self.cadastro_tab, "Cadastro")
        self.tabs.addTab(self.production_tab, "Produção")
        self.tabs.addTab(self.records_tab, "Registros")
        self.tabs.addTab(self.prompts_tab, "Prompts")
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index: int) -> None:
        if self.tabs.widget(index) is self.records_tab:
            self.records_tab.refresh()

    def show_prompts(self) -> None:
        """Abre os prompts pelo botão disponível dentro do Cadastro."""
        self.tabs.setCurrentWidget(self.prompts_tab)


# MainWindow procura PromptsTab em tempo de execucao. A atribuicao preserva as
# classes históricas; a implementação ativa vem do pacote _APP_/prompts.
PromptsTab = CatalogPromptsTab

"""Janela principal e telas que não pertencem ao cadastro."""

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from _FERRAMENTAS_.Prompts import (
    Criar_Fundo_img_MOSTRA,
    Descrition_entrad,
    Foto_Profissional_Marketplace,
    Prompt_Analisador_Produtos,
    Remover_Sombras_Fundo_Branco,
)
from _APP_.Cadastro.Cadastro.App_Cadastro_Prod_PySide6_Enhanced import CadastroTab
from _APP_.PySide6_core import (
    BackgroundMixin,
    DB_PATH,
    apagar_entrada,
    executar_producao,
    init_database,
    ler_entradas,
    parse_tipo_kit,
)


class PromptCard(QGroupBox):
    """Cartão com texto somente leitura e ação de cópia."""

    def __init__(self, title: str, text: str):
        super().__init__(title)
        layout = QVBoxLayout(self)
        self.editor = QPlainTextEdit()
        self.editor.setPlainText(text.strip())
        self.editor.setReadOnly(True)
        self.editor.setMinimumHeight(150)
        layout.addWidget(self.editor)
        self.copy_button = QPushButton("Copiar prompt")
        self.copy_button.clicked.connect(self.copy_prompt)
        layout.addWidget(self.copy_button)

    def copy_prompt(self) -> None:
        QApplication.clipboard().setText(self.editor.toPlainText())
        self.copy_button.setText("Copiado")

    def set_text(self, text: str) -> None:
        self.editor.setPlainText(text.strip())


class PromptsTab(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.addWidget(
            QLabel(
                "<b>Prompts pré-configurados</b><br>"
                "Use o botão de cada cartão para copiar e colar na IA."
            )
        )

        product_row = QHBoxLayout()
        product_row.addWidget(QLabel("Produto para o prompt de marketplace:"))
        self.product_name = QLineEdit()
        self.product_name.setPlaceholderText("Nome do produto")
        product_row.addWidget(self.product_name, 1)
        update_button = QPushButton("Atualizar prompt")
        update_button.clicked.connect(self.update_marketplace_prompt)
        product_row.addWidget(update_button)
        root.addLayout(product_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cards = QWidget()
        cards_layout = QVBoxLayout(cards)
        self.marketplace_card = PromptCard(
            "Descrição de Marketplace",
            Descrition_entrad(""),
        )
        for card in (
            PromptCard("Prompt Analisador de Produtos", Prompt_Analisador_Produtos()),
            PromptCard("Remover Fundo e Sombras", Remover_Sombras_Fundo_Branco()),
            PromptCard("Foto Profissional Marketplace", Foto_Profissional_Marketplace()),
            PromptCard("Criar Fundo para Mostrar o Produto", Criar_Fundo_img_MOSTRA()),
            self.marketplace_card,
        ):
            cards_layout.addWidget(card)
        cards_layout.addStretch()
        scroll.setWidget(cards)
        root.addWidget(scroll, 1)

    def update_marketplace_prompt(self) -> None:
        self.marketplace_card.set_text(
            Descrition_entrad(self.product_name.text().strip())
        )


class ProductionTab(QWidget, BackgroundMixin):
    def __init__(self):
        QWidget.__init__(self)
        BackgroundMixin.__init__(self)
        self.current_row: tuple | None = None
        self.build_ui()
        self.refresh()

    def build_ui(self) -> None:
        root = QVBoxLayout(self)
        controls = QGroupBox("Produto mais recente")
        form = QFormLayout(controls)
        self.product_label = QLabel("Nenhum cadastro encontrado.")
        self.path_label = QLabel("-")
        self.path_label.setWordWrap(True)
        self.config_label = QLabel("-")
        self.delete_button = QPushButton("Apagar cadastro")
        self.delete_button.clicked.connect(self.delete_current)
        form.addRow("Produto", self.product_label)
        form.addRow("Pasta", self.path_label)
        form.addRow("Configuração", self.config_label)
        form.addRow(self.delete_button)
        root.addWidget(controls)

        options = QGroupBox("Configuração da produção")
        options_layout = QGridLayout(options)
        self.shadow = QComboBox()
        self.shadow.addItems(["2.0", "0.5", "1.5", "2.5", "40"])
        self.music = QComboBox()
        self.music.addItems(["0", "0.15", "0.25", "0.55", "0.80"])
        self.order = QComboBox()
        self.order.addItems(["", "Crescente", "Decrescente"])
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
        self.kit_options = QListWidget()
        for value in (
            "Peça única",
            "Kit: 2",
            "Kit: 3",
            "Kit: 4",
            "Kit: 5",
            "Kit: 6",
            "Kit: 8",
            "Kit: 10",
        ):
            item = QListWidgetItem(value)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.kit_options.addItem(item)
        options_layout.addWidget(QLabel("Altura da sombra"), 0, 0)
        options_layout.addWidget(self.shadow, 0, 1)
        options_layout.addWidget(QLabel("Volume da música"), 1, 0)
        options_layout.addWidget(self.music, 1, 1)
        options_layout.addWidget(QLabel("Ordem das imagens"), 2, 0)
        options_layout.addWidget(self.order, 2, 1)
        options_layout.addWidget(QLabel("Tipo de medidas"), 3, 0)
        options_layout.addWidget(self.measure_type, 3, 1)
        options_layout.addWidget(QLabel("Formas de venda"), 0, 2)
        options_layout.addWidget(self.kit_options, 0, 3, 4, 1)
        options_layout.setColumnStretch(3, 1)
        root.addWidget(options)

        actions = QHBoxLayout()
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.refresh)
        self.run_button = QPushButton("Iniciar produção")
        self.run_button.clicked.connect(self.run_production)
        actions.addWidget(self.refresh_button)
        actions.addWidget(self.run_button)
        actions.addStretch()
        root.addLayout(actions)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        root.addWidget(self.progress)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(150)
        root.addWidget(self.log, 1)

    def refresh(self) -> None:
        entradas = ler_entradas()
        self.current_row = entradas[-1] if entradas else None
        if not self.current_row:
            self.product_label.setText("Nenhum cadastro encontrado.")
            self.path_label.setText("-")
            self.config_label.setText("-")
            self.run_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            return
        self.product_label.setText(str(self.current_row[0]))
        self.path_label.setText(str(self.current_row[2]))
        self.config_label.setText(str(self.current_row[7]))
        self.run_button.setEnabled(True)
        self.delete_button.setEnabled(True)

    def selected_kit_options(self) -> list[str] | str | None:
        selecionados = [
            self.kit_options.item(index).text()
            for index in range(self.kit_options.count())
            if self.kit_options.item(index).checkState()
            == Qt.CheckState.Checked
        ]
        if selecionados:
            return selecionados
        config = parse_tipo_kit(str(self.current_row[7])) if self.current_row else {}
        if config.get("TIPO") in ("ÚNICO", "UNICO"):
            return "Sem Kit"
        return None

    def delete_current(self) -> None:
        if not self.current_row:
            return
        resposta = QMessageBox.question(
            self,
            "Confirmar",
            f"Apagar o cadastro de {self.current_row[0]}?",
        )
        if resposta == QMessageBox.StandardButton.Yes:
            apagar_entrada(str(self.current_row[0]))
            self.refresh()

    def run_production(self) -> None:
        if not self.current_row:
            return
        self.run_button.setEnabled(False)
        self.progress.show()
        self.start_task(
            executar_producao,
            self.current_row,
            float(self.shadow.currentText()),
            float(self.music.currentText()),
            self.order.currentText().lower(),
            self.measure_type.currentText(),
            self.selected_kit_options(),
            on_done=self.production_done,
            on_error=self.production_failed,
        )

    def production_done(self, result: object) -> None:
        self.run_button.setEnabled(True)
        self.progress.hide()
        QMessageBox.information(self, "Concluído", f"Produção concluída:\n{result}")

    def production_failed(self, error: str) -> None:
        self.run_button.setEnabled(True)
        self.progress.hide()
        self.log.appendPlainText(error)
        QMessageBox.critical(self, "Erro na produção", error)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Controle de Produtos")
        self.resize(1400, 900)
        self.setStyleSheet(
            """
            QWidget { font-size: 14px; }
            QGroupBox { font-weight: bold; margin-top: 10px; }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
            QPushButton { padding: 7px 12px; }
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
                padding: 5px;
            }
            """
        )
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.production_tab = ModularProductionTab()
        self.records_tab = RecordsTab()
        self.prompts_tab = PromptsTab()
        self.cadastro_tab = CadastroTab(
            self.production_tab.refresh,
            self.show_prompts,
        )
        self.tabs.addTab(self.cadastro_tab, "Cadastro")
        self.tabs.addTab(self.production_tab, "Produção")
        self.tabs.addTab(self.records_tab, "Registros")
        self.tabs.addTab(self.prompts_tab, "Prompts")
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index: int) -> None:
        if self.tabs.widget(index) is self.records_tab:
            self.records_tab.refresh()

    def show_prompts(self) -> None:
        """Abre os prompts pelo botão disponível dentro do Cadastro."""
        self.tabs.setCurrentWidget(self.prompts_tab)

"""Janela principal e telas que não pertencem ao cadastro."""


import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from _FERRAMENTAS_.Prompts import (
    Criar_Fundo_img_MOSTRA,
    Descrition_entrad,
    Foto_Profissional_Marketplace,
    Prompt_Analisador_Produtos,
    Remover_Sombras_Fundo_Branco,
)
from _APP_.Cadastro.Cadastro.App_Cadastro_Prod_PySide6_Enhanced import CadastroTab
from _APP_.PySide6_core import (
    BackgroundMixin,
    DB_PATH,
    apagar_entrada,
    executar_producao,
    init_database,
    ler_entradas,
    parse_tipo_kit,
)


class PromptCard(QGroupBox):
    """Cartão com texto somente leitura e ação de cópia."""

    def __init__(self, title: str, text: str):
        super().__init__(title)
        layout = QVBoxLayout(self)
        self.editor = QPlainTextEdit()
        self.editor.setPlainText(text.strip())
        self.editor.setReadOnly(True)
        self.editor.setMinimumHeight(150)
        layout.addWidget(self.editor)
        self.copy_button = QPushButton("Copiar prompt")
        self.copy_button.clicked.connect(self.copy_prompt)
        layout.addWidget(self.copy_button)

    def copy_prompt(self) -> None:
        QApplication.clipboard().setText(self.editor.toPlainText())
        self.copy_button.setText("Copiado")

    def set_text(self, text: str) -> None:
        self.editor.setPlainText(text.strip())


class PromptsTab(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.addWidget(
            QLabel(
                "<b>Prompts pré-configurados</b><br>"
                "Use o botão de cada cartão para copiar e colar na IA."
            )
        )

        product_row = QHBoxLayout()
        product_row.addWidget(QLabel("Produto para o prompt de marketplace:"))
        self.product_name = QLineEdit()
        self.product_name.setPlaceholderText("Nome do produto")
        product_row.addWidget(self.product_name, 1)
        update_button = QPushButton("Atualizar prompt")
        update_button.clicked.connect(self.update_marketplace_prompt)
        product_row.addWidget(update_button)
        root.addLayout(product_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cards = QWidget()
        cards_layout = QVBoxLayout(cards)
        self.marketplace_card = PromptCard(
            "Descrição de Marketplace",
            Descrition_entrad(""),
        )
        for card in (
            PromptCard("Prompt Analisador de Produtos", Prompt_Analisador_Produtos()),
            PromptCard("Remover Fundo e Sombras", Remover_Sombras_Fundo_Branco()),
            PromptCard("Foto Profissional Marketplace", Foto_Profissional_Marketplace()),
            PromptCard("Criar Fundo para Mostrar o Produto", Criar_Fundo_img_MOSTRA()),
            self.marketplace_card,
        ):
            cards_layout.addWidget(card)
        cards_layout.addStretch()
        scroll.setWidget(cards)
        root.addWidget(scroll, 1)

    def update_marketplace_prompt(self) -> None:
        self.marketplace_card.set_text(
            Descrition_entrad(self.product_name.text().strip())
        )


class ProductionTab(QWidget, BackgroundMixin):
    def __init__(self):
        QWidget.__init__(self)
        BackgroundMixin.__init__(self)
        self.current_row: tuple | None = None
        self.build_ui()
        self.refresh()

    def build_ui(self) -> None:
        root = QVBoxLayout(self)
        controls = QGroupBox("Produto mais recente")
        form = QFormLayout(controls)
        self.product_label = QLabel("Nenhum cadastro encontrado.")
        self.path_label = QLabel("-")
        self.path_label.setWordWrap(True)
        self.config_label = QLabel("-")
        self.delete_button = QPushButton("Apagar cadastro")
        self.delete_button.clicked.connect(self.delete_current)
        form.addRow("Produto", self.product_label)
        form.addRow("Pasta", self.path_label)
        form.addRow("Configuração", self.config_label)
        form.addRow(self.delete_button)
        root.addWidget(controls)

        options = QGroupBox("Configuração da produção")
        options_layout = QGridLayout(options)
        self.shadow = QComboBox()
        self.shadow.addItems(["2.0", "0.5", "1.5", "2.5", "40"])
        self.music = QComboBox()
        self.music.addItems(["0", "0.15", "0.25", "0.55", "0.80"])
        self.order = QComboBox()
        self.order.addItems(["", "Crescente", "Decrescente"])
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
        self.kit_options = QListWidget()
        for value in (
            "Peça única",
            "Kit: 2",
            "Kit: 3",
            "Kit: 4",
            "Kit: 5",
            "Kit: 6",
            "Kit: 8",
            "Kit: 10",
        ):
            item = QListWidgetItem(value)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.kit_options.addItem(item)
        options_layout.addWidget(QLabel("Altura da sombra"), 0, 0)
        options_layout.addWidget(self.shadow, 0, 1)
        options_layout.addWidget(QLabel("Volume da música"), 1, 0)
        options_layout.addWidget(self.music, 1, 1)
        options_layout.addWidget(QLabel("Ordem das imagens"), 2, 0)
        options_layout.addWidget(self.order, 2, 1)
        options_layout.addWidget(QLabel("Tipo de medidas"), 3, 0)
        options_layout.addWidget(self.measure_type, 3, 1)
        options_layout.addWidget(QLabel("Formas de venda"), 0, 2)
        options_layout.addWidget(self.kit_options, 0, 3, 4, 1)
        options_layout.setColumnStretch(3, 1)
        root.addWidget(options)

        actions = QHBoxLayout()
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.refresh)
        self.run_button = QPushButton("Iniciar produção")
        self.run_button.clicked.connect(self.run_production)
        actions.addWidget(self.refresh_button)
        actions.addWidget(self.run_button)
        actions.addStretch()
        root.addLayout(actions)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        root.addWidget(self.progress)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(150)
        root.addWidget(self.log, 1)

    def refresh(self) -> None:
        entradas = ler_entradas()
        self.current_row = entradas[-1] if entradas else None
        if not self.current_row:
            self.product_label.setText("Nenhum cadastro encontrado.")
            self.path_label.setText("-")
            self.config_label.setText("-")
            self.run_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            return
        self.product_label.setText(str(self.current_row[0]))
        self.path_label.setText(str(self.current_row[2]))
        self.config_label.setText(str(self.current_row[7]))
        self.run_button.setEnabled(True)
        self.delete_button.setEnabled(True)

    def selected_kit_options(self) -> list[str] | str | None:
        selecionados = [
            self.kit_options.item(index).text()
            for index in range(self.kit_options.count())
            if self.kit_options.item(index).checkState()
            == Qt.CheckState.Checked
        ]
        if selecionados:
            return selecionados
        config = parse_tipo_kit(str(self.current_row[7])) if self.current_row else {}
        if config.get("TIPO") in ("ÚNICO", "UNICO"):
            return "Sem Kit"
        return None

    def delete_current(self) -> None:
        if not self.current_row:
            return
        resposta = QMessageBox.question(
            self,
            "Confirmar",
            f"Apagar o cadastro de {self.current_row[0]}?",
        )
        if resposta == QMessageBox.StandardButton.Yes:
            apagar_entrada(str(self.current_row[0]))
            self.refresh()

    def run_production(self) -> None:
        if not self.current_row:
            return
        self.run_button.setEnabled(False)
        self.progress.show()
        self.start_task(
            executar_producao,
            self.current_row,
            float(self.shadow.currentText()),
            float(self.music.currentText()),
            self.order.currentText().lower(),
            self.measure_type.currentText(),
            self.selected_kit_options(),
            on_done=self.production_done,
            on_error=self.production_failed,
        )

    def production_done(self, result: object) -> None:
        self.run_button.setEnabled(True)
        self.progress.hide()
        QMessageBox.information(self, "Concluído", f"Produção concluída:\n{result}")

    def production_failed(self, error: str) -> None:
        self.run_button.setEnabled(True)
        self.progress.hide()
        self.log.appendPlainText(error)
        QMessageBox.critical(self, "Erro na produção", error)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Controle de Produtos")
        self.resize(1400, 900)
        self.setStyleSheet(
            """
            QWidget { font-size: 14px; }
            QGroupBox { font-weight: bold; margin-top: 10px; }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
            QPushButton { padding: 7px 12px; }
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
                padding: 5px;
            }
            """
        )
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.production_tab = ModularProductionTab()
        self.records_tab = RecordsTab()
        self.prompts_tab = PromptsTab()
        self.cadastro_tab = CadastroTab(
            self.production_tab.refresh,
            self.show_prompts,
        )
        self.tabs.addTab(self.cadastro_tab, "Cadastro")
        self.tabs.addTab(self.production_tab, "Produção")
        self.tabs.addTab(self.records_tab, "Registros")
        self.tabs.addTab(self.prompts_tab, "Prompts")
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index: int) -> None:
        if self.tabs.widget(index) is self.records_tab:
            self.records_tab.refresh()

    def show_prompts(self) -> None:
        """Abre os prompts pelo botão disponível dentro do Cadastro."""
        self.tabs.setCurrentWidget(self.prompts_tab)

"""Janela principal e telas que não pertencem ao cadastro."""

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from _FERRAMENTAS_.Prompts import (
    Criar_Fundo_img_MOSTRA,
    Descrition_entrad,
    Foto_Profissional_Marketplace,
    Prompt_Analisador_Produtos,
    Remover_Sombras_Fundo_Branco,
)
from _APP_.Cadastro.Cadastro.App_Cadastro_Prod_PySide6_Enhanced import CadastroTab
from _APP_.PySide6_core import (
    BackgroundMixin,
    DB_PATH,
    apagar_entrada,
    executar_producao,
    init_database,
    ler_entradas,
    parse_tipo_kit,
)


class PromptCard(QGroupBox):
    """Cartão com texto somente leitura e ação de cópia."""

    def __init__(self, title: str, text: str):
        super().__init__(title)
        layout = QVBoxLayout(self)
        self.editor = QPlainTextEdit()
        self.editor.setPlainText(text.strip())
        self.editor.setReadOnly(True)
        self.editor.setMinimumHeight(150)
        layout.addWidget(self.editor)
        self.copy_button = QPushButton("Copiar prompt")
        self.copy_button.clicked.connect(self.copy_prompt)
        layout.addWidget(self.copy_button)

    def copy_prompt(self) -> None:
        QApplication.clipboard().setText(self.editor.toPlainText())
        self.copy_button.setText("Copiado")

    def set_text(self, text: str) -> None:
        self.editor.setPlainText(text.strip())


class PromptsTab(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.addWidget(
            QLabel(
                "<b>Prompts pré-configurados</b><br>"
                "Use o botão de cada cartão para copiar e colar na IA."
            )
        )

        product_row = QHBoxLayout()
        product_row.addWidget(QLabel("Produto para o prompt de marketplace:"))
        self.product_name = QLineEdit()
        self.product_name.setPlaceholderText("Nome do produto")
        product_row.addWidget(self.product_name, 1)
        update_button = QPushButton("Atualizar prompt")
        update_button.clicked.connect(self.update_marketplace_prompt)
        product_row.addWidget(update_button)
        root.addLayout(product_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cards = QWidget()
        cards_layout = QVBoxLayout(cards)
        self.marketplace_card = PromptCard(
            "Descrição de Marketplace",
            Descrition_entrad(""),
        )
        for card in (
            PromptCard("Prompt Analisador de Produtos", Prompt_Analisador_Produtos()),
            PromptCard("Remover Fundo e Sombras", Remover_Sombras_Fundo_Branco()),
            PromptCard("Foto Profissional Marketplace", Foto_Profissional_Marketplace()),
            PromptCard("Criar Fundo para Mostrar o Produto", Criar_Fundo_img_MOSTRA()),
            self.marketplace_card,
        ):
            cards_layout.addWidget(card)
        cards_layout.addStretch()
        scroll.setWidget(cards)
        root.addWidget(scroll, 1)

    def update_marketplace_prompt(self) -> None:
        self.marketplace_card.set_text(
            Descrition_entrad(self.product_name.text().strip())
        )


class ProductionTab(QWidget, BackgroundMixin):
    def __init__(self):
        QWidget.__init__(self)
        BackgroundMixin.__init__(self)
        self.current_row: tuple | None = None
        self.build_ui()
        self.refresh()

    def build_ui(self) -> None:
        root = QVBoxLayout(self)
        controls = QGroupBox("Produto mais recente")
        form = QFormLayout(controls)
        self.product_label = QLabel("Nenhum cadastro encontrado.")
        self.path_label = QLabel("-")
        self.path_label.setWordWrap(True)
        self.config_label = QLabel("-")
        self.delete_button = QPushButton("Apagar cadastro")
        self.delete_button.clicked.connect(self.delete_current)
        form.addRow("Produto", self.product_label)
        form.addRow("Pasta", self.path_label)
        form.addRow("Configuração", self.config_label)
        form.addRow(self.delete_button)
        root.addWidget(controls)

        options = QGroupBox("Configuração da produção")
        options_layout = QGridLayout(options)
        self.shadow = QComboBox()
        self.shadow.addItems(["2.0", "0.5", "1.5", "2.5", "40"])
        self.music = QComboBox()
        self.music.addItems(["0", "0.15", "0.25", "0.55", "0.80"])
        self.order = QComboBox()
        self.order.addItems(["", "Crescente", "Decrescente"])
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
        self.kit_options = QListWidget()
        for value in (
            "Peça única",
            "Kit: 2",
            "Kit: 3",
            "Kit: 4",
            "Kit: 5",
            "Kit: 6",
            "Kit: 8",
            "Kit: 10",
        ):
            item = QListWidgetItem(value)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.kit_options.addItem(item)
        options_layout.addWidget(QLabel("Altura da sombra"), 0, 0)
        options_layout.addWidget(self.shadow, 0, 1)
        options_layout.addWidget(QLabel("Volume da música"), 1, 0)
        options_layout.addWidget(self.music, 1, 1)
        options_layout.addWidget(QLabel("Ordem das imagens"), 2, 0)
        options_layout.addWidget(self.order, 2, 1)
        options_layout.addWidget(QLabel("Tipo de medidas"), 3, 0)
        options_layout.addWidget(self.measure_type, 3, 1)
        options_layout.addWidget(QLabel("Formas de venda"), 0, 2)
        options_layout.addWidget(self.kit_options, 0, 3, 4, 1)
        options_layout.setColumnStretch(3, 1)
        root.addWidget(options)

        actions = QHBoxLayout()
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.refresh)
        self.run_button = QPushButton("Iniciar produção")
        self.run_button.clicked.connect(self.run_production)
        actions.addWidget(self.refresh_button)
        actions.addWidget(self.run_button)
        actions.addStretch()
        root.addLayout(actions)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        root.addWidget(self.progress)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(150)
        root.addWidget(self.log, 1)

    def refresh(self) -> None:
        entradas = ler_entradas()
        self.current_row = entradas[-1] if entradas else None
        if not self.current_row:
            self.product_label.setText("Nenhum cadastro encontrado.")
            self.path_label.setText("-")
            self.config_label.setText("-")
            self.run_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            return
        self.product_label.setText(str(self.current_row[0]))
        self.path_label.setText(str(self.current_row[2]))
        self.config_label.setText(str(self.current_row[7]))
        self.run_button.setEnabled(True)
        self.delete_button.setEnabled(True)

    def selected_kit_options(self) -> list[str] | str | None:
        selecionados = [
            self.kit_options.item(index).text()
            for index in range(self.kit_options.count())
            if self.kit_options.item(index).checkState()
            == Qt.CheckState.Checked
        ]
        if selecionados:
            return selecionados
        config = parse_tipo_kit(str(self.current_row[7])) if self.current_row else {}
        if config.get("TIPO") in ("ÚNICO", "UNICO"):
            return "Sem Kit"
        return None

    def delete_current(self) -> None:
        if not self.current_row:
            return
        resposta = QMessageBox.question(
            self,
            "Confirmar",
            f"Apagar o cadastro de {self.current_row[0]}?",
        )
        if resposta == QMessageBox.StandardButton.Yes:
            apagar_entrada(str(self.current_row[0]))
            self.refresh()

    def run_production(self) -> None:
        if not self.current_row:
            return
        self.run_button.setEnabled(False)
        self.progress.show()
        self.start_task(
            executar_producao,
            self.current_row,
            float(self.shadow.currentText()),
            float(self.music.currentText()),
            self.order.currentText().lower(),
            self.measure_type.currentText(),
            self.selected_kit_options(),
            on_done=self.production_done,
            on_error=self.production_failed,
        )

    def production_done(self, result: object) -> None:
        self.run_button.setEnabled(True)
        self.progress.hide()
        QMessageBox.information(self, "Concluído", f"Produção concluída:\n{result}")

    def production_failed(self, error: str) -> None:
        self.run_button.setEnabled(True)
        self.progress.hide()
        self.log.appendPlainText(error)
        QMessageBox.critical(self, "Erro na produção", error)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Controle de Produtos")
        self.resize(1400, 900)
        self.setStyleSheet(
            """
            QWidget { font-size: 14px; }
            QGroupBox { font-weight: bold; margin-top: 10px; }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
            QPushButton { padding: 7px 12px; }
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
                padding: 5px;
            }
            """
        )
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.production_tab = ModularProductionTab()
        self.records_tab = RecordsTab()
        self.prompts_tab = PromptsTab()
        self.cadastro_tab = CadastroTab(
            self.production_tab.refresh,
            self.show_prompts,
        )
        self.tabs.addTab(self.cadastro_tab, "Cadastro")
        self.tabs.addTab(self.production_tab, "Produção")
        self.tabs.addTab(self.records_tab, "Registros")
        self.tabs.addTab(self.prompts_tab, "Prompts")
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index: int) -> None:
        if self.tabs.widget(index) is self.records_tab:
            self.records_tab.refresh()

    def show_prompts(self) -> None:
        """Abre os prompts pelo botão disponível dentro do Cadastro."""
        self.tabs.setCurrentWidget(self.prompts_tab)