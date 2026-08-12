import os
from openai import OpenAI
import chromadb
from dotenv import load_dotenv

# Load .env
load_dotenv()
YOUR_OPENAI_API_KEY = os.getenv("YOUR_OPENAI_API_KEY")
persist_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma"
)

# OpenAI client
client = OpenAI(api_key=YOUR_OPENAI_API_KEY)

# Function to generate embedding
def make_embedding(text):
    resp = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return resp.data[0].embedding

# Connect to Chroma
chroma_client = chromadb.PersistentClient(path=persist_dir)

# Load the existing collection
collection_name = "argo_embeddings"
collection = chroma_client.get_or_create_collection(name=collection_name)

# ----- Test query -----
def query_response(text: str, top_k: int = 5):
    """
    Query a Chroma collection with a given text.

    Args:
        collection: ChromaDB collection object
        text (str): The query text
        top_k (int): Number of results to return (default=5)

    Returns:
        dict: A dictionary with IDs, documents, and metadata
    """
    # Convert text to embedding
    query_emb = make_embedding(text)
    
    # Query collection
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=top_k
    )

    # Format response
    return {
        "ids": results["ids"],
        "documents": results["documents"],
        "metadata": results["metadatas"]
    }

