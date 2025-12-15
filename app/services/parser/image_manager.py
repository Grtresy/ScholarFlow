"""Local image storage and management."""
from __future__ import annotations

import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


@dataclass
class ValidationResult:
    """Result of image token validation."""
    total_tokens: int
    valid_count: int
    invalid_tokens: List[Tuple[str, str]]  # (token, error_message)
    missing_files: List[str]


class ImageManager:
    """Manages local image storage and path operations."""

    def __init__(self, base_dir: Path):
        """Initialize image manager.

        Args:
            base_dir: Base directory for all image storage
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_task_dir(self, task_id: str) -> Path:
        """Create directory for a specific task.

        Args:
            task_id: Unique task identifier

        Returns:
            Path to task directory
        """
        task_dir = self.base_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (task_dir / "images").mkdir(exist_ok=True)
        (task_dir / "pdf").mkdir(exist_ok=True)
        (task_dir / "markdown").mkdir(exist_ok=True)
        (task_dir / "output").mkdir(exist_ok=True)

        return task_dir

    def copy_images(
        self,
        source_paths: Iterable[Path],
        task_id: str,
        preserve_names: bool = True,
    ) -> Dict[str, Path]:
        """Copy images to task directory with path mapping.

        Args:
            source_paths: List of source image paths
            task_id: Task identifier
            preserve_names: Whether to preserve original filenames

        Returns:
            Dictionary mapping original name to new path
        """
        task_dir = self.create_task_dir(task_id)
        images_dir = task_dir / "images"

        path_mapping = {}
        for src_path in source_paths:
            if not src_path.exists():
                print(f"Warning: Image not found: {src_path}")
                continue

            # Determine new filename
            if preserve_names:
                new_name = src_path.name
            else:
                # Generate UUID filename with original extension
                ext = src_path.suffix
                new_name = f"{uuid.uuid4().hex}{ext}"

            dest_path = images_dir / new_name

            # Copy file
            shutil.copy2(src_path, dest_path)
            path_mapping[src_path.name] = dest_path

            print(f"📷 Copied image: {src_path.name} → {dest_path.relative_to(self.base_dir)}")

        return path_mapping

    def get_image_url(self, task_id: str, filename: str) -> str:
        """Get URL for accessing an image.

        Args:
            task_id: Task identifier
            filename: Image filename

        Returns:
            Relative URL path for the image
        """
        return f"/api/images/{task_id}/{filename}"

    def update_markdown_image_paths(
        self,
        markdown_content: str,
        task_id: str,
        image_mapping: Dict[str, Path],
    ) -> str:
        """Update image paths in Markdown content.

        Args:
            markdown_content: Original Markdown content
            task_id: Task identifier
            image_mapping: Mapping of original to new paths

        Returns:
            Updated Markdown content with correct image URLs
        """
        updated_content = markdown_content

        for original_name, new_path in image_mapping.items():
            # Try different patterns for image references
            patterns = [
                f"![{original_name}]({original_name})",
                f"![{original_name}](./{original_name})",
                f"![{original_name}](images/{original_name})",
                f"![{new_path.name}]({original_name})",
            ]

            url = self.get_image_url(task_id, new_path.name)

            for pattern in patterns:
                if pattern in updated_content:
                    # Replace with new URL
                    # Extract alt text if present
                    if "![" in pattern:
                        alt_start = pattern.find("[")
                        alt_end = pattern.find("]")
                        alt_text = pattern[alt_start+1:alt_end]
                        new_pattern = f"![{alt_text}]({url})"
                        updated_content = updated_content.replace(pattern, new_pattern)
                    break

        return updated_content

    def list_images(self, task_id: str) -> List[Path]:
        """List all images for a task.

        Args:
            task_id: Task identifier

        Returns:
            List of image paths
        """
        images_dir = self.base_dir / task_id / "images"

        if not images_dir.exists():
            return []

        return [p for p in images_dir.iterdir() if p.is_file()]

    def cleanup_task(self, task_id: str, keep_hours: int = 24) -> bool:
        """Clean up old task files.

        Args:
            task_id: Task identifier to remove
            keep_hours: Only remove tasks older than this many hours

        Returns:
            True if cleanup was performed
        """
        import time
        from datetime import datetime, timedelta

        task_dir = self.base_dir / task_id

        if not task_dir.exists():
            return False

        # Check modification time
        mtime = task_dir.stat().st_mtime
        mtime_datetime = datetime.fromtimestamp(mtime)
        cutoff = datetime.now() - timedelta(hours=keep_hours)

        if mtime_datetime > cutoff:
            print(f"Task {task_id} is too recent to clean up")
            return False

        # Remove directory
        shutil.rmtree(task_dir)
        print(f"🗑️  Cleaned up task directory: {task_dir}")
        return True

    def get_task_info(self, task_id: str) -> Dict[str, any]:
        """Get information about a task.

        Args:
            task_id: Task identifier

        Returns:
            Dictionary with task information
        """
        task_dir = self.base_dir / task_id

        if not task_dir.exists():
            return {"exists": False}

        info = {
            "exists": True,
            "path": str(task_dir),
            "images": [],
            "pdf": None,
            "markdown": None,
            "output": None,
        }

        # Check images
        images_dir = task_dir / "images"
        if images_dir.exists():
            info["images"] = [p.name for p in images_dir.iterdir() if p.is_file()]

        # Check PDF
        pdf_dir = task_dir / "pdf"
        if pdf_dir.exists():
            pdf_files = list(pdf_dir.glob("*.pdf"))
            if pdf_files:
                info["pdf"] = pdf_files[0].name

        # Check markdown
        md_dir = task_dir / "markdown"
        if md_dir.exists():
            md_files = list(md_dir.glob("*.md"))
            if md_files:
                info["markdown"] = md_files[0].name

        # Check output
        output_dir = task_dir / "output"
        if output_dir.exists():
            output_files = list(output_dir.glob("*"))
            if output_files:
                info["output"] = [p.name for p in output_files]

        return info

    # Token-based image handling methods

    IMAGE_TOKEN_PATTERN = re.compile(r'\[\[IMAGE:([^\]]+)\]\]')

    def tokenize_image_references(self, markdown_text: str) -> Tuple[str, List[str]]:
        """Replace image references with token format.

        Args:
            markdown_text: Markdown content with image references

        Returns:
            Tuple of (tokenized_text, extracted_filenames)
        """
        # Pattern to match all image references
        # Matches: ![alt](images/filename.jpg) or ![alt](filename.jpg) or ![](filename.jpg)
        pattern = r'!\[([^\]]*)\]\(([^)]+)\)'

        extracted_filenames = []
        tokenized_text = markdown_text

        # Find all matches
        matches = re.finditer(pattern, markdown_text)
        for match in matches:
            full_match = match.group(0)
            alt_text = match.group(1)
            image_path = match.group(2)

            # Extract filename from path (handle both 'images/filename.jpg' and 'filename.jpg')
            filename = image_path.split('/')[-1]

            # Only process if it looks like an image file
            if any(filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.tiff', '.tif']):
                token = f'[[IMAGE:{filename}]]'
                # Replace only this occurrence
                tokenized_text = tokenized_text.replace(full_match, token, 1)
                if filename not in extracted_filenames:
                    extracted_filenames.append(filename)

        return tokenized_text, extracted_filenames

    def validate_image_tokens(self, tokens: List[str], task_id: str) -> ValidationResult:
        """Validate that all image tokens correspond to existing files.

        Args:
            tokens: List of image tokens (e.g., [[IMAGE:filename.jpg]])
            task_id: Task identifier

        Returns:
            ValidationResult with validation status
        """
        invalid_tokens = []
        missing_files = []
        valid_count = 0

        for token in tokens:
            # Extract filename from token
            match = self.IMAGE_TOKEN_PATTERN.match(token)
            if not match:
                invalid_tokens.append((token, "Invalid token format"))
                continue

            filename = match.group(1)
            image_path = self.base_dir / task_id / "images" / filename

            if not image_path.exists():
                missing_files.append(filename)
                invalid_tokens.append((token, f"File not found: {filename}"))
            else:
                valid_count += 1

        return ValidationResult(
            total_tokens=len(tokens),
            valid_count=valid_count,
            invalid_tokens=invalid_tokens,
            missing_files=missing_files
        )

    def restore_tokens_to_markdown(self, markdown_text: str, task_id: str) -> str:
        """Restore image tokens to proper markdown image format.

        Args:
            markdown_text: Markdown content with [[IMAGE:...]] tokens
            task_id: Task identifier

        Returns:
            Markdown content with proper image URLs
        """
        def replace_token(match):
            filename = match.group(1)
            url = self.get_image_url(task_id, filename)
            # Try to find if there's a description before the token
            # Look for pattern like "- 图：描述 [[IMAGE:filename]]"
            # We need to extract the description part before the token
            return f'![{filename}]({url})'

        return self.IMAGE_TOKEN_PATTERN.sub(replace_token, markdown_text)

    def report_validation_issues(self, result: ValidationResult, task_id: str) -> str:
        """Generate a user-friendly validation report.

        Args:
            result: ValidationResult from validate_image_tokens
            task_id: Task identifier

        Returns:
            Formatted report string
        """
        if not result.invalid_tokens:
            return f"✅ All {result.total_tokens} image tokens are valid."

        report = f"\n⚠️  图片验证发现问题：\n\n"
        report += f"发现 {result.total_tokens} 个图片标记，"
        report += f"其中 {result.valid_count} 个有效，{result.invalid_tokens.__len__()} 个无效。\n\n"

        if result.missing_files:
            report += "缺失的图片文件：\n"
            for filename in result.missing_files:
                report += f"  - {filename}\n"
            report += "\n"

        report += "请选择：\n"
        report += "[1] 重新生成 (推荐)\n"
        report += "[2] 忽略并继续 (图片将显示为占位符)\n\n"
        report += f"请输入选择 (1-2): "

        return report


def create_image_manager(data_dir: str | Path = "data") -> ImageManager:
    """Create an ImageManager instance.

    Args:
        data_dir: Base data directory

    Returns:
        ImageManager instance
    """
    base_dir = Path(data_dir) / "intermediates"
    return ImageManager(base_dir)
