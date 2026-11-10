from __future__ import annotations

from io import BytesIO
from pathlib import Path
import tempfile

from PIL import Image

QUALIDADE = 90
EXTENSOES = (".jpg", ".jpeg", ".png", ".webp")
LIMITE_BYTES = 2_000_000


def _format_for(path: Path) -> str:
    return {
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".png": "PNG",
        ".webp": "WEBP",
    }[path.suffix.lower()]


def _write_atomically(path: Path, data: bytes) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{path.stem}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(data)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _reduce_file(path: Path, fator: float, limite_bytes: int) -> None:
    if path.stat().st_size <= limite_bytes:
        return

    image_format = _format_for(path)
    with Image.open(path) as opened:
        has_alpha = (
            "A" in opened.getbands()
            or "transparency" in opened.info
        )
        keep_alpha = has_alpha and image_format in {"PNG", "WEBP"}
        original = opened.convert("RGBA" if keep_alpha else "RGB")

    original_width, original_height = original.size
    previous_size: tuple[int, int] | None = None
    resampling = getattr(Image, "Resampling", Image).LANCZOS

    for attempt in range(32):
        scale = fator**attempt
        size = (
            max(1, round(original_width * scale)),
            max(1, round(original_height * scale)),
        )
        if size == previous_size:
            break
        previous_size = size

        resized = (
            original.copy()
            if size == original.size
            else original.resize(size, resampling)
        )
        options: dict[str, object]
        if image_format == "JPEG":
            options = {"quality": QUALIDADE, "optimize": True}
        elif image_format == "PNG":
            options = {"optimize": True, "compress_level": 9}
        else:
            options = {"quality": QUALIDADE, "method": 6}

        output = BytesIO()
        resized.save(output, format=image_format, **options)
        data = output.getvalue()
        if len(data) <= limite_bytes:
            _write_atomically(path, data)
            return
        if size == (1, 1):
            break

    raise ValueError(
        f"Não foi possível reduzir {path.name} para menos de "
        f"{limite_bytes:,} bytes sem chegar a uma imagem vazia."
    )


def Reduzir_IMG(
    pasta_entrada: str | Path,
    fator: float = 0.5,
    limite_bytes: int = LIMITE_BYTES,
) -> None:
    """Reduz imagens acima do limite, preservando o formato e a transparência."""
    entrada = Path(pasta_entrada)
    if not 0 < fator < 1:
        raise ValueError("O fator de redução deve estar entre 0 e 1.")
    if limite_bytes <= 0:
        raise ValueError("O limite de bytes deve ser maior que zero.")
    if not entrada.exists():
        raise FileNotFoundError(f"Pasta ou imagem não encontrada: {entrada}")

    if entrada.is_file():
        imagens = [entrada] if entrada.suffix.lower() in EXTENSOES else []
    else:
        imagens = sorted(
            (
                path
                for path in entrada.rglob("*")
                if path.is_file() and path.suffix.lower() in EXTENSOES
            ),
            key=lambda path: str(path).casefold(),
        )

    for caminho_img in imagens:
        _reduce_file(caminho_img, fator, limite_bytes)


if __name__ == "__main__":
    Reduzir_IMG(
        r"C:\Users\henri\Downloads\PRODUTOS\tttt",
        fator=0.5,
    )
