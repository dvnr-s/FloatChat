from mcp.server.fastmcp import FastMCP
from openai import OpenAI
from sqlalchemy import create_engine, text
import chromadb
import json
import os
from dotenv import load_dotenv

# Project root (this file lives in <root>/S), so paths work regardless of cwd
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load .env file
load_dotenv(os.path.join(BASE_DIR, ".env"))
# === Setup ===

mcp = FastMCP("argo-summarizer")
YOUR_OPENAI_API_KEY = os.getenv("YOUR_OPENAI_API_KEY")
client = OpenAI(api_key=YOUR_OPENAI_API_KEY)
# Neon PostgreSQL connection (replace with your Neon credentials!)
DATABASE_URL = os.getenv("POSTGRES_URI")
# Built lazily so the MCP server still starts (and reports a clear error)
# when POSTGRES_URI is not configured.
engine = create_engine(DATABASE_URL) if DATABASE_URL else None

# Chroma vector DB
chroma_client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chroma"))
collection = chroma_client.get_or_create_collection("water_landmarks")

@mcp.tool()
def summarize_ocean_data(user_query: str, n: int = 5):
    """
    Takes a user query, fetches relevant oceanographic data 
    argo_parameters = {
   "bbp700": "Particulate backscattering coefficient at 700 nm — proxy for particle concentration (like phytoplankton).",
   "chla": "Chlorophyll-a concentration — indicates phytoplankton biomass and primary productivity.",
   "doxy": "Dissolved oxygen — oxygen concentration in seawater, important for marine life and biogeochemical cycles.",
   "nitrate": "Nitrate concentration — key nutrient for phytoplankton growth, part of the nitrogen cycle.",
  "ph_in_situ_total": "In-situ pH (total scale) — acidity/alkalinity of seawater, relevant for ocean acidification.",
   "salinity": "Salinity — measure of salt content in seawater, influences density and circulation.",
  "salinity_sfile": "Adjusted salinity — salinity values corrected/calibrated from sensor data.",
  "temperature": "Temperature — in-situ water temperature at measured depth, affects density, stratification, and currents.",
     "temperature_sfile": "Adjusted temperature — temperature values corrected/calibrated from sensor data."
 }
    from Neon PostgreSQL using vector DB for location, and summarize while providing data used to get to that analysis.
    don't answer questions outside ocean domain.
    """

    # Step 1: Extract context (force JSON output)
    extraction_prompt = f"""
    Extract structured info from this query: "{user_query}".
    Respond ONLY with valid JSON object with keys:
    - parameters (list) made of following ["bbp700","chla","doxy","nitrate","ph_in_situ_total","salinity","salinity_sfile","temperature"]
    - location_name
    - latitude
    - longitude
    - time_start
    - time_end
    """
    extraction = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a query parser. Return only valid JSON."},
            {"role": "user", "content": extraction_prompt}
        ],
        response_format={"type": "json_object"}
    )

    raw = extraction.choices[0].message.content
    print("RAW extraction:", raw)  # ✅ Debugging

    try:
        context = json.loads(raw)
        # If model returned a list instead of dict, normalize
        if isinstance(context, list) and len(context) > 0:
            context = context[0]
    except Exception as e:
        return {"error": f"Failed to parse JSON: {e}", "raw": raw}

    # Step 2: Resolve location if only name provided
    if (not context.get("latitude")) or (not context.get("longitude")):
        if context.get("location_name"):
            query_emb = client.embeddings.create(
                model="text-embedding-3-small",
                input=context["location_name"]
            ).data[0].embedding
            loc_result = collection.query(query_embeddings=[query_emb], n_results=1)

            
            if loc_result.get("metadatas") and loc_result["metadatas"][0]:
                lat = loc_result["metadatas"][0][0]["latitude"]
                lon = loc_result["metadatas"][0][0]["longitude"]
                context["latitude"], context["longitude"] = lat, lon

    # Step 3: Run SQL query for EACH parameter
    lat, lon = context.get("latitude"), context.get("longitude")
    t_start = context.get("time_start") or "2000-01-01"
    t_end = context.get("time_end") or "2100-01-01"

    if engine is None:
        return {"error": "POSTGRES_URI is not set in .env", "context": context}

    if lat is None or lon is None:
        return {
            "error": "Could not resolve a location for this query. "
                     "Try naming an Indian coastal place, bay, island or lake.",
            "context": context,
        }

    sql = text("""
        SELECT parameter_name, parameter_value, measurement_time, latitude, longitude, depth_pressure
        FROM argofinal
        WHERE parameter_name = :param
          AND latitude BETWEEN :lat_min AND :lat_max
          AND longitude BETWEEN :lon_min AND :lon_max
          
        ORDER BY measurement_time ASC
        LIMIT 200
    """)

    all_results = {}
    try:
        with engine.connect() as conn:
            for param in context.get("parameters", []):
                rows = conn.execute(sql, {
                    "param": param,
                    "lat_min": lat - 10.0, "lat_max": lat + 10.0,
                    "lon_min": lon - 10.0, "lon_max": lon + 10.0,
                    "t_start": t_start, "t_end": t_end
                }).fetchall()
                all_results[param] = [dict(r._mapping) for r in rows]
    except Exception as e:
        return {"error": f"Database query failed: {e}", "context": context}

   
    return {
        "context": context,
        "data": all_results
    }
