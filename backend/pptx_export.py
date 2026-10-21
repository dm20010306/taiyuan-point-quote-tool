from __future__ import annotations

import html
import io
import textwrap
import zipfile
from pathlib import Path
from typing import Callable

from PIL import Image
from backend.path_resolver import get_paths

EMU = 914400
SLIDE_W = 13.333
SLIDE_H = 7.5
PATHS = get_paths(__file__)
TEMPLATE_PATH = PATHS.resolve_app_asset("templates/报价表格-母版.pptx")


def emu(value: float) -> int:
    return round(value * EMU)


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=False)


def lines(value: object, width: int = 22, limit: int = 3) -> str:
    text = str(value or "-").replace("\r\n", "\n").replace("\r", "\n")
    result: list[str] = []
    for paragraph in text.split("\n"):
        result.extend(textwrap.wrap(paragraph, width=width, break_long_words=True, break_on_hyphens=False) or [""])
    if len(result) > limit:
        result = result[:limit]
        result[-1] = (result[-1][:-1] if result[-1] else "") + "…"
    return "\n".join(result)


class SlideBuilder:
    def __init__(self, title: str, project: dict, page_label: str):
        self.title = title
        self.project = project
        self.page_label = page_label
        self.shape_id = 2
        self.image_id = 0
        self.shapes: list[str] = []
        self.image_rels: list[tuple[str, bytes, str]] = []

    def _shape(self, body: str) -> None:
        self.shapes.append(body)
        self.shape_id += 1

    def text(self, x: float, y: float, w: float, h: float, value: object, *, size: int = 16, color: str = "111111", bold: bool = False, fill: str | None = None, line: str | None = None, align: str = "ctr") -> None:
        fill_xml = f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>' if fill else '<a:noFill/>'
        line_xml = f'<a:ln w="12700"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>' if line else '<a:ln><a:noFill/></a:ln>'
        align_value = "l" if align == "l" else "r" if align == "r" else "ctr"
        runs = []
        for index, part in enumerate(str(value or "").split("\n")):
            if index:
                runs.append('<a:br/>')
            runs.append(f'<a:r><a:rPr lang="zh-CN" sz="{size * 100}" b="{str(bold).lower()}"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill><a:latin typeface="PingFang SC"/><a:ea typeface="PingFang SC"/></a:rPr><a:t>{esc(part)}</a:t></a:r>')
        # Keep every cell and title vertically centered.  The small, symmetric
        # margins prevent glyphs from touching the borders while the normal
        # autofit lets long model/parameter text reduce slightly instead of
        # overflowing a cell.
        body = f'''<p:sp><p:nvSpPr><p:cNvPr id="{self.shape_id}" name="Text {self.shape_id}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom>{fill_xml}{line_xml}</p:spPr><p:txBody><a:bodyPr wrap="square" anchor="ctr" marL="45720" marR="45720" marT="0" marB="0"><a:normAutofit fontScale="90000" lnSpcReduction="10000"/></a:bodyPr><a:lstStyle/><a:p><a:pPr algn="{align_value}"/><a:r><a:rPr lang="zh-CN" sz="{size * 100}" b="{str(bold).lower()}"><a:latin typeface="PingFang SC"/><a:ea typeface="PingFang SC"/></a:rPr><a:t></a:t></a:r>{''.join(runs)}<a:endParaRPr lang="zh-CN" sz="{size * 100}"/></a:p></p:txBody></p:sp>'''
        self._shape(body)

    def image(self, x: float, y: float, w: float, h: float, path: Path) -> None:
        try:
            source = Image.open(path).convert("RGBA")
            source.thumbnail((round(w * 120), round(h * 120)), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (max(1, round(w * 120)), max(1, round(h * 120))), "white")
            canvas.alpha_composite(source, ((canvas.width - source.width) // 2, (canvas.height - source.height) // 2))
            buffer = io.BytesIO(); canvas.convert("RGB").save(buffer, "PNG")
            self.image_id += 1
            rid = f"rId{self.image_id + 1}"
            self.image_rels.append((rid, buffer.getvalue(), f"image{self.image_id}.png"))
            body = f'''<p:pic><p:nvPicPr><p:cNvPr id="{self.shape_id}" name="Product image {self.image_id}"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:ln><a:noFill/></a:ln></p:spPr></p:pic>'''
            self._shape(body)
        except Exception:
            pass

    def slide_xml(self) -> str:
        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>{''.join(self.shapes)}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'''

    def rels_xml(self) -> str:
        rels = ['<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>']
        for rid, _, filename in self.image_rels:
            rels.append(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/{filename}"/>')
        return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + ''.join(rels) + '</Relationships>'


def add_detail_slide(project: dict, items: list[dict], page_label: str, image_resolver: Callable[[str | None], Path | None]) -> SlideBuilder:
    slide = SlideBuilder("报价清单", project, page_label)
    slide.text(0.92, 0.80, 11.50, 0.72, "产品报价清单", size=25, color="FFFFFF", bold=True, fill="000000")
    slide.text(0.94, 0.45, 4.8, 0.22, project.get("name") or "", size=10, color="60646D", align="l")
    slide.text(10.9, 0.45, 1.45, 0.22, page_label, size=9, color="777B84", align="r")
    left, top, width, header_h = 0.92, 1.98, 11.50, 0.62
    # Reserve the footer and calculate the detail row height from the actual
    # number of rows on this slide. This keeps the final row inside the 16:9
    # page instead of relying on a fixed seven-row height.
    footer_y = 7.08
    row_h = max(0.62, min(0.84, (footer_y - 0.18 - top - header_h) / max(1, len(items))))
    widths = [1.75, 0.80, 1.00, 2.40, 1.15, 0.80, 0.62, 0.98, 0.62, 1.38]
    headers = ["产品名称", "图片", "产品型号", "产品参数", "品牌", "产地", "数量", "单价", "单位", "合计"]
    x = left
    for w, label in zip(widths, headers):
        slide.text(x, top, w, header_h, label, size=9, color="FFFFFF", bold=True, fill="000000", line="000000")
        x += w
    for row_index, item in enumerate(items[:7]):
        product = item["product"]; y = top + header_h + row_index * row_h; x = left
        values = [product.get("name") or "-", "", product.get("model") or "-", product.get("params") or "-", product.get("brand_name") or "-", product.get("origin") or "-", item["quantity"], "¥" + item["actual_price"], product.get("unit") or "个", "¥" + item["subtotal"]]
        for index, (w, value) in enumerate(zip(widths, values)):
            slide.text(x, y, w, row_h, lines(value, 18 if index == 3 else 12, 4 if index == 3 else 2), size=8 if index == 3 else 9, fill="FFFFFF", line="000000")
            if index == 1:
                image_path = image_resolver(product.get("image_path"))
                if image_path: slide.image(x + 0.08, y + 0.07, w - 0.16, max(0.2, row_h - 0.14), image_path)
            x += w
    slide.text(0.92, 7.08, 7.0, 0.18, "客户：" + (project.get("customer") or "-") + "    地址：" + (project.get("address") or "-"), size=8, color="777B84", align="l")
    return slide


def add_summary_slide(project: dict, groups: list[dict], fees: list[dict], total: str, page_label: str) -> SlideBuilder:
    slide = SlideBuilder("项目汇总", project, page_label)
    slide.text(0.92, 0.80, 11.50, 0.72, "项目汇总", size=25, color="FFFFFF", bold=True, fill="000000")
    slide.text(0.94, 0.45, 4.8, 0.22, project.get("name") or "", size=10, color="60646D", align="l")
    slide.text(10.9, 0.45, 1.45, 0.22, page_label, size=9, color="777B84", align="r")
    rows = [(g["label"], "¥" + g["subtotal"]) for g in groups]
    if fees: rows.append(("服务及其他费用", "¥" + f'{sum(float(f["amount"]) for f in fees):.2f}'))
    rows.append(("合计", "¥" + total))
    left, top, width, header_h = 0.92, 1.98, 11.50, 0.62
    row_h = max(0.62, min(1.35, (6.75 - top - header_h) / max(1, len(rows))))
    slide.text(left, top, width / 2, header_h, "项目类别", size=10, color="FFFFFF", bold=True, fill="000000", line="000000")
    slide.text(left + width / 2, top, width / 2, header_h, "项目合计", size=10, color="FFFFFF", bold=True, fill="000000", line="000000")
    for index, (label, amount) in enumerate(rows):
        y = top + header_h + index * row_h
        slide.text(left, y, width / 2, row_h, label, size=13, fill="FFFFFF", line="000000")
        slide.text(left + width / 2, y, width / 2, row_h, amount, size=13, fill="FFFFFF", line="000000")
    slide.text(0.92, 7.08, 7.0, 0.18, "客户：" + (project.get("customer") or "-") + "    地址：" + (project.get("address") or "-"), size=8, color="777B84", align="l")
    return slide


def _template_part(name: str, fallback: str) -> str:
    """Read the supplied quote deck's master styling when it is available."""
    try:
        with zipfile.ZipFile(TEMPLATE_PATH) as template:
            value = template.read(name).decode("utf-8").lstrip()
            return value.split("?>", 1)[1] if value.startswith("<?xml") else value
    except (FileNotFoundError, KeyError, OSError, UnicodeDecodeError):
        return fallback


def _write_package(slides: list[SlideBuilder], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    rels = ['<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>']
    slide_ids = []
    for index in range(len(slides)):
        rid = f"rId{index + 2}"; rels.append(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{index + 1}.xml"/>'); slide_ids.append(f'<p:sldId id="{index + 256}" r:id="{rid}"/>')
    content = ['<Default Extension="xml" ContentType="application/xml"/>','<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>','<Default Extension="png" ContentType="image/png"/>','<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>','<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>','<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>','<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>']
    for index in range(len(slides)): content.append(f'<Override PartName="/ppt/slides/slide{index + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>')
    presentation = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" saveSubsetFonts="1"><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:sldIdLst>{''.join(slide_ids)}</p:sldIdLst><p:sldSz cx="12192000" cy="6858000" type="screen16x9"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>'''
    master_xml = _template_part("ppt/slideMasters/slideMaster1.xml", '<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld><p:clrMap accent1="accent1" accent2="accent2" bg1="bg1" bg2="bg2" tx1="tx1" tx2="tx2" hlink="hlink" folHlink="folHlink"/></p:sldMaster>')
    master_rels = _template_part("ppt/slideMasters/_rels/slideMaster1.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/></Relationships>')
    layout_xml = _template_part("ppt/slideLayouts/slideLayout1.xml", '<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank"><p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>')
    layout_rels = _template_part("ppt/slideLayouts/_rels/slideLayout1.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/></Relationships>')
    theme_xml = _template_part("ppt/theme/theme1.xml", '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="PointQuote"><a:themeElements><a:clrScheme name="Office"><a:dk1><a:srgbClr val="000000"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1></a:clrScheme><a:fontScheme name="Office"><a:majorFont><a:latin typeface="PingFang SC"/><a:ea typeface="PingFang SC"/></a:majorFont><a:minorFont><a:latin typeface="PingFang SC"/><a:ea typeface="PingFang SC"/></a:minorFont></a:fontScheme><a:fmtScheme name="Office"><a:fillStyleLst/><a:lnStyleLst/><a:effectStyleLst/><a:bgFillStyleLst/></a:fmtScheme></a:themeElements></a:theme>')
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' + ''.join(content) + '</Types>')
        archive.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/></Relationships>')
        archive.writestr("ppt/presentation.xml", presentation)
        archive.writestr("ppt/_rels/presentation.xml.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + ''.join(rels) + '</Relationships>')
        archive.writestr("ppt/slideMasters/slideMaster1.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' + master_xml)
        archive.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' + master_rels)
        archive.writestr("ppt/slideLayouts/slideLayout1.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' + layout_xml)
        archive.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' + layout_rels)
        archive.writestr("ppt/theme/theme1.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' + theme_xml)
        for index, slide in enumerate(slides, 1):
            archive.writestr(f"ppt/slides/slide{index}.xml", slide.slide_xml())
            archive.writestr(f"ppt/slides/_rels/slide{index}.xml.rels", slide.rels_xml())
            for _, data, filename in slide.image_rels: archive.writestr(f"ppt/media/{filename}", data)


def export_quote_pptx(data: dict, output: Path, image_resolver: Callable[[str | None], Path | None]) -> None:
    detail = data["detail"]
    slides: list[SlideBuilder] = []
    # Six rows fit comfortably even when the parameter column wraps to four
    # lines. More products become additional detail slides automatically.
    chunks = [detail[index:index + 6] for index in range(0, len(detail), 6)] or [[]]
    total_pages = len(chunks) + 1
    for index, chunk in enumerate(chunks, 1):
        slides.append(add_detail_slide(data["project"], chunk, f"第 {index} / {total_pages} 页", image_resolver))
    slides.append(add_summary_slide(data["project"], quote_groups_for_pptx(data), data["fees"], data["total"], f"第 {total_pages} / {total_pages} 页"))
    _write_package(slides, output)


def quote_groups_for_pptx(data: dict) -> list[dict]:
    grouped: dict[str, dict] = {}
    for item in data["summary"]:
        category = str(item["product"].get("category") or "智能")
        group = grouped.setdefault(category, {"label": {"智能": "智能系统", "影音": "影音系统", "灯光": "灯光系统", "网络": "网络系统"}.get(category, category), "subtotal": 0.0})
        group["subtotal"] += float(item["subtotal"])
    return [{"label": group["label"], "subtotal": f'{group["subtotal"]:.2f}'} for group in grouped.values()]
