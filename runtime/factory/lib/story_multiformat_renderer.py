from __future__ import annotations

import hashlib
import html
import json
import re
import textwrap
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

SCHEMA_ID = "valo.story-manifest.v1"
PPTX_WIDTH_EMU = 12_192_000
PPTX_HEIGHT_EMU = 6_858_000
PDF_WIDTH = 960
PDF_HEIGHT = 540


class StoryRenderError(ValueError):
    """Raised when a story manifest is invalid or cannot be rendered."""


@dataclass(frozen=True)
class StoryTheme:
    background: str = "0B0D10"
    foreground: str = "F4F7FB"
    accent: str = "5EA1FF"
    muted: str = "AAB4C3"


@dataclass(frozen=True)
class StorySlide:
    title: str
    kicker: str = ""
    body: tuple[str, ...] = ()
    footer: str = ""


@dataclass(frozen=True)
class StoryManifest:
    title: str
    subtitle: str
    theme: StoryTheme
    slides: tuple[StorySlide, ...]
    source_sha256: str


def _normalize_hex(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise StoryRenderError(f"theme.{field} must be a string")
    raw = value.strip().removeprefix("#").upper()
    if not re.fullmatch(r"[0-9A-F]{6}", raw):
        raise StoryRenderError(f"theme.{field} must be a 6-digit hex colour")
    return raw


def canonical_source_bytes(raw: dict[str, Any]) -> bytes:
    return json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def source_sha256(raw: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_source_bytes(raw)).hexdigest()


def load_manifest(path: str | Path) -> StoryManifest:
    manifest_path = Path(path)
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise StoryRenderError(f"cannot read manifest: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise StoryRenderError(f"invalid JSON manifest: {exc}") from exc
    return parse_manifest(raw)


def parse_manifest(raw: dict[str, Any]) -> StoryManifest:
    if not isinstance(raw, dict):
        raise StoryRenderError("manifest root must be an object")
    if raw.get("schema") != SCHEMA_ID:
        raise StoryRenderError(f"schema must be {SCHEMA_ID}")

    title = raw.get("title")
    if not isinstance(title, str) or not title.strip():
        raise StoryRenderError("title must be a non-empty string")
    subtitle = raw.get("subtitle", "")
    if not isinstance(subtitle, str):
        raise StoryRenderError("subtitle must be a string")

    theme_raw = raw.get("theme", {})
    if not isinstance(theme_raw, dict):
        raise StoryRenderError("theme must be an object")
    theme = StoryTheme(
        background=_normalize_hex(theme_raw.get("background", "0B0D10"), "background"),
        foreground=_normalize_hex(theme_raw.get("foreground", "F4F7FB"), "foreground"),
        accent=_normalize_hex(theme_raw.get("accent", "5EA1FF"), "accent"),
        muted=_normalize_hex(theme_raw.get("muted", "AAB4C3"), "muted"),
    )

    slides_raw = raw.get("slides")
    if not isinstance(slides_raw, list) or not slides_raw:
        raise StoryRenderError("slides must be a non-empty array")
    slides: list[StorySlide] = []
    for index, item in enumerate(slides_raw, start=1):
        if not isinstance(item, dict):
            raise StoryRenderError(f"slides[{index}] must be an object")
        slide_title = item.get("title")
        if not isinstance(slide_title, str) or not slide_title.strip():
            raise StoryRenderError(f"slides[{index}].title must be non-empty")
        kicker = item.get("kicker", "")
        footer = item.get("footer", "")
        body_raw = item.get("body", [])
        if not isinstance(kicker, str) or not isinstance(footer, str):
            raise StoryRenderError(f"slides[{index}] kicker/footer must be strings")
        if not isinstance(body_raw, list) or not all(isinstance(line, str) for line in body_raw):
            raise StoryRenderError(f"slides[{index}].body must be an array of strings")
        slides.append(StorySlide(slide_title.strip(), kicker.strip(), tuple(body_raw), footer.strip()))

    return StoryManifest(
        title=title.strip(),
        subtitle=subtitle.strip(),
        theme=theme,
        slides=tuple(slides),
        source_sha256=source_sha256(raw),
    )


def render_all(manifest: StoryManifest, output_dir: str | Path, stem: str = "story") -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "html": out / f"{stem}.html",
        "pdf": out / f"{stem}.pdf",
        "pptx": out / f"{stem}.pptx",
    }
    paths["html"].write_text(render_html(manifest), encoding="utf-8")
    paths["pdf"].write_bytes(render_pdf(manifest))
    paths["pptx"].write_bytes(render_pptx(manifest))
    return paths


def render_html(manifest: StoryManifest) -> str:
    t = manifest.theme
    sections: list[str] = []
    for idx, slide in enumerate(manifest.slides, start=1):
        body = "".join(f"<li>{html.escape(line)}</li>" for line in slide.body)
        kicker = f'<div class="kicker">{html.escape(slide.kicker)}</div>' if slide.kicker else ""
        footer = f'<div class="footer">{html.escape(slide.footer)}</div>' if slide.footer else ""
        sections.append(
            f'<section class="slide" id="slide-{idx}" data-slide="{idx}">'
            f'{kicker}<h2>{html.escape(slide.title)}</h2><ul>{body}</ul>{footer}'
            f'<div class="counter">{idx}/{len(manifest.slides)}</div></section>'
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="valo-source-sha256" content="{manifest.source_sha256}">
<title>{html.escape(manifest.title)}</title>
<style>
:root{{--bg:#{t.background};--fg:#{t.foreground};--accent:#{t.accent};--muted:#{t.muted};}}
*{{box-sizing:border-box}} html,body{{margin:0;background:var(--bg);color:var(--fg);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
body{{overflow:hidden}} .deck{{height:100vh;display:flex;transition:transform .32s ease}} .slide{{min-width:100vw;height:100vh;padding:8vh 8vw;position:relative;display:flex;flex-direction:column;justify-content:center;background:var(--bg)}}
.kicker{{font-size:clamp(14px,1.3vw,22px);letter-spacing:.12em;text-transform:uppercase;color:var(--accent);margin-bottom:1.4rem}} h2{{font-size:clamp(40px,6vw,88px);line-height:.98;margin:0 0 2.2rem;max-width:15ch}}
ul{{list-style:none;padding:0;margin:0;max-width:72ch}} li{{font-size:clamp(20px,2vw,34px);line-height:1.28;margin:.75rem 0;color:var(--fg)}} li::before{{content:"—";color:var(--accent);margin-right:.75em}}
.footer{{position:absolute;left:8vw;bottom:6vh;color:var(--muted);font-size:clamp(12px,1vw,18px)}} .counter{{position:absolute;right:8vw;bottom:6vh;color:var(--muted)}}
.source{{position:fixed;top:1rem;right:1rem;font:10px ui-monospace,monospace;color:var(--muted);opacity:.45;z-index:3}} .nav{{position:fixed;right:2rem;top:50%;transform:translateY(-50%);z-index:4;display:flex;flex-direction:column;gap:.5rem}} .nav button{{border:1px solid #{t.muted};background:transparent;color:var(--fg);width:42px;height:42px;border-radius:50%;cursor:pointer}}
@media print{{body{{overflow:visible}} .deck{{display:block;transform:none!important;height:auto}} .slide{{width:13.333in;min-width:13.333in;height:7.5in;page-break-after:always;padding:.75in 1in}} .nav,.source{{display:none}}}}
</style>
</head>
<body data-source-sha256="{manifest.source_sha256}">
<div class="source">source {manifest.source_sha256[:12]}</div>
<div class="nav"><button type="button" aria-label="Previous slide" onclick="move(-1)">↑</button><button type="button" aria-label="Next slide" onclick="move(1)">↓</button></div>
<main class="deck" id="deck">{''.join(sections)}</main>
<script>
let index=0;const total={len(manifest.slides)};const deck=document.getElementById('deck');
function show(){{deck.style.transform=`translateX(${{-index*100}}vw)`}}function move(delta){{index=Math.max(0,Math.min(total-1,index+delta));show()}}
addEventListener('keydown',e=>{{if(['ArrowRight','ArrowDown','PageDown',' '].includes(e.key))move(1);if(['ArrowLeft','ArrowUp','PageUp'].includes(e.key))move(-1)}});
</script>
</body></html>"""


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _ascii_pdf_text(value: str) -> str:
    return value.encode("latin-1", errors="replace").decode("latin-1")


def _hex_to_pdf_rgb(value: str) -> tuple[float, float, float]:
    return tuple(int(value[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def _pdf_text_commands(text: str, x: float, y: float, size: float, rgb: tuple[float, float, float]) -> list[str]:
    r, g, b = rgb
    safe = _pdf_escape(_ascii_pdf_text(text))
    return [f"{r:.4f} {g:.4f} {b:.4f} rg", "BT", f"/F1 {size:.1f} Tf", f"{x:.1f} {y:.1f} Td", f"({safe}) Tj", "ET"]


def render_pdf(manifest: StoryManifest) -> bytes:
    bg = _hex_to_pdf_rgb(manifest.theme.background)
    fg = _hex_to_pdf_rgb(manifest.theme.foreground)
    accent = _hex_to_pdf_rgb(manifest.theme.accent)
    muted = _hex_to_pdf_rgb(manifest.theme.muted)

    streams: list[bytes] = []
    for index, slide in enumerate(manifest.slides, start=1):
        commands = [
            "q",
            f"{bg[0]:.4f} {bg[1]:.4f} {bg[2]:.4f} rg",
            f"0 0 {PDF_WIDTH} {PDF_HEIGHT} re f",
            "Q",
        ]
        y = 455.0
        if slide.kicker:
            commands += _pdf_text_commands(slide.kicker.upper(), 78, y, 14, accent)
            y -= 56
        title_lines = textwrap.wrap(slide.title, width=30) or [slide.title]
        for line in title_lines[:3]:
            commands += _pdf_text_commands(line, 78, y, 36, fg)
            y -= 44
        y -= 12
        for bullet in slide.body[:7]:
            wrapped = textwrap.wrap(bullet, width=68) or [bullet]
            commands += _pdf_text_commands("- " + wrapped[0], 90, y, 18, fg)
            y -= 25
            for cont in wrapped[1:3]:
                commands += _pdf_text_commands("  " + cont, 90, y, 18, fg)
                y -= 25
            y -= 5
        if slide.footer:
            commands += _pdf_text_commands(slide.footer, 78, 42, 10, muted)
        commands += _pdf_text_commands(f"{index}/{len(manifest.slides)}", 846, 42, 10, muted)
        streams.append(("\n".join(commands) + "\n").encode("latin-1"))

    objects: list[bytes] = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)

    catalog_id = add(b"")
    pages_id = add(b"")
    font_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids: list[int] = []
    content_ids: list[int] = []
    for stream in streams:
        content_ids.append(add(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"endstream"))
        page_ids.append(add(b""))
    info_id = add(
        f"<< /Title ({_pdf_escape(_ascii_pdf_text(manifest.title))}) /Producer (VALO Factory story renderer) /Subject (source_sha256={manifest.source_sha256}) >>".encode("latin-1")
    )

    objects[catalog_id - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode()
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[pages_id - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode()
    for page_id, content_id in zip(page_ids, content_ids):
        objects[page_id - 1] = (
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PDF_WIDTH} {PDF_HEIGHT}] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode()

    out = BytesIO()
    out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{idx} 0 obj\n".encode())
        out.write(obj)
        out.write(b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objects)+1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.write(f"{offset:010d} 00000 n \n".encode())
    out.write(
        f"trailer\n<< /Size {len(objects)+1} /Root {catalog_id} 0 R /Info {info_id} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return out.getvalue()


def _pptx_paragraph(text: str, size: int, color: str, bold: bool = False) -> str:
    b = ' b="1"' if bold else ""
    return (
        '<a:p><a:r><a:rPr lang="en-US" sz="%d"%s><a:solidFill><a:srgbClr val="%s"/></a:solidFill></a:rPr>'
        '<a:t>%s</a:t></a:r><a:endParaRPr lang="en-US" sz="%d"/></a:p>'
    ) % (size, b, color, xml_escape(text), size)


def _pptx_textbox(shape_id: int, name: str, x: int, y: int, cx: int, cy: int, paragraphs: str) -> str:
    return f'''<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="{xml_escape(name)}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr>
<p:txBody><a:bodyPr wrap="square"/><a:lstStyle/>{paragraphs}</p:txBody></p:sp>'''


def _slide_xml(manifest: StoryManifest, slide: StorySlide, index: int) -> str:
    t = manifest.theme
    shapes: list[str] = []
    shape_id = 2
    if slide.kicker:
        shapes.append(_pptx_textbox(shape_id, "Kicker", 720000, 540000, 10500000, 420000, _pptx_paragraph(slide.kicker.upper(), 1600, t.accent, True)))
        shape_id += 1
    shapes.append(_pptx_textbox(shape_id, "Title", 720000, 1100000, 10500000, 1500000, _pptx_paragraph(slide.title, 3600, t.foreground, True)))
    shape_id += 1
    body_paragraphs = "".join(_pptx_paragraph("- " + line, 2000, t.foreground, False) for line in slide.body[:8])
    shapes.append(_pptx_textbox(shape_id, "Body", 800000, 2850000, 10400000, 2500000, body_paragraphs))
    shape_id += 1
    if slide.footer:
        shapes.append(_pptx_textbox(shape_id, "Footer", 720000, 6150000, 9300000, 300000, _pptx_paragraph(slide.footer, 1000, t.muted)))
        shape_id += 1
    shapes.append(_pptx_textbox(shape_id, "Counter", 10800000, 6150000, 600000, 300000, _pptx_paragraph(f"{index}/{len(manifest.slides)}", 1000, t.muted)))

    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="{t.background}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>{''.join(shapes)}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'''


def _zip_write(zf: zipfile.ZipFile, name: str, content: str | bytes) -> None:
    info = zipfile.ZipInfo(name)
    info.date_time = (1980, 1, 1, 0, 0, 0)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    data = content.encode("utf-8") if isinstance(content, str) else content
    zf.writestr(info, data)


def render_pptx(manifest: StoryManifest) -> bytes:
    slide_count = len(manifest.slides)
    slide_overrides = "".join(
        f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, slide_count + 1)
    )
    content_types = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/><Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/><Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/><Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>{slide_overrides}<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>'''

    slide_ids = "".join(f'<p:sldId id="{255+i}" r:id="rId{2+i}"/>' for i in range(1, slide_count + 1))
    presentation = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:sldIdLst>{slide_ids}</p:sldIdLst><p:sldSz cx="{PPTX_WIDTH_EMU}" cy="{PPTX_HEIGHT_EMU}" type="screen16x9"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>'''
    presentation_rels = ['<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>']
    presentation_rels.extend(
        f'<Relationship Id="rId{2+i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>'
        for i in range(1, slide_count + 1)
    )
    presentation_rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + "".join(presentation_rels) + '</Relationships>'

    root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>'''
    slide_master = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld name="Master"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMap accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" bg1="lt1" bg2="lt2" folHlink="folHlink" hlink="hlink" tx1="dk1" tx2="dk2"/><p:sldLayoutIdLst><p:sldLayoutId id="1" r:id="rId1"/></p:sldLayoutIdLst><p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>'''
    slide_master_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/></Relationships>'''
    slide_layout = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1"><p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>'''
    slide_layout_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/></Relationships>'''
    theme = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="VALO Story"><a:themeElements><a:clrScheme name="VALO"><a:dk1><a:srgbClr val="{manifest.theme.background}"/></a:dk1><a:lt1><a:srgbClr val="{manifest.theme.foreground}"/></a:lt1><a:dk2><a:srgbClr val="20242B"/></a:dk2><a:lt2><a:srgbClr val="E8EDF5"/></a:lt2><a:accent1><a:srgbClr val="{manifest.theme.accent}"/></a:accent1><a:accent2><a:srgbClr val="7399C6"/></a:accent2><a:accent3><a:srgbClr val="7CC4A3"/></a:accent3><a:accent4><a:srgbClr val="D9A66C"/></a:accent4><a:accent5><a:srgbClr val="B98AD8"/></a:accent5><a:accent6><a:srgbClr val="D47474"/></a:accent6><a:hlink><a:srgbClr val="0563C1"/></a:hlink><a:folHlink><a:srgbClr val="954F72"/></a:folHlink></a:clrScheme><a:fontScheme name="VALO"><a:majorFont><a:latin typeface="Aptos Display"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont><a:minorFont><a:latin typeface="Aptos"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme><a:fmtScheme name="VALO"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="6350" cap="flat" cmpd="sng" algn="ctr"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>'''
    core = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>{xml_escape(manifest.title)}</dc:title><dc:creator>VALO Factory</dc:creator><dc:description>source_sha256={manifest.source_sha256}</dc:description><cp:lastModifiedBy>VALO Factory</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">1980-01-01T00:00:00Z</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">1980-01-01T00:00:00Z</dcterms:modified></cp:coreProperties>'''
    app = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>VALO Factory</Application><PresentationFormat>On-screen Show (16:9)</PresentationFormat><Slides>{slide_count}</Slides><Notes>0</Notes><HiddenSlides>0</HiddenSlides><Company>VALO Research</Company><AppVersion>1.0</AppVersion></Properties>'''

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        _zip_write(zf, "[Content_Types].xml", content_types)
        _zip_write(zf, "_rels/.rels", root_rels)
        _zip_write(zf, "docProps/core.xml", core)
        _zip_write(zf, "docProps/app.xml", app)
        _zip_write(zf, "ppt/presentation.xml", presentation)
        _zip_write(zf, "ppt/_rels/presentation.xml.rels", presentation_rels_xml)
        _zip_write(zf, "ppt/slideMasters/slideMaster1.xml", slide_master)
        _zip_write(zf, "ppt/slideMasters/_rels/slideMaster1.xml.rels", slide_master_rels)
        _zip_write(zf, "ppt/slideLayouts/slideLayout1.xml", slide_layout)
        _zip_write(zf, "ppt/slideLayouts/_rels/slideLayout1.xml.rels", slide_layout_rels)
        _zip_write(zf, "ppt/theme/theme1.xml", theme)
        for index, slide in enumerate(manifest.slides, start=1):
            _zip_write(zf, f"ppt/slides/slide{index}.xml", _slide_xml(manifest, slide, index))
            rel = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/></Relationships>'
            _zip_write(zf, f"ppt/slides/_rels/slide{index}.xml.rels", rel)
    return buffer.getvalue()
