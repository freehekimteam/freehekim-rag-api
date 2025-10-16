"""
Tests for embeddings module
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "fastapi"))

from rag.embeddings import EmbeddingError, embed, embed_batch, get_embedding_dimension


class TestEmbed:
    """Test single text embedding"""

    @patch("rag.embeddings._get_openai_client")
    def test_embed_success(self, mock_get_client):
        """Test successful embedding generation"""
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_client.embeddings.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = embed("Test text")

        assert len(result) == 1536
        assert all(isinstance(x, float) for x in result)
        mock_client.embeddings.create.assert_called_once()

    def test_embed_empty_text_raises_error(self):
        """Test that empty text raises ValueError"""
        with pytest.raises(ValueError, match="Cannot embed empty text"):
            embed("")

        with pytest.raises(ValueError, match="Cannot embed empty text"):
            embed("   ")

    @patch("rag.embeddings._get_openai_client")
    def test_embed_long_text_truncated(self, mock_get_client):
        """Test that very long text is truncated"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_client.embeddings.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        long_text = "a" * 10000
        embed(long_text)

        # Check that text was truncated
        call_args = mock_client.embeddings.create.call_args
        assert len(call_args.kwargs["input"]) <= 8000

    @patch("rag.embeddings._get_openai_client")
    def test_embed_openai_error_raises_embedding_error(self, mock_get_client):
        """Test that OpenAI errors are converted to EmbeddingError"""
        from openai import OpenAIError

        mock_client = MagicMock()
        mock_client.embeddings.create.side_effect = OpenAIError("API error")
        mock_get_client.return_value = mock_client

        with pytest.raises(EmbeddingError, match="Failed to generate embedding"):
            embed("Test text")


class TestEmbedBatch:
    """Test batch embedding"""

    @patch("rag.embeddings._get_openai_client")
    def test_embed_batch_success(self, mock_get_client):
        """Test successful batch embedding"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536),
            MagicMock(embedding=[0.3] * 1536),
        ]
        mock_client.embeddings.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        texts = ["text1", "text2", "text3"]
        results = embed_batch(texts)

        assert len(results) == 3
        assert all(len(emb) == 1536 for emb in results)

    def test_embed_batch_empty_list_raises_error(self):
        """Test that empty list raises ValueError"""
        with pytest.raises(ValueError, match="Cannot embed empty list"):
            embed_batch([])

    @patch("rag.embeddings._get_openai_client")
    def test_embed_batch_filters_empty_texts(self, mock_get_client):
        """Test that empty texts are filtered out"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536),
        ]
        mock_client.embeddings.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        texts = ["text1", "", "text2", "   "]
        results = embed_batch(texts)

        # Should only embed non-empty texts
        assert len(results) == 2

    def test_embed_batch_invalid_batch_size(self):
        """Test that invalid batch_size raises ValueError"""
        with pytest.raises(ValueError, match="batch_size must be between"):
            embed_batch(["text"], batch_size=0)

        with pytest.raises(ValueError, match="batch_size must be between"):
            embed_batch(["text"], batch_size=3000)

    @patch("rag.embeddings._get_openai_client")
    def test_embed_batch_multiple_batches(self, mock_get_client):
        """Test that large lists are split into batches"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        # Simulate batch responses
        mock_response.data = [MagicMock(embedding=[0.1] * 1536) for _ in range(10)]
        mock_client.embeddings.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        texts = [f"text{i}" for i in range(25)]
        results = embed_batch(texts, batch_size=10)

        # Should make 3 API calls (10 + 10 + 5)
        assert mock_client.embeddings.create.call_count == 3
        assert len(results) == 25


class TestGetEmbeddingDimension:
    """Test embedding dimension helper"""

    @patch("rag.embeddings.settings")
    def test_dimension_for_small_model(self, mock_settings):
        """Test dimension for text-embedding-3-small"""
        mock_settings.embed_provider = "openai"
        mock_settings.openai_embedding_model = "text-embedding-3-small"

        assert get_embedding_dimension() == 1536

    @patch("rag.embeddings.settings")
    def test_dimension_for_large_model(self, mock_settings):
        """Test dimension for text-embedding-3-large"""
        mock_settings.embed_provider = "openai"
        mock_settings.openai_embedding_model = "text-embedding-3-large"

        assert get_embedding_dimension() == 3072

    @patch("rag.embeddings.settings")
    def test_dimension_default(self, mock_settings):
        """Test default dimension for unknown models"""
        mock_settings.embed_provider = "unknown"

        assert get_embedding_dimension() == 1536
