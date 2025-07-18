import json
import requests
import time
import re
import os
from typing import Dict, List, Tuple, Set, Optional

from city_configs import CITIES, CITY_PREFIXES, CityConfig


def get_zone_bbox(city_config: CityConfig, zone_name: str) -> Optional[Tuple[float, float, float, float]]:
    """Get bounding box for a zone, handling zone mappings"""
    if zone_name.startswith('no_'):
        return (0, 0, 0, 0)
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

def union_bboxes(bboxes: List[Tuple[float, float, float, float]]) -> Tuple[float, float, float, float]:
    """Create union of multiple bounding boxes"""
    if not bboxes:
        return (0, 0, 0, 0)
    
    min_south = min(bbox[0] for bbox in bboxes)
    min_west = min(bbox[1] for bbox in bboxes)
    max_north = max(bbox[2] for bbox in bboxes)
    max_east = max(bbox[3] for bbox in bboxes)
    
    return (min_south, min_west, max_north, max_east)

class CoordinatesFetcher:
    def __init__(self, cache_file="coordinates.json"):
        self.cache_file = cache_file
        self.cache = self._load_cache()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "CoordinatesFetcher/2.0"})
        self.stats = {'fetched': 0, 'cached': 0, 'failed': 0, 'filtered': 0, 'zone_filtered': 0}

    def _load_cache(self) -> Dict:
        """Load existing coordinates cache"""
        cache = {}
        
        # Load from cache file (coordinates.json or other cache file)
        cache_files = ["coordinates.json", self.cache_file]
        
        for cache_file in cache_files:
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        file_cache = json.load(f)
                    
                    # Check if this looks like cache data (has city prefixes)
                    is_cache_format = True
                    if file_cache:
                        sample_keys = list(file_cache.keys())[:5]  # Check first 5 keys
                        for key in sample_keys:
                            # Check if key has city prefix and proper structure
                            has_city_prefix = any(key.startswith(city + '_') for city in CITIES.keys())
                            if has_city_prefix and isinstance(file_cache[key], dict) and 'geometries' in file_cache[key]:
                                continue  # This looks like cache format
                            else:
                                is_cache_format = False
                                break
                    
                    if is_cache_format:
                        # Merge with existing cache (later files take precedence)
                        cache.update(file_cache)
                        print(f"📦 Loaded {len(file_cache)} places from {cache_file}")
                    else:
                        print(f"📦 Ignoring unrecognized format in {cache_file}")
                        
                except Exception as e:
                    print(f"📦 Error loading {cache_file}: {e}")
        
        if not cache:
            print("📦 Starting fresh cache")
        else:
            print(f"📦 Total cache entries: {len(cache)}")
        
        return cache

    def _save_cache(self):
        """Save coordinates cache"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def _detect_city(self, ord_id: str) -> Optional[str]:
        """Detect city from ordinance ID"""
        for prefix in CITIES.keys():
            if prefix in ord_id.upper():
                return prefix
        return None

    def extract_elements(self, specification: str) -> Set[str]:
        """Extract all atomic elements from specification"""
        elements = set()
        
        # 1. TRACT: "A tratto compreso tra B e C" -> extract A, B, C separately
        tract_match = re.search(r'^(.+?)\s+tratto compreso tra\s+(.+?)\s+e\s+(.+?)$', specification, re.IGNORECASE)
        if tract_match:
            # Main street
            primary = tract_match.group(1).strip()
            elements.add(primary)
            
            # First endpoint
            endpoint1 = tract_match.group(2).strip()
            # Check if it's a civic address reference in parentheses
            civic_match1 = re.search(r'^(.+?)\s*\(fronte civico (\d+)\)$', endpoint1)
            if civic_match1:
                street = civic_match1.group(1).strip()
                civic_num = civic_match1.group(2)
                elements.add(street)  # Add the street itself
                elements.add(f"{street} civico {civic_num}")  # Add the civic address
            else:
                # Check if endpoint1 is already a civic address
                civic_direct1 = re.search(r'^(.+?)\s+civico\s+(\d+)$', endpoint1)
                if civic_direct1:
                    street = civic_direct1.group(1).strip()
                    elements.add(street)  # Add the street itself
                    elements.add(endpoint1)  # Add the full civic address
                else:
                    elements.add(endpoint1)
            
            # Second endpoint
            endpoint2 = tract_match.group(3).strip()
            # Check if it's a civic address reference in parentheses
            civic_match2 = re.search(r'^(.+?)\s*\(fronte civico (\d+)\)$', endpoint2)
            if civic_match2:
                street = civic_match2.group(1).strip()
                civic_num = civic_match2.group(2)
                elements.add(street)
                elements.add(f"{street} civico {civic_num}")
            else:
                # Check if it's already a civic address
                civic_direct2 = re.search(r'^(.+?)\s+civico\s+(\d+)$', endpoint2)
                if civic_direct2:
                    street = civic_direct2.group(1).strip()
                    elements.add(street)  # Add the street itself
                    elements.add(endpoint2)  # Add the full civic address
                else:
                    elements.add(endpoint2)
            
            return elements

        # 2. INTERSECTION: "A incrocio con B" -> extract A and B separately
        intersection_patterns = [
            r'^(.+?)\s+incrocio con\s+(.+?)$',
            r'^incrocio tra\s+(.+?)\s+e\s+(.+?)$',
            r'^(.+?)\s+sino all\'incrocio con\s+(.+?)$',
            r'^(.+?)\s+all\'incrocio con\s+(.+?)$',
            r'^(.+?)\s+angolo\s+(.+?)$',  # Also handle "angolo" (corner)
            r'^(.+?)\s+incrocio\s+(.+?)$'  # Handle simple "incrocio" without "con"
        ]
        
        for pattern in intersection_patterns:
            match = re.search(pattern, specification, re.IGNORECASE)
            if match:
                # First street/place
                place1 = match.group(1).strip()
                # Check if place1 has civic in parentheses
                civic_in_place1 = re.search(r'^(.+?)\s*\(fronte civico (\d+)\)$', place1)
                if civic_in_place1:
                    street = civic_in_place1.group(1).strip()
                    civic_num = civic_in_place1.group(2)
                    elements.add(street)
                    elements.add(f"{street} civico {civic_num}")
                else:
                    elements.add(place1)
                
                # Second street/place  
                place2 = match.group(2).strip()
                # Check if place2 has civic in parentheses
                civic_in_place2 = re.search(r'^(.+?)\s*\(fronte civico (\d+)\)$', place2)
                if civic_in_place2:
                    street = civic_in_place2.group(1).strip()
                    civic_num = civic_in_place2.group(2)
                    elements.add(street)
                    elements.add(f"{street} civico {civic_num}")
                else:
                    elements.add(place2)
                
                # IMPORTANT: Do NOT add the full specification!
                # We only want the atomic elements
                return elements

        # 3. CIVIC ADDRESS: "Via X (fronte civico 123)" -> extract "Via X" and "Via X civico 123"
        civico_match = re.search(r'^(.+?)\s*\(fronte civico (\d+)\)$', specification)
        if civico_match:
            street = civico_match.group(1).strip()
            civic_num = civico_match.group(2)
            elements.add(street)
            elements.add(f"{street} civico {civic_num}")
            return elements
        
        # 3b. Direct civic address: "Via X civico 123" -> extract "Via X" and keep full address
        direct_civico_match = re.search(r'^(.+?)\s+civico\s+(\d+)$', specification)
        if direct_civico_match:
            street = direct_civico_match.group(1).strip()
            elements.add(street)  # Add just the street
            elements.add(specification.strip())  # Add the full civic address
            return elements

        # 4. SIMPLE ELEMENT: just add as-is
        # This is only reached if none of the above patterns match
        elements.add(specification.strip())
        return elements

    def _generate_variants(self, name: str, city: CityConfig) -> List[str]:
        """Generate search variants for a place name"""
        variants = [name]
        
        # First, extract base name by removing common prefixes
        prefixes = ["Via ", "Viale ", "Piazza ", "Piazzale ", "Corso ", "Largo "]
        base_name = name
        original_prefix = ""
        
        for prefix in prefixes:
            if name.startswith(prefix):
                base_name = name[len(prefix):].strip()
                original_prefix = prefix
                break
        
        # Add base name without prefix
        if base_name != name:
            variants.append(base_name)
        
        # 1. Apply special cases from city config using the base name
        base_name_lower = base_name.lower()
        
        for pattern, replacements in city.special_cases.items():
            pattern_lower = pattern.lower()
            
            # Check if the base name matches the pattern (case insensitive)
            if base_name_lower == pattern_lower or pattern_lower in base_name_lower:
                if replacements == []:  # Empty list = skip entirely
                    return []
                elif replacements == "":  # Empty string = remove pattern
                    continue
                elif isinstance(replacements, list):  # List = add variants
                    for replacement in replacements:
                        variants.append(replacement)
                        # Also try with original prefix if it had one
                        if original_prefix:
                            variants.append(f"{original_prefix}{replacement}")
        
        # 2. Check for partial word matches in base name
        words = base_name_lower.split()
        for pattern, replacements in city.special_cases.items():
            pattern_lower = pattern.lower()
            pattern_words = pattern_lower.split()
            
            # Check if pattern words are a subsequence of base name words
            if len(pattern_words) <= len(words):
                for i in range(len(words) - len(pattern_words) + 1):
                    if words[i:i+len(pattern_words)] == pattern_words:
                        if isinstance(replacements, list):
                            for replacement in replacements:
                                # Replace the matched words with replacement
                                new_words = words[:i] + [replacement] + words[i+len(pattern_words):]
                                variant = " ".join(new_words)
                                variants.append(variant)
                                if original_prefix:
                                    variants.append(f"{original_prefix}{variant}")
                
        # Remove duplicates and empty strings, preserve order
        seen = set()
        final_variants = []
        for v in variants:
            v_clean = v.strip()
            if v_clean and v_clean.lower() not in seen:
                seen.add(v_clean.lower())
                final_variants.append(v_clean)

        return final_variants

    def _parse_element(self, element: str) -> Set[str]:
        """Parse single element - handle civic addresses"""
        elements = set()
        
        # Civic: "Via X (fronte civico 123)" -> ["Via X", "Via X civico 123"]
        civico_match = re.search(r'^(.+?)\s*\(fronte civico (\d+)\)$', element)
        if civico_match:
            street = civico_match.group(1).strip()
            civic_num = civico_match.group(2)
            elements.add(street)
            elements.add(f"{street} civico {civic_num}")
        else:
            elements.add(element.strip())
        
        return elements

    def _is_inside_bbox(self, coord: List[float], bbox: Tuple[float, float, float, float]) -> bool:
        """Check if coordinate is inside bounding box"""
        if len(coord) < 2:
            return False
        lat, lon = coord[0], coord[1]
        south, west, north, east = bbox
        return south <= lat <= north and west <= lon <= east

    def _filter_geometries(self, geometries: List[Dict], target_bbox: Tuple[float, float, float, float], filter_type: str = "zone") -> Tuple[List[Dict], int]:
        """Filter geometries to keep only coordinates inside bbox"""
        filtered = []
        filtered_count = 0
        
        for geom in geometries:
            coords = geom.get('coordinates', [])
            geom_type = geom.get('type')
            
            if geom_type == 'Point':
                if self._is_inside_bbox(coords, target_bbox):
                    filtered.append(geom)
                else:
                    filtered_count += 1
                    
            elif geom_type == 'LineString':
                valid_coords = [c for c in coords if self._is_inside_bbox(c, target_bbox)]
                if valid_coords:
                    new_geom = dict(geom)
                    new_geom['coordinates'] = valid_coords
                    filtered.append(new_geom)
                filtered_count += len(coords) - len(valid_coords)
                
            elif geom_type == 'Polygon':
                outer_ring = coords[0] if coords else []
                valid_coords = [c for c in outer_ring if self._is_inside_bbox(c, target_bbox)]
                if valid_coords and len(valid_coords) >= 3:
                    # Ensure closed polygon
                    if valid_coords[0] != valid_coords[-1]:
                        valid_coords.append(valid_coords[0])
                    new_geom = dict(geom)
                    new_geom['coordinates'] = [valid_coords]
                    filtered.append(new_geom)
                filtered_count += len(outer_ring) - len(valid_coords)
        
        if filter_type == "zone":
            self.stats['zone_filtered'] += filtered_count
        else:
            self.stats['filtered'] += filtered_count
        
        return filtered, filtered_count

    def _search_nominatim(self, query: str, city: CityConfig) -> List[str]:
        """Search place in Nominatim API"""
        south, west, north, east = city.default_bbox
        params = {
            'q': f"{query}, {city.city_pattern}, Italy",
            'format': 'json',
            'viewbox': f"{west},{north},{east},{south}",
            'bounded': 1,
            'limit': 5,
            'countrycodes': 'it'
        }
        
        try:
            response = self.session.get(
                "https://nominatim.openstreetmap.org/search", 
                params=params, timeout=30
            )
            time.sleep(1.2)  # Rate limiting
            
            if response.status_code == 200:
                results = []
                for result in response.json():
                    # Accept ways, nodes, and marketplaces
                    if (((result['osm_type'] in ['way', 'node'] and 
                          result.get('class') in ['highway', 'leisure', 'amenity']) or
                         (result['osm_type'] in ['way', 'node'] and 
                          result.get('type') == 'marketplace')) and
                        city.city_pattern in result.get('display_name', '')):
                        results.append(result['osm_id'])
                return results
        except Exception:
            pass
        return []

    def _get_geometry(self, osm_id: str, city: CityConfig, original_place_name: str = None) -> List[Dict]:
        """Get geometry from Overpass API"""
        try:
            # Get element info
            query1 = f"[out:json]; (way({osm_id}); node({osm_id});); out tags;"
            response = self.session.post(
                "http://overpass-api.de/api/interpreter", 
                data=query1, timeout=30
            )
            time.sleep(1.0)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            if not data.get('elements'):
                return []
            
            element = data['elements'][0]
            tags = element.get('tags', {})
            
            # Handle nodes (points) - including marketplaces
            if element.get('type') == 'node':
                lat, lon = element.get('lat'), element.get('lon')
                if lat and lon:
                    return [{'type': 'Point', 'coordinates': [lat, lon]}]
            
            # Handle ways - get all segments with same name OR marketplace amenity
            name = tags.get('name', '')
            amenity = tags.get('amenity', '')
            
            if not name and amenity != 'marketplace':
                return []
            
            south, west, north, east = city.default_bbox
            
            # Search by name if available
            if name:
                escaped_name = name.replace('"', '\\"')
                
                # SMART QUERY: Prioritize proper square/plaza tags
                if 'piazza' in name.lower() or (original_place_name and 'piazza' in original_place_name.lower()):
                    # For squares/piazzas, prioritize proper landuse/leisure tags
                    smart_query = f'''[out:json][timeout:30];
                    (
                    // Priority 1: Proper square/plaza areas
                    way[name="{escaped_name}"][leisure~"^(plaza|square)$"]({south},{west},{north},{east});
                    way[name="{escaped_name}"][place~"^(square|plaza)$"]({south},{west},{north},{east});
                    way[name="{escaped_name}"][landuse="retail"][area="yes"]({south},{west},{north},{east});
                    
                    // Priority 2: Large closed ways (likely main boundaries)
                    way[name="{escaped_name}"]["area"="yes"]({south},{west},{north},{east});
                    
                    // Priority 3: Relations containing the square
                    rel[name="{escaped_name}"]["type"="multipolygon"]({south},{west},{north},{east});
                    
                    // Priority 4: Fallback - but exclude small/platform stuff
                    way[name="{escaped_name}"][!"railway"][!"public_transport"]({south},{west},{north},{east});
                    );
                    out geom;'''
                else:
                    # For streets, use existing logic
                    smart_query = f'[out:json]; way[name="{escaped_name}"]({south},{west},{north},{east}); out geom;'
                
                response = self.session.post(
                    "http://overpass-api.de/api/interpreter", 
                    data=smart_query, timeout=30
                )
                time.sleep(1.0)
                
                if response.status_code != 200:
                    return []
                
                elements = response.json().get('elements', [])
                
                # POST-PROCESS: Filter out tiny fragments for squares
                if 'piazza' in name.lower() or (original_place_name and 'piazza' in original_place_name.lower()):
                    elements = self._filter_square_elements(elements)
                                
            # If exact match failed and we have a name, try case-insensitive regex
            if not elements and name:
                # Use original place name if provided, otherwise fall back to OSM element name
                search_name = original_place_name if original_place_name else name
                
                # Clean the search name and extract key words
                clean_name = search_name.strip()
                words = clean_name.replace("Via ", "").replace("Viale ", "").replace("Piazza ", "").replace("Corso ", "").strip().split()
                
                if words:
                    # Try with last word (most specific)
                    last_word = words[-1].strip()
                    key_word = ''.join(c for c in last_word if c.isalpha()).lower()
                    
                    if len(key_word) >= 3:
                        query3 = f'[out:json]; way[name~"{key_word}",i]({south},{west},{north},{east}); out geom;'
                        
                        print(f"         🔍 Trying regex search with cleaned key: '{key_word}' (from '{search_name}')")

            for elem in elements:
                if elem.get('type') == 'node':
                    lat, lon = elem.get('lat'), elem.get('lon')
                    if lat and lon:
                        geometries.append({'type': 'Point', 'coordinates': [lat, lon]})
                elif 'geometry' in elem and elem['geometry']:
                    coords = [[p['lat'], p['lon']] for p in elem['geometry']]
                    if len(coords) > 1:
                        # Check if closed (polygon)
                        is_closed = (len(coords) > 3 and 
                                abs(coords[0][0] - coords[-1][0]) < 0.00001 and 
                                abs(coords[0][1] - coords[-1][1]) < 0.00001)
                        
                        elem_tags = elem.get('tags', {})
                        if (is_closed or 'piazza' in name.lower() or 
                            elem_tags.get('amenity') == 'marketplace'):
                            if not is_closed:
                                coords.append(coords[0])
                            geometries.append({'type': 'Polygon', 'coordinates': [coords]})
                        else:
                            geometries.append({'type': 'LineString', 'coordinates': coords})
            
            return geometries
            
        except Exception as e:
            print(f"         ❌ Exception in _get_geometry: {e}")
            return []
        
    
    def _filter_square_elements(self, elements):
        """Filter out tiny fragments and platform pieces for squares"""
        if len(elements) <= 5:
            return elements  # Keep all if not too many
        
        # Calculate areas and filter out tiny pieces
        element_data = []
        for elem in elements:
            if 'geometry' in elem and elem['geometry']:
                coords = elem['geometry']
                if len(coords) > 2:
                    # Calculate bounding box area
                    lats = [p['lat'] for p in coords]
                    lons = [p['lon'] for p in coords]
                    area = (max(lats) - min(lats)) * (max(lons) - min(lons))
                    
                    # Skip tiny fragments (< 0.00001 degrees²)
                    if area > 0.00001:
                        element_data.append((elem, area))
        
        # Sort by area and keep largest 10
        element_data.sort(key=lambda x: x[1], reverse=True)
        filtered = [elem for elem, area in element_data[:10]]
        
        print(f"         🔧 Square filtering: {len(elements)} → {len(filtered)} elements")
        return filtered

    def _search_overpass_direct(self, place_name: str, city: CityConfig, zone_bboxes: List[Tuple[float, float, float, float]]) -> List[Dict]:
        """Direct Overpass search as fallback when Nominatim fails"""
        south, west, north, east = city.default_bbox
        
        # Apply special cases from city config first
        search_terms = []
        place_lower = place_name.lower()
        
        # Check special cases
        for pattern, replacements in city.special_cases.items():
            if pattern.lower() in place_lower:
                if isinstance(replacements, list) and replacements:
                    for replacement in replacements:
                        clean_replacement = replacement.replace("Via ", "").replace("Piazza ", "").replace("Viale ", "").replace("Corso ", "").strip()
                        if len(clean_replacement) >= 3:
                            search_terms.append(clean_replacement.lower())
                    break
        
        # If no special cases found, use original logic
        if not search_terms:
            clean_name = place_name
            for prefix in ["Via ", "Viale ", "Piazza ", "Piazzale ", "Corso ", "Largo "]:
                clean_name = clean_name.replace(prefix, "")
            
            if "(" in clean_name:
                clean_name = clean_name.split("(")[0]
            
            words = clean_name.split()
            
            # Strategy 1: Last significant word
            for word in reversed(words):
                clean_word = ''.join(c for c in word if c.isalpha()).lower()
                if len(clean_word) >= 3:
                    search_terms.append(clean_word)
                    break
            
            # Strategy 2: First significant word if different
            for word in words:
                clean_word = ''.join(c for c in word if c.isalpha()).lower()
                if len(clean_word) >= 3 and clean_word not in search_terms:
                    search_terms.append(clean_word)
                    break
        
        print(f"         🔍 Direct search terms: {search_terms}")
        
        for term in search_terms:
            # Create multiple search variants for character encoding issues
            search_variants = [term]
            
            # Add variants with different accent handling
            if 'à' in term:
                search_variants.append(term.replace('à', 'a'))
            if 'è' in term:
                search_variants.append(term.replace('è', 'e'))
            if 'é' in term:
                search_variants.append(term.replace('é', 'e'))
            if 'ì' in term:
                search_variants.append(term.replace('ì', 'i'))
            if 'ò' in term:
                search_variants.append(term.replace('ò', 'o'))
            if 'ù' in term:
                search_variants.append(term.replace('ù', 'u'))
        
            # Try each search variant
            for search_term in search_variants:
                try:
                    query = f'[out:json]; way[name~"{search_term}",i]({south},{west},{north},{east}); out geom;'
                    
                    response = self.session.post(
                        "http://overpass-api.de/api/interpreter", 
                        data=query, timeout=30
                    )
                    time.sleep(1.0)
                    
                    if response.status_code == 200:
                        elements = response.json().get('elements', [])
                        if search_term != term:
                            print(f"         📍 Search with accent variant '{search_term}' found {len(elements)} results")
                        else:
                            print(f"         📍 Direct search with '{search_term}' found {len(elements)} results")
                        
                        if elements:
                            geometries = []
                            for elem in elements:
                                if elem.get('type') == 'node':
                                    lat, lon = elem.get('lat'), elem.get('lon')
                                    if lat and lon:
                                        geometries.append({'type': 'Point', 'coordinates': [lat, lon]})
                                elif 'geometry' in elem and elem['geometry']:
                                    coords = [[p['lat'], p['lon']] for p in elem['geometry']]
                                    if len(coords) > 1:
                                        is_closed = (len(coords) > 3 and 
                                                abs(coords[0][0] - coords[-1][0]) < 0.00001 and 
                                                abs(coords[0][1] - coords[-1][1]) < 0.00001)
                                        
                                        elem_tags = elem.get('tags', {})
                                        elem_name = elem_tags.get('name', '').lower()
                                        
                                        if (is_closed or 'piazza' in elem_name or 
                                            elem_tags.get('amenity') == 'marketplace'):
                                            if not is_closed:
                                                coords.append(coords[0])
                                            geometries.append({'type': 'Polygon', 'coordinates': [coords]})
                                        else:
                                            geometries.append({'type': 'LineString', 'coordinates': coords})
                            
                            if geometries:
                                # Apply zone filtering if needed
                                if zone_bboxes:
                                    union_bbox = union_bboxes(zone_bboxes)
                                    filtered_geoms, _ = self._filter_geometries(geometries, union_bbox, "zone")
                                    if filtered_geoms:  # Only return if we have results after filtering
                                        return filtered_geoms
                                else:
                                    return geometries
                                    
                except Exception as e:
                    print(f"         ❌ Error in direct search with '{search_term}': {e}")
                    continue
        
        return []


    def _fetch_civic(self, cache_key: str, street: str, civic_num: str, city: CityConfig, zone_bboxes: List[Tuple[float, float, float, float]]) -> bool:
        """Fetch civic address coordinates with zone filtering"""
        south, west, north, east = city.default_bbox
        variants = self._generate_variants(street, city)
        
        for variant in variants:
            try:
                escaped_variant = variant.replace('"', '\\"')
                query = f"""
                [out:json][timeout:25];
                (
                node["addr:street"="{escaped_variant}"]["addr:housenumber"="{civic_num}"]({south},{west},{north},{east});
                way["addr:street"="{escaped_variant}"]["addr:housenumber"="{civic_num}"]({south},{west},{north},{east});
                );
                out geom;
                """
                
                response = self.session.post(
                    "http://overpass-api.de/api/interpreter", 
                    data=query, timeout=30
                )
                time.sleep(1.0)
                
                if response.status_code == 200:
                    geometries = []
                    for elem in response.json().get('elements', []):
                        if elem.get('type') == 'node':
                            lat, lon = elem.get('lat'), elem.get('lon')
                            if lat and lon and self._is_inside_bbox([lat, lon], city.default_bbox):
                                geometries.append({'type': 'Point', 'coordinates': [lat, lon]})
                        elif elem.get('type') == 'way' and 'geometry' in elem:
                            geom = elem['geometry']
                            if geom:
                                lat, lon = geom[0]['lat'], geom[0]['lon']
                                if self._is_inside_bbox([lat, lon], city.default_bbox):
                                    geometries.append({'type': 'Point', 'coordinates': [lat, lon]})
                    
                    if geometries:
                        # Filter by zone bboxes if available
                        if zone_bboxes:
                            all_filtered = []
                            for zone_bbox in zone_bboxes:
                                filtered_geoms, _ = self._filter_geometries(geometries, zone_bbox, "zone")
                                all_filtered.extend(filtered_geoms)
                            # Remove duplicates
                            unique_geoms = []
                            for geom in all_filtered:
                                if geom not in unique_geoms:
                                    unique_geoms.append(geom)
                            geometries = unique_geoms
                        
                        if geometries:
                            self.cache[cache_key] = {
                                'type': 'civic',
                                'geometries': geometries
                            }
                            return True
                        
            except Exception:
                continue
        
        return False

    def fetch_place(self, place_name: str, city_prefix: str, zones_info: Dict[str, Set[str]]) -> bool:
        """Fetch coordinates for a place with zone-based filtering"""
        # Create city-specific cache key
        cache_key = f"{city_prefix}_{place_name}"
        
        # Check cache first - if we have coordinates for this city, use them
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if cached and cached.get('geometries') and len(cached['geometries']) > 0:
                # We have valid cached coordinates for this city - use them
                self.stats['cached'] += 1
                return True
        
        # Get zone bboxes for this place (only if we need to fetch new data)
        city = CITIES[city_prefix]
        zone_bboxes = []
        
        for zone_name in zones_info.get(place_name, set()):
            zone_bbox = get_zone_bbox(city, zone_name)
            if zone_bbox:
                zone_bboxes.append(zone_bbox)

        zones_str = ", ".join(zones_info.get(place_name, set()))
        print(f"      🔍 Fetching: {place_name} (zones: {zones_str})")
        
        # Check if civic address
        civico_match = re.search(r'^(.+?)\s+civico\s+(\d+)$', place_name)
        if civico_match:
            street, civic_num = civico_match.group(1).strip(), civico_match.group(2)
            if self._fetch_civic(cache_key, street, civic_num, city, zone_bboxes):
                print(f"         🏠 Found civic address")
                self.stats['fetched'] += 1
                return True
            else:
                print(f"         ❌ Civic not found")
                self.stats['failed'] += 1
                return False
        
        # Normal place (street, square, etc.)
        variants = self._generate_variants(place_name, city)
        
        print(f"         🔄 Trying variants: {', '.join(variants[:])}")
        
        for variant in variants:
            osm_ids = self._search_nominatim(variant, city)
            if osm_ids:
                all_geometries = []
                for osm_id in osm_ids:
                    geometries = self._get_geometry(osm_id, city, place_name)  # Pass original place name
                    all_geometries.extend(geometries)
                            
                if all_geometries:
                    # First filter to city bbox
                    city_filtered, city_filtered_count = self._filter_geometries(
                        all_geometries, city.default_bbox, "city"
                    )
                    
                    # Then filter to zone bboxes if available
                    final_geometries = city_filtered
                    if zone_bboxes and city_filtered:
                        union_bbox = union_bboxes(zone_bboxes)
                        final_geometries, zone_filtered_count = self._filter_geometries(
                            city_filtered, union_bbox, "zone"
                        )
                        if zone_filtered_count > 0:
                            print(f"         🎯 Zone-filtered {zone_filtered_count} coords")
                    
                    if final_geometries:
                        place_type = 'square' if any('piazza' in place_name.lower() for _ in [1]) else 'street'
                        self.cache[cache_key] = {
                            'type': place_type,
                            'geometries': final_geometries
                        }
                        print(f"         ✅ Found with variant '{variant}': {len(final_geometries)} geometries")
                        if city_filtered_count > 0:
                            print(f"         🗑️ City-filtered {city_filtered_count} coords")
                        self.stats['fetched'] += 1
                        return True

        print(f"         🔄 Nominatim failed, trying direct Overpass search...")
        direct_geometries = self._search_overpass_direct(place_name, city, zone_bboxes)
        
        if direct_geometries:
            place_type = 'square' if 'piazza' in place_name.lower() else 'street'
            self.cache[place_name] = {
                'type': place_type,
                'geometries': direct_geometries
            }
            print(f"         ✅ Found via direct Overpass: {len(direct_geometries)} geometries")
            self.stats['fetched'] += 1
            return True
        
        print(f"         ❌ Not found after trying {len(variants)} variants")
        self.stats['failed'] += 1
        return False
        
    def process_ordinances(self):
        """Main processing function with zone-based filtering"""
        print("🏛️ ZONE-FILTERED COORDINATES FETCHER v2.1")
        print("=" * 50)
        
        # Load ordinances
        try:
            with open("ordinanze.json", 'r', encoding='utf-8') as f:
                ordinances = json.load(f)
        except FileNotFoundError:
            print("❌ ordinanze.json not found")
            return
        
        # Extract all unique elements and track their zones
        all_elements = {}  # element_name -> {city: city_prefix, zones: set of zone names}
        
        print("🔍 Parsing ordinances...")
        start = 0
        for ord_id, ord_data in ordinances.items():
            start +=1
            if start > 2:
                break
            city_prefix = self._detect_city(ord_id)
            if not city_prefix or city_prefix not in CITIES:
                continue
            
            for zone_name, locations in ord_data['zones'].items():
                for specification in locations:
                    elements = self.extract_elements(specification)
                    for element in elements:
                        if element not in all_elements:
                            all_elements[element] = {
                                'city': city_prefix,
                                'zones': set()
                            }
                        all_elements[element]['zones'].add(zone_name)
        
        print(f"📊 Found {len(all_elements)} unique elements")
        
        # Group by city and process
        by_city = {}
        zones_info = {}  # element -> set of zones
        
        for element, info in all_elements.items():
            city = info['city']
            if city not in by_city:
                by_city[city] = []
            by_city[city].append(element)
            zones_info[element] = info['zones']
        
        # Process each city
        for city_prefix, elements in by_city.items():
            city_name = CITIES[city_prefix].city_name
            print(f"\n🏛️ {city_name}: {len(elements)} elements")
            
            # Count zones with bboxes
            city_config = CITIES[city_prefix]
            zones_with_bbox = set()
            total_zones = set()
            
            for element in elements:
                for zone_name in zones_info[element]:
                    total_zones.add(zone_name)
                    if get_zone_bbox(city_config, zone_name):
                        zones_with_bbox.add(zone_name)
            
            print(f"   📍 {len(zones_with_bbox)}/{len(total_zones)} zones have bboxes")
            
            for i, element in enumerate(elements):
                print(f"\n[{i+1}/{len(elements)}] {element}")
                self.fetch_place(element, city_prefix, zones_info)
                
                # Save progress every 10
                if (i + 1) % 10 == 0:
                    self._save_cache()
        
        # Final save and stats
        self._save_cache()
        
        print(f"\n🎉 COMPLETE!")
        print(f"   ✅ Fetched: {self.stats['fetched']}")
        print(f"   📋 Cached: {self.stats['cached']}")
        print(f"   ❌ Failed: {self.stats['failed']}")
        print(f"   🗑️ City-filtered (outside city bbox): {self.stats['filtered']}")
        print(f"   🎯 Zone-filtered (outside zone bbox): {self.stats['zone_filtered']}")
        print(f"   💾 Total in cache: {len(self.cache)}")


def main():
    fetcher = CoordinatesFetcher()
    fetcher.process_ordinances()

if __name__ == "__main__":
    main()