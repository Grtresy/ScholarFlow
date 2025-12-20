import json
from typing import List, Dict, Any, Optional

DEFAULT_MAX_CHARS = 60000


def split_markdown(md: str, max_chars: int = DEFAULT_MAX_CHARS) -> List[Dict[str, Any]]:

    lines = md.splitlines()

    sections: List[Dict[str, str]] = []
    current_title = "Intro"        
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
            "text": text
        })

        pending_parent_title = None
        current_lines = []

    for line in lines:
        stripped = line.lstrip()

        if stripped.startswith("# "):   
            flush_section()
            current_title = stripped.lstrip("# ").strip()

        elif stripped.startswith("## "):  
            flush_section()
            current_title = stripped.lstrip("#").strip()

        else:
            current_lines.append(line)

    flush_section()

    chunks: List[Dict[str, Any]] = []
    chunk_id = 1

    for sec in sections:
        text = (sec.get("text") or "").strip()
        if not text:
            continue

        title = sec.get("title") or "Untitled"

        if len(text) <= max_chars:
            chunks.append({
                "id": chunk_id,
                "title": title,
                "text": text,
            })
            chunk_id += 1
        else:

            paragraphs = text.split("\n\n")
            buf: List[str] = []
            buf_len = 0
            part_idx = 1

            for p in paragraphs:
                p = p.strip()
                if not p:
                    continue
                p_len = len(p)

                if buf and buf_len + p_len + 2 > max_chars:
                    chunks.append({
                        "id": chunk_id,
                        "title": f"{title} (part {part_idx})",
                        "text": "\n\n".join(buf).strip(),
                    })
                    chunk_id += 1
                    part_idx += 1
                    buf = [p]
                    buf_len = p_len
                else:
                    buf.append(p)
                    buf_len += p_len
            if buf:
                chunks.append({
                    "id": chunk_id,
                    "title": f"{title} (part {part_idx})",
                    "text": "\n\n".join(buf).strip(),
                })
                chunk_id += 1

    return chunks


def merge_chunks(chunks: List[Dict[str, Any]], target_count: Optional[int]) -> List[Dict[str, Any]]:

    if not target_count or target_count <= 0:
        return chunks
    if len(chunks) <= target_count:
        return chunks

    current = chunks
    while len(current) > target_count:
        new_chunks: List[Dict[str, Any]] = []
        i = 0

        while i < len(current):
            if i + 1 < len(current):
                c1 = current[i]
                c2 = current[i + 1]

                merged_title = f"{c1.get('title', '')} / {c2.get('title', '')}".strip(" /")
                merged_text = (
                    (c1.get("text", "") or "").rstrip()
                    + "\n\n"
                    + (c2.get("text", "") or "").lstrip()
                ).strip()

                new_chunks.append({
                    "id": c1.get("id"),
                    "title": merged_title or "Merged",
                    "text": merged_text,
                })
                i += 2
            else:
                new_chunks.append(current[i])
                i += 1

        current = new_chunks

    for idx, c in enumerate(current, start=1):
        c["id"] = idx

    return current


def main(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    工作流模式入口：
    - 假设上游 MinerU 节点输出字段名为 'markdown'；
    - 可选输入：
        - 'max_chars': 控制单个 chunk 的最大长度（字符数）；
        - 'target_chunks': 希望的 chunk 数量上限（例如 6）。
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
    fine_chunks = split_markdown(markdown_text, max_chars=6000)
    merged_chunks = merge_chunks(fine_chunks, target_count=6)

    result = {"chunks": merged_chunks}
    print(json.dumps(result, ensure_ascii=False, indent=2))