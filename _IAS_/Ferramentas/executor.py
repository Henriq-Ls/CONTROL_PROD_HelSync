"""Executor explícito das ferramentas conhecidas pelo painel da IA."""

from __future__ import annotations

from typing import Any, Callable, Mapping

from .edicao_input import EditorInputCadastro
from .leitura_cadastro import ler_formulario_cadastro
from .pesquisa_link import pesquisar_link_produto
from .resultado import ResultadoFerramenta


class ExecutorFerramentas:
    """Despacha somente nomes registrados, sem executar métodos arbitrários."""

    def __init__(
        self,
        editor: EditorInputCadastro | None = None,
        snapshot_provider: Callable[[], Mapping[str, Any]] | None = None,
    ):
        self._editor = editor
        self._snapshot_provider = snapshot_provider

    def executar(
        self,
        nome: str,
        argumentos: Mapping[str, Any] | None = None,
        *,
        confirmacao_visual: bool = False,
    ) -> ResultadoFerramenta:
        args = dict(argumentos or {})
        ferramenta = str(nome or "").strip()
        if ferramenta == "ler_formulario_cadastro":
            snapshot = args.get("snapshot")
            if not isinstance(snapshot, Mapping) and self._snapshot_provider:
                snapshot = self._snapshot_provider()
            return ler_formulario_cadastro(snapshot)

        if ferramenta == "editar_input_cadastro":
            if self._editor is None:
                return ResultadoFerramenta.erro(
                    ferramenta,
                    "O Cadastro ainda não está conectado às ferramentas.",
                    codigo="CADASTRO_NAO_CONECTADO",
                )
            if confirmacao_visual:
                proposta = args.get("proposta")
                return self._editor.aplicar(proposta, confirmar=True)
            # A IA nunca pode aplicar uma edição, mesmo que envie
            # confirmar=True ou uma proposta completa. Quando um modelo
            # antigo envia confirmar junto com os valores, tratamos a
            # chamada como uma nova proposta para abrir a confirmação visual.
            if bool(args.get("confirmar")) and not args.get("campo_id"):
                return ResultadoFerramenta.erro(
                    ferramenta,
                    (
                        "A confirmação precisa ser feita no pop-up do Cadastro. "
                        "A IA não pode aplicar uma proposta diretamente."
                    ),
                    codigo="CONFIRMACAO_VISUAL_NECESSARIA",
                )
            return self._editor.propor(
                str(args.get("campo_id") or ""),
                args.get("novo_valor"),
                motivo=str(args.get("motivo") or ""),
            )

        if ferramenta == "pesquisar_link_produto":
            return pesquisar_link_produto(str(args.get("url") or ""))

        return ResultadoFerramenta.erro(
            ferramenta or "ferramenta",
            f"Ferramenta não registrada: {ferramenta or '(vazia)'}",
            codigo="FERRAMENTA_DESCONHECIDA",
        )

    def confirmar_edicao(
        self,
        proposta: Mapping[str, Any],
    ) -> ResultadoFerramenta:
        """Aplica uma proposta somente após ação explícita da interface."""
        if self._editor is None:
            return ResultadoFerramenta.erro(
                "editar_input_cadastro",
                "O Cadastro ainda não está conectado às ferramentas.",
                codigo="CADASTRO_NAO_CONECTADO",
            )
        return self._editor.aplicar(proposta, confirmar=True)