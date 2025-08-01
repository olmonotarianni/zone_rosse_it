from dataclasses import dataclass
from typing import Optional
import json
import os
import shutil

@dataclass
class CityConfig:
    city_name: str
    city_pattern: str  # For API searches
    default_bbox: tuple[float, float, float, float]  # south, west, north, east
    zone_bboxes: dict[str, tuple[float, float, float, float]]
    zone_mappings: dict[str, str]
    special_cases: dict[str, list[str]]


def create_rome_config() -> CityConfig:
    return CityConfig(
        city_name="Roma",
        city_pattern="Roma",
        default_bbox=(41.8, 12.4, 42.0, 12.6),
        zone_bboxes={
            'esquilino': (41.888, 12.495, 41.905, 12.52),
            'tuscolano': (41.872067,12.508718,41.884657,12.539617),
            'valle_aurelia': (41.889, 12.41, 41.925, 12.46)
        },
        zone_mappings={
            'zona_esquilino': 'esquilino',
            'zona_stazione_termini_esquilino': 'esquilino',
            'zona_tuscolano': 'tuscolano',
            'zona_valle_aurelia': 'valle_aurelia',
            'assi_viari_inclusi_nel_perimetro_zona_valle_aurelia': 'valle_aurelia'
        },
        special_cases={
            "la marmora": ["La Marmora", "Lamarmora"],
            "sottopasso": ["Sottopasso", "Sottopassaggio"],
            "pettinelli": ["Turbigo"],
            # Common abbreviations and variants
            "turati": ["Filippo Turati", "F. Turati"],
            "giolitti": ["Giovanni Giolitti", "G. Giolitti"],
            "amendola": ["Giovanni Amendola", "G. Amendola"],
            "giacinto de vecchi pieralice": ["Pieralice"],
            "anastasio II": ["Anastasio Secondo"]
        }
    )

def create_milan_config() -> CityConfig:
    return CityConfig(
        city_name="Milano", 
        city_pattern="Milano",
        default_bbox=(45.352097,8.980637,45.590120,9.385071),
        zone_bboxes={
            'zona_duomo': (45.460, 9.175, 45.470, 9.205),
            'navigli_darsena_colonne': (45.440, 9.160, 45.465, 9.195),
            'stazione_centrale': (45.468, 9.192, 45.494, 9.215),
            'stazione_porta_garibaldi': (45.475, 9.178, 45.495, 9.198),
            'stazione_rogoredo': (45.418, 9.210, 45.445, 9.250),
            'rozzano': (45.360970, 9.120197, 45.39, 9.201908),
            'via_padova': (45.481992, 9.211702, 45.511592, 9.253951),
        },
        zone_mappings={
            'zona_navigli': 'navigli_darsena_colonne',
            'darsena_e_navigli': 'navigli_darsena_colonne',
            'zona_darsena_e_navigli': 'navigli_darsena_colonne',
            'colonne_di_san_lorenzo': 'navigli_darsena_colonne',
            'duomo': 'zona_duomo',
            'zona_stazione_centrale': 'stazione_centrale',
            'zona_porta_garibaldi': 'stazione_porta_garibaldi',
            'zona_rogoredo': 'stazione_rogoredo',
            'stazione_ffss_centrale': 'stazione_centrale',
            'stazione_ffss_porta_garibaldi': 'stazione_porta_garibaldi',
            'stazione_ffss_rogoredo': 'stazione_rogoredo',
            'rozzano_quartiere_dei_fiori': 'rozzano',
            'via_padova': 'via_padova',
        },
        special_cases={
            "duomo": ["Duomo", "Piazza del Duomo", "Piazza Duomo"],
            "scala": ["La Scala", "Teatro alla Scala", "Piazza della Scala"],
            "castello": ["Castello Sforzesco", "Castello"],
            "bocconi": ["Università Bocconi", "Via Bocconi"],
            "centrale": ["Stazione Centrale", "Milano Centrale"],
            "garibaldi": ["Porta Garibaldi", "Stazione Garibaldi"],
            "rogoredo": ["Stazione Rogoredo"],
            "cadorna": ["Cadorna", "Stazione Cadorna"],
            "loreto": ["Piazzale Loreto"],
            "corvetto": ["Corvetto", "Piazzale Luigi Emanuele Corvetto", "Piazzale Corvetto"],
            "gabrio rosa": ["Gabriele Rosa", "Piazzale Gabriele Rosa"],
            "meda": ["Filippo Meda"],
            "diaz": ["Armando Diaz"],
            "porta genova": ["Pta Genova", "P.ta Genova"],
            "xxiv maggio (lato mercato comunale/darsena)": ["Mercato Comunale Ticinese", "Darsena"],
            "corso di porta ticinese (lato numero pari)": ["Corso di Porta Ticinese", "Corso di P.ta Ticinese"],
            " (lato numeri pari)": "",
            "colonne di san lorenzo": ["San Lorenzo"],
            "baden powell": ["B.-Powell", "Baden-Powell", "B. Powell"],
            "giardino robert baden-powell": ["Baden-Powell", "Parco Baden Powell", "Robert Baden-Powell"],
            "padova": ["Viale Padova"],
            #"cordusio": ["Piazzale Cordusio"],
            "dei gerani": ["delle mimose"]
        }
    )

def create_bologna_config() -> CityConfig:
    return CityConfig(
        city_name="Bologna",
        city_pattern="Bologna",
        default_bbox=(44.45, 11.25, 44.55, 11.40),
        
        zone_bboxes={
            'centro_storico': (44.490, 11.335, 44.505, 11.355),   
            'bolognina': (44.500325, 11.330073, 44.524318, 11.365108)
            },
        
        zone_mappings={
            'centro_storico': 'centro_storico',
            'zona_bolognina': 'bolognina'
        },
        
        special_cases={
        }
    )

def create_padova_config() -> CityConfig:
    return CityConfig(
        city_name="Padova",
        city_pattern="Padova",
        default_bbox= (45.364979, 11.825855, 45.445488, 11.925435),
        
        zone_bboxes={
            'stazione_ferroviaria': (45.411442, 11.870238, 45.424275, 11.889816),   
            'arcella': (45.416841, 11.868553, 45.430094, 11.900153)
            },
        
        zone_mappings={
            'centro_storico': 'centro_storico',
            'quartiere_arcella': 'arcella'
        },
        
        special_cases={
            ' (confine nord)': [""],
            ' (confine sud)': [""],
            ' (confine est)': [""],
            ' (confine ovest)': [""],
            'Card. Callegari': ["Cardinale Callegari", "Callegari"],
            "Area antistante all'autostazione": ["autostazione"],
            "antistante all'autostazione": ["autostazione"],
            "antistante": ["autostazione"],
        }
    )

CITIES = {
    'RM': create_rome_config(),
    'MI': create_milan_config(),
    'PD': create_padova_config(),
    'BO': create_bologna_config()
}

CITY_PREFIXES = {
    'Roma': 'RM',
    'Milano': 'MI',
    'Padova': 'PD',
    'Bologna': 'BO'
}



# ========================
# COORDINATE MANAGEMENT
# ========================

def is_coordinate_in_bbox(coord: tuple[float, float], bbox: tuple[float, float, float, float]) -> bool:
    """Check if coordinate is within bounding box"""
    lat, lon = coord
    south, west, north, east = bbox
    return south <= lat <= north and west <= lon <= east

def extract_coordinates_from_geometries(geometries: list[dict]) -> list[tuple[float, float]]:
    """Extract all coordinate points from geometries list"""
    coordinates = []
    
    for geom in geometries:
        geom_type = geom.get('type')
        coords = geom.get('coordinates', [])
        
        if geom_type == 'Point':
            if len(coords) >= 2:
                coordinates.append((coords[0], coords[1]))
                
        elif geom_type == 'LineString':
            for coord in coords:
                if len(coord) >= 2:
                    coordinates.append((coord[0], coord[1]))
                    
        elif geom_type == 'Polygon':
            # Use outer ring only
            if coords and len(coords) > 0:
                for coord in coords[0]:
                    if len(coord) >= 2:
                        coordinates.append((coord[0], coord[1]))
    
    return coordinates

def detect_city_from_coordinates(geometries: list[dict]) -> Optional[str]:
    """Detect city from coordinate geometries using bounding boxes"""
    if not geometries:
        return None
    
    coordinates = extract_coordinates_from_geometries(geometries)
    if not coordinates:
        return None
    
    # Count coordinates in each city's bounding box
    city_scores = {city_code: 0 for city_code in CITIES.keys()}
    
    for coord in coordinates:
        for city_code, city_config in CITIES.items():
            if is_coordinate_in_bbox(coord, city_config.default_bbox):
                city_scores[city_code] += 1
    
    # Return city with highest score
    if max(city_scores.values()) > 0:
        return max(city_scores, key=city_scores.get)
    
    return None

def detect_city_from_street_name(street_name: str) -> Optional[str]:
    """Detect city from street name patterns"""
    street_lower = street_name.lower()
    
    # Check each city's indicators
    for city_code, city_config in CITIES.items():
        # Check zone names
        for zone_name in city_config.zone_bboxes.keys():
            zone_clean = zone_name.replace('_', ' ').replace('stazione', '').strip()
            if zone_clean in street_lower:
                return city_code
        
        # Check zone mappings
        for mapping_key in city_config.zone_mappings.keys():
            mapping_clean = mapping_key.replace('_', ' ').replace('zona', '').replace('stazione', '').strip()
            if mapping_clean in street_lower:
                return city_code
        
        # Check special cases
        for special_key in city_config.special_cases.keys():
            if special_key.lower() in street_lower:
                return city_code
    
    return None

def validate_coordinates_in_zones(street_data: dict, city_code: str) -> bool:
    """Check if street coordinates are within any of the city's zones or default bbox"""
    city_config = CITIES.get(city_code)
    if not city_config:
        return True  # If no config, assume valid
    
    geometries = street_data.get('geometries', [])
    coordinates = extract_coordinates_from_geometries(geometries)
    
    if not coordinates:
        return True  # No coordinates to validate
    
    # Check if any coordinate is within city's default bbox
    for coord in coordinates:
        if is_coordinate_in_bbox(coord, city_config.default_bbox):
            return True
    
    return False

def merge_duplicate_geometries(existing_geometries: list[dict], new_geometries: list[dict]) -> list[dict]:
    """Merge two geometry lists, removing exact duplicates"""
    merged = list(existing_geometries)  # Start with existing
    
    for new_geom in new_geometries:
        # Check if this geometry already exists
        is_duplicate = False
        for existing_geom in merged:
            if (existing_geom.get('type') == new_geom.get('type') and 
                existing_geom.get('coordinates') == new_geom.get('coordinates')):
                is_duplicate = True
                break
        
        if not is_duplicate:
            merged.append(new_geom)
    
    return merged

def clean_and_validate_coordinates():
    """Main function to clean coordinates.json: add city prefixes, remove duplicates, validate zones"""
    
    if not os.path.exists('coordinates.json'):
        print("❌ coordinates.json not found!")
        return
    
    # Create backup
    backup_name = 'coordinates_backup.json'
    shutil.copy('coordinates.json', backup_name)
    print(f"💾 Created backup: {backup_name}")
    
    # Load existing data
    with open('coordinates.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📦 Loaded {len(data)} entries from coordinates.json")
    
    cleaned_data = {}
    stats = {
        'processed': 0,
        'already_prefixed': 0,
        'converted': 0,
        'duplicates_merged': 0,
        'invalid_coordinates': 0,
        'missing_geometries': 0,
        'by_city': {city: 0 for city in CITIES.keys()}
    }
    
    for street_name, street_data in data.items():
        stats['processed'] += 1
        
        # Check if already has city prefix
        has_prefix = any(street_name.startswith(city + '_') for city in CITIES.keys())
        
        if has_prefix:
            # Already has prefix - validate and keep
            city_code = street_name.split('_')[0]
            
            # Validate coordinates are in correct city
            if validate_coordinates_in_zones(street_data, city_code):
                cleaned_data[street_name] = street_data
                stats['already_prefixed'] += 1
                stats['by_city'][city_code] += 1
                print(f"✅ Kept valid: {street_name}")
            else:
                print(f"⚠️ Removed invalid coordinates: {street_name}")
                stats['invalid_coordinates'] += 1
            
        else:
            # Need to add prefix - detect city
            geometries = street_data.get('geometries', [])
            
            if not geometries:
                print(f"⚠️ Skipped - no geometries: {street_name}")
                stats['missing_geometries'] += 1
                continue
            
            # Try to detect city from coordinates first, then name
            city_code = detect_city_from_coordinates(geometries)
            if not city_code:
                city_code = detect_city_from_street_name(street_name)
            
            if not city_code:
                city_code = 'RM'  # Default fallback
                print(f"🔄 Using default city RM for: {street_name}")
            
            # Validate coordinates are reasonable for detected city
            if not validate_coordinates_in_zones(street_data, city_code):
                print(f"⚠️ Removed - coordinates don't match detected city {city_code}: {street_name}")
                stats['invalid_coordinates'] += 1
                continue
            
            new_key = f"{city_code}_{street_name}"
            
            # Check for duplicates
            if new_key in cleaned_data:
                print(f"🔄 Merging duplicate: {new_key}")
                
                # Merge geometries
                existing_geoms = cleaned_data[new_key].get('geometries', [])
                new_geoms = street_data.get('geometries', [])
                
                merged_geoms = merge_duplicate_geometries(existing_geoms, new_geoms)
                cleaned_data[new_key]['geometries'] = merged_geoms
                
                # Merge special coordinates if present
                existing_special = cleaned_data[new_key].get('special_coordinates', [])
                new_special = street_data.get('special_coordinates', [])
                if new_special:
                    # Simple merge for special coordinates (they're usually unique)
                    merged_special = existing_special + new_special
                    cleaned_data[new_key]['special_coordinates'] = merged_special
                
                stats['duplicates_merged'] += 1
                print(f"   🔗 Merged {len(new_geoms)} geometries with {len(existing_geoms)} existing")
                
            else:
                # New entry
                cleaned_data[new_key] = street_data
                stats['converted'] += 1
                stats['by_city'][city_code] += 1
                print(f"🆕 Converted: {street_name} → {new_key} (detected: {city_code})")
    
    # Save cleaned data
    with open('coordinates.json', 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
    
    # Print summary
    print(f"\n🎉 COORDINATE CLEANING COMPLETE!")
    print(f"   📦 Input entries: {len(data)}")
    print(f"   📦 Output entries: {len(cleaned_data)}")
    print(f"   📊 Processed: {stats['processed']}")
    print(f"   ✅ Already prefixed (kept): {stats['already_prefixed']}")
    print(f"   🆕 Converted: {stats['converted']}")
    print(f"   🔗 Duplicates merged: {stats['duplicates_merged']}")
    print(f"   ❌ Invalid coordinates removed: {stats['invalid_coordinates']}")
    print(f"   ❌ Missing geometries skipped: {stats['missing_geometries']}")
    print(f"   📍 By city:")
    for city, count in stats['by_city'].items():
        city_name = CITIES[city].city_name
        print(f"      {city} ({city_name}): {count} entries")
    print(f"   💾 Backup saved as: {backup_name}")

def validate_city_zones():
    """Validate that all coordinates in the file are in their correct city zones"""
    
    if not os.path.exists('coordinates.json'):
        print("❌ coordinates.json not found!")
        return
    
    with open('coordinates.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"🔍 Validating {len(data)} entries...")
    
    validation_stats = {
        'total': len(data),
        'valid': 0,
        'invalid': 0,
        'no_prefix': 0,
        'by_city': {city: {'valid': 0, 'invalid': 0} for city in CITIES.keys()}
    }
    
    invalid_entries = []
    
    for street_name, street_data in data.items():
        # Check if has city prefix
        has_prefix = any(street_name.startswith(city + '_') for city in CITIES.keys())
        
        if not has_prefix:
            validation_stats['no_prefix'] += 1
            invalid_entries.append(f"No city prefix: {street_name}")
            continue
        
        city_code = street_name.split('_')[0]
        
        if validate_coordinates_in_zones(street_data, city_code):
            validation_stats['valid'] += 1
            validation_stats['by_city'][city_code]['valid'] += 1
        else:
            validation_stats['invalid'] += 1
            validation_stats['by_city'][city_code]['invalid'] += 1
            invalid_entries.append(f"Invalid coordinates for {city_code}: {street_name}")
    
    print(f"\n📊 VALIDATION RESULTS:")
    print(f"   ✅ Valid entries: {validation_stats['valid']}")
    print(f"   ❌ Invalid entries: {validation_stats['invalid']}")
    print(f"   ⚠️ No city prefix: {validation_stats['no_prefix']}")
    print(f"   📍 By city:")
    for city, counts in validation_stats['by_city'].items():
        city_name = CITIES[city].city_name
        total = counts['valid'] + counts['invalid']
        print(f"      {city} ({city_name}): {counts['valid']}/{total} valid")
    
    if invalid_entries:
        print(f"\n❌ Invalid entries found:")
        for entry in invalid_entries[:10]:  # Show first 10
            print(f"   {entry}")
        if len(invalid_entries) > 10:
            print(f"   ... and {len(invalid_entries) - 10} more")

if __name__ == "__main__":
    print("🚀 Starting coordinate cleaning and validation...")
    
    # Main cleaning process
    clean_and_validate_coordinates()
    
    print("\n" + "="*50)
    
    # Validation check
    validate_city_zones()
    
    print("\n✨ Process complete!")