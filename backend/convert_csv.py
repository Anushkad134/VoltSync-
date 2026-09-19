import csv
import re
import uuid
import os

input_file = "EV-Dataset.csv"
output_dir = "data"
output_file = os.path.join(output_dir, "charging_stations.csv")

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# The expected columns
headers = [
    "station_id",
    "cpo_name",
    "govt_private",
    "state",
    "district_city_village",
    "location",
    "latitude",
    "longitude",
    "charger_types_connectors_installed",
    "charger_rating",
    "connector_rating",
    "no_of_connectors"
]

def parse_line(line):
    # Remove quotes and newline
    line = line.strip().strip('"')
    
    # We can try to extract from right to left using regex, because the numbers at the end are somewhat structured.
    # Pattern to capture the end numbers and connector type:
    # ... <lat> <lon> <charger type...> <rating1> <rating2> <count>
    # Note: charger type might have spaces (e.g. Type-II AC)
    
    pattern = r'(.*?)\s+([0-9]+\.[0-9]+)\s+([0-9]+\.[0-9]+)\s+(.*?)\s+([0-9]+(?:\.[0-9]+)?)\s+([0-9]+(?:\.[0-9]+)?)\s+([0-9]+)$'
    match = re.search(pattern, line)
    
    if not match:
        return None
        
    prefix = match.group(1).strip()
    lat = match.group(2)
    lon = match.group(3)
    charger_type = match.group(4).strip()
    charger_rating = match.group(5)
    connector_rating = match.group(6)
    count = match.group(7)
    
    # Now parse the prefix: CPO, Govt, State, District, City, Location
    # They are separated by multiple spaces typically.
    parts = re.split(r'\s{2,}', prefix)
    
    if len(parts) >= 6:
        cpo = parts[0]
        govt = parts[1]
        state = parts[2]
        district = parts[3]
        city = parts[4]
        # Location might have been split if it contained multiple spaces, so we join the rest
        loc = " ".join(parts[5:])
    else:
        # Fallback if less than 6 parts
        cpo = parts[0] if len(parts) > 0 else ""
        govt = parts[1] if len(parts) > 1 else ""
        state = parts[2] if len(parts) > 2 else ""
        district = parts[3] if len(parts) > 3 else ""
        city = parts[4] if len(parts) > 4 else ""
        loc = " ".join(parts[5:]) if len(parts) > 5 else "Unknown"

    return {
        "station_id": f"ST-{uuid.uuid4().hex[:8].upper()}",
        "cpo_name": cpo,
        "govt_private": govt,
        "state": state,
        "district_city_village": f"{district} / {city}",
        "location": loc,
        "latitude": lat,
        "longitude": lon,
        "charger_types_connectors_installed": charger_type,
        "charger_rating": charger_rating,
        "connector_rating": connector_rating,
        "no_of_connectors": count
    }

with open(input_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Skip the first 3 lines (headers)
data_lines = lines[3:]

parsed_data = []
for i, line in enumerate(data_lines):
    if not line.strip():
        continue
    parsed = parse_line(line)
    if parsed:
        parsed_data.append(parsed)
    else:
        pass # Ignore failed parsing

with open(output_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()
    writer.writerows(parsed_data)

print(f"Successfully converted {len(parsed_data)} stations to {output_file}")
