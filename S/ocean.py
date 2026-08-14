from mcp.server.fastmcp import FastMCP
from openai import OpenAI
from sqlalchemy import create_engine, text
import chromadb
import json
import os
import re
from datetime import datetime
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

def _as_date(value, fallback):
    """Coerce whatever the extractor returned into a YYYY-MM-DD string."""
    if not value:
        return fallback
    text_value = str(value).strip()
    if re.fullmatch(r"\d{4}", text_value):          # bare year
        return f"{text_value}-01-01" if fallback.startswith("2000") else f"{text_value}-12-31"
    if re.fullmatch(r"\d{4}-\d{2}", text_value):    # year-month
        return f"{text_value}-01"
    try:
        return datetime.fromisoformat(text_value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return fallback


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
    # The extractor sometimes emits "2024" or "last year" — anything Postgres
    # can't cast would now abort the query, so fall back to an open bound.
    t_start = _as_date(context.get("time_start"), "2000-01-01")
    t_end = _as_date(context.get("time_end"), "2100-01-01")

    if engine is None:
        return {"error": "POSTGRES_URI is not set in .env", "context": context}

    if lat is None or lon is None:
        return {
            "error": "Could not resolve a location for this query. "
                     "Try naming an Indian coastal place, bay, island or lake.",
            "context": context,
        }

    # measurement_time IS filtered here — leaving it out made every answer fall
    # back to whatever the LIMIT happened to catch. Newest first, so a question
    # with no explicit date range gets the most recent profiles.
    sql = text("""
        SELECT parameter_name, parameter_value, parameter_unit, measurement_time,
               latitude, longitude, depth_pressure, platform_number
        FROM argofinal
        WHERE parameter_name = :param
          AND latitude BETWEEN :lat_min AND :lat_max
          AND longitude BETWEEN :lon_min AND :lon_max
          AND measurement_time BETWEEN :t_start AND :t_end
        ORDER BY measurement_time DESC, depth_pressure ASC
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

    # Pre-compute the numbers the model would otherwise try to eyeball from 200
    # raw rows — it gets them wrong, and a summary is what the user asked for.
    summary = {}
    for param, rows in all_results.items():
        if not rows:
            summary[param] = {"n": 0}
            continue
        vals = [float(r["parameter_value"]) for r in rows if r["parameter_value"] is not None]
        depths = [float(r["depth_pressure"]) for r in rows if r["depth_pressure"] is not None]
        times = [r["measurement_time"] for r in rows if r["measurement_time"]]
        summary[param] = {
            "n": len(rows),
            "unit": rows[0].get("parameter_unit"),
            "value_min": round(min(vals), 4) if vals else None,
            "value_max": round(max(vals), 4) if vals else None,
            "value_mean": round(sum(vals) / len(vals), 4) if vals else None,
            "surface_value": round(vals[0], 4) if vals else None,
            "depth_min_m": round(min(depths), 1) if depths else None,
            "depth_max_m": round(max(depths), 1) if depths else None,
            "latest_reading": max(times).isoformat() if times else None,
            "earliest_reading": min(times).isoformat() if times else None,
            "platforms": sorted({r["platform_number"] for r in rows if r.get("platform_number")}),
        }

    return {
        "context": context,
        "summary": summary,
        "data": all_results,
        "presentation": (
            "Answer in GitHub-flavoured Markdown. Lead with a one-sentence takeaway, "
            "then a table with columns | Parameter | Surface | Range | Mean | Depth span | Latest reading |, "
            "using the numbers in `summary` verbatim. Do not list individual rows and do not "
            "invent values. Close with one short 'What this means' line in plain language. "
            "Do not print your Thought/Action reasoning."
        ),
    }
