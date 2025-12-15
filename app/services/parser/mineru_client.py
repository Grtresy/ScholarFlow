"""Client wrapper for invoking MinerU parsing."""
from __future__ import annotations

import json
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

import requests

from app.core.config import get_settings


class MinerUClient:
    """Client for interacting with MinerU API."""

    def __init__(self, api_token: str | None = None):
        """Initialize MinerU client.

        Args:
            api_token: MinerU API token. If None, reads from environment.
        """
        settings = get_settings()
        self.api_token = api_token or settings.mineru_api_key
        if not self.api_token:
            raise ValueError("MinerU API token is required. Set MINERU_API_KEY environment variable.")

        self.base_url = "https://mineru.net/api/v4"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_token}"
        }

    def process_pdf(self, pdf_path: Path, model_version: str = "vlm",
                   output_dir: Path | None = None) -> Tuple[Path, List[Path], Dict[str, Any]]:
        """Parse PDF via MinerU and extract structured content.

        Args:
            pdf_path: Path to the PDF file to process
            model_version: Model version - 'pipeline' or 'vlm' (default: 'vlm')
            output_dir: Directory to store output. If None, uses pdf_path parent with stem_result

        Returns:
            Tuple of (markdown_path, image_paths, metadata)

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            RuntimeError: If processing fails
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Determine output directory
        if output_dir is None:
            file_stem = pdf_path.stem
            output_dir = pdf_path.parent / f"{file_stem}_result"

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"🚀 Starting to process PDF: {pdf_path.name}")

        # Step 1: Get upload URL
        print("1️⃣  Requesting upload URL...")
        upload_info = self._get_upload_url(pdf_path.name, model_version)
        if not upload_info:
            raise RuntimeError("Failed to get upload URL")

        batch_id = upload_info['batch_id']
        upload_url = upload_info['upload_url']

        # Step 2: Upload file
        print("2️⃣  Uploading file...")
        if not self._upload_file(pdf_path, upload_url):
            raise RuntimeError("Failed to upload file")

        print("✅ Upload successful!")

        # Step 3: Poll for results and download
        print(f"3️⃣  Starting parsing (Batch ID: {batch_id})...")
        result_info = self._poll_and_download(batch_id, output_dir)

        # Step 4: Locate markdown and images
        markdown_path = output_dir / "full.md"
        if not markdown_path.exists():
            # Try to find markdown file
            md_files = list(output_dir.glob("*.md"))
            if md_files:
                markdown_path = md_files[0]
            else:
                raise RuntimeError(f"No markdown file found in {output_dir}")

        # Find images directory
        images_dir = output_dir / "images"
        if not images_dir.exists():
            images_dir = output_dir  # Images might be directly in output dir

        image_paths = list(images_dir.glob("*")) if images_dir.exists() else []

        print(f"✨ Processing complete! Output: {output_dir}")
        return markdown_path, image_paths, result_info

    def _get_upload_url(self, filename: str, model_version: str) -> Dict[str, str] | None:
        """Get upload URL from MinerU API."""
        url = f"{self.base_url}/file-urls/batch"
        data = {
            "files": [{"name": filename, "data_id": f"task_{int(time.time())}"}],
            "model_version": model_version
        }
        try:
            res = requests.post(url, headers=self.headers, json=data, timeout=30)
            res_json = res.json()
            if res.status_code == 200 and res_json.get("code") == 0:
                return {
                    "batch_id": res_json["data"]["batch_id"],
                    "upload_url": res_json["data"]["file_urls"][0]
                }
            print(f"❌ Failed to get upload URL: {res_json.get('msg')}")
            return None
        except Exception as e:
            print(f"❌ Request exception: {e}")
            return None

    def _upload_file(self, file_path: Path, upload_url: str) -> bool:
        """Upload file to the provided URL."""
        try:
            with open(file_path, 'rb') as f:
                res = requests.put(upload_url, data=f, timeout=300)
                return res.status_code == 200
        except Exception as e:
            print(f"❌ Upload exception: {e}")
            return False

    def _poll_and_download(self, batch_id: str, output_dir: Path) -> Dict[str, Any]:
        """Poll for processing results and download when complete."""
        url = f"{self.base_url}/extract-results/batch/{batch_id}"

        while True:
            try:
                res = requests.get(url, headers=self.headers, timeout=30)
                res_json = res.json()

                if res_json.get("code") != 0:
                    raise RuntimeError(f"Query failed: {res_json.get('msg')}")

                file_result = res_json["data"]["extract_result"][0]
                state = file_result["state"]

                if state == "done":
                    print("\n🎉 Parsing complete! Preparing download...")
                    download_url = file_result['full_zip_url']
                    self._download_and_extract(download_url, output_dir)

                    # Return metadata
                    progress = file_result.get("extract_progress", {})
                    return {
                        "batch_id": batch_id,
                        "state": state,
                        "total_pages": progress.get("total_pages", 0),
                        "extracted_pages": progress.get("extracted_pages", 0),
                        "download_url": download_url
                    }

                elif state == "failed":
                    error_msg = file_result.get('err_msg', 'Unknown error')
                    raise RuntimeError(f"Parsing failed: {error_msg}")

                elif state == "running":
                    progress = file_result.get("extract_progress", {})
                    extracted = progress.get("extracted_pages", 0)
                    total = progress.get("total_pages", "?")
                    print(f"\r⏳ Processing... Extracted {extracted}/{total} pages", end="", flush=True)

                else:
                    print(f"\r⏳ Status: {state}...", end="", flush=True)

                time.sleep(3)

            except Exception as e:
                raise RuntimeError(f"Processing exception: {e}")

    def _download_and_extract(self, url: str, output_dir: Path) -> None:
        """Download ZIP file and extract to output directory."""
        zip_path = output_dir / "result.zip"

        print(f"⬇️  Downloading results to {output_dir}...")
        try:
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(zip_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            print("✅ Download complete, extracting...")

            # Extract ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(output_dir)

            print(f"✨ Extraction complete! Check folder: {output_dir}")

            # Optionally remove ZIP after extraction
            # zip_path.unlink()

        except Exception as e:
            raise RuntimeError(f"Download or extraction failed: {e}")


def parse_pdf(pdf_path: Path, model_version: str = "vlm",
              output_dir: Path | None = None) -> Tuple[Path, List[Path], Dict[str, Any]]:
    """Parse PDF via MinerU; returns markdown path, image paths, and metadata.

    This is the main entry point for PDF parsing.
    """
    client = MinerUClient()
    return client.process_pdf(pdf_path, model_version, output_dir)
