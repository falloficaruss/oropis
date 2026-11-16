from __future__ import annotations

from dataclasses import dataclass
from html import escape
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError

from ..config import AccountCfg

MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_HERO_WIDTH = 2000
MAX_INLINE_WIDTH = 1600
UPLOAD_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}


class UploadError(ValueError):
    pass


@dataclass(frozen=True)
class ProcessedImage:
    data: bytes
    width: int
    height: int
    mime: str = "image/webp"


def process_upload(raw: bytes, *, kind: str) -> ProcessedImage:
    if not raw:
        raise UploadError("choose an image file")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise UploadError("image is larger than 12 MB")
    try:
        image = Image.open(BytesIO(raw))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise UploadError("file is not a readable image") from exc
    if image.format not in UPLOAD_FORMATS:
        raise UploadError("use a JPEG, PNG, or WebP image")
    image = ImageOps.exif_transpose(image) or image
    if image.mode not in ("RGB", "RGBA"):
        if image.mode in ("LA", "P") or "transparency" in image.info:
            image = image.convert("RGBA")
        else:
            image = image.convert("RGB")
    max_width = MAX_HERO_WIDTH if kind == "hero" else MAX_INLINE_WIDTH
    if image.width > max_width:
        height = round(image.height * max_width / image.width)
        image = image.resize((max_width, height), Image.Resampling.LANCZOS)
    output = BytesIO()
    image.save(output, format="WEBP", quality=84, method=6)
    return ProcessedImage(output.getvalue(), image.width, image.height)


def save_upload(cfg: AccountCfg, story_id: int, kind: str, image: ProcessedImage) -> str:
    folder = "heroes" if kind == "hero" else "inline"
    rel = Path("uploads") / folder / str(story_id) / f"{uuid4().hex}.webp"
    target = cfg.root / cfg.site.media_dir / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(image.data)
    return rel.as_posix()


def resolve_media(cfg: AccountCfg, rel: str | Path) -> Path:
    root = (cfg.root / cfg.site.media_dir).resolve()
    target = (root / Path(rel)).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("media path escapes the upload directory") from exc
    if target.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError("unsupported media type")
    return target


def delete_upload(cfg: AccountCfg, rel: str | None) -> None:
    if not rel:
        return
    try:
        path = resolve_media(cfg, rel)
    except ValueError:
        return
    if path.is_file():
        path.unlink()
    parent = path.parent
    root = (cfg.root / cfg.site.media_dir).resolve()
    while parent != root and parent.exists() and not any(parent.iterdir()):
        parent.rmdir()
        parent = parent.parent


def media_url(rel: str) -> str:
    return f"/media/{rel}"


def figure_markup(
    rel: str,
    *,
    alt: str,
    caption: str = "",
    credit: str = "",
    width: int | None = None,
    height: int | None = None,
) -> str:
    attrs = [
        f'src="{escape(media_url(rel), quote=True)}"',
        f'alt="{escape(alt, quote=True)}"',
    ]
    if width:
        attrs.append(f'width="{int(width)}"')
    if height:
        attrs.append(f'height="{int(height)}"')
    attrs.extend(['loading="lazy"', 'decoding="async"'])
    lines = ['<figure class="article-figure">', f'  <img {" ".join(attrs)}>']
    if caption or credit:
        detail = escape(caption)
        if credit:
            credit_html = f'<span class="image-credit">Credit: {escape(credit)}</span>'
            detail = f"{detail} {credit_html}".strip()
        lines.append(f"  <figcaption>{detail}</figcaption>")
    lines.append("</figure>")
    return "\n".join(lines)
