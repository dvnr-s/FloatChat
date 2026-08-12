import os
from openai import OpenAI
import chromadb
from dotenv import load_dotenv

# Load .env
load_dotenv()
YOUR_OPENAI_API_KEY = os.getenv("YOUR_OPENAI_API_KEY")


# OpenAI client
client = OpenAI(api_key=YOUR_OPENAI_API_KEY)

chroma_client = chromadb.PersistentClient(
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma")
)
collection = chroma_client.get_or_create_collection("water_landmarks")




print("Count:", collection.count())

query_emb = client.embeddings.create(
                model="text-embedding-3-small",
                input="salinity in goa"
            ).data[0].embedding
loc_result = collection.query(query_embeddings=[query_emb], n_results=5)
print(loc_result)