"""Aba de identidade da loja e mídias próprias armazenadas no AppData."""

from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
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
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QComboBox,
)

from _APPDATA_ import appdata
from _APP_.Cadastro.Cadastro.catalogo import (
    carregar_catalogo_cadastro,
    novo_id_regra,
    salvar_catalogo_cadastro,
)
from _APPDATA_.gerenciador import MIDIA_CATEGORIAS


class ConfiguracoesTab(QWidget):
    """Permite cadastrar a identidade da loja e importar mídias para o AppData."""

    configuracoes_alteradas = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        appdata.inicializar()
        self.catalogo_cadastro = carregar_catalogo_cadastro()
        self._editores_opcoes: dict[str, dict[str, object]] = {}
        self._regra_selecionada_id = ""
        self._construir_ui()
        self._carregar_identidade()
        self._carregar_catalogo_ui()
        self._atualizar_lista_midias()

    def _construir_ui(self) -> None:
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(12, 12, 12, 12)
        raiz.setSpacing(10)

        self.abas_configuracao = QTabWidget()
        raiz.addWidget(self.abas_configuracao)
        pagina_loja = QWidget()
        loja_layout = QVBoxLayout(pagina_loja)
        loja_layout.setContentsMargins(0, 0, 0, 0)
        loja_layout.setSpacing(10)
        self.abas_configuracao.addTab(pagina_loja, "Loja")

        identidade = QGroupBox("Identidade da loja")
        identidade_layout = QVBoxLayout(identidade)
        formulario = QFormLayout()
        self.perfil_social = QLineEdit()
        self.perfil_social.setPlaceholderText("@sualoja")
        self.perfil_social.setToolTip(
            "Texto de marca impresso nas imagens finais. Pode ficar vazio."
        )
        self.url_loja = QLineEdit()
        self.url_loja.setPlaceholderText("sualoja.com.br")
        self.url_loja.setToolTip(
            "Link ou domínio exibido nos vídeos convertidos. Pode ficar vazio."
        )
        formulario.addRow("Perfil / @ nas imagens", self.perfil_social)
        formulario.addRow("Link da loja nos vídeos", self.url_loja)
        identidade_layout.addLayout(formulario)

        identidade_acoes = QHBoxLayout()
        self.salvar_identidade = QPushButton("Salvar identidade")
        self.salvar_identidade.clicked.connect(self._salvar_identidade)
        self.identidade_status = QLabel("")
        identidade_acoes.addWidget(self.salvar_identidade)
        identidade_acoes.addWidget(self.identidade_status, 1)
        identidade_layout.addLayout(identidade_acoes)
        loja_layout.addWidget(identidade)

        midias = QGroupBox("Mídias da loja")
        midias_layout = QVBoxLayout(midias)
        midias_layout.addWidget(
            QLabel(
                "Os arquivos selecionados são copiados para o AppData do usuário. "
                "O original permanece no local escolhido."
            )
        )

        self.categoria_midia = QComboBox()
        for categoria, dados in MIDIA_CATEGORIAS.items():
            self.categoria_midia.addItem(dados["rotulo"], categoria)
        self.categoria_midia.currentIndexChanged.connect(
            self._atualizar_lista_midias
        )
        midias_layout.addWidget(self.categoria_midia)

        fundo_medida_layout = QHBoxLayout()
        fundo_medida_layout.addWidget(
            QLabel("Fundo ativo para imagens de medidas:")
        )
        self.fundo_medida_padrao = QComboBox()
        self.fundo_medida_padrao.setToolTip(
            "Este fundo é aplicado às imagens da pasta D durante a Produção."
        )
        self.fundo_medida_padrao.currentIndexChanged.connect(
            self._salvar_fundo_medida_padrao
        )
        fundo_medida_layout.addWidget(self.fundo_medida_padrao, 1)
        midias_layout.addLayout(fundo_medida_layout)

        self.lista_midias = QListWidget()
        self.lista_midias.setMinimumHeight(180)
        midias_layout.addWidget(self.lista_midias, 1)

        acoes_midias = QHBoxLayout()
        self.adicionar_midia = QPushButton("Adicionar arquivo")
        self.remover_midia = QPushButton("Remover cópia do AppData")
        self.adicionar_midia.clicked.connect(self._adicionar_midia)
        self.remover_midia.clicked.connect(self._remover_midia)
        acoes_midias.addWidget(self.adicionar_midia)
        acoes_midias.addWidget(self.remover_midia)
        acoes_midias.addStretch()
        midias_layout.addLayout(acoes_midias)

        self.midias_status = QLabel("")
        self.midias_status.setWordWrap(True)
        midias_layout.addWidget(self.midias_status)
        loja_layout.addWidget(midias, 1)
        loja_layout.addStretch()

        pagina_cadastro = QWidget()
        cadastro_layout = QVBoxLayout(pagina_cadastro)
        cadastro_layout.setContentsMargins(0, 0, 0, 0)
        cadastro_layout.addWidget(
            QLabel(
                "As opções ficam no AppData e aparecem no Cadastro. "
                "As descrições das regras são enviadas ao prompt quando "
                "a regra é selecionada para um produto."
            )
        )
        self.abas_catalogo = QTabWidget()
        cadastro_layout.addWidget(self.abas_catalogo, 1)
        self.abas_configuracao.addTab(pagina_cadastro, "Opções do Cadastro")

        self.abas_catalogo.addTab(
            self._construir_editor_opcoes(
                "acompanha",
                "Opções de Acompanha",
                "Cadastre os itens que poderão ser selecionados em Acompanha.",
                "Nome da opção",
            ),
            "Acompanha",
        )
        self.abas_catalogo.addTab(
            self._construir_editor_opcoes(
                "acabamentos",
                "Acabamentos",
                "Cadastre os acabamentos disponíveis no Cadastro.",
                "Nome do acabamento",
            ),
            "Acabamento",
        )
        self.abas_catalogo.addTab(
            self._construir_editor_regras(),
            "Regras do anúncio",
        )

    def _construir_editor_opcoes(
        self,
        chave: str,
        titulo: str,
        orientacao: str,
        placeholder: str,
    ) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.addWidget(QLabel(orientacao))
        lista = QListWidget()
        layout.addWidget(lista, 1)
        entrada = QLineEdit()
        entrada.setPlaceholderText(placeholder)
        layout.addWidget(entrada)
        acoes = QHBoxLayout()
        salvar = QPushButton("Adicionar / atualizar")
        remover = QPushButton("Remover opção")
        status = QLabel()
        status.setWordWrap(True)
        acoes.addWidget(salvar)
        acoes.addWidget(remover)
        acoes.addWidget(status, 1)
        layout.addLayout(acoes)
        lista.currentRowChanged.connect(
            lambda row, key=chave: self._selecionar_opcao(key, row)
        )
        salvar.clicked.connect(
            lambda checked=False, key=chave: self._salvar_opcao(key)
        )
        remover.clicked.connect(
            lambda checked=False, key=chave: self._remover_opcao(key)
        )
        self._editores_opcoes[chave] = {
            "titulo": titulo,
            "lista": lista,
            "entrada": entrada,
            "status": status,
        }
        return pagina

    def _construir_editor_regras(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.addWidget(
            QLabel(
                "O título aparece como opção no Cadastro. A descrição é "
                "livre e acompanha a regra selecionada até o prompt."
            )
        )
        self.lista_regras = QListWidget()
        layout.addWidget(self.lista_regras, 1)
        self.titulo_regra = QLineEdit()
        self.titulo_regra.setPlaceholderText("Título da regra")
        layout.addWidget(self.titulo_regra)
        self.descricao_regra = QPlainTextEdit()
        self.descricao_regra.setPlaceholderText(
            "Descrição livre enviada ao prompt quando esta regra for marcada"
        )
        self.descricao_regra.setMinimumHeight(110)
        layout.addWidget(self.descricao_regra)
        acoes = QHBoxLayout()
        self.salvar_regra = QPushButton("Adicionar regra")
        self.remover_regra = QPushButton("Remover regra")
        self.regras_status = QLabel()
        self.regras_status.setWordWrap(True)
        acoes.addWidget(self.salvar_regra)
        acoes.addWidget(self.remover_regra)
        acoes.addWidget(self.regras_status, 1)
        layout.addLayout(acoes)
        self.lista_regras.currentRowChanged.connect(
            self._selecionar_regra
        )
        self.salvar_regra.clicked.connect(self._salvar_regra)
        self.remover_regra.clicked.connect(self._remover_regra)
        return pagina

    def _carregar_catalogo_ui(self) -> None:
        for chave, editor in self._editores_opcoes.items():
            lista = editor["lista"]
            lista.clear()
            for valor in self.catalogo_cadastro.get(chave, []):
                lista.addItem(str(valor))

        self.lista_regras.clear()
        for regra in self.catalogo_cadastro.get("regras_anuncio", []):
            item = QListWidgetItem(regra["titulo"])
            item.setData(Qt.ItemDataRole.UserRole, regra["id"])
            self.lista_regras.addItem(item)
        self._limpar_editor_regra()

    def _selecionar_opcao(self, chave: str, indice: int) -> None:
        editor = self._editores_opcoes[chave]
        lista = editor["lista"]
        entrada = editor["entrada"]
        entrada.setText(lista.item(indice).text() if indice >= 0 else "")

    def _salvar_opcao(self, chave: str) -> None:
        editor = self._editores_opcoes[chave]
        entrada = editor["entrada"]
        lista = editor["lista"]
        valor = entrada.text().strip()
        if not valor:
            editor["status"].setText("Digite o nome da opção.")
            return
        valores = list(self.catalogo_cadastro.get(chave, []))
        indice = lista.currentRow()
        for outro_indice, existente in enumerate(valores):
            if (
                outro_indice != indice
                and existente.casefold() == valor.casefold()
            ):
                editor["status"].setText("Essa opção já existe.")
                return
        if 0 <= indice < len(valores):
            valores[indice] = valor
        else:
            valores.append(valor)
        self.catalogo_cadastro[chave] = valores
        self._persistir_catalogo(
            f"Opção salva em {editor['titulo']}.",
            editor["status"],
        )

    def _remover_opcao(self, chave: str) -> None:
        editor = self._editores_opcoes[chave]
        indice = editor["lista"].currentRow()
        valores = list(self.catalogo_cadastro.get(chave, []))
        if indice < 0 or indice >= len(valores):
            editor["status"].setText("Selecione uma opção para remover.")
            return
        valores.pop(indice)
        self.catalogo_cadastro[chave] = valores
        self._persistir_catalogo(
            f"Opção removida de {editor['titulo']}.",
            editor["status"],
        )

    def _selecionar_regra(self, indice: int) -> None:
        item = self.lista_regras.item(indice) if indice >= 0 else None
        regra_id = (
            str(item.data(Qt.ItemDataRole.UserRole) or "")
            if item is not None
            else ""
        )
        regra = next(
            (
                item_regra
                for item_regra in self.catalogo_cadastro["regras_anuncio"]
                if item_regra["id"] == regra_id
            ),
            None,
        )
        self._regra_selecionada_id = regra_id
        self.titulo_regra.setText(regra["titulo"] if regra else "")
        self.descricao_regra.setPlainText(
            regra["descricao"] if regra else ""
        )
        self.salvar_regra.setText(
            "Salvar alterações" if regra else "Adicionar regra"
        )

    def _limpar_editor_regra(self) -> None:
        self._regra_selecionada_id = ""
        self.titulo_regra.clear()
        self.descricao_regra.clear()
        self.salvar_regra.setText("Adicionar regra")

    def _salvar_regra(self) -> None:
        titulo = self.titulo_regra.text().strip()
        descricao = self.descricao_regra.toPlainText().strip()
        if not titulo:
            self.regras_status.setText("Digite o título da regra.")
            return

        regras = list(self.catalogo_cadastro.get("regras_anuncio", []))
        for regra in regras:
            if (
                regra["id"] != self._regra_selecionada_id
                and regra["titulo"].casefold() == titulo.casefold()
            ):
                self.regras_status.setText("Esse título já existe.")
                return

        existente = next(
            (
                regra
                for regra in regras
                if regra["id"] == self._regra_selecionada_id
            ),
            None,
        )
        if existente is None:
            regras.append(
                {
                    "id": novo_id_regra(),
                    "titulo": titulo,
                    "descricao": descricao,
                }
            )
        else:
            existente["titulo"] = titulo
            existente["descricao"] = descricao
        self.catalogo_cadastro["regras_anuncio"] = regras
        self._persistir_catalogo("Regra salva no AppData.")

    def _remover_regra(self) -> None:
        if not self._regra_selecionada_id:
            self.regras_status.setText("Selecione uma regra para remover.")
            return
        self.catalogo_cadastro["regras_anuncio"] = [
            regra
            for regra in self.catalogo_cadastro["regras_anuncio"]
            if regra["id"] != self._regra_selecionada_id
        ]
        self._persistir_catalogo("Regra removida do AppData.")

    def _persistir_catalogo(self, mensagem: str, status=None) -> None:
        if not salvar_catalogo_cadastro(self.catalogo_cadastro):
            QMessageBox.critical(
                self,
                "Falha ao salvar",
                "Não foi possível salvar as opções do Cadastro no AppData. "
                "Confira os logs do aplicativo.",
            )
            return
        self.catalogo_cadastro = carregar_catalogo_cadastro()
        self._carregar_catalogo_ui()
        (status or self.regras_status).setText(mensagem)
        self.configuracoes_alteradas.emit()

    def _carregar_identidade(self) -> None:
        configuracao = appdata.ler_config()
        marca = configuracao.get("marca", {})
        if not isinstance(marca, dict):
            marca = {}
        self.perfil_social.setText(str(marca.get("perfil_social") or ""))
        self.url_loja.setText(str(marca.get("url_loja") or ""))

    def _salvar_identidade(self) -> None:
        configuracao = appdata.ler_config()
        configuracao["marca"] = {
            "perfil_social": self.perfil_social.text().strip(),
            "url_loja": self.url_loja.text().strip(),
        }
        if not appdata.salvar_config(configuracao):
            QMessageBox.critical(
                self,
                "Falha ao salvar",
                "Não foi possível salvar a identidade no AppData. "
                "Confira os logs do aplicativo.",
            )
            return
        self.identidade_status.setText("Identidade salva no AppData.")
        self.configuracoes_alteradas.emit()

    def _categoria_atual(self) -> str:
        return str(self.categoria_midia.currentData() or "")

    def _atualizar_lista_midias(self, *_args) -> None:
        categoria = self._categoria_atual()
        self.lista_midias.clear()
        self._atualizar_fundo_medida_padrao()
        if not categoria:
            self.remover_midia.setEnabled(False)
            return

        arquivos = appdata.listar_midias(categoria)
        for nome in arquivos:
            item = QListWidgetItem(nome)
            item.setData(Qt.ItemDataRole.UserRole, nome)
            self.lista_midias.addItem(item)

        dados = MIDIA_CATEGORIAS[categoria]
        if arquivos:
            self.midias_status.setText(
                f"{len(arquivos)} arquivo(s) em "
                f"{appdata.pasta_midia_categoria(categoria)}"
            )
        else:
            self.midias_status.setText(
                f"Nenhum arquivo cadastrado para {dados['rotulo'].lower()}."
            )
        self.adicionar_midia.setText(
            "Substituir arquivo"
            if not dados["multiplo"] and arquivos
            else "Adicionar arquivo"
        )
        self.remover_midia.setEnabled(bool(arquivos))

    def _atualizar_fundo_medida_padrao(self) -> None:
        arquivos = appdata.listar_midias("fundo_medida")
        configuracao = appdata.ler_config()
        producao = configuracao.get("producao", {})
        if not isinstance(producao, dict):
            producao = {}
        salvo = producao.get("fundo_medida")
        escolhido = salvo if salvo in arquivos else (arquivos[0] if arquivos else None)

        self.fundo_medida_padrao.blockSignals(True)
        self.fundo_medida_padrao.clear()
        if arquivos:
            for nome in arquivos:
                self.fundo_medida_padrao.addItem(nome, nome)
            self.fundo_medida_padrao.setCurrentIndex(
                self.fundo_medida_padrao.findData(escolhido)
            )
            self.fundo_medida_padrao.setEnabled(True)
        else:
            self.fundo_medida_padrao.addItem("Nenhum fundo cadastrado", None)
            self.fundo_medida_padrao.setEnabled(False)
        self.fundo_medida_padrao.blockSignals(False)

        if salvo != escolhido and (salvo is not None or escolhido is not None):
            self._gravar_fundo_medida_padrao(escolhido, emitir=False)

    def _salvar_fundo_medida_padrao(self, *_args) -> None:
        escolhido = self.fundo_medida_padrao.currentData()
        if not escolhido:
            return
        self._gravar_fundo_medida_padrao(str(escolhido), emitir=True)

    def _gravar_fundo_medida_padrao(
        self,
        escolhido: str | None,
        *,
        emitir: bool,
    ) -> None:
        configuracao = appdata.ler_config()
        producao = configuracao.get("producao", {})
        if not isinstance(producao, dict):
            producao = {}
        if escolhido:
            producao["fundo_medida"] = escolhido
        else:
            producao.pop("fundo_medida", None)
        configuracao["producao"] = producao
        if not appdata.salvar_config(configuracao):
            self.midias_status.setText(
                "Não foi possível salvar o fundo de medidas no AppData."
            )
            return
        if emitir:
            self.midias_status.setText(
                f"Fundo ativo para imagens de medidas: {escolhido}"
            )
            self.configuracoes_alteradas.emit()

    @staticmethod
    def _nome_disponivel(pasta: Path, nome: str) -> Path:
        destino = pasta / nome
        if not destino.exists():
            return destino
        origem = Path(nome)
        numero = 2
        while True:
            destino = pasta / f"{origem.stem}_{numero}{origem.suffix}"
            if not destino.exists():
                return destino
            numero += 1

    def _adicionar_midia(self) -> None:
        categoria = self._categoria_atual()
        if not categoria:
            return

        dados = MIDIA_CATEGORIAS[categoria]
        extensoes = dados["extensoes"]
        padrao = " ".join(f"*{ext}" for ext in extensoes)
        filtro = f"{dados['rotulo']} ({padrao})"
        caminho, _ = QFileDialog.getOpenFileName(
            self,
            f"Selecionar {dados['rotulo'].lower()}",
            "",
            f"{filtro};;Todos os arquivos (*)",
        )
        if not caminho:
            return

        origem = Path(caminho)
        if origem.suffix.casefold() not in extensoes:
            QMessageBox.warning(
                self,
                "Formato não suportado",
                f"Selecione um arquivo compatível com {dados['rotulo'].lower()}.",
            )
            return

        pasta = Path(appdata.pasta_midia_categoria(categoria))
        pasta.mkdir(parents=True, exist_ok=True)
        existentes = [
            pasta / nome for nome in appdata.listar_midias(categoria)
        ]
        origem_resolvida = origem.resolve()
        if any(item.resolve() == origem_resolvida for item in existentes):
            self.midias_status.setText("Esse arquivo já está cadastrado.")
            return

        if not dados["multiplo"] and existentes:
            resposta = QMessageBox.question(
                self,
                "Substituir arquivo",
                f"Substituir o arquivo cadastrado em {dados['rotulo'].lower()}? "
                "O arquivo original escolhido não será apagado.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if resposta != QMessageBox.StandardButton.Yes:
                return

        destino = self._nome_disponivel(pasta, origem.name)
        try:
            shutil.copy2(origem, destino)
            if not dados["multiplo"]:
                for anterior in existentes:
                    anterior.unlink(missing_ok=True)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Falha ao copiar mídia",
                f"Não foi possível salvar o arquivo no AppData:\n{exc}",
            )
            return

        self._atualizar_lista_midias()
        self.midias_status.setText(f"Arquivo copiado para o AppData: {destino}")
        self.configuracoes_alteradas.emit()

    def _remover_midia(self) -> None:
        item = self.lista_midias.currentItem()
        categoria = self._categoria_atual()
        if item is None or not categoria:
            return

        nome = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if not nome or Path(nome).name != nome:
            return
        caminho = Path(appdata.pasta_midia_categoria(categoria)) / nome
        resposta = QMessageBox.question(
            self,
            "Remover mídia",
            f"Apagar somente a cópia do AppData?\n\n{nome}\n\n"
            "O arquivo original escolhido antes não será apagado.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return
        try:
            caminho.unlink()
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Falha ao remover mídia",
                f"Não foi possível remover o arquivo do AppData:\n{exc}",
            )
            return

        self._atualizar_lista_midias()
        self.configuracoes_alteradas.emit()
