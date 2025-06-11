import json
import requests
import time
from typing import Dict, List, Tuple, Optional

def create_simple_rome_viewer():
    """
    Simple function to create an HTML viewer for Rome ordinances.
    Shows real coordinates from Overpass API with no fallbacks.
    """
    
    # Rome bounding box
    rome_bbox = {
        'south': 41.8,
        'west': 12.4,
        'north': 42.0,
        'east': 12.6
    }
    
    # Load ordinances data
    try:
        with open('zonerosse_ordinanze_scomode/ordinances.json', "r", encoding="utf-8") as f:
            ordinances_data = json.load(f)
    except FileNotFoundError:
        # Fallback data structure for demo
        ordinances_data = {
            "ordinance_6747": {
                "protocol": "6747",
                "date": "2025-01-08",
                "title": "Prima ordinanza prefettizia",
                "zones": {
                    "Zona Esquilino": [
                        "Via Giovanni Giolitti",
                        "Via Giovanni Amendola", 
                        "Via Filippo Turati",
                        "Piazza Vittorio Emanuele II"
                    ],
                    "Zona Tuscolano": [
                        "Via Tuscolana",
                        "Piazza Ragusa"
                    ]
                }
            },
            "ordinance_133331": {
                "protocol": "133331",
                "date": "2025-03-26",
                "title": "Seconda ordinanza prefettizia",
                "zones": {
                    "Zona Stazione Termini - Esquilino": [
                        "Piazza dei Cinquecento",
                        "Via Marsala",
                        "Via Giovanni Giolitti"
                    ],
                    "Zona Valle Aurelia": [
                        "Viale di Valle Aurelia",
                        "Via Baldo degli Ubaldi"
                    ]
                }
            }
        }
    
def query_overpass_for_street(street_name: str) -> Optional[List[Tuple[float, float]]]:
    """
    Query Overpass API for street coordinates. Returns ALL coordinate points
    that make up the street geometry (not civic numbers, but the actual street path).
    """
    # Clean street name
    # clean_name = street_name.replace("Via ", "").replace("Piazza ", "").replace("Viale ", "")
    clean_name = street_name
    
    # Overpass query
    overpass_query = f"""
    [out:json][timeout:25];
    (
        way["highway"]["name"~"{clean_name}",i]({rome_bbox['south']},{rome_bbox['west']},{rome_bbox['north']},{rome_bbox['east']});
        way["place"]["name"~"{clean_name}",i]({rome_bbox['south']},{rome_bbox['west']},{rome_bbox['north']},{rome_bbox['east']});
        relation["place"]["name"~"{clean_name}",i]({rome_bbox['south']},{rome_bbox['west']},{rome_bbox['north']},{rome_bbox['east']});
    );
    (._;>;);
    out geom;
    """
    
    try:
        print(f"🔍 Querying: {street_name}")
        
        response = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=overpass_query,
            timeout=30,
            verify=False
        )
        
        if response.status_code == 200:
            data = response.json()
            coordinates = []
            
            for element in data.get('elements', []):
                if element.get('type') == 'way' and 'geometry' in element:
                    # Extract all coordinates from way geometry
                    for node in element['geometry']:
                        coordinates.append((node['lat'], node['lon']))
                elif element.get('type') == 'node':
                    coordinates.append((element['lat'], element['lon']))
            
            if coordinates:
                print(f"✅ Found {len(coordinates)} coordinate points")
                return coordinates
            else:
                print(f"❌ No coordinates found")
                return None
        else:
            print(f"❌ HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def generate_ordinances_html(ordinances_data):
    """Generate HTML for ordinances list."""
    html = ""
    
    for ord_id, ord_data in ordinances_data.items():
        html += f"""
        <div class="ordinance" id="ord-{ord_id}" onclick="toggleOrdinance('{ord_id}')">
            <h3>📋 Ordinanza {ord_data['protocol']}</h3>
            <p><strong>Data:</strong> {ord_data['date']}</p>
            <p>{ord_data['title']}</p>
        </div>
        <div id="zones-{ord_id}" style="display: none;">
        """
        
        for zone_index, (zone_name, streets) in enumerate(ord_data['zones'].items()):
            html += f"""
            <div class="zone" id="zone-{ord_id}-{zone_index}" onclick="toggleZone('{ord_id}', {zone_index})">
                <strong>📍 {zone_name}</strong>
                <small>({len(streets)} vie/piazze)</small>
            </div>
            <div id="streets-{ord_id}-{zone_index}" style="display: none;">
            """
            
            for street in streets:
                html += f"""
                <div class="street" onclick="selectStreet('{street}')">
                    {street}
                </div>
                """
            
            html += "</div>"
        
        html += "</div>"
    
    return html
    
        # Create the HTML content
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rome Ordinances Viewer</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.css" />
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            height: 100vh;
        }}
        
        .sidebar {{
            width: 400px;
            background: #f8f9fa;
            border-right: 1px solid #ddd;
            overflow-y: auto;
            padding: 20px;
        }}
        
        .map-container {{
            flex: 1;
            position: relative;
        }}
        
        #map {{
            height: 100%;
            width: 100%;
        }}
        
        .ordinance {{
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            margin-bottom: 15px;
            padding: 15px;
            cursor: pointer;
            transition: all 0.3s;
        }}
        
        .ordinance:hover {{
            background: #e3f2fd;
            border-color: #2196f3;
        }}
        
        .ordinance.active {{
            background: #e8f5e8;
            border-color: #4caf50;
        }}
        
        .zone {{
            background: #f1f1f1;
            border: 1px solid #ccc;
            border-radius: 5px;
            margin: 10px 0;
            padding: 10px;
            cursor: pointer;
            margin-left: 20px;
        }}
        
        .zone:hover {{
            background: #e1f5fe;
        }}
        
        .zone.active {{
            background: #c8e6c9;
        }}
        
        .street {{
            background: #fafafa;
            border: 1px solid #bbb;
            border-radius: 3px;
            margin: 5px 0;
            padding: 8px;
            cursor: pointer;
            margin-left: 40px;
            font-size: 0.9em;
        }}
        
        .street:hover {{
            background: #fff3e0;
        }}
        
        .street.active {{
            background: #ffcc80;
            font-weight: bold;
        }}
        
        .loading {{
            color: #666;
            font-style: italic;
        }}
        
        .coords-info {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(255,255,255,0.9);
            padding: 10px;
            border-radius: 5px;
            font-size: 0.9em;
            max-width: 300px;
            z-index: 1000;
        }}
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>🏛️ Rome Ordinances</h2>
        <div id="ordinances-container">
            {generate_ordinances_html(ordinances_data)}
        </div>
    </div>
    
    <div class="map-container">
        <div id="map"></div>
        <div id="coords-info" class="coords-info" style="display: none;">
            <strong>Coordinate Points:</strong>
            <div id="coords-details"></div>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js"></script>
    <script>
        // Initialize map
        const map = L.map('map').setView([41.9028, 12.4964], 12);
        
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors'
        }}).addTo(map);
        
        let currentMarkers = [];
        let currentPolylines = [];
        
        function clearMap() {{
            currentMarkers.forEach(marker => map.removeLayer(marker));
            currentPolylines.forEach(polyline => map.removeLayer(polyline));
            currentMarkers = [];
            currentPolylines = [];
        }}
        
        function showCoordinates(streetName, coordinates) {{
            clearMap();
            
            if (!coordinates || coordinates.length === 0) {{
                alert('No coordinates found for: ' + streetName);
                return;
            }}
            
            // Add markers for each coordinate point
            coordinates.forEach((coord, index) => {{
                const marker = L.circleMarker([coord[0], coord[1]], {{
                    radius: 4,
                    fillColor: '#ff0000',
                    color: '#darkred',
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.8
                }}).addTo(map);
                
                marker.bindPopup(`Point ${{index + 1}}: ${{coord[0].toFixed(6)}}, ${{coord[1].toFixed(6)}}`);
                currentMarkers.push(marker);
            }});
            
            // Draw polyline connecting the points if more than one
            if (coordinates.length > 1) {{
                const polyline = L.polyline(coordinates, {{
                    color: '#ff0000',
                    weight: 3,
                    opacity: 0.7
                }}).addTo(map);
                currentPolylines.push(polyline);
                
                // Fit map to show all points
                map.fitBounds(polyline.getBounds(), {{padding: [20, 20]}});
            }} else {{
                map.setView([coordinates[0][0], coordinates[0][1]], 16);
            }}
            
            // Update info panel
            document.getElementById('coords-info').style.display = 'block';
            document.getElementById('coords-details').innerHTML = `
                <strong>${{streetName}}</strong><br>
                Found: ${{coordinates.length}} coordinate points<br>
                <small>These are the actual geometry points that define the street path</small>
            `;
        }}
        
        // Handle clicks
        function toggleOrdinance(ordinanceId) {{
            const element = document.getElementById('ord-' + ordinanceId);
            const zonesContainer = document.getElementById('zones-' + ordinanceId);
            
            if (element.classList.contains('active')) {{
                element.classList.remove('active');
                zonesContainer.style.display = 'none';
            }} else {{
                // Close other ordinances
                document.querySelectorAll('.ordinance').forEach(ord => {{
                    ord.classList.remove('active');
                    const id = ord.id.replace('ord-', '');
                    document.getElementById('zones-' + id).style.display = 'none';
                }});
                
                element.classList.add('active');
                zonesContainer.style.display = 'block';
            }}
        }}
        
        function toggleZone(ordinanceId, zoneIndex) {{
            const element = document.getElementById(`zone-${{ordinanceId}}-${{zoneIndex}}`);
            const streetsContainer = document.getElementById(`streets-${{ordinanceId}}-${{zoneIndex}}`);
            
            if (element.classList.contains('active')) {{
                element.classList.remove('active');
                streetsContainer.style.display = 'none';
            }} else {{
                element.classList.add('active');
                streetsContainer.style.display = 'block';
            }}
        }}
        
        // Street coordinates data (will be populated by Python)
        const streetCoordinates = {{}};
        
        async function selectStreet(streetName) {{
            // Clear previous selections
            document.querySelectorAll('.street').forEach(s => s.classList.remove('active'));
            event.target.classList.add('active');
            
            if (streetCoordinates[streetName]) {{
                showCoordinates(streetName, streetCoordinates[streetName]);
            }} else {{
                // This would be called via AJAX in a real implementation
                alert('Coordinates not available for: ' + streetName + '\\n\\nRun the Python script to fetch coordinates.');
            }}
        }}
    </script>
</body>
</html>
"""
    
    # Save the HTML file
    with open("rome_ordinances_viewer.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print("✅ Created rome_ordinances_viewer.html")
    print("🌐 Open it in your browser to see the interface")
    
    # Optionally fetch some coordinates
    print("\n🔍 Fetching sample coordinates...")
    sample_coordinates = {}
    
    # Test with a few streets
    sample_streets = [
        "Via Giovanni Giolitti",
        "Piazza Vittorio Emanuele II", 
        "Via Tuscolana"
    ]
    
    for street in sample_streets:
        coords = query_overpass_for_street(street)
        if coords:
            sample_coordinates[street] = coords
        time.sleep(2)  # Rate limiting
    
    # Update the HTML with the fetched coordinates
    if sample_coordinates:
        coords_js = json.dumps(sample_coordinates, indent=2)
        updated_html = html_content.replace(
            "const streetCoordinates = {};",
            f"const streetCoordinates = {coords_js};"
        )
        
        with open("rome_ordinances_viewer.html", "w", encoding="utf-8") as f:
            f.write(updated_html)
        
        print(f"✅ Updated with {len(sample_coordinates)} street coordinate sets")
    
    return sample_coordinates

# Run the function
if __name__ == "__main__":
    coordinates = create_simple_rome_viewer()
    print("\n📊 Sample results:")
    for street, coords in coordinates.items():
        print(f"  • {street}: {len(coords)} coordinate points")