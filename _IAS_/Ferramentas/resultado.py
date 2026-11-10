"""Resultado comum das ferramentas da IA."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class ResultadoFerramenta:
    """Resposta serializável de uma ferramenta."""

    sucesso: bool
    ferramenta: str
    mensagem: str
    dados: dict[str, Any] = field(default_factory=dict)
    requer_confirmacao: bool = False
    codigo: str = ""

    def como_dict(self) -> dict[str, Any]:
        return {
            "sucesso": self.sucesso,
            "ferramenta": self.ferramenta,
            "mensagem": self.mensagem,
            "dados": dict(self.dados),
            "requer_confirmacao": self.requer_confirmacao,
            "codigo": self.codigo,
        }

    @classmethod
    def ok(
        cls,
        ferramenta: str,
        mensagem: str,
        dados: Mapping[str, Any] | None = None,
        *,
        requer_confirmacao: bool = False,
    ) -> "ResultadoFerramenta":
        return cls(
            sucesso=True,
            ferramenta=ferramenta,
            mensagem=mensagem,
            dados=dict(dados or {}),
            requer_confirmacao=requer_confirmacao,
        )

    @classmethod
    def erro(
        cls,
        ferramenta: str,
        mensagem: str,
        *,
        codigo: str,
        dados: Mapping[str, Any] | None = None,
    ) -> "ResultadoFerramenta":
        return cls(
            sucesso=False,
            ferramenta=ferramenta,
            mensagem=mensagem,
            dados=dict(dados or {}),
            codigo=codigo,
        )