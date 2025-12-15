"""Wrapper around Marp CLI rendering with ARM64 support."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional, Literal


OutputFormat = Literal["pptx", "pdf", "html"]


class MarpEngine:
    """Marp CLI wrapper with ARM64 support and custom themes."""

    def __init__(self, project_root: Path | None = None):
        """Initialize Marp engine.

        Args:
            project_root: Project root directory. If None, uses current directory.
        """
        self.project_root = project_root or Path.cwd()
        self._marp_bin = self._find_marp_binary()
        self._chrome_path = self._find_chrome_binary()

    def _find_marp_binary(self) -> Path:
        """Find Marp binary in node_modules."""
        marp_bin = self.project_root / "node_modules" / ".bin" / "marp"

        if not marp_bin.exists():
            raise FileNotFoundError(
                f"Marp binary not found at {marp_bin}. "
                "Please run: npm install --save-dev @marp-team/marp-cli"
            )

        return marp_bin

    def _find_chrome_binary(self) -> str:
        """Find Chrome/Chromium binary for ARM64."""
        # Common Chrome paths on ARM64 Linux
        chrome_paths = [
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
            "/usr/bin/google-chrome",
            "/snap/bin/chromium",
        ]

        for path in chrome_paths:
            if os.path.exists(path):
                return path

        # Try to find via 'which'
        try:
            result = subprocess.run(
                ["which", "chromium-browser"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        try:
            result = subprocess.run(
                ["which", "chromium"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        raise FileNotFoundError(
            "Chrome/Chromium not found. Please install chromium-browser:\n"
            "  sudo apt-get update\n"
            "  sudo apt-get install -y chromium-browser libgbm-dev"
        )

    def render(
        self,
        input_md: Path,
        output_path: Path,
        format: OutputFormat = "pptx",
        theme_css: Optional[Path] = None,
        allow_local_files: bool = True,
    ) -> bool:
        """Render Markdown to presentation format via Marp CLI.

        Args:
            input_md: Path to input Markdown file
            output_path: Path to output file (without extension)
            format: Output format (pptx, pdf, html)
            theme_css: Optional custom CSS theme
            allow_local_files: Whether to allow reading local images

        Returns:
            True if successful, False otherwise

        Raises:
            FileNotFoundError: If input file doesn't exist
            RuntimeError: If rendering fails
        """
        if not input_md.exists():
            raise FileNotFoundError(f"Input Markdown file not found: {input_md}")

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build command
        cmd = [
            str(self._marp_bin),
            str(input_md),
            "--output", str(output_path.with_suffix(f".{format}")),
        ]

        # Add theme if specified
        if theme_css:
            if not theme_css.exists():
                raise FileNotFoundError(f"Theme CSS not found: {theme_css}")
            cmd.extend(["--theme-set", str(theme_css)])
        else:
            # Use default theme
            default_theme = self.project_root / "app" / "services" / "renderer" / "styles" / "default.css"
            if default_theme.exists():
                cmd.extend(["--theme-set", str(default_theme)])

        # Add flags
        if allow_local_files:
            cmd.append("--allow-local-files")

        # Add format
        cmd.extend([f"--{format}"])

        # Prepare environment with Chrome path
        env = os.environ.copy()
        env["CHROME_PATH"] = self._chrome_path

        # Execute command
        print(f"🎨 Rendering {input_md.name} to {format.upper()}...")
        try:
            result = subprocess.run(
                cmd,
                env=env,
                check=True,
                capture_output=True,
                text=True,
                timeout=300
            )
            print(f"✅ Rendering complete: {output_path.with_suffix(f'.{format}')}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Rendering failed!")
            print(f"Error: {e.stderr}")
            return False
        except subprocess.TimeoutExpired:
            print(f"❌ Rendering timeout (300s)")
            return False
        except Exception as e:
            print(f"❌ Rendering exception: {e}")
            return False

    def render_multiple(
        self,
        input_md: Path,
        output_base: Path,
        formats: list[OutputFormat] = ["pptx"],
        theme_css: Optional[Path] = None,
    ) -> dict[str, bool]:
        """Render to multiple formats.

        Args:
            input_md: Input Markdown file
            output_base: Base output path (without extension)
            formats: List of formats to generate
            theme_css: Optional custom CSS theme

        Returns:
            Dictionary mapping format to success status
        """
        results = {}
        for fmt in formats:
            output_path = output_base
            success = self.render(input_md, output_path, fmt, theme_css)
            results[fmt] = success

        return results

    async def render_markdown(
        self,
        markdown_content: str,
        output_dir: str,
        format: OutputFormat = "pptx",
        theme_css: Optional[Path] = None,
        allow_local_files: bool = True,
    ) -> str:
        """Render markdown content directly to presentation format.

        Args:
            markdown_content: The markdown content to render
            output_dir: Directory to save the output file
            format: Output format (pptx, pdf, html)
            theme_css: Optional custom CSS theme
            allow_local_files: Whether to allow reading local images

        Returns:
            Path to the rendered file as a string
        """
        import tempfile
        from pathlib import Path

        # Create temporary markdown file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(markdown_content)
            temp_md_path = Path(f.name)

        try:
            # Create output path
            output_path = Path(output_dir) / "presentation"

            # Render
            success = self.render(
                input_md=temp_md_path,
                output_path=output_path,
                format=format,
                theme_css=theme_css,
                allow_local_files=allow_local_files
            )

            if not success:
                raise RuntimeError("Marp rendering failed")

            # Return the actual output path
            return str(output_path.with_suffix(f".{format}"))

        finally:
            # Clean up temp file
            temp_md_path.unlink(missing_ok=True)


def render_marp(
    input_md: Path,
    output_path: Path,
    format: OutputFormat = "pptx",
    theme_css: Optional[Path] = None,
) -> bool:
    """Render Markdown to presentation via Marp CLI.

    This is the main entry point for rendering.

    Args:
        input_md: Path to input Markdown file
        output_path: Path to output file (without extension)
        format: Output format (pptx, pdf, html)
        theme_css: Optional custom CSS theme

    Returns:
        True if successful, False otherwise
    """
    engine = MarpEngine()
    return engine.render(input_md, output_path, format, theme_css)
