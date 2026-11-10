"""Ferramenta de proposta e aplicação de edição de input."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from .cadastro_adapter import AdaptadorCadastro
from .campos_cadastro import (
    CAMPOS_EDITAVEIS_IA,
    CampoCadastro,
    campo_por_id,
)
from .resultado import ResultadoFerramenta


NOME_FERRAMENTA = "editar_input_cadastro"


@dataclass(frozen=True)
class PropostaEdicao:
    """Alteração pendente; não altera a tela sozinha."""

    id: str
    campo_id: str
    valor_anterior: Any
    novo_valor: Any
    motivo: str
    criada_em: str

    def como_dict(self) -> dict[str, Any]:
        return asdict(self)


class EditorInputCadastro:
    """Cria propostas e aplica somente propostas confirmadas."""

    def __init__(self, adaptador: AdaptadorCadastro):
        self.adaptador = adaptador

    def propor(
        self,
        campo_id: str,
        novo_valor: Any,
        *,
        motivo: str = "",
    ) -> ResultadoFerramenta:
        campo = campo_por_id(campo_id)
        if campo is None:
            return ResultadoFerramenta.erro(
                NOME_FERRAMENTA,
                f"Campo desconhecido: {campo_id}.",
                codigo="CAMPO_DESCONHECIDO",
            )
        if campo.id not in CAMPOS_EDITAVEIS_IA:
            return ResultadoFerramenta.erro(
                NOME_FERRAMENTA,
                (
                    f"O campo '{campo.rotulo}' é apenas para sugestão. "
                    "A IA só pode preencher Nome, Descrição e Como pode ser usado."
                ),
                codigo="CAMPO_SOMENTE_SUGESTAO",
            )
        if not campo.editavel:
            return ResultadoFerramenta.erro(
                NOME_FERRAMENTA,
                f"O campo '{campo.rotulo}' é somente leitura nesta primeira versão.",
                codigo="CAMPO_SOMENTE_LEITURA",
            )

        try:
            valor_atual = self.adaptador.ler_valor(campo_id)
            valor_normalizado = self._normalizar_e_validar(campo, novo_valor)
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            return ResultadoFerramenta.erro(
                NOME_FERRAMENTA,
                str(exc),
                codigo="VALOR_INVALIDO",
            )

        proposta = PropostaEdicao(
            id=uuid.uuid4().hex,
            campo_id=campo_id,
            valor_anterior=valor_atual,
            novo_valor=valor_normalizado,
            motivo=str(motivo or "").strip(),
            criada_em=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        return ResultadoFerramenta.ok(
            NOME_FERRAMENTA,
            f"Proposta criada para o campo '{campo.rotulo}'.",
            {
                "proposta": proposta.como_dict(),
                "campo": campo.como_dict(valor_atual),
            },
            requer_confirmacao=True,
        )

    def aplicar(
        self,
        proposta: PropostaEdicao | Mapping[str, Any],
        *,
        confirmar: bool = False,
    ) -> ResultadoFerramenta:
        proposta_obj = self._converter_proposta(proposta)
        if proposta_obj is None:
            return ResultadoFerramenta.erro(
                NOME_FERRAMENTA,
                "Proposta de edição inválida.",
                codigo="PROPOSTA_INVALIDA",
            )
        if not confirmar:
            return ResultadoFerramenta.erro(
                NOME_FERRAMENTA,
                "A edição só pode ser aplicada após confirmação explícita.",
                codigo="CONFIRMACAO_NECESSARIA",
                dados={"proposta": proposta_obj.como_dict()},
            )

        try:
            valor_atual = self.adaptador.ler_valor(proposta_obj.campo_id)
        except (AttributeError, KeyError, TypeError) as exc:
            return ResultadoFerramenta.erro(
                NOME_FERRAMENTA,
                str(exc),
                codigo="CAMPO_INDISPONIVEL",
            )
        if valor_atual != proposta_obj.valor_anterior:
            return ResultadoFerramenta.erro(
                NOME_FERRAMENTA,
                "O campo mudou desde a proposta; a alteração foi cancelada.",
                codigo="CONFLITO_DE_VALOR",
                dados={
                    "valor_da_proposta": proposta_obj.valor_anterior,
                    "valor_atual": valor_atual,
                },
            )

        try:
            valor_aplicado = self.adaptador.aplicar_valor(
                proposta_obj.campo_id,
                proposta_obj.novo_valor,
            )
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            return ResultadoFerramenta.erro(
                NOME_FERRAMENTA,
                str(exc),
                codigo="FALHA_AO_APLICAR",
            )
        return ResultadoFerramenta.ok(
            NOME_FERRAMENTA,
            "Alteração aplicada ao input do Cadastro.",
            {
                "proposta": proposta_obj.como_dict(),
                "valor_anterior": valor_atual,
                "valor_aplicado": valor_aplicado,
                "snapshot": self.adaptador.snapshot_atual(),
            },
        )

    @staticmethod
    def _normalizar_e_validar(campo: CampoCadastro, valor: Any) -> Any:
        if campo.tipo == "multiseleção":
            valores = (
                valor
                if isinstance(valor, (list, tuple, set))
                else str(valor or "").split(",")
            )
            normalizados = [str(item).strip() for item in valores if str(item).strip()]
            if not normalizados:
                return ""
            permitidos = set(campo.opcoes)
            invalidos = [item for item in normalizados if item not in permitidos]
            if invalidos:
                raise ValueError(
                    f"Opção(s) inválida(s) para {campo.id}: {', '.join(invalidos)}."
                )
            return ", ".join(dict.fromkeys(normalizados))

        texto = str(valor if valor is not None else "").strip()
        if campo.obrigatorio and not texto:
            raise ValueError(f"O campo obrigatório '{campo.rotulo}' não pode ficar vazio.")
        if campo.opcoes and texto not in campo.opcoes:
            raise ValueError(
                f"Valor inválido para {campo.id}. Opções aceitas: "
                f"{', '.join(campo.opcoes)}."
            )
        return texto

    @staticmethod
    def _converter_proposta(
        proposta: PropostaEdicao | Mapping[str, Any],
    ) -> PropostaEdicao | None:
        if isinstance(proposta, PropostaEdicao):
            return proposta
        if not isinstance(proposta, Mapping):
            return None
        try:
            return PropostaEdicao(
                id=str(proposta["id"]),
                campo_id=str(proposta["campo_id"]),
                valor_anterior=proposta["valor_anterior"],
                novo_valor=proposta["novo_valor"],
                motivo=str(proposta.get("motivo") or ""),
                criada_em=str(proposta["criada_em"]),
            )
        except (KeyError, TypeError, ValueError):
            return None