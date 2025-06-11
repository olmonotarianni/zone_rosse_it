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
    def __init__(self):
        self.rome_bbox = {
            'south': 41.8,
            'west': 12.4,
            'north': 42.0,
            'east': 12.6
        }
        
        # Zone-specific bounding boxes for more precise searches
        self.zone_bboxes = {
            'esquilino': {
                'south': 41.888,
                'west': 12.495,
                'north': 41.905,
                'east': 12.52
            },
            'tuscolano': {
                'south': 41.85,
                'west': 12.512,
                'north': 41.883,
                'east': 12.56
            },
            'valle_aurelia': {
                'south': 41.889,
                'west': 12.41,
                'north': 41.925,
                'east': 12.46
            }
        }
        
        self.overpass_url = "https://overpass-api.de/api/interpreter"
    
    def parse_location_specification(self, location_string: str) -> LocationSpec:
        """Parse location string into structured specification"""
        
        # Pattern 1: (fronte civico X)
        civico_match = re.search(r'^(.+?)\s*\(fronte civico (\d+)\)$', location_string)
        if civico_match:
            primary = civico_match.group(1).strip()
            civico_num = civico_match.group(2)
            return LocationSpec(
                primary_street=primary,
                specification_type='civico',
                specification=civico_num,
                query_targets=[primary],
                display_info=f"Near house number {civico_num}",
                original_text=location_string
            )
        
        # Pattern 2: tratto compreso tra A e B
        tratto_match = re.search(r'^(.+?)\s+tratto compreso tra (.+?)$', location_string)
        if tratto_match:
            primary = tratto_match.group(1).strip()
            endpoints_str = tratto_match.group(2)
            endpoints = [ep.strip() for ep in endpoints_str.split(' e ')]
            
            return LocationSpec(
                primary_street=primary,
                specification_type='tratto',
                specification=endpoints_str,
                query_targets=[primary] + endpoints,
                display_info=f"Section between {' and '.join(endpoints)}",
                original_text=location_string
            )
        
        # Pattern 3: incrocio con X
        incrocio_match = re.search(r'^(.+?)\s+incrocio con (.+?)$', location_string)
        if incrocio_match:
            primary = incrocio_match.group(1).strip()
            intersecting = incrocio_match.group(2).strip()
            
            return LocationSpec(
                primary_street=primary,
                specification_type='incrocio',
                specification=intersecting,
                query_targets=[primary, intersecting],
                display_info=f"Intersection with {intersecting}",
                original_text=location_string
            )
        
        # Pattern 4: Simple street name (no specifications)
        return LocationSpec(
            primary_street=location_string.strip(),
            specification_type='simple',
            specification=None,
            query_targets=[location_string.strip()],
            display_info='Entire street/square',
            original_text=location_string
        )
    
    def get_zone_bbox(self, zone_name: str) -> Dict:
        """Get bounding box for specific zone or default to Rome bbox"""
        zone_key = zone_name.lower().replace(' ', '_').replace('-', '_')
        
        # Map zone names to our predefined bboxes
        zone_mappings = {
            'zona_esquilino': 'esquilino',
            'zona_stazione_termini_esquilino': 'esquilino',
            'zona_tuscolano': 'tuscolano',
            'zona_valle_aurelia': 'valle_aurelia',
            'assi_viari_inclusi_nel_perimetro_zona_valle_aurelia': 'valle_aurelia'
        }
        
        mapped_zone = zone_mappings.get(zone_key, zone_key)
        return self.zone_bboxes.get(mapped_zone, self.rome_bbox)
    
    def generate_name_variants(self, street_name: str) -> List[str]:
        """Generate different variants of street names to try"""
        variants = [street_name]  # Start with original name
        
        # Extract street type prefix
        street_prefix = ""
        base_name = street_name
        for prefix in ["Via ", "Piazza ", "Viale ", "Largo ", "Corso ", "Sottopasso "]:
            if base_name.startswith(prefix):
                street_prefix = prefix
                base_name = base_name[len(prefix):]
                break
        
        # Special hardcoded cases
        special_cases = {
            "La Marmora": ["La Marmora", "Lamarmora"],
            "Sottopasso": ["Sottopasso", "Sottopassaggio"]
        }
        
        if base_name in special_cases:
            for special_variant in special_cases[base_name]:
                if street_prefix:
                    variants.append(f"{street_prefix}{special_variant}")
                variants.append(special_variant)
        
        # Check if name contains Roman numerals
        roman_numeral_pattern = r'\b(I{1,3}|IV|V|VI{0,3}|IX|X|XI{0,2})\b$'
        has_roman_numeral = re.search(roman_numeral_pattern, base_name)
        
        if has_roman_numeral:
            # Handle names with Roman numerals specially
            self._add_roman_numeral_variants(variants, street_prefix, base_name)
        else:
            # Regular name processing
            self._add_regular_variants(variants, street_prefix, base_name)
        
        # Remove duplicates while preserving order
        unique_variants = []
        for variant in variants:
            if variant not in unique_variants:
                unique_variants.append(variant)
        
        return unique_variants
    
    def _add_roman_numeral_variants(self, variants: List[str], street_prefix: str, base_name: str):
        """Add variants for names containing Roman numerals"""
        
        # Roman numeral to Italian word mapping
        roman_to_italian = {
            'I': 'Primo',
            'II': 'Secondo', 
            'III': 'Terzo',
            'IV': 'Quarto',
            'V': 'Quinto',
            'VI': 'Sesto',
            'VII': 'Settimo',
            'VIII': 'Ottavo',
            'IX': 'Nono',
            'X': 'Decimo',
            'XI': 'Undicesimo',
            'XII': 'Dodicesimo'
        }
        
        # Common abbreviations that preserve Roman numerals
        abbreviation_patterns = [
            (r'\bVittorio Emanuele\b', 'V. Emanuele'),
            (r'\bVittorio Emanuele\b', 'Emanuele'),
            (r'\bGiovanni\b', 'G.'),
            (r'\bVincenzo\b', 'V.'),
            (r'\bFilippo\b', 'F.'),
            (r'\bPrincipe\b', 'P.'),
            (r'\bDaniele\b', 'D.'),
            (r'\bEnrico\b', 'E.'),
            (r'\bUrbano\b', 'U.'),
            (r'\bAlfredo\b', 'A.'),
            (r'\bBettino\b', 'B.'),
            (r'\bCarlo\b', 'C.'),
            (r'\bManfredo\b', 'M.'),
            (r'\bAnastasio\b', 'A.'),
        ]
        
        # Add base name without prefix if not already added
        if base_name not in variants:
            variants.append(base_name)
        
        # Generate abbreviated versions (keeping Roman numerals intact)
        for pattern, replacement in abbreviation_patterns:
            abbreviated = re.sub(pattern, replacement, base_name)
            if abbreviated != base_name:
                if street_prefix:
                    variants.append(f"{street_prefix}{abbreviated}")
                variants.append(abbreviated)
        
        # Try substituting Roman numerals with Italian words
        for roman, italian in roman_to_italian.items():
            if base_name.endswith(f' {roman}'):
                # Replace Roman numeral with Italian word
                italian_version = re.sub(f' {roman}$', f' {italian}', base_name)
                if street_prefix:
                    variants.append(f"{street_prefix}{italian_version}")
                variants.append(italian_version)
                
                # Also try abbreviated versions with Italian words
                for pattern, replacement in abbreviation_patterns:
                    abbreviated_italian = re.sub(pattern, replacement, italian_version)
                    if abbreviated_italian != italian_version:
                        if street_prefix:
                            variants.append(f"{street_prefix}{abbreviated_italian}")
                        variants.append(abbreviated_italian)
    
    def _add_regular_variants(self, variants: List[str], street_prefix: str, base_name: str):
        """Add variants for regular names without Roman numerals"""
        
        # Add base name without prefix if not already added
        if base_name not in variants:
            variants.append(base_name)
        
        # Italian stopwords and particles to exclude from isolated searches
        italian_stopwords = {'di', 'del', 'della', 'delle', 'dei', 'degli', 'da', 'de', 'con'}
        
        # Handle common abbreviations and name variations
        abbreviation_patterns = [
            # Common name abbreviations
            (r'\bGiovanni\b', 'G.'),
            (r'\bVincenzo\b', 'V.'),
            (r'\bFilippo\b', 'F.'),
            (r'\bPrincipe\b', 'P.'),
            (r'\bDaniele\b', 'D.'),
            (r'\bEnrico\b', 'E.'),
            (r'\bUrbano\b', 'U.'),
            (r'\bAlfredo\b', 'A.'),
            (r'\bBettino\b', 'B.'),
            (r'\bCarlo\b', 'C.'),
            (r'\bManfredo\b', 'M.'),
            # Handle multiple names - keep meaningful chunks together
            (r'\bdi Valle Aurelia\b', 'Valle Aurelia'),
            (r'\bdegli Ubaldi\b', 'Ubaldi'),
            (r'\bDe Vecchi Pieralice\b', 'de Vecchi Pieralice'),
            (r'\bdi Bartolo\b', 'Bartolo'),
        ]
        
        # Generate abbreviated versions
        for pattern, replacement in abbreviation_patterns:
            abbreviated = re.sub(pattern, replacement, base_name)
            if abbreviated != base_name:
                variants.append(abbreviated)
        
        # Smart name truncation - avoid isolating middle words or stopwords
        words = base_name.split()
        if len(words) > 1:
            # Only add meaningful endings, not isolated particles
            last_word = words[-1].lower()
            if last_word not in italian_stopwords and len(last_word) > 2:
                variants.append(words[-1])
            
            # For compound names, try meaningful combinations
            if len(words) >= 3:
                # For names like "Giuseppe di Bartolo" -> try "Giuseppe Bartolo" 
                filtered_words = [w for w in words if w.lower() not in italian_stopwords]
                if len(filtered_words) >= 2:
                    variants.append(' '.join(filtered_words))
                
                # For names like "Giacinto De Vecchi Pieralice" -> try "De Vecchi Pieralice", "Vecchi Pieralice"
                if len(words) >= 3:
                    # Try last two meaningful words
                    last_two = words[-2:]
                    if all(w.lower() not in italian_stopwords for w in last_two):
                        variants.append(' '.join(last_two))
                    
                    # Try last three if available and meaningful
                    if len(words) >= 4:
                        last_three = words[-3:]
                        if all(w.lower() not in italian_stopwords for w in last_three):
                            variants.append(' '.join(last_three))
    
    def query_street_coordinates(self, street_name: str, zone_name: str = None) -> Optional[Dict]:
        """Query coordinates for a location specification with parsing"""
        
        # Parse the location specification
        location_spec = self.parse_location_specification(street_name)
        
        bbox = self.get_zone_bbox(zone_name) if zone_name else self.rome_bbox
        
        print(f"🔍 Parsing: {street_name}")
        print(f"   Type: {location_spec.specification_type}")
        print(f"   Primary: {location_spec.primary_street}")
        print(f"   Info: {location_spec.display_info}")
        print(f"   Query targets: {location_spec.query_targets}")
        if zone_name:
            print(f"   Zone: {zone_name}")
        
        # Query coordinates for each target
        all_coordinates = {}
        for target in location_spec.query_targets:
            name_variants = self.generate_name_variants(target)
            
            print(f"   🎯 Querying: {target}")
            print(f"      Variants: {name_variants}")
            
            for variant in name_variants:
                coordinates = self._search_with_variant(variant, bbox)
                if coordinates:
                    print(f"      ✅ Found {len(coordinates)} points with variant: '{variant}'")
                    all_coordinates[target] = {
                        'coordinates': coordinates,
                        'found_variant': variant
                    }
                    break
                else:
                    print(f"      ❌ No results for variant: '{variant}'")
            
            if target not in all_coordinates:
                print(f"   ❌ No coordinates found for: {target}")
        
        # Process coordinates based on specification type
        processed_result = self._process_coordinates_by_type(location_spec, all_coordinates)
        
        if processed_result:
            print(f"✅ Successfully processed {location_spec.specification_type} specification")
            return processed_result
        else:
            print(f"❌ No coordinates found for any target")
            return None
    
    def _process_coordinates_by_type(self, location_spec: LocationSpec, all_coordinates: Dict) -> Optional[Dict]:
        """Process coordinates based on the specification type"""
        
        if not all_coordinates:
            return None
        
        result = {
            'specification': location_spec.__dict__,
            'coordinates': [],
            'metadata': {
                'type': location_spec.specification_type,
                'display_info': location_spec.display_info,
                'color': self._get_color_for_type(location_spec.specification_type),
                'icon': self._get_icon_for_type(location_spec.specification_type)
            }
        }
        
        if location_spec.specification_type == 'simple':
            # Simple case: just return the coordinates
            primary_data = all_coordinates.get(location_spec.primary_street)
            if primary_data:
                result['coordinates'] = primary_data['coordinates']
                result['metadata']['found_variant'] = primary_data['found_variant']
        
        elif location_spec.specification_type == 'civico':
            # For civico: return primary street coordinates
            # TODO: In the future, could filter by proximity to house number
            primary_data = all_coordinates.get(location_spec.primary_street)
            if primary_data:
                result['coordinates'] = primary_data['coordinates']
                result['metadata']['found_variant'] = primary_data['found_variant']
                result['metadata']['note'] = f"Showing entire street (house number {location_spec.specification} not precisely located)"
        
        elif location_spec.specification_type == 'incrocio':
            # For intersection: combine coordinates from both streets
            primary_data = all_coordinates.get(location_spec.primary_street)
            intersecting_data = all_coordinates.get(location_spec.specification)
            
            if primary_data:
                result['coordinates'].extend([{'type': 'primary', 'coords': coord} for coord in primary_data['coordinates']])
                result['metadata']['primary_variant'] = primary_data['found_variant']
            
            if intersecting_data:
                result['coordinates'].extend([{'type': 'intersecting', 'coords': coord} for coord in intersecting_data['coordinates']])
                result['metadata']['intersecting_variant'] = intersecting_data['found_variant']
            
            # TODO: In the future, could find actual intersection points
            if primary_data or intersecting_data:
                result['metadata']['note'] = "Showing both streets (intersection point not precisely calculated)"
        
        elif location_spec.specification_type == 'tratto':
            # For section: combine primary street with endpoints
            primary_data = all_coordinates.get(location_spec.primary_street)
            if primary_data:
                result['coordinates'].extend([{'type': 'primary', 'coords': coord} for coord in primary_data['coordinates']])
                result['metadata']['primary_variant'] = primary_data['found_variant']
            
            # Add endpoints as reference points
            endpoints = location_spec.specification.split(' e ')
            for i, endpoint in enumerate(endpoints):
                endpoint = endpoint.strip()
                endpoint_data = all_coordinates.get(endpoint)
                if endpoint_data:
                    result['coordinates'].extend([{'type': f'endpoint_{i+1}', 'coords': coord} for coord in endpoint_data['coordinates']])
                    result['metadata'][f'endpoint_{i+1}_variant'] = endpoint_data['found_variant']
            
            # TODO: In the future, could calculate the actual section between endpoints
            if primary_data:
                result['metadata']['note'] = f"Showing entire street with reference points ({location_spec.specification})"
        
        return result if result['coordinates'] else None
    
    def _get_color_for_type(self, spec_type: str) -> str:
        """Get map color for specification type"""
        colors = {
            'simple': 'green',
            'civico': 'blue', 
            'incrocio': 'red',
            'tratto': 'orange'
        }
        return colors.get(spec_type, 'gray')
    
    def _get_icon_for_type(self, spec_type: str) -> str:
        """Get map icon for specification type"""
        icons = {
            'simple': '📍',
            'civico': '🏠',
            'incrocio': '✕',
            'tratto': '🔗'
        }
        return icons.get(spec_type, '❓')
    
    def _search_with_variant(self, name_variant: str, bbox: Dict) -> Optional[List[Tuple[float, float]]]:
        """Search for a specific name variant"""
        
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
            response = requests.post(
                self.overpass_url,
                data=query,
                timeout=30,
                verify=False
            )
            
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
        """Fetch coordinates for all streets in all ordinances with parsing."""
        
        # Load ordinances
        try:
            with open(ordinances_file, "r", encoding="utf-8") as f:
                ordinances_data = json.load(f)
        except FileNotFoundError:
            print(f"❌ File not found: {ordinances_file}")
            return {}
        
        results = {}
        total_streets = 0
        
        # Count total streets
        for ord_data in ordinances_data.values():
            for streets in ord_data['zones'].values():
                total_streets += len(streets)
        
        print(f"🏛️ Processing {total_streets} streets from {len(ordinances_data)} ordinances...")
        print(f"🧠 Using parsing for location specifications...")
        
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
                    
                    if coordinates_result:
                        results[ord_id]['zones'][zone_name][street] = coordinates_result
                    else:
                        results[ord_id]['zones'][zone_name][street] = None
                    
                    # Rate limiting
                    time.sleep(1.5)
        
        return results
    
    def save_coordinates(self, coordinates: Dict, output_file: str = "coordinates.json"):
        """Save  coordinates to JSON file."""
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(coordinates, f, ensure_ascii=False, indent=2)
        
        print(f"💾 coordinates saved to {output_file}")
        
        # Print summary
        total_found = 0
        total_streets = 0
        type_counts = {'simple': 0, 'civico': 0, 'incrocio': 0, 'tratto': 0}
        
        for ord_data in coordinates.values():
            for zone_data in ord_data['zones'].values():
                for street, result in zone_data.items():
                    total_streets += 1
                    if result:
                        total_found += 1
                        spec_type = result.get('specification', {}).get('specification_type', 'unknown')
                        if spec_type in type_counts:
                            type_counts[spec_type] += 1
        
        print(f"\n📊 Processing Summary:")
        print(f"   Total streets: {total_streets}")
        print(f"   Coordinates found: {total_found}")
        print(f"   Success rate: {total_found/total_streets*100:.1f}%")
        print(f"\n📋 Specification Types:")
        for spec_type, count in type_counts.items():
            if count > 0:
                icon = self._get_icon_for_type(spec_type)
                color = self._get_color_for_type(spec_type)
                print(f"   {icon} {spec_type}: {count} ({color})")

def main():
    """Main function to fetch  coordinates."""
    
    fetcher = CoordinatesFetcher()
    
    # Fetch all coordinates with parsing
    coordinates = fetcher.fetch_all_coordinates("ordinanze.json")
    
    if coordinates:
        # Save to file
        fetcher.save_coordinates(coordinates)
        
        print(f"\n🎯 Next steps:")
        print(f"   1. Update your HTML viewer to handle the new coordinate format")
        print(f"   2. Use the 'metadata' field for proper visualization")
        print(f"   3. Show different colors/icons based on specification type")
        print(f"   4. Display the 'display_info' for user-friendly descriptions")
    
    return coordinates

if __name__ == "__main__":
    main()