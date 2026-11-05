import sys
import os
import json
import xml.etree.ElementTree as ET

# Add project root to path to be able to import db_connect
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.db_connect import connect
from scripts.bbox_utils import load_bounding_boxes

def export_files_geojson():
    """
    Saves all files that have a georeferenced bounding box (web.map_overlay) as a
    GeoJSON FeatureCollection in data/files/file-metadata.geojson.
    Each feature is the image extent as Polygon (lon, lat) with basic file metadata.
    """
    conn = connect()
    if conn is None:
        return

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    output_path = os.path.join(project_root, 'data', 'files', 'file-metadata.geojson')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    ns = {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'edm': 'http://www.europeana.eu/schemas/edm/',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'dcterms': 'http://purl.org/dc/terms/',
        'ore': 'http://www.openarchives.org/ore/terms/'
    }

    try:
        cur = conn.cursor()

        print("Fetching bounding boxes from web.map_overlay...")
        bounding_boxes = load_bounding_boxes(cur)

        print("Fetching data from devill_meta.xml_export...")
        cur.execute("SELECT id, edm FROM devill_meta.xml_export;")
        rows = cur.fetchall()

        features = []
        found_ids = set()
        for db_id, edm_xml in rows:
            bbox = bounding_boxes.get(db_id)
            if not bbox or not edm_xml:
                continue

            properties = {
                'title': None,
                'description_de': None,
                'description_en': None,
                'created': None,
                'is_shown_at': None,
                'is_shown_by': None,
                'api_endpoint': f"https://thanados.openatlas.eu/api/entity/{db_id}",
                'bounding_box': bbox['raw'],
            }

            try:
                root = ET.fromstring(edm_xml)
                cho = root.find('.//edm:ProvidedCHO', ns)
                agg = root.find('.//ore:Aggregation', ns)

                if cho is not None:
                    title = cho.find('dc:title', ns)
                    if title is not None:
                        properties['title'] = title.text
                    for desc in cho.findall('dc:description', ns):
                        lang = desc.get('{http://www.w3.org/XML/1998/namespace}lang')
                        if lang == 'en':
                            properties['description_en'] = desc.text
                        elif lang == 'de' or not properties['description_de']:
                            properties['description_de'] = desc.text
                    created = cho.find('dcterms:created', ns)
                    if created is not None:
                        properties['created'] = created.text

                if agg is not None:
                    at = agg.find('edm:isShownAt', ns)
                    if at is not None:
                        properties['is_shown_at'] = at.get('{%s}resource' % ns['rdf'])
                    by = agg.find('edm:isShownBy', ns)
                    if by is not None:
                        properties['is_shown_by'] = by.get('{%s}resource' % ns['rdf'])
            except Exception as parse_err:
                print(f"Warning: Could not parse metadata of file {db_id}: {parse_err}")

            found_ids.add(db_id)
            features.append({
                'type': 'Feature',
                'id': db_id,
                'geometry': bbox['geometry'],
                'properties': properties
            })

        for image_id in sorted(set(bounding_boxes) - found_ids):
            print(f"Warning: No file with id {image_id} found in devill_meta.xml_export, skipping.")

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
        print(f"Error during file GeoJSON export: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    export_files_geojson()
