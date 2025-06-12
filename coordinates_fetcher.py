"""
coordinates_fetcher.py
Intelligent parsing of location specifications
"""

import json
import requests
import time
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class LocationSpec:
    """Parsed location specification"""
    primary_street: str
    specification_type: str  # 'civico', 'tratto', 'incrocio', 'simple'
    specification: Optional[str]
    query_targets: List[str]
    display_info: str
    original_text: str

class CoordinatesFetcher:
    def __init__(self, cache_file: str = "coordinates_cache.json"):
        self.rome_bbox = {
            'south': 41.8,
            'west': 12.4,
            'north': 42.0,
            'east': 12.6
        }
        
        self.zone_bboxes = {
            'esquilino': {'south': 41.888, 'west': 12.495, 'north': 41.905, 'east': 12.52},
            'tuscolano': {'south': 41.85, 'west': 12.512, 'north': 41.883, 'east': 12.56},
            'valle_aurelia': {'south': 41.889, 'west': 12.41, 'north': 41.925, 'east': 12.46}
        }
        
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.cache_file = cache_file
        self.cache = self._load_cache()
        
        self.special_cases = {
            "la marmora": ["La Marmora", "Lamarmora"],
            "sottopasso": ["Sottopasso", "Sottopassaggio"],
            "pettinelli": ["Turbigo"],
        }
        
        self.roman_to_italian = {
            'I': 'Primo', 'II': 'Secondo', 'III': 'Terzo', 'IV': 'Quarto',
            'V': 'Quinto', 'VI': 'Sesto', 'VII': 'Settimo', 'VIII': 'Ottavo',
            'IX': 'Nono', 'X': 'Decimo', 'XI': 'Undicesimo', 'XII': 'Dodicesimo'
        }
        
        self.abbreviations = [
            (r'\bVittorio Emanuele\b', 'V. Emanuele'), (r'\bVittorio Emanuele\b', 'Emanuele'),
            (r'\bGiovanni\b', 'G.'), (r'\bVincenzo\b', 'V.'), (r'\bFilippo\b', 'F.'),
            (r'\bPrincipe\b', 'P.'), (r'\bDaniele\b', 'D.'), (r'\bEnrico\b', 'E.'),
            (r'\bUrbano\b', 'U.'), (r'\bAlfredo\b', 'A.'), (r'\bBettino\b', 'B.'),
            (r'\bCarlo\b', 'C.'), (r'\bManfredo\b', 'M.'), (r'\bAnastasio\b', 'A.'),
            (r'\bdi Valle Aurelia\b', 'Valle Aurelia'), (r'\bdegli Ubaldi\b', 'Ubaldi'),
            (r'\bDe Vecchi Pieralice\b', 'de Vecchi Pieralice'), (r'\bdi Bartolo\b', 'Bartolo')
        ]
        
        self.italian_stopwords = {'di', 'del', 'della', 'delle', 'dei', 'degli', 'da', 'de', 'con'}
        
        self.zone_mappings = {
            'zona_esquilino': 'esquilino',
            'zona_stazione_termini_esquilino': 'esquilino',
            'zona_tuscolano': 'tuscolano',
            'zona_valle_aurelia': 'valle_aurelia',
            'assi_viari_inclusi_nel_perimetro_zona_valle_aurelia': 'valle_aurelia'
        }
    
    def _load_cache(self) -> Dict:
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
                print(f"📦 Loaded cache with {len(cache)} entries")
                return cache
        except FileNotFoundError:
            print(f"📦 Starting fresh cache")
            return {}
    
    def _save_cache(self):
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
        print(f"💾 Saved cache with {len(self.cache)} entries")
    
    def _cache_key(self, street_name: str, zone_name: str = None) -> str:
        zone_suffix = f"__{zone_name}" if zone_name else ""
        return f"{street_name.strip()}{zone_suffix}"
    
    def parse_location_specification(self, location_string: str) -> LocationSpec:
        civico_match = re.search(r'^(.+?)\s*\(fronte civico (\d+)\)$', location_string)
        if civico_match:
            primary = civico_match.group(1).strip()
            civico_num = civico_match.group(2)
            return LocationSpec(primary, 'civico', civico_num, [primary], f"Near house number {civico_num}", location_string)
        
        tratto_match = re.search(r'^(.+?)\s+tratto compreso tra (.+?)$', location_string)
        if tratto_match:
            primary = tratto_match.group(1).strip()
            endpoints_str = tratto_match.group(2)
            endpoints = [ep.strip() for ep in endpoints_str.split(' e ')]
            return LocationSpec(primary, 'tratto', endpoints_str, [primary] + endpoints, f"Section between {' and '.join(endpoints)}", location_string)
        
        incrocio_match = re.search(r'^(.+?)\s+incrocio con (.+?)$', location_string)
        if incrocio_match:
            primary = incrocio_match.group(1).strip()
            intersecting = incrocio_match.group(2).strip()
            return LocationSpec(primary, 'incrocio', intersecting, [primary, intersecting], f"Intersection with {intersecting}", location_string)
        
        return LocationSpec(location_string.strip(), 'simple', None, [location_string.strip()], 'Entire street/square', location_string)
    
    def get_zone_bbox(self, zone_name: str) -> Dict:
        zone_key = zone_name.lower().replace(' ', '_').replace('-', '_')
        mapped_zone = self.zone_mappings.get(zone_key, zone_key)
        return self.zone_bboxes.get(mapped_zone, self.rome_bbox)
    
    def generate_name_variants(self, street_name: str) -> List[str]:
        variants = [street_name]
        
        street_prefix = ""
        base_name = street_name
        for prefix in ["Via ", "Piazza ", "Viale ", "Largo ", "Corso ", "Sottopasso "]:
            if base_name.lower().startswith(prefix.lower()):
                street_prefix = prefix
                base_name = base_name[len(prefix):]
                break
        
        if base_name.lower() in self.special_cases:
            for special_variant in self.special_cases[base_name.lower()]:
                if street_prefix:
                    variants.append(f"{street_prefix}{special_variant}")
                variants.append(special_variant)
        
        if base_name not in variants:
            variants.append(base_name)
        
        for pattern, replacement in self.abbreviations:
            abbreviated = re.sub(pattern, replacement, base_name)
            if abbreviated != base_name:
                if street_prefix:
                    variants.append(f"{street_prefix}{abbreviated}")
                variants.append(abbreviated)
        
        roman_numeral_pattern = r'\b(I{1,3}|IV|V|VI{0,3}|IX|X|XI{0,2})\b$'
        if re.search(roman_numeral_pattern, base_name):
            for roman, italian in self.roman_to_italian.items():
                if base_name.endswith(f' {roman}'):
                    italian_version = re.sub(f' {roman}$', f' {italian}', base_name)
                    if street_prefix:
                        variants.append(f"{street_prefix}{italian_version}")
                    variants.append(italian_version)
                    
                    for pattern, replacement in self.abbreviations:
                        abbreviated_italian = re.sub(pattern, replacement, italian_version)
                        if abbreviated_italian != italian_version:
                            if street_prefix:
                                variants.append(f"{street_prefix}{abbreviated_italian}")
                            variants.append(abbreviated_italian)
        
        words = base_name.split()
        if len(words) > 1:
            last_word = words[-1].lower()
            if last_word not in self.italian_stopwords and len(last_word) > 2:
                variants.append(words[-1])
            
            if len(words) >= 3:
                filtered_words = [w for w in words if w.lower() not in self.italian_stopwords]
                if len(filtered_words) >= 2:
                    variants.append(' '.join(filtered_words))
                
                last_two = words[-2:]
                if all(w.lower() not in self.italian_stopwords for w in last_two):
                    variants.append(' '.join(last_two))
                
                if len(words) >= 4:
                    last_three = words[-3:]
                    if all(w.lower() not in self.italian_stopwords for w in last_three):
                        variants.append(' '.join(last_three))
        
        return list(dict.fromkeys(variants))
    
    def _search_civic_number(self, street_name: str, civic_number: str, bbox: Dict) -> Optional[List[Tuple[float, float]]]:
        name_variants = self.generate_name_variants(street_name)
        print(f"   🏠 Searching civic number {civic_number}")
        
        for variant in name_variants:
            query = f"""
            [out:json][timeout:25];
            (
              way["highway"]["name"~"^{re.escape(variant)}$",i]["addr:housenumber"="{civic_number}"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
              node["addr:street"~"^{re.escape(variant)}$",i]["addr:housenumber"="{civic_number}"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
              way["highway"]["name"~"^Via {re.escape(variant)}$",i]["addr:housenumber"="{civic_number}"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
              node["addr:street"~"^Via {re.escape(variant)}$",i]["addr:housenumber"="{civic_number}"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
            );
            (._;>;);
            out geom;
            """
            
            try:
                response = requests.post(self.overpass_url, data=query, timeout=30, verify=False)
                if response.status_code == 200:
                    data = response.json()
                    coordinates = []
                    
                    for element in data.get('elements', []):
                        if element.get('type') == 'node':
                            coordinates.append((element['lat'], element['lon']))
                        elif element.get('type') == 'way' and 'geometry' in element and element['geometry']:
                            first_node = element['geometry'][0]
                            coordinates.append((first_node['lat'], first_node['lon']))
                    
                    if coordinates:
                        print(f"      🎯 Found civic {civic_number} with variant: '{variant}'")
                        return coordinates
                        
            except Exception as e:
                print(f"❌ Error searching civic '{variant}': {e}")
                continue
        
        print(f"   ❌ No civic {civic_number} found")
        return None
    
    def query_street_coordinates(self, street_name: str, zone_name: str = None) -> Optional[Dict]:
        location_spec = self.parse_location_specification(street_name)
        bbox = self.get_zone_bbox(zone_name) if zone_name else self.rome_bbox
        
        print(f"🔍 Parsing: {street_name}")
        print(f"   Type: {location_spec.specification_type}")
        print(f"   Primary: {location_spec.primary_street}")
        print(f"   Info: {location_spec.display_info}")
        print(f"   Query targets: {location_spec.query_targets}")
        if zone_name:
            print(f"   Zone: {zone_name}")
        
        all_coordinates = {}
        for target in location_spec.query_targets:
            cache_key = self._cache_key(target, zone_name)
            
            if cache_key in self.cache:
                print(f"   📋 Using cached: {target}")
                all_coordinates[target] = self.cache[cache_key]
                continue
            
            name_variants = self.generate_name_variants(target)
            print(f"   🎯 Querying: {target}")
            print(f"      Variants: {name_variants}")
            
            for variant in name_variants:
                coordinates = self._search_with_variant(variant, bbox)
                if coordinates:
                    print(f"      ✅ Found {len(coordinates)} points with variant: '{variant}'")
                    coord_data = {'coordinates': coordinates, 'found_variant': variant}
                    all_coordinates[target] = coord_data
                    self.cache[cache_key] = coord_data
                    break
                else:
                    print(f"      ❌ No results for variant: '{variant}'")
            
            if target not in all_coordinates:
                print(f"   ❌ No coordinates found for: {target}")
        
        special_coordinates = []
        if location_spec.specification_type == 'civico' and location_spec.specification:
            civic_coords = self._search_civic_number(location_spec.primary_street, location_spec.specification, bbox)
            if civic_coords:
                special_coordinates = civic_coords
        
        processed_result = self._process_coordinates_by_type(location_spec, all_coordinates, special_coordinates)
        
        if processed_result:
            print(f"✅ Successfully processed {location_spec.specification_type} specification")
            return processed_result
        else:
            print(f"❌ No coordinates found for any target")
            return None
    
    def _process_coordinates_by_type(self, location_spec: LocationSpec, all_coordinates: Dict, special_coordinates: List = None) -> Optional[Dict]:
        if not all_coordinates:
            return None
        
        colors = {'simple': 'green', 'civico': 'blue', 'incrocio': 'red', 'tratto': 'orange'}
        icons = {'simple': '📍', 'civico': '🏠', 'incrocio': '✕', 'tratto': '🔗'}
        
        result = {
            'specification': location_spec.__dict__,
            'coordinates': [],
            'metadata': {
                'type': location_spec.specification_type,
                'display_info': location_spec.display_info,
                'color': colors.get(location_spec.specification_type, 'gray'),
                'icon': icons.get(location_spec.specification_type, '❓')
            }
        }
        
        if special_coordinates:
            result['special_coordinates'] = special_coordinates
        
        if location_spec.specification_type == 'simple':
            primary_data = all_coordinates.get(location_spec.primary_street)
            if primary_data:
                result['coordinates'] = primary_data['coordinates']
                result['metadata']['found_variant'] = primary_data['found_variant']
        
        elif location_spec.specification_type == 'civico':
            primary_data = all_coordinates.get(location_spec.primary_street)
            if primary_data:
                result['coordinates'] = primary_data['coordinates']
                result['metadata']['found_variant'] = primary_data['found_variant']
                result['metadata']['note'] = f"Found specific coordinates for house number {location_spec.specification}" if special_coordinates else f"Showing entire street (house number {location_spec.specification} not precisely located)"
        
        elif location_spec.specification_type == 'incrocio':
            primary_data = all_coordinates.get(location_spec.primary_street)
            intersecting_data = all_coordinates.get(location_spec.specification)
            
            if primary_data:
                result['coordinates'].extend([{'type': 'primary', 'coords': coord} for coord in primary_data['coordinates']])
                result['metadata']['primary_variant'] = primary_data['found_variant']
            
            if intersecting_data:
                result['coordinates'].extend([{'type': 'intersecting', 'coords': coord} for coord in intersecting_data['coordinates']])
                result['metadata']['intersecting_variant'] = intersecting_data['found_variant']
            
            if primary_data or intersecting_data:
                result['metadata']['note'] = "Showing both streets (intersection point not precisely calculated)"
        
        elif location_spec.specification_type == 'tratto':
            primary_data = all_coordinates.get(location_spec.primary_street)
            if primary_data:
                result['coordinates'].extend([{'type': 'primary', 'coords': coord} for coord in primary_data['coordinates']])
                result['metadata']['primary_variant'] = primary_data['found_variant']
            
            endpoints = location_spec.specification.split(' e ')
            for i, endpoint in enumerate(endpoints):
                endpoint = endpoint.strip()
                endpoint_data = all_coordinates.get(endpoint)
                if endpoint_data:
                    result['coordinates'].extend([{'type': f'endpoint_{i+1}', 'coords': coord} for coord in endpoint_data['coordinates']])
                    result['metadata'][f'endpoint_{i+1}_variant'] = endpoint_data['found_variant']
            
            if primary_data:
                result['metadata']['note'] = f"Showing entire street with reference points ({location_spec.specification})"
        
        return result if result['coordinates'] else None
    
    def _search_with_variant(self, name_variant: str, bbox: Dict) -> Optional[List[Tuple[float, float]]]:
        query = f"""
        [out:json][timeout:25];
        (
          way["highway"]["name"~"^{re.escape(name_variant)}$",i]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          way["highway"]["name"~"^Via {re.escape(name_variant)}$",i]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          way["highway"]["name"~"^Viale {re.escape(name_variant)}$",i]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          way["place"]["name"~"^{re.escape(name_variant)}$",i]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          way["place"]["name"~"^Piazza {re.escape(name_variant)}$",i]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          relation["place"]["name"~"^{re.escape(name_variant)}$",i]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          relation["place"]["name"~"^Piazza {re.escape(name_variant)}$",i]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          node["place"="square"]["name"~"^{re.escape(name_variant)}$",i]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
          node["place"="square"]["name"~"^Piazza {re.escape(name_variant)}$",i]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
        );
        (._;>;);
        out geom;
        """
        
        try:
            response = requests.post(self.overpass_url, data=query, timeout=30, verify=False)
            if response.status_code == 200:
                data = response.json()
                coordinates = []
                
                for element in data.get('elements', []):
                    if element.get('type') == 'way' and 'geometry' in element:
                        for node in element['geometry']:
                            coordinates.append((node['lat'], node['lon']))
                    elif element.get('type') == 'node':
                        coordinates.append((element['lat'], element['lon']))
                
                return coordinates if coordinates else None
            else:
                return None
                
        except Exception as e:
            print(f"❌ Error searching variant '{name_variant}': {e}")
            return None
    
    def fetch_all_coordinates(self, ordinances_file: str) -> Dict:
        try:
            with open(ordinances_file, "r", encoding="utf-8") as f:
                ordinances_data = json.load(f)
        except FileNotFoundError:
            print(f"❌ File not found: {ordinances_file}")
            return {}
        
        results = {}
        total_streets = sum(len(streets) for ord_data in ordinances_data.values() for streets in ord_data['zones'].values())
        
        print(f"🏛️ Processing {total_streets} streets from {len(ordinances_data)} ordinances...")
        print(f"🧠 Using parsing with caching...")
        
        current_street = 0
        
        for ord_id, ord_data in ordinances_data.items():
            results[ord_id] = {
                'metadata': {
                    'protocol': ord_data.get('protocol', ord_id),
                    'date': ord_data.get('date', ''),
                    'title': ord_data.get('title', '')
                },
                'zones': {}
            }
            
            for zone_name, streets in ord_data['zones'].items():
                results[ord_id]['zones'][zone_name] = {}
                
                for street in streets:
                    current_street += 1
                    print(f"\n[{current_street}/{total_streets}] {street}")
                    
                    coordinates_result = self.query_street_coordinates(street, zone_name)
                    results[ord_id]['zones'][zone_name][street] = coordinates_result
                    
                    time.sleep(1.5)
        
        self._save_cache()
        return results
    
    def save_coordinates(self, coordinates: Dict, output_file: str = "coordinates.json"):
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(coordinates, f, ensure_ascii=False, indent=2)
        
        print(f"💾 coordinates saved to {output_file}")
        
        total_found = 0
        total_streets = 0
        type_counts = {'simple': 0, 'civico': 0, 'incrocio': 0, 'tratto': 0}
        special_count = 0
        
        for ord_data in coordinates.values():
            for zone_data in ord_data['zones'].values():
                for street, result in zone_data.items():
                    total_streets += 1
                    if result:
                        total_found += 1
                        spec_type = result.get('specification', {}).get('specification_type', 'unknown')
                        if spec_type in type_counts:
                            type_counts[spec_type] += 1
                        if result.get('special_coordinates'):
                            special_count += 1
        
        print(f"\n📊 Processing Summary:")
        print(f"   Total streets: {total_streets}")
        print(f"   Coordinates found: {total_found}")
        print(f"   Success rate: {total_found/total_streets*100:.1f}%")
        print(f"   Special coordinates: {special_count}")
        print(f"\n📋 Specification Types:")
        
        icons = {'simple': '📍', 'civico': '🏠', 'incrocio': '✕', 'tratto': '🔗'}
        colors = {'simple': 'green', 'civico': 'blue', 'incrocio': 'red', 'tratto': 'orange'}
        
        for spec_type, count in type_counts.items():
            if count > 0:
                icon = icons.get(spec_type, '❓')
                color = colors.get(spec_type, 'gray')
                print(f"   {icon} {spec_type}: {count} ({color})")

def main():
    fetcher = CoordinatesFetcher()
    coordinates = fetcher.fetch_all_coordinates("ordinanze.json")
    
    if coordinates:
        fetcher.save_coordinates(coordinates)
        print(f"\n🎯 Next steps:")
        print(f"   1. Update your HTML viewer to handle the new coordinate format")
        print(f"   2. Use the 'metadata' field for proper visualization")
        print(f"   3. Show different colors/icons based on specification type")
        print(f"   4. Display the 'display_info' for user-friendly descriptions")
        print(f"   5. Highlight 'special_coordinates' for civic numbers")
    
    return coordinates

if __name__ == "__main__":
    main()