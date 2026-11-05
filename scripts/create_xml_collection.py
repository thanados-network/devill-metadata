import sys
import os
import psycopg2

# Add project root to path to be able to import db_connect
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.db_connect import connect
from scripts.bbox_utils import load_bounding_boxes, WKT_LITERAL_DATATYPE

DCAT_NS = 'http://www.w3.org/ns/dcat#'

def add_bounding_boxes(conn, cur):
    """
    Inserts a dcat:bbox element (WKT polygon, lon lat) before </edm:ProvidedCHO>
    for every file in devill_meta.xml_export that has an entry in web.map_overlay.
    Invalid or unmatched entries are skipped with a warning.
    """
    boxes = load_bounding_boxes(cur)
    print(f"Adding bounding boxes for {len(boxes)} overlay(s)...")
    updated = 0
    for image_id, box in boxes.items():
        element = (
            f'<dcat:bbox rdf:datatype="{WKT_LITERAL_DATATYPE}" '
            f'xmlns:dcat="{DCAT_NS}">{box["wkt"]}</dcat:bbox>'
        )
        try:
            cur.execute(
                """
                UPDATE devill_meta.xml_export
                SET edm = replace(edm::text, '</edm:ProvidedCHO>', %s || '</edm:ProvidedCHO>')::xml
                WHERE id = %s AND edm::text LIKE '%%</edm:ProvidedCHO>%%'
                """,
                (element, image_id)
            )
        except Exception as e:
            print(f"Warning: Could not add bounding box for id {image_id}: {e}")
            conn.rollback()
            continue
        if cur.rowcount:
            conn.commit()
            updated += 1
        else:
            print(f"Warning: No file with id {image_id} found in devill_meta.xml_export, skipping bounding box.")
    conn.commit()
    print(f"Bounding boxes added to {updated} file(s).")

def create_xml_collection():
    """
    Creates the devill_meta.xml_export table by selecting data from devill_meta.xml_data
    and replacing the local URL with the production URL in the edm XML field.
    Afterwards a dcat:bbox (WKT polygon) is added to the edm:ProvidedCHO of every file
    that has a georeferenced overlay in web.map_overlay.
    """
    conn = connect()
    if conn is None:
        return

    try:
        cur = conn.cursor()
        
        # Ensure the schema exists
        cur.execute("CREATE SCHEMA IF NOT EXISTS devill_meta;")

        # SQL to create the table with the URL replacement
        sql = """
        DROP TABLE IF EXISTS devill_meta.xml_export;
        CREATE TABLE devill_meta.xml_export AS
        SELECT
            id,
            filename,
            extension,
            mimetype,
            last_update,
            replace(
                    edm::text,
                    'http://127.0.0.1:5000',
                    'https://devill.oegmn.or.at'
            )::xml AS edm
        FROM devill_meta.xml_data
        WHERE id NOT IN (207673, 207672) --Overview Lists that contain all sites (A-L and M-Z);
        """
        
        print("Executing SQL to create devill_meta.xml_export...")
        cur.execute(sql)
        conn.commit()
        print("Table devill_meta.xml_export created successfully.")

        add_bounding_boxes(conn, cur)

        cur.close()
    except Exception as e:
        print(f"Error creating table: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_xml_collection()
