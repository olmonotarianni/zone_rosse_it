"""
simple_embed_coordinates.py
Simple script to embed coordinates into the baseline Rome viewer
"""

import json
import os

def embed_coordinates():
    """Embed coordinates into the baseline HTML viewer"""
    
    # File paths
    coordinates_file = 'enhanced_coordinates.json'  # or 'enhanced_coordinates.json' 
    baseline_html = 'rome_viewer.html'  # The clean HTML we just created
    output_file = 'rome_viewer_embedded.html'
    
    # Load coordinates
    try:
        with open(coordinates_file, 'r', encoding='utf-8') as f:
            coordinates_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ {coordinates_file} not found.")
        print("Available files:")
        for file in os.listdir('.'):
            if file.endswith('.json'):
                print(f"  - {file}")
        return
    
    # Load the baseline HTML
    try:
        with open(baseline_html, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"❌ {baseline_html} not found.")
        print("Please save the baseline HTML first.")
        return
    
    # Convert coordinates to JavaScript
    js_data = json.dumps(coordinates_data, indent=12)
    
    # Find and replace the fetch call with embedded data
    fetch_line = "coordinatesData = await fetch('./coordinates.json').then(response => response.json());"
    embedded_line = f"coordinatesData = {js_data};"
    
    if fetch_line in html_content:
        html_content = html_content.replace(fetch_line, embedded_line)
        print("✅ Replaced fetch with embedded data")
    else:
        print("❌ Could not find fetch line to replace")
        print("Looking for alternative patterns...")
        
        # Try other patterns
        patterns = [
            "coordinatesData = await fetch('./coordinates.json')",
            "coordinatesData = await fetch('coordinates.json')",
            "await fetch('./coordinates.json')",
            "await fetch('coordinates.json')"
        ]
        
        replaced = False
        for pattern in patterns:
            if pattern in html_content:
                # Find the full line containing this pattern
                lines = html_content.split('\n')
                for i, line in enumerate(lines):
                    if pattern in line:
                        # Replace the entire line
                        indent = len(line) - len(line.lstrip())
                        lines[i] = ' ' * indent + embedded_line
                        html_content = '\n'.join(lines)
                        print(f"✅ Replaced pattern: {pattern}")
                        replaced = True
                        break
                break
        
        if not replaced:
            print("❌ Could not find any coordinate loading pattern")
            return
    
    # Save the embedded HTML
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Created {output_file}")
    
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
    
    success_rate = (streets_with_coords / total_streets * 100) if total_streets > 0 else 0
    
    print(f"\n📊 Embedded data summary:")
    print(f"   📋 {total_ordinances} ordinances")
    print(f"   🏛️ {streets_with_coords}/{total_streets} streets with coordinates")
    print(f"   ✅ {success_rate:.1f}% success rate")
    
    print(f"\n🎯 Next steps:")
    print(f"   1. Open {output_file} in your browser")
    print(f"   2. Click 'Toggle' buttons to show/hide zones")
    print(f"   3. Click 'Details' to see street lists")
    print(f"   4. Click individual streets to focus on them")

if __name__ == "__main__":
    print("🗺️ Simple Rome Ordinances Embedder")
    print("=" * 40)
    embed_coordinates()