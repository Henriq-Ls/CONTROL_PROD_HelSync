"""Serviços para processar mídias sem alterar o cadastro do produto."""

from __future__ import annotations

import os
import re
import shutil
import tempfile
import unicodedata
from pathlib import Path
from typing import Callable

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv")
AVULSAS_OUTPUT_FOLDER = "H_Arq_avulsas"
IMAGE_OUTPUT_FOLDERS = ("b_sem_fundo", "c_fundo_branco", "d_medidas")
VIDEO_OUTPUT_FOLDER = "F_video_shopee"
MAX_VIDEO_SIZE_MB = 30
MAX_VIDEO_DURATION_SECONDS = 59
MEASURE_TYPES = (
    "alt x larg x esp",
    "alt x larg x comp",
    "alt x diam x esp",
    "alt x diam",
)


def _progress(callback: Callable[[str], None] | None, message: str) -> None:
    if callback:
        callback(message)


def _normalize_number(value: str, label: str, *, allow_zero: bool = False) -> str:
    from decimal import Decimal, InvalidOperation

    original = str(value or "").strip().replace(",", ".")
    try:
        number = Decimal(original)
    except InvalidOperation as exc:
        raise ValueError(f"Informe um valor numérico válido para {label}.") from exc
    if not number.is_finite() or number < 0 or (number == 0 and not allow_zero):
        regra = "maior ou igual a zero" if allow_zero else "maior que zero"
        raise ValueError(f"{label.capitalize()} deve ser {regra}.")
    return format(number.normalize(), "f")


def _dimensions_for_name(
    height: str,
    width: str,
    third_dimension: str,
    weight: str,
    measure_type: str,
) -> tuple[str, str]:
    if measure_type not in MEASURE_TYPES:
        raise ValueError("Selecione um tipo de medida válido.")

    height_value = _normalize_number(height, "altura")
    width_label = "diâmetro" if "diam" in measure_type else "largura"
    width_value = _normalize_number(width, width_label)

    if measure_type == "alt x diam":
        dimensions = f"{height_value}x{width_value}"
    else:
        third_value = _normalize_number(third_dimension, "terceira medida")
        dimensions = f"{height_value}x{width_value}x{third_value}"

    weight_value = (
        _normalize_number(weight, "peso", allow_zero=True) + "gm"
        if str(weight or "").strip()
        else "0gm"
    )
    return dimensions, weight_value


def _safe_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_value).strip("-").lower()
    return slug[:60] or "imagem"


def _file_for_stem(folder: Path, stem: str) -> Path | None:
    if not folder.is_dir():
        return None
    matches = sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.stem.casefold() == stem.casefold()
    )
    return matches[0] if matches else None


def _compor_fundo_branco(source: Path, destination: Path) -> None:
    from PIL import Image, ImageOps

    with Image.open(source) as original:
        foreground = ImageOps.exif_transpose(original).convert("RGBA")
    background = Image.new("RGBA", foreground.size, (255, 255, 255, 255))
    background.alpha_composite(foreground)
    background.convert("RGB").save(destination, "JPEG", quality=97, optimize=True)


def _copy_without_overwrite(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copy2(source, temporary)
        try:
            # Linking within the same destination directory publishes the
            # complete file atomically and refuses to replace an existing one.
            os.link(temporary, destination)
        except FileExistsError:
            raise
        except OSError:
            # Some filesystems do not support hard links. Keep the no-clobber
            # guarantee with exclusive creation as a portable fallback.
            created = False
            try:
                with temporary.open("rb") as source_stream:
                    with destination.open("xb") as destination_stream:
                        created = True
                        shutil.copyfileobj(source_stream, destination_stream)
                shutil.copystat(temporary, destination)
            except Exception:
                if created:
                    destination.unlink(missing_ok=True)
                raise
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    temporary.unlink(missing_ok=True)
    return destination


def processar_imagens_avulsas(
    image_paths: list[str],
    destination_folder: str,
    height: str,
    width: str,
    third_dimension: str,
    weight: str,
    measure_type: str,
    measure_background_path: str = "",
    progress: Callable[[str], None] | None = None,
) -> list[str]:
    """Processa imagens selecionadas e salva cópias em pastas de saída próprias."""
    sources = [Path(path).expanduser() for path in image_paths]
    if not sources:
        raise ValueError("Adicione pelo menos uma imagem.")
    for source in sources:
        if not source.is_file() or source.suffix.casefold() not in IMAGE_EXTENSIONS:
            raise FileNotFoundError(f"Imagem inválida ou indisponível: {source}")

    dimensions, weight_value = _dimensions_for_name(
        height,
        width,
        third_dimension,
        weight,
        measure_type,
    )
    background = Path(measure_background_path).expanduser() if measure_background_path else None
    if background is not None and not background.is_file():
        raise FileNotFoundError(f"Fundo de medidas indisponível: {background}")

    destination = Path(destination_folder).expanduser()
    if not destination.is_dir():
        raise FileNotFoundError(
            f"Selecione uma pasta de destino existente: {destination}"
        )
    output_root = destination / AVULSAS_OUTPUT_FOLDER
    output_root.mkdir(parents=True, exist_ok=True)
    output_folders = {
        folder_name: output_root / folder_name
        for folder_name in IMAGE_OUTPUT_FOLDERS
    }

    with tempfile.TemporaryDirectory(
        prefix=".hen-place-midias-avulsas-",
        dir=output_root,
    ) as temporary_root:
        temporary = Path(temporary_root)
        input_folder = temporary / "entrada"
        adjusted_folder = temporary / "ajustada"
        removed_folder = temporary / "sem_fundo"
        white_folder = temporary / "fundo_branco"
        measure_input_folder = temporary / "entrada_medidas"
        measure_output_folder = temporary / "medidas"
        for folder in (
            input_folder,
            adjusted_folder,
            removed_folder,
            white_folder,
            measure_input_folder,
            measure_output_folder,
        ):
            folder.mkdir()

        stems: list[str] = []
        from PIL import Image, ImageOps

        for index, source in enumerate(sources, start=1):
            slug = _safe_slug(source.stem)
            stem_prefix = f"avulsa-{slug}-{index:02d}"
            stem = f"{stem_prefix}_{dimensions}_{weight_value}"
            suffix_index = 2
            while any(
                (folder / f"{stem}{extension}").exists()
                for folder in output_folders.values()
                for extension in IMAGE_EXTENSIONS
            ):
                stem = (
                    f"{stem_prefix}-{suffix_index}_{dimensions}_{weight_value}"
                )
                suffix_index += 1
            stems.append(stem)

            with Image.open(source) as original:
                normalized = ImageOps.exif_transpose(original)
                normalized.save(input_folder / f"{stem}{source.suffix.lower()}")

        _progress(progress, f"Melhorando {len(sources)} imagem(ns)...")
        from Tratar_midias.b__Ajuste_Geral_IMG import Ajuste_IMG

        Ajuste_IMG(str(input_folder), str(adjusted_folder))
        missing_adjusted = [
            stem for stem in stems if _file_for_stem(adjusted_folder, stem) is None
        ]
        if missing_adjusted:
            raise RuntimeError(
                "A melhoria não gerou todas as imagens: "
                + ", ".join(missing_adjusted)
            )

        _progress(progress, "Removendo o fundo das imagens...")
        from Tratar_midias.c__Remove_Refina_IMG import Remove_IMG

        Remove_IMG(str(adjusted_folder), str(removed_folder), progress=progress)
        missing_removed = [
            stem for stem in stems if _file_for_stem(removed_folder, stem) is None
        ]
        if missing_removed:
            raise RuntimeError(
                "A remoção de fundo não gerou todas as imagens: "
                + ", ".join(missing_removed)
            )

        _progress(progress, "Criando as versões com fundo branco...")
        for index, stem in enumerate(stems, start=1):
            source = _file_for_stem(removed_folder, stem)
            if source is None:
                raise FileNotFoundError(f"Imagem sem fundo não encontrada: {stem}")
            _compor_fundo_branco(source, white_folder / f"{stem}.jpg")
            _progress(progress, f"Fundo branco {index}/{len(stems)}: {source.name}")

        measure_input = removed_folder
        if background is not None:
            _progress(progress, "Aplicando o fundo salvo às imagens de medidas...")
            from Tratar_midias.d__Trocar_Fundo_IMG import Trocar_fundo

            Trocar_fundo(
                str(removed_folder),
                str(measure_input_folder),
                str(background),
                progress=progress,
            )
            measure_input = measure_input_folder

        _progress(progress, "Desenhando as medidas nas imagens...")
        from Tratar_midias.f__Medidas_Graficos import Colocar_medidas

        Colocar_medidas(
            str(measure_input),
            str(measure_output_folder),
            None,
            measure_type,
            progress=progress,
        )
        missing_measures = [
            stem for stem in stems if not (measure_output_folder / f"{stem}.jpg").is_file()
        ]
        if missing_measures:
            raise RuntimeError(
                "A etapa de medidas não gerou todas as imagens: "
                + ", ".join(missing_measures)
            )

        stage_sources: dict[str, list[Path]] = {
            "b_sem_fundo": [
                _file_for_stem(removed_folder, stem) for stem in stems
            ],
            "c_fundo_branco": [
                white_folder / f"{stem}.jpg" for stem in stems
            ],
            "d_medidas": [
                measure_output_folder / f"{stem}.jpg" for stem in stems
            ],
        }
        written: list[Path] = []
        try:
            for stem_index, stem in enumerate(stems):
                for folder_name, files in stage_sources.items():
                    source = files[stem_index]
                    if source is None or not source.is_file():
                        raise FileNotFoundError(
                            f"Saída de {folder_name} ausente para {stem}."
                        )
                    target = output_folders[folder_name] / f"{stem}{source.suffix.lower()}"
                    written.append(_copy_without_overwrite(source, target))
            _progress(progress, f"Imagens salvas na pasta: {output_root}")
            return [str(path) for path in written]
        except Exception:
            for path in reversed(written):
                path.unlink(missing_ok=True)
            raise


def converter_video_avulso(
    video_path: str,
    destination_folder: str,
    music_path: str = "",
    music_volume: float = 0.25,
    progress: Callable[[str], None] | None = None,
) -> str:
    """Converte um vídeo avulso usando a mesma receita da Produção."""
    source = Path(video_path).expanduser()
    if not source.is_file() or source.suffix.casefold() not in VIDEO_EXTENSIONS:
        raise FileNotFoundError(f"Vídeo inválido ou indisponível: {source}")
    try:
        volume = float(music_volume)
    except (TypeError, ValueError) as exc:
        raise ValueError("O volume da música não é válido.") from exc
    if not 0 <= volume <= 1:
        raise ValueError("O volume da música deve estar entre 0 e 1.")

    music = Path(music_path).expanduser() if music_path else None
    if volume > 0 and music is None:
        raise ValueError(
            "Escolha uma faixa em Configurações ou selecione volume zero."
        )
    if music is not None and not music.is_file():
        raise FileNotFoundError(f"Faixa de música indisponível: {music}")

    destination = Path(destination_folder).expanduser()
    if not destination.is_dir():
        raise FileNotFoundError(
            f"Selecione uma pasta de destino existente: {destination}"
        )
    output_root = destination / AVULSAS_OUTPUT_FOLDER
    output_root.mkdir(parents=True, exist_ok=True)
    video_folder = output_root / VIDEO_OUTPUT_FOLDER
    video_folder.mkdir(parents=True, exist_ok=True)

    from _APPDATA_ import appdata

    appdata.inicializar()

    def first_resource(category: str) -> Path | None:
        candidates = appdata.listar_midias(category)
        if not candidates:
            return None
        path = Path(appdata.pasta_midia_categoria(category)) / candidates[0]
        return path if path.is_file() else None

    video_logo = first_resource("logo_video")
    qr_code = first_resource("qr_video")
    config = appdata.ler_config()
    brand = config.get("marca", {})
    if not isinstance(brand, dict):
        brand = {}
    store_url = str(brand.get("url_loja") or "").strip()

    stem = _safe_slug(source.stem)
    output_ref = stem
    suffix_index = 2
    while (video_folder / f"video_{output_ref}.mp4").exists():
        output_ref = f"{stem}-{suffix_index}"
        suffix_index += 1
    output_path = video_folder / f"video_{output_ref}.mp4"

    _progress(progress, f"Convertendo vídeo: {source.name}")
    with tempfile.TemporaryDirectory(
        prefix=".hen-place-video-avulso-",
        dir=output_root,
    ) as temporary_root:
        from Tratar_midias.v__Converter_video import Converte_Video_Completo

        converted = Converte_Video_Completo(
            ref=output_ref,
            input_video=str(source),
            pasta_video=temporary_root,
            logo_path=str(video_logo) if video_logo else None,
            qrcode_path=str(qr_code) if qr_code else None,
            musica_path=str(music) if music else None,
            som=volume,
            link_url=store_url,
            max_size_mb=MAX_VIDEO_SIZE_MB,
            max_duration=MAX_VIDEO_DURATION_SECONDS,
            progress=progress,
        )
        temporary_video = Path(temporary_root) / output_path.name
        if (
            converted is not True
            or not temporary_video.is_file()
            or temporary_video.stat().st_size == 0
        ):
            raise RuntimeError(
                "A conversão não terminou corretamente. "
                "O vídeo original foi mantido."
            )
        tamanho_mib = temporary_video.stat().st_size / (1024 * 1024)
        if tamanho_mib > MAX_VIDEO_SIZE_MB:
            raise RuntimeError(
                "O vídeo permaneceu acima do limite de "
                f"{MAX_VIDEO_SIZE_MB} MB após a compressão "
                f"({tamanho_mib:.1f} MB). O original foi mantido."
            )
        _copy_without_overwrite(temporary_video, output_path)

    _progress(progress, f"Vídeo pronto: {output_path}")
    return str(output_path)
