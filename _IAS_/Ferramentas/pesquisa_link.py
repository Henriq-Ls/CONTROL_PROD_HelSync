"""Pesquisa controlada de uma pagina de produto a partir de uma URL."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .resultado import ResultadoFerramenta


NOME_FERRAMENTA = "pesquisar_link_produto"


class _ExtratorPagina(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.titulo = ""
        self.descricao = ""
        self.textos: list[str] = []
        self.json_ld: list[dict[str, Any]] = []
        self._em_titulo = False
        self._em_script_json = False
        self._script_atual: list[str] = []
        self._nivel_conteudo_ignorado = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        atributos = {chave.lower(): valor or "" for chave, valor in attrs}
        if tag == "title":
            self._em_titulo = True
        if tag == "script":
            self._nivel_conteudo_ignorado += 1
            if atributos.get("type", "").lower() == "application/ld+json":
                self._em_script_json = True
                self._script_atual = []
        elif tag in {"style", "noscript", "template"}:
            self._nivel_conteudo_ignorado += 1
        if tag.lower() == "meta":
            nome = (atributos.get("name") or atributos.get("property") or "").lower()
            if nome in {"description", "og:description"} and not self.descricao:
                self.descricao = atributos.get("content", "").strip()
            if nome in {"og:title", "twitter:title"} and not self.titulo:
                self.titulo = atributos.get("content", "").strip()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._em_titulo = False
        if tag == "script":
            if self._em_script_json:
                self._em_script_json = False
                bruto = "".join(self._script_atual).strip()
                if bruto:
                    try:
                        dados = json.loads(bruto)
                    except (TypeError, ValueError):
                        dados = None
                    if isinstance(dados, dict):
                        self.json_ld.append(dados)
                    elif isinstance(dados, list):
                        self.json_ld.extend(
                            item for item in dados if isinstance(item, dict)
                        )
                self._script_atual = []
            self._nivel_conteudo_ignorado = max(
                0,
                self._nivel_conteudo_ignorado - 1,
            )
        elif tag in {"style", "noscript", "template"}:
            self._nivel_conteudo_ignorado = max(
                0,
                self._nivel_conteudo_ignorado - 1,
            )

    def handle_data(self, data: str) -> None:
        if self._em_titulo:
            self.titulo += data
        if self._em_script_json:
            self._script_atual.append(data)
            return
        if self._nivel_conteudo_ignorado:
            return
        texto = " ".join(data.split())
        if texto and not self._em_script_json:
            self.textos.append(texto)


def _produto_json_ld(itens: list[dict[str, Any]]) -> dict[str, Any]:
    resultado: dict[str, Any] = {}
    for item in itens:
        tipo = str(item.get("@type") or "").lower()
        if tipo != "product" and "product" not in tipo:
            continue
        for chave in ("name", "sku", "mpn", "brand", "category", "description"):
            valor = item.get(chave)
            if isinstance(valor, dict):
                valor = valor.get("name")
            if valor not in (None, ""):
                resultado[chave] = str(valor)
        oferta = item.get("offers")
        if isinstance(oferta, dict):
            for chave in ("price", "priceCurrency", "availability"):
                if oferta.get(chave) not in (None, ""):
                    resultado[chave] = str(oferta[chave])
        break
    return resultado


def _parece_conteudo_tecnico(texto: str) -> bool:
    """Evita entregar código de aplicação como se fosse texto do produto."""
    amostras = texto[:12000].lower()
    marcadores = (
        "window.__",
        "webpack",
        "navigator.useragent",
        "document.getelementbyid",
        "application/javascript",
        "self.__next_f.push",
    )
    ocorrencias = sum(marcador in amostras for marcador in marcadores)
    return ocorrencias >= 2


def pesquisar_link_produto(url: str) -> ResultadoFerramenta:
    """Lê somente metadados e texto público da URL informada."""
    endereco = str(url or "").strip()
    partes = urlsplit(endereco)
    if partes.scheme not in {"http", "https"} or not partes.netloc:
        return ResultadoFerramenta.erro(
            NOME_FERRAMENTA,
            "A URL precisa começar com http:// ou https://.",
            codigo="URL_INVALIDA",
        )
    requisicao = Request(
        endereco,
        headers={
            "User-Agent": "HenPlaceControl/1.0 (pesquisa de produto)",
            "Accept": "text/html,application/xhtml+xml",
        },
        method="GET",
    )
    try:
        with urlopen(requisicao, timeout=25) as resposta:
            bruto = resposta.read(800_000)
            charset = resposta.headers.get_content_charset() or "utf-8"
            html = bruto.decode(charset, errors="replace")
            endereco_final = resposta.geturl()
    except HTTPError as exc:
        return ResultadoFerramenta.erro(
            NOME_FERRAMENTA,
            f"O site respondeu HTTP {exc.code}.",
            codigo="HTTP_ERRO",
            dados={"url": endereco, "fonte": endereco},
        )
    except (URLError, TimeoutError, OSError) as exc:
        return ResultadoFerramenta.erro(
            NOME_FERRAMENTA,
            f"Não foi possível consultar a página: {exc}.",
            codigo="FALHA_DE_REDE",
            dados={"url": endereco, "fonte": endereco},
        )

    extrator = _ExtratorPagina()
    try:
        extrator.feed(html)
    except Exception as exc:
        return ResultadoFerramenta.erro(
            NOME_FERRAMENTA,
            f"A página não pôde ser interpretada: {exc}.",
            codigo="HTML_INVALIDO",
            dados={"url": endereco_final, "fonte": endereco_final},
        )

    dados = _produto_json_ld(extrator.json_ld)
    titulo = re.sub(r"\s+", " ", extrator.titulo).strip()
    descricao = re.sub(r"\s+", " ", extrator.descricao).strip()
    texto = re.sub(r"\s+", " ", " ".join(extrator.textos)).strip()
    conteudo_tecnico = _parece_conteudo_tecnico(texto)
    if titulo:
        dados.setdefault("titulo_pagina", titulo)
    if descricao:
        dados.setdefault("descricao_pagina", descricao[:2000])
    if texto and not conteudo_tecnico:
        dados["texto_publico"] = texto[:6000]
    dados["url"] = endereco_final
    dados["fonte"] = endereco_final
    dados["confianca"] = "confirmado somente pelo conteúdo público retornado pela URL"
    if (
        not dados.get("name")
        and not dados.get("description")
        and not descricao
        and (not texto or conteudo_tecnico)
        and not _produto_json_ld(extrator.json_ld)
    ):
        return ResultadoFerramenta.erro(
            NOME_FERRAMENTA,
            (
                "A página respondeu, mas não entregou dados públicos de produto "
                "em formato utilizável. Ela pode exigir JavaScript, login ou "
                "bloquear consultas automáticas."
            ),
            codigo="CONTEUDO_INDISPONIVEL",
            dados={"url": endereco_final, "fonte": endereco_final},
        )
    return ResultadoFerramenta.ok(
        NOME_FERRAMENTA,
        "Página consultada. Os dados devem ser tratados como provenientes somente da fonte indicada.",
        dados,
    )