"""Janela principal real do aplicativo com a infraestrutura do template."""

from __future__ import annotations

from _CONFIGURA_ import (
    ALTURA_MIN,
    ALTURA_PADRAO,
    ESTILO_ESCURO_GLOBAL,
    IMAGEM_ICO,
    LARGURA_MIN,
    LARGURA_PADRAO,
    TITULO_APP,
    VERSAO_APP,
)
from _LOGS_ import log
from _APPDATA_ import appdata
from _THREADS_ import thread_manager

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QSplitter,
    QStackedWidget,
    QWidget,
)

from _IAS_.Painel_IA_PySide6 import AIPanel
from _APP_ import App_Janela_PySide6 as _janela_existente
from _APP_.App_Janela_PySide6 import MainWindow as _MainWindowExistente
from _APP_.area_navigation import AreaNavigation
from _APP_.Cadastro import CadastroWorkspace
from _APP_.Cadastro.Cadastro import CadastroTab
from _APP_.Cadastro.Criacao import CreationTab
from _APP_.Cadastro.Medidas_Avulsas import MidiasAvulsasTab
from _APP_.Configuracao import (
    ConfiguracaoWorkspace,
    ConfiguracoesTab,
    DatabaseMigrationPage,
)
from _APP_.Configuracao.Prompts import CatalogPromptsTab
from _APP_.Marketplace import MarketplaceWorkspace
from _APP_.Marketplace.Anunciar import AnunciarActionPage
from _APP_.Marketplace.Anuncios import AnuncioTab, AnunciarPage
from _APP_.Marketplace.Anuncios.Data_Anuncio_PySide6 import (
    listar_produtos_para_anunciar_somente_leitura,
)
from _APP_.Marketplace.Registros import RecordsTab
from _APP_.Marketplace.Sociais import SociaisTab
from _APP_.Vendas.Vendas import VendasWorkspace
from _APP_.product_lifecycle import contar_produtos_pendentes


class MainWindow(_MainWindowExistente):
    """Janela com navegação por áreas e ciclo de vida centralizado."""

    def __init__(self, parent=None):
        # O modulo historico declara PromptsTab varias vezes. A classe
        # documentada/editavel precisa ser escolhida antes do construtor base.
        _janela_existente.PromptsTab = CatalogPromptsTab
        _janela_existente.CadastroTab = CadastroTab
        _janela_existente.ModularProductionTab = CreationTab
        _janela_existente.RecordsTab = RecordsTab
        super().__init__()

        self.creation_tab = self.production_tab
        self.results_tab = self.creation_tab.results_page
        self.media_tab = MidiasAvulsasTab()
        self.anuncio_tab = AnuncioTab()
        self.anunciar_page = self.anuncio_tab.anunciar_page
        anunciar_index = self.anuncio_tab.inner_pages.indexOf(
            self.anunciar_page
        )
        if anunciar_index >= 0:
            self.anuncio_tab.inner_pages.removeTab(anunciar_index)
        self.anuncio_tab.inner_pages.tabBar().hide()

        self.vendas_tab = VendasWorkspace()
        self.socials_tab = SociaisTab()
        self.records_tab = self.records_tab
        self.prompts_tab = self.prompts_tab

        setup = self.anuncio_tab.marketplace_setup
        self.label_section = setup.label_section
        setup.layout().removeWidget(self.label_section)
        self.label_section.setParent(None)
        self.anunciar_action_page = AnunciarActionPage(
            label_section=self.label_section,
            load_products=listar_produtos_para_anunciar_somente_leitura,
            current_product=self._current_label_product,
            select_product=setup.set_current_product,
        )

        self.cadastro_pages = CadastroWorkspace(
            cadastro=self.cadastro_tab,
            criacao=self.creation_tab,
            resultados=self.results_tab,
            montar_anuncio=self.anuncio_tab,
            midias_avulsas=self.media_tab,
        )

        self.marketplace_pages = MarketplaceWorkspace(
            anuncios=self.anunciar_page,
            anunciar=self.anunciar_action_page,
            sociais=self.socials_tab,
            registros=self.records_tab,
        )

        self.settings_tab = ConfiguracoesTab()
        self.migration_page = DatabaseMigrationPage()
        self.configuracao_pages = ConfiguracaoWorkspace(
            configuracoes=self.settings_tab,
            prompts=self.prompts_tab,
            banco_dados=self.migration_page,
        )

        self._area_tabs = {
            "cadastro": self.cadastro_pages,
            "marketplace": self.marketplace_pages,
            "vendas": self.vendas_tab,
            "configuracao": self.configuracao_pages,
        }
        self._active_area = "cadastro"
        self.area_stack = QStackedWidget()
        for area_id in ("cadastro", "marketplace", "vendas", "configuracao"):
            self.area_stack.addWidget(self._area_tabs[area_id])

        # Retira as telas da barra histórica superior; os widgets são
        # reaproveitados nas quatro áreas e não recriados.
        while self.tabs.count():
            self.tabs.removeTab(0)
        self.tabs.setParent(None)

        self.creation_tab.results_requested.connect(
            self._mostrar_resultados
        )
        self.settings_tab.configuracoes_alteradas.connect(
            self.media_tab.refresh_resources
        )
        if parent is not None:
            self.setParent(parent)

        self.ai_panel = AIPanel()
        self.navigation = AreaNavigation()
        self.navigation.area_selected.connect(self._set_active_area)
        self.marketplace_pages.currentChanged.connect(
            self._on_marketplace_page_changed
        )
        for area_id in self._area_tabs:
            tabs = self._area_tab_control(area_id)
            tabs.currentChanged.connect(
                lambda index, current_area=area_id:
                self._on_area_page_changed(current_area, index)
            )
        self.creation_tab.ai_context_changed.connect(
            self._on_creation_ai_context_changed
        )
        self.anuncio_tab.ai_context_changed.connect(
            self._on_anuncio_ai_context_changed
        )
        self.socials_tab.ai_context_changed.connect(
            self._on_social_ai_context_changed
        )
        self.prompts_tab.ai_context_changed.connect(
            self._on_prompts_ai_context_changed
        )
        self.anuncio_tab.refresh_requested.connect(self.creation_tab.refresh)
        self.anuncio_tab.product_completed.connect(
            self._on_product_completed
        )
        self.anuncio_tab.prompt_requested.connect(
            self._on_anuncio_prompt_requested
        )
        self.socials_tab.prompt_requested.connect(
            self._on_social_prompt_requested
        )
        self.ai_panel.anuncio_response_received.connect(
            self.anuncio_tab.handle_ai_response
        )
        self.ai_panel.anuncio_response_failed.connect(
            self.anuncio_tab.ai_request_failed
        )
        self.ai_panel.social_response_received.connect(
            self.socials_tab.handle_ai_response
        )
        self.ai_panel.social_response_failed.connect(
            self.socials_tab.ai_request_failed
        )
        self.settings_tab.configuracoes_alteradas.connect(
            self.creation_tab.refresh_visual_resources_from_settings
        )
        self.settings_tab.configuracoes_alteradas.connect(
            self.cadastro_tab.refresh_product_options
        )
        self.cadastro_tab.set_ai_context_callback(
            self.ai_panel.set_contexto_produto
        )
        self.ai_panel.conectar_ferramentas_cadastro(self.cadastro_tab)
        self.anuncio_tab.set_current_row(self.creation_tab.current_row)
        self.migration_page.migration_completed.connect(
            self._refresh_lifecycle_views
        )
        self.creation_tab.ai_context_changed.connect(
            lambda _snapshot: self._refresh_pending_navigation()
        )

        workspace = QSplitter(Qt.Orientation.Horizontal)
        workspace.setChildrenCollapsible(False)
        workspace.addWidget(self.navigation)
        workspace.addWidget(self.area_stack)
        workspace.addWidget(self.ai_panel)
        workspace.setStretchFactor(0, 0)
        workspace.setStretchFactor(1, 1)
        workspace.setStretchFactor(2, 0)
        workspace.setSizes([128, 850, 300])
        self.setCentralWidget(workspace)
        self._configurar_tooltips_abas()
        self._refresh_pending_navigation()

        self._configurar_janela()
        self._aplicar_estilo()
        self._restaurar_sessao()
        self._conectar_shutdown()
        self._atualizar_contexto_ia_por_aba()
        log.ok("MainWindow", "__init__", "janela principal pronta")

    def _refresh_media_tab(self, *_args: object) -> None:
        if (
            self._active_area == "cadastro"
            and self._active_widget() is self.media_tab
        ):
            self.media_tab.refresh_destinations()
            self.media_tab.refresh_resources()

    def _on_area_page_changed(self, area_id: str, _index: int) -> None:
        if area_id == self._active_area:
            self._atualizar_contexto_ia_por_aba()
            if area_id == "vendas":
                self._refresh_sales_views()
        self._refresh_media_tab()

    def _set_active_area(self, area_id: str) -> None:
        if area_id not in self._area_tabs:
            return
        self._active_area = area_id
        self.area_stack.setCurrentWidget(self._area_tabs[area_id])
        self.navigation.set_active_area(area_id)
        self._atualizar_contexto_ia_por_aba()
        if area_id == "vendas":
            self._refresh_sales_views()
        self._refresh_media_tab()

    def _area_tab_control(self, area_id: str):
        """Retorna o QTabWidget interno de uma área ou a própria área."""
        area = self._area_tabs[area_id]
        return getattr(area, "pages", area)

    def _set_active_widget(self, widget: QWidget) -> None:
        for area_id, area in self._area_tabs.items():
            tabs = self._area_tab_control(area_id)
            if tabs.indexOf(widget) >= 0:
                self._active_area = area_id
                self.area_stack.setCurrentWidget(area)
                tabs.setCurrentWidget(widget)
                self.navigation.set_active_area(area_id)
                self._atualizar_contexto_ia_por_aba()
                self._refresh_media_tab()
                return

    def _active_widget(self) -> QWidget | None:
        return self._area_tab_control(self._active_area).currentWidget()

    def _configurar_tooltips_abas(self) -> None:
        descricoes = {
            "cadastro": (
                (self.cadastro_tab, "Cadastrar produto e organizar mídias."),
                (self.creation_tab, "Processar as mídias do produto pendente."),
                (self.results_tab, "Revisar as mídias processadas."),
                (self.anuncio_tab, "Montar o anúncio do produto pendente."),
                (self.media_tab, "Processar mídias sem alterar o cadastro."),
            ),
            "marketplace": (
                (self.anunciar_page, "Revisar anúncios salvos por produto."),
                (self.socials_tab, "Preparar publicações sociais manualmente."),
                (self.records_tab, "Consultar IDs e unidades de estoque."),
            ),
            "configuracao": (
                (self.settings_tab, "Configurar loja e mídias reutilizáveis."),
                (self.prompts_tab, "Editar os prompts do aplicativo."),
                (self.migration_page, "Atualizar o banco após backup verificado."),
            ),
        }
        for area_id, widgets in descricoes.items():
            tabs = self._area_tabs[area_id]
            for widget, tooltip in widgets:
                index = tabs.indexOf(widget)
                if index >= 0:
                    tabs.setTabToolTip(index, tooltip)
        self.vendas_tab.pages.setTabToolTip(
            0,
            "Registrar uma venda e atualizar o estoque disponível.",
        )
        self.vendas_tab.pages.setTabToolTip(
            1,
            "Consultar as vendas registradas e os dados do comprador.",
        )
        marketplace_action_index = self.marketplace_pages.indexOf(
            self.label_section.parentWidget()
        )
        if marketplace_action_index >= 0:
            self.marketplace_pages.setTabToolTip(
                marketplace_action_index,
                "Preparar e imprimir etiquetas; publicação continua manual.",
            )

    def _refresh_label_products(self, *_args: object) -> None:
        self.anunciar_action_page.refresh_products()

    def _refresh_sales_views(self) -> None:
        self.vendas_tab.refresh_marketplaces()
        self.vendas_tab._load_products()
        self.vendas_tab._load_history()

    def _current_label_product(self) -> str:
        current_row = self.creation_tab.current_row
        return (
            str(current_row[0] or "").strip()
            if current_row
            else ""
        )

    def _refresh_pending_navigation(self) -> None:
        pendentes = contar_produtos_pendentes()
        for widget in (self.creation_tab, self.results_tab, self.anuncio_tab):
            index = self.cadastro_pages.indexOf(widget)
            if index >= 0:
                self.cadastro_pages.setTabVisible(index, pendentes > 0)
        if (
            not pendentes
            and self._active_area == "cadastro"
            and self._active_widget()
            in (self.creation_tab, self.results_tab, self.anuncio_tab)
        ):
            self.cadastro_pages.setCurrentWidget(self.cadastro_tab)

    def _refresh_lifecycle_views(self) -> None:
        self._refresh_pending_navigation()
        self.anuncio_tab._set_product_actions_enabled(
            self.anuncio_tab._current_product is not None
        )
        self.anunciar_page.refresh_products()
        self.socials_tab.refresh_products()
        self._refresh_label_products()
        self._refresh_sales_views()

    def _on_marketplace_page_changed(self, _index: int) -> None:
        widget = self.marketplace_pages.currentWidget()
        if widget is self.anunciar_page:
            self.anunciar_page.refresh_products()
        elif widget is self.socials_tab:
            self.socials_tab.refresh_products()
        elif widget is self.label_section.parentWidget():
            self._refresh_label_products()

    def _mostrar_resultados(self) -> None:
        self._set_active_widget(self.results_tab)

    def show_prompts(self) -> None:
        """Abre Prompts dentro da área Configuração."""
        self._set_active_widget(self.prompts_tab)

    def _atualizar_contexto_ia_por_aba(self, *_args: object) -> None:
        """Troca o escopo do painel conforme a área e subaba ativas."""
        aba = self._active_widget()
        if aba is self.cadastro_tab:
            publicar = getattr(self.cadastro_tab, "_publish_ai_context", None)
            if publicar is not None:
                publicar()
            else:
                self.ai_panel.set_contexto_produto({}, escopo="Cadastro")
            return

        if aba is self.creation_tab or aba is self.results_tab:
            snapshot = dict(self.creation_tab.ai_context_snapshot())
            snapshot["area_ativa"] = (
                "Resultados" if aba is self.results_tab else "Criação"
            )
            self.ai_panel.set_contexto_produto(snapshot, escopo="Producao")
            return

        if aba is self.anuncio_tab:
            self.creation_tab.refresh()
            return

        if aba is self.socials_tab:
            self.socials_tab.refresh_products()
            self.ai_panel.set_contexto_produto(
                self.socials_tab.ai_context_snapshot(),
                escopo="Sociais",
            )
            return

        if (
            aba is not None
            and self.vendas_tab.pages.indexOf(aba) >= 0
        ):
            self.ai_panel.set_contexto_produto({}, escopo="Vendas")
            return

        if aba is self.records_tab:
            self.ai_panel.set_contexto_produto({}, escopo="Registros")
            return

        if aba is self.prompts_tab:
            self.ai_panel.set_contexto_produto(
                self.prompts_tab.ai_context_snapshot(),
                escopo="Prompts",
            )
            return

        if aba is self.settings_tab or aba is self.migration_page:
            self.ai_panel.set_contexto_produto({}, escopo="Configuracoes")

    def _configurar_janela(self) -> None:
        self.setWindowTitle(f"{TITULO_APP} {VERSAO_APP}")
        self.setMinimumSize(LARGURA_MIN, ALTURA_MIN)
        self.resize(LARGURA_PADRAO, ALTURA_PADRAO)
        if IMAGEM_ICO:
            self.setWindowIcon(QIcon(IMAGEM_ICO))

    def _aplicar_estilo(self) -> None:
        self.setStyleSheet(ESTILO_ESCURO_GLOBAL)

    def _restaurar_sessao(self) -> None:
        sessao = appdata.ler_sessao()
        try:
            geometria = sessao.get("geometria")
            estado = sessao.get("estado")
            if geometria:
                self.restoreGeometry(QByteArray.fromBase64(geometria.encode()))
            if estado:
                self.restoreState(QByteArray.fromBase64(estado.encode()))
            log.ok("MainWindow", "_restaurar_sessao", "sessão restaurada")
        except Exception as exc:
            log.aviso(
                "MainWindow",
                "_restaurar_sessao",
                f"falha ao restaurar sessão: {exc}",
            )

    def _salvar_sessao(self) -> None:
        try:
            sessao = {
                "geometria": self.saveGeometry().toBase64().data().decode(),
                "estado": self.saveState().toBase64().data().decode(),
            }
            appdata.salvar_sessao(sessao)
        except Exception as exc:
            log.erro(
                "MainWindow",
                "_salvar_sessao",
                f"falha ao salvar sessão: {exc}",
            )

    def _conectar_shutdown(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._ao_encerrar)

    def _on_creation_ai_context_changed(self, snapshot: dict) -> None:
        self.anuncio_tab.set_current_row(self.creation_tab.current_row)
        self._refresh_pending_navigation()
        if self._active_widget() in (
            self.creation_tab,
            self.results_tab,
        ):
            contexto = dict(snapshot)
            contexto["area_ativa"] = (
                "Resultados"
                if self._active_widget() is self.results_tab
                else "Criação"
            )
            self.ai_panel.set_contexto_produto(contexto, escopo="Producao")

    def _on_anuncio_prompt_requested(self, prompt: str) -> None:
        if not self.ai_panel.send_anuncio_prompt(prompt):
            self.anuncio_tab.ai_request_rejected(
                self.ai_panel.status.text()
                or "A IA não aceitou a solicitação de Anúncio."
            )

    def _on_social_prompt_requested(
        self,
        platform_id: str,
        prompt: str,
    ) -> None:
        if not self.ai_panel.send_social_prompt(platform_id, prompt):
            self.socials_tab.ai_request_rejected(
                platform_id,
                self.ai_panel.status.text()
                or "A IA não aceitou a solicitação de Sociais.",
            )

    def _on_anuncio_ai_context_changed(self, snapshot: dict) -> None:
        if self._active_widget() is self.anuncio_tab:
            self.ai_panel.set_contexto_produto(
                snapshot,
                escopo="Anuncio",
            )

    def _on_social_ai_context_changed(self, snapshot: dict) -> None:
        if self._active_widget() is self.socials_tab:
            self.ai_panel.set_contexto_produto(
                snapshot,
                escopo="Sociais",
            )

    def _on_prompts_ai_context_changed(self) -> None:
        if self._active_widget() is self.prompts_tab:
            self.ai_panel.set_contexto_produto(
                self.prompts_tab.ai_context_snapshot(),
                escopo="Prompts",
            )

    def _on_product_completed(self, product: str) -> None:
        self.creation_tab.refresh()
        self.anunciar_page.refresh_products()
        self.socials_tab.refresh_products()
        self._refresh_label_products()
        self._refresh_pending_navigation()
        self._set_active_widget(self.anunciar_page)

    def _ao_encerrar(self) -> None:
        log.info("MainWindow", "_ao_encerrar", "encerrando aplicação...")
        thread_manager.encerrar_todas()
        log.info("MainWindow", "_ao_encerrar", "shutdown concluído")

    def closeEvent(self, event) -> None:
        log.info("MainWindow", "closeEvent", "janela fechando...")
        self._salvar_sessao()
        super().closeEvent(event)