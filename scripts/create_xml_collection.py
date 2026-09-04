import sys
import os
import psycopg2

# Add project root to path to be able to import db_connect
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.db_connect import connect

def create_xml_collection():
    """
    Creates the devill_meta.xml_export table by selecting data from devill_meta.xml_data
    and replacing the local URL with the production URL in the edm XML field.
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
