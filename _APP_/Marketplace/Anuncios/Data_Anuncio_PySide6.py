"""Leituras somente leitura do banco usadas por telas do aplicativo."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from _APP_.PySide6_core import DB_PATH


def ler_produtos_permanentes_somente_leitura() -> list[tuple]:
    """Lê somente produtos permanentes para o Marketplace, sem escrever."""
    caminho = Path(DB_PATH).expanduser()
    if not caminho.is_file():
        raise FileNotFoundError(
            f"O banco existente não foi encontrado: {caminho}"
        )

    uri = f"{caminho.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=5.0) as conexao:
        tabelas = {
            str(linha[0])
            for linha in conexao.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if "PRODUTOS_ATIVOS" not in tabelas:
            return []
        colunas_existentes = {
            str(linha[1])
            for linha in conexao.execute(
                "PRAGMA table_info(PRODUTOS_ATIVOS)"
            )
        }
        campos = (
            "PRODUTO",
            "REFERENCIA",
            "DIRETORIO",
            "DESCRITION",
            "SERVENTIA",
            "ACOMPANHA",
            "ACABAMENTO",
            "KIT",
            "OBS",
            "REGRAS_ANUNCIO",
            "PROPORCAO",
        )
        campos_sql = [
            f'"{campo}"' if campo in colunas_existentes
            else f'NULL AS "{campo}"'
            for campo in campos
        ]
        return conexao.execute(
            """
            SELECT {colunas}
            FROM PRODUTOS_ATIVOS
            ORDER BY rowid DESC
            """.format(colunas=", ".join(campos_sql))
        ).fetchall()


def listar_produtos_para_anunciar_somente_leitura() -> list[str]:
    """Lista produtos ativos e registros legados sem alterar o banco."""
    caminho = Path(DB_PATH).expanduser()
    if not caminho.is_file():
        raise FileNotFoundError(
            f"O banco existente não foi encontrado: {caminho}"
        )

    uri = f"{caminho.resolve().as_uri()}?mode=ro"
    nomes: list[str] = []
    vistos: set[str] = set()
    fontes = (
        ("PRODUTOS_ATIVOS", "PRODUTO"),
        ("VENDAS", "NOME_PRODUTO"),
        ("MARKET_PLACE", "NOME_PRODUTO"),
    )
    with sqlite3.connect(uri, uri=True, timeout=5.0) as conexao:
        tabelas = {
            str(linha[0])
            for linha in conexao.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        fontes_existentes = [
            (tabela, coluna)
            for tabela, coluna in fontes
            if tabela in tabelas
        ]
        if not fontes_existentes:
            raise RuntimeError(
                "O banco não contém produtos ativos nem registros legados."
            )

        for tabela, coluna in fontes_existentes:
            linhas = conexao.execute(
                f"""
                SELECT "{coluna}"
                FROM "{tabela}"
                WHERE "{coluna}" IS NOT NULL
                  AND TRIM("{coluna}") <> ''
                ORDER BY rowid DESC
                """
            ).fetchall()
            for linha in linhas:
                nome = str(linha[0] or "").strip()
                chave = nome.casefold()
                if nome and chave not in vistos:
                    vistos.add(chave)
                    nomes.append(nome)
    return nomes


def ler_entradas_somente_leitura() -> list[tuple]:
    """Lê a fila temporária A_ENTRADA sem criar ou modificar tabelas."""
    caminho = Path(DB_PATH).expanduser()
    if not caminho.is_file():
        raise FileNotFoundError(
            f"O banco existente não foi encontrado: {caminho}"
        )

    uri = f"{caminho.resolve().as_uri()}?mode=ro"
    conexao = sqlite3.connect(uri, uri=True, timeout=5.0)
    try:
        tabelas = {
            str(linha[0])
            for linha in conexao.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if "A_ENTRADA" not in tabelas:
            return []
        colunas_existentes = {
            str(linha[1])
            for linha in conexao.execute("PRAGMA table_info(A_ENTRADA)")
        }
        campos = (
            "PRODUTO",
            "REFERENCIA",
            "DIRETORIO",
            "DESCRITION",
            "SERVENTIA",
            "ACOMPANHA",
            "ACABAMENTO",
            "KIT",
            "OBS",
            "REGRAS_ANUNCIO",
            "PROPORCAO",
        )
        campos_sql = [
            f'"{campo}"' if campo in colunas_existentes
            else f'NULL AS "{campo}"'
            for campo in campos
        ]
        return conexao.execute(
            f"""
            SELECT {", ".join(campos_sql)}
            FROM A_ENTRADA
            ORDER BY rowid
            """
        ).fetchall()
    finally:
        conexao.close()
