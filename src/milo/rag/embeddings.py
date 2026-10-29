from milo.config import Settings


def create_embeddings(settings: Settings):
    if not settings.google_api_key or not settings.google_api_key.get_secret_value():
        raise RuntimeError("Falta GOOGLE_API_KEY o GEMINI_API_KEY; no se han creado embeddings.")
    # Evita aplicar silenciosamente la configuración de 001 a modelos de otra familia.
    if settings.embedding_model != "gemini-embedding-001" or settings.embedding_dimension != 3072:
        raise ValueError("Sprint 1 prepara gemini-embedding-001 / 3072; otros modelos requieren revisión.")
    try:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
    except ImportError as exc:
        raise RuntimeError('Instala la integración opcional: pip install -e ".[rag]"') from exc
    return GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.google_api_key.get_secret_value(),
        output_dimensionality=settings.embedding_dimension,
    )
