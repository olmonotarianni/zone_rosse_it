import json
import math
import re
from typing import List, Dict, Tuple, Optional, Set

# Import city configurations
from city_configs import CITIES, CITY_PREFIXES, CityConfig

def calculate_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """Calculate distance between coordinates using Haversine formula"""
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return 6371 * c * 1000  # Distance in meters

def is_coordinate_in_bbox(coord: Tuple[float, float], bbox: Tuple[float, float, float, float]) -> bool:
    """Check if coordinate is within bounding box"""
    lat, lon = coord
    min_lat, min_lon, max_lat, max_lon = bbox
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon

def get_zone_bbox(city_config: CityConfig, zone_name: str) -> Optional[Tuple[float, float, float, float]]:
    """Get bounding box for a zone, handling zone mappings"""
    # First check direct zone name
    if zone_name in city_config.zone_bboxes:
        return city_config.zone_bboxes[zone_name]
    
    # Check zone mappings
    if zone_name in city_config.zone_mappings:
        mapped_zone = city_config.zone_mappings[zone_name]
        if mapped_zone in city_config.zone_bboxes:
            return city_config.zone_bboxes[mapped_zone]
    
    # Check case-insensitive matches
    zone_lower = zone_name.lower()
    for bbox_zone in city_config.zone_bboxes:
        if bbox_zone.lower() == zone_lower:
            return city_config.zone_bboxes[bbox_zone]
    
    # Check partial matches in mappings
    for mapping_key, mapped_zone in city_config.zone_mappings.items():
        if zone_lower in mapping_key.lower() or mapping_key.lower() in zone_lower:
            if mapped_zone in city_config.zone_bboxes:
                return city_config.zone_bboxes[mapped_zone]
    
    # More flexible matching for common patterns
    zone_clean = zone_lower.replace('.', '').replace('ff.ss.', '').replace('stazione', '').strip()
    
    # Check if cleaned zone name matches any bbox keys
    for bbox_zone in city_config.zone_bboxes:
        bbox_clean = bbox_zone.lower().replace('stazione_', '').replace('zona_', '')
        if zone_clean in bbox_clean or bbox_clean in zone_clean:
            return city_config.zone_bboxes[bbox_zone]
    
    # Check mappings with cleaned names
    for mapping_key, mapped_zone in city_config.zone_mappings.items():
        mapping_clean = mapping_key.lower().replace('stazione_', '').replace('zona_', '').replace('_', ' ')
        if zone_clean in mapping_clean or mapping_clean in zone_clean:
            if mapped_zone in city_config.zone_bboxes:
                return city_config.zone_bboxes[mapped_zone]
    
    return None

def extract_all_coordinates(place_data: Dict, zone_bbox: Optional[Tuple[float, float, float, float]] = None) -> List[Tuple[float, float]]:
    """Extract all coordinate points from a place (geometries + special coordinates), filtered by zone bbox"""
    points = []
    
    # From geometries (LineString or Polygon)
    for geom in place_data.get('geometries', []):
        coords = geom.get('coordinates', [])
        if geom.get('type') == 'Polygon':
            coords = coords[0]  # Outer ring
        for coord in coords:
            if len(coord) >= 2:
                point = (coord[0], coord[1])
                # Filter by zone bbox if provided
                if zone_bbox is None or is_coordinate_in_bbox(point, zone_bbox):
                    points.append(point)
    
    # From special coordinates (Points)
    for special in place_data.get('special_coordinates', []):
        if special.get('type') == 'Point':
            coord = special.get('coordinates', [])
            if len(coord) >= 2:
                point = (coord[0], coord[1])
                # Filter by zone bbox if provided
                if zone_bbox is None or is_coordinate_in_bbox(point, zone_bbox):
                    points.append(point)
    
    return points

def filter_geometries_by_bbox(geometries: List[Dict], zone_bbox: Tuple[float, float, float, float]) -> List[Dict]:
    """Filter geometries to only include coordinates within the zone bbox"""
    filtered_geometries = []
    
    for geom in geometries:
        if not geom.get('coordinates'):
            continue
            
        geom_type = geom.get('type')
        coords = geom.get('coordinates')
        
        if geom_type == 'LineString':
            # Filter LineString coordinates
            filtered_coords = []
            for coord in coords:
                if len(coord) >= 2:
                    point = (coord[0], coord[1])
                    if is_coordinate_in_bbox(point, zone_bbox):
                        filtered_coords.append(coord)
            
            # Only keep geometry if it has coordinates in the bbox
            if filtered_coords:
                filtered_geom = geom.copy()
                filtered_geom['coordinates'] = filtered_coords
                filtered_geom['bbox_filtered'] = True
                filtered_geometries.append(filtered_geom)
                
        elif geom_type == 'Polygon':
            # Filter Polygon coordinates (outer ring)
            if coords and len(coords) > 0:
                outer_ring = coords[0]
                filtered_ring = []
                for coord in outer_ring:
                    if len(coord) >= 2:
                        point = (coord[0], coord[1])
                        if is_coordinate_in_bbox(point, zone_bbox):
                            filtered_ring.append(coord)
                
                # Only keep polygon if it has coordinates in the bbox
                if len(filtered_ring) >= 3:  # Minimum for a valid polygon
                    filtered_geom = geom.copy()
                    filtered_geom['coordinates'] = [filtered_ring]
                    filtered_geom['bbox_filtered'] = True
                    filtered_geometries.append(filtered_geom)
        else:
            # For other geometry types, keep as is for now
            filtered_geometries.append(geom)
    
    return filtered_geometries

def filter_special_coordinates_by_bbox(special_coords: List[Dict], zone_bbox: Tuple[float, float, float, float]) -> List[Dict]:
    """Filter special coordinates by zone bbox"""
    filtered_coords = []
    
    for special in special_coords:
        if special.get('type') == 'Point':
            coord = special.get('coordinates', [])
            if len(coord) >= 2:
                point = (coord[0], coord[1])
                if is_coordinate_in_bbox(point, zone_bbox):
                    filtered_special = special.copy()
                    filtered_special['bbox_filtered'] = True
                    filtered_coords.append(filtered_special)
        else:
            # Keep non-Point special coordinates as is
            filtered_coords.append(special)
    
    return filtered_coords

def find_intersection_point(place1_data: Dict, place2_data: Dict, threshold: float = 100.0, zone_bbox: Optional[Tuple[float, float, float, float]] = None) -> Optional[Tuple[float, float]]:
    """Find intersection point between two places, filtered by zone bbox"""
    points1 = extract_all_coordinates(place1_data, zone_bbox)
    points2 = extract_all_coordinates(place2_data, zone_bbox)
    
    if not points1 or not points2:
        return None
    
    # Find closest points between the two places
    min_distance = float('inf')
    best_point1 = None
    best_point2 = None
    
    for p1 in points1:
        for p2 in points2:
            distance = calculate_distance(p1, p2)
            if distance < min_distance:
                min_distance = distance
                best_point1 = p1
                best_point2 = p2
    
    # If points are close enough, create intersection point
    if min_distance < threshold and best_point1 and best_point2:
        lat = (best_point1[0] + best_point2[0]) / 2
        lon = (best_point1[1] + best_point2[1]) / 2
        intersection_point = (lat, lon)
        
        # Check if intersection point is in zone bbox
        if zone_bbox is None or is_coordinate_in_bbox(intersection_point, zone_bbox):
            return intersection_point
    
    return None

def compute_tract_segment(street_data: Dict, endpoint1_data: Dict, endpoint2_data: Dict, margin: float = 0.0005, zone_bbox: Optional[Tuple[float, float, float, float]] = None) -> List[Dict]:
    """Compute street tract between two endpoints, filtered by zone bbox"""
    street_points = extract_all_coordinates(street_data, zone_bbox)
    endpoint1_points = extract_all_coordinates(endpoint1_data, zone_bbox)
    endpoint2_points = extract_all_coordinates(endpoint2_data, zone_bbox)
    
    if not street_points or not endpoint1_points or not endpoint2_points:
        # Return filtered geometries if points are filtered out
        if zone_bbox:
            return filter_geometries_by_bbox(street_data.get('geometries', []), zone_bbox)
        return street_data.get('geometries', [])
    
    # Find nearest points on street to both endpoints
    min_dist1, nearest_to_end1 = float('inf'), None
    for street_point in street_points:
        for end1_point in endpoint1_points:
            dist = calculate_distance(street_point, end1_point)
            if dist < min_dist1:
                min_dist1, nearest_to_end1 = dist, street_point
    
    min_dist2, nearest_to_end2 = float('inf'), None
    for street_point in street_points:
        for end2_point in endpoint2_points:
            dist = calculate_distance(street_point, end2_point)
            if dist < min_dist2:
                min_dist2, nearest_to_end2 = dist, street_point
    
    if not nearest_to_end1 or not nearest_to_end2:
        if zone_bbox:
            return filter_geometries_by_bbox(street_data.get('geometries', []), zone_bbox)
        return street_data.get('geometries', [])
    
    # Create bounding box for tract
    min_lat = min(nearest_to_end1[0], nearest_to_end2[0]) - margin
    max_lat = max(nearest_to_end1[0], nearest_to_end2[0]) + margin
    min_lon = min(nearest_to_end1[1], nearest_to_end2[1]) - margin
    max_lon = max(nearest_to_end1[1], nearest_to_end2[1]) + margin
    
    # Combine tract bbox with zone bbox if provided
    if zone_bbox:
        zone_min_lat, zone_min_lon, zone_max_lat, zone_max_lon = zone_bbox
        min_lat = max(min_lat, zone_min_lat)
        max_lat = min(max_lat, zone_max_lat)
        min_lon = max(min_lon, zone_min_lon)
        max_lon = min(max_lon, zone_max_lon)
    
    # Filter street geometries to tract segment
    filtered_geometries = []
    for geom in street_data.get('geometries', []):
        if geom.get('type') != 'LineString':
            continue
        
        filtered_coords = []
        for coord in geom.get('coordinates', []):
            if min_lat <= coord[0] <= max_lat and min_lon <= coord[1] <= max_lon:
                filtered_coords.append(coord)
        
        if filtered_coords:
            tract_geom = {
                'type': 'LineString',
                'coordinates': filtered_coords,
                'osm_id': geom.get('osm_id'),
                'is_tract_segment': True,
                'bbox_filtered': True
            }
            filtered_geometries.append(tract_geom)
    
    return filtered_geometries if filtered_geometries else (
        filter_geometries_by_bbox(street_data.get('geometries', []), zone_bbox) if zone_bbox 
        else street_data.get('geometries', [])
    )

class PlacesEmbedder:
    def __init__(self, places_file: str = "coordinates.json", ordinances_file: str = "ordinanze.json"):
        self.places_file = places_file
        self.ordinances_file = ordinances_file
        self.places_catalog = {}
        self.ordinances = {}
        
        # Load data
        self._load_places_catalog()
        self._load_ordinances()
    
    def _load_places_catalog(self):
        """Load places catalog"""
        try:
            with open(self.places_file, 'r', encoding='utf-8') as f:
                self.places_catalog = json.load(f)
            print(f"📦 Loaded {len(self.places_catalog)} places from {self.places_file}")
        except FileNotFoundError:
            print(f"❌ Places catalog not found: {self.places_file}")
            raise
    
    def _load_ordinances(self):
        """Load ordinances data"""
        try:
            with open(self.ordinances_file, 'r', encoding='utf-8') as f:
                self.ordinances = json.load(f)
            print(f"📦 Loaded {len(self.ordinances)} ordinances from {self.ordinances_file}")
        except FileNotFoundError:
            print(f"❌ Ordinances file not found: {self.ordinances_file}")
            raise
    
    def detect_city_from_ordinance(self, ord_id: str, ord_data: Dict) -> Optional[CityConfig]:
        """Detect city from ordinance ID and data"""
        # Extract city code from ordinance ID (e.g., "RM_ordinance_6747" -> "RM")
        if '_' in ord_id:
            city_code = ord_id.split('_')[0].upper()
            if city_code in CITIES:
                return CITIES[city_code]
        
        # Fallback: check zones for city-specific patterns
        zones = ord_data.get('zones', {})
        zone_names = ' '.join(zones.keys()).lower()
        
        for config in CITIES.values():
            # Check if any zone names match city-specific patterns
            for zone_mapping in config.zone_mappings.keys():
                if zone_mapping.lower() in zone_names:
                    return config
        
        return None
    
    def parse_specification(self, specification: str) -> Dict:
        """Parse location specification into structured data"""
        spec = specification.strip()
        
        # Civic number pattern
        civico_match = re.search(r'^(.+?)\s*\(fronte civico (\d+)\)$', spec)
        if civico_match:
            return {
                'type': 'civico',
                'primary': civico_match.group(1).strip(),
                'civic_number': civico_match.group(2),
                'places': [civico_match.group(1).strip(), f"{civico_match.group(1).strip()} civico {civico_match.group(2)}"]
            }
        
        # Tract pattern
        tratto_match = re.search(r'^(.+?)\s+tratto compreso tra (.+?)$', spec)
        if tratto_match:
            primary = tratto_match.group(1).strip()
            endpoints = [ep.strip() for ep in tratto_match.group(2).split(' e ')]
            return {
                'type': 'tratto',
                'primary': primary,
                'endpoints': endpoints,
                'places': [primary] + endpoints
            }
        
        # Intersection pattern
        incrocio_match = re.search(r'^(.+?)\s+incrocio con (.+?)$', spec)
        if incrocio_match:
            primary = incrocio_match.group(1).strip()
            intersecting = incrocio_match.group(2).strip()
            return {
                'type': 'incrocio',
                'primary': primary,
                'intersecting': intersecting,
                'places': [primary, intersecting]
            }
        
        # Simple place
        return {
            'type': 'simple',
            'primary': spec,
            'places': [spec]
        }
    
    def get_place_data(self, place_name: str, city_config: Optional[CityConfig] = None) -> Optional[Dict]:
        """Get place data from catalog with city prefix handling"""
        
        # FORCED DEBUG for civics
        if 'civico' in place_name:
            print(f"🔍 LOOKING UP: {place_name}")
        
        # Try direct lookup first
        if place_name in self.places_catalog:
            if 'civico' in place_name:
                print(f"✅ FOUND DIRECT: {place_name}")
            return self.places_catalog[place_name]
            
        # If we have city config, try with city prefix
        if city_config and city_config.city_name in CITY_PREFIXES:
            city_prefix = CITY_PREFIXES[city_config.city_name]
            prefixed_name = f"{city_prefix}_{place_name}"
            if prefixed_name in self.places_catalog:
                return self.places_catalog[prefixed_name]
        
        # Try all city prefixes as fallback
        for prefix in CITY_PREFIXES.values():
            prefixed_name = f"{prefix}_{place_name}"
            if prefixed_name in self.places_catalog:
                return self.places_catalog[prefixed_name]
        
        return None
    
    def process_specification(self, specification: str, zone_name: str, ord_id: str, city_config: Optional[CityConfig] = None) -> Dict:
        """Process a single specification and return visualization data with zone filtering"""
        
        # FORCED DEBUG - this should ALWAYS print
        # print(f"🔍 PROCESSING: {specification}")
        if 'Tuscolana' in specification:
            print(f"🏠 *** TUSCOLANA FOUND: {specification} ***")
        
        parsed = self.parse_specification(specification)
        spec_type = parsed['type']
        
        # print(f"    Type: {spec_type}")
        if 'Tuscolana' in specification:
            print(f"    Parsed: {parsed}")   

        # Get zone bbox for filtering
        zone_bbox = None
        if city_config:
            if zone_name.startswith('no_'):
                zone_bbox = (0,0,0,0)
            else:
                zone_bbox = get_zone_bbox(city_config, zone_name)
            if not zone_bbox:
                print(f"⚠️ No bbox found for zone: {zone_name} in {city_config.city_name}")
        
        result = {
            'specification': specification,
            'type': spec_type,
            'geometries': [],
            'special_coordinates': [],
            'metadata': {
                'zone': zone_name,
                'ordinance': ord_id,
                'places_found': [],
                'places_missing': [],
                'zone_bbox': zone_bbox,
                'bbox_filtered': zone_bbox is not None,
                'city': city_config.city_name if city_config else 'Unknown'
            }
        }
        
        # Get place data for all referenced places
        place_data = {}
        for place_name in parsed['places']:
            data = self.get_place_data(place_name, city_config)
            if data:
                place_data[place_name] = data
                result['metadata']['places_found'].append(place_name)
            else:
                result['metadata']['places_missing'].append(place_name)
        
        # Process based on specification type
        if spec_type == 'simple':
            # Simple place - just show the place
            primary_data = place_data.get(parsed['primary'])
            if primary_data:
                # Filter geometries and special coordinates by zone bbox
                if zone_bbox:
                    result['geometries'] = filter_geometries_by_bbox(primary_data.get('geometries', []), zone_bbox)
                    result['special_coordinates'] = filter_special_coordinates_by_bbox(primary_data.get('special_coordinates', []), zone_bbox)
                else:
                    result['geometries'] = primary_data.get('geometries', [])
                    result['special_coordinates'] = primary_data.get('special_coordinates', [])
        
        elif spec_type == 'civico':
            # Civic number - show civic point if available, otherwise street
            civic_place = f"{parsed['primary']} civico {parsed['civic_number']}"
            civic_data = place_data.get(civic_place)
            
            if civic_data:
                # FIXED: Check both special_coordinates AND geometries for Point data
                civic_points = []
                
                # Method 1: Check special_coordinates (existing logic)
                for special in civic_data.get('special_coordinates', []):
                    if special.get('type') == 'Point':
                        civic_points.append(special)
                
                # Method 2: Check geometries for Point type (MISSING - this was the bug!)
                for geom in civic_data.get('geometries', []):
                    if geom.get('type') == 'Point':
                        # Convert geometry to special_coordinates format
                        civic_points.append({
                            'type': 'Point',
                            'coordinates': geom.get('coordinates', [])
                        })
                
                # Apply zone filtering to all found civic points
                if zone_bbox and civic_points:
                    result['special_coordinates'] = filter_special_coordinates_by_bbox(civic_points, zone_bbox)
                else:
                    result['special_coordinates'] = civic_points
                    
                result['metadata']['display_mode'] = 'civic_only'

        elif spec_type == 'incrocio':
            # Intersection - calculate intersection point with zone filtering
            primary_data = place_data.get(parsed['primary'])
            intersecting_data = place_data.get(parsed['intersecting'])
            
            if primary_data and intersecting_data:
                intersection_point = find_intersection_point(primary_data, intersecting_data, zone_bbox=zone_bbox)
                if intersection_point:
                    result['special_coordinates'] = [{
                        'type': 'Point',
                        'coordinates': [intersection_point[0], intersection_point[1]],
                        'calculated_intersection': True,
                        'bbox_filtered': zone_bbox is not None
                    }]
                    result['metadata']['display_mode'] = 'intersection_only'
                    result['metadata']['intersection_calculated'] = True
                else:
                    # Fallback: show both streets with zone filtering
                    if zone_bbox:
                        result['geometries'].extend(filter_geometries_by_bbox(primary_data.get('geometries', []), zone_bbox))
                        result['geometries'].extend(filter_geometries_by_bbox(intersecting_data.get('geometries', []), zone_bbox))
                    else:
                        result['geometries'].extend(primary_data.get('geometries', []))
                        result['geometries'].extend(intersecting_data.get('geometries', []))
            else:
                # Show available places with zone filtering
                for data in place_data.values():
                    if zone_bbox:
                        result['geometries'].extend(filter_geometries_by_bbox(data.get('geometries', []), zone_bbox))
                    else:
                        result['geometries'].extend(data.get('geometries', []))
        
        elif spec_type == 'tratto':
            # Tract - compute segment between endpoints with zone filtering
            primary_data = place_data.get(parsed['primary'])
            endpoint1_data = place_data.get(parsed['endpoints'][0]) if len(parsed['endpoints']) > 0 else None
            endpoint2_data = place_data.get(parsed['endpoints'][1]) if len(parsed['endpoints']) > 1 else None
            
            if primary_data and endpoint1_data and endpoint2_data:
                tract_geometries = compute_tract_segment(primary_data, endpoint1_data, endpoint2_data, zone_bbox=zone_bbox)
                result['geometries'] = tract_geometries
                result['metadata']['display_mode'] = 'tract_only'
                result['metadata']['tract_calculated'] = True
            else:
                # Fallback: show available places with zone filtering
                for data in place_data.values():
                    if zone_bbox:
                        result['geometries'].extend(filter_geometries_by_bbox(data.get('geometries', []), zone_bbox))
                    else:
                        result['geometries'].extend(data.get('geometries', []))
        
        return result
    
    def process_all_ordinances(self) -> Dict:
        """Process all ordinances and generate complete coordinates data with automatic city detection"""
        coordinates_data = {}
        
        stats = {
            'total_specifications': 0,
            'simple': 0, 'civico': 0, 'incrocio': 0, 'tratto': 0,
            'intersections_calculated': 0,
            'tracts_calculated': 0,
            'missing_places': 0,
            'bbox_filtered_specs': 0,
            'zones_with_bbox': 0,
            'zones_without_bbox': 0,
            'cities_detected': {},
            'ordinances_no_city': 0,
            'places_found_with_prefix': 0,
            'places_found_without_prefix': 0
        }
        
        for ord_id, ord_data in self.ordinances.items():
            # Detect city for this ordinance
            city_config = self.detect_city_from_ordinance(ord_id, ord_data)
            
            if city_config:
                print(f"🌍 Detected city for ordinance {ord_id}: {city_config.city_name}")
                if city_config.city_name not in stats['cities_detected']:
                    stats['cities_detected'][city_config.city_name] = 0
                stats['cities_detected'][city_config.city_name] += 1
            else:
                print(f"❓ Could not detect city for ordinance {ord_id}")
                stats['ordinances_no_city'] += 1
            
            coordinates_data[ord_id] = {
                'metadata': {
                    'protocol': ord_data.get('protocol', ord_id),
                    'date': ord_data.get('date', ''),
                    'title': ord_data.get('title', ''),
                    'city': city_config.city_name if city_config else 'Unknown',
                    'city_code': next((code for code, config in CITIES.items() if config == city_config), None) if city_config else None
                },
                'zones': {}
            }
            
            for zone_name, specifications in ord_data.get('zones', {}).items():
                coordinates_data[ord_id]['zones'][zone_name] = {}
                
                # Check if zone has bbox with current city config
                has_bbox = city_config and get_zone_bbox(city_config, zone_name) is not None
                if has_bbox:
                    stats['zones_with_bbox'] += 1
                else:
                    stats['zones_without_bbox'] += 1
                
                for specification in specifications:
                    stats['total_specifications'] += 1
                    
                    # ADD THIS DEBUG
                    if 'Tuscolana' in specification:
                        print(f"🚨 ABOUT TO PROCESS TUSCOLANA: '{specification}'")
                    
                    result = self.process_specification(specification, zone_name, ord_id, city_config)
                    
                    # ADD THIS DEBUG TOO
                    if 'Tuscolana' in specification:
                        print(f"🚨 TUSCOLANA RESULT: {result}")
                    
                    coordinates_data[ord_id]['zones'][zone_name][specification] = result
                    
                    # Update stats
                    spec_type = result['type']
                    stats[spec_type] += 1
                    
                    if result['metadata'].get('intersection_calculated'):
                        stats['intersections_calculated'] += 1
                    if result['metadata'].get('tract_calculated'):
                        stats['tracts_calculated'] += 1
                    if result['metadata'].get('places_missing'):
                        stats['missing_places'] += len(result['metadata']['places_missing'])
                    if result['metadata'].get('bbox_filtered'):
                        stats['bbox_filtered_specs'] += 1
                    
                    # Track place finding success with/without prefix
                    if result['metadata'].get('places_found'):
                        stats['places_found_with_prefix'] += len(result['metadata']['places_found'])
        
        print(f"\n📊 Processing Statistics:")
        print(f"   📍 Total specifications: {stats['total_specifications']}")
        print(f"   🏷️ Types: {stats['simple']} simple, {stats['civico']} civic, {stats['incrocio']} intersections, {stats['tratto']} tracts")
        print(f"   ✅ Calculated: {stats['intersections_calculated']} intersections, {stats['tracts_calculated']} tracts")
        print(f"   ⚠️ Missing places: {stats['missing_places']}")
        print(f"   🔍 Places found: {stats['places_found_with_prefix']}")
        print(f"   🎯 Zone filtering: {stats['bbox_filtered_specs']} specifications filtered")
        print(f"   📦 Zones: {stats['zones_with_bbox']} with bbox, {stats['zones_without_bbox']} without bbox")
        print(f"   🌍 Cities detected: {dict(stats['cities_detected'])}")
        print(f"   ❓ Ordinances without city detection: {stats['ordinances_no_city']}")
        
        return coordinates_data

    
    def embed_into_html(self, html_file: str = "rome_viewer_osm.html", output_file: str = "rome_viewer_embedded.html"):
        """Embed processed coordinates into HTML viewer"""
        print(f"🚨 EMBEDDING STARTED!")
        print(f"🌐 Embedding into HTML viewer...")
        
        # Check if our civic exists in ordinances
        found_tuscolana = False
        for ord_id, ord_data in self.ordinances.items():
            for zone_name, specifications in ord_data.get('zones', {}).items():
                for spec in specifications:
                    if 'Tuscolana' in spec and 'civico' in spec:
                        print(f"🏠 FOUND TUSCOLANA SPEC: '{spec}' in {ord_id}/{zone_name}")
                        found_tuscolana = True
        
        if not found_tuscolana:
            print(f"❌ TUSCOLANA CIVIC NOT FOUND IN ORDINANCES!")  

        print(f"🔍 About to call process_all_ordinances()...")
        coordinates_data = self.process_all_ordinances()
        print(f"🔍 process_all_ordinances() completed!")
        print(f"📊 Coordinates data keys: {list(coordinates_data.keys())}")


        # Process all ordinances
        coordinates_data = self.process_all_ordinances()

        if 'RM_ordinance_6747' in coordinates_data:
            tuscolano_zone = coordinates_data['RM_ordinance_6747'].get('zones', {}).get('Zona Tuscolano', {})
            print(f"🏠 Zona Tuscolano has {len(tuscolano_zone)} specifications")
            for spec_name in tuscolano_zone.keys():
                if 'Tuscolana' in spec_name:
                    print(f"🎯 Found: {spec_name}")
                    print(f"    Data: {tuscolano_zone[spec_name]}")


        # Load HTML template
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except FileNotFoundError:
            print(f"❌ HTML template not found: {html_file}")
            return
        
        # Convert to JavaScript
        js_data = json.dumps(coordinates_data, indent=4)
        embedded_line = f"        coordinatesData = {js_data};"
        
        # Replace fetch pattern
        fetch_patterns = [
            "coordinatesData = await fetch('./coordinates.json').then(response => response.json());",
            "coordinatesData = await fetch('./coordinates_backup.json').then(response => response.json());",
            "        coordinatesData = await fetch('./coordinates.json').then(response => response.json());"
        ]
        
        replaced = False
        for pattern in fetch_patterns:
            if pattern in html_content:
                html_content = html_content.replace(pattern, embedded_line)
                replaced = True
                break
        
        if not replaced:
            # Try to find any fetch pattern and replace
            import re
            fetch_pattern = re.search(r'coordinatesData = await fetch\([^)]+\)[^;]+;', html_content)
            if fetch_pattern:
                html_content = html_content.replace(fetch_pattern.group(0), embedded_line)
                replaced = True
        
        if not replaced:
            print("❌ Could not find coordinates loading pattern in HTML")
            return
        
        # Save embedded HTML
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Created {output_file}")
        print(f"🎯 Ready to view: open {output_file} in your browser")
        print(f"🌍 Automatic city detection and zone filtering applied")
    
    def save_coordinates(self, output_file: str = "coordinates_processed.json"):
        """Save processed coordinates to JSON file"""
        coordinates_data = self.process_all_ordinances()
                
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(coordinates_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Saved processed coordinates to {output_file}")
        print(f"🌍 Automatic city detection and zone filtering applied")

def main():
    """Main function"""
    print("🏛️ FIXED CITY DETECTION EMBEDDER")
    print("=" * 50)
    
    # Initialize embedder (no city specification needed)
    embedder = PlacesEmbedder(
        places_file="coordinates.json",
        ordinances_file="ordinanze.json"
    )
    
    # Choose operation
    print("\nChoose operation:")
    print("1. Generate HTML viewer")
    print("2. Save processed coordinates JSON")
    print("3. Both")
    
    choice = input("Enter choice (1/2/3): ").strip()
    
    if choice in ['1', '3']:
        embedder.embed_into_html()
    
    if choice in ['2', '3']:
        embedder.save_coordinates()
    
    print(f"\n🎉 Complete!")

if __name__ == "__main__":
    main()