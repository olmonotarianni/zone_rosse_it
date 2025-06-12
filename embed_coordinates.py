"""
embed_coordinates.py
Embed coordinates with calculated intersection points and preserve data structure
"""

import json
import math

def calculate_distance(coord1, coord2):
    """Calculate distance between two coordinates using Haversine formula"""
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Earth radius in kilometers
    
    return r * c * 1000  # Return distance in meters

def is_valid_coordinate(coord):
    """Check if coordinate is valid"""
    if not coord or len(coord) != 2:
        return False
    lat, lon = coord
    return (-90 <= lat <= 90) and (-180 <= lon <= 180) and lat != 0 and lon != 0

def find_intersection_point(primary_coords, intersecting_coords):
    """Find the intersection point between two streets"""
    if not primary_coords or not intersecting_coords:
        return None
    
    # Filter valid coordinates
    valid_primary = [c for c in primary_coords if is_valid_coordinate(c)]
    valid_intersecting = [c for c in intersecting_coords if is_valid_coordinate(c)]
    
    if not valid_primary or not valid_intersecting:
        return None
    
    min_distance = float('inf')
    best_primary = None
    best_intersecting = None
    
    for p_coord in valid_primary:
        for i_coord in valid_intersecting:
            distance = calculate_distance(p_coord, i_coord)
            if distance < min_distance:
                min_distance = distance
                best_primary = p_coord
                best_intersecting = i_coord
    
    if best_primary and best_intersecting:
        lat = (best_primary[0] + best_intersecting[0]) / 2
        lon = (best_primary[1] + best_intersecting[1]) / 2
        if is_valid_coordinate([lat, lon]):
            return (lat, lon)
    
    return None

def process_coordinates(coordinates_data):
    """Process coordinates and calculate intersection points without losing original data"""
    processed_count = 0
    
    for ord_id, ord_data in coordinates_data.items():
        for zone_name, zone_data in ord_data['zones'].items():
            for street_name, street_data in zone_data.items():

                if not street_data:
                    continue
                    
                if street_data.get('metadata', {}).get('type') == 'incrocio':
                    # Extract coordinates
                    primary_coords = []
                    intersecting_coords = []
                    
                    for coord_entry in street_data.get('coordinates', []):
                        if coord_entry.get('type') == 'primary' and is_valid_coordinate(coord_entry.get('coords')):
                            primary_coords.append(coord_entry['coords'])
                        elif coord_entry.get('type') == 'intersecting' and is_valid_coordinate(coord_entry.get('coords')):
                            intersecting_coords.append(coord_entry['coords'])
                    
                    # Calculate intersection point
                    intersection = find_intersection_point(primary_coords, intersecting_coords)
                    
                    if intersection:
                        # Add intersection point to coordinates (don't replace, add)
                        street_data['coordinates'].append({
                            'type': 'intersection',
                            'coords': list(intersection)
                        })
                        street_data['metadata']['has_calculated_intersection'] = True
                        processed_count += 1
                        print(f"✅ Calculated intersection: {street_name}")
                    else:
                        print(f"❌ Failed to calculate: {street_name}")
    
    print(f"🎯 Processed {processed_count} intersections")
    return coordinates_data

def embed_coordinates():
    """Embed coordinates into HTML viewer"""
    
    coordinates_file = 'coordinates.json'  
    baseline_html = 'rome_viewer.html'
    output_file = 'rome_viewer_embedded.html'
    
    # Load coordinates
    try:
        with open(coordinates_file, 'r', encoding='utf-8') as f:
            coordinates_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ {coordinates_file} not found.")
        return
    
    # Load HTML
    try:
        with open(baseline_html, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"❌ {baseline_html} not found.")
        return
    
    print("🧮 Processing coordinates...")
    
    # Process coordinates (adds intersection points, preserves original data)
    coordinates_data = process_coordinates(coordinates_data)
    
    # Convert to JavaScript
    js_data = json.dumps(coordinates_data, indent=4)
    
    # Replace fetch with embedded data
    fetch_pattern = "coordinatesData = await fetch('./coordinates.json').then(response => response.json());"
    embedded_line = f"coordinatesData = {js_data};"
    
    if fetch_pattern in html_content:
        html_content = html_content.replace(fetch_pattern, embedded_line)
        print("✅ Embedded coordinates data")
    else:
        # Try alternative patterns
        patterns = [
            "await fetch('./coordinates.json')",
            "await fetch('coordinates.json')"
        ]
        
        found = False
        for pattern in patterns:
            if pattern in html_content:
                lines = html_content.split('\n')
                for i, line in enumerate(lines):
                    if pattern in line:
                        indent = len(line) - len(line.lstrip())
                        lines[i] = ' ' * indent + embedded_line
                        html_content = '\n'.join(lines)
                        print("✅ Embedded coordinates data")
                        found = True
                        break
                break
        
        if not found:
            print("❌ Could not find coordinates loading pattern in HTML")
            return
    
    # Save
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Created {output_file}")
    
    # Print summary
    total_ordinances = len(coordinates_data)
    total_streets = 0
    streets_with_coords = 0
    intersections = 0
    
    for ord_data in coordinates_data.values():
        for zone_data in ord_data['zones'].values():
            for street_name, street_data in zone_data.items():
                total_streets += 1
                if street_data and street_data.get('coordinates'):
                    streets_with_coords += 1
                    if street_data.get('metadata', {}).get('has_calculated_intersection'):
                        intersections += 1
        
    print(f"\n📊 Summary:")
    print(f"   📋 {total_ordinances} ordinances")
    print(f"   🏛️ {streets_with_coords}/{total_streets} streets with coordinates")
    print(f"   🎯 {intersections} calculated intersections")

if __name__ == "__main__":
    embed_coordinates()