"""Testes offline do fluxo de conversa da IA, sem abrir a janela PySide6.

Execute com:
    python teste/simular_chat_ia.py

O provedor HTTP é falso: nenhum acesso à internet ou chave real é usado.
"""

from __future__ import annotations

import ast
import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import types
import unittest
from types import MethodType
from pathlib import Path
from unittest.mock import patch


PROJETO = Path(__file__).resolve().parents[1]
ARQUIVO_SERVICO = PROJETO / "_IAS_" / "ia_service.py"
ARQUIVO_PAINEL = PROJETO / "_IAS_" / "Painel_IA_PySide6.py"
ARQUIVO_JANELA = PROJETO / "_APP_" / "main_window.py"
ARQUIVO_CONTEXTOS = PROJETO / "_IAS_" / "ia_contextos.py"
ARQUIVO_MEMORIA = PROJETO / "_IAS_" / "ia_memory_appdata.py"
ARQUIVO_CAMPOS_CADASTRO = (
    PROJETO / "_IAS_" / "Ferramentas" / "campos_cadastro.py"
)


def _carregar_resumo_aba():
    spec = importlib.util.spec_from_file_location(
        "_hen_place_ia_contextos_offline",
        ARQUIVO_CONTEXTOS,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Não foi possível carregar {ARQUIVO_CONTEXTOS}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.resumo_aba_ia


resumo_aba_ia = _carregar_resumo_aba()


def _carregar_funcoes_campos_cadastro():
    spec = importlib.util.spec_from_file_location(
        "_hen_place_ia_campos_cadastro_offline",
        ARQUIVO_CAMPOS_CADASTRO,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Não foi possível carregar {ARQUIVO_CAMPOS_CADASTRO}"
        )
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo.snapshot_para_ia, modulo.sanitizar_snapshot_para_ia


snapshot_para_ia_real, sanitizar_snapshot_para_ia = (
    _carregar_funcoes_campos_cadastro()
)


_REQUISICOES_CAPTURADAS = []
_MEMORIA_PRODUTOS = {}
_MEMORIA_GLOBAIS = {}
_MEMORIA_RASCUNHOS = {}
_MEMORIA_COMPARTILHADA = {}
_MEMORIA_SALVAS = []


class _LogSilencioso:
    def info(self, *args, **kwargs):
        pass

    def ok(self, *args, **kwargs):
        pass

    def aviso(self, *args, **kwargs):
        pass

    def erro(self, *args, **kwargs):
        pass


class _MessageBoxFalso:
    StandardButton = types.SimpleNamespace(Yes=1, No=0)
    ultima_pergunta = ""

    @classmethod
    def question(cls, _parent, _titulo, mensagem, *_args):
        cls.ultima_pergunta = str(mensagem)
        return cls.StandardButton.Yes


class _TimerSilencioso:
    @staticmethod
    def singleShot(_atraso, callback):
        callback()


class _SignalFalso:
    def connect(self, *_args, **_kwargs):
        pass


class _ThreadFalso:
    def __init__(self, *_args, **_kwargs):
        self.started = _SignalFalso()
        self.finished = _SignalFalso()

    def start(self):
        pass

    def quit(self):
        pass


class _WorkerFalso:
    def __init__(self, funcao, config, mensagens, **kwargs):
        _REQUISICOES_CAPTURADAS.append(
            {
                "funcao": funcao,
                "config": copy.deepcopy(config),
                "mensagens": copy.deepcopy(mensagens),
                "kwargs": copy.deepcopy(kwargs),
            }
        )
        self.progress_with_request = _SignalFalso()
        self.finished_with_request = _SignalFalso()
        self.failed_with_request = _SignalFalso()
        self.finished = _SignalFalso()
        self.failed = _SignalFalso()

    def moveToThread(self, *_args, **_kwargs):
        pass

    def run(self):
        pass

    def deleteLater(self):
        pass


def _carregar_memoria_produto(produto_id, escopo, _limite=20, **_kwargs):
    return copy.deepcopy(
        _MEMORIA_PRODUTOS.get((str(produto_id), str(escopo)), [])
    )


def _carregar_memoria_global(escopo, limite=100):
    return copy.deepcopy(_MEMORIA_GLOBAIS.get(str(escopo), []))


def _carregar_memoria_rascunho(rascunho_id, escopo, limite=100):
    return copy.deepcopy(
        _MEMORIA_RASCUNHOS.get((str(rascunho_id), str(escopo)), [])
    )


def _carregar_memoria_compartilhada(
    produto_id,
    conversa_id,
    escopo_atual,
    **_kwargs,
):
    return copy.deepcopy(
        _MEMORIA_COMPARTILHADA.get(
            (str(produto_id), str(conversa_id), str(escopo_atual)),
            [],
        )
    )


def _salvar_memoria_produto(*args, **kwargs):
    _MEMORIA_SALVAS.append((copy.deepcopy(args), copy.deepcopy(kwargs)))
    return 1


def _carregar_memoria_persistente_sem_appdata():
    """Carrega a persistência real com AppData apontado para uma raiz temporária."""
    pacote_appdata = types.ModuleType("_APPDATA_")
    pacote_appdata.appdata = types.SimpleNamespace(pasta_raiz="")
    sys.modules["_APPDATA_"] = pacote_appdata
    spec = importlib.util.spec_from_file_location(
        "_hen_place_ia_memory_appdata_offline",
        ARQUIVO_MEMORIA,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Não foi possível carregar {ARQUIVO_MEMORIA}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


memoria_persistente = _carregar_memoria_persistente_sem_appdata()


def _carregar_servico_sem_pyside():
    """Carrega o serviço real sem importar o pacote UI nem QSettings."""
    pacote = types.ModuleType("_IAS_")
    pacote.__path__ = [str(PROJETO / "_IAS_")]
    sys.modules["_IAS_"] = pacote

    configuracao = types.ModuleType("_IAS_.ia_config")

    def normalizar_provedor(item, indice=0):
        provedor = str(item.get("provider") or "").strip().lower()
        return {
            "name": str(item.get("name") or provedor or f"IA {indice + 1}"),
            "provider": provedor,
            "model": str(item.get("model") or "").strip(),
            "base_url": str(item.get("base_url") or "").strip(),
            "api_key": str(item.get("api_key") or "").strip(),
        }

    configuracao.normalizar_provedor = normalizar_provedor
    sys.modules["_IAS_.ia_config"] = configuracao

    modulo_logs = types.ModuleType("_LOGS_")
    modulo_logs.log = _LogSilencioso()
    sys.modules["_LOGS_"] = modulo_logs

    spec = importlib.util.spec_from_file_location(
        "_IAS_.ia_service",
        ARQUIVO_SERVICO,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Não foi possível carregar {ARQUIVO_SERVICO}")
    servico = importlib.util.module_from_spec(spec)
    sys.modules["_IAS_.ia_service"] = servico
    spec.loader.exec_module(servico)
    return servico


ia_service = _carregar_servico_sem_pyside()


def _extrair_funcoes(caminho, nomes, *, classe=None, ambiente=None):
    """Compila funções selecionadas do código real sem importar a interface."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    corpo = arvore.body
    if classe is not None:
        definicao_classe = next(
            (
                no
                for no in corpo
                if isinstance(no, ast.ClassDef) and no.name == classe
            ),
            None,
        )
        if definicao_classe is None:
            raise RuntimeError(f"Classe {classe} não encontrada em {caminho}")
        corpo = definicao_classe.body

    encontrados = {
        no.name: no
        for no in corpo
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
        and no.name in nomes
    }
    ausentes = set(nomes) - encontrados.keys()
    if ausentes:
        raise RuntimeError(
            f"Funções ausentes em {caminho}: {', '.join(sorted(ausentes))}"
        )

    namespace = dict(ambiente or {})
    for nome in nomes:
        funcao = copy.deepcopy(encontrados[nome])
        funcao.decorator_list = []
        exec(
            compile(
                ast.Module(body=[funcao], type_ignores=[]),
                str(caminho),
                "exec",
            ),
            namespace,
        )
    return {nome: namespace[nome] for nome in nomes}


class _RespostaSSEFalsa:
    """Resposta HTTP em memória que também observa o progresso durante a leitura."""

    headers = {"Content-Type": "text/event-stream; charset=utf-8"}

    def __init__(self, eventos, progresso):
        self._linhas = []
        self._progresso = progresso
        self.token_apareceu_antes_do_fim = False
        for evento in eventos:
            dados = json.dumps(evento, ensure_ascii=False)
            self._linhas.extend(
                [f"data: {dados}\n".encode("utf-8"), b"\n"]
            )
        self._linhas.extend([b"data: [DONE]\n", b"\n"])

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def __iter__(self):
        for indice, linha in enumerate(self._linhas):
            yield linha
            if indice == 1:
                self.token_apareceu_antes_do_fim = any(
                    evento.startswith("token|")
                    for evento in self._progresso
                )


_PAINEL_AUXILIARES = _extrair_funcoes(
    ARQUIVO_PAINEL,
    {"_chave_historico_aba", "_rotulo_historico_aba"},
)


def _funcoes_do_painel_sem_qt():
    """Compila os métodos puros do painel sem importar ou iniciar Qt."""
    nomes = {
        "_send_message",
        "_on_send_button_clicked",
        "_start_ai_request",
        "_ai_progress",
        "_ai_finished",
        "_ai_failed",
        "_update_send_state",
        "_marcar_resposta_ativa_descartada",
        "set_contexto_produto",
        "_carregar_memoria_atual",
        "_contexto_id_e_rascunho",
        "_persistir_mensagem",
        "_limpar_historico",
    }
    return _extrair_funcoes(
        ARQUIVO_PAINEL,
        nomes,
        classe="AIPanel",
        ambiente={
            "Any": object,
            "json": json,
            "log": _LogSilencioso(),
            "QMessageBox": _MessageBoxFalso,
            "_chave_historico_aba": _PAINEL_AUXILIARES[
                "_chave_historico_aba"
            ],
            "_rotulo_historico_aba": _PAINEL_AUXILIARES[
                "_rotulo_historico_aba"
            ],
            "pathlib": pathlib,
            "formatar_erro_usuario": ia_service.formatar_erro_usuario,
            "QTimer": _TimerSilencioso,
            "QThread": _ThreadFalso,
            "_CallableWorker": _WorkerFalso,
            "gerar_resposta": lambda *args, **kwargs: None,
            "resumo_aba_ia": resumo_aba_ia,
            "prompt_do_escopo": lambda escopo: f"PROMPT_SCOPE:{escopo}",
            "snapshot_para_ia": snapshot_para_ia_real,
            "sanitizar_snapshot_para_ia": sanitizar_snapshot_para_ia,
            "abrir_conversa": lambda produto_id, snapshot: f"conversa:{produto_id}",
            "salvar_produto": lambda *args, **kwargs: None,
            "promover_rascunho": lambda *args, **kwargs: 0,
            "carregar_mensagens": _carregar_memoria_produto,
            "carregar_memoria_compartilhada_produto": (
                _carregar_memoria_compartilhada
            ),
            "salvar_mensagem": _salvar_memoria_produto,
            "apagar_historico_conversa": (
                memoria_persistente.apagar_historico_conversa
            ),
            "abrir_conversa_global": lambda escopo: f"global:{escopo}",
            "carregar_mensagens_globais": _carregar_memoria_global,
            "carregar_rascunho_mensagens": _carregar_memoria_rascunho,
        },
    )


painel_funs = _funcoes_do_painel_sem_qt()


janela_funs = _extrair_funcoes(
    ARQUIVO_JANELA,
    {
        "_atualizar_contexto_ia_por_aba",
        "_on_creation_ai_context_changed",
        "_on_anuncio_ai_context_changed",
        "_on_prompts_ai_context_changed",
    },
    classe="MainWindow",
)


class _ControleFalso:
    def __init__(self, texto=""):
        self.texto = texto
        self.habilitado = True
        self.visivel = True
        self.tooltip = ""

    def setEnabled(self, valor):
        self.habilitado = bool(valor)

    def setVisible(self, valor):
        self.visivel = bool(valor)

    def setToolTip(self, texto):
        self.tooltip = str(texto)

    def setText(self, texto):
        self.texto = str(texto)

    def clear(self):
        self.texto = ""

    def toPlainText(self):
        return self.texto


class _LayoutFalso:
    def count(self):
        return 1

    def removeWidget(self, *_args, **_kwargs):
        pass


class _BolhaFalsa:
    def __init__(self):
        self.texto = ""

    def update_text(self, texto):
        self.texto = str(texto)

    def deleteLater(self):
        pass


class _CatalogoFerramentasFalso:
    def para_provedor(self):
        return []


class _EstadoPainelFalso:
    """Estado mínimo para executar os métodos reais sem QApplication."""

    def __init__(self):
        self.message = _ControleFalso()
        self.attachments_label = _ControleFalso()
        self.send_button = _ControleFalso()
        self.attach_button = _ControleFalso()
        self.microphone_button = _ControleFalso()
        self.status = _ControleFalso()
        self.draft_button = _ControleFalso()
        self.clear_history_button = _ControleFalso()
        self._anexos = []
        self._active_ai_request_id = None
        self._discarded_ai_request_ids = set()
        self._request_target = ""
        self._request_scope = ""
        self._request_product_id = ""
        self._contexto_produto = ""
        self._contexto_produto_id = ""
        self._contexto_aba = "Cadastro"
        self._contexto_snapshot = {}
        self._contexto_persistente = False
        self._escopo_historico = "Cadastro"
        self._contexto_produto_pendente = None
        self._conversa_id = ""
        self._rascunho_id = ""
        self._rascunho_historicos = {}
        self._historico = []
        self._mensagens_exibidas = []
        self._mensagens_persistidas = []
        self._propostas_ferramenta_pendentes = []
        self._ferramentas_pendentes_continuacao = None
        self._prompts_gerados_pendentes = []
        self._live_text = ""
        self._live_bubble = _BolhaFalsa()
        self._chat_layout = _LayoutFalso()
        self._chat_container = object()
        self._ai_request_sequence = 0
        self._rodada_ferramentas = 0
        self._ai_thread = None
        self._ai_worker = None
        self._catalogo_ferramentas = _CatalogoFerramentasFalso()
        self.config = {"system_prompt": "BASE_SYSTEM_PROMPT"}

        self._send_message = MethodType(painel_funs["_send_message"], self)
        self._on_send_button_clicked = MethodType(
            painel_funs["_on_send_button_clicked"],
            self,
        )
        self._start_ai_request = MethodType(
            painel_funs["_start_ai_request"],
            self,
        )
        self.set_contexto_produto = MethodType(
            painel_funs["set_contexto_produto"],
            self,
        )
        self._carregar_memoria_atual = MethodType(
            painel_funs["_carregar_memoria_atual"],
            self,
        )
        self._contexto_id_e_rascunho = MethodType(
            painel_funs["_contexto_id_e_rascunho"],
            self,
        )
        self._ai_progress = MethodType(painel_funs["_ai_progress"], self)
        self._ai_finished = MethodType(painel_funs["_ai_finished"], self)
        self._ai_failed = MethodType(painel_funs["_ai_failed"], self)
        self._ai_thread_finished = lambda: None

    def _append_message(self, papel, texto):
        self._mensagens_exibidas.append((str(papel), str(texto)))

    def _arquivo_contexto(self, _anexos):
        return ""

    def _persistir_mensagem(self, papel, conteudo, **_kwargs):
        self._mensagens_persistidas.append((str(papel), str(conteudo)))

    def _update_send_state(self):
        pass

    def _mensagem_pede_edicao(self, _texto):
        return False

    def _mensagem_pede_ferramenta(self, _texto):
        return False

    def _decisao_confirmacao(self, _texto):
        return None

    def _garantir_rascunho(self, _snapshot=None, _escopo="Cadastro"):
        self._rascunho_id = self._rascunho_id or "rascunho-offline"
        return self._rascunho_id


class _PainelCaptura:
    def __init__(self):
        self.chamadas = []

    def set_contexto_produto(self, contexto, produto_id="", escopo="Cadastro"):
        self.chamadas.append(
            {
                "contexto": copy.deepcopy(contexto),
                "produto_id": str(produto_id),
                "escopo": str(escopo),
            }
        )


class _AbasFalsas:
    def __init__(self, widgets):
        self.widgets = list(widgets)
        self.indice_atual = 0

    def widget(self, indice):
        return self.widgets[indice]

    def currentWidget(self):
        return self.widgets[self.indice_atual]


class _JanelaPrincipalFalsa:
    def __init__(self):
        self.ai_panel = _PainelCaptura()
        self.tabs = _AbasFalsas([])
        self.cadastro_snapshot = {
            "memoria_tipo": "rascunho",
            "salvo_no_banco": False,
            "nome": "CADASTRO_FICTICIO_SEM_ID",
        }
        self.producao_snapshot = {
            "memoria_tipo": "produto",
            "produto_id": "PRODUTO_FICTICIO_IA_7401",
            "nome": "PRODUTO_FICTICIO_CRIACAO_7401",
        }
        self.anuncio_snapshot = {
            "memoria_tipo": "produto",
            "produto_id": "PRODUTO_FICTICIO_ANUNCIO_7402",
            "nome": "PRODUTO_FICTICIO_ANUNCIO_7402",
        }
        self.prompts_snapshot = {
            "tipo_contexto": "catalogo_de_prompts",
            "prompt_ficticio": "MARCADOR_PROMPT_FICTICIO_7403",
        }

        self.cadastro_tab = types.SimpleNamespace()
        self.creation_tab = types.SimpleNamespace(current_row="linha-ficticia")
        self.results_tab = object()
        self.anuncio_tab = types.SimpleNamespace()
        self.vendas_tab = object()
        self.records_tab = object()
        self.prompts_tab = types.SimpleNamespace()
        self.settings_tab = object()

        self._atualizar_contexto_ia_por_aba = MethodType(
            janela_funs["_atualizar_contexto_ia_por_aba"],
            self,
        )
        self._on_creation_ai_context_changed = MethodType(
            janela_funs["_on_creation_ai_context_changed"],
            self,
        )
        self._on_anuncio_ai_context_changed = MethodType(
            janela_funs["_on_anuncio_ai_context_changed"],
            self,
        )
        self._on_prompts_ai_context_changed = MethodType(
            janela_funs["_on_prompts_ai_context_changed"],
            self,
        )

        self.cadastro_tab._publish_ai_context = (
            lambda: self.ai_panel.set_contexto_produto(
                self.cadastro_snapshot,
                escopo="Cadastro",
            )
        )
        self.creation_tab.ai_context_snapshot = (
            lambda: copy.deepcopy(self.producao_snapshot)
        )
        self.creation_tab.refresh = (
            lambda: self._on_creation_ai_context_changed(
                self.creation_tab.ai_context_snapshot()
            )
        )
        self.anuncio_tab.set_current_row = (
            lambda _row: self._on_anuncio_ai_context_changed(
                self.anuncio_snapshot
            )
        )
        self.prompts_tab.ai_context_snapshot = (
            lambda: copy.deepcopy(self.prompts_snapshot)
        )
        self.tabs.widgets = [
            self.cadastro_tab,
            self.creation_tab,
            self.results_tab,
            self.anuncio_tab,
            self.vendas_tab,
            self.records_tab,
            self.prompts_tab,
            self.settings_tab,
        ]


def _configuracao_free():
    return {
        "providers": [
            {
                "name": "OpenRouter",
                "provider": "openrouter",
                "model": "openrouter/free",
                "base_url": "https://offline.invalid/api/v1",
                "api_key": "offline-mock",
            }
        ]
    }


def _evento_conteudo(texto):
    return {
        "choices": [
            {
                "delta": {"content": texto},
                "finish_reason": None,
            }
        ]
    }


def _evento_final(motivo="stop"):
    return {
        "choices": [
            {
                "delta": {},
                "finish_reason": motivo,
            }
        ]
    }


class SimulacaoConversaIA(unittest.TestCase):
    def setUp(self):
        self.config = _configuracao_free()
        self.mensagens = [{"role": "user", "content": "olá"}]
        _REQUISICOES_CAPTURADAS.clear()
        _MEMORIA_PRODUTOS.clear()
        _MEMORIA_GLOBAIS.clear()
        _MEMORIA_RASCUNHOS.clear()
        _MEMORIA_COMPARTILHADA.clear()
        _MEMORIA_SALVAS.clear()

    def _enviar_no_painel_falso(self, estado, texto):
        estado._send_message(text_override=texto)
        self.assertTrue(_REQUISICOES_CAPTURADAS)
        return _REQUISICOES_CAPTURADAS[-1]["mensagens"]

    def test_clique_enviar_ignora_booleano_do_qt_e_limpa_o_campo(self):
        codigo_painel = ARQUIVO_PAINEL.read_text(encoding="utf-8")
        self.assertIn(
            "self.send_button.clicked.connect(self._on_send_button_clicked)",
            codigo_painel,
        )

        estado = _EstadoPainelFalso()
        pergunta_real = "Qual produto está selecionado neste cadastro?"
        estado.message.texto = pergunta_real

        # QPushButton.clicked emite False quando o botão não é checkable.
        estado._on_send_button_clicked(False)

        self.assertEqual(estado.message.texto, "")
        self.assertEqual(
            estado._historico[-1],
            {"role": "user", "content": pergunta_real},
        )
        self.assertEqual(
            estado._mensagens_exibidas[0],
            ("user", pergunta_real),
        )
        mensagens_worker = _REQUISICOES_CAPTURADAS[-1]["mensagens"]
        self.assertEqual(mensagens_worker[-1]["content"], pergunta_real)
        self.assertNotIn("False", str(mensagens_worker))

    def test_janela_principal_roda_o_escopo_e_a_tela_ativos(self):
        janela = _JanelaPrincipalFalsa()
        esperado = [
            ("Cadastro", janela.cadastro_snapshot, ""),
            (
                "Producao",
                {**janela.producao_snapshot, "area_ativa": "Criação"},
                "",
            ),
            (
                "Producao",
                {**janela.producao_snapshot, "area_ativa": "Resultados"},
                "",
            ),
            ("Anuncio", janela.anuncio_snapshot, ""),
            ("Vendas", {}, ""),
            ("Registros", {}, ""),
            ("Prompts", janela.prompts_snapshot, ""),
            ("Configuracoes", {}, ""),
        ]

        for indice, (escopo, snapshot, produto_id) in enumerate(esperado):
            with self.subTest(escopo=escopo, snapshot=snapshot):
                janela.tabs.indice_atual = indice
                antes = len(janela.ai_panel.chamadas)
                janela._atualizar_contexto_ia_por_aba(indice)
                self.assertEqual(len(janela.ai_panel.chamadas), antes + 1)
                chamada = janela.ai_panel.chamadas[-1]
                self.assertEqual(chamada["escopo"], escopo)
                self.assertEqual(chamada["produto_id"], produto_id)
                self.assertEqual(chamada["contexto"], snapshot)

        self.assertEqual(
            janela.ai_panel.chamadas[1]["contexto"]["area_ativa"],
            "Criação",
        )
        self.assertEqual(
            janela.ai_panel.chamadas[2]["contexto"]["area_ativa"],
            "Resultados",
        )
        self.assertEqual(janela.ai_panel.chamadas[4]["contexto"], {})
        self.assertEqual(janela.ai_panel.chamadas[5]["contexto"], {})
        self.assertEqual(janela.ai_panel.chamadas[7]["contexto"], {})

    def test_contexto_real_de_cada_aba_chega_ao_worker(self):
        casos = [
            (
                "Cadastro",
                {
                    "memoria_tipo": "rascunho",
                    "salvo_no_banco": False,
                    "produto_id": "",
                    "nome": "MARCADOR_CADASTRO_RASCUNHO_8101",
                    "origem_midias": "CAMINHO_ORIGEM_PRIVADO_8101",
                    "diretorio_base": "CAMINHO_DESTINO_PRIVADO_8101",
                    "proporcao": "PROPORCAO_PRIVADA_8101",
                    "arquivo_txt_origem": "CAMINHO_TXT_PRIVADO_8101",
                    "registro_banco": {
                        "campos": {
                            "DIRETORIO": "CAMINHO_BANCO_PRIVADO_8101",
                        }
                    },
                },
                "Snapshot atual do Cadastro (rascunho não salvo)",
            ),
            (
                "Producao",
                {
                    "memoria_tipo": "produto",
                    "produto_id": "PRODUTO_FICTICIO_CRIACAO_8102",
                    "nome": "MARCADOR_PRODUCAO_8102",
                    "area_ativa": "Criação",
                    "diretorio": "CAMINHO_PRODUCAO_PRIVADO_8102",
                    "proporcao": "PROPORCAO_PRODUCAO_PRIVADA_8102",
                },
                "Contexto do produto ativo em Criação/Resultados",
            ),
            (
                "Producao",
                {
                    "memoria_tipo": "produto",
                    "produto_id": "PRODUTO_FICTICIO_RESULTADOS_8103",
                    "nome": "MARCADOR_RESULTADOS_8103",
                    "area_ativa": "Resultados",
                },
                "Contexto do produto ativo em Criação/Resultados",
            ),
            (
                "Anuncio",
                {
                    "memoria_tipo": "produto",
                    "produto_id": "PRODUTO_FICTICIO_ANUNCIO_8104",
                    "nome": "MARCADOR_ANUNCIO_8104",
                },
                "Contexto textual do produto ativo em Anúncio",
            ),
            ("Vendas", {}, ""),
            ("Registros", {}, ""),
            (
                "Prompts",
                {
                    "tipo_contexto": "catalogo_de_prompts",
                    "prompt_ficticio": "MARCADOR_CATALOGO_PROMPTS_8105",
                },
                "Contexto do catálogo da aba Prompts",
            ),
            ("Configuracoes", {}, ""),
        ]
        sistemas = {}

        for indice, (escopo, snapshot, rotulo) in enumerate(casos):
            with self.subTest(escopo=escopo, indice=indice):
                _REQUISICOES_CAPTURADAS.clear()
                estado = _EstadoPainelFalso()
                produto_id = str(snapshot.get("produto_id") or "")
                if produto_id:
                    escopo_historico = (
                        _PAINEL_AUXILIARES["_chave_historico_aba"](
                            escopo,
                            snapshot,
                        )
                    )
                    _MEMORIA_PRODUTOS[(produto_id, escopo_historico)] = [
                        {
                            "role": "assistant",
                            "content": f"HISTORICO_ATUAL:{produto_id}",
                        }
                    ]

                estado.set_contexto_produto(snapshot, escopo=escopo)
                mensagens = self._enviar_no_painel_falso(
                    estado,
                    f"Pergunta da aba {escopo} {indice}",
                )
                sistema = mensagens[0]["content"]

                self.assertEqual(mensagens[0]["role"], "system")
                self.assertIn(
                    resumo_aba_ia(
                        escopo,
                        str(snapshot.get("area_ativa") or ""),
                    ),
                    sistema,
                )
                self.assertIn(f"PROMPT_SCOPE:{escopo}", sistema)
                if escopo != "Anuncio":
                    self.assertNotIn("PROMPT_SCOPE:Anuncio", sistema)
                if snapshot:
                    self.assertIn(rotulo, sistema)
                    for chave, valor in snapshot.items():
                        if (
                            isinstance(valor, str)
                            and valor
                            and chave
                            not in {
                                "origem_midias",
                                "diretorio_base",
                                "proporcao",
                                "arquivo_txt_origem",
                                "diretorio",
                            }
                        ):
                            self.assertIn(valor, sistema)
                else:
                    self.assertNotIn("Contexto do produto atual:", sistema)
                    self.assertNotIn("Contexto atual da aba:", sistema)
                for valor_privado in (
                    "CAMINHO_ORIGEM_PRIVADO_8101",
                    "CAMINHO_DESTINO_PRIVADO_8101",
                    "PROPORCAO_PRIVADA_8101",
                    "CAMINHO_TXT_PRIVADO_8101",
                    "CAMINHO_BANCO_PRIVADO_8101",
                    "CAMINHO_PRODUCAO_PRIVADO_8102",
                    "PROPORCAO_PRODUCAO_PRIVADA_8102",
                ):
                    self.assertNotIn(valor_privado, sistema)
                self.assertIn(
                    f"Pergunta da aba {escopo} {indice}",
                    mensagens[-1]["content"],
                )
                sistemas[(escopo, indice)] = sistema

        sistema_vendas = sistemas[("Vendas", 4)]
        self.assertIn("não recebe os dados das vendas", sistema_vendas)
        self.assertIn("não recebe essas linhas", sistemas[("Registros", 5)])

    def test_aba_producao_identifica_criacao_ou_revisao_de_resultados(self):
        criacao = resumo_aba_ia("Producao", "Criação")
        resultados = resumo_aba_ia("Producao", "Resultados")

        self.assertIn("Tela ativa: Criação", criacao)
        self.assertIn("preparando o processamento", criacao)
        self.assertIn("Tela ativa: Resultados", resultados)
        self.assertIn("revisando os resultados gerados", resultados)
        self.assertNotIn("Tela ativa: Resultados", criacao)
        self.assertNotIn("Tela ativa: Criação", resultados)

    def test_trocar_produto_e_aba_nao_envia_historico_anterior(self):
        produto_a = {
            "memoria_tipo": "produto",
            "produto_id": "PRODUTO_FICTICIO_A_8201",
            "nome": "MARCADOR_PRODUTO_A_8201",
            "area_ativa": "Criação",
        }
        produto_b = {
            "memoria_tipo": "produto",
            "produto_id": "PRODUTO_FICTICIO_B_8202",
            "nome": "MARCADOR_PRODUTO_B_8202",
        }
        _MEMORIA_PRODUTOS[
            (produto_a["produto_id"], "Producao_Criacao")
        ] = [
            {"role": "assistant", "content": "HISTORICO_EXCLUSIVO_PRODUTO_A_8201"}
        ]
        _MEMORIA_PRODUTOS[(produto_b["produto_id"], "Anuncio")] = [
            {"role": "assistant", "content": "HISTORICO_EXCLUSIVO_PRODUTO_B_8202"}
        ]

        estado = _EstadoPainelFalso()
        estado.set_contexto_produto(produto_a, escopo="Producao")
        mensagens_a = self._enviar_no_painel_falso(estado, "Pergunta do produto A")
        self.assertIn("HISTORICO_EXCLUSIVO_PRODUTO_A_8201", str(mensagens_a))

        # Simula a conclusão do pedido antes da troca de contexto.
        estado._active_ai_request_id = None
        estado.set_contexto_produto(produto_b, escopo="Anuncio")
        estado._active_ai_request_id = None
        mensagens_b = self._enviar_no_painel_falso(estado, "Pergunta do produto B")
        texto_b = str(mensagens_b)
        self.assertIn("MARCADOR_PRODUTO_B_8202", texto_b)
        self.assertIn("HISTORICO_EXCLUSIVO_PRODUTO_B_8202", texto_b)
        self.assertNotIn("PRODUTO_FICTICIO_A_8201", texto_b)
        self.assertNotIn("MARCADOR_PRODUTO_A_8201", texto_b)
        self.assertNotIn("HISTORICO_EXCLUSIVO_PRODUTO_A_8201", texto_b)

        estado._active_ai_request_id = None
        contexto_resultados = {
            **produto_b,
            "area_ativa": "Resultados",
        }
        estado.set_contexto_produto(contexto_resultados, escopo="Producao")
        mensagens_resultados = self._enviar_no_painel_falso(
            estado,
            "Quero revisar os resultados",
        )
        texto_resultados = str(mensagens_resultados)
        self.assertIn("Tela ativa: Resultados", texto_resultados)
        self.assertIn("PRODUTO_FICTICIO_B_8202", texto_resultados)
        self.assertNotIn("PRODUTO_FICTICIO_A_8201", texto_resultados)
        self.assertNotIn("HISTORICO_EXCLUSIVO_PRODUTO_B_8202", texto_resultados)

    def test_historico_do_mesmo_produto_e_separado_por_aba(self):
        produto_id = "PRODUTO_FICTICIO_TRES_ABAS_8250"
        criacao = {
            "memoria_tipo": "produto",
            "produto_id": produto_id,
            "nome": "PRODUTO_COMUM_8250",
            "area_ativa": "Criação",
        }
        resultados = {
            **criacao,
            "area_ativa": "Resultados",
        }
        anuncio = {
            "memoria_tipo": "produto",
            "produto_id": produto_id,
            "nome": "PRODUTO_COMUM_8250",
        }
        cadastro = {
            "memoria_tipo": "produto",
            "produto_id": produto_id,
            "nome": "PRODUTO_COMUM_8250",
        }
        _MEMORIA_PRODUTOS[(produto_id, "Producao")] = [
            {"role": "assistant", "content": "HISTORICO_LEGADO_MISTO_8250"}
        ]
        _MEMORIA_PRODUTOS[(produto_id, "Producao_Criacao")] = [
            {"role": "assistant", "content": "HISTORICO_CRIACAO_8250"}
        ]
        _MEMORIA_PRODUTOS[(produto_id, "Producao_Resultados")] = [
            {"role": "assistant", "content": "HISTORICO_RESULTADOS_8250"}
        ]
        _MEMORIA_PRODUTOS[(produto_id, "Anuncio")] = [
            {"role": "assistant", "content": "HISTORICO_ANUNCIO_8250"}
        ]
        _MEMORIA_PRODUTOS[(produto_id, "Cadastro")] = [
            {"role": "assistant", "content": "HISTORICO_CADASTRO_8250"}
        ]

        estado = _EstadoPainelFalso()
        casos = [
            (criacao, "Producao", "HISTORICO_CRIACAO_8250"),
            (resultados, "Producao", "HISTORICO_RESULTADOS_8250"),
            (criacao, "Producao", "HISTORICO_CRIACAO_8250"),
            (anuncio, "Anuncio", "HISTORICO_ANUNCIO_8250"),
            (cadastro, "Cadastro", "HISTORICO_CADASTRO_8250"),
        ]
        for indice, (snapshot, escopo, marcador_esperado) in enumerate(casos):
            with self.subTest(indice=indice, escopo=escopo):
                estado._active_ai_request_id = None
                estado.set_contexto_produto(snapshot, escopo=escopo)
                self.assertIn(
                    marcador_esperado,
                    str(estado._historico),
                )
                self.assertNotIn(
                    "HISTORICO_LEGADO_MISTO_8250",
                    str(estado._historico),
                )
                self._enviar_no_painel_falso(
                    estado,
                    f"Pergunta isolada {indice}",
                )
                mensagens_worker = _REQUISICOES_CAPTURADAS[-1]["mensagens"]
                texto_worker = str(mensagens_worker)
                self.assertIn(marcador_esperado, texto_worker)
                outros = {
                    "HISTORICO_CRIACAO_8250",
                    "HISTORICO_RESULTADOS_8250",
                    "HISTORICO_ANUNCIO_8250",
                    "HISTORICO_CADASTRO_8250",
                    "HISTORICO_LEGADO_MISTO_8250",
                } - {marcador_esperado}
                for marcador in outros:
                    self.assertNotIn(marcador, texto_worker)

    def test_gravacao_persistente_usa_chave_da_aba_sem_mudar_escopo_logico(self):
        estado = types.SimpleNamespace(
            _contexto_persistente=True,
            _contexto_produto_id="PRODUTO_FICTICIO_GRAVACAO_8260",
            _conversa_id="conversa-ficticia-8260",
            _contexto_aba="Producao",
            _escopo_historico="Producao_Resultados",
        )
        persistir = MethodType(painel_funs["_persistir_mensagem"], estado)
        persistir("assistant", "RESPOSTA_RESULTADOS_8260")

        self.assertEqual(len(_MEMORIA_SALVAS), 1)
        args, kwargs = _MEMORIA_SALVAS[0]
        self.assertEqual(
            args,
            (
                "PRODUTO_FICTICIO_GRAVACAO_8260",
                "Producao_Resultados",
                "assistant",
                "RESPOSTA_RESULTADOS_8260",
            ),
        )
        self.assertEqual(kwargs["conversa_id"], "conversa-ficticia-8260")
        self.assertEqual(estado._contexto_aba, "Producao")

    def test_historico_das_outras_abas_do_mesmo_produto_chega_ao_worker(self):
        produto_id = "PRODUTO_FICTICIO_MEMORIA_COMPARTILHADA_8267"
        conversa_id = "CONVERSA_FICTICIA_COMPARTILHADA_8267"
        estado = _EstadoPainelFalso()
        estado._contexto_persistente = True
        estado._contexto_produto_id = produto_id
        estado._conversa_id = conversa_id
        estado._contexto_aba = "Anuncio"
        estado._escopo_historico = "Anuncio"
        estado._contexto_produto = '{"nome": "Produto de teste"}'
        estado._contexto_snapshot = {"nome": "Produto de teste"}
        estado._historico = [
            {"role": "assistant", "content": "HISTORICO_VISIVEL_ANUNCIO_8267"}
        ]
        _MEMORIA_COMPARTILHADA[(produto_id, conversa_id, "Anuncio")] = [
            {
                "escopo": "Producao_Criacao",
                "role": "user",
                "content": "ASSUNTO_DEBATIDO_NA_CRIACAO_8267",
                "created_at": "2026-10-12T10:00:00+00:00",
            },
            {
                "escopo": "Producao_Resultados",
                "role": "assistant",
                "content": "DECISAO_DE_RESULTADOS_8267",
                "created_at": "2026-10-12T10:01:00+00:00",
            },
            {
                "escopo": "Producao",
                "role": "assistant",
                "content": "HISTORICO_LEGADO_8267",
                "created_at": "2026-10-12T10:02:00+00:00",
            },
        ]

        mensagens = self._enviar_no_painel_falso(
            estado,
            "Continue considerando o que debatemos sobre este produto.",
        )
        system_prompt = mensagens[0]["content"]

        self.assertIn("ASSUNTO_DEBATIDO_NA_CRIACAO_8267", system_prompt)
        self.assertIn("DECISAO_DE_RESULTADOS_8267", system_prompt)
        self.assertIn("HISTORICO_LEGADO_8267", system_prompt)
        self.assertIn(
            "Produção (legado; aba não identificada)",
            system_prompt,
        )
        self.assertIn("Anúncio", system_prompt)
        self.assertNotIn(
            "ASSUNTO_DEBATIDO_NA_CRIACAO_8267",
            str(estado._mensagens_exibidas),
        )
        self.assertNotIn(
            "DECISAO_DE_RESULTADOS_8267",
            str(estado._historico),
        )
        self.assertIn(
            "HISTORICO_VISIVEL_ANUNCIO_8267",
            str(estado._historico),
        )

    def test_conversa_global_de_producao_separa_criacao_e_resultados(self):
        _MEMORIA_GLOBAIS["Producao_Criacao"] = [
            {"role": "assistant", "content": "GLOBAL_CRIACAO_8265"}
        ]
        _MEMORIA_GLOBAIS["Producao_Resultados"] = [
            {"role": "assistant", "content": "GLOBAL_RESULTADOS_8265"}
        ]
        estado = _EstadoPainelFalso()

        for area, esperado, outro in (
            ("Criação", "GLOBAL_CRIACAO_8265", "GLOBAL_RESULTADOS_8265"),
            ("Resultados", "GLOBAL_RESULTADOS_8265", "GLOBAL_CRIACAO_8265"),
        ):
            estado._active_ai_request_id = None
            estado.set_contexto_produto(
                {"area_ativa": area},
                escopo="Producao",
            )
            self.assertEqual(estado._historico[0]["content"], esperado)
            mensagens = self._enviar_no_painel_falso(
                estado,
                f"Pergunta global de {area}",
            )
            self.assertIn(esperado, str(mensagens))
            self.assertNotIn(outro, str(mensagens))

    def test_persistencia_real_separa_abas_e_expoe_legado_isolado(self):
        produto_id = "PRODUTO_FICTICIO_MEMORIA_8270"
        with tempfile.TemporaryDirectory() as pasta_temporaria:
            with patch.object(
                memoria_persistente.appdata,
                "pasta_raiz",
                pasta_temporaria,
            ):
                conversa_id = memoria_persistente.abrir_conversa(
                    produto_id,
                    {"nome": "Produto fictício"},
                )
                memoria_persistente.salvar_produto(
                    produto_id,
                    {"produto_id": produto_id, "nome": "Produto fictício"},
                    conversa_id=conversa_id,
                )
                for escopo, texto in (
                    ("Producao", "LEGADO_MISTO_8270"),
                    ("Producao_Criacao", "CRIACAO_8270"),
                    ("Producao_Resultados", "RESULTADOS_8270"),
                    ("Anuncio", "ANUNCIO_8270"),
                ):
                    memoria_persistente.salvar_mensagem(
                        produto_id,
                        escopo,
                        "assistant",
                        texto,
                        conversa_id=conversa_id,
                    )

                self.assertEqual(
                    [
                        item["content"]
                        for item in memoria_persistente.carregar_mensagens(
                            produto_id,
                            "Producao_Criacao",
                            conversa_id=conversa_id,
                        )
                    ],
                    ["CRIACAO_8270"],
                )
                self.assertEqual(
                    [
                        item["content"]
                        for item in memoria_persistente.carregar_mensagens(
                            produto_id,
                            "Producao_Resultados",
                            conversa_id=conversa_id,
                        )
                    ],
                    ["RESULTADOS_8270"],
                )
                legado = memoria_persistente.carregar_historico_legado_producao(
                    produto_id,
                    conversa_id,
                )
                self.assertEqual(
                    [item["content"] for item in legado],
                    ["LEGADO_MISTO_8270"],
                )

    def test_memoria_compartilhada_inclui_outros_chats_e_isola_produto(self):
        produto_id = "PRODUTO_FICTICIO_CONTEXTO_CRUZADO_8275"
        outro_produto = "OUTRO_PRODUTO_FICTICIO_8275"
        with tempfile.TemporaryDirectory() as pasta_temporaria:
            with patch.object(
                memoria_persistente.appdata,
                "pasta_raiz",
                pasta_temporaria,
            ):
                conversa_id = memoria_persistente.abrir_conversa(
                    produto_id,
                    {"nome": "Produto fictício"},
                )
                conversa_outro = memoria_persistente.abrir_conversa(
                    outro_produto,
                    {"nome": "Outro produto fictício"},
                )
                for escopo, papel, texto in (
                    ("Cadastro", "user", "DEBATE_CADASTRO_8275"),
                    (
                        "Producao_Criacao",
                        "assistant",
                        "DEBATE_CRIACAO_8275",
                    ),
                    (
                        "Producao_Resultados",
                        "user",
                        "DEBATE_RESULTADOS_8275",
                    ),
                    ("Anuncio", "assistant", "HISTORICO_ATUAL_8275"),
                    ("Producao", "assistant", "LEGADO_NAO_COMPARTILHAR_8275"),
                ):
                    memoria_persistente.salvar_mensagem(
                        produto_id,
                        escopo,
                        papel,
                        texto,
                        conversa_id=conversa_id,
                    )
                arquivo_criacao = (
                    memoria_persistente._pasta_conversa(
                        produto_id,
                        conversa_id,
                        "Producao_Criacao",
                        criar=False,
                    )
                    / "conversa.jsonl"
                )
                with arquivo_criacao.open("a", encoding="utf-8") as arquivo:
                    arquivo.write("[]\nnull\n")
                memoria_persistente.salvar_mensagem(
                    outro_produto,
                    "Cadastro",
                    "assistant",
                    "OUTRO_PRODUTO_NAO_COMPARTILHAR_8275",
                    conversa_id=conversa_outro,
                )

                mensagens = (
                    memoria_persistente.carregar_memoria_compartilhada_produto(
                        produto_id,
                        conversa_id,
                        "Anuncio",
                    )
                )
                texto = str(mensagens)

                self.assertIn("DEBATE_CADASTRO_8275", texto)
                self.assertIn("DEBATE_CRIACAO_8275", texto)
                self.assertIn("DEBATE_RESULTADOS_8275", texto)
                self.assertNotIn("HISTORICO_ATUAL_8275", texto)
                self.assertIn("LEGADO_NAO_COMPARTILHAR_8275", texto)
                self.assertNotIn("OUTRO_PRODUTO_NAO_COMPARTILHAR_8275", texto)
                historico_criacao = memoria_persistente.carregar_mensagens(
                    produto_id,
                    "Producao_Criacao",
                    conversa_id=conversa_id,
                )
                self.assertEqual(
                    [item["content"] for item in historico_criacao],
                    ["DEBATE_CRIACAO_8275"],
                )

    def test_apagar_no_painel_remove_apenas_a_conversa_ativa(self):
        produto_id = "PRODUTO_FICTICIO_EXCLUSAO_8280"
        with tempfile.TemporaryDirectory() as pasta_temporaria:
            with patch.object(
                memoria_persistente.appdata,
                "pasta_raiz",
                pasta_temporaria,
            ):
                conversa_id = memoria_persistente.abrir_conversa(
                    produto_id,
                    {"produto_id": produto_id, "nome": "Produto fictício"},
                )
                memoria_persistente.salvar_produto(
                    produto_id,
                    {"produto_id": produto_id, "nome": "Produto fictício"},
                    conversa_id=conversa_id,
                )
                for escopo, texto in (
                    ("Producao", "LEGADO_PRESERVADO_8280"),
                    ("Producao_Criacao", "CRIACAO_APAGADA_8280"),
                    ("Producao_Resultados", "RESULTADOS_PRESERVADOS_8280"),
                ):
                    memoria_persistente.salvar_mensagem(
                        produto_id,
                        escopo,
                        "assistant",
                        texto,
                        conversa_id=conversa_id,
                    )

                estado = types.SimpleNamespace(
                    _active_ai_request_id=None,
                    _contexto_persistente=True,
                    _contexto_produto_id=produto_id,
                    _contexto_aba="Producao",
                    _contexto_snapshot={"area_ativa": "Criação"},
                    _escopo_historico="Producao_Criacao",
                    _conversa_id=conversa_id,
                    _historico=[{"role": "assistant", "content": "antiga"}],
                    _marcar_resposta_ativa_descartada=lambda: False,
                    _carregar_memoria_atual=lambda: None,
                )
                _MessageBoxFalso.ultima_pergunta = ""
                MethodType(painel_funs["_limpar_historico"], estado)()

                self.assertIn(
                    "somente as mensagens desta conversa de Criação",
                    _MessageBoxFalso.ultima_pergunta,
                )
                self.assertIn("histórico legado de Produção", _MessageBoxFalso.ultima_pergunta)
                self.assertEqual(estado._historico, [])
                self.assertEqual(
                    memoria_persistente.carregar_mensagens(
                        produto_id,
                        "Producao_Criacao",
                        conversa_id=conversa_id,
                    ),
                    [],
                )
                self.assertEqual(
                    [
                        item["content"]
                        for item in memoria_persistente.carregar_mensagens(
                            produto_id,
                            "Producao_Resultados",
                            conversa_id=conversa_id,
                        )
                    ],
                    ["RESULTADOS_PRESERVADOS_8280"],
                )
                self.assertEqual(
                    [
                        item["content"]
                        for item in memoria_persistente.carregar_historico_legado_producao(
                            produto_id,
                            conversa_id,
                        )
                    ],
                    ["LEGADO_PRESERVADO_8280"],
                )
                self.assertIsNotNone(
                    memoria_persistente.obter_produto(produto_id)
                )

    def test_cadastro_sem_produto_nao_herda_identidade_anterior(self):
        produto_anterior = {
            "memoria_tipo": "produto",
            "produto_id": "PRODUTO_ANTERIOR_8301",
            "nome": "MARCADOR_PRODUTO_ANTERIOR_8301",
        }
        _MEMORIA_PRODUTOS[
            (produto_anterior["produto_id"], "Producao_Criacao")
        ] = [
            {"role": "assistant", "content": "HISTORICO_PRODUTO_ANTERIOR_8301"}
        ]
        estado = _EstadoPainelFalso()
        estado.set_contexto_produto(
            {**produto_anterior, "area_ativa": "Criação"},
            escopo="Producao",
        )
        estado._active_ai_request_id = None

        rascunho = {
            "memoria_tipo": "rascunho",
            "salvo_no_banco": False,
            "produto_id": "",
            "nome": "",
            "descricao": "descrição parcial sem identidade confirmada",
        }
        estado.set_contexto_produto(rascunho, escopo="Cadastro")
        mensagens = self._enviar_no_painel_falso(
            estado,
            "Quais informações faltam?",
        )
        texto = str(mensagens)

        self.assertEqual(estado._contexto_produto_id, "__rascunho_atual__")
        self.assertFalse(estado._contexto_persistente)
        self.assertIn("Snapshot atual do Cadastro (rascunho não salvo)", texto)
        self.assertIn("peça esclarecimento", texto)
        self.assertNotIn("PRODUTO_ANTERIOR_8301", texto)
        self.assertNotIn("HISTORICO_PRODUTO_ANTERIOR_8301", texto)

    def test_ola_recebe_resposta_em_partes_sem_rede(self):
        progresso = []
        resposta_falsa = _RespostaSSEFalsa(
            [
                _evento_conteudo("Olá! "),
                _evento_conteudo("Estou respondendo."),
                _evento_final(),
            ],
            progresso,
        )
        requisicoes = []

        def abrir_url_falso(request, timeout):
            requisicoes.append(
                {
                    "payload": json.loads(request.data.decode("utf-8")),
                    "timeout": timeout,
                }
            )
            return resposta_falsa

        with patch.object(ia_service, "urlopen", side_effect=abrir_url_falso):
            resultado = ia_service.gerar_resposta(
                self.config,
                self.mensagens,
                progress=progresso.append,
            )

        self.assertEqual(resultado.texto, "Olá! Estou respondendo.")
        self.assertTrue(
            any(evento.startswith("token|Olá!") for evento in progresso)
        )
        self.assertTrue(
            resposta_falsa.token_apareceu_antes_do_fim,
            "O primeiro trecho deve chegar à interface antes do fim do stream.",
        )
        self.assertEqual(requisicoes[0]["payload"]["max_tokens"], 4096)
        self.assertTrue(requisicoes[0]["payload"]["stream"])

    def test_finish_length_gera_mensagem_com_proximo_passo(self):
        progresso = []
        resposta_falsa = _RespostaSSEFalsa(
            [_evento_final("length")],
            progresso,
        )

        with patch.object(
            ia_service,
            "urlopen",
            return_value=resposta_falsa,
        ):
            with self.assertRaises(RuntimeError) as erro:
                ia_service.gerar_resposta(
                    self.config,
                    self.mensagens,
                    progress=progresso.append,
                )

        status, mensagem = ia_service.formatar_erro_usuario(str(erro.exception))
        self.assertTrue(status)
        self.assertIn("limite", mensagem.casefold())
        self.assertIn("próximo passo", mensagem.casefold())

    def test_falha_atual_aparece_como_mensagem_do_sistema(self):
        class LayoutFalso:
            def removeWidget(self, widget):
                pass

        class BolhaFalsa:
            def deleteLater(self):
                pass

        class Estado:
            _request_target = ""
            _request_scope = ""
            _request_product_id = ""
            _discarded_ai_request_ids = set()
            _live_bubble = BolhaFalsa()
            _chat_layout = LayoutFalso()
            mensagens = []

            class status:
                valor = ""

                @classmethod
                def setText(cls, texto):
                    cls.valor = texto

            @staticmethod
            def _append_message(papel, texto):
                Estado.mensagens.append((papel, texto))

            @staticmethod
            def _scroll_chat_to_bottom():
                pass

        # Executa o método real extraído do arquivo, sem criar QApplication.
        metodo = painel_funs["_ai_failed"]
        erro = (
            "Nenhuma IA cadastrada respondeu.\n"
            "- OpenRouter (openrouter/free): finish_reason=length."
        )
        metodo(Estado, 5, erro)

        self.assertEqual(Estado.mensagens[-1][0], "system")
        texto = Estado.mensagens[-1][1].casefold()
        self.assertIn("limite", texto)
        self.assertIn("próximo passo", texto)
        self.assertTrue(Estado.status.valor)

    def test_apagar_marca_pedido_e_ignora_resposta_tardia(self):
        class LayoutFalso:
            def __init__(self):
                self.removidos = []

            def removeWidget(self, widget):
                self.removidos.append(widget)

        class BolhaFalsa:
            atualizada = False
            apagada = False

            def update_text(self, _texto):
                self.atualizada = True

            def deleteLater(self):
                self.apagada = True

        class Estado:
            _active_ai_request_id = 41
            _discarded_ai_request_ids = set()
            _ferramentas_pendentes_continuacao = ([], 1)
            _prompts_gerados_pendentes = ["próxima"]
            _propostas_ferramenta_pendentes = [{"nome": "pendente"}]
            _live_text = "resposta parcial"
            _live_bubble = BolhaFalsa()
            _chat_layout = LayoutFalso()

        bolha = Estado._live_bubble
        self.assertTrue(
            painel_funs["_marcar_resposta_ativa_descartada"](Estado)
        )
        self.assertIn(41, Estado._discarded_ai_request_ids)
        self.assertIsNone(Estado._ferramentas_pendentes_continuacao)
        self.assertEqual(Estado._prompts_gerados_pendentes, [])
        self.assertEqual(Estado._propostas_ferramenta_pendentes, [])
        self.assertIsNone(Estado._live_bubble)
        self.assertTrue(bolha.apagada)

        # Callbacks recebidos depois da exclusão não podem atualizar a conversa.
        painel_funs["_ai_progress"](Estado, 41, "token|resposta atrasada")
        painel_funs["_ai_finished"](Estado, 41, object())
        painel_funs["_ai_failed"](Estado, 41, "erro tardio")
        self.assertFalse(bolha.atualizada)


if __name__ == "__main__":
    unittest.main(verbosity=2)
