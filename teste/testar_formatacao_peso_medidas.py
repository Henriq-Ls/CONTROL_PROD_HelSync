"""Testes isolados da unidade exibida nas imagens de medidas.

Execute da raiz do projeto:
    python teste/testar_formatacao_peso_medidas.py

As funções puras são carregadas da AST para não importar Pillow, rembg nem abrir
a interface desktop.
"""

from __future__ import annotations

import ast
import math
import os
import pathlib
import re
import unittest
from decimal import Decimal, InvalidOperation


PROJETO = pathlib.Path(__file__).resolve().parents[1]
ARQUIVO = PROJETO / "Tratar_midias" / "f__Medidas_Graficos.py"


def _carregar_funcoes():
    arvore = ast.parse(ARQUIVO.read_text(encoding="utf-8"))
    nomes = {"_extrair_medidas", "_formatar_peso_exibicao"}
    funcoes = [
        no
        for no in arvore.body
        if isinstance(no, ast.FunctionDef) and no.name in nomes
    ]
    encontrados = {funcao.name for funcao in funcoes}
    if encontrados != nomes:
        raise RuntimeError(
            f"Funções de peso ausentes em {ARQUIVO}: {nomes - encontrados}"
        )

    modulo = ast.Module(body=funcoes, type_ignores=[])
    ast.fix_missing_locations(modulo)
    namespace = {
        "Decimal": Decimal,
        "InvalidOperation": InvalidOperation,
        "math": math,
        "os": os,
        "re": re,
    }
    exec(compile(modulo, str(ARQUIVO), "exec"), namespace)
    return namespace["_extrair_medidas"], namespace["_formatar_peso_exibicao"]


_extrair_medidas, _formatar_peso = _carregar_funcoes()


class TestarFormatacaoPesoMedidas(unittest.TestCase):
    def test_peso_sem_unidade_no_nome_recebe_gramas(self):
        medidas = _extrair_medidas("CAS1_05_7x4x2_25.jpg")
        self.assertEqual(medidas[3], "25")
        self.assertEqual(_formatar_peso(medidas[3]), "25gm")

    def test_peso_abaixo_de_mil_usa_gramas(self):
        self.assertEqual(_formatar_peso("999"), "999gm")
        self.assertEqual(_formatar_peso("0,25"), "0,25gm")

    def test_peso_de_mil_gramas_ou_mais_usa_quilogramas(self):
        self.assertEqual(_formatar_peso("1000"), "1.0kg")
        self.assertEqual(_formatar_peso("1250g"), "1.25kg")

    def test_unidade_quilograma_informada_e_preservada(self):
        self.assertEqual(_formatar_peso("0.25 kg"), "0.25kg")

    def test_unidade_g_e_normalizada_para_gm(self):
        self.assertEqual(_formatar_peso("25 g"), "25gm")
        self.assertEqual(_formatar_peso("25GM"), "25gm")

    def test_peso_zero_ou_vazio(self):
        self.assertEqual(_formatar_peso("0"), "0gm")
        self.assertEqual(_formatar_peso(""), "")


if __name__ == "__main__":
    unittest.main()
