import json
import re
from typing import List, Dict, Any

SLIDE_HEADER_RE = re.compile(r'^\s*Slide\s*(\d+)\s*[:：]\s*(.+)\s*$')


def parse_outline_text(text: str) -> List[Dict[str, Any]]:
    slides: List[Dict[str, Any]] = []
    current: Dict[str, Any] | None = None

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line:

            continue
        m = SLIDE_HEADER_RE.match(line)
        if m:

            if current is not None:
                slides.append(current)

            title = m.group(2).strip()
            current = {
                "title": title,
                "bullets": []
            }
            continue
        if current is not None and line.lstrip().startswith(("-", "•")):
            bullet = line.lstrip().lstrip("-•").strip()
            if bullet:
                current["bullets"].append(bullet)
            continue

        if current is not None:
            text_part = line.strip()
            if not text_part:
                continue
            if current["bullets"]:
                current["bullets"][-1] += " " + text_part
            else:
                current["bullets"].append(text_part)
    if current is not None:
        slides.append(current)

    return slides


def merge_outlines(items: List[Dict[str, Any]]) -> str:

    items_sorted = sorted(
        items,
        key=lambda x: x.get("chunk_id", 0)
    )
    all_slides: List[Dict[str, Any]] = []

    for item in items_sorted:
        outline = (item.get("outline") or "").strip()
        if not outline:
            continue

        slides = parse_outline_text(outline)
        all_slides.extend(slides)

    lines: List[str] = []
    slide_no = 1

    for slide in all_slides:
        title = slide.get("title") or f"Untitled {slide_no}"
        lines.append(f"Slide {slide_no}：{title}")
        for bullet in slide.get("bullets") or []:
            lines.append(f"- {bullet}")
        lines.append("") 
        slide_no += 1

    return "\n".join(lines).rstrip()


def main(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    工作流模式入口：

    假设上游循环节点 / 聚合节点输出字段名为 'items'，
    其中每个元素包含：
        - chunk_id: int
        - chunk_title: str (可选)
        - outline: str   (Stage 1 LLM 输出的大纲）

    本节点输出：
        {
            "outline_merged": "<统一后的大纲文本>"
        }
    """
    items = inputs.get("items") or []
    if not isinstance(items, list):
        raise ValueError("inputs['items'] 必须是列表")

    merged = merge_outlines(items)
    return {
        "outline_merged": merged
    }


if __name__ == "__main__":
    """
    本地调试入口：

    假设有一个 JSON 文件，内容类似：
        {
          "items": [
            {"chunk_id": 1, "chunk_title": "...", "outline": "Slide 1：..."},
            ...
          ]
        }
    """

    json_path = "chunks.json"  # TODO: 换成实际路径

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("chunks", [])
    merged_text = merge_outlines(items)

    print(merged_text)
