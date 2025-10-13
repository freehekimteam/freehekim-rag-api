#!/usr/bin/env python3
"""
HakanCloud RAG System Test Script
==================================

Tests the complete RAG pipeline:
1. OpenAI embeddings generation
2. Qdrant collection connectivity
3. Full RAG query (retrieve + rank + generate)

Usage:
    python test_rag_system.py
"""
import os
import sys
from pathlib import Path

# Add fastapi directory to path
sys.path.insert(0, str(Path(__file__).parent / "fastapi"))

from rag.embeddings import embed, embed_batch, get_embedding_dimension
from rag.client_qdrant import _qdrant, INTERNAL, EXTERNAL
from rag.pipeline import retrieve_answer
from config import Settings

def test_config():
    """Test configuration loading"""
    print("=" * 60)
    print("🔧 Testing Configuration...")
    print("=" * 60)

    settings = Settings()

    print(f"✓ Environment: {settings.env}")
    print(f"✓ Qdrant Host: {settings.qdrant_host}:{settings.qdrant_port}")
    print(f"✓ Embed Provider: {settings.embed_provider}")
    print(f"✓ OpenAI Model: {settings.openai_embedding_model}")
    print(f"✓ OpenAI API Key: {'✓ Set' if settings.openai_api_key else '✗ Missing'}")
    print()


def test_embeddings():
    """Test embedding generation"""
    print("=" * 60)
    print("🧠 Testing Embeddings...")
    print("=" * 60)

    test_text = "Diyabet nedir ve belirtileri nelerdir?"

    try:
        # Test single embedding
        print(f"Query: {test_text}")
        vector = embed(test_text)

        print(f"✓ Embedding generated successfully")
        print(f"✓ Dimension: {len(vector)}")
        print(f"✓ First 5 values: {vector[:5]}")
        print()

        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_qdrant_connection():
    """Test Qdrant connectivity and collections"""
    print("=" * 60)
    print("🗄️  Testing Qdrant Connection...")
    print("=" * 60)

    try:
        collections = _qdrant.get_collections().collections

        print(f"✓ Connected to Qdrant")
        print(f"✓ Found {len(collections)} collections:")

        for col in collections:
            info = _qdrant.get_collection(col.name)
            print(f"  - {col.name}: {info.points_count} points, {info.config.params.vectors.size} dims")

        print()
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_rag_pipeline():
    """Test full RAG pipeline"""
    print("=" * 60)
    print("🚀 Testing Full RAG Pipeline...")
    print("=" * 60)

    test_queries = [
        "Diyabet hastalığı nedir?",
        "Metformin yan etkileri nelerdir?",
        "COVID-19 aşısı güvenli midir?"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n[Test {i}/{len(test_queries)}]")
        print(f"Question: {query}")
        print("-" * 60)

        try:
            result = retrieve_answer(query, top_k=3)

            print(f"✓ Answer generated:")
            print(f"  {result['answer'][:200]}...")
            print()
            print(f"✓ Sources used: {len(result['sources'])}")
            for j, source in enumerate(result['sources'], 1):
                print(f"  [{j}] {source['source']} (score: {source['score']})")

            print()
            print(f"✓ Metadata:")
            print(f"  - Internal hits: {result['metadata']['internal_hits']}")
            print(f"  - External hits: {result['metadata']['external_hits']}")
            print(f"  - Tokens used: {result['metadata']['tokens_used']}")
            print()

        except Exception as e:
            print(f"✗ Error: {e}")
            continue

    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🧪 HakanCloud RAG System Tests")
    print("=" * 60 + "\n")

    results = {}

    # Test 1: Configuration
    results['config'] = test_config()

    # Test 2: Embeddings
    results['embeddings'] = test_embeddings()

    # Test 3: Qdrant
    results['qdrant'] = test_qdrant_connection()

    # Test 4: Full RAG (only if previous tests passed)
    if all([results['config'], results['embeddings'], results['qdrant']]):
        results['rag_pipeline'] = test_rag_pipeline()
    else:
        print("⚠️  Skipping RAG pipeline test due to previous failures")
        results['rag_pipeline'] = False

    # Summary
    print("=" * 60)
    print("📊 Test Summary")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {test_name}")

    print()

    if all(results.values()):
        print("🎉 All tests passed! RAG system is ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Check configuration and logs.")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
