import os
import pytest
from rag_pipeline import RAGPipeline


@pytest.fixture(scope="module")
def rag_system():
    pipeline = RAGPipeline(docs_dir="docs", chroma_path="data/test_chroma")
    pipeline.build_vector_store(force_rebuild=True)
    return pipeline


def test_document_loading(rag_system):
    docs = rag_system.load_documents()
    assert len(docs) > 0
    sources = [doc.metadata.get("source") for doc in docs]
    assert "vpn_guide.txt" in sources
    assert "hr_policy.txt" in sources
    assert "password_policy.txt" in sources


def test_document_chunking(rag_system):
    raw_docs = rag_system.load_documents()
    chunks = rag_system.split_documents(raw_docs)
    assert len(chunks) >= len(raw_docs)
    assert all(len(c.page_content) <= 600 for c in chunks)


def test_context_retrieval(rag_system):
    retrieved = rag_system.retrieve_context("What is the VPN policy?", top_k=3)
    assert len(retrieved) > 0
    contents = " ".join([d.page_content for d in retrieved])
    assert "VPN" in contents or "GlobalProtect" in contents or "corporate" in contents


def test_grounded_response_generation(rag_system):
    retrieved = rag_system.retrieve_context("How do I request Docker access?", top_k=3)
    ans = rag_system.generate_grounded_response("How do I request Docker access?", retrieved)
    assert "Docker" in ans or "Software Access" in ans or "policy" in ans


def test_unsupported_query_handling(rag_system):
    retrieved = rag_system.retrieve_context("What is the recipe for chocolate cake?", top_k=2)
    ans = rag_system.generate_grounded_response("What is the recipe for chocolate cake?", retrieved)
    assert "I could not find this information in the available ABC Technologies knowledge base." in ans
