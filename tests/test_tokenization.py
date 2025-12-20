"""Test image tokenization mechanism."""
import pytest
from pathlib import Path
from app.services.parser.image_manager import ImageManager


class TestTokenization:
    """Test cases for image tokenization and restoration."""

    def test_tokenize_and_restore_basic(self):
        """Test basic tokenization and restoration."""
        manager = ImageManager(Path("data/test_tokenization"))

        # Sample markdown with image references
        markdown = """# Test Document

This is a test with images.

![Figure 1](images/df31c4889a278a680daa11239dcc9df51b4c7fd8b86edfa336bc2b3dec9e25d0.jpg)

More text here.

![Figure 2](images/2e91889abe47de1d8c146c7997719d4a4ed0ce07d4080a6ecaee8ed56ae5af65.jpg)
"""

        # Tokenize
        tokenized, token_map = manager.tokenize_image_references_enhanced(
            markdown_content=markdown,
            task_id="test_001"
        )

        # Verify tokenization
        assert tokenized.count("[[TOKEN_IMG_") == 2
        assert len(token_map) == 2

        # Verify token map structure
        assert "[[TOKEN_IMG_001]]" in token_map
        assert token_map["[[TOKEN_IMG_001]]"]["hash"] == "df31c4889a278a680daa11239dcc9df51b4c7fd8b86edfa336bc2b3dec9e25d0"
        assert token_map["[[TOKEN_IMG_001]]"]["alt_text"] == "Figure 1"

        assert "[[TOKEN_IMG_002]]" in token_map
        assert token_map["[[TOKEN_IMG_002]]"]["hash"] == "2e91889abe47de1d8c146c7997719d4a4ed0ce07d4080a6ecaee8ed56ae5af65"
        assert token_map["[[TOKEN_IMG_002]]"]["alt_text"] == "Figure 2"

        # Restore
        restored = manager.restore_tokens_to_markdown_enhanced(
            tokenized_content=tokenized,
            token_map=token_map,
            output_format='marp'
        )

        # Verify restoration
        assert "df31c4889a278a680daa11239dcc9df51b4c7fd8b86edfa336bc2b3dec9e25d0" in restored
        assert "2e91889abe47de1d8c146c7997719d4a4ed0ce07d4080a6ecaee8ed56ae5af65" in restored
        assert "images/" in restored
        assert "[[TOKEN_IMG_" not in restored

    def test_tokenize_preserves_alt_text(self):
        """Test that alt text is preserved in tokenization."""
        manager = ImageManager(Path("data/test_tokenization"))

        markdown = '![CIFAR-10 训练曲线对比](images/hash1.jpg)'

        tokenized, token_map = manager.tokenize_image_references_enhanced(
            markdown_content=markdown,
            task_id="test_002"
        )

        assert token_map["[[TOKEN_IMG_001]]"]["alt_text"] == "CIFAR-10 训练曲线对比"

        restored = manager.restore_tokens_to_markdown_enhanced(
            tokenized_content=tokenized,
            token_map=token_map,
            output_format='marp'
        )

        assert "CIFAR-10 训练曲线对比" in restored

    def test_tokenize_empty_markdown(self):
        """Test tokenization of markdown without images."""
        manager = ImageManager(Path("data/test_tokenization"))

        markdown = "# No Images\n\nJust plain text."

        tokenized, token_map = manager.tokenize_image_references_enhanced(
            markdown_content=markdown,
            task_id="test_003"
        )

        assert tokenized == markdown
        assert len(token_map) == 0

    def test_token_integrity_validation(self):
        """Test token integrity validation."""
        manager = ImageManager(Path("data/test_tokenization"))

        # Content with 3 tokens
        content_with_tokens = "Text [[TOKEN_IMG_001]] more [[TOKEN_IMG_002]] text [[TOKEN_IMG_003]] end"

        # Valid - all tokens present and sequential
        report = manager.validate_token_integrity(content_with_tokens, expected_token_count=3)
        assert report['is_valid'] is True
        assert report['actual_count'] == 3
        assert report['duplicate_count'] == 0
        assert report['is_sequential'] is True

        # Invalid - missing token
        content_missing = "Text [[TOKEN_IMG_001]] more [[TOKEN_IMG_003]] end"
        report = manager.validate_token_integrity(content_missing, expected_token_count=3)
        assert report['is_valid'] is False
        assert report['missing_count'] == 1

        # Invalid - duplicate token
        content_duplicate = "Text [[TOKEN_IMG_001]] more [[TOKEN_IMG_001]] text"
        report = manager.validate_token_integrity(content_duplicate, expected_token_count=2)
        assert report['is_valid'] is False
        assert report['duplicate_count'] == 1

    def test_tokenize_multiple_image_formats(self):
        """Test tokenization with various image formats."""
        manager = ImageManager(Path("data/test_tokenization"))

        markdown = """![JPG Image](images/test1.jpg)
![PNG Image](test2.png)
![GIF Image](./test3.gif)
![No Prefix](test4.jpg)
"""

        tokenized, token_map = manager.tokenize_image_references_enhanced(
            markdown_content=markdown,
            task_id="test_004"
        )

        # Should handle all formats
        assert len(token_map) == 4
        assert tokenized.count("[[TOKEN_IMG_") == 4

        # All should extract hash correctly
        for i in range(1, 5):
            token = f"[[TOKEN_IMG_{i:03d}]]"
            assert token in token_map
            assert 'hash' in token_map[token]

    def test_restore_different_formats(self):
        """Test restoration to different output formats."""
        manager = ImageManager(Path("data/test_tokenization"))

        markdown = '![Test Image](images/abcd1234.jpg)'
        tokenized, token_map = manager.tokenize_image_references_enhanced(
            markdown_content=markdown,
            task_id="test_005"
        )

        # Marp format
        marp_restored = manager.restore_tokens_to_markdown_enhanced(
            tokenized_content=tokenized,
            token_map=token_map,
            output_format='marp'
        )
        assert "![Test Image](images/abcd1234.jpg)" == marp_restored.strip()

        # HTML format
        html_restored = manager.restore_tokens_to_markdown_enhanced(
            tokenized_content=tokenized,
            token_map=token_map,
            output_format='html'
        )
        assert '<img src="images/abcd1234.jpg" alt="Test Image" />' in html_restored

    def test_token_map_persistence(self):
        """Test that token map is saved to file."""
        manager = ImageManager(Path("data/test_tokenization"))

        markdown = '![Test](images/test.jpg)'
        task_id = "test_persistence_001"

        tokenized, token_map = manager.tokenize_image_references_enhanced(
            markdown_content=markdown,
            task_id=task_id
        )

        # Check if token map file was created (saved in base_dir/task_id)
        token_map_path = Path("data/test_tokenization") / task_id / "token_map.json"
        assert token_map_path.exists()

        # Verify content
        import json
        with open(token_map_path, 'r', encoding='utf-8') as f:
            saved_map = json.load(f)

        assert saved_map == token_map


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
