"""
embed_coordinates.py
Simple script to embed coordinates.json directly into the HTML file.
This avoids CORS issues when opening HTML files directly.
"""

import json
import os

coordinates_file = 'coordinates.json'
html_file = 'rome-viewer.html'


def embed_coordinates_in_html():
    """Embed coordinates directly in HTML to avoid CORS issues."""
    
    # File paths - adjust these to your actual paths
    output_file = 'rome_viewer_embedded.html'
    
    # Load coordinates
    try:
        with open(coordinates_file, 'r', encoding='utf-8') as f:
            coordinates_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ {coordinates_file} not found. Run coordinates_fetcher.py first.")
        return
    
    # Convert to JavaScript
    js_data = json.dumps(coordinates_data, indent=8)
    
    # Read the HTML template
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"❌ {html_file} not found.")
        return
    
    # Create the new loadCoordinates function with embedded data
    new_load_function = f"""        // Coordinates data embedded directly (no file loading needed)
        async function loadCoordinates() {{
            coordinatesData = {js_data};
            generateInterface();
            console.log('✅ Embedded coordinates loaded successfully');
        }}"""
    
    # Find and replace the loadCoordinates function
    start_marker = "        // Load coordinates from JSON file"
    
    start_idx = html_content.find(start_marker)
    if start_idx == -1:
        print("❌ Could not find loadCoordinates function in HTML")
        return
    
    # Find the end of the function (look for the closing brace)
    brace_count = 0
    in_function = False
    end_idx = start_idx
    
    for i, char in enumerate(html_content[start_idx:], start_idx):
        if char == '{':
            brace_count += 1
            in_function = True
        elif char == '}':
            brace_count -= 1
            if in_function and brace_count == 0:
                end_idx = i + 1
                break
    
    # Replace the function
    new_html = (
        html_content[:start_idx] +
        new_load_function +
        html_content[end_idx:]
    )
    
    # Save the new HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(new_html)
    
    print(f"✅ Created {output_file}")
    print("🌐 You can now open this file directly in your browser!")
    print("📊 No HTTP server needed, no CORS issues!")
    
    # Print summary
    total_ordinances = len(coordinates_data)
    total_streets = 0
    streets_with_coords = 0
    
    for ord_data in coordinates_data.values():
        for streets in ord_data['zones'].values():
            for street, coords in streets.items():
                total_streets += 1
                if coords:
                    streets_with_coords += 1
    
    print(f"\n📈 Embedded data summary:")
    print(f"   📋 {total_ordinances} ordinances")
    print(f"   🏛️ {streets_with_coords}/{total_streets} streets with coordinates")
    print(f"   📍 {len(coordinates_data)} zone definitions")
    print(f"   🗺️ 4 bounding boxes (Rome, Esquilino, Tuscolano, Valle Aurelia)")
    
    success_rate = (streets_with_coords / total_streets * 100) if total_streets > 0 else 0
    print(f"   ✅ {success_rate:.1f}% success rate")

def create_coordinates_summary():
    """Create a summary of what coordinates were found."""
        
    try:
        with open(coordinates_file, 'r', encoding='utf-8') as f:
            coordinates_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ {coordinates_file} not found.")
        return
    
    print("\n🔍 Detailed coordinates summary:")
    print("=" * 50)
    
    for ord_id, ord_data in coordinates_data.items():
        metadata = ord_data.get('metadata', {})
        protocol = metadata.get('protocol', ord_id)
        date = metadata.get('date', 'Unknown date')
        
        print(f"\n📋 Ordinanza {protocol} ({date})")
        
        for zone_name, streets in ord_data['zones'].items():
            total_streets = len(streets)
            streets_with_coords = sum(1 for coords in streets.values() if coords is not None)
            
            print(f"  📍 {zone_name}: {streets_with_coords}/{total_streets} streets")
            
            # Show missing streets
            missing_streets = [name for name, coords in streets.items() if coords is None]
            if missing_streets:
                print(f"     ❌ Missing: {', '.join(missing_streets[:3])}")
                if len(missing_streets) > 3:
                    print(f"     ... and {len(missing_streets) - 3} more")

if __name__ == "__main__":
    print("🗺️ Rome Ordinances - Coordinate Embedder")
    print("=" * 40)
    
    embed_coordinates_in_html()
    create_coordinates_summary()
    
    print(f"\n🎯 Next steps:")
    print(f"   1. Open rome_viewer_embedded.html in your browser")
    print(f"   2. Toggle bounding boxes to see search areas")
    print(f"   3. Click on streets to see their coordinates")
    print(f"   4. Enjoy exploring Rome's zone rosse! 🇮DIOCAN")