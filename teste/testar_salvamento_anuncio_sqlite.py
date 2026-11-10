"""Teste isolado do salvamento comercial sem iniciar o aplicativo PySide6."""

from __future__ import annotations

import ast
import math
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = PROJECT_ROOT / "_APP_" / "PySide6_core.py"
PRODUCT = "Produto de teste"
ITEM_ID = "TESTE-001"


def _carregar_funcao_core(
    db_path: Path,
    function_name: str,
) -> Callable[..., int]:
    """Carrega somente a função real, sem importar o módulo que usa PySide6."""
    tree = ast.parse(
        CORE_PATH.read_text(encoding="utf-8"),
        filename=str(CORE_PATH),
    )
    definitions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == function_name
    ]
    if len(definitions) != 1:
        raise AssertionError(
            f"Esperava exatamente uma definição ativa de {function_name}."
        )

    future_annotations = ast.ImportFrom(
        module="__future__",
        names=[ast.alias(name="annotations")],
        level=0,
    )
    isolated_module = ast.Module(
        body=[future_annotations, *definitions],
        type_ignores=[],
    )
    ast.fix_missing_locations(isolated_module)
    namespace: dict[str, Any] = {
        "sqlite3": sqlite3,
        "math": math,
        "DB_PATH": db_path,
        # O teste cria seu próprio esquema mínimo e não inicializa o app.
        "init_database": lambda: None,
    }
    exec(compile(isolated_module, str(CORE_PATH), "exec"), namespace)
    return namespace[function_name]


def _carregar_salvamento(db_path: Path) -> Callable[..., int]:
    return _carregar_funcao_core(
        db_path,
        "salvar_itens_anuncio_marketplace",
    )


def _carregar_salvamento_textos(db_path: Path) -> Callable[..., int]:
    return _carregar_funcao_core(
        db_path,
        "salvar_textos_anuncio_marketplace",
    )


def _criar_banco(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE VENDAS (
                ID TEXT,
                DATA TEXT,
                NOME_PRODUTO TEXT,
                KIT TEXT,
                OBSERVACOES TEXT,
                PLATAFORMAS_POSTADO TEXT,
                VALOR_VENDA REAL,
                CUSTO_PRODUTO REAL
            );
            CREATE TABLE MARKET_PLACE (
                ID TEXT,
                IMAGEM TEXT,
                DATA TEXT,
                NOME_PRODUTO TEXT,
                KIT TEXT,
                PLATAFORMAS_POSTADO TEXT,
                PLATAFORMA_VENDA TEXT,
                CLIENTE_NOME TEXT,
                CLIENTE_CPF TEXT,
                CLIENTE_TELEFONE TEXT,
                ENDERECO TEXT,
                VALOR_VENDA REAL,
                CUSTO_PRODUTO REAL,
                TAXA_PLATAFORMA REAL,
                LUCRO REAL,
                QUANTIDADE INTEGER,
                TITULO TEXT,
                DESCRITION TEXT
            );
            INSERT INTO VENDAS
                (ID, DATA, NOME_PRODUTO, KIT, OBSERVACOES,
                 PLATAFORMAS_POSTADO, VALOR_VENDA, CUSTO_PRODUTO)
            VALUES
                ('TESTE-001', '2026-10-12', 'Produto de teste', 'Kit teste',
                 'imagem-teste.png', '', 0, 0);
            """
        )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="hen-place-anuncio-") as temp_dir:
        db_path = Path(temp_dir) / "teste.sqlite"
        _criar_banco(db_path)
        salvar = _carregar_salvamento(db_path)

        primeiro = salvar(
            PRODUCT,
            "Título de teste",
            "Descrição de teste",
            [
                {
                    "id": ITEM_ID,
                    "platforms": ["Shopee"],
                    "sale_price": 24.90,
                    "cost": 5.00,
                    "quantity": 1,
                }
            ],
        )
        assert primeiro == 1, f"Esperava salvar 1 ID, recebi {primeiro}."

        segundo = salvar(
            PRODUCT,
            "Título atualizado",
            "Descrição atualizada",
            [
                {
                    "id": ITEM_ID,
                    "platforms": ["Shopee", "Site"],
                    "sale_price": 25.50,
                    "cost": 5.25,
                    "quantity": 1,
                }
            ],
        )
        assert segundo == 1, f"Esperava atualizar 1 ID, recebi {segundo}."

        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            venda = conn.execute(
                "SELECT * FROM VENDAS WHERE ID = ?", (ITEM_ID,)
            ).fetchone()
            itens = conn.execute(
                "SELECT * FROM MARKET_PLACE WHERE ID = ?", (ITEM_ID,)
            ).fetchall()

        assert venda is not None
        assert venda["PLATAFORMAS_POSTADO"] == "Shopee, Site"
        assert venda["VALOR_VENDA"] == 25.50
        assert venda["CUSTO_PRODUTO"] == 5.25
        assert len(itens) == 1, (
            f"Esperava uma unidade disponível, recebi {len(itens)}."
        )
        assert itens[0]["TITULO"] == "Título atualizado"
        assert itens[0]["DESCRITION"] == "Descrição atualizada"
        assert itens[0]["VALOR_VENDA"] == 25.50
        assert itens[0]["CUSTO_PRODUTO"] == 5.25

        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO MARKET_PLACE
                    (ID, IMAGEM, DATA, NOME_PRODUTO, KIT,
                     PLATAFORMAS_POSTADO, PLATAFORMA_VENDA, CLIENTE_NOME,
                     CLIENTE_CPF, CLIENTE_TELEFONE, ENDERECO, VALOR_VENDA,
                     CUSTO_PRODUTO, TAXA_PLATAFORMA, LUCRO, QUANTIDADE,
                     TITULO, DESCRITION)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ITEM_ID,
                    "imagem-vendida.png",
                    "2026-10-12",
                    PRODUCT,
                    "Kit teste",
                    "Shopee",
                    "Shopee",
                    "Cliente teste",
                    "00000000000",
                    "11999999999",
                    "Endereço teste",
                    25.50,
                    5.25,
                    0,
                    20.25,
                    1,
                    "Título atualizado",
                    "Descrição atualizada",
                ),
            )
            antes = conn.execute(
                """
                SELECT rowid, ID, IMAGEM, DATA, NOME_PRODUTO, KIT,
                       PLATAFORMAS_POSTADO, PLATAFORMA_VENDA, CLIENTE_NOME,
                       CLIENTE_CPF, CLIENTE_TELEFONE, ENDERECO, VALOR_VENDA,
                       CUSTO_PRODUTO, TAXA_PLATAFORMA, LUCRO, QUANTIDADE
                FROM MARKET_PLACE
                WHERE ID = ?
                ORDER BY rowid
                """,
                (ITEM_ID,),
            ).fetchall()

        salvar_textos = _carregar_salvamento_textos(db_path)
        ids_atualizados = salvar_textos(
            PRODUCT,
            "Título pronto atualizado",
            "Descrição pronta atualizada",
        )
        assert ids_atualizados == 1, (
            f"Esperava atualizar 1 ID de anúncio, recebi {ids_atualizados}."
        )

        with sqlite3.connect(db_path) as conn:
            depois = conn.execute(
                """
                SELECT rowid, ID, IMAGEM, DATA, NOME_PRODUTO, KIT,
                       PLATAFORMAS_POSTADO, PLATAFORMA_VENDA, CLIENTE_NOME,
                       CLIENTE_CPF, CLIENTE_TELEFONE, ENDERECO, VALOR_VENDA,
                       CUSTO_PRODUTO, TAXA_PLATAFORMA, LUCRO, QUANTIDADE,
                       TITULO, DESCRITION
                FROM MARKET_PLACE
                WHERE ID = ?
                ORDER BY rowid
                """,
                (ITEM_ID,),
            ).fetchall()

        assert len(antes) == len(depois) == 2
        for original, atual in zip(antes, depois):
            assert atual[:17] == original
            assert atual[17] == "Título pronto atualizado"
            assert atual[18] == "Descrição pronta atualizada"

    print(
        "OK: configuração comercial e texto do anúncio foram salvos no "
        "SQLite sem alterar estoque ou dados da venda."
    )


if __name__ == "__main__":
    main()
