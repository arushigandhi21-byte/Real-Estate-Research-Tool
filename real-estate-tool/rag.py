"""Retrieval-augmented generation helpers for the Streamlit application."""

import os
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
VECTORSTORE_DIR = PROJECT_DIR / "resources" / "vectorstore"
COLLECTION_NAME = "real_estate"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"

_llm = None
_vector_store = None


def _load_web_page(url):
    """Fetch readable HTML text without requiring an NLP model download."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Enter a complete http:// or https:// URL.")

    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; RealEstateResearchTool/1.0)"},
        timeout=20,
    )
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    if "html" not in content_type:
        raise ValueError(f"Expected an HTML page, received {content_type or 'unknown content type'}.")

    soup = BeautifulSoup(response.text, "html.parser")
    for element in soup(["script", "style", "noscript", "nav", "footer", "form"]):
        element.decompose()
    content = soup.find("article") or soup.find("main") or soup.body or soup
    text = content.get_text(separator="\n", strip=True)
    if not text:
        raise ValueError("The page has no readable text.")
    return Document(page_content=text, metadata={"source": url})


def _get_vector_store():
    """Create the local embedding model and persistent vector store lazily."""
    global _vector_store
    if _vector_store is None:
        VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        _vector_store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=str(VECTORSTORE_DIR),
        )
    return _vector_store


def _get_llm():
    """Create the Groq client only when a question is submitted."""
    global _llm
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError(
            "GROQ_API_KEY is missing. Copy .env.example to .env and add your key."
        )
    if _llm is None:
        _llm = ChatGroq(
            model=os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL),
            temperature=0.1,
            max_tokens=500,
        )
    return _llm


def process_urls(urls):
    """Load URLs, split their text, and replace the local vector collection."""
    clean_urls = [url.strip() for url in urls if url.strip()]
    if not clean_urls:
        raise ValueError("Provide at least one URL.")

    yield "Initializing the local embedding model..."
    vector_store = _get_vector_store()

    yield "Loading article content..."
    documents = []
    failures = []
    for url in clean_urls:
        try:
            documents.append(_load_web_page(url))
        except (requests.RequestException, ValueError) as exc:
            failures.append(f"{url}: {exc}")
            yield f"Skipped {url}: {exc}"
    if not documents:
        raise RuntimeError("No URLs could be loaded. " + " ".join(failures))

    yield "Splitting text into chunks..."
    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ". ", " "],
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(documents)
    if not chunks:
        raise RuntimeError("The loaded pages did not contain any indexable text.")

    yield "Resetting the vector store..."
    vector_store.reset_collection()

    yield f"Adding {len(chunks)} chunks to the vector store..."
    vector_store.add_documents(
        chunks, ids=[str(uuid4()) for _ in range(len(chunks))]
    )
    yield "URLs processed successfully. You can now ask a question."


def generate_answer(query):
    """Answer a question using the most relevant indexed article chunks."""
    vector_store = _get_vector_store()
    if not vector_store.get(limit=1).get("ids"):
        raise RuntimeError("Process at least one URL before asking a question.")

    documents = vector_store.similarity_search(query, k=4)
    context = "\n\n".join(document.page_content for document in documents)
    prompt = (
        "Answer the question using only the context below. If the answer is not "
        "present, say that you could not find it in the supplied articles. Be "
        "concise and factual.\n\n"
        f"Context:\n{context}\n\nQuestion: {query}"
    )
    response = _get_llm().invoke(prompt)

    sources = []
    for document in documents:
        source = document.metadata.get("source")
        if source and source not in sources:
            sources.append(source)
    return str(response.content), sources


if __name__ == "__main__":
    sample_urls = [
        "https://www.cnbc.com/2024/12/21/how-the-federal-reserves-rate-policy-affects-mortgages.html",
        "https://www.cnbc.com/2024/12/20/why-mortgage-rates-jumped-despite-fed-interest-rate-cut.html",
    ]
    for message in process_urls(sample_urls):
        print(message)
    answer, answer_sources = generate_answer(
        "What was the 30-year fixed mortgage rate, and on what date?"
    )
    print(f"Answer: {answer}")
    print("Sources:", *answer_sources, sep="\n")
