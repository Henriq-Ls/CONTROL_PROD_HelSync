"""Configuração local do painel de inteligência artificial.

As configurações ficam em PASTA_APPDATA/config/config.json, dentro da chave
``ia``. O QSettings só é consultado uma vez para migrar configurações antigas.
Nenhuma chave ou credencial é embutida no código.
"""

from __future__ import annotations

import json
import uuid
from typing import Any
from urllib.parse import urlsplit

from _APPDATA_ import appdata
from PySide6.QtCore import QSettings


DEFAULT_PHRASES = [
    "Aponte dados ausentes ou conflitantes no cadastro, sem sugerir fatos.",
    "Escreva uma descrição objetiva usando somente os dados do cadastro.",
    "Escreva como o produto pode ser usado usando somente os dados fornecidos.",
]

DEFAULT_CONFIG: dict[str, Any] = {
    "provider": "Ollama",
    "base_url": "http://localhost:11434",
    "model": "llama3.2:3b",
    "api_key": "",
    "system_prompt": (
        "Você é um assistente de apoio ao usuário do Hen Place Control. "
        "Responda em português, de forma concisa, direta e em texto simples, "
        "sem Markdown ou frases de preenchimento. Para texto destinado a um "
        "campo, retorne somente o conteúdo em um parágrafo. Use apenas fatos "
        "explícitos no contexto atual ou informados pelo usuário. Não invente "
        "nem complete características de produtos ou registros; se faltarem "
        "dados ou houver conflito, pergunte em vez de presumir."
    ),
    "phrases": DEFAULT_PHRASES,
}

PROVIDER_OPTIONS = ("Ollama", "OpenRouter", "OpenAI compatível")


def _normalizar_base_url(provider: str, valor: Any, padrao: str) -> str:
    """Converte endereços cadastrados para uma URL HTTP utilizável.

    Configurações antigas podem conter ``openrouter.ai/api/v1`` sem protocolo.
    O cadastro continua aceitando esse formato, mas persiste a forma canônica
    para que o serviço HTTP nunca receba uma URL relativa.
    """
    base = str(valor or "").strip().rstrip("/")
    if not base:
        base = padrao.rstrip("/")

    if "://" not in base:
        protocolo = "http" if provider == "Ollama" else "https"
        base = f"{protocolo}://{base}"

    partes = urlsplit(base)
    if partes.scheme not in {"http", "https"} or not partes.netloc:
        return padrao.rstrip("/")
    return base


def _defaults_for_provider(provider: str) -> dict[str, str]:
    """Retorna os valores iniciais da tela para um tipo de provedor."""
    if provider == "OpenRouter":
        return {
            "name": "OpenRouter",
            "provider": provider,
            "base_url": "https://openrouter.ai/api/v1",
            "model": "openai/gpt-4o-mini",
            "api_key": "",
        }
    if provider == "OpenAI compatível":
        return {
            "name": "OpenAI compatível",
            "provider": provider,
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o-mini",
            "api_key": "",
        }
    return {
        "name": "Ollama local",
        "provider": "Ollama",
        "base_url": "http://localhost:11434",
        "model": "llama3.2:3b",
        "api_key": "",
    }


def novo_provedor(provider: str = "Ollama") -> dict[str, str]:
    """Cria um cadastro novo de IA com um identificador estável."""
    dados = _defaults_for_provider(provider)
    dados["id"] = f"ia-{uuid.uuid4().hex[:10]}"
    return dados


def normalizar_provedor(
    provider: dict[str, Any] | None,
    indice: int = 0,
) -> dict[str, str]:
    """
    Normaliza um cadastro salvo e aceita nomes do formato legado.

    A lista de provedores é deliberadamente simples: a ordem da lista representa
    a prioridade global (posição 0 = primeira tentativa).
    """
    origem = provider if isinstance(provider, dict) else {}
    tipo_original = str(
        origem.get("provider")
        or origem.get("provedor")
        or origem.get("tipo")
        or "Ollama"
    ).strip()
    tipo_legado = tipo_original.lower()
    if tipo_legado in {"rede", "openrouter"}:
        tipo_original = "OpenRouter"
    elif tipo_legado in {"local", "ollama"}:
        tipo_original = "Ollama"
    tipo = tipo_original
    if tipo not in PROVIDER_OPTIONS:
        tipo = "OpenAI compatível" if tipo.lower() not in {"ollama", "openrouter"} else (
            "Ollama" if tipo.lower() == "ollama" else "OpenRouter"
        )

    defaults = _defaults_for_provider(tipo)
    identificador = str(
        origem.get("id") or origem.get("provider_id") or f"ia-{indice + 1}"
    ).strip()
    nome = str(
        origem.get("name")
        or origem.get("nome")
        or defaults["name"]
    ).strip()

    return {
        "id": identificador,
        "name": nome or defaults["name"],
        "provider": tipo,
        "base_url": _normalizar_base_url(
            tipo,
            origem.get("base_url") or origem.get("url"),
            defaults["base_url"],
        ).strip(),
        "model": str(
            origem.get("model")
            or origem.get("modelo")
            or (
                origem.get("modelo_or")
                if tipo == "OpenRouter"
                else origem.get("modelo_ol")
            )
            or defaults["model"]
        ).strip(),
        "api_key": str(
            origem.get("api_key")
            or origem.get("chave")
            or origem.get("chave_rede")
            or origem.get("openrouter_key")
            or ""
        ),
    }


def _normalizar_lista_provedores(
    providers: Any,
    legado: dict[str, Any],
) -> list[dict[str, str]]:
    """Converte a lista nova ou a configuração antiga para o formato atual."""
    if isinstance(providers, list):
        candidatos = providers
    else:
        candidatos = [legado]

    resultado: list[dict[str, str]] = []
    usados: set[str] = set()
    for indice, item in enumerate(candidatos):
        cadastro = normalizar_provedor(item, indice)
        identificador = cadastro["id"]
        if identificador in usados:
            identificador = f"ia-{indice + 1}-{uuid.uuid4().hex[:6]}"
            cadastro["id"] = identificador
        usados.add(identificador)
        resultado.append(cadastro)

    return resultado or [novo_provedor()]


def _ler_config_appdata() -> dict[str, Any]:
    """Garante o AppData e devolve o JSON central do aplicativo."""
    appdata.inicializar()
    dados = appdata.ler_config()
    return dados if isinstance(dados, dict) else {}


def _ler_config_legada() -> dict[str, Any]:
    """Lê o antigo QSettings apenas para uma migração única."""
    settings = QSettings("HenPlaceControl", "InteligenciaArtificial")
    config: dict[str, Any] = {}
    for key in (
        "provider",
        "provedor",
        "tipo",
        "base_url",
        "model",
        "modelo",
        "api_key",
        "chave_rede",
        "system_prompt",
    ):
        value = settings.value(key)
        if value is not None:
            config[key] = str(value)

    raw_phrases = settings.value("phrases")
    if isinstance(raw_phrases, str):
        try:
            parsed = json.loads(raw_phrases)
        except (TypeError, ValueError):
            parsed = []
        if isinstance(parsed, list):
            config["phrases"] = [
                str(item).strip() for item in parsed if str(item).strip()
            ]
    elif isinstance(raw_phrases, list):
        config["phrases"] = [
            str(item).strip() for item in raw_phrases if str(item).strip()
        ]
    return config


def load_config() -> dict[str, Any]:
    """Carrega ``config.json["ia"]`` e migra dados antigos se existirem."""
    dados = _ler_config_appdata()
    ia_salva = dados.get("ia")
    precisa_persistir = not isinstance(ia_salva, dict)
    if precisa_persistir:
        ia_salva = _ler_config_legada()

    config = dict(DEFAULT_CONFIG)
    config["phrases"] = list(DEFAULT_PHRASES)
    config.update(ia_salva)
    config["providers"] = _normalizar_lista_provedores(
        config.get("providers"),
        config,
    )
    # Mantém os campos antigos sincronizados com a primeira IA. O serviço usa
    # providers, mas esses campos preservam compatibilidade com configurações
    # e chamadas legadas.
    principal = config["providers"][0]
    config["provider"] = principal["provider"]
    config["base_url"] = principal["base_url"]
    config["model"] = principal["model"]
    config["api_key"] = principal["api_key"]
    if not isinstance(config.get("phrases"), list):
        config["phrases"] = list(DEFAULT_PHRASES)
    config["phrases"] = [
        str(item).strip() for item in config["phrases"] if str(item).strip()
    ]
    url_ou_lista_corrigida = (
        not isinstance(ia_salva, dict)
        or ia_salva.get("providers") != config["providers"]
        or ia_salva.get("base_url") != config["base_url"]
        or ia_salva.get("provider") != config["provider"]
        or ia_salva.get("model") != config["model"]
    )
    if precisa_persistir or url_ou_lista_corrigida:
        appdata.salvar_config_ia(dict(config))
    return config


def save_config(config: dict[str, Any]) -> None:
    """Salva as configurações da IA em ``PASTA_APPDATA/config/config.json``."""
    frases = config.get("phrases", [])
    providers = _normalizar_lista_provedores(
        config.get("providers"),
        config,
    )
    # A tela de configuração edita os campos legados no nível superior
    # (provider/base_url/model/api_key), enquanto o serviço usa a lista
    # ``providers``. Sincronize os dois formatos antes de persistir; sem isso,
    # o botão Save regravava o provedor antigo e descartava as edições recentes.
    principal = dict(providers[0])
    for campo in ("provider", "base_url", "model", "api_key"):
        if campo in config:
            principal[campo] = config[campo]
    providers[0] = normalizar_provedor(principal, 0)
    principal = providers[0]
    configuracao = {
        # Campos legados mantidos para o ia_service atual.
        "provider": principal["provider"],
        "base_url": principal["base_url"],
        "model": principal["model"],
        "api_key": principal["api_key"],
        "system_prompt": str(config.get("system_prompt", "")),
        "phrases": [
            str(item).strip() for item in frases if str(item).strip()
        ],
        # A ordem da lista é a prioridade configurada pelo usuário.
        "providers": providers,
        "active_provider_id": str(
            config.get("active_provider_id") or principal["id"]
        ),
    }
    appdata.salvar_config_ia(configuracao)