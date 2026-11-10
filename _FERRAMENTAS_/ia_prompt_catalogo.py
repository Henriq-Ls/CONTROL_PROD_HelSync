"""Carregamento do catalogo editavel de prompts por escopo."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any, Mapping

from _APPDATA_ import appdata


_PADRAO = Path(__file__).resolve().parent / "prompts_ia" / "catalogo.json"
_PADRAO_PROMPTS_IMAGEM = (
    Path(__file__).resolve().parent
    / "prompts_ia"
    / "geracao_imagem.json"
)
_MARCADORES_PROMPT_IMAGEM = {
    "[[PRODUTO]]",
    "[[REFERENCIA]]",
    "[[DESCRICAO]]",
    "[[SERVENTIA]]",
    "[[ACABAMENTO]]",
    "[[ALTURA]]",
    "[[LARGURA]]",
    "[[ESPESSURA]]",
    "[[PESO]]",
    "[[IMAGEM_REFERENCIA]]",
}
_MARCADORES_OBRIGATORIOS_POR_PROMPT = {
    "capa": {
        "[[PRODUTO]]",
        "[[DESCRICAO]]",
        "[[ACABAMENTO]]",
    },
    "uso": {
        "[[PRODUTO]]",
        "[[DESCRICAO]]",
        "[[SERVENTIA]]",
        "[[ACABAMENTO]]",
        "[[ALTURA]]",
        "[[LARGURA]]",
        "[[ESPESSURA]]",
    },
    "detalhe": {
        "[[PRODUTO]]",
        "[[DESCRICAO]]",
        "[[ACABAMENTO]]",
    },
}
# Hashes of the previous built-in templates: migrate only untouched copies in
# AppData, leaving user-edited prompt text intact.
_HASHES_PADROES_IMAGEM_ANTERIORES = {
    "capa": {
        "48ad63611c43120922681378125f1000b312a7f50c531ce32ef5556bf0544381",
        "4060f453cae166753a49774e3069b324def7f787b7680fb5c029157111b3d68d",
        "0178b507b19fbef3a8fbafc4d0185adad050379a8c1cb05cfc5922c7036b0e02",
        "72c0fc0d8c055efca17898b736538b73ccccf5bdd94d20e94f23eedfd0535ac6",
        "e6baad7c974859f4deca66aa746a8df633894efd733f95bff35f75a68f070a19",
    },
    "uso": {
        "5a4bf84260a80c4fc4bd05904ad68c603cbac094b2f7d3988b4aed94071cbf24",
        "05c0ef1bc19f5a23785ed113f317bb62aa230d92b89934a10e7727ffd47a0d1e",
        "39bee2ba3e5667496fdcd8c08eaaba3a9d3a8ab6c2a13140ed2f895ba235ee9b",
        "cb13debe57954a4f4190791a2e20e3aab4d6219b2b9cbfbfe190061f193512fa",
        "131cdc8efc581a0ba3ba4e229916509fd35ab7a8d503b43fefdcd68e6491947b",
    },
    "detalhe": {
        "3c22bd0ad47f58205b0762c8617ea8bc22d94945e7b3040688a41bcb0f166f65",
        "af24458dfd336f04e63d3f2b342cee9aa453240050701df423c720b864e4096d",
        "22ec6c10752b52b6b5a77915b51684ec61022311ae68a41dce3392a86b2559db",
        "4a13761aeff85e6cb380e55133489255aaefd3313353fef3d82c263d35e207fd",
        "a784a01daa63f1d0cf58f612ef61367ca23c37f969b883d84267a4d3e7590e80",
    },
}


def _arquivo_catalogo() -> Path:
    pasta = Path(appdata.pasta_raiz) / "IAs" / "prompts"
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / "catalogo.json"
    if not destino.exists() and _PADRAO.exists():
        shutil.copy2(_PADRAO, destino)
    return destino


def carregar_catalogo() -> list[dict[str, Any]]:
    caminho = _arquivo_catalogo()
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return []
    if not isinstance(dados, list):
        return []
    itens = [dict(item) for item in dados if isinstance(item, Mapping)]
    escopos_existentes = {
        str(item.get("escopo") or "").strip().casefold()
        for item in itens
        if str(item.get("escopo") or "").strip()
    }

    # Mostra e disponibiliza prompts dos escopos novos sem substituir os
    # prompts personalizados que já existam no catálogo do AppData.
    try:
        padroes = json.loads(_PADRAO.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return itens
    if not isinstance(padroes, list):
        return itens
    for item in padroes:
        if not isinstance(item, Mapping):
            continue
        escopo = str(item.get("escopo") or "").strip()
        chave = escopo.casefold()
        if escopo and chave not in escopos_existentes:
            itens.append(dict(item))
            escopos_existentes.add(chave)
    return itens


def salvar_catalogo(itens: list[Mapping[str, Any]]) -> None:
    caminho = _arquivo_catalogo()
    temporario = caminho.with_suffix(".json.tmp")
    temporario.write_text(
        json.dumps([dict(item) for item in itens], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporario.replace(caminho)


def salvar_prompt(prompt: Mapping[str, Any]) -> None:
    prompt_id = str(prompt.get("id") or "").strip()
    if not prompt_id:
        return
    itens = carregar_catalogo()
    atualizado = False
    for indice, item in enumerate(itens):
        if str(item.get("id") or "").strip() == prompt_id:
            itens[indice] = dict(prompt)
            atualizado = True
            break
    if not atualizado:
        itens.append(dict(prompt))
    salvar_catalogo(itens)


def prompt_do_escopo(escopo: str) -> str:
    alvo = str(escopo or "").strip().casefold()
    for item in carregar_catalogo():
        if str(item.get("escopo") or "").strip().casefold() == alvo:
            return str(item.get("texto") or "").strip()

    # A configuração em AppData pode ter sido criada antes de um novo escopo
    # existir no catálogo padrão. Use o padrão como fallback, sem sobrescrever
    # nem migrar as personalizações salvas pelo usuário.
    try:
        padroes = json.loads(_PADRAO.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return ""
    if not isinstance(padroes, list):
        return ""
    for item in padroes:
        if (
            isinstance(item, Mapping)
            and str(item.get("escopo") or "").strip().casefold() == alvo
        ):
            return str(item.get("texto") or "").strip()
    return ""


def _arquivo_prompts_imagem() -> Path:
    pasta = Path(appdata.pasta_raiz) / "IAs" / "prompts"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta / "geracao_imagem.json"


def carregar_prompts_imagem_padrao() -> dict[str, str]:
    """Carrega os modelos versionados usados para preparar prompts de imagem."""
    try:
        dados = json.loads(
            _PADRAO_PROMPTS_IMAGEM.read_text(encoding="utf-8")
        )
    except (OSError, TypeError, ValueError) as exc:
        raise ValueError(
            "Os modelos padrão de geração de imagem não puderam ser lidos."
        ) from exc
    if not isinstance(dados, dict):
        raise ValueError(
            "O arquivo padrão de geração de imagem deve conter um objeto JSON."
        )
    prompts = {
        str(chave): texto
        for chave, texto in dados.items()
        if isinstance(texto, str)
    }
    obrigatorios = {"capa", "uso", "detalhe"}
    if not obrigatorios.issubset(prompts):
        raise ValueError(
            "O arquivo padrão precisa conter os prompts capa, uso e detalhe."
        )
    return prompts


def _gravar_prompts_imagem(
    caminho: Path,
    dados: Mapping[str, Any],
) -> None:
    temporario = caminho.with_suffix(".json.tmp")
    temporario.write_text(
        json.dumps(dict(dados), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporario.replace(caminho)


def carregar_prompts_imagem() -> dict[str, str]:
    """Carrega padrões e personalizações do usuário sem misturar o catálogo de chat."""
    padroes = carregar_prompts_imagem_padrao()
    caminho = _arquivo_prompts_imagem()
    if not caminho.exists():
        _gravar_prompts_imagem(caminho, padroes)
        return dict(padroes)

    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError) as exc:
        raise ValueError(
            "O arquivo de prompts de imagem salvo no AppData não pôde ser lido."
        ) from exc
    if not isinstance(dados, dict):
        raise ValueError(
            "O arquivo de prompts de imagem do AppData deve conter um objeto JSON."
        )

    salvos = {
        str(chave): texto
        for chave, texto in dados.items()
        if isinstance(texto, str)
    }
    migrados = {}
    for chave, hashes_anteriores in _HASHES_PADROES_IMAGEM_ANTERIORES.items():
        texto_salvo = salvos.get(chave)
        if (
            isinstance(texto_salvo, str)
            and hashlib.sha256(texto_salvo.encode("utf-8")).hexdigest()
            in hashes_anteriores
        ):
            salvos[chave] = padroes[chave]
            migrados[chave] = padroes[chave]

    if migrados:
        dados_atualizados = dict(dados)
        dados_atualizados.update(migrados)
        try:
            _gravar_prompts_imagem(caminho, dados_atualizados)
        except OSError:
            # A preparação do prompt continua com os modelos novos em memória;
            # o salvamento da migração pode ser tentado no próximo carregamento.
            pass

    prompts = dict(padroes)
    prompts.update(salvos)
    return prompts


def salvar_prompt_imagem(prompt_id: str, texto: str) -> None:
    """Salva um dos modelos de imagem sem sobrescrever os demais."""
    chave = str(prompt_id or "").strip()
    padroes = carregar_prompts_imagem_padrao()
    if chave not in padroes:
        raise ValueError("Tipo de prompt de imagem desconhecido.")
    texto_prompt = str(texto).strip()
    if not texto_prompt:
        raise ValueError("O prompt não pode ficar vazio.")
    marcadores_encontrados = set(
        re.findall(r"\[\[[A-Z_]+\]\]", texto_prompt)
    )
    desconhecidos = marcadores_encontrados - _MARCADORES_PROMPT_IMAGEM
    if desconhecidos:
        raise ValueError(
            "O modelo usa marcadores não aceitos: "
            + ", ".join(sorted(desconhecidos))
        )
    faltantes = (
        _MARCADORES_OBRIGATORIOS_POR_PROMPT[chave]
        - marcadores_encontrados
    )
    if faltantes:
        raise ValueError(
            "Mantenha no modelo os campos obrigatórios para este tipo de "
            "imagem: " + ", ".join(sorted(faltantes))
        )

    caminho = _arquivo_prompts_imagem()
    dados: dict[str, Any] = dict(padroes)
    if caminho.exists():
        try:
            existentes = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError) as exc:
            raise ValueError(
                "O arquivo salvo de prompts de imagem está inválido; "
                "não foi sobrescrito."
            ) from exc
        if not isinstance(existentes, dict):
            raise ValueError(
                "O arquivo salvo de prompts de imagem tem formato inválido; "
                "não foi sobrescrito."
            )
        dados.update(
            {
                str(chave_existente): valor
                for chave_existente, valor in existentes.items()
                if isinstance(valor, str)
            }
        )

    dados[chave] = texto_prompt
    _gravar_prompts_imagem(caminho, dados)


def _arquivo_referencias() -> Path:
    pasta = Path(appdata.pasta_raiz) / "IAs" / "prompts"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta / "referencias.json"


def _gravar_referencias(caminho: Path, dados: Mapping[str, Any]) -> None:
    temporario = caminho.with_suffix(".json.tmp")
    temporario.write_text(
        json.dumps(dict(dados), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporario.replace(caminho)


def _arquivo_sistema() -> Path:
    pasta = Path(appdata.pasta_raiz) / "IAs" / "prompts"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta / "sistema.json"


def _gravar_sistema(caminho: Path, dados: Mapping[str, Any]) -> None:
    temporario = caminho.with_suffix(".json.tmp")
    temporario.write_text(
        json.dumps(dict(dados), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporario.replace(caminho)


def carregar_prompts_sistema(
    padroes: Mapping[str, str],
) -> dict[str, Any]:
    """Carrega o mapa independente de prompts usados pelo sistema."""
    defaults = {str(chave): str(texto) for chave, texto in padroes.items()}
    try:
        caminho = _arquivo_sistema()
        if not caminho.exists():
            _gravar_sistema(caminho, defaults)
            return defaults
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return defaults

    if not isinstance(dados, dict):
        return defaults
    return dados


def salvar_prompt_sistema(
    prompt_id: str,
    texto: str,
    padroes: Mapping[str, str],
) -> None:
    """Atualiza uma chave sem descartar outras chaves futuras do arquivo."""
    chave = str(prompt_id or "").strip()
    if not chave:
        return

    defaults = {str(key): str(value) for key, value in padroes.items()}
    caminho = _arquivo_sistema()
    dados: dict[str, Any] = dict(defaults)
    if caminho.exists():
        try:
            existentes = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            existentes = None
        if isinstance(existentes, dict):
            dados = dict(existentes)

    dados[chave] = str(texto)
    _gravar_sistema(caminho, dados)


def carregar_referencias(padroes: Mapping[str, str]) -> dict[str, Any]:
    defaults = {str(chave): str(texto) for chave, texto in padroes.items()}
    try:
        caminho = _arquivo_referencias()
        if not caminho.exists():
            _gravar_referencias(caminho, defaults)
            return defaults
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return defaults

    if not isinstance(dados, dict):
        return defaults
    return dados


def salvar_referencia(
    prompt_id: str,
    texto: str,
    padroes: Mapping[str, str],
) -> None:
    chave = str(prompt_id or "").strip()
    if not chave:
        return
    dados = carregar_referencias(padroes)
    dados[chave] = str(texto)
    _gravar_referencias(_arquivo_referencias(), dados)
