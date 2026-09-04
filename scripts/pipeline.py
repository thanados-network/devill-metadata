import sys
import os
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.create_xml_collection import create_xml_collection
from scripts.export_rdf import export_rdf_collection
from scripts.export_turtle import export_turtle
from scripts.export_jsonld import export_jsonld
from scripts.export_csv import export_csv
from scripts.export_archaeological_objects import export_archaeological_objects
from scripts.export_crossrefs import export_crossrefs

def run_pipeline():
    """
    Runs the entire metadata processing pipeline:
    1. Create/Update database collection table
    2. Export to RDF/XML
    3. Export to Turtle
    4. Export to JSON-LD
    5. Export to CSV (Metadata)
    6. Export to CSV (Archaeological Objects)
    7. Export to CSV (Cross-References)
    """
    start_time = time.time()
    print("=== Starting DeVill Metadata Pipeline ===")

    try:
        # Step 1: Database Setup
        print("\n--- Step 1: Creating XML collection in database ---")
        create_xml_collection()

        # Step 2: RDF Export
        print("\n--- Step 2: Exporting RDF/XML ---")
        export_rdf_collection()

        # Step 3: Turtle Export
        print("\n--- Step 3: Exporting Turtle ---")
        export_turtle()

        # Step 4: JSON-LD Export
        print("\n--- Step 4: Exporting JSON-LD ---")
        export_jsonld()

        # Step 5: CSV Export (Metadata)
        print("\n--- Step 5: Exporting CSV (Metadata) ---")
        export_csv()

        # Step 6: CSV Export (Archaeological Objects)
        print("\n--- Step 6: Exporting CSV (Archaeological Objects) ---")
        export_archaeological_objects()

        # Step 7: CSV Export (Cross-References)
        print("\n--- Step 7: Exporting CSV (Cross-References) ---")
        export_crossrefs()

        end_time = time.time()
        duration = end_time - start_time
        print(f"\n=== Pipeline finished successfully in {duration:.2f} seconds ===")

    except Exception as e:
        print(f"\n!!! Pipeline failed: {e} !!!")
        sys.exit(1)

if __name__ == "__main__":
    run_pipeline()
