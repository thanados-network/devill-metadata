import sys
import os
import json
from scripts.db_connect import connect

# Add project root to path to be able to import db_connect
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def export_geojson():
    """
    Fetches archaeological object data from devill.entitiestmp and saves it as a GeoJSON file.
    Filters for openatlas_class_name = 'place' and geom IS NOT NULL.
    """
    conn = connect()
    if conn is None:
        return

    # Define project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    output_path = os.path.join(project_root, 'data', 'archaeological_objects', 'archaeological_objects.geojson')
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        cur = conn.cursor()
        
        # Select data as GeoJSON features
        # We use json_build_object to create the GeoJSON structure directly in SQL for efficiency
        sql = """
        SELECT jsonb_build_object(
            'type',     'Feature',
            'id',       e.child_id,
            'geometry', e.geom::jsonb,
            'properties', jsonb_build_object(
                'name', e.child_name,
                'type', m.name,
                'class', e.openatlas_class_name,
                'description', e.description,
                'devill_endpoint', 'https://devill.oegmn.or.at/entity/' || e.child_id
            )
        )
        FROM devill.entitiestmp e
        LEFT JOIN devill.maintype m ON e.child_id = m.entity_id
        WHERE e.openatlas_class_name = 'place' 
          AND e.geom IS NOT NULL;
        """
        
        print("Fetching GeoJSON data from devill.entitiestmp...")
        cur.execute(sql)
        rows = cur.fetchall()

        features = [row[0] for row in rows]
        
        geojson_data = {
            "type": "FeatureCollection",
            "features": features
        }

        print(f"Writing GeoJSON export to {output_path}...")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(geojson_data, f, ensure_ascii=False, indent=2)
            
        print(f"Export completed successfully. Total features: {len(features)}")
        cur.close()
    except Exception as e:
        print(f"Error during GeoJSON export: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    export_geojson()
