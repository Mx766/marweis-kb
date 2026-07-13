"""Generate demo files for seed data — a PDF, a TXT, and a Markdown file."""
import os


def _build_minimal_pdf(text_content: str) -> bytes:
    """Build a minimal valid PDF containing the given text, with zero dependencies.

    Uses hand-crafted PDF syntax — no reportlab/fpdf2 required.  Supports basic
    ASCII / UTF-8 content (the PDF declares no embedded fonts, so non-Latin
    glyphs may render as tofu in some viewers; this is fine for seed data).
    """
    # Encode the text as a PDF string (escape backslash / parens)
    escaped = text_content.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    # Break very long lines so viewers don't choke
    lines = []
    for line in escaped.split("\n"):
        while len(line) > 120:
            lines.append(line[:120])
            line = line[120:]
        lines.append(line)
    text_lines = "\n".join(f"({l})'" for l in lines)

    pdf = f"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 44>>stream
BT /F1 14 Tf 50 750 Td {text_lines} ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000256 00000 n
0000000359 00000 n
trailer<</Size 6/Root 1 0 R>>
startxref
443
%%EOF"""
    return pdf.encode("latin-1", errors="replace")


def generate_demo_files(output_dir: str) -> dict[str, bytes]:
    """Generate three demo files and return {basename: bytes}.

    Returns:
        {"sample_guide.pdf": bytes, "sample_notes.txt": bytes, "sample_readme.md": bytes}
    """
    os.makedirs(output_dir, exist_ok=True)

    # ---- 1. PDF 示例 ---- #
    pdf_text = (
        "迈瑞生知识库 — 示例文档\n"
        "========================\n\n"
        "这是一份自动生成的 PDF 示例文件，用于测试文件上传和预览功能。\n\n"
        "内容概述：\n"
        "  1. 医疗器械注册流程简介\n"
        "  2. NMPA 法规要点\n"
        "  3. 临床评价基本要求\n\n"
        "本文档仅供内部测试使用，不构成正式的法律或合规建议。\n"
    )
    pdf_bytes = _build_minimal_pdf(pdf_text)
    pdf_path = os.path.join(output_dir, "sample_guide.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    # ---- 2. TXT 示例 ---- #
    txt_content = (
        "医疗器械注册文档管理 — 快速参考\n"
        "=================================\n\n"
        "一、注册分类\n"
        "  - I 类：备案管理\n"
        "  - II 类：省级药监注册\n"
        "  - III 类：国家局注册\n\n"
        "二、关键法规\n"
        "  - 医疗器械监督管理条例 (2025 修订)\n"
        "  - 医疗器械注册管理办法\n"
        "  - 体外诊断试剂注册管理办法\n\n"
        "三、技术文档清单\n"
        "  1. 产品技术要求\n"
        "  2. 检测报告\n"
        "  3. 临床评价报告\n"
        "  4. 质量管理体系文件\n"
        "  5. 标签和说明书\n\n"
        "四、常用链接\n"
        "  NMPA 官网: https://www.nmpa.gov.cn\n"
        "  CMDE 官网: https://www.cmde.org.cn\n\n"
        "---\n"
        "本文档为迈瑞生知识库示例文件，用于测试目的。\n"
    )
    txt_bytes = txt_content.encode("utf-8")
    txt_path = os.path.join(output_dir, "sample_notes.txt")
    with open(txt_path, "wb") as f:
        f.write(txt_bytes)

    # ---- 3. Markdown 示例 ---- #
    md_content = (
        "# 临床评价报告（CER）撰写模板\n\n"
        "## 1. 基本信息\n\n"
        "| 项目 | 内容 |\n"
        "|------|------|\n"
        "| 产品名称 | [填写] |\n"
        "| 注册申请人 | [填写] |\n"
        "| 评价路径 | 等同性论证 / 临床试验 |\n"
        "| 版本号 | v1.0 |\n\n"
        "## 2. 临床评价范围\n\n"
        "本报告覆盖以下方面：\n\n"
        "- **安全性能**：产品在预期用途下的安全性评估\n"
        "- **有效性能**：产品是否达到预期的临床效果\n"
        "- **风险收益分析**：权衡产品受益与潜在风险\n\n"
        "## 3. 等同性论证要点\n\n"
        "根据 NMPA《医疗器械临床评价技术指导原则》，等同性论证需对比：\n\n"
        "1. 适用范围（适应证、适用人群、使用部位等）\n"
        "2. 结构组成和设计\n"
        "3. 性能指标\n"
        "4. 生物学特性\n\n"
        "> **注意**：以上内容仅为模板示例，实际报告需根据具体产品编写。\n\n"
        "## 4. 参考文献\n\n"
        "- 医疗器械临床评价技术指导原则 (2025 版)\n"
        "- MEDDEV 2.7/1 Rev.4\n"
        "- ISO 14155:2020\n"
    )
    md_bytes = md_content.encode("utf-8")
    md_path = os.path.join(output_dir, "sample_readme.md")
    with open(md_path, "wb") as f:
        f.write(md_bytes)

    return {
        "sample_guide.pdf": pdf_bytes,
        "sample_notes.txt": txt_bytes,
        "sample_readme.md": md_bytes,
    }


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    result = generate_demo_files(here)
    print(f"Generated {len(result)} demo files in {here}:")
    for name, data in result.items():
        print(f"  {name} ({len(data)} bytes)")
