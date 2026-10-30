#!/usr/bin/env python3
"""批量提取课程 PDF 为干净 Markdown,供后续蒸馏使用。"""
import re
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent  # 课程根目录
OUT = Path(__file__).resolve().parent / "extracted"

# 需要剔除的噪音行(页眉/页脚/导航残留)
NOISE = [
    re.compile(r"^\d{4}/\d{2}/\d{2}\s"),                       # 日期页眉
    re.compile(r"^https?://\S*"),                               # URL 页脚
    re.compile(r"^\d+\s*/\s*\d+\s*$"),                          # 页码
    re.compile(r"^(下载APP|进入课程|登录|注册)$"),
    re.compile(r"^(讲述|时长)[:：]"),                            # 音频元数据
    re.compile(r"^时长\d{2}:\d{2}"),
    re.compile(r"^分布式金融架构课\s*进入课程$"),
]
LECTURE_RE = re.compile(r"^(\d+)\s*丨")


def clean_text(text: str) -> str:
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            lines.append("")
            continue
        if any(p.match(s) for p in NOISE):
            continue
        lines.append(s)
    # 合并连续空行
    out, prev_blank = [], False
    for ln in lines:
        blank = ln == ""
        if blank and prev_blank:
            continue
        out.append(ln)
        prev_blank = blank
    return "\n".join(out).strip()


def parse_meta(path: Path):
    module_dir = path.parent.name  # 如 "02-金融业务与系统 (6讲)"
    module = re.sub(r"\s*\(\d+讲\)$", "", module_dir)
    module_no = int(module.split("-")[0])
    stem = path.stem
    m = LECTURE_RE.match(stem)
    if m:
        order = int(m.group(1))
        title = stem  # 完整标题保留
    else:
        order = 0  # 开篇词/春节策划,按文件序
        title = stem
    return module, module_no, order, title


def slug(s: str) -> str:
    s = re.sub(r"[/\\:：|丨？?*\"<>（）()，。·—\s]+", "-", s)
    return s.strip("-")[:60]


def main():
    pdfs = sorted(p for p in ROOT.rglob("*.pdf"))
    manifest = []
    for pdf in pdfs:
        module, module_no, order, title = parse_meta(pdf)
        reader = PdfReader(str(pdf))
        text = "\n\n".join(clean_text(pg.extract_text() or "") for pg in reader.pages)
        outdir = OUT / f"M{module_no:02d}"
        outdir.mkdir(parents=True, exist_ok=True)
        outpath = outdir / f"{order:02d}-{slug(title)}.md"
        fm = (
            f"---\nsource: {pdf.name}\nmodule: {module}\n"
            f"module_no: {module_no}\norder: {order}\ntitle: {title}\n---\n\n"
        )
        outpath.write_text(fm + text, encoding="utf-8")
        manifest.append({"module": module, "module_no": module_no, "order": order,
                         "title": title, "chars": len(text), "out": str(outpath.relative_to(OUT))})
    print(f"提取完成:{len(manifest)} 个文件,总字符数 {sum(m['chars'] for m in manifest):,}")
    for m in sorted(manifest, key=lambda x: (x["module_no"], x["order"])):
        print(f"  M{m['module_no']:02d}#{m['order']:02d} [{m['chars']:>6,}字] {m['title'][:44]}")


if __name__ == "__main__":
    main()
