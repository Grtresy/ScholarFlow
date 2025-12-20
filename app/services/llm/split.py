import json
from typing import List, Dict, Any, Optional

DEFAULT_MAX_CHARS = 8000
DEFAULT_MAX_CHARS = 60000


def split_markdown(md: str, max_chars: int = DEFAULT_MAX_CHARS) -> List[Dict[str, Any]]:

    lines = md.splitlines()

    sections: List[Dict[str, Any]] = []
    current_title = "Intro"
    current_level = 0
    current_lines: List[str] = []
    pending_parent_title: Optional[str] = None  

    def flush_section():
        nonlocal current_lines, current_title, sections, pending_parent_title

        if not current_lines:
            if current_title != "Intro":
                pending_parent_title = current_title
            current_lines = []
            return

        text = "\n".join(current_lines).strip()
        if not text:
            if current_title != "Intro":
                pending_parent_title = current_title
            current_lines = []
            return

        if pending_parent_title:
            full_title = f"{pending_parent_title} / {current_title}"
        else:
            full_title = current_title

        sections.append({
            "title": full_title,
            "text": text,
            "level": current_level,
        })

        pending_parent_title = None
        current_lines = []

    for line in lines:
        stripped = line.lstrip()

        if stripped.startswith("# "):
            flush_section()
            current_title = stripped.lstrip("# ").strip()
            current_level = 1

        elif stripped.startswith("## "):
            flush_section()
            current_title = stripped.lstrip("#").strip()
            current_level = 2

        else:
            current_lines.append(line)

    flush_section()

    chunks: List[Dict[str, Any]] = []
    chunk_id = 1

    def format_section(title: str, text: str, level: int) -> str:
        text = text.strip()
        if not text:
            return ""
        if title and title != "Intro" and level > 0:
            prefix = "#" * level
            return f"{prefix} {title}\n{text}"
        return text

    def add_chunk(title: str, text: str) -> None:
        nonlocal chunk_id
        text = text.strip()
        if not text:
            return
        chunks.append({
            "id": chunk_id,
            "title": title or "Untitled",
            "text": text,
        })
        chunk_id += 1

    buffer_titles: List[str] = []
    buffer_parts: List[str] = []
    buffer_len = 0

    def flush_buffer() -> None:
        nonlocal buffer_titles, buffer_parts, buffer_len
        if not buffer_parts:
            return
        merged_title = " / ".join([t for t in buffer_titles if t]).strip(" /")
        merged_text = "\n\n".join(buffer_parts).strip()
        add_chunk(merged_title or "Merged", merged_text)
        buffer_titles = []
        buffer_parts = []
        buffer_len = 0

    for sec in sections:
        raw_text = (sec.get("text") or "").strip()
        if not raw_text:
            continue

        title = sec.get("title") or "Untitled"
        level = int(sec.get("level", 0) or 0)
        section_text = format_section(title, raw_text, level)
        if not section_text:
            continue

        if len(raw_text) <= max_chars:
            if buffer_parts:
                prospective_len = buffer_len + 2 + len(section_text)
                if prospective_len > max_chars:
                    flush_buffer()
                else:
                    buffer_len = prospective_len
            if not buffer_parts:
                buffer_len = len(section_text)
            buffer_parts.append(section_text)
            buffer_titles.append(title)
            continue

        flush_buffer()

        if title and title != "Intro" and level > 0:
            header_len = len(f"{'#' * level} {title} (part 1)\n")
            max_body_chars = max_chars - header_len if max_chars > header_len else max_chars
        else:
            max_body_chars = max_chars

        paragraphs = raw_text.split("\n\n")
        buf: List[str] = []
        buf_len = 0
        part_idx = 1

        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            p_len = len(p)

            if buf and buf_len + p_len + 2 > max_body_chars:
                part_title = f"{title} (part {part_idx})"
                part_text = "\n\n".join(buf).strip()
                add_chunk(part_title, format_section(part_title, part_text, level))
                part_idx += 1
                buf = [p]
                buf_len = p_len
            else:
                buf.append(p)
                buf_len += p_len
        if buf:
            part_title = f"{title} (part {part_idx})"
            part_text = "\n\n".join(buf).strip()
            add_chunk(part_title, format_section(part_title, part_text, level))

    flush_buffer()

    return chunks


def merge_chunks(chunks: List[Dict[str, Any]], target_count: Optional[int]) -> List[Dict[str, Any]]:
    if not target_count or target_count <= 0:
        return chunks
    if len(chunks) <= target_count:
        return chunks

    current = list(chunks)

    while len(current) > target_count:
        best_idx = None
        best_size = None

        for i in range(len(current) - 1):
            c1 = current[i]
            c2 = current[i + 1]
            size = len((c1.get("text") or "")) + len((c2.get("text") or ""))
            if best_size is None or size < best_size:
                best_size = size
                best_idx = i

        if best_idx is None:
            break

        c1 = current[best_idx]
        c2 = current[best_idx + 1]
        merged_title = f"{c1.get('title', '')} / {c2.get('title', '')}".strip(" /")
        merged_text = (
            (c1.get("text", "") or "").rstrip()
            + "\n\n"
            + (c2.get("text", "") or "").lstrip()
        ).strip()

        merged_chunk = {
            "id": c1.get("id"),
            "title": merged_title or "Merged",
            "text": merged_text,
        }

        current = current[:best_idx] + [merged_chunk] + current[best_idx + 2 :]

    for idx, c in enumerate(current, start=1):
        c["id"] = idx

    return current


def main(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    工作流模式入口：
    - 假设上游 MinerU 节点输出字段名为 'markdown'；
    - 可选输入：
        - 'max_chars': 控制单个 chunk 的最大长度（字符数）；
        - 'target_chunks': 希望的 chunk 数量上限（例如 3）。
    - 输出 {"chunks": [...]}，供后续循环调用 LLM。
    """
    md = inputs.get("markdown", "") or ""
    max_chars_input = inputs.get("max_chars")
    if isinstance(max_chars_input, (int, float)) and max_chars_input > 0:
        max_chars = int(max_chars_input)
    else:
        try:
            max_chars = int(max_chars_input)
            if max_chars <= 0:
                max_chars = DEFAULT_MAX_CHARS
        except Exception:
            max_chars = DEFAULT_MAX_CHARS

    target_chunks_input = inputs.get("target_chunks")
    target_chunks: Optional[int]
    try:
        if target_chunks_input is None:
            target_chunks = None
        else:
            tc = int(target_chunks_input)
            target_chunks = tc if tc > 0 else None
    except Exception:
        target_chunks = None

    chunks = split_markdown(md, max_chars=max_chars)
    chunks = merge_chunks(chunks, target_count=target_chunks)

    return {
        "chunks": chunks
    }


if __name__ == "__main__":
    """
    本地调试入口：
    从指定 markdown 文件读取 MinerU 输出，打印拆分 & 合并后的 chunks（JSON）。
    """

    md_path = "MinerU_Cyclical_Learning_Rates_for_Training_Neural_Networks__20251206030346.md"

    with open(md_path, "r", encoding="utf-8") as f:
        markdown_text = f.read()
    fine_chunks = split_markdown(markdown_text, max_chars=8000)
    merged_chunks = merge_chunks(fine_chunks, target_count=3)

    result = {"chunks": merged_chunks}
    print(json.dumps(result, ensure_ascii=False, indent=2))
