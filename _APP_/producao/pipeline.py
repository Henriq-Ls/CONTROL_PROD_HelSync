"""Pipeline atual da aba Produção.

O Cadastro já entrega imagens com grupo, sequência, medidas e peso no nome.
Este módulo não renomeia essas imagens. Ele valida o pacote salvo, separa
amostras e imagens de medidas pela regra dos grupos e reaproveita os módulos
antigos apenas para os tratamentos visuais.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Callable

from _APPDATA_ import appdata
from _LOGS_ import log as app_log
from _APP_.PySide6_core import (
    DB_PATH,
    PASTA_AJUSTE_GERAL,
    PASTA_FUNDO_BRANCO,
    PASTA_FUNDO_CAPA,
    PASTA_MEDIDAS,
    PASTA_PREVIEWS,
    PASTA_SEM_FUNDO,
    PASTA_VIDEO_CONVERTIDO,
    PASTA_VIDEO_LEGADO,
    IMAGE_EXTENSIONS,
    _copiar_selecionadas,
    _formas_de_venda,
    _ler_linhas_produtos_txt,
    _ler_ordem_midias_producao,
    _separar_imagens_por_papel,
    _validar_nomes_e_txt,
    init_database,
)


def _primeiro_arquivo(
    pasta: Path,
    prefixos: tuple[str, ...],
) -> Path | None:
    if not pasta.exists():
        return None
    candidatos = sorted(
        caminho
        for caminho in pasta.iterdir()
        if caminho.is_file()
        and caminho.suffix.lower() in IMAGE_EXTENSIONS
        and caminho.name.lower().startswith(prefixos)
    )
    return candidatos[0] if candidatos else None


def _recurso_visual(
    categoria: str,
    nome: str | None,
    descricao: str,
    *,
    obrigatorio: bool = False,
    usar_primeiro: bool = False,
) -> Path | None:
    """Resolve pelo AppData o arquivo escolhido para uma categoria."""
    pasta = Path(appdata.pasta_midia_categoria(categoria))
    candidatos = appdata.listar_midias(categoria)
    if nome:
        nome = str(nome)
        if Path(nome).name != nome:
            raise ValueError(f"Nome inválido para {descricao}: {nome}")
        if nome in candidatos:
            return pasta / nome
        raise FileNotFoundError(
            f"O {descricao} '{nome}' não foi encontrado no AppData: {pasta}"
        )
    if candidatos and usar_primeiro:
        return pasta / candidatos[0]
    if obrigatorio:
        raise FileNotFoundError(
            f"Nenhum arquivo de {descricao} foi cadastrado. "
            "Abra a aba Configurações e adicione essa mídia."
        )
    return None


def _fundo_medida_configurado() -> str | None:
    """Retorna o fundo de medidas ativo em Configurações."""
    arquivos = appdata.listar_midias("fundo_medida")
    configuracao = appdata.ler_config()
    producao = configuracao.get("producao", {})
    if not isinstance(producao, dict):
        producao = {}
    escolhido = producao.get("fundo_medida")
    if escolhido in arquivos:
        return str(escolhido)
    return arquivos[0] if arquivos else None


def preparar_imagens_marketplace(
    imagens: list[str | Path],
    destino: str | Path,
    *,
    logo_path: str | Path | None = None,
    texto: str = "",
    recursos_por_imagem: dict[str, dict[str, object]] | None = None,
    reduzir_para_marketplace: bool = True,
    progress: Callable[[str], None] | None = None,
) -> list[str]:
    """Aplica recursos escolhidos em cópias; reduz somente quando vai para G."""
    from PIL import Image, ImageDraw
    from Tratar_midias.e__Colocar_Logos_Ref import carregar_fonte

    fontes = [Path(caminho) for caminho in imagens]
    if not fontes:
        raise ValueError("Selecione ao menos uma imagem para preparar.")
    for fonte in fontes:
        if not fonte.is_file() or fonte.suffix.lower() not in IMAGE_EXTENSIONS:
            raise FileNotFoundError(f"Imagem de origem indisponível: {fonte}")

    logo = Path(logo_path) if logo_path else None
    if logo is not None and not logo.is_file():
        raise FileNotFoundError(f"Logo indisponível: {logo}")

    pasta_destino = Path(destino)
    pasta_destino.mkdir(parents=True, exist_ok=True)
    pasta_temporaria = Path(
        tempfile.mkdtemp(prefix=".preparacao-marketplace-", dir=pasta_destino.parent)
    )
    geradas: list[Path] = []

    def desenhar_texto(
        draw,
        imagem,
        valor: str,
        posicao: str,
    ) -> None:
        texto_limpo = str(valor or "").strip()
        if not texto_limpo:
            return
        tamanho_fonte = max(16, int(imagem.width * 0.022))
        fonte_texto = carregar_fonte(tamanho_fonte)
        margem = max(14, int(imagem.width * 0.02))
        largura_maxima = max(
            1,
            int((imagem.width - margem * 3) / 2)
            if posicao in {"inferior_esquerda", "inferior_direita"}
            else int(imagem.width * 0.62),
        )
        linhas: list[str] = []
        linha_atual = ""
        for palavra in texto_limpo.split():
            partes = [palavra]
            caixa_palavra = draw.textbbox((0, 0), palavra, font=fonte_texto)
            if caixa_palavra[2] - caixa_palavra[0] > largura_maxima:
                partes = []
                parte_atual = ""
                for caractere in palavra:
                    candidata = parte_atual + caractere
                    caixa = draw.textbbox((0, 0), candidata, font=fonte_texto)
                    if (
                        parte_atual
                        and caixa[2] - caixa[0] > largura_maxima
                    ):
                        partes.append(parte_atual)
                        parte_atual = caractere
                    else:
                        parte_atual = candidata
                if parte_atual:
                    partes.append(parte_atual)

            for parte in partes:
                candidata = f"{linha_atual} {parte}".strip()
                caixa = draw.textbbox((0, 0), candidata, font=fonte_texto)
                if linha_atual and caixa[2] - caixa[0] > largura_maxima:
                    linhas.append(linha_atual)
                    linha_atual = parte
                else:
                    linha_atual = candidata
        if linha_atual:
            linhas.append(linha_atual)

        caixas = [
            draw.textbbox((0, 0), linha, font=fonte_texto)
            for linha in linhas
        ]
        alturas = [caixa[3] - caixa[1] for caixa in caixas]
        espacamento = max(3, int(tamanho_fonte * 0.15))
        altura_total = sum(alturas) + espacamento * max(0, len(linhas) - 1)
        y = (
            margem
            if posicao == "superior_direita"
            else imagem.height - margem - altura_total
        )
        for linha, caixa, altura in zip(linhas, caixas, alturas):
            largura_texto = caixa[2] - caixa[0]
            x = (
                imagem.width - margem - largura_texto
                if posicao in {"superior_direita", "inferior_direita"}
                else margem
            )
            draw.text(
                (x, y - caixa[1]),
                linha,
                fill=(0, 0, 0, 255),
                font=fonte_texto,
                stroke_width=max(1, int(tamanho_fonte * 0.06)),
                stroke_fill=(255, 255, 255, 255),
            )
            y += altura + espacamento

    try:
        for indice, fonte in enumerate(fontes, start=1):
            if progress:
                progress(f"Preparando imagem {indice}/{len(fontes)}: {fonte.name}")

            chave_fonte = str(fonte.resolve())
            recursos_imagem = (
                recursos_por_imagem.get(chave_fonte)
                if recursos_por_imagem is not None
                else None
            )
            if recursos_imagem is None:
                logo_imagem_path = logo
                textos = {"inferior_esquerda": str(texto or "").strip()}
            else:
                logo_escolhida = str(
                    recursos_imagem.get("logo_path") or ""
                ).strip()
                logo_imagem_path = Path(logo_escolhida) if logo_escolhida else None
                configuracao_textos = recursos_imagem.get("textos", {})
                textos = (
                    {
                        str(posicao): str(valor or "").strip()
                        for posicao, valor in configuracao_textos.items()
                        if str(valor or "").strip()
                    }
                    if isinstance(configuracao_textos, dict)
                    else {}
                )
            if logo_imagem_path is not None and not logo_imagem_path.is_file():
                raise FileNotFoundError(
                    f"Logo indisponível para {fonte.name}: {logo_imagem_path}"
                )

            with Image.open(fonte) as original:
                imagem = original.convert("RGBA")

            if logo_imagem_path is not None:
                with Image.open(logo_imagem_path) as original_logo:
                    camada_logo = original_logo.convert("RGBA")
                tamanho_logo = max(1, int(imagem.width * 0.11))
                camada_logo.thumbnail(
                    (tamanho_logo, tamanho_logo),
                    Image.Resampling.LANCZOS,
                )
                imagem.alpha_composite(camada_logo, (25, 25))

            if textos:
                draw = ImageDraw.Draw(imagem)
                for posicao in (
                    "superior_direita",
                    "inferior_esquerda",
                    "inferior_direita",
                ):
                    desenhar_texto(
                        draw,
                        imagem,
                        str(textos.get(posicao) or ""),
                        posicao,
                    )

            alpha = imagem.getchannel("A").getextrema()
            manter_transparencia = alpha[0] < 255
            extensao = (
                ".png"
                if manter_transparencia
                else ".jpg"
            )
            nome_temporario = fonte.stem
            sufixo_temporario = 2
            while any(
                caminho.stem.casefold() == nome_temporario.casefold()
                for caminho in geradas
            ):
                nome_temporario = f"{fonte.stem}_{sufixo_temporario}"
                sufixo_temporario += 1
            gerada = pasta_temporaria / f"{nome_temporario}{extensao}"
            if extensao == ".jpg":
                imagem.convert("RGB").save(gerada, quality=95)
            else:
                imagem.save(gerada, "PNG")
            geradas.append(gerada)

        if reduzir_para_marketplace:
            from Tratar_midias.z__Reduz_IMG import Reduzir_IMG

            if progress:
                progress(
                    "Reduzindo imagens para o limite de 2.000.000 bytes por arquivo..."
                )
            Reduzir_IMG(pasta_temporaria, fator=0.5)

        resultados: list[str] = []
        for gerada in geradas:
            base = gerada.stem
            extensao = gerada.suffix
            destino_final = pasta_destino / f"{base}{extensao}"
            sufixo = 2
            while destino_final.exists():
                destino_final = pasta_destino / f"{base}_{sufixo}{extensao}"
                sufixo += 1
            temporario_final = pasta_destino / f".{destino_final.name}.tmp"
            shutil.copy2(gerada, temporario_final)
            temporario_final.replace(destino_final)
            resultados.append(str(destino_final))
            if progress:
                progress(f"Imagem pronta em G_marketplace: {destino_final.name}")
        return resultados
    finally:
        shutil.rmtree(pasta_temporaria, ignore_errors=True)


def _assinatura_recurso(
    categoria: str,
    nome: str | None = None,
    *,
    usar_primeiro: bool = False,
) -> dict:
    pasta = Path(appdata.pasta_midia_categoria(categoria))
    candidatos = appdata.listar_midias(categoria)
    escolhido = nome
    if escolhido is None and usar_primeiro and candidatos:
        escolhido = candidatos[0]
    caminho = (
        pasta / escolhido
        if escolhido and Path(escolhido).name == escolhido
        else None
    )
    return {
        "nome": escolhido,
        "arquivo": _assinatura_arquivo(caminho),
    }


def _pasta_entrada_imagens(pasta: Path) -> Path | None:
    """Prefere a pasta A em minúsculas e aceita nomes antigos do Cadastro."""
    nomes = (
        PASTA_AJUSTE_GERAL,
        "a_Ajuste_Geral",
        "a_AjusteGeral",
        "A_Ajuste_Geral",
        "A_AjusteGeral",
        "Ajuste_Geral",
    )
    for nome in nomes:
        candidata = pasta / nome
        if candidata.is_dir() and any(
            caminho.is_file() and caminho.suffix.lower() in IMAGE_EXTENSIONS
            for caminho in candidata.iterdir()
        ):
            return candidata
    return None


def _gerar_previews(
    pasta: Path,
    referencia: str,
    imagens_ordem: list[str],
    imagem_capa: str | Path,
    imagem_medida: str,
    logo_nome: str | None = None,
    fundo_capa_nome: str | None = None,
    fundo_medida_nome: str | None = None,
    progress: Callable[[str], None] | None = None,
) -> tuple[Path | None, Path, Path]:
    logo = _recurso_visual("logo", logo_nome, "logo")
    fundo_medida = _recurso_visual(
        "fundo_medida",
        fundo_medida_nome or _fundo_medida_configurado(),
        "fundo de medida",
        obrigatorio=True,
    )
    fundo_capa = _recurso_visual(
        "fundo_capa",
        fundo_capa_nome,
        "fundo de capa",
        obrigatorio=True,
    )

    pasta_entrada = _pasta_entrada_imagens(pasta)
    if pasta_entrada is None:
        pasta_entrada = pasta
    por_stem: dict[str, list[Path]] = {}
    for pasta_imagens in (pasta_entrada, pasta):
        for caminho in pasta_imagens.iterdir():
            if caminho.is_file() and caminho.suffix.lower() in IMAGE_EXTENSIONS:
                por_stem.setdefault(caminho.stem.casefold(), []).append(caminho)

    def localizar_imagem(nome: str | Path) -> Path | None:
        caminho_explicito = Path(nome)
        if caminho_explicito.is_file():
            return caminho_explicito
        correspondentes = por_stem.get(caminho_explicito.stem.casefold(), [])
        if not correspondentes:
            return None
        extensao_preferida = caminho_explicito.suffix.casefold()
        return min(
            correspondentes,
            key=lambda candidato: (
                candidato.parent != pasta_entrada,
                candidato.suffix.casefold() != extensao_preferida,
                IMAGE_EXTENSIONS.index(candidato.suffix.lower()),
                candidato.name.casefold(),
            ),
        )

    capa = localizar_imagem(imagem_capa)
    medida = localizar_imagem(imagem_medida)
    if capa is None or medida is None:
        ausente = imagem_capa if capa is None else imagem_medida
        raise FileNotFoundError(
            f"O manifesto aponta para a imagem com stem '{Path(ausente).stem}', "
            f"ausente na pasta {pasta}."
        )

    previews = pasta / PASTA_PREVIEWS
    previews.mkdir(exist_ok=True)
    logo_sufixo = f"_LOGO_{logo.stem}" if logo else ""

    def caminho_preview(prefixo: str, fundo: Path) -> Path:
        fonte_capa = (
            f"_{capa.parent.name}_{capa.stem}{capa.suffix.lower()}"
            if prefixo == "CAPA"
            else ""
        )
        return previews / (
            f"{prefixo}_{referencia}{fonte_capa}_{fundo.stem}"
            f"{logo_sufixo}.png"
        )

    def preview_atual(
        caminho: Path,
        imagem: Path,
        fundo: Path,
        logo_path: Path | None,
    ) -> bool:
        if not caminho.is_file():
            return False
        try:
            fontes = [imagem.stat().st_mtime, fundo.stat().st_mtime]
            if logo_path is not None:
                fontes.append(logo_path.stat().st_mtime)
            return caminho.stat().st_mtime >= max(fontes)
        except OSError:
            return False

    pendentes = [
        (prefixo, fundo, imagem)
        for prefixo, fundo, imagem in (
        ("CAPA", fundo_capa, capa),
        ("MEDIDA", fundo_medida, medida),
        )
        if not preview_atual(
            caminho_preview(prefixo, fundo),
            imagem,
            fundo,
            logo,
        )
    ]
    if pendentes:
        try:
            from _FERRAMENTAS_.Previews import preview_produto_com_fundo
        except Exception as exc:
            raise RuntimeError(
                "Não foi possível carregar o gerador de prévias. "
                "A instalação de rembg/onnxruntime não conseguiu carregar "
                f"seus provedores: {exc}"
            ) from exc
        for prefixo, fundo, imagem in pendentes:
            caminho = caminho_preview(prefixo, fundo)
            resultado = preview_produto_com_fundo(
                imagem,
                fundo,
                sombra_altura=0.18,
            )
            if resultado is None:
                raise RuntimeError(
                    f"Não foi possível gerar a prévia {caminho.name}. "
                    "Confira os recursos de rembg/onnxruntime."
                )
            if logo is not None:
                from PIL import Image

                resultado = resultado.convert("RGBA")
                with Image.open(logo) as arquivo_logo:
                    logo_imagem = arquivo_logo.convert("RGBA")
                tamanho_logo = max(1, int(resultado.width * 0.11))
                logo_imagem.thumbnail((tamanho_logo, tamanho_logo))
                resultado.alpha_composite(logo_imagem, (25, 25))
            resultado.save(caminho, "PNG")
            if progress:
                progress(f"Preview salvo: {caminho.name}")
    return logo, fundo_capa, fundo_medida


def gerar_previews_para_producao(
    produto_row: tuple,
    *,
    logo_nome: str | None = None,
    fundo_capa_nome: str | None = None,
    fundo_medida_nome: str | None = None,
    imagem_capa_path: Path | str | None = None,
    progress: Callable[[str], None] | None = None,
) -> tuple[Path, Path]:
    """Cria/reutiliza composições de capa e medida antes da Produção."""
    if len(produto_row) < 3:
        raise ValueError("O Cadastro atual não contém a pasta do produto.")
    pasta = Path(str(produto_row[2]))
    referencia = str(produto_row[1] or "").strip()
    if not pasta.is_dir():
        raise FileNotFoundError(f"A pasta do produto não existe: {pasta}")

    imagens_ordem, _videos = _ler_ordem_midias_producao(pasta)
    amostras, imagens_medida, _resumo = _separar_imagens_por_papel(
        imagens_ordem
    )
    if not amostras or not imagens_medida:
        raise ValueError(
            "O manifesto do Cadastro não tem imagens suficientes para criar "
            "as prévias de capa e medida."
        )

    logo, fundo_capa, fundo_medida = _gerar_previews(
        pasta,
        referencia,
        imagens_ordem,
        Path(imagem_capa_path) if imagem_capa_path else amostras[0],
        imagens_medida[-1],
        logo_nome=logo_nome,
        fundo_capa_nome=fundo_capa_nome,
        fundo_medida_nome=fundo_medida_nome,
        progress=progress,
    )
    pasta_previews = pasta / PASTA_PREVIEWS
    logo_sufixo = f"_LOGO_{logo.stem}" if logo else ""
    caminho_capa = (
        Path(imagem_capa_path) if imagem_capa_path else Path(amostras[0])
    )
    if not caminho_capa.is_file():
        pasta_entrada = _pasta_entrada_imagens(pasta) or pasta
        correspondentes = [
            caminho
            for pasta_imagens in (pasta_entrada, pasta)
            for caminho in pasta_imagens.iterdir()
            if caminho.is_file()
            and caminho.suffix.lower() in IMAGE_EXTENSIONS
            and caminho.stem.casefold() == caminho_capa.stem.casefold()
        ]
        if correspondentes:
            extensao_preferida = caminho_capa.suffix.casefold()
            caminho_capa = min(
                correspondentes,
                key=lambda caminho: (
                    caminho.suffix.casefold() != extensao_preferida,
                    IMAGE_EXTENSIONS.index(caminho.suffix.lower()),
                    caminho.name.casefold(),
                ),
            )
    fonte_capa = (
        f"_{caminho_capa.parent.name}_{caminho_capa.stem}"
        f"{caminho_capa.suffix.lower()}"
    )
    return (
        pasta_previews
        / f"CAPA_{referencia}{fonte_capa}_{fundo_capa.stem}{logo_sufixo}.png",
        pasta_previews
        / f"MEDIDA_{referencia}_{fundo_medida.stem}{logo_sufixo}.png",
    )


def _nomes_saida_jpg(nomes: list[str]) -> set[str]:
    return {f"{Path(nome).stem}.jpg" for nome in nomes}


def _assinatura_arquivo(caminho: Path | None) -> dict | None:
    if caminho is None or not caminho.is_file():
        return None
    stat = caminho.stat()
    return {
        "path": str(caminho.resolve()),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _assinatura_imagens(pasta: Path, nomes: list[str]) -> list | None:
    if not pasta.is_dir():
        return None
    por_stem: dict[str, list[Path]] = {}
    for caminho in pasta.iterdir():
        if caminho.is_file() and caminho.suffix.lower() in IMAGE_EXTENSIONS:
            por_stem.setdefault(caminho.stem.casefold(), []).append(caminho)

    resultado = []
    for nome in nomes:
        arquivos = sorted(
            por_stem.get(Path(nome).stem.casefold(), []),
            key=lambda caminho: caminho.name.casefold(),
        )
        if not arquivos:
            return None
        resultado.append(
            {
                "nome_manifesto": Path(nome).name.casefold(),
                "arquivos": [
                    _assinatura_arquivo(caminho)
                    for caminho in arquivos
                ],
            }
        )
    return resultado


def _fingerprint_etapa(dados: dict) -> str:
    serializado = json.dumps(
        dados,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serializado.encode("utf-8")).hexdigest()


def _etapa_tem_saidas_imagem(
    pasta: Path,
    nomes: list[str],
) -> bool:
    if not pasta.is_dir():
        return False
    stems = {
        caminho.stem.casefold()
        for caminho in pasta.iterdir()
        if caminho.is_file()
        and caminho.suffix.lower() in IMAGE_EXTENSIONS
        and caminho.stat().st_size > 0
    }
    return all(Path(nome).stem.casefold() in stems for nome in nomes)


def _etapa_tem_arquivos(
    pasta: Path,
    nomes: set[str],
) -> bool:
    if not pasta.is_dir():
        return False
    existentes = {
        caminho.name.casefold()
        for caminho in pasta.iterdir()
        if caminho.is_file() and caminho.stat().st_size > 0
    }
    return all(nome.casefold() in existentes for nome in nomes)


def _etapa_precisa_reprocessar(
    nome: str,
    pasta_saida: Path,
    assinatura: str,
    saidas_completas: bool,
    forcar: bool,
    log: Callable[[str], None],
) -> bool:
    if forcar:
        log(f"{nome}: entrada anterior foi refeita; atualizando esta etapa.")
        return True
    if not saidas_completas:
        log(f"{nome}: faltam saídas; refazendo somente esta etapa.")
        return True

    caminho_cache = pasta_saida / ".pipeline_cache.json"
    assinatura_anterior = None
    if caminho_cache.is_file():
        try:
            estado = json.loads(caminho_cache.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            log(f"{nome}: cache inválido; refazendo a etapa para validar as saídas.")
            return True
        if (
            not isinstance(estado, dict)
            or estado.get("version") != 1
            or not isinstance(estado.get("signature"), str)
        ):
            log(f"{nome}: versão do cache incompatível; refazendo a etapa.")
            return True
        assinatura_anterior = estado["signature"]

    if assinatura_anterior is None:
        log(f"{nome}: saídas completas existentes; registrando a referência do cache.")
        return False
    if assinatura_anterior != assinatura:
        log(f"{nome}: entradas ou configurações mudaram; refazendo esta etapa.")
        return True
    log(f"{nome}: saídas completas e atuais; etapa ignorada.")
    return False


def _gravar_assinatura_etapa(pasta_saida: Path, assinatura: str) -> None:
    pasta_saida.mkdir(parents=True, exist_ok=True)
    caminho_cache = pasta_saida / ".pipeline_cache.json"
    temporario = caminho_cache.with_name(caminho_cache.name + ".tmp")
    temporario.write_text(
        json.dumps(
            {"version": 1, "signature": assinatura},
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    temporario.replace(caminho_cache)


def _todos_atuais_com_fonte(
    pasta_saida: Path,
    pasta_entrada: Path,
    nomes: list[str],
) -> bool:
    if not pasta_saida.is_dir() or not pasta_entrada.is_dir():
        return False
    entradas: dict[str, list[Path]] = {}
    saidas: dict[str, list[Path]] = {}
    for caminho in pasta_entrada.iterdir():
        if caminho.is_file() and caminho.suffix.lower() in IMAGE_EXTENSIONS:
            entradas.setdefault(caminho.stem.casefold(), []).append(caminho)
    for caminho in pasta_saida.iterdir():
        if caminho.is_file() and caminho.suffix.lower() == ".png":
            saidas.setdefault(caminho.stem.casefold(), []).append(caminho)

    for nome in nomes:
        stem = Path(nome).stem.casefold()
        fontes = entradas.get(stem, [])
        resultados = saidas.get(stem, [])
        if not fontes or not resultados:
            return False
        data_fonte = max(caminho.stat().st_mtime_ns for caminho in fontes)
        data_saida = max(caminho.stat().st_mtime_ns for caminho in resultados)
        if data_saida < data_fonte:
            return False
    return True


def _remover_saidas_desatualizadas(
    pasta_saida: Path,
    pasta_entrada: Path,
    nomes: list[str],
) -> None:
    if not pasta_saida.is_dir() or not pasta_entrada.is_dir():
        return
    fontes = {
        caminho.stem.casefold(): caminho
        for caminho in pasta_entrada.iterdir()
        if caminho.is_file() and caminho.suffix.lower() in IMAGE_EXTENSIONS
    }
    for nome in nomes:
        fonte = fontes.get(Path(nome).stem.casefold())
        if fonte is None:
            continue
        for saida in pasta_saida.iterdir():
            if (
                saida.is_file()
                and saida.suffix.lower() in IMAGE_EXTENSIONS
                and saida.stem.casefold() == fonte.stem.casefold()
                and (
                    saida.suffix.lower() != ".png"
                    or saida.stat().st_mtime_ns < fonte.stat().st_mtime_ns
                )
            ):
                saida.unlink()


def _copiar_resultados_por_stem(
    pasta_origem: Path,
    pasta_destino: Path,
) -> None:
    pasta_destino.mkdir(parents=True, exist_ok=True)
    for arquivo in sorted(
        (
            caminho
            for caminho in pasta_origem.iterdir()
            if caminho.is_file() and caminho.suffix.lower() in IMAGE_EXTENSIONS
        ),
        key=lambda caminho: caminho.name.casefold(),
    ):
        for existente in pasta_destino.iterdir():
            if (
                existente.is_file()
                and existente.suffix.lower() in IMAGE_EXTENSIONS
                and existente.stem.casefold() == arquivo.stem.casefold()
                and existente.name.casefold() != arquivo.name.casefold()
            ):
                existente.unlink()
        shutil.copy2(arquivo, pasta_destino / arquivo.name)


def _gravar_vendas(
    produto: str,
    tipo_kit_config: str,
    pasta_saida: Path,
    nomes: set[str],
) -> None:
    init_database()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "DELETE FROM VENDAS WHERE UPPER(NOME_PRODUTO) = UPPER(?)",
            (produto,),
        )
        for nome in sorted(nomes, key=str.casefold):
            arquivo = pasta_saida / nome
            if not arquivo.exists():
                continue
            conn.execute(
                """
                INSERT OR REPLACE INTO VENDAS
                (ID, DATA, NOME_PRODUTO, KIT, OBSERVACOES)
                VALUES (?, date('now'), ?, ?, ?)
                """,
                (
                    arquivo.stem,
                    produto,
                    tipo_kit_config,
                    str(arquivo),
                ),
            )


def _migrar_pasta_video_legada(
    pasta_produto: Path,
    pasta_video: Path,
    log: Callable[[str], None],
) -> None:
    """Renomeia a pasta antiga de vídeo sem sobrescrever a pasta nova."""
    if pasta_video.exists():
        return
    for nome_legado in (PASTA_VIDEO_LEGADO, "Video_shopee_convertido"):
        pasta_legada = pasta_produto / nome_legado
        if not pasta_legada.is_dir():
            continue
        try:
            pasta_legada.rename(pasta_video)
        except OSError as erro:
            log(
                f"Não foi possível renomear {pasta_legada.name} para "
                f"{pasta_video.name}; a pasta antiga foi preservada: {erro}"
            )
        else:
            log(
                f"Pasta de vídeo renomeada: {pasta_legada.name} → "
                f"{pasta_video.name}."
            )
        return


def executar_producao(
    produto_row: tuple,
    sombra_altura: float,
    volume_musica: float,
    ordem: str,
    tipo_medidas: str,
    kit_opcoes: list[str] | str | None,
    progress: Callable[[str], None] | None = None,
    *,
    logo_nome: str | None = None,
    fundo_capa_nome: str | None = None,
    fundo_medida_nome: str | None = None,
    fundo_branco_nome: str | None = None,
    musica_nome: str | None = None,
    perfil_social: str = "",
    url_loja: str = "",
) -> str:
    """Executa a produção usando o pacote final criado pelo Cadastro."""

    def log(texto: str) -> None:
        app_log.info("Producao.pipeline", "executar_producao", texto)
        if progress:
            progress(texto)

    def aviso(texto: str) -> None:
        app_log.aviso("Producao.pipeline", "executar_producao", texto)
        if progress:
            progress(texto)

    log("Worker da Produção entrou na pipeline.")
    produto = str(produto_row[0]).upper()
    referencia = str(produto_row[1])
    pasta = Path(str(produto_row[2]))
    tipo_kit_config = str(produto_row[7])
    log(
        f"Produto={produto}; referência={referencia}; "
        f"pasta={pasta}; configuração={tipo_kit_config}"
    )
    if not pasta.exists():
        raise FileNotFoundError(f"Pasta do produto não encontrada: {pasta}")

    log("Lendo .ordem_midias.json...")
    imagens_ordem, videos_manifesto = _ler_ordem_midias_producao(pasta)
    log(
        f"Manifesto lido: {len(imagens_ordem)} imagem(ns), "
        f"{len(videos_manifesto)} vídeo(s)."
    )
    log("Lendo produtos.txt para conferência...")
    linhas_txt = _ler_linhas_produtos_txt(pasta, imagens_ordem)
    log("Conferindo nomes finais, medidas e pesos...")
    _validar_nomes_e_txt(imagens_ordem, linhas_txt)
    log("Separando os grupos pela ordem oficial do Cadastro...")
    amostras, imagens_medida, resumo_grupos = _separar_imagens_por_papel(
        imagens_ordem
    )
    log(
        f"Papéis calculados: {len(amostras)} amostra(s)/variação(ões), "
        f"{len(imagens_medida)} imagem(ns) de medida."
    )
    formas_venda = _formas_de_venda(tipo_kit_config, kit_opcoes)

    log(f"Iniciando produção de {produto}")
    log(
        f"Cadastro validado: {len(imagens_ordem)} imagem(ns), "
        f"{len(videos_manifesto)} vídeo(s), "
        f"{len(resumo_grupos)} grupo(s)."
    )
    for resumo in resumo_grupos:
        log(f"  {resumo}")
    log(f"Formas de venda: {', '.join(formas_venda)}")

    ajuste_geral = _pasta_entrada_imagens(pasta)
    if ajuste_geral is None:
        raise FileNotFoundError(
            f"A pasta {PASTA_AJUSTE_GERAL} não contém imagens válidas. "
            "Confira o nome da pasta e gere os PNGs pelo Cadastro."
        )
    if (
        ajuste_geral.name.casefold().startswith("a_")
        and any(
            caminho.is_file()
            and caminho.suffix.lower() in IMAGE_EXTENSIONS
            and caminho.suffix.lower() != ".png"
            for caminho in ajuste_geral.iterdir()
        )
    ):
        raise ValueError(
            f"A pasta {PASTA_AJUSTE_GERAL} deve conter somente PNGs. "
            "Os JPEGs originais ficam fora dessa pasta."
        )

    sem_fundo = pasta / PASTA_SEM_FUNDO
    fundo_branco = pasta / PASTA_FUNDO_BRANCO
    medidas_finais = pasta / PASTA_MEDIDAS
    fundo_capa = pasta / PASTA_FUNDO_CAPA
    fundo_capa.mkdir(parents=True, exist_ok=True)
    video_dir = pasta / PASTA_VIDEO_CONVERTIDO
    _migrar_pasta_video_legada(pasta, video_dir, log)
    video_dir.mkdir(parents=True, exist_ok=True)

    log(
        "Selecionando logo, fundo de capa e fundo de medida "
        "definidos para a Produção..."
    )
    logo_path = _recurso_visual(
        "logo",
        logo_nome,
        "logo",
    )
    fundo_capa_path = _recurso_visual(
        "fundo_capa",
        fundo_capa_nome,
        "fundo de capa",
    )
    medida_path = _recurso_visual(
        "fundo_medida",
        fundo_medida_nome or _fundo_medida_configurado(),
        "fundo de medida",
        obrigatorio=True,
    )
    log(
        "Recursos selecionados: "
        f"logo={logo_path.name if logo_path else 'nenhuma'}; "
        f"fundo_capa={fundo_capa_path.name if fundo_capa_path else 'nenhum'}; "
        f"fundo_medida={medida_path.name}"
    )
    fundo_branco_path = _recurso_visual(
        "fundo_branco",
        fundo_branco_nome,
        "fundo branco",
        usar_primeiro=True,
    )

    _remover_saidas_desatualizadas(
        sem_fundo,
        ajuste_geral,
        imagens_ordem,
    )
    sem_fundo_reconstruido = False
    if not _todos_atuais_com_fonte(
        sem_fundo,
        ajuste_geral,
        imagens_ordem,
    ):
        log(f"Gerando pasta sem fundo: {sem_fundo}")
        log(
            "Carregando o módulo e o modelo de remoção de fundo; "
            "a primeira carga pode levar alguns minutos..."
        )
        try:
            from Tratar_midias.c__Remove_Refina_IMG import Remove_IMG
        except Exception as exc:
            raise RuntimeError(
                "A remoção de fundo não pôde carregar PyTorch/CUDA. "
                "A DLL do torch está incompatível ou incompleta. "
                f"Detalhe original: {exc}"
            ) from exc
        Remove_IMG(str(ajuste_geral), str(sem_fundo), progress=log)
        sem_fundo_reconstruido = True
        saidas_sem_fundo = {
            caminho.stem.casefold()
            for caminho in sem_fundo.iterdir()
            if caminho.is_file() and caminho.suffix.lower() in IMAGE_EXTENSIONS
        } if sem_fundo.is_dir() else set()
        faltando_sem_fundo = [
            Path(nome).stem
            for nome in imagens_ordem
            if Path(nome).stem.casefold() not in saidas_sem_fundo
        ]
        if faltando_sem_fundo:
            mensagem = (
                "A remoção de fundo não gerou todas as imagens esperadas. "
                f"Faltando: {', '.join(faltando_sem_fundo)}"
            )
            aviso(mensagem)
            raise RuntimeError(mensagem)
        log(f"Pasta sem fundo concluída: {sem_fundo}")
    else:
        log("Pasta sem fundo já está completa; etapa ignorada.")

    if fundo_branco_path is None:
        raise FileNotFoundError(
            "Nenhum fundo branco foi cadastrado. "
            "Adicione-o na aba Configurações antes da Produção."
        )
    assinatura_fundo_branco = _fingerprint_etapa(
        {
            "version": 1,
            "imagens": _assinatura_imagens(sem_fundo, imagens_ordem),
            "fundo_branco": _assinatura_arquivo(fundo_branco_path),
            "sombra_altura": sombra_altura,
        }
    )
    if _etapa_precisa_reprocessar(
        PASTA_FUNDO_BRANCO,
        fundo_branco,
        assinatura_fundo_branco,
        _etapa_tem_saidas_imagem(fundo_branco, imagens_ordem),
        sem_fundo_reconstruido,
        log,
    ):
        log(f"Atualizando fundo branco: {fundo_branco}")
        from Tratar_midias.d__Trocar_Fundo_IMG import Trocar_fundo

        with tempfile.TemporaryDirectory(
            prefix="hen-place-fundo-branco-"
        ) as pasta_temporaria:
            temporaria = Path(pasta_temporaria)
            entrada_branca = temporaria / "entrada"
            resultado_branco = temporaria / "resultado"
            _copiar_selecionadas(
                sem_fundo,
                entrada_branca,
                imagens_ordem,
                preferir_png=True,
            )
            Trocar_fundo(
                str(entrada_branca),
                str(resultado_branco),
                str(fundo_branco_path),
                sombra_altura,
                progress=log,
            )
            geradas_brancas = {
                caminho.stem.casefold()
                for caminho in resultado_branco.iterdir()
                if caminho.is_file()
                and caminho.suffix.lower() in IMAGE_EXTENSIONS
            }
            faltando_branco = [
                Path(nome).stem
                for nome in imagens_ordem
                if Path(nome).stem.casefold() not in geradas_brancas
            ]
            if faltando_branco:
                raise RuntimeError(
                    "O fundo branco não foi gerado para todas as imagens: "
                    + ", ".join(faltando_branco)
                )
            _copiar_resultados_por_stem(resultado_branco, fundo_branco)
        log(f"Fundo branco concluído: {fundo_branco}")
    _gravar_assinatura_etapa(fundo_branco, assinatura_fundo_branco)

    nomes_medida_jpg = _nomes_saida_jpg(imagens_medida)
    assinatura_medidas = _fingerprint_etapa(
        {
            "version": 1,
            "referencia": referencia,
            "imagens": _assinatura_imagens(sem_fundo, imagens_medida),
            "fundo_medida": _assinatura_arquivo(medida_path),
            "logo": _assinatura_arquivo(logo_path),
            "sombra_altura": sombra_altura,
            "tipo_kit": tipo_kit_config,
            "tipo_medidas": tipo_medidas,
            "perfil_social": perfil_social,
            "nomes_saida": sorted(nomes_medida_jpg),
        }
    )
    if _etapa_precisa_reprocessar(
        PASTA_MEDIDAS,
        medidas_finais,
        assinatura_medidas,
        _etapa_tem_arquivos(medidas_finais, nomes_medida_jpg),
        sem_fundo_reconstruido,
        log,
    ):
        log(f"Gerando imagens finais de medidas: {medidas_finais}")
        medidas_finais.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="hen-place-medidas-"
        ) as pasta_temporaria:
            temporaria = Path(pasta_temporaria)
            entrada_medidas = temporaria / "entrada"
            fundo_medidas_temp = temporaria / "fundo"
            medidas_temp = temporaria / "medidas"
            final_temp = temporaria / "final"
            _copiar_selecionadas(
                sem_fundo,
                entrada_medidas,
                imagens_medida,
                preferir_png=True,
            )
            from Tratar_midias.d__Trocar_Fundo_IMG import Trocar_fundo

            Trocar_fundo(
                str(entrada_medidas),
                str(fundo_medidas_temp),
                str(medida_path),
                sombra_altura,
                progress=log,
            )
            from Tratar_midias.f__Medidas_Graficos import Colocar_medidas

            Colocar_medidas(
                str(fundo_medidas_temp),
                str(medidas_temp),
                tipo_kit_config,
                tipo_medidas,
                progress=log,
            )
            from Tratar_midias.e__Colocar_Logos_Ref import Adicionar_logo_completa

            Adicionar_logo_completa(
                str(medidas_temp),
                str(final_temp),
                str(logo_path) if logo_path else None,
                perfil_social,
                "",
                "Sim",
                progress=log,
            )
            arquivos_finais = sorted(
                caminho
                for caminho in final_temp.iterdir()
                if caminho.is_file()
                and caminho.suffix.lower() in IMAGE_EXTENSIONS
            )
            if not arquivos_finais:
                raise RuntimeError("Nenhuma imagem final de medidas foi gerada.")
            _copiar_resultados_por_stem(final_temp, medidas_finais)
        log(f"Imagens finais de medidas concluídas: {medidas_finais}")

    faltando_medidas = sorted(
        nome
        for nome in nomes_medida_jpg
        if not (medidas_finais / nome).is_file()
    )
    if faltando_medidas:
        raise RuntimeError(
            f"{PASTA_MEDIDAS} não contém todos os JPGs esperados: "
            + ", ".join(faltando_medidas)
        )
    _gravar_assinatura_etapa(medidas_finais, assinatura_medidas)

    if fundo_capa_path is None:
        log(
            f"Nenhum fundo de capa selecionado; {PASTA_FUNDO_CAPA} "
            "não receberá novas imagens. Os arquivos existentes foram preservados."
        )
    else:
        assinatura_capa = _fingerprint_etapa(
            {
                "version": 1,
                "imagens_sem_fundo": _assinatura_imagens(
                    sem_fundo,
                    imagens_ordem,
                ),
                "fundo_capa": _assinatura_arquivo(fundo_capa_path),
                "sombra_altura": sombra_altura,
            }
        )
        if _etapa_precisa_reprocessar(
            PASTA_FUNDO_CAPA,
            fundo_capa,
            assinatura_capa,
            _etapa_tem_saidas_imagem(fundo_capa, imagens_ordem),
            sem_fundo_reconstruido,
            log,
        ):
            log(f"Gerando fundo de capa: {fundo_capa}")
            with tempfile.TemporaryDirectory(
                prefix="hen-place-fundo-capa-"
            ) as pasta_temporaria:
                temporaria = Path(pasta_temporaria)
                entrada_capa = temporaria / "entrada"
                saida_capa = temporaria / "resultado"
                _copiar_selecionadas(
                    sem_fundo,
                    entrada_capa,
                    imagens_ordem,
                    preferir_png=True,
                )
                from Tratar_midias.d__Trocar_Fundo_IMG import Trocar_fundo

                Trocar_fundo(
                    str(entrada_capa),
                    str(saida_capa),
                    str(fundo_capa_path),
                    sombra_altura,
                    progress=log,
                )
                if not _etapa_tem_saidas_imagem(saida_capa, imagens_ordem):
                    raise RuntimeError(
                        "A etapa de fundo de capa não gerou todas as imagens "
                        "esperadas; os arquivos anteriores foram preservados."
                    )
                _copiar_resultados_por_stem(saida_capa, fundo_capa)
            log(f"Imagens de fundo de capa concluídas: {fundo_capa}")
        _gravar_assinatura_etapa(fundo_capa, assinatura_capa)

    _gravar_vendas(
        produto,
        tipo_kit_config,
        medidas_finais,
        nomes_medida_jpg,
    )

    videos = [pasta / nome for nome in videos_manifesto]
    video_nome = f"video_{referencia}.mp4"
    video_output = video_dir / video_nome
    assinatura_video = _fingerprint_etapa(
        {
            "version": 1,
            "referencia": referencia,
            "video": _assinatura_arquivo(videos[0]) if videos else None,
            "musica": (
                _assinatura_recurso("musica", musica_nome)
                if videos and volume_musica > 0
                else None
            ),
            "logo": (
                _assinatura_recurso("logo_video", usar_primeiro=True)
                if videos
                else None
            ),
            "qr": (
                _assinatura_recurso("qr_video", usar_primeiro=True)
                if videos
                else None
            ),
            "volume_musica": volume_musica,
            "url_loja": url_loja,
            "max_size_mb": 30,
            "max_duration": 59,
        }
    )
    video_existente = next(
        (
            caminho
            for caminho in (video_output,)
            if caminho.is_file() and caminho.stat().st_size > 0
        ),
        None,
    )
    if videos and _etapa_precisa_reprocessar(
        PASTA_VIDEO_CONVERTIDO,
        video_dir,
        assinatura_video,
        video_existente is not None,
        False,
        log,
    ):
        from Tratar_midias.v__Converter_video import Converte_Video_Completo

        musica_path = _recurso_visual("musica", musica_nome, "música")
        if volume_musica > 0 and musica_path is None:
            raise FileNotFoundError(
                "Nenhuma música foi selecionada. Cadastre uma faixa em "
                "Configurações ou escolha volume zero na Produção."
            )
        video_logo_path = _recurso_visual(
            "logo_video",
            None,
            "logo para vídeo",
            usar_primeiro=True,
        )
        qrcode_path = _recurso_visual(
            "qr_video",
            None,
            "QR Code para vídeo",
            usar_primeiro=True,
        )
        log("Convertendo vídeo...")
        with tempfile.TemporaryDirectory(
            prefix="hen-place-video-"
        ) as pasta_temporaria_video:
            resultado_video = Converte_Video_Completo(
                ref=referencia,
                input_video=str(videos[0]),
                pasta_video=pasta_temporaria_video,
                logo_path=str(video_logo_path) if video_logo_path else None,
                som=volume_musica,
                qrcode_path=str(qrcode_path) if qrcode_path else None,
                musica_path=str(musica_path) if musica_path else None,
                link_url=url_loja,
                max_size_mb=30,
                max_duration=59,
                progress=log,
            )
            arquivo_temporario_video = (
                Path(pasta_temporaria_video) / video_nome
            )
            if (
                resultado_video is not True
                or not arquivo_temporario_video.is_file()
                or arquivo_temporario_video.stat().st_size == 0
            ):
                raise RuntimeError(
                    "A conversão do vídeo não foi concluída; a versão "
                    "anterior foi preservada."
                )
            temporario_final = video_output.with_name(
                video_output.name + ".tmp"
            )
            shutil.copy2(arquivo_temporario_video, temporario_final)
            temporario_final.replace(video_output)
        log(f"Vídeo convertido: {video_output}")
    elif not videos:
        log("Nenhum vídeo encontrado; etapa de vídeo ignorada.")
    if videos:
        _gravar_assinatura_etapa(video_dir, assinatura_video)

    (pasta / "formas_venda.json").write_text(
        json.dumps(
            {
                "produto": produto,
                "configuracao_cadastro": tipo_kit_config,
                "formas": formas_venda,
                "grupos": resumo_grupos,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    log("Produção concluída.")
    return str(pasta)