"""
coordinates_fetcher.py
Recupera coordinate per vie/piazze/ da Overpass API 
"""

import json
import requests
import time
import re
from typing import Dict, List, Tuple, Optional

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
    
    def extract_street_info(self, street_description: str) -> Tuple[str, Optional[str]]:
        """Extract street name and specific location info (like civico numbers)"""
        
        # Handle specific location indicators
        civico_match = re.search(r'\(fronte civico (\d+)\)', street_description)
        tratto_match = re.search(r'tratto compreso tra (.+)', street_description)
        incrocio_match = re.search(r'incrocio con (.+)', street_description)
        
        specific_info = None
        clean_name = street_description
        
        if civico_match:
            specific_info = f"near civico {civico_match.group(1)}"
            clean_name = re.sub(r'\s*\(fronte civico \d+\)', '', street_description)
        elif tratto_match:
            specific_info = f"section between {tratto_match.group(1)}"
            clean_name = re.sub(r'\s*tratto compreso tra .+', '', street_description)
        elif incrocio_match:
            specific_info = f"intersection with {incrocio_match.group(1)}"
            clean_name = re.sub(r'\s*incrocio con .+', '', street_description)
        
        return clean_name.strip(), specific_info
    
    def generate_name_variants(self, street_name: str) -> List[str]:
        """Generate different variants of street names to try"""
        variants = [street_name]  # Start with original name
        
        # Extract street type prefix
        street_prefix = ""
        base_name = street_name
        for prefix in ["Via ", "Piazza ", "Viale ", "Largo ", "Corso "]:
            if base_name.startswith(prefix):
                street_prefix = prefix
                base_name = base_name[len(prefix):]
                break
        
        # Special hardcoded cases
        special_cases = {
            "La Marmora": ["La Marmora", "Lamarmora"],
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
    
    def query_street_coordinates(self, street_name: str, zone_name: str = None, specific_info: str = None) -> Optional[List[Tuple[float, float]]]:
        """Query Overpass API for street coordinates with zone-specific search"""
        
        bbox = self.get_zone_bbox(zone_name) if zone_name else self.rome_bbox
        
        # Extract clean name and handle specific location info
        clean_name, extracted_info = self.extract_street_info(street_name)
        if extracted_info:
            specific_info = extracted_info
        
        # Generate variants to try
        name_variants = self.generate_name_variants(clean_name)
        
        print(f"🔍 Querying: {street_name}")
        if zone_name:
            print(f"   Zone: {zone_name}")
        if specific_info:
            print(f"   Specific: {specific_info}")
        print(f"   Trying variants: {name_variants}")
        
        # Try each variant
        for variant in name_variants:
            coordinates = self._search_with_variant(variant, bbox)
            if coordinates:
                print(f"✅ Found {len(coordinates)} points with variant: '{variant}'")
                
                # If we have specific location info, try to filter results
                if specific_info and "civico" in specific_info:
                    # For now, return all coordinates - we could add more filtering logic here
                    pass
                
                return coordinates
            else:
                print(f"   ❌ No results for variant: '{variant}'")
        
        print(f"❌ No coordinates found for any variant")
        return None
    
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
        """Fetch coordinates for all streets in all ordinances."""
        
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
                    
                    coordinates = self.query_street_coordinates(street, zone_name)
                    
                    if coordinates:
                        results[ord_id]['zones'][zone_name][street] = coordinates
                    else:
                        results[ord_id]['zones'][zone_name][street] = None
                    
                    # Rate limiting
                    time.sleep(1.5)
        
        return results
    
    def save_coordinates(self, coordinates: Dict, output_file: str = "coordinates.json"):
        """Save coordinates to JSON file."""
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(coordinates, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Coordinates saved to {output_file}")

def main():
    """Main function to fetch coordinates."""
    
    fetcher = CoordinatesFetcher()
    
    # Fetch all coordinates
    coordinates = fetcher.fetch_all_coordinates("ordinanze/ordinanze.json")
    
    if coordinates:
        # Save to file
        fetcher.save_coordinates(coordinates)
        
        # Print summary
        total_found = 0
        total_streets = 0
        
        for ord_data in coordinates.values():
            for zone_data in ord_data['zones'].values():
                for street, coords in zone_data.items():
                    total_streets += 1
                    if coords:
                        total_found += 1
        
        print(f"\n📊 Summary:")
        print(f"   Total streets: {total_streets}")
        print(f"   Coordinates found: {total_found}")
        print(f"   Success rate: {total_found/total_streets*100:.1f}%")
    
    return coordinates

if __name__ == "__main__":
    main()