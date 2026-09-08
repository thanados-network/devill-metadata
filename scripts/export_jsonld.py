import sys
import os
import xml.etree.ElementTree as ET
import json

# Add project root to path to be able to import db_connect
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.db_connect import connect

def export_jsonld():
    """
    Fetches data from devill_meta.xml_export and saves it as a JSON-LD file
    in data/files/rdf/file-metadata.jsonld.
    """
    conn = connect()
    if conn is None:
        return

    # Define project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    output_path = os.path.join(project_root, 'data', 'files', 'file-metadata.jsonld')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        cur = conn.cursor()
        sql = "SELECT edm FROM devill_meta.xml_export;"
        print("Fetching data from devill_meta.xml_export...")
        cur.execute(sql)
        rows = cur.fetchall()

        # Define JSON-LD context
        context = {
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "edm": "http://www.europeana.eu/schemas/edm/",
            "dc": "http://purl.org/dc/elements/1.1/",
            "dcterms": "http://purl.org/dc/terms/",
            "ore": "http://www.openarchives.org/ore/terms/",
            "cc": "http://creativecommons.org/ns#",
            "odrl": "http://www.w3.org/ns/odrl/2/",
            "svcs": "http://rdfs.org/sioc/services#",
            "doap": "http://usefulinc.com/ns/doap#",
            "skos": "http://www.w3.org/2004/02/skos/core#",
            "type": "@type",
            "id": "@id"
        }

        # Namespaces for parsing XML
        ns = {
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'edm': 'http://www.europeana.eu/schemas/edm/',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'dcterms': 'http://purl.org/dc/terms/',
            'ore': 'http://www.openarchives.org/ore/terms/'
        }

        jsonld_graph = []

        for row in rows:
            edm_xml = row[0]
            if not edm_xml:
                continue

            try:
                root = ET.fromstring(edm_xml)
                
                # Process ProvidedCHO
                cho = root.find('.//edm:ProvidedCHO', ns)
                cho_obj = None
                if cho is not None:
                    cho_obj = {
                        "id": cho.get('{%s}about' % ns['rdf']),
                        "type": "edm:ProvidedCHO"
                    }
                    
                    for child in list(cho):
                        tag = child.tag.split('}')[-1]
                        prefix = None
                        for p, uri in ns.items():
                            if child.tag.startswith('{%s}' % uri):
                                prefix = p
                                break
                        
                        if not prefix: continue
                        
                        prop = f"{prefix}:{tag}"
                        resource = child.get('{%s}resource' % ns['rdf'])
                        lang = child.get('{http://www.w3.org/XML/1998/namespace}lang')
                        
                        value = None
                        if resource:
                            value = {"id": resource}
                        else:
                            text = child.text if child.text else ""
                            if lang:
                                value = {"@value": text, "@language": lang}
                            else:
                                value = text
                        
                        # Handle multiple values for same property
                        if prop in cho_obj:
                            if isinstance(cho_obj[prop], list):
                                cho_obj[prop].append(value)
                            else:
                                cho_obj[prop] = [cho_obj[prop], value]
                        else:
                            cho_obj[prop] = value

                # Process Aggregation
                agg = root.find('.//ore:Aggregation', ns)
                if agg is not None:
                    agg_obj = {
                        "id": agg.get('{%s}about' % ns['rdf']),
                        "type": "ore:Aggregation"
                    }
                    
                    for child in list(agg):
                        tag = child.tag.split('}')[-1]
                        prefix = None
                        for p, uri in ns.items():
                            if child.tag.startswith('{%s}' % uri):
                                prefix = p
                                break
                        
                        if not prefix: continue
                        
                        prop = f"{prefix}:{tag}"
                        resource = child.get('{%s}resource' % ns['rdf'])
                        
                        value = None
                        # Special handling for aggregatedCHO to embed the ProvidedCHO object
                        if tag == 'aggregatedCHO' and prefix == 'edm' and cho_obj:
                            value = cho_obj
                        elif resource:
                            value = {"id": resource}
                        else:
                            value = child.text if child.text else ""
                        
                        if prop in agg_obj:
                            if isinstance(agg_obj[prop], list):
                                agg_obj[prop].append(value)
                            else:
                                agg_obj[prop] = [agg_obj[prop], value]
                        else:
                            agg_obj[prop] = value
                            
                    jsonld_graph.append(agg_obj)
                elif cho_obj:
                    # Fallback if no aggregation but CHO exists
                    jsonld_graph.append(cho_obj)

            except Exception as parse_err:
                print(f"Error parsing row: {parse_err}")

        # Final JSON-LD structure
        final_output = {
            "@context": context,
            "@graph": jsonld_graph
        }

        print(f"Writing JSON-LD export to {output_path}...")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)
            
        print(f"JSON-LD export completed successfully.")
        cur.close()
    except Exception as e:
        print(f"Error during JSON-LD export: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    export_jsonld()
