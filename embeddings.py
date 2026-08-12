import pandas as pd
from sqlalchemy import create_engine, text
import chromadb
from openai import OpenAI
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load .env file
load_dotenv()
YOUR_OPENAI_API_KEY = os.getenv("YOUR_OPENAI_API_KEY")
POSTGRES_URI = os.getenv("POSTGRES_URI")

# OpenAI client
client = OpenAI(api_key=YOUR_OPENAI_API_KEY)

# ChromaDB setup
persist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma")
os.makedirs(persist_dir, exist_ok=True)  # Ensure directory exists

chroma_client = chromadb.PersistentClient(path=persist_dir)
collection_name = "argo_embeddings"
collection = chroma_client.get_or_create_collection(name=collection_name)

# Database connection
engine = create_engine(POSTGRES_URI)

# ---- CHECKPOINT HANDLING ----
CHECKPOINT_FILE = "last_checkpoint.json"

def load_last_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            return json.load(f).get("last_updated_at")
    return None

def save_checkpoint(timestamp):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({"last_updated_at": timestamp}, f)

last_checkpoint = load_last_checkpoint()
print(f"Last checkpoint: {last_checkpoint}")

# ---- FETCH DATA ----
if last_checkpoint:
    query = f"""
    SELECT id, platform_number, measurement_time, depth_pressure,
           parameter_name, parameter_value, latitude, longitude, updated_at
    FROM argofinal
    WHERE parameter_name='salinity'
    ORDER BY updated_at ASC
    LIMIT 20;
    """
else:
    # First run → fetch all
    query = """
    SELECT id, platform_number, measurement_time, depth_pressure,
           parameter_name, parameter_value, latitude, longitude, updated_at
    FROM argofinal
    ORDER BY updated_at ASC
    LIMIT 20;
    """

df = pd.read_sql(query, engine)
print(f"Fetched {len(df)} new/updated rows from Postgres")

def make_embedding(text):
    resp = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return resp.data[0].embedding

# ---- ADD TO CHROMA ----
latest_timestamp = last_checkpoint
for idx, row in df.iterrows():
    text_summary = (
        f"{row['parameter_name']}={row['parameter_value']} at depth {row['depth_pressure']} dbar, "
        f"location ({row['latitude']},{row['longitude']}), time={row['measurement_time']}, "
        f"platform={row['platform_number']}"
    )

    emb = make_embedding(text_summary)

    try:
        collection.add(
            ids=[str(row['id'])],
            embeddings=[emb],
            documents=[text_summary],
            metadatas=[{
                "platform_number": row['platform_number'],
                "parameter": row['parameter_name'],
                "depth": float(row['depth_pressure']),
                "latitude": float(row['latitude']),
                "longitude": float(row['longitude']),
                "measurement_time": str(row['measurement_time'])
            }]
        )
          # update checkpoint
        print(f"Stored embedding for id {row['id']}")
    except Exception as e:
        print(f"Error storing embedding for id {row['id']}: {e}")

# ---- SAVE NEW CHECKPOINT ----
latest_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
save_checkpoint(latest_timestamp)
print(f"Updated checkpoint saved: {latest_timestamp}")

print(f"Collection count: {collection.count()}")
