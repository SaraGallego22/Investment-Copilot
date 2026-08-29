"""CLI: indexa `data/corpus/` en el vector store del RAG."""

from collaborative_partner.rag.ingest import ingest

if __name__ == "__main__":
    count = ingest()
    print(f"Documentos indexados: {count}")
