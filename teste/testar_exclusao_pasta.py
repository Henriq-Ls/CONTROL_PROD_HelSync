"""Testes offline do método de exclusão de pasta da aba Criação.

Execute da raiz do projeto:
    python teste/testar_exclusao_pasta.py

O método real é compilado do controlador com QFile, QMessageBox e banco falsos.
Nenhuma interface é aberta e nenhum arquivo real é enviado à Lixeira.
"""

from __future__ import annotations

import ast
import copy
import pathlib
import tempfile
import unittest
from enum import IntFlag
from types import MethodType, SimpleNamespace


PROJETO = pathlib.Path(__file__).resolve().parents[1]
ARQUIVO_CONTROLADOR = (
    PROJETO / "_APP_" / "criacao" / "Controller_Criacao_PySide6.py"
)


def _extrair_funcao(caminho, nome, classe=None, ambiente=None):
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    if classe is None:
        declaracoes = [
            no
            for no in arvore.body
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
    else:
        classe_ast = next(
            (
                no
                for no in arvore.body
                if isinstance(no, ast.ClassDef) and no.name == classe
            ),
            None,
        )
        if classe_ast is None:
            raise RuntimeError(f"Classe {classe} não encontrada em {caminho}")
        declaracoes = [
            no
            for no in classe_ast.body
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
    funcao_ast = next((no for no in declaracoes if no.name == nome), None)
    if funcao_ast is None:
        raise RuntimeError(f"Função {nome} não encontrada em {caminho}")

    funcao_ast = copy.deepcopy(funcao_ast)
    funcao_ast.decorator_list = []
    modulo = ast.Module(body=[funcao_ast], type_ignores=[])
    ast.fix_missing_locations(modulo)
    namespace = dict(ambiente or {})
    exec(compile(modulo, str(caminho), "exec"), namespace)
    return namespace[nome]


class _QFileFalso:
    resultado = True
    chamadas = []

    @classmethod
    def moveToTrash(cls, caminho):
        cls.chamadas.append(str(caminho))
        return cls.resultado


class _MessageBoxFalso:
    class StandardButton(IntFlag):
        Yes = 1
        No = 2

    resposta = StandardButton.Yes
    avisos = []
    criticos = []
    confirmacoes = []

    @classmethod
    def question(cls, *args):
        cls.confirmacoes.append(args)
        return cls.resposta

    @classmethod
    def warning(cls, *args):
        cls.avisos.append(args)

    @classmethod
    def critical(cls, *args):
        cls.criticos.append(args)


class _ControladorFalso:
    def __init__(self, linha):
        self.current_row = linha
        self.refresh_calls = 0

    def refresh(self):
        self.refresh_calls += 1


class TesteExclusaoPasta(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        raiz = pathlib.Path(self.tempdir.name)
        self.pasta_produto = raiz / "produtos" / "produto-teste"
        self.pasta_produto.mkdir(parents=True)
        (self.pasta_produto / "imagem-teste.txt").write_text(
            "conteúdo de teste",
            encoding="utf-8",
        )
        self.appdata = raiz / "appdata"
        self.appdata.mkdir()
        self.linha = (
            "Produto de teste",
            "REF-TESTE",
            str(self.pasta_produto),
        )
        self.outras_entradas = [self.linha]
        self.apagados = []
        self.erro_no_banco = False
        self.ler_chamadas = 0
        _QFileFalso.resultado = True
        _QFileFalso.chamadas = []
        _MessageBoxFalso.resposta = _MessageBoxFalso.StandardButton.Yes
        _MessageBoxFalso.avisos = []
        _MessageBoxFalso.criticos = []
        _MessageBoxFalso.confirmacoes = []

        def ler_entradas():
            self.ler_chamadas += 1
            return list(self.outras_entradas)

        def apagar_entrada(produto):
            if self.erro_no_banco:
                raise RuntimeError("falha simulada no banco")
            self.apagados.append(produto)

        self.ambiente = {
            "Path": pathlib.Path,
            "QFile": _QFileFalso,
            "QMessageBox": _MessageBoxFalso,
            "appdata": SimpleNamespace(pasta_raiz=str(self.appdata)),
            "ler_entradas": ler_entradas,
            "apagar_entrada": apagar_entrada,
            "_path_contains": _extrair_funcao(
                ARQUIVO_CONTROLADOR,
                "_path_contains",
                ambiente={"Path": pathlib.Path},
            ),
            "__file__": str(ARQUIVO_CONTROLADOR),
        }
        self.metodo = _extrair_funcao(
            ARQUIVO_CONTROLADOR,
            "delete_folder_and_entry",
            classe="CreationController",
            ambiente=self.ambiente,
        )
        self.controlador = _ControladorFalso(self.linha)
        self.controlador.delete_folder_and_entry = MethodType(
            self.metodo,
            self.controlador,
        )

    def test_botao_novo_fica_ligado_ao_metodo_e_ao_estado_do_cadastro(self):
        codigo = ARQUIVO_CONTROLADOR.read_text(encoding="utf-8")

        self.assertIn(
            'self.delete_folder_button = QPushButton("Apagar pasta + cadastro")',
            codigo,
        )
        self.assertIn(
            "self.delete_folder_button.clicked.connect(",
            codigo,
        )
        self.assertIn(
            "self.delete_folder_button.setEnabled(False)",
            codigo,
        )
        self.assertIn(
            "self.delete_folder_button.setEnabled(True)",
            codigo,
        )

    def test_sucesso_move_a_pasta_para_lixeira_e_apaga_a_entrada(self):
        self.controlador.delete_folder_and_entry()

        self.assertEqual(
            _QFileFalso.chamadas,
            [str(self.pasta_produto.resolve())],
        )
        self.assertEqual(self.apagados, ["Produto de teste"])
        self.assertEqual(self.controlador.refresh_calls, 1)
        texto_confirmacao = str(_MessageBoxFalso.confirmacoes[0])
        self.assertIn("A_ENTRADA", texto_confirmacao)
        self.assertIn("Lixeira", texto_confirmacao)

    def test_cancelamento_nao_move_pasta_nem_apaga_cadastro(self):
        _MessageBoxFalso.resposta = _MessageBoxFalso.StandardButton.No

        self.controlador.delete_folder_and_entry()

        self.assertEqual(_QFileFalso.chamadas, [])
        self.assertEqual(self.apagados, [])
        self.assertEqual(self.controlador.refresh_calls, 0)

    def test_falha_ao_enviar_a_lixeira_preserva_o_cadastro(self):
        _QFileFalso.resultado = False

        self.controlador.delete_folder_and_entry()

        self.assertEqual(len(_QFileFalso.chamadas), 1)
        self.assertEqual(self.apagados, [])
        self.assertEqual(self.controlador.refresh_calls, 0)
        self.assertTrue(_MessageBoxFalso.avisos)

    def test_retorno_composto_com_falha_na_lixeira_preserva_o_cadastro(self):
        _QFileFalso.resultado = (False, "")

        self.controlador.delete_folder_and_entry()

        self.assertEqual(len(_QFileFalso.chamadas), 1)
        self.assertEqual(self.apagados, [])
        self.assertEqual(self.controlador.refresh_calls, 0)
        self.assertTrue(_MessageBoxFalso.avisos)

    def test_falha_no_banco_avisa_e_atualiza_a_tela(self):
        self.erro_no_banco = True

        self.controlador.delete_folder_and_entry()

        self.assertEqual(len(_QFileFalso.chamadas), 1)
        self.assertEqual(self.apagados, [])
        self.assertEqual(self.controlador.refresh_calls, 1)
        self.assertTrue(_MessageBoxFalso.criticos)

    def test_nao_apaga_pasta_compartilhada_com_outro_cadastro(self):
        subpasta = self.pasta_produto / "outro-produto"
        self.outras_entradas.append(
            ("Outro produto", "REF-OUTRO", str(subpasta))
        )

        self.controlador.delete_folder_and_entry()

        self.assertEqual(_QFileFalso.chamadas, [])
        self.assertEqual(self.apagados, [])
        self.assertTrue(_MessageBoxFalso.avisos)


if __name__ == "__main__":
    resultado = unittest.main(verbosity=2, exit=False)
    raise SystemExit(not resultado.result.wasSuccessful())
