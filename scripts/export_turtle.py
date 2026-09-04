import sys
import os
import xml.etree.ElementTree as ET

# Add project root to path to be able to import db_connect
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.db_connect import connect

def escape_turtle(text):
    """Simple escape for Turtle strings."""
    if text is None:
        return ""
    return text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')

def export_turtle():
    """
    Fetches data from devill_meta.xml_export and saves it as a Turtle (.ttl) file
    in data/files/rdf/devill-file-metadata.ttl.
    """
    conn = connect()
    if conn is None:
        return

    # Define project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    output_path = os.path.join(project_root, 'data', 'files', 'devill-file-metadata.ttl')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        cur = conn.cursor()
        sql = "SELECT edm FROM devill_meta.xml_export;"
        print("Fetching data from devill_meta.xml_export...")
        cur.execute(sql)
        rows = cur.fetchall()

        prefixes = [
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix edm: <http://www.europeana.eu/schemas/edm/> .",
            "@prefix dc: <http://purl.org/dc/elements/1.1/> .",
            "@prefix dcterms: <http://purl.org/dc/terms/> .",
            "@prefix ore: <http://www.openarchives.org/ore/terms/> .",
            "@prefix cc: <http://creativecommons.org/ns#> .",
            "@prefix odrl: <http://www.w3.org/ns/odrl/2/> .",
            "@prefix svcs: <http://rdfs.org/sioc/services#> .",
            "@prefix doap: <http://usefulinc.com/ns/doap#> .",
            "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
            ""
        ]

        # Namespaces for parsing
        ns = {
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'edm': 'http://www.europeana.eu/schemas/edm/',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'dcterms': 'http://purl.org/dc/terms/',
            'ore': 'http://www.openarchives.org/ore/terms/'
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(prefixes) + '\n')

            for row in rows:
                edm_xml = row[0]
                if not edm_xml:
                    continue

                try:
                    # Parse the XML fragment
                    root = ET.fromstring(edm_xml)
                    
                    ns_map = {
                        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                        'edm': 'http://www.europeana.eu/schemas/edm/',
                        'dc': 'http://purl.org/dc/elements/1.1/',
                        'dcterms': 'http://purl.org/dc/terms/',
                        'ore': 'http://www.openarchives.org/ore/terms/'
                    }

                    cho = root.find('.//edm:ProvidedCHO', ns_map)
                    agg = root.find('.//ore:Aggregation', ns_map)

                    if agg is not None:
                        agg_about = agg.get('{%s}about' % ns_map['rdf'])
                        f.write(f'<{agg_about}> a ore:Aggregation ;\n')
                        
                        agg_children = list(agg)
                        for i, child in enumerate(agg_children):
                            tag = child.tag.split('}')[-1]
                            prefix = None
                            for p, uri in ns_map.items():
                                if child.tag.startswith('{%s}' % uri):
                                    prefix = p
                                    break
                            
                            if not prefix: continue
                            pred = f"{prefix}:{tag}"
                            
                            # If it's the aggregatedCHO link, and we have the CHO object, nest it!
                            if tag == 'aggregatedCHO' and prefix == 'edm' and cho is not None:
                                cho_about = cho.get('{%s}about' % ns_map['rdf'])
                                f.write(f'    {pred} <{cho_about}> ;\n')
                                # We will write the CHO separately below to keep it clean, 
                                # or we could nest it with []. 
                                # Given it has a URI, separate block is standard but reordered.
                                continue

                            resource = child.get('{%s}resource' % ns_map['rdf'])
                            line = f"    {pred} "
                            if resource:
                                line += f"<{resource}>"
                            else:
                                val = escape_turtle(child.text)
                                line += f'"{val}"'
                            
                            if i == len(agg_children) - 1:
                                f.write(line + " .\n\n")
                            else:
                                f.write(line + " ;\n")

                    if cho is not None:
                        cho_about = cho.get('{%s}about' % ns_map['rdf'])
                        f.write(f'<{cho_about}> a edm:ProvidedCHO ;\n')
                        
                        cho_children = list(cho)
                        for i, child in enumerate(cho_children):
                            tag = child.tag.split('}')[-1]
                            prefix = None
                            for p, uri in ns_map.items():
                                if child.tag.startswith('{%s}' % uri):
                                    prefix = p
                                    break
                            
                            if not prefix: continue
                            pred = f"{prefix}:{tag}"
                            resource = child.get('{%s}resource' % ns_map['rdf'])
                            lang = child.get('{http://www.w3.org/XML/1998/namespace}lang')
                            
                            line = f"    {pred} "
                            if resource:
                                line += f"<{resource}>"
                            else:
                                val = escape_turtle(child.text)
                                line += f'"{val}"'
                                if lang:
                                    line += f"@{lang}"
                            
                            if i == len(cho_children) - 1:
                                f.write(line + " .\n\n")
                            else:
                                f.write(line + " ;\n")

                except Exception as parse_err:
                    print(f"Error parsing row: {parse_err}")

        print(f"Turtle export completed: {output_path}")
        cur.close()
    except Exception as e:
        print(f"Error during Turtle export: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    export_turtle()
