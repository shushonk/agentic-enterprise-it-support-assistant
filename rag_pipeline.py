import os
import glob
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

load_dotenv()

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHROMA_PATH = os.getenv("CHROMA_PATH", "data/chroma")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")

SYSTEM_GROUNDING_PROMPT = (
    "You are the ABC Technologies enterprise support assistant.\n"
    "Answer ONLY using the supplied knowledge-base context.\n"
    "If the information is not available in the supplied context, say:\n"
    "'I could not find this information in the available ABC Technologies knowledge base.'\n"
    "Do not invent company policy."
)


class RAGPipeline:
    def __init__(
        self,
        docs_dir: str = "docs",
        chroma_path: str = CHROMA_PATH,
        embedding_model_name: str = EMBEDDING_MODEL,
        ollama_model: str = OLLAMA_MODEL
    ):
        self.docs_dir = docs_dir
        self.chroma_path = chroma_path
        self.embedding_model_name = embedding_model_name
        self.ollama_model = ollama_model
        
        self.embeddings = None
        self.vector_store = None
        self._init_embeddings()

    def _init_embeddings(self):
        """Initialize HuggingFace embeddings."""
        try:
            logger.info(f"Initializing embedding model: {self.embedding_model_name}")
            self.embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model_name)
        except Exception as e:
            logger.error(f"Error initializing embeddings: {e}")
            raise RuntimeError(f"Failed to load embedding model {self.embedding_model_name}: {e}")

    def load_documents(self) -> List[Document]:
        """Load text documents from docs directory."""
        documents = []
        if not os.path.exists("docs"):
            logger.warning("Docs directory does not exist.")
            return documents

        txt_files = glob.glob(os.path.join("docs", "*.txt"))
        for file_path in txt_files:
            try:
                loader = TextLoader(file_path, encoding="utf-8")
                docs = loader.load()
                for doc in docs:
                    doc.metadata["source"] = os.path.basename(file_path)
                documents.extend(docs)
                logger.info(f"Loaded {len(docs)} document from {file_path}")
            except Exception as e:
                logger.error(f"Failed to load document {file_path}: {e}")
        return documents

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split loaded documents into smaller chunks for vector indexing."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = splitter.split_documents(documents)
        logger.info(f"Split {len(documents)} documents into {len(chunks)} chunks.")
        return chunks

    def create_embeddings(self) -> HuggingFaceEmbeddings:
        """Get the initialized embedding model."""
        if not self.embeddings:
            self._init_embeddings()
        return self.embeddings

    def build_vector_store(self, force_rebuild: bool = False) -> Chroma:
        """Build or load persistent Chroma vector store."""
        if not self.embeddings:
            self._init_embeddings()

        if not force_rebuild and os.path.exists(self.chroma_path) and os.listdir(self.chroma_path):
            logger.info(f"Loading existing vector store from {self.chroma_path}")
            self.vector_store = Chroma(
                persist_directory=self.chroma_path,
                embedding_function=self.embeddings
            )
            return self.vector_store

        logger.info(f"Building new vector store at {self.chroma_path}")
        raw_docs = self.load_documents()
        if not raw_docs:
            logger.warning("No documents found in docs/. Creating empty Chroma vector store.")
            os.makedirs(self.chroma_path, exist_ok=True)
            self.vector_store = Chroma(
                persist_directory=self.chroma_path,
                embedding_function=self.embeddings
            )
            return self.vector_store

        chunks = self.split_documents(raw_docs)
        os.makedirs(self.chroma_path, exist_ok=True)
        self.vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=self.chroma_path
        )
        logger.info("Vector store successfully built and persisted.")
        return self.vector_store

    def retrieve_context(self, query: str, top_k: int = 3) -> List[Document]:
        """Retrieve relevant context chunks for a user query."""
        if not self.vector_store:
            self.build_vector_store()

        results = self.vector_store.similarity_search_with_score(query, k=top_k)
        docs = []
        for doc, score in results:
            docs.append(doc)
            logger.info(f"Retrieved chunk from {doc.metadata.get('source', 'unknown')} with score {score}")
        return docs

    def generate_grounded_response(self, query: str, context_docs: List[Document]) -> str:
        """Generate a grounded answer using strict enterprise knowledge context."""
        if not context_docs:
            return "I could not find this information in the available ABC Technologies knowledge base."

        context_str = "\n---\n".join([doc.page_content for doc in context_docs])
        
        # Check relevance/presence of relevant details
        query_words = set(query.lower().split())
        matched = False
        for doc in context_docs:
            content_lower = doc.page_content.lower()
            if any(word in content_lower for word in query_words if len(word) > 3):
                matched = True
                break

        if not matched:
            return "I could not find this information in the available ABC Technologies knowledge base."

        prompt = (
            f"{SYSTEM_GROUNDING_PROMPT}\n\n"
            f"CONTEXT:\n{context_str}\n\n"
            f"USER QUESTION: {query}\n\n"
            f"ANSWER:"
        )

        try:
            from langchain_ollama import OllamaLLM
            llm = OllamaLLM(model=self.ollama_model, timeout=10)
            response = llm.invoke(prompt)
            if response and response.strip():
                return response.strip()
        except Exception as e:
            logger.warning(f"Ollama LLM call failed or offline ({e}). Generating fallback grounded response.")

        # Fallback grounded extraction if LLM endpoint is unavailable
        extracted_sections = []
        for doc in context_docs:
            extracted_sections.append(f"• According to **{doc.metadata.get('source', 'policy')}**:\n{doc.page_content.strip()}")
        
        return "Based on ABC Technologies policy:\n\n" + "\n\n".join(extracted_sections)
