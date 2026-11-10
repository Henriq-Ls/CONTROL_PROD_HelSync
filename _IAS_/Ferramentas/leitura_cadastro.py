"""Ferramenta de leitura do formulario atual do Cadastro."""

from __future__ import annotations

from typing import Any, Mapping

from .campos_cadastro import campos_com_valores
from .resultado import ResultadoFerramenta


NOME_FERRAMENTA = "ler_formulario_cadastro"


def ler_formulario_cadastro(
    snapshot: Mapping[str, Any] | None,
) -> ResultadoFerramenta:
    """Entrega à IA os campos, finalidades e valores do Cadastro atual."""
    dados_snapshot = dict(snapshot or {})
    campos = campos_com_valores(dados_snapshot)
    return ResultadoFerramenta.ok(
        NOME_FERRAMENTA,
        "Campos autorizados do Cadastro carregados para a IA.",
        {
            "aba": "Cadastro",
            "memoria_tipo": dados_snapshot.get("memoria_tipo", "rascunho"),
            "produto_id": dados_snapshot.get("produto_id", ""),
            "campos": campos,
        },
    )