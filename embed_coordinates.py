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

def find_nearest_point_on_street(street_coords, reference_point):
    """Find the nearest point on a street to a reference point"""
    if not street_coords or not reference_point or not is_valid_coordinate(reference_point):
        return None
    
    min_distance = float('inf')
    nearest_point = None
    nearest_index = -1
    
    for i, coord in enumerate(street_coords):
        if is_valid_coordinate(coord):
            distance = calculate_distance(coord, reference_point)
            if distance < min_distance:
                min_distance = distance
                nearest_point = coord
                nearest_index = i
    
    return {'point': nearest_point, 'index': nearest_index, 'distance': min_distance}

def get_bounding_box(coord1, coord2):
    """Get bounding box from two coordinates"""
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    return {
        'min_lat': min(lat1, lat2),
        'max_lat': max(lat1, lat2),
        'min_lon': min(lon1, lon2),
        'max_lon': max(lon1, lon2)
    }

def is_point_in_bounding_box(point, bbox):
    """Check if a point is within the bounding box"""
    lat, lon = point
    return (bbox['min_lat'] <= lat <= bbox['max_lat'] and 
            bbox['min_lon'] <= lon <= bbox['max_lon'])

def compute_street_tract(primary_coords, endpoint_coords_1, endpoint_coords_2):
    """Compute the tract of a street between two endpoints"""
    if not primary_coords or not endpoint_coords_1 or not endpoint_coords_2:
        return primary_coords
    
    # Find nearest points on primary street to both endpoints
    nearest_to_end1 = find_nearest_point_on_street(primary_coords, endpoint_coords_1[0] if endpoint_coords_1 else None)
    nearest_to_end2 = find_nearest_point_on_street(primary_coords, endpoint_coords_2[0] if endpoint_coords_2 else None)
    
    if not nearest_to_end1 or not nearest_to_end2:
        return primary_coords
    
    # Create bounding box from the two nearest points
    bbox = get_bounding_box(nearest_to_end1['point'], nearest_to_end2['point'])
    
    # Filter street coordinates to only those within the bounding box
    tract_coords = []
    for coord in primary_coords:
        if is_valid_coordinate(coord) and is_point_in_bounding_box(coord, bbox):
            tract_coords.append(coord)
    
    # Always include the exact nearest points if they're not already in the tract
    if nearest_to_end1['point'] not in tract_coords:
        tract_coords.append(nearest_to_end1['point'])
    if nearest_to_end2['point'] not in tract_coords:
        tract_coords.append(nearest_to_end2['point'])
    
    return tract_coords if tract_coords else primary_coords

def process_coordinates(coordinates_data):
    """Process coordinates and calculate intersection points and street tracts"""
    processed_count = 0
    tract_count = 0
    civic_count = 0
    
    for ord_id, ord_data in coordinates_data.items():
        for zone_name, zone_data in ord_data['zones'].items():
            for street_name, street_data in zone_data.items():

                if not street_data:
                    continue
                    
                metadata_type = street_data.get('metadata', {}).get('type')
                
                if metadata_type == 'civico':
                    # Handle civic numbers - use only special coordinates if available
                    special_coords = street_data.get('special_coordinates', [])
                    
                    if special_coords:
                        # Replace coordinates with only the civic number coordinates
                        street_data['coordinates'] = [
                            {'type': 'civic', 'coords': coord} for coord in special_coords
                        ]
                        street_data['metadata']['has_civic_coordinates'] = True
                        street_data['metadata']['civic_count'] = len(special_coords)
                        civic_count += 1
                        print(f"✅ Using civic coordinates: {street_name} ({len(special_coords)} points)")
                    else:
                        print(f"⚠️ No civic coordinates found for: {street_name}")
                
                elif metadata_type == 'incrocio':
                    # Handle intersections (existing logic)
                    primary_coords = []
                    intersecting_coords = []
                    
                    for coord_entry in street_data.get('coordinates', []):
                        if coord_entry.get('type') == 'primary' and is_valid_coordinate(coord_entry.get('coords')):
                            primary_coords.append(coord_entry['coords'])
                        elif coord_entry.get('type') == 'intersecting' and is_valid_coordinate(coord_entry.get('coords')):
                            intersecting_coords.append(coord_entry['coords'])
                    
                    intersection = find_intersection_point(primary_coords, intersecting_coords)
                    
                    if intersection:
                        street_data['coordinates'].append({
                            'type': 'intersection',
                            'coords': list(intersection)
                        })
                        street_data['metadata']['has_calculated_intersection'] = True
                        processed_count += 1
                        print(f"✅ Calculated intersection: {street_name}")
                    else:
                        print(f"❌ Failed to calculate: {street_name}")
                
                elif metadata_type == 'tratto':
                    # Handle street tracts
                    primary_coords = []
                    endpoint_coords_1 = []
                    endpoint_coords_2 = []
                    
                    for coord_entry in street_data.get('coordinates', []):
                        coord_type = coord_entry.get('type')
                        coords = coord_entry.get('coords')
                        
                        if coord_type == 'primary' and is_valid_coordinate(coords):
                            primary_coords.append(coords)
                        elif coord_type == 'endpoint_1' and is_valid_coordinate(coords):
                            endpoint_coords_1.append(coords)
                        elif coord_type == 'endpoint_2' and is_valid_coordinate(coords):
                            endpoint_coords_2.append(coords)
                    
                    if primary_coords and endpoint_coords_1 and endpoint_coords_2:
                        # Compute the tract
                        tract_coords = compute_street_tract(primary_coords, endpoint_coords_1, endpoint_coords_2)
                        
                        # Replace coordinates with tract coordinates
                        street_data['coordinates'] = [
                            {'type': 'tract', 'coords': coord} for coord in tract_coords
                        ]
                        street_data['metadata']['has_calculated_tract'] = True
                        street_data['metadata']['original_primary_count'] = len(primary_coords)
                        street_data['metadata']['tract_count'] = len(tract_coords)
                        
                        tract_count += 1
                        print(f"✅ Calculated tract: {street_name} ({len(tract_coords)}/{len(primary_coords)} points)")
                    else:
                        missing = []
                        if not primary_coords: missing.append("primary")
                        if not endpoint_coords_1: missing.append("endpoint_1") 
                        if not endpoint_coords_2: missing.append("endpoint_2")
                        print(f"❌ Failed to calculate tract for {street_name}: missing {', '.join(missing)}")
    
    print(f"🎯 Processed {processed_count} intersections, {tract_count} tracts, and {civic_count} civic numbers")
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
    civic_numbers = 0
    tracts = 0
    
    for ord_data in coordinates_data.values():
        for zone_data in ord_data['zones'].values():
            for street_name, street_data in zone_data.items():
                total_streets += 1
                if street_data and street_data.get('coordinates'):
                    streets_with_coords += 1
                    if street_data.get('metadata', {}).get('has_calculated_intersection'):
                        intersections += 1
                    if street_data.get('metadata', {}).get('has_civic_coordinates'):
                        civic_numbers += 1
                    if street_data.get('metadata', {}).get('has_calculated_tract'):
                        tracts += 1
        
    print(f"\n📊 Summary:")
    print(f"   📋 {total_ordinances} ordinances")
    print(f"   🏛️ {streets_with_coords}/{total_streets} streets with coordinates")
    print(f"   🎯 {intersections} calculated intersections")
    print(f"   🏠 {civic_numbers} civic number coordinates")
    print(f"   📏 {tracts} calculated tracts")

if __name__ == "__main__":
    embed_coordinates()