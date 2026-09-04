import pandas as pd
import requests
import rdflib
import time
import os
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_data():
    csv_path = 'data/archaeological_objects/archaeological_objects.csv'
    output_dir = 'data/archaeological_objects/'
    base_url = 'https://thanados.openatlas.eu/api/0.4/query/'
    
    logging.info(f"Reading CSV from {csv_path}")
    df = pd.read_csv(csv_path)
    
    # Extract IDs, drop NaNs, and convert to integer/string
    ids = df['id'].dropna().astype(int).astype(str).tolist()
    logging.info(f"Extracted {len(ids)} IDs from the CSV.")
    
    batch_size = 100
    batches = [ids[i:i + batch_size] for i in range(0, len(ids), batch_size)]
    logging.info(f"Total batches to process: {len(batches)} (Batch size: {batch_size})")
    
    all_results = []
    common_context = "https://linked.art/ns/v1/linked-art.json"
    
    logging.info("--- Fetching JSON-LD (loud) data ---")
    for i, batch in enumerate(batches):
        logging.info(f"Fetching batch {i+1}/{len(batches)}")
        params = [('limit', batch_size), ('format', 'loud')] + [('entities', ent_id) for ent_id in batch]
        
        retries = 3
        for attempt in range(retries):
            try:
                response = requests.get(base_url, params=params, timeout=60)
                response.raise_for_status()
                
                data = response.json()
                if 'results' in data:
                    for item in data['results']:
                        if '@context' in item:
                            common_context = item.pop('@context')
                        
                        # Cleanup invalid equivalents
                        if 'equivalent' in item:
                            valid_equivalents = []
                            for eq in item['equivalent']:
                                eq_id = str(eq.get('id', ''))
                                if eq_id.startswith('http'):
                                    valid_equivalents.append(eq)
                            if valid_equivalents:
                                item['equivalent'] = valid_equivalents
                            else:
                                del item['equivalent']

                        # Find the Internal Database ID
                        internal_id = None
                        if 'identified_by' in item:
                            for ident in item['identified_by']:
                                if ident.get('_label') == 'Internal Database ID':
                                    content = ident.get('content', '')
                                    if content:
                                        internal_id = content.split('/')[-1]
                                        break
                        
                        # Add the equivalent field
                        if internal_id:
                            equiv_obj = {
                                "id": f"https://devill.oegmn.or.at/entity/{internal_id}",
                                "type": item.get("type"),
                                "_label": item.get("_label")
                            }
                            if "equivalent" not in item:
                                item["equivalent"] = []
                            item["equivalent"].append(equiv_obj)
                            
                        all_results.append(item)
                break
            except requests.exceptions.RequestException as e:
                logging.warning(f"Error on batch {i+1} (attempt {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(2)
                else:
                    logging.error(f"Failed batch {i+1} after {retries} attempts.")
                    raise
            except json.JSONDecodeError as e:
                logging.warning(f"JSON Parse Error on batch {i+1} (attempt {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(2)
                else:
                    logging.error(f"Failed batch {i+1} due to JSON decode error.")
                    raise
        
        time.sleep(0.5)
        
    final_jsonld = {
        "@context": common_context,
        "@graph": all_results
    }
        
    jsonld_file = os.path.join(output_dir, 'archaeological_objects.jsonld')
    logging.info(f"Saving enriched JSON-LD to {jsonld_file}...")
    with open(jsonld_file, 'w', encoding='utf-8') as f:
        json.dump(final_jsonld, f, ensure_ascii=False, indent=2)
    logging.info(f"Finished saving {jsonld_file}.")
    
    # Generate TTL and RDF using rdflib
    logging.info("Parsing enriched JSON-LD with rdflib...")
    graph = rdflib.Graph()
    # Serialize to string and parse to avoid file IO issues with rdflib json-ld parser
    graph.parse(data=json.dumps(final_jsonld), format='json-ld')
    
    ttl_file = os.path.join(output_dir, 'archaeological_objects.ttl')
    logging.info(f"Saving Turtle to {ttl_file}...")
    graph.serialize(destination=ttl_file, format='turtle')
    logging.info(f"Finished saving {ttl_file}.")
    
    rdf_file = os.path.join(output_dir, 'archaeological_objects.rdf')
    logging.info(f"Saving XML to {rdf_file}...")
    graph.serialize(destination=rdf_file, format='xml')
    logging.info(f"Finished saving {rdf_file}.")

if __name__ == '__main__':
    fetch_data()
