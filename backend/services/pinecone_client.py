"""Pinecone vector database client for semantic search"""

from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
import openai

from core.config import settings

# Global client
_pc: Optional[Pinecone] = None
_index = None


async def init_pinecone():
    """Initialize Pinecone client and ensure index exists"""
    global _pc, _index
    
    if not settings.PINECONE_API_KEY:
        print("Warning: PINECONE_API_KEY not set, vector search disabled")
        return
    
    _pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    
    # Check if index exists, create if not
    index_name = settings.PINECONE_INDEX_NAME
    
    if index_name not in _pc.list_indexes().names():
        _pc.create_index(
            name=index_name,
            dimension=1536,  # text-embedding-3-small
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
    
    _index = _pc.Index(index_name)
    print(f"Pinecone index '{index_name}' ready")


def get_index():
    """Get Pinecone index instance"""
    if _index is None:
        raise RuntimeError("Pinecone not initialized")
    return _index


async def generate_embedding(text: str) -> List[float]:
    """Generate embedding using OpenAI"""
    client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    response = await client.embeddings.create(
        input=text,
        model=settings.EMBEDDING_MODEL
    )
    
    return response.data[0].embedding


async def upsert_app(app_id: str, app_data: Dict[str, Any]):
    """Upsert app to vector database"""
    if _index is None:
        return
    
    # Create rich text for embedding
    text_to_embed = f"""
    {app_data['name']} by {app_data['developer']}
    Category: {app_data['category']}
    {app_data['description']}
    """.strip()
    
    # Generate embedding
    embedding = await generate_embedding(text_to_embed)
    
    # Prepare metadata
    metadata = {
        "name": app_data['name'],
        "developer": app_data['developer'],
        "category": app_data['category'],
        "price": app_data['price'],
        "rating": app_data.get('rating', 0),
        "icon_url": app_data['icon_url'],
        "description": app_data['description'][:1000],  # Limit length
    }
    
    # Upsert to Pinecone
    _index.upsert(
        vectors=[{
            "id": app_id,
            "values": embedding,
            "metadata": metadata
        }],
        namespace=settings.PINECONE_NAMESPACE
    )


async def search_similar_apps(
    query: str,
    top_k: int = 10,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Search apps by semantic similarity"""
    if _index is None:
        return []
    
    # Generate query embedding
    query_embedding = await generate_embedding(query)
    
    # Build filter if provided
    filter_dict = {}
    if filters:
        if 'category' in filters:
            filter_dict['category'] = {'$eq': filters['category']}
        if 'max_price' in filters:
            filter_dict['price'] = {'$lte': filters['max_price']}
        if 'min_rating' in filters:
            filter_dict['rating'] = {'$gte': filters['min_rating']}
    
    # Query Pinecone
    results = _index.query(
        vector=query_embedding,
        top_k=top_k,
        namespace=settings.PINECONE_NAMESPACE,
        filter=filter_dict if filter_dict else None,
        include_metadata=True
    )
    
    return [
        {
            "id": match.id,
            "score": match.score,
            **match.metadata
        }
        for match in results.matches
    ]


async def delete_app(app_id: str):
    """Remove app from vector database"""
    if _index is None:
        return
    
    _index.delete(
        ids=[app_id],
        namespace=settings.PINECONE_NAMESPACE
    )
