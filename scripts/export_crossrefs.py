import sys
import os
import csv

# Add project root to path to be able to import db_connect
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.db_connect import connect

def export_crossrefs():
    """
    Fetches file-to-object cross-references from devill.files and saves them as a CSV file
    in data/crossrefs/object_file_relation.csv.
    Checks if all parent_ids exist in the archaeological objects table.
    """
    conn = connect()
    if conn is None:
        return

    # Define project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    output_path = os.path.join(project_root, 'data', 'crossrefs', 'object_file_relation.csv')
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        cur = conn.cursor()
        
        # 1. Fetch data for CSV
        sql = """
        SELECT 
            f.id AS file_id,
            f.filename,
            f.name AS file_label,
            f.parent_id AS object_id,
            e.child_name AS object_name
        FROM devill.files f
        LEFT JOIN devill.entitiestmp e ON f.parent_id = e.child_id;
        """
        
        print("Fetching cross-references from devill.files with names...")
        cur.execute(sql)
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]

        # 2. Verify parent_ids against objects
        # We check if there are any parent_ids in devill.files that ARE NOT in devill.entitiestmp
        verify_sql = """
        SELECT DISTINCT parent_id 
        FROM devill.files 
        WHERE parent_id NOT IN (SELECT child_id FROM devill.entitiestmp)
        AND parent_id IS NOT NULL;
        """
        cur.execute(verify_sql)
        missing_parents = cur.fetchall()
        
        if missing_parents:
            print(f"Warning: Found {len(missing_parents)} parent_ids in devill.files that do not exist in devill.entitiestmp.")
            # Optionally list some
            # for p in missing_parents[:5]:
            #     print(f"  Missing: {p[0]}")
        else:
            print("Verification successful: All parent_ids exist in the objects table.")

        # 3. Write CSV
        print(f"Writing CSV export to {output_path}...")
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(colnames)
            writer.writerows(rows)
            
        print(f"Export completed successfully. Total records: {len(rows)}")
        cur.close()
    except Exception as e:
        print(f"Error during crossref export: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    export_crossrefs()
