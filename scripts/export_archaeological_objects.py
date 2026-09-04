import sys
import os
import csv

# Add project root to path to be able to import db_connect
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.db_connect import connect

def export_archaeological_objects():
    """
    Fetches archaeological object data from devill.entitiestmp and saves it as a CSV file
    in data/archaeological_objects/archaeological_objects.csv.
    Filters for child_id != 0 and renames columns as requested.
    """
    conn = connect()
    if conn is None:
        return

    # Define project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    output_path = os.path.join(project_root, 'data', 'archaeological_objects', 'archaeological_objects.csv')
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        cur = conn.cursor()
        
        # Columns to select and rename
        # child_name -> name
        # child_id -> id
        # openatlas_class_name -> class
        # geom -> geometry
        
        sql = """
        SELECT 
            parent_id,
            child_name AS name,
            child_id AS id,
            description,
            begin_from,
            begin_to,
            end_from,
            end_to,
            openatlas_class_name AS class,
            geom AS geometry,
            lon,
            lat
        FROM devill.entitiestmp
        WHERE child_id != 0;
        """
        
        print("Fetching data from devill.entitiestmp...")
        cur.execute(sql)
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]

        print(f"Writing CSV export to {output_path}...")
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(colnames)
            writer.writerows(rows)
            
        print(f"Export completed successfully. Total records: {len(rows)}")
        cur.close()
    except Exception as e:
        print(f"Error during CSV export: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    export_archaeological_objects()
