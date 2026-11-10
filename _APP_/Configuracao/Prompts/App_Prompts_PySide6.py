"""Aba desktop para editar, organizar e copiar prompts."""

from __future__ import annotations

from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QScrollArea,
    QTabWidget,
    QToolButton,
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
from _FERRAMENTAS_.ia_prompt_catalogo import (
    carregar_catalogo,
    carregar_prompts_imagem,
    carregar_prompts_imagem_padrao,
    carregar_prompts_sistema,
    carregar_referencias,
    salvar_prompt,
    salvar_prompt_imagem,
    salvar_prompt_sistema,
    salvar_referencia,
)
from _ULTILIDADES_.icones import icone, ico_ok, ico_salvar


def _botao_icone(
    icon: QIcon,
    nome: str,
    dica: str,
    fallback: str,
) -> QToolButton:
    """Cria um botão compacto, acessível e com fallback sem qtawesome."""
    button = QToolButton()
    button.setIcon(icon)
    button.setIconSize(QSize(15, 15))
    button.setFixedSize(28, 28)
    button.setAutoRaise(True)
    button.setToolTip(dica)
    button.setAccessibleName(nome)
    if icon.isNull():
        button.setText(fallback)
    return button


IMAGE_PROMPT_SPECS = (
    ("capa", "Capa principal"),
    ("uso", "Produto em uso"),
    ("detalhe", "Detalhes do produto"),
)


class PromptCard(QGroupBox):
    """Cartão de referência editável e copiável."""

    def __init__(self, title: str, text: str):
        super().__init__(title)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 6)
        layout.setSpacing(4)
        self.editor = QPlainTextEdit()
        self.editor.setPlainText(text.strip())
        self.editor.setReadOnly(True)
        self.editor.setMinimumHeight(110)
        layout.addWidget(self.editor)
        self.actions_layout = QHBoxLayout()
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(4)
        self.actions_layout.addStretch(1)
        self.copy_button = _botao_icone(
            icone("fa5s.copy"),
            "Copiar prompt",
            "Copiar prompt para a área de transferência",
            "⧉",
        )
        self.copy_button.clicked.connect(self.copy_prompt)
        self.actions_layout.addWidget(self.copy_button)
        layout.addLayout(self.actions_layout)

    def copy_prompt(self) -> None:
        QApplication.clipboard().setText(self.editor.toPlainText())
        self.copy_button.setToolTip(
            "Prompt copiado para a área de transferência"
        )

    def set_text(self, text: str) -> None:
        self.editor.setPlainText(text.strip())

    def add_action_button(self, button: QToolButton) -> None:
        """Acrescenta ações alinhadas lado a lado no rodapé do cartão."""
        self.actions_layout.addWidget(button)


class PromptCatalogCard(QGroupBox):
    """Editor de um prompt do catálogo por finalidade e escopo."""

    prompt_saved = Signal()

    def __init__(self, item: dict[str, object]):
        nome = str(item.get("nome") or item.get("id") or "Prompt")
        escopo = str(item.get("escopo") or "Geral")
        super().__init__(f"{nome} · {escopo}")
        self.item = dict(item)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 6)
        layout.setSpacing(4)

        finalidade = QLabel(
            str(item.get("finalidade") or "Sem finalidade documentada.")
        )
        finalidade.setWordWrap(True)
        layout.addWidget(finalidade)

        self.editor = QPlainTextEdit()
        self.editor.setPlainText(str(item.get("texto") or ""))
        self.editor.setMinimumHeight(125)
        layout.addWidget(self.editor)

        self.save_button = _botao_icone(
            ico_salvar(),
            "Salvar prompt",
            "Salvar prompt no AppData",
            "💾",
        )
        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.addStretch(1)
        actions.addWidget(self.save_button)
        self.save_button.clicked.connect(self.save_prompt)
        layout.addLayout(actions)

    def save_prompt(self) -> None:
        self.item["texto"] = self.editor.toPlainText()
        salvar_prompt(self.item)
        self.save_button.setIcon(ico_ok())
        self.save_button.setToolTip("Prompt salvo no AppData.")
        self.save_button.setAccessibleName("Prompt salvo")
        self.prompt_saved.emit()


class ImagePromptEditor(QWidget):
    """Editor de um modelo de imagem usado pela preparação em Resultados."""

    def __init__(
        self,
        prompt_id: str,
        title: str,
        text: str,
        default_text: str,
        load_error: str = "",
    ):
        super().__init__()
        self.prompt_id = prompt_id
        self.title = title
        self.default_text = default_text
        self._saved_text = text

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        self.editor = QPlainTextEdit()
        self.editor.setPlainText(text)
        self.editor.setMinimumHeight(180)
        self.editor.setToolTip(
            "Edite o modelo enviado ao preparar este tipo de imagem."
        )
        layout.addWidget(self.editor, 1)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(4)
        actions.addStretch(1)
        self.copy_button = _botao_icone(
            icone("fa5s.copy"),
            f"Copiar prompt: {title}",
            "Copiar o modelo com seus marcadores para a área de transferência",
            "⧉",
        )
        self.copy_button.clicked.connect(self.copy_prompt)
        actions.addWidget(self.copy_button)
        self.restore_button = _botao_icone(
            icone("fa5s.undo"),
            f"Carregar padrão: {title}",
            "Carrega o padrão no editor; clique em Salvar para aplicá-lo",
            "↶",
        )
        self.restore_button.clicked.connect(self.restore_default)
        actions.addWidget(self.restore_button)
        self.save_button = _botao_icone(
            ico_salvar(),
            f"Salvar prompt: {title}",
            "Salvar este modelo em AppData/IAs/prompts/geracao_imagem.json",
            "💾",
        )
        self.save_button.clicked.connect(self.save_prompt)
        actions.addWidget(self.save_button)
        layout.addLayout(actions)

        self.status = QLabel(load_error)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.editor.textChanged.connect(self._mark_dirty)

    def copy_prompt(self) -> None:
        QApplication.clipboard().setText(self.editor.toPlainText())
        self.status.setText("Modelo copiado para a área de transferência.")

    def restore_default(self) -> None:
        self.editor.setPlainText(self.default_text)
        self.status.setText(
            "Padrão carregado no editor. Clique em Salvar para aplicá-lo."
        )

    def save_prompt(self) -> None:
        try:
            salvar_prompt_imagem(
                self.prompt_id,
                self.editor.toPlainText(),
            )
        except (OSError, TypeError, ValueError) as exc:
            self.status.setText("Não foi possível salvar este modelo.")
            QMessageBox.warning(
                self,
                "Erro ao salvar prompt de imagem",
                str(exc),
            )
            return

        self._saved_text = self.editor.toPlainText()
        self.save_button.setIcon(ico_ok())
        self.save_button.setToolTip("Prompt salvo no AppData.")
        self.save_button.setAccessibleName("Prompt salvo")
        self.status.setText(
            "Prompt salvo em AppData/IAs/prompts/geracao_imagem.json."
        )

    def _mark_dirty(self) -> None:
        if self.editor.toPlainText() == self._saved_text:
            return
        self.save_button.setIcon(ico_salvar())
        self.save_button.setToolTip("Salvar prompt no AppData.")
        self.save_button.setAccessibleName("Salvar prompt")


class CatalogPromptsTab(QWidget):
    """Implementação ativa da aba Prompts."""

    ai_context_changed = Signal()

    def __init__(self):
        super().__init__()
        self._carregar_prompts_sistema = carregar_prompts_sistema
        self._salvar_prompt_sistema = salvar_prompt_sistema
        self.system_prompt_id = "anuncio_pesquisa_externa"
        self.system_prompt_defaults = {
            self.system_prompt_id: Descrition_entrad("").strip()
        }
        self._carregar_referencias = carregar_referencias
        self._salvar_referencia = salvar_referencia
        self.reference_defaults = {
            "prompt_analisador_produtos": Prompt_Analisador_Produtos(),
            "remover_fundo_sombras": Remover_Sombras_Fundo_Branco(),
            "foto_profissional_marketplace": Foto_Profissional_Marketplace(),
            "criar_fundo_produto": Criar_Fundo_img_MOSTRA(),
        }
        self.reference_info = [
            (
                "prompt_analisador_produtos",
                "Prompt Analisador de Produtos",
                "Referência para copiar; também aparece como contexto do "
                "orientador na aba Prompts, mas não é acionado automaticamente.",
            ),
            (
                "remover_fundo_sombras",
                "Remover Fundo e Sombras",
                "Referência histórica para copiar; não aciona a remoção de fundo.",
            ),
            (
                "foto_profissional_marketplace",
                "Foto Profissional Marketplace",
                "Referência histórica para copiar; não é aplicada "
                "automaticamente às imagens.",
            ),
            (
                "criar_fundo_produto",
                "Criar Fundo para Mostrar o Produto",
                "Referência histórica para copiar; não gera fundos "
                "automaticamente.",
            ),
        ]
        referencias = carregar_referencias(self.reference_defaults)
        self.image_prompt_defaults = carregar_prompts_imagem_padrao()
        self.image_prompt_load_error = ""
        try:
            image_prompts = carregar_prompts_imagem()
        except (OSError, TypeError, ValueError) as exc:
            image_prompts = dict(self.image_prompt_defaults)
            self.image_prompt_load_error = (
                "Não foi possível carregar os modelos personalizados. "
                f"Os padrões estão sendo exibidos: {exc}"
            )

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.addWidget(QLabel("<b>Usados pelo sistema</b>"))
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_cards = QWidget()
        left_cards_layout = QVBoxLayout(left_cards)
        left_cards_layout.setContentsMargins(4, 4, 4, 4)
        left_cards_layout.setSpacing(6)
        image_prompt_group = QGroupBox(
            "Prompts de imagem · usados em Resultados"
        )
        image_prompt_layout = QVBoxLayout(image_prompt_group)
        image_prompt_layout.setContentsMargins(8, 6, 8, 6)
        image_prompt_layout.setSpacing(4)
        image_prompt_note = QLabel(
            "Os modelos usam produto, descrição e acabamento do cadastro; "
            "“Produto em uso” também recebe a Serventia. Altura, largura, "
            "espessura e peso são incluídos quando podem ser lidos do nome da "
            "imagem. O nome do arquivo não é enviado. Ao preparar o prompt, o "
            "sistema acrescenta somente a proporção salva no Cadastro, sem "
            "impor largura, altura ou resolução em pixels. Marcadores dos "
            "modelos: [[PRODUTO]], [[DESCRICAO]], [[SERVENTIA]], "
            "[[ACABAMENTO]], [[ALTURA]], [[LARGURA]], [[ESPESSURA]] e "
            "[[PESO]]. Os modelos são salvos separadamente dos prompts do "
            "painel de conversa."
        )
        image_prompt_note.setWordWrap(True)
        image_prompt_layout.addWidget(image_prompt_note)
        image_prompt_tabs = QTabWidget()
        for prompt_id, title in IMAGE_PROMPT_SPECS:
            editor = ImagePromptEditor(
                prompt_id,
                title,
                image_prompts.get(
                    prompt_id,
                    self.image_prompt_defaults[prompt_id],
                ),
                self.image_prompt_defaults[prompt_id],
                self.image_prompt_load_error,
            )
            image_prompt_tabs.addTab(editor, title)
        image_prompt_layout.addWidget(image_prompt_tabs)
        left_cards_layout.addWidget(image_prompt_group)

        tooltips = {
            "assistente_cadastro": "Usado pelo painel de IA na aba Cadastro.",
            "assistente_producao": (
                "Usado pelo painel de IA em Criação e Resultados."
            ),
            "assistente_anuncio": (
                "Usado pelo painel de IA e pela geração de texto na aba Anúncio."
            ),
            "assistente_vendas": (
                "Usado pelo painel de IA na aba Vendas; não consulta vendas ou "
                "estoque automaticamente."
            ),
            "assistente_sociais": (
                "Usado pelo painel de IA na aba Sociais para rascunhos textuais."
            ),
            "assistente_registros": (
                "Usado no painel de Registros; os dados devem ser "
                "fornecidos na conversa."
            ),
            "catalogo_prompts": "Usado pelo orientador de IA na aba Prompts.",
            "assistente_configuracoes": (
                "Usado pelo painel de IA na aba Configurações; não lê os valores "
                "da tela."
            ),
        }
        for item in carregar_catalogo():
            card = PromptCatalogCard(item)
            tooltip = tooltips.get(
                str(item.get("id") or ""),
                "Prompt personalizado; vale para o escopo da aba correspondente.",
            )
            card.setToolTip(tooltip)
            card.editor.setToolTip(tooltip)
            card.prompt_saved.connect(self._notify_ai_context_changed)
            left_cards_layout.addWidget(card)

        self.external_research_prompt_tooltip = (
            "Usado na aba Anúncio, no botão que gera o prompt para colar no "
            "ChatGPT. O bloco de dados do cadastro é montado pelo sistema e "
            "vem depois deste texto."
        )
        system_prompts = carregar_prompts_sistema(
            self.system_prompt_defaults
        )
        external_prompt_text = system_prompts.get(self.system_prompt_id)
        if not isinstance(external_prompt_text, str):
            external_prompt_text = self.system_prompt_defaults[
                self.system_prompt_id
            ]

        external_prompt_card = QGroupBox(
            "Anúncio - pesquisa para ChatGPT"
        )
        external_prompt_card.setToolTip(
            self.external_research_prompt_tooltip
        )
        external_prompt_layout = QVBoxLayout(external_prompt_card)
        external_prompt_layout.setContentsMargins(8, 6, 8, 6)
        external_prompt_layout.setSpacing(4)
        self.external_research_prompt_editor = QPlainTextEdit()
        self.external_research_prompt_editor.setPlainText(
            external_prompt_text
        )
        self.external_research_prompt_editor.setMinimumHeight(140)
        self.external_research_prompt_editor.setToolTip(
            self.external_research_prompt_tooltip
        )
        external_prompt_layout.addWidget(
            self.external_research_prompt_editor
        )

        external_prompt_note = QLabel(
            "O sistema acrescenta automaticamente: produto, referência, "
            "serventia, descrição, acompanha, acabamento, medidas/peso e "
            "formas de venda."
        )
        external_prompt_note.setWordWrap(True)
        external_prompt_note.setToolTip(
            self.external_research_prompt_tooltip
        )
        external_prompt_layout.addWidget(external_prompt_note)

        external_prompt_actions = QHBoxLayout()
        external_prompt_actions.setContentsMargins(0, 0, 0, 0)
        external_prompt_actions.setSpacing(4)
        external_prompt_actions.addStretch(1)
        self.external_research_prompt_save_button = _botao_icone(
            ico_salvar(),
            "Salvar prompt externo",
            self.external_research_prompt_tooltip,
            "💾",
        )
        self.external_research_prompt_save_button.setToolTip(
            self.external_research_prompt_tooltip
        )
        self.external_research_prompt_save_button.clicked.connect(
            self._save_external_research_prompt
        )
        external_prompt_actions.addWidget(
            self.external_research_prompt_save_button
        )
        self.external_research_prompt_restore_button = _botao_icone(
            icone("fa5s.undo"),
            "Restaurar padrão",
            "Restaura e salva o texto padrão definido no código.",
            "↶",
        )
        self.external_research_prompt_restore_button.setToolTip(
            "Restaura e salva o texto padrão definido no código."
        )
        self.external_research_prompt_restore_button.clicked.connect(
            self._restore_external_research_prompt
        )
        external_prompt_actions.addWidget(
            self.external_research_prompt_restore_button
        )
        external_prompt_layout.addLayout(external_prompt_actions)

        self.external_research_prompt_status = QLabel("")
        self.external_research_prompt_status.setWordWrap(True)
        external_prompt_layout.addWidget(
            self.external_research_prompt_status
        )
        left_cards_layout.addWidget(external_prompt_card)
        left_cards_layout.addStretch()
        left_scroll.setWidget(left_cards)
        left_layout.addWidget(left_scroll, 1)

        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.addWidget(QLabel("<b>Para copiar</b>"))
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_cards = QWidget()
        right_cards_layout = QVBoxLayout(right_cards)
        right_cards_layout.setContentsMargins(4, 4, 4, 4)
        right_cards_layout.setSpacing(6)
        for prompt_id, title, tooltip in self.reference_info:
            card = PromptCard(
                title,
                self._reference_text(prompt_id, referencias),
            )
            card.editor.setReadOnly(False)
            card.setToolTip(tooltip)
            card.editor.setToolTip(tooltip)
            save_button = _botao_icone(
                ico_salvar(),
                f"Salvar referência: {title}",
                "Salvar referência no AppData",
                "💾",
            )
            save_button.clicked.connect(
                lambda _checked=False, key=prompt_id, editor=card.editor, button=save_button:
                    self._save_reference_prompt(key, editor, button)
            )
            card.add_action_button(save_button)
            right_cards_layout.addWidget(card)
        right_cards_layout.addStretch()
        right_scroll.setWidget(right_cards)
        right_layout.addWidget(right_scroll, 1)

        root.addWidget(left_column, 1)
        root.addWidget(right_column, 1)

    def _notify_ai_context_changed(self) -> None:
        self.ai_context_changed.emit()

    def _save_external_research_prompt(self) -> None:
        try:
            self._salvar_prompt_sistema(
                self.system_prompt_id,
                self.external_research_prompt_editor.toPlainText(),
                self.system_prompt_defaults,
            )
        except (OSError, TypeError, ValueError) as exc:
            self.external_research_prompt_status.setText(
                "Não foi possível salvar o prompt."
            )
            QMessageBox.warning(
                self,
                "Erro ao salvar prompt",
                str(exc),
            )
            return
        self.external_research_prompt_status.setText(
            "Prompt salvo em AppData/IAs/prompts/sistema.json."
        )

    def _restore_external_research_prompt(self) -> None:
        texto_padrao = self.system_prompt_defaults[
            self.system_prompt_id
        ]
        self.external_research_prompt_editor.setPlainText(texto_padrao)
        self._save_external_research_prompt()

    def _save_reference_prompt(
        self,
        prompt_id: str,
        editor: QPlainTextEdit,
        save_button: QToolButton,
    ) -> None:
        try:
            self._salvar_referencia(
                prompt_id,
                editor.toPlainText(),
                self.reference_defaults,
            )
        except (OSError, TypeError, ValueError) as exc:
            QMessageBox.warning(self, "Erro ao salvar prompt", str(exc))
            return
        save_button.setIcon(ico_ok())
        save_button.setToolTip("Referência salva no AppData.")
        save_button.setAccessibleName("Referência salva")
        self._notify_ai_context_changed()

    def _reference_text(
        self,
        prompt_id: str,
        referencias: dict[str, object],
    ) -> str:
        texto = referencias.get(prompt_id)
        if isinstance(texto, str):
            return texto
        return self.reference_defaults[prompt_id]

    def ai_context_snapshot(self) -> dict[str, object]:
        """Entrega ao orientador o catálogo e as referências visíveis na aba."""
        referencias = self._carregar_referencias(self.reference_defaults)
        return {
            "tipo_contexto": "catalogo_de_prompts",
            "prompts_editaveis": carregar_catalogo(),
            "prompts_historicos": [
                {
                    "nome": title,
                    "uso": tooltip,
                    "texto": self._reference_text(prompt_id, referencias),
                }
                for prompt_id, title, tooltip in self.reference_info
            ],
            "observacao": (
                "O prompt de escopo ativo é aplicado pelo painel de IA. "
                "Prompts históricos só são usados se o usuário os copiar para "
                "uma solicitação."
            ),
        }


PromptsTab = CatalogPromptsTab
