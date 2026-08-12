import requests, pandas as pd

url = "http://overpass-api.de/api/interpreter"
query = """
[out:json][timeout:60];
(
  node["place"="island"](6,68,37,97);
  way["place"="island"](6,68,37,97);
  relation["place"="island"](6,68,37,97);
);
out center;
"""

response = requests.post(url, data={"data": query})
data = response.json()

islands = []
for el in data["elements"]:
    name = el.get("tags", {}).get("name", "Unnamed Island")
    if "lat" in el and "lon" in el:
        lat, lon = el["lat"], el["lon"]
    elif "center" in el:
        lat, lon = el["center"]["lat"], el["center"]["lon"]
    else:
        continue
    islands.append({"name": name, "latitude": lat, "longitude": lon})

df = pd.DataFrame(islands)
df.to_csv("indian_islands.csv", index=False)

print(f"✅ Saved {len(df)} islands to indian_islands.csv")

