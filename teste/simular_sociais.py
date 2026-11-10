"""Simulação offline dos prompts e do roteamento da aba Sociais.

Execute da raiz do projeto:
    python teste/simular_sociais.py

O script usa somente a biblioteca padrão. Ele extrai os métodos reais dos
arquivos da aplicação sem importar PySide6, abrir a janela ou fazer chamadas
de rede. As respostas são exemplos fixos para testar o formato e o fluxo; não
são respostas de um modelo de IA real.
"""

from __future__ import annotations

import ast
import copy
import json
import pathlib
import re
import sys
import types
import unittest
from types import MethodType


PROJETO = pathlib.Path(__file__).resolve().parents[1]
ARQUIVO_SOCIAIS = (
    PROJETO / "_APP_" / "sociais" / "Controller_Sociais_PySide6.py"
)
ARQUIVO_PAINEL = PROJETO / "_IAS_" / "Painel_IA_PySide6.py"
ARQUIVO_JANELA = PROJETO / "_APP_" / "main_window.py"
ARQUIVO_CATALOGO_PROMPTS = (
    PROJETO / "_FERRAMENTAS_" / "prompts_ia" / "catalogo.json"
)
ARQUIVO_CONTEXTOS = PROJETO / "_IAS_" / "ia_contextos.py"


def _extrair_metodos(caminho, nome_classe, nomes, ambiente=None):
    """Compila métodos reais da classe indicada, sem importar seus módulos."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    classe = next(
        (
            no
            for no in arvore.body
            if isinstance(no, ast.ClassDef) and no.name == nome_classe
        ),
        None,
    )
    if classe is None:
        raise RuntimeError(f"Classe {nome_classe} não encontrada em {caminho}")

    declaracoes = {
        no.name: no
        for no in classe.body
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    namespace_base = dict(ambiente or {})
    metodos = {}
    for nome in nomes:
        no = declaracoes.get(nome)
        if no is None:
            raise RuntimeError(f"Método {nome} não encontrado em {caminho}")
        funcao = copy.deepcopy(no)
        funcao.decorator_list = []
        modulo = ast.Module(body=[funcao], type_ignores=[])
        ast.fix_missing_locations(modulo)
        namespace = dict(namespace_base)
        exec(compile(modulo, str(caminho), "exec"), namespace)
        metodos[nome] = namespace[nome]
    return metodos


def _carregar_configuracao_redes():
    arvore = ast.parse(ARQUIVO_SOCIAIS.read_text(encoding="utf-8"))
    valor = next(
        (
            no.value
            for no in arvore.body
            if isinstance(no, ast.AnnAssign)
            and isinstance(no.target, ast.Name)
            and no.target.id == "PLATFORM_CONFIGS"
        ),
        None,
    )
    if valor is None:
        raise RuntimeError(f"PLATFORM_CONFIGS não encontrado em {ARQUIVO_SOCIAIS}")
    return ast.literal_eval(valor)


PLATFORM_CONFIGS = _carregar_configuracao_redes()
METODOS_SOCIAIS = _extrair_metodos(
    ARQUIVO_SOCIAIS,
    "SociaisController",
    {"_build_prompt", "handle_ai_response"},
    ambiente={"PLATFORM_CONFIGS": PLATFORM_CONFIGS},
)


class _LogFalso:
    def info(self, *_args, **_kwargs):
        pass

    def aviso(self, *_args, **_kwargs):
        pass


class _RespostaIASentinela:
    """Tipo sentinela: as respostas deste teste são strings fixas."""


METODOS_PAINEL_IA = _extrair_metodos(
    ARQUIVO_PAINEL,
    "AIPanel",
    {"send_social_prompt", "_ai_finished"},
    ambiente={"log": _LogFalso(), "RespostaIA": _RespostaIASentinela},
)
METODOS_JANELA = _extrair_metodos(
    ARQUIVO_JANELA,
    "MainWindow",
    {"_on_social_prompt_requested"},
)


class _StatusFalso:
    def __init__(self):
        self.texto = ""

    def setText(self, texto):
        self.texto = str(texto)


class _SinalFalso:
    def __init__(self):
        self._slot = None

    def connect(self, slot):
        self._slot = slot

    def emit(self, *args):
        if self._slot is not None:
            self._slot(*args)


class _BolhaFalsa:
    def __init__(self):
        self.texto = ""

    def update_text(self, texto):
        self.texto = str(texto)


class _CartaoSocialFalso:
    def __init__(self):
        self.texto = ""
        self.status = ""

    def set_content(self, texto):
        self.texto = str(texto)

    def set_generation_status(self, texto):
        self.status = str(texto)


class _PainelFalso:
    """Substitui a interface e o envio HTTP, mantendo métodos reais de IA."""

    def __init__(self, product_id="TESTE-SOCIAL-001", scope="Sociais"):
        self._contexto_aba = scope
        self._contexto_produto_id = product_id
        self._active_ai_request_id = None
        self._discarded_ai_request_ids = set()
        self._request_target = ""
        self._request_scope = ""
        self._request_product_id = ""
        self._historico = []
        self._live_bubble = _BolhaFalsa()
        self._rascunho_id = ""
        self.config = {}
        self.status = _StatusFalso()
        self.sent = []
        self.persisted = []
        self.social_response_received = _SinalFalso()
        self.send_social_prompt = MethodType(
            METODOS_PAINEL_IA["send_social_prompt"],
            self,
        )
        self._ai_finished = MethodType(
            METODOS_PAINEL_IA["_ai_finished"],
            self,
        )

    def _send_message(self, text_override=None, *, response_target=""):
        """Captura a chamada e reproduz os metadados definidos no AIPanel."""
        self.sent.append(
            {
                "text": str(text_override or ""),
                "target": str(response_target or ""),
            }
        )
        self._request_target = str(response_target or "")
        self._request_scope = self._contexto_aba
        self._request_product_id = self._contexto_produto_id

    def _persistir_mensagem(self, papel, texto, **kwargs):
        self.persisted.append((papel, texto, kwargs))


class _SociaisFalsas:
    def __init__(self, produto_ativo, rede_pendente):
        self.cards = {rede: _CartaoSocialFalso() for rede in PLATFORM_CONFIGS}
        self._drafts_by_product = {}
        self._active_product_name = produto_ativo
        self._pending_request = (produto_ativo, rede_pendente)
        self.busy_changes = []

    def _set_generation_busy(self, busy):
        self.busy_changes.append(bool(busy))


PRODUTO_FICTICIO = (
    "Organizador adesivo de cabos",
    "SOCIAL-TEST-001",
    "CAMINHO_PRIVADO_NAO_ENVIAR",
    "Organizador adesivo para agrupar cabos em mesas e bancadas.",
    "Manter cabos agrupados em mesas e bancadas.",
    "1 organizador",
    "Preto",
    "1 unidade",
    "Instalar em superfície limpa e seca.",
)


# São apenas respostas fixas e conservadoras para simular a volta do modelo.
RESPOSTAS_SIMULADAS = {
    "pinterest": (
        "Título (até 100 caracteres): Organizador adesivo de cabos\n"
        "Descrição para colar (até 800 caracteres): Organize cabos em mesas "
        "e bancadas com este organizador adesivo.\n"
        "Tópicos relacionados para pesquisar/selecionar no Pinterest "
        "(até 5, sem #): organização de cabos; mesas organizadas"
    ),
    "instagram": (
        "Legenda pronta para colar (com até 5 hashtags relevantes no final): "
        "Organize cabos em mesas e bancadas com este organizador adesivo. "
        "#organizacaodecabos #mesaeorganizacao"
    ),
    "facebook": (
        "Texto da publicação (hashtags opcionais no próprio texto): "
        "Mantenha os cabos agrupados em mesas e bancadas com este "
        "organizador adesivo."
    ),
    "tiktok": (
        "Descrição para colar:\n"
        "Organize cabos em mesas e bancadas com este organizador adesivo.\n"
        "Hashtags para adicionar no passo próprio do TikTok "
        "(somente as relevantes):\n"
        "#organizacaodecabos #mesaeorganizacao"
    ),
    "youtube_shorts": (
        "Título (até 100 caracteres): Organizador adesivo de cabos\n"
        "Descrição para colar (até 5.000 caracteres, com até 3 hashtags "
        "relevantes no final): Agrupe cabos em mesas e bancadas com este "
        "organizador adesivo. #organizacaodecabos\n"
        "Tags opcionais do YouTube Studio (somente variantes de grafia "
        "úteis; se não houver, escreva “Não necessárias”): Não necessárias"
    ),
}


class TesteOfflineSociais(unittest.TestCase):
    def test_prompt_por_rede_inclui_regras_fatos_e_nao_envia_caminho(self):
        self.assertEqual(set(PLATFORM_CONFIGS), set(RESPOSTAS_SIMULADAS))
        prompts = {}
        termos_especificos = {
            "pinterest": ("até 5 tópicos", "eles não são hashtags"),
            "instagram": ("no máximo 5 hashtags", "não um título"),
            "facebook": ("Hashtags são opcionais", "não crie título"),
            "tiktok": ("sem tendências inventadas", "Não crie título"),
            "youtube_shorts": (
                "no máximo 3",
                "Tags do YouTube Studio",
                "variantes de grafia",
            ),
        }

        for rede, config in PLATFORM_CONFIGS.items():
            with self.subTest(rede=rede):
                prompt = METODOS_SOCIAIS["_build_prompt"](
                    rede,
                    PRODUTO_FICTICIO,
                )
                prompts[rede] = prompt

                self.assertIn(config["name"], prompt)
                self.assertIn(config["guidance"], prompt)
                self.assertIn(config["output_format"], prompt)
                self.assertIn("Não invente materiais", prompt)
                self.assertIn(
                    "A IA não recebeu nem analisou imagens ou vídeos.",
                    prompt,
                )
                for fato in (
                    PRODUTO_FICTICIO[0],
                    PRODUTO_FICTICIO[1],
                    PRODUTO_FICTICIO[3],
                    PRODUTO_FICTICIO[4],
                    PRODUTO_FICTICIO[5],
                    PRODUTO_FICTICIO[6],
                    PRODUTO_FICTICIO[7],
                    PRODUTO_FICTICIO[8],
                ):
                    self.assertIn(fato, prompt)
                self.assertNotIn(PRODUTO_FICTICIO[2], prompt)
                for termo in termos_especificos[rede]:
                    self.assertIn(termo.casefold(), prompt.casefold())

        self.assertEqual(len(set(prompts.values())), len(PLATFORM_CONFIGS))

    def test_prompt_combina_anuncio_salvo_com_fatos_do_cadastro(self):
        prompt = METODOS_SOCIAIS["_build_prompt"](
            "instagram",
            PRODUTO_FICTICIO,
            {
                "title": "Organizador de cabos compacto",
                "description": "Mantenha os cabos da mesa em ordem.",
            },
        )

        self.assertIn(
            "Título: Organizador de cabos compacto",
            prompt,
        )
        self.assertIn(
            "Descrição: Mantenha os cabos da mesa em ordem.",
            prompt,
        )
        self.assertIn(
            "Descrição cadastrada: "
            "Organizador adesivo para agrupar cabos em mesas e bancadas.",
            prompt,
        )
        self.assertIn("Os fatos do Cadastro são a fonte factual", prompt)

    def test_fluxo_simulado_envia_para_ia_e_volta_ao_card_correspondente(self):
        for rede, resposta in RESPOSTAS_SIMULADAS.items():
            with self.subTest(rede=rede):
                painel = _PainelFalso(product_id=PRODUTO_FICTICIO[0])
                sociais = _SociaisFalsas(PRODUTO_FICTICIO[0], rede)
                sociais.handle_ai_response = MethodType(
                    METODOS_SOCIAIS["handle_ai_response"],
                    sociais,
                )
                painel.social_response_received.connect(
                    sociais.handle_ai_response
                )
                janela = types.SimpleNamespace(
                    ai_panel=painel,
                    socials_tab=types.SimpleNamespace(
                        ai_request_rejected=lambda *_args: None,
                    ),
                )
                janela._on_social_prompt_requested = MethodType(
                    METODOS_JANELA["_on_social_prompt_requested"],
                    janela,
                )
                prompt = METODOS_SOCIAIS["_build_prompt"](
                    rede,
                    PRODUTO_FICTICIO,
                )

                janela._on_social_prompt_requested(rede, prompt)

                self.assertEqual(len(painel.sent), 1)
                self.assertEqual(painel.sent[0]["text"], prompt)
                self.assertEqual(painel.sent[0]["target"], f"Sociais:{rede}")
                self.assertEqual(painel._request_scope, "Sociais")
                self.assertEqual(
                    painel._request_product_id,
                    PRODUTO_FICTICIO[0],
                )

                # Passa uma fixture pelo método real que trata a resposta.
                painel._ai_finished(1, resposta)

                self.assertEqual(sociais.cards[rede].texto, resposta)
                self.assertIn("Texto recebido", sociais.cards[rede].status)
                self.assertEqual(
                    sociais._drafts_by_product[PRODUTO_FICTICIO[0]][rede][
                        "text"
                    ],
                    resposta,
                )
                for outra_rede, cartao in sociais.cards.items():
                    if outra_rede != rede:
                        self.assertEqual(cartao.texto, "")
                self.assertEqual(painel._request_target, "")
                self.assertEqual(painel._request_scope, "")
                self.assertEqual(painel._request_product_id, "")

    def test_resposta_de_produto_anterior_nao_aparece_no_card_ativo(self):
        sociais = _SociaisFalsas("Produto atual", "instagram")
        sociais.handle_ai_response = MethodType(
            METODOS_SOCIAIS["handle_ai_response"],
            sociais,
        )

        sociais.handle_ai_response(
            "Produto anterior",
            "instagram",
            "Resposta antiga de teste",
        )

        self.assertEqual(sociais.cards["instagram"].texto, "")
        self.assertEqual(
            sociais._drafts_by_product["Produto anterior"]["instagram"][
                "text"
            ],
            "Resposta antiga de teste",
        )

    def test_fixtures_nao_incluem_caracteristicas_nao_cadastradas(self):
        alegacoes_nao_confirmadas = (
            "silicone",
            "alumínio",
            "inox",
            "à prova d'água",
            "garantia",
            "sem furos",
            "super resistente",
        )
        for rede, resposta in RESPOSTAS_SIMULADAS.items():
            with self.subTest(rede=rede):
                self.assertIn("organizador", resposta.casefold())
                for alegacao in alegacoes_nao_confirmadas:
                    self.assertNotIn(alegacao, resposta.casefold())


def _relatar_contexto_padrao_sociais():
    """Mostra se há instruções centrais padrão para conversa livre em Sociais."""
    avisos = []
    if ARQUIVO_CATALOGO_PROMPTS.exists():
        catalogo = json.loads(
            ARQUIVO_CATALOGO_PROMPTS.read_text(encoding="utf-8")
        )
        tem_prompt = any(
            str(item.get("escopo") or "").strip().casefold() == "sociais"
            for item in catalogo
            if isinstance(item, dict)
        )
        if not tem_prompt:
            avisos.append(
                "o catálogo padrão de prompts não tem entrada de escopo "
                "Sociais; os prompts do botão de geração continuam contendo "
                "regras específicas por rede"
            )
    if ARQUIVO_CONTEXTOS.exists():
        mapa = ARQUIVO_CONTEXTOS.read_text(encoding="utf-8").casefold()
        if "sociais" not in mapa:
            avisos.append(
                "o mapa geral de contexto da IA não tem uma entrada Sociais; "
                "isso afeta mais a conversa livre do que o botão de geração"
            )
    return avisos


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(
        sys.modules[__name__]
    )
    resultado = unittest.TextTestRunner(verbosity=2).run(suite)
    for aviso in _relatar_contexto_padrao_sociais():
        print(f"AVISO: {aviso}")
    print(
        "\nSimulação offline: nenhuma janela, rede ou IA real foi iniciada. "
        "As respostas acima são fixtures fixas."
    )
    raise SystemExit(not resultado.wasSuccessful())
