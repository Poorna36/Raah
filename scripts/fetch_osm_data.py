"""
Fetch NH-275 OpenStreetMap data via Overpass API
Downloads highway data and saves as GeoJSON for the RAAH system
"""

import requests
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Overpass API endpoint
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# NH-275 corridor bounding box (approximate)
# Mysore to Bangalore corridor
BOUNDING_BOX = {
    "south": 12.2,   # Southern boundary
    "west": 76.5,    # Western boundary  
    "north": 13.2,   # Northern boundary
    "east": 77.8     # Eastern boundary
}

def fetch_nh275_data():
    """
    Fetch NH-275 highway data from OpenStreetMap using Overpass API
    """
    
    # Overpass QL query for NH-275
    # Looking for highways with ref=NH 275 or NH275
    query = f"""
    [out:json][timeout:60];
    (
      // Search for highways with NH 275 reference
      way["highway"]["ref"~"NH.?275",i]({BOUNDING_BOX['south']},{BOUNDING_BOX['west']},{BOUNDING_BOX['north']},{BOUNDING_BOX['east']});
      // Also search for roads that might be tagged as NH275 without space
      way["highway"]["ref"="NH275"]({BOUNDING_BOX['south']},{BOUNDING_BOX['west']},{BOUNDING_BOX['north']},{BOUNDING_BOX['east']});
      // Include some major connecting roads
      way["highway"~"motorway|trunk|primary"]["ref"]({BOUNDING_BOX['south']},{BOUNDING_BOX['west']},{BOUNDING_BOX['north']},{BOUNDING_BOX['east']});
    );
    out body;
    >;
    out skel qt;
    """
    
    logger.info("Fetching NH-275 data from OpenStreetMap...")
    
    try:
        response = requests.post(OVERPASS_URL, data={'data': query})
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Received {len(data.get('elements', []))} elements from OSM")
        
        return data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch OSM data: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse OSM response: {e}")
        raise


def convert_to_geojson(osm_data):
    """
    Convert OSM data to GeoJSON format
    """
    features = []
    
    # Process ways (highways)
    ways = [elem for elem in osm_data.get('elements', []) if elem.get('type') == 'way']
    nodes = {elem['id']: elem for elem in osm_data.get('elements', []) if elem.get('type') == 'node'}
    
    logger.info(f"Processing {len(ways)} ways and {len(nodes)} nodes")
    
    for way in ways:
        # Skip if no geometry data
        if 'geometry' not in way and 'nodes' not in way:
            continue
            
        # Get coordinates
        coordinates = []
        if 'geometry' in way:
            # Already has geometry from Overpass
            for geom in way['geometry']:
                coordinates.append([geom['lon'], geom['lat']])
        elif 'nodes' in way:
            # Build geometry from node references
            for node_id in way['nodes']:
                if node_id in nodes:
                    node = nodes[node_id]
                    coordinates.append([node['lon'], node['lat']])
        
        if not coordinates:
            continue
            
        # Create feature properties
        properties = {
            'osm_id': way['id'],
            'highway': way.get('tags', {}).get('highway'),
            'ref': way.get('tags', {}).get('ref'),
            'name': way.get('tags', {}).get('name'),
            'lanes': way.get('tags', {}).get('lanes'),
            'maxspeed': way.get('tags', {}).get('maxspeed'),
            'surface': way.get('tags', {}).get('surface'),
            'oneway': way.get('tags', {}).get('oneway'),
        }
        
        # Filter for NH-275 specifically
        ref = properties.get('ref', '')
        if '275' not in ref and 'NH' not in ref:
            # Include major highways anyway for context
            if properties['highway'] not in ['motorway', 'trunk', 'primary']:
                continue
        
        # Create GeoJSON feature
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'LineString',
                'coordinates': coordinates
            },
            'properties': properties
        }
        
        features.append(feature)
    
    # Create GeoJSON collection
    geojson = {
        'type': 'FeatureCollection',
        'features': features,
        'metadata': {
            'source': 'OpenStreetMap via Overpass API',
            'query': 'NH-275 corridor',
            'timestamp': requests.utils.default_user_agent(),
            'feature_count': len(features)
        }
    }
    
    logger.info(f"Created GeoJSON with {len(features)} features")
    return geojson


def save_geojson(geojson_data, output_path):
    """
    Save GeoJSON data to file
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(geojson_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved GeoJSON to {output_path}")
        
    except IOError as e:
        logger.error(f"Failed to save GeoJSON file: {e}")
        raise


def main():
    """
    Main function to fetch and save NH-275 OSM data
    """
    output_path = Path("nh275-osm.geojson")
    
    try:
        # Fetch OSM data
        osm_data = fetch_nh275_data()
        
        # Convert to GeoJSON
        geojson_data = convert_to_geojson(osm_data)
        
        # Save to file
        save_geojson(geojson_data, output_path)
        
        # Print summary
        print(f"\n=== NH-275 OSM Data Summary ===")
        print(f"Features saved: {len(geojson_data['features'])}")
        
        # Show some highway refs found
        refs_found = set()
        for feature in geojson_data['features']:
            ref = feature['properties'].get('ref')
            if ref:
                refs_found.add(ref)
        
        print(f"Highway references found: {sorted(refs_found)}")
        print(f"Output file: {output_path.absolute()}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to fetch and save NH-275 data: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)