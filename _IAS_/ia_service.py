"""Chamadas simples aos provedores de IA usadas pelo painel de chat.

Usa apenas a biblioteca padrão para que o painel possa funcionar sem instalar
um novo cliente Python. Ollama e endpoints compatíveis com OpenAI respondem
através de HTTP.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from _LOGS_ import log

from .ia_config import normalizar_provedor


ProgressCallback = Callable[[str], None]


def _sem_acentos(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(
        caractere
        for caractere in normalizado
        if not unicodedata.combining(caractere)
    )


def _remover_rotulos_seguranca(texto: str) -> str:
    """Remove o cabeçalho interno de classificação caso o modelo o exponha."""
    padrao = re.compile(
        r"^\s*User\s+Safety\s*:\s*(?:safe|unsafe)(?:\s+|[,;|]\s*)"
        r"Response\s+Safety\s*:\s*(?:safe|unsafe)\s*(?:[-:–—]\s*)?",
        re.IGNORECASE,
    )
    return padrao.sub("", str(texto or ""), count=1).strip()


def _texto_da_mensagem(conteudo: Any) -> str:
    if isinstance(conteudo, str):
        return conteudo
    if isinstance(conteudo, list):
        return "\n".join(
            str(item.get("text") or item.get("content") or "")
            for item in conteudo
            if isinstance(item, dict)
        )
    return str(conteudo or "")


def _usuario_pediu_json(messages: list[dict[str, Any]]) -> bool:
    texto_usuario = next(
        (
            _sem_acentos(_texto_da_mensagem(item.get("content")))
            for item in reversed(messages)
            if item.get("role") == "user"
        ),
        "",
    )
    if not texto_usuario:
        return False
    if re.search(
        r"\b(?:nao|nunca|sem|evite)\b.{0,40}\bjson\b",
        texto_usuario,
    ):
        return False
    padroes = (
        r"\b(?:em|como|no formato de|formato de|formato)\s+(?:um\s+)?json\b",
        r"\b(?:responda|retorne|gere|produza|entregue|devolva|escreva|mande)"
        r"\s+(?:(?:somente|apenas)\s+)?(?:um\s+)?json\b",
        r"\b(?:somente|apenas)\s+json\b",
        r"\bjson\s+(?:valido|puro)\b",
    )
    return any(re.search(padrao, texto_usuario) for padrao in padroes)


def _rotulo_legivel(chave: object) -> str:
    texto = re.sub(r"[_-]+", " ", str(chave or "")).strip()
    return texto[:1].upper() + texto[1:] if texto else "Informação"


def _valor_legivel(valor: Any, profundidade: int = 0) -> str:
    if valor is None:
        return "não informado"
    if isinstance(valor, bool):
        return "Sim" if valor else "Não"
    if isinstance(valor, dict):
        if profundidade >= 2:
            return "informações adicionais"
        partes = [
            f"{_rotulo_legivel(chave)}: "
            f"{_valor_legivel(item, profundidade + 1)}"
            for chave, item in list(valor.items())[:8]
        ]
        return "; ".join(partes) or "sem detalhes"
    if isinstance(valor, list):
        partes = [
            _valor_legivel(item, profundidade + 1)
            for item in valor[:8]
        ]
        return "; ".join(parte for parte in partes if parte) or "nenhum item"
    return str(valor).strip() or "vazio"


def _resposta_json_em_texto(texto: str) -> str:
    """Evita exibir JSON acidental como resposta normal do chat."""
    original = str(texto or "").strip()
    if not original:
        return original

    candidato = original
    bloco = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        candidato,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if bloco:
        candidato = bloco.group(1).strip()

    if not candidato.startswith(("{", "[")):
        return original
    try:
        dados = json.loads(candidato)
    except json.JSONDecodeError:
        return (
            "A resposta veio incompleta em formato estruturado. "
            "Peça novamente em texto natural."
        )

    if isinstance(dados, str):
        return dados.strip() or "A IA não retornou conteúdo."
    if isinstance(dados, bool):
        return "Sim." if dados else "Não."
    if dados is None:
        return "A IA não retornou conteúdo."
    if isinstance(dados, dict):
        chaves_textuais = {
            "resposta",
            "answer",
            "message",
            "mensagem",
            "texto",
            "text",
            "content",
            "output",
        }
        if len(dados) == 1:
            chave, valor = next(iter(dados.items()))
            if str(chave).casefold() in chaves_textuais and isinstance(valor, str):
                return valor.strip() or "A IA não retornou conteúdo."
        linhas = [
            f"{_rotulo_legivel(chave)}: {_valor_legivel(valor)}"
            for chave, valor in list(dados.items())[:20]
        ]
        return "\n".join(linhas)[:6000] or "A IA não retornou conteúdo."
    if isinstance(dados, list):
        linhas = [
            f"{indice}. {_valor_legivel(item)}"
            for indice, item in enumerate(dados[:20], start=1)
        ]
        return "\n".join(linhas)[:6000] or "A IA não retornou conteúdo."
    return _valor_legivel(dados)


@dataclass(frozen=True)
class ChamadaFerramenta:
    """Chamada normalizada recebida de um provedor compatível."""

    id: str
    nome: str
    argumentos: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RespostaIA:
    """Resposta textual ou chamada estruturada de ferramenta."""

    texto: str
    chamadas_ferramenta: tuple[ChamadaFerramenta, ...] = ()
    provedor: str = ""
    modelo: str = ""


def _url_complementar(base_url: str, sufixo: str) -> str:
    base = base_url.strip().rstrip("/")
    if "://" not in base:
        protocolo = "http" if sufixo == "/api/chat" else "https"
        base = f"{protocolo}://{base}"
    partes = urlsplit(base)
    if partes.scheme not in {"http", "https"} or not partes.netloc:
        raise ValueError(f"Endereço inválido para o provedor: {base_url!r}")
    if base.endswith(sufixo):
        return base
    return f"{base}{sufixo}"


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urlopen(request, timeout=180) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        detalhe = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Servidor respondeu HTTP {exc.code}: {_detalhe_erro_http(detalhe)}"
        ) from exc
    except URLError as exc:
        raise RuntimeError(f"Não foi possível conectar ao provedor: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError("O provedor demorou demais para responder.") from exc

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("O provedor retornou uma resposta inválida.") from exc
    if not isinstance(result, dict):
        raise RuntimeError("O provedor retornou um formato inesperado.")
    return result


def _sanitizar_detalhe(texto: Any, limite: int = 500) -> str:
    """Limita detalhes do provedor e mascara credenciais antes de exibi-los/logá-los."""
    valor = " ".join(str(texto or "").split())
    valor = re.sub(r"(?i)\bBearer\s+[^\s,;]+", "Bearer [redigido]", valor)
    valor = re.sub(
        r"(?i)(https?://)[^/\s:@]+:[^/@\s]+@",
        r"\1[redigido]@",
        valor,
    )
    valor = re.sub(
        r"\bsk-(?:or-v1-)?[A-Za-z0-9_-]{12,}\b",
        "[chave redigida]",
        valor,
    )
    valor = re.sub(
        r"(?i)([?&](?:api[_-]?key|token|key|secret|password|authorization)=)"
        r"[^&#\s]+",
        r"\1[redigido]",
        valor,
    )
    valor = re.sub(
        r"""(?i)(["']?(?:api[_-]?key|token|secret|password|authorization)["']?\s*[:=]\s*["']?)[^"',\s}]+""",
        r"\1[redigido]",
        valor,
    )
    return valor[:limite]


def _detalhe_erro_http(corpo: str) -> str:
    """Extrai somente a mensagem útil de um erro HTTP, sem registrar o payload inteiro."""
    try:
        resposta = json.loads(corpo)
    except (TypeError, ValueError):
        resposta = None
    if isinstance(resposta, dict):
        erro = resposta.get("error")
        if isinstance(erro, dict):
            mensagem = erro.get("message") or erro.get("detail") or erro.get("code")
            if mensagem:
                return _sanitizar_detalhe(mensagem)
        elif erro:
            return _sanitizar_detalhe(erro)
        mensagem = resposta.get("message")
        if mensagem:
            return _sanitizar_detalhe(mensagem)
    return _sanitizar_detalhe(corpo) or "corpo vazio"


def _classificar_erro_usuario(
    detalhe: Any,
) -> tuple[str, str, str, str]:
    """Classifica a falha e sugere uma ação sem expor credenciais."""
    seguro = _sanitizar_detalhe(detalhe, limite=700)
    normalizado = _sem_acentos(seguro)

    if not seguro:
        return (
            "Falha sem detalhe",
            "O provedor não informou a causa da falha.",
            "Abra Logs para consultar o diagnóstico disponível e tente novamente.",
            "",
        )
    if (
        "chave da api nao informada" in normalizado
        or "api key is missing" in normalizado
    ):
        return (
            "Chave da API ausente",
            "A chave de acesso deste provedor não está configurada.",
            "Abra Configurações da IA e confira a chave. Não envie a chave pelo chat.",
            seguro,
        )
    if (
        "modelo nao informado" in normalizado
        or "endereco do provedor nao informado" in normalizado
        or "endereco invalido para o provedor" in normalizado
    ):
        return (
            "Configuração incompleta",
            "Falta configurar corretamente o modelo ou o endereço do provedor.",
            "Abra Configurações da IA, confira o provedor, o endereço e o nome do modelo.",
            seguro,
        )
    if "finish_reason=length" in normalizado or "limite de saida" in normalizado:
        return (
            "Limite de resposta atingido",
            "O provedor encerrou a geração por limite de saída antes de entregar texto visível.",
            "Tente uma pergunta mais curta ou outro modelo. Se persistir, consulte Logs para ajustar o limite de saída.",
            seguro,
        )
    if any(
        termo in normalizado
        for termo in (
            "sem conteudo de texto",
            "stream sem texto",
            "sem enviar um evento de resposta legivel",
        )
    ):
        return (
            "Provedor encerrou sem texto",
            "O provedor terminou a chamada sem enviar uma resposta de texto que o painel consiga mostrar.",
            "Tente novamente. Se acontecer de novo, consulte Logs ou teste outro modelo/provedor.",
            seguro,
        )

    codigo_http = re.search(r"\bhttp\s+(\d{3})\b", normalizado)
    codigo = int(codigo_http.group(1)) if codigo_http else 0
    if codigo in {401, 403}:
        return (
            "Acesso recusado pelo provedor",
            f"O provedor recusou a autenticação ou o acesso (HTTP {codigo}).",
            "Confira a chave e se ela pertence a este provedor/modelo em Configurações. Não compartilhe a chave.",
            seguro,
        )
    if codigo == 402 or any(
        termo in normalizado
        for termo in ("insufficient_quota", "sem creditos", "saldo insuficiente")
    ):
        return (
            "Cota ou saldo do provedor",
            "O provedor recusou a chamada por cota, saldo ou plano.",
            "Confira os limites e o saldo diretamente na conta do provedor.",
            seguro,
        )
    if codigo == 429:
        return (
            "Limite temporário do provedor",
            "O provedor está limitando solicitações neste momento.",
            "Aguarde um pouco e tente novamente; se continuar, confira a cota ou use outro provedor.",
            seguro,
        )
    if codigo in {408, 504}:
        return (
            "Tempo de resposta excedido",
            f"O provedor não concluiu a chamada a tempo (HTTP {codigo}).",
            "Tente novamente; se repetir, confira a conexão ou use outro provedor.",
            seguro,
        )
    if 500 <= codigo <= 599:
        return (
            "Falha no serviço do provedor",
            f"O serviço do provedor retornou um erro HTTP {codigo}.",
            "Aguarde e tente novamente ou use outro provedor.",
            seguro,
        )
    if 400 <= codigo <= 499:
        return (
            "Solicitação recusada pelo provedor",
            f"O provedor recusou a solicitação (HTTP {codigo}).",
            "Confira o modelo e tente uma mensagem mais curta; veja o detalhe abaixo.",
            seguro,
        )
    if (
        "demorou demais para responder" in normalizado
        or "timed out" in normalizado
        or "timeout" in normalizado
    ):
        return (
            "Tempo de resposta excedido",
            "O provedor demorou demais para responder.",
            "Confira a conexão e tente novamente; se repetir, teste outro provedor.",
            seguro,
        )
    if any(
        termo in normalizado
        for termo in (
            "nao foi possivel conectar",
            "connection refused",
            "connection reset",
            "network is unreachable",
            "getaddrinfo",
            "name or service not known",
            "failed to establish a new connection",
        )
    ):
        return (
            "Falha de conexão",
            "O aplicativo não conseguiu alcançar o provedor.",
            "Confira a internet e o endereço do provedor em Configurações; depois tente novamente.",
            seguro,
        )
    if "resposta invalida" in normalizado or "formato inesperado" in normalizado:
        return (
            "Resposta inválida do provedor",
            "O provedor respondeu em um formato que o aplicativo não reconhece.",
            "Tente novamente ou selecione outro modelo/provedor; consulte Logs se persistir.",
            seguro,
        )

    return (
        "Falha não identificada",
        "O aplicativo recebeu uma falha, mas não conseguiu determinar a causa.",
        "Confira o detalhe técnico abaixo e consulte Logs. Não compartilhe chaves ou credenciais.",
        seguro,
    )


def formatar_erro_usuario(erro: Any) -> tuple[str, str]:
    """Gera status curto e explicação visível, com causa e próximo passo."""
    linhas = [
        str(linha).strip()
        for linha in str(erro or "").splitlines()
        if str(linha).strip()
    ]
    if not linhas:
        linhas = ["O provedor não informou detalhes do erro."]

    cabecalho = _sem_acentos(linhas[0])
    if cabecalho.startswith("nenhuma ia cadastrada respondeu"):
        tentativas: list[tuple[str, str, str, str, str]] = []
        for indice, linha in enumerate(linhas[1:], start=1):
            item = linha.lstrip("- ").strip()
            if not item:
                continue
            identificacao, separador, detalhe = item.partition(": ")
            if not separador:
                identificacao = f"Provedor {indice}"
                detalhe = item
            identificacao = _sanitizar_detalhe(identificacao, limite=180)
            status, causa, proximo_passo, detalhe_seguro = _classificar_erro_usuario(
                detalhe
            )
            tentativas.append(
                (identificacao, status, causa, proximo_passo, detalhe_seguro)
            )

        if not tentativas:
            return (
                "Nenhum provedor configurado",
                "Nenhum provedor de IA está configurado ou ativo.\n\n"
                "Abra Configurações da IA, cadastre um provedor e confira o modelo.",
            )

        if len(tentativas) == 1:
            identificacao, status, causa, proximo_passo, detalhe = tentativas[0]
            mensagem = (
                "A IA não conseguiu responder.\n\n"
                f"Provedor/modelo: {identificacao}\n"
                f"Causa: {causa}\n"
                f"Próximo passo: {proximo_passo}"
            )
            if detalhe:
                mensagem += f"\n\nDetalhe técnico seguro: {detalhe}"
            return status, mensagem

        partes = [
            "Nenhum dos provedores cadastrados conseguiu responder.",
            "",
        ]
        for identificacao, _status, causa, proximo_passo, detalhe in tentativas:
            parte = (
                f"{identificacao}\n"
                f"Causa: {causa}\n"
                f"Próximo passo: {proximo_passo}"
            )
            if detalhe:
                parte += f"\nDetalhe técnico seguro: {detalhe}"
            partes.append(parte)
        return (
            f"Falha em todos os provedores ({len(tentativas)} tentativas)",
            "\n\n".join(partes)[:5000],
        )

    status, causa, proximo_passo, detalhe = _classificar_erro_usuario(
        "\n".join(linhas)
    )
    mensagem = (
        "A IA não conseguiu responder.\n\n"
        f"Causa: {causa}\n"
        f"Próximo passo: {proximo_passo}"
    )
    if detalhe:
        mensagem += f"\n\nDetalhe técnico seguro: {detalhe}"
    return status, mensagem


def _payloads_stream(corpo: str, sse: bool) -> list[str]:
    """Separa eventos SSE, JSON único ou linhas NDJSON sem expor o conteúdo."""
    texto = corpo.strip()
    if not texto:
        return []
    if not sse:
        try:
            json.loads(texto)
        except json.JSONDecodeError:
            return [linha.strip() for linha in texto.splitlines() if linha.strip()]
        return [texto]

    payloads: list[str] = []
    dados: list[str] = []
    for linha in corpo.splitlines():
        linha = linha.rstrip("\r")
        if not linha:
            if dados:
                payloads.append("\n".join(dados))
                dados.clear()
            continue
        if linha.startswith(":"):
            continue
        campo, separador, valor = linha.partition(":")
        if campo == "data" and separador:
            dados.append(valor.lstrip())
        elif campo in {"event", "id", "retry"} and separador:
            continue
        elif not separador:
            if dados:
                payloads.append("\n".join(dados))
                dados.clear()
            payloads.append(linha)
    if dados:
        payloads.append("\n".join(dados))
    return payloads


def _payloads_sse_incremental(
    response: Any,
) -> Iterator[tuple[str, int]]:
    """Entrega cada evento SSE assim que chega, sem acumular o stream inteiro."""
    dados: list[str] = []
    bytes_evento = 0
    for linha_bruta in response:
        if isinstance(linha_bruta, bytes):
            bytes_linha = linha_bruta
            linha = linha_bruta.decode("utf-8", errors="replace")
        else:
            linha = str(linha_bruta)
            bytes_linha = linha.encode("utf-8")
        bytes_evento += len(bytes_linha)
        linha = linha.rstrip("\r\n")
        if not linha:
            yield "\n".join(dados), bytes_evento
            dados.clear()
            bytes_evento = 0
            continue
        if linha.startswith(":"):
            continue
        campo, separador, valor = linha.partition(":")
        if campo == "data" and separador:
            dados.append(valor.lstrip())
        elif campo in {"event", "id", "retry"} and separador:
            continue
        elif not separador:
            dados.append(linha)
    if dados or bytes_evento:
        yield "\n".join(dados), bytes_evento


def _erro_evento_stream(item: dict[str, Any]) -> str:
    erro: Any = item.get("error")
    resposta = item.get("response")
    if erro is None and isinstance(resposta, dict):
        erro = resposta.get("error")
    tipo = str(item.get("type") or "").casefold()
    if erro is None and tipo in {"error", "response.failed"}:
        erro = item
    if not erro:
        return ""
    if isinstance(erro, dict):
        detalhe = erro.get("message") or erro.get("detail") or erro.get("code")
    else:
        detalhe = erro
    return _sanitizar_detalhe(detalhe) or "erro sem descrição"


def _texto_conteudo(valor: Any) -> str:
    if isinstance(valor, str):
        return valor
    if isinstance(valor, list):
        trechos: list[str] = []
        for parte in valor:
            if isinstance(parte, str):
                trechos.append(parte)
            elif isinstance(parte, dict):
                texto = parte.get("text") or parte.get("content")
                if isinstance(texto, str):
                    trechos.append(texto)
        return "".join(trechos)
    return ""


def _texto_e_motivo_evento(
    item: dict[str, Any],
    provider: str,
) -> tuple[str, str]:
    """Normaliza delta SSE, resposta JSON final e as variantes do Ollama."""
    if provider == "ollama":
        mensagem = item.get("message")
        texto = (
            _texto_conteudo(mensagem.get("content"))
            if isinstance(mensagem, dict)
            else ""
        )
        if not texto:
            texto = _texto_conteudo(item.get("response"))
        motivo = str(item.get("done_reason") or "")
        if not motivo and item.get("done"):
            motivo = "stop"
        return texto, motivo

    escolhas = item.get("choices")
    if isinstance(escolhas, list) and escolhas and isinstance(escolhas[0], dict):
        escolha = escolhas[0]
        delta = escolha.get("delta")
        mensagem = escolha.get("message")
        texto = (
            _texto_conteudo(delta.get("content"))
            if isinstance(delta, dict)
            else ""
        )
        if not texto and isinstance(mensagem, dict):
            texto = _texto_conteudo(mensagem.get("content"))
        if not texto:
            texto = _texto_conteudo(escolha.get("text"))
        if not texto:
            texto = _texto_conteudo(
                (delta or {}).get("refusal")
                if isinstance(delta, dict)
                else (mensagem or {}).get("refusal")
                if isinstance(mensagem, dict)
                else ""
            )
        motivo = str(escolha.get("finish_reason") or "")
        return texto, motivo

    return (
        _texto_conteudo(item.get("output_text") or item.get("content")),
        str(item.get("finish_reason") or ""),
    )


def _post_stream(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    provider: str,
    on_piece: Callable[[str], None],
) -> str:
    """Lê os formatos de streaming do Ollama e da API compatível com OpenAI."""
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    partes: list[str] = []
    eventos = 0
    payloads_invalidos = 0
    motivo_final = ""
    content_type = ""
    bytes_recebidos = 0

    def processar_payload(payload_text: str) -> None:
        nonlocal eventos, payloads_invalidos, motivo_final
        if payload_text.strip() == "[DONE]":
            return
        try:
            item = json.loads(payload_text)
        except json.JSONDecodeError:
            payloads_invalidos += 1
            return
        if not isinstance(item, dict):
            payloads_invalidos += 1
            return
        eventos += 1
        erro = _erro_evento_stream(item)
        if erro:
            raise RuntimeError(f"O provedor informou um erro: {erro}")

        piece, motivo = _texto_e_motivo_evento(item, provider)
        if motivo:
            motivo_final = _sanitizar_detalhe(motivo, limite=80)
        if piece:
            partes.append(piece)
            on_piece(piece)

    try:
        with urlopen(request, timeout=60) as response:
            content_type = str(
                response.headers.get("Content-Type", "")
            ).split(";", 1)[0].strip().lower()
            if "text/event-stream" in content_type:
                for payload_text, bytes_evento in _payloads_sse_incremental(response):
                    bytes_recebidos += bytes_evento
                    if payload_text:
                        processar_payload(payload_text)
            else:
                corpo = response.read()
                bytes_recebidos += len(corpo)
                texto_corpo = corpo.decode("utf-8", errors="replace")
                for payload_text in _payloads_stream(texto_corpo, sse=False):
                    processar_payload(payload_text)
    except HTTPError as exc:
        detalhe = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Servidor respondeu HTTP {exc.code}: {_detalhe_erro_http(detalhe)}"
        ) from exc
    except URLError as exc:
        raise RuntimeError(f"Não foi possível conectar ao provedor: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError("O provedor demorou demais para responder.") from exc

    resposta = "".join(partes).strip()
    if not resposta:
        diagnostico = (
            f"eventos={eventos}; payloads_invalidos={payloads_invalidos}; "
            f"content_type={content_type or 'não informado'}; "
            f"finish_reason={motivo_final or 'não informado'}"
        )
        log.aviso(
            "IA",
            "_post_stream",
            (
                f"stream sem texto; provedor={provider!r}; "
                f"bytes={bytes_recebidos}; {diagnostico}"
            ),
        )
        if eventos == 0:
            raise RuntimeError(
                "O provedor encerrou a transmissão sem enviar um evento de "
                f"resposta legível ({diagnostico})."
            )
        raise RuntimeError(
            "O provedor concluiu a transmissão sem conteúdo de texto "
            f"({diagnostico})."
        )
    return resposta


def _normalizar_chamadas(
    resposta: dict[str, Any],
    provider: str,
    model: str,
) -> RespostaIA:
    if provider == "ollama":
        mensagem = resposta.get("message", {})
    else:
        escolhas = resposta.get("choices", [])
        mensagem = escolhas[0].get("message", {}) if escolhas else {}
    if not isinstance(mensagem, dict):
        mensagem = {}

    conteudo = mensagem.get("content", "") or ""
    if isinstance(conteudo, list):
        conteudo = "".join(
            str(parte.get("text", ""))
            for parte in conteudo
            if isinstance(parte, dict)
        )
    chamadas: list[ChamadaFerramenta] = []
    for indice, chamada in enumerate(mensagem.get("tool_calls", []) or []):
        if not isinstance(chamada, dict):
            continue
        funcao = chamada.get("function", {})
        if not isinstance(funcao, dict):
            continue
        argumentos = funcao.get("arguments", {})
        if isinstance(argumentos, str):
            try:
                argumentos = json.loads(argumentos or "{}")
            except json.JSONDecodeError:
                argumentos = {}
        if not isinstance(argumentos, dict):
            argumentos = {}
        nome = str(funcao.get("name") or "").strip()
        if not nome:
            continue
        chamadas.append(
            ChamadaFerramenta(
                id=str(chamada.get("id") or f"tool-{indice + 1}"),
                nome=nome,
                argumentos=dict(argumentos),
            )
        )
    return RespostaIA(
        texto=str(conteudo).strip(),
        chamadas_ferramenta=tuple(chamadas),
        provedor=provider,
        modelo=model,
    )


def _post_com_ferramentas(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    provider: str,
    model: str,
) -> RespostaIA:
    resposta = _post_json(url, payload, headers)
    return _normalizar_chamadas(resposta, provider, model)


def gerar_resposta(
    config: dict[str, Any],
    messages: list[dict[str, Any]],
    progress: ProgressCallback | None = None,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
) -> RespostaIA:
    """Tenta as IAs cadastradas em ordem, sem duplicar streaming entre tentativas."""
    informar = progress or (lambda _mensagem: None)
    provedores = _lista_provedores(config)
    erros: list[str] = []

    for indice, cadastro in enumerate(provedores, start=1):
        nome = cadastro.get("name") or cadastro.get("provider") or f"IA {indice}"
        model = str(cadastro.get("model", "")).strip()
        total = len(provedores)
        informar(f"status|Tentando IA {indice}/{total}: {nome} · {model}")
        inicio = time.monotonic()
        log.info(
            "IA",
            "gerar_resposta",
            (
                f"início da tentativa {indice}/{total}; "
                f"provedor={_sanitizar_detalhe(nome, 80)!r}; "
                f"modelo={_sanitizar_detalhe(model, 120)!r}; "
                f"mensagens={len(messages)}; ferramentas={len(tools or [])}; "
                f"streaming={not bool(tools)}"
            ),
        )

        # Emite os trechos durante o stream. Se esta tentativa falhar, limpa a
        # bolha provisória antes de iniciar o próximo provedor.
        trechos: list[str] = []

        def receber_trecho(trecho: str) -> None:
            trechos.append(trecho)
            informar(f"token|{trecho}")

        try:
            resposta = _gerar_por_provedor(
                cadastro,
                messages,
                receber_trecho,
                tools=tools,
                tool_choice=tool_choice,
            )
        except Exception as exc:
            if trechos:
                informar("reset|Tentativa falhou; aguardando o próximo provedor.")
            duracao_ms = int((time.monotonic() - inicio) * 1000)
            motivo = _sanitizar_detalhe(exc) or exc.__class__.__name__
            nome_seguro = _sanitizar_detalhe(nome, 80) or f"IA {indice}"
            modelo_seguro = (
                _sanitizar_detalhe(model, 120) or "modelo não informado"
            )
            erros.append(f"{nome_seguro} ({modelo_seguro}): {motivo}")
            log.aviso(
                "IA",
                "gerar_resposta",
                (
                    f"tentativa falhou após {duracao_ms} ms; "
                    f"provedor={nome_seguro!r}; "
                    f"modelo={modelo_seguro!r}; "
                    f"motivo={motivo}"
                ),
            )
            if indice < total:
                informar(f"status|{nome} falhou; tentando a próxima IA...")
            continue

        texto_seguro = _remover_rotulos_seguranca(resposta.texto)
        if texto_seguro != resposta.texto:
            resposta = RespostaIA(
                texto=texto_seguro,
                chamadas_ferramenta=resposta.chamadas_ferramenta,
                provedor=resposta.provedor,
                modelo=resposta.modelo,
            )
            informar(f"replace|{texto_seguro}")
            trechos = [texto_seguro] if texto_seguro else []

        if not resposta.texto.strip() and not resposta.chamadas_ferramenta:
            raise RuntimeError(
                "O provedor concluiu a chamada sem conteúdo de texto nem "
                "chamada de ferramenta."
            )

        if not resposta.chamadas_ferramenta and not _usuario_pediu_json(messages):
            texto_normalizado = _resposta_json_em_texto(resposta.texto)
            if texto_normalizado != resposta.texto:
                resposta = RespostaIA(
                    texto=texto_normalizado,
                    chamadas_ferramenta=resposta.chamadas_ferramenta,
                    provedor=resposta.provedor,
                    modelo=resposta.modelo,
                )
                informar(f"replace|{texto_normalizado}")
                trechos = [texto_normalizado] if texto_normalizado else []

        log.ok(
            "IA",
            "gerar_resposta",
            (
                f"tentativa concluída em {int((time.monotonic() - inicio) * 1000)} ms; "
                f"provedor={_sanitizar_detalhe(nome, 80)!r}; "
                f"modelo={_sanitizar_detalhe(model, 120)!r}; "
                f"caracteres={len(resposta.texto)}; "
                f"ferramentas={len(resposta.chamadas_ferramenta)}"
            ),
        )
        return resposta

    detalhes = "\n".join(f"- {erro}" for erro in erros)
    raise RuntimeError(f"Nenhuma IA cadastrada respondeu.\n{detalhes}")


def _lista_provedores(config: dict[str, Any]) -> list[dict[str, str]]:
    """Obtém a lista nova e mantém compatibilidade com a configuração antiga."""
    candidatos = config.get("providers")
    if not isinstance(candidatos, list) or not candidatos:
        candidatos = [config]

    resultado: list[dict[str, str]] = []
    for indice, item in enumerate(candidatos):
        if isinstance(item, dict):
            resultado.append(normalizar_provedor(item, indice))
    return resultado


def _gerar_por_provedor(
    cadastro: dict[str, str],
    messages: list[dict[str, Any]],
    on_piece: Callable[[str], None],
    *,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
) -> RespostaIA:
    """Executa uma tentativa isolada de Ollama ou API compatível com OpenAI."""
    provider = cadastro["provider"].strip().lower()
    model = cadastro["model"].strip()
    base_url = cadastro["base_url"].strip()
    if not model:
        raise ValueError("modelo não informado")
    if not base_url:
        raise ValueError("endereço do provedor não informado")

    if provider == "ollama":
        payload = {
            "model": model,
            "messages": messages,
            "stream": not tools,
        }
        if tools:
            payload["tools"] = tools
            return _post_com_ferramentas(
                _url_complementar(base_url, "/api/chat"),
                payload,
                {},
                "ollama",
                model,
            )
        resposta = _post_stream(
            _url_complementar(base_url, "/api/chat"),
            payload,
            {},
            "ollama",
            on_piece,
        )
        return RespostaIA(texto=resposta, provedor=provider, modelo=model)

    api_key = cadastro.get("api_key", "").strip()
    if not api_key:
        raise ValueError("chave da API não informada")
    limite_saida = (
        4096
        if provider == "openrouter" and model.casefold() == "openrouter/free"
        else 1500
    )
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": limite_saida,
        "stream": not tools,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice or "auto"
    headers = {"Authorization": f"Bearer {api_key}"}
    if provider == "openrouter":
        headers.update(
            {
                "HTTP-Referer": "http://localhost",
                "X-Title": "Hen Place Control",
            }
        )
    if tools:
        return _post_com_ferramentas(
            _url_complementar(base_url, "/chat/completions"),
            payload,
            headers,
            "openai",
            model,
        )
    resposta = _post_stream(
        _url_complementar(base_url, "/chat/completions"),
        payload,
        headers,
        "openai",
        on_piece,
    )
    return RespostaIA(texto=resposta, provedor=provider, modelo=model)