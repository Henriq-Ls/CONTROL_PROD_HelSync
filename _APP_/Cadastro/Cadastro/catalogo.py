"""Opções dinâmicas do Cadastro, persistidas na configuração do AppData."""

from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

from _APPDATA_ import appdata


CHAVE_CATALOGO = "catalogo_cadastro"
CATALOGO_PADRAO = {
    "acompanha": [],
    "acabamentos": [
        "Lixado",
        "Lavado",
        "Envernizado",
        "Impressão a laser",
    ],
    "regras_anuncio": [],
}


def novo_id_regra() -> str:
    return uuid4().hex


def _normalizar_opcoes(valor: object, padrao: list[str]) -> list[str]:
    if not isinstance(valor, list):
        valor = padrao
    resultado: list[str] = []
    vistos: set[str] = set()
    for item in valor:
        texto = str(item or "").strip()
        chave = texto.casefold()
        if texto and chave not in vistos:
            vistos.add(chave)
            resultado.append(texto)
    return resultado


def _normalizar_regras(valor: object) -> list[dict[str, str]]:
    if not isinstance(valor, list):
        return []
    resultado: list[dict[str, str]] = []
    ids: set[str] = set()
    for item in valor:
        if not isinstance(item, dict):
            continue
        regra_id = str(item.get("id") or "").strip()
        titulo = str(item.get("titulo") or "").strip()
        if not regra_id or not titulo or regra_id in ids:
            continue
        ids.add(regra_id)
        resultado.append(
            {
                "id": regra_id,
                "titulo": titulo,
                "descricao": str(item.get("descricao") or "").strip(),
            }
        )
    return resultado


def normalizar_catalogo(valor: object) -> dict[str, object]:
    dados = valor if isinstance(valor, dict) else {}
    return {
        "acompanha": _normalizar_opcoes(
            dados.get("acompanha"),
            CATALOGO_PADRAO["acompanha"],
        ),
        "acabamentos": _normalizar_opcoes(
            dados.get("acabamentos"),
            CATALOGO_PADRAO["acabamentos"],
        ),
        "regras_anuncio": _normalizar_regras(
            dados.get("regras_anuncio")
        ),
    }


def carregar_catalogo_cadastro() -> dict[str, object]:
    appdata.inicializar()
    configuracao = appdata.ler_config()
    return normalizar_catalogo(configuracao.get(CHAVE_CATALOGO))


def salvar_catalogo_cadastro(catalogo: object) -> bool:
    appdata.inicializar()
    configuracao = appdata.ler_config()
    configuracao[CHAVE_CATALOGO] = normalizar_catalogo(catalogo)
    return appdata.salvar_config(configuracao)


def regras_por_ids(
    catalogo: object,
    ids: list[object],
) -> list[dict[str, str]]:
    dados = normalizar_catalogo(catalogo)
    regras = dados["regras_anuncio"]
    por_id = {
        regra["id"]: regra
        for regra in regras
        if isinstance(regra, dict)
    }
    resultado: list[dict[str, str]] = []
    for regra_id in ids:
        regra = por_id.get(str(regra_id))
        if regra is not None:
            resultado.append(deepcopy(regra))
    return resultado
