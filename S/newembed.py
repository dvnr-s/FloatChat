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


# OpenAI client
client = OpenAI(api_key=YOUR_OPENAI_API_KEY)

# ChromaDB setup
persist_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma"
)
os.makedirs(persist_dir, exist_ok=True)  # Ensure directory exists

chroma_client = chromadb.PersistentClient(path=persist_dir)
collection_name = "water_landmarks"
collection = chroma_client.get_or_create_collection(name=collection_name)

def upload_csv_to_chroma(csv_file, category):
    df = pd.read_csv(csv_file)
    count=0
    for i, row in df.iterrows():
        landmark_name = str(row["name"])
        lat, lon = row["latitude"], row["longitude"]

        # Generate embedding from landmark name
        embedding = client.embeddings.create(
            model="text-embedding-3-small",
            input=landmark_name
        ).data[0].embedding

        # Add to Chroma
        collection.add(
            ids=[f"{category}_{i}"],
            embeddings=[embedding],
            documents=[landmark_name],
            metadatas=[{
                "latitude": float(lat),
                "longitude": float(lon),
                "category": category
            }]
        )
        print(count)
        count=count+1

    print(f"✅ Uploaded {len(df)} {category} entries from {csv_file}")


# upload_csv_to_chroma(r"data/indian_beaches.csv", "beach")
upload_csv_to_chroma(r"data/indian_bays.csv", "bay")
# upload_csv_to_chroma(r"data/indian_lakes.csv", "lake")
# upload_csv_to_chroma(r"data/indian_islands.csv", "island")
# argo_parameters = {
#     "bbp700": "Particulate backscattering coefficient at 700 nm — proxy for particle concentration (like phytoplankton).",
#     "chla": "Chlorophyll-a concentration — indicates phytoplankton biomass and primary productivity.",
#     "doxy": "Dissolved oxygen — oxygen concentration in seawater, important for marine life and biogeochemical cycles.",
#     "nitrate": "Nitrate concentration — key nutrient for phytoplankton growth, part of the nitrogen cycle.",
#     "ph_in_situ_total": "In-situ pH (total scale) — acidity/alkalinity of seawater, relevant for ocean acidification.",
#     "salinity": "Salinity — measure of salt content in seawater, influences density and circulation.",
#     "salinity_sfile": "Adjusted salinity — salinity values corrected/calibrated from sensor data.",
#     "temperature": "Temperature — in-situ water temperature at measured depth, affects density, stratification, and currents.",
#     "temperature_sfile": "Adjusted temperature — temperature values corrected/calibrated from sensor data."
# }
# for param, meaning in argo_parameters.items():
#     # Create embedding
#     embedding = client.embeddings.create(
#         model="text-embedding-3-small",
#         input=f"{param}: {meaning}"
#     ).data[0].embedding

#     collection.add(
#         ids=[param],
#         embeddings=[embedding],
#         documents=[meaning],
#         metadatas=[{"parameter": param}]
#     )

# print("✅ Parameters inserted into vector DB")
