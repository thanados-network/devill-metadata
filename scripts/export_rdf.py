import sys
import os

# Add project root to path to be able to import db_connect
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.db_connect import connect

def export_rdf_collection():
    """
    Fetches data from devill_meta.xml_export and saves it as an RDF collection
    in data/files/rdf/file-metadata.rdf.
    """
    conn = connect()
    if conn is None:
        return

    # Define project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    output_path = os.path.join(project_root, 'data', 'files', 'file-metadata.rdf')
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        cur = conn.cursor()
        
        # Select all edm fields from the collection table
        sql = "SELECT edm FROM devill_meta.xml_export;"
        
        print("Fetching data from devill_meta.xml_export...")
        cur.execute(sql)
        rows = cur.fetchall()
        
        # RDF Collection header
        # Since each row's 'edm' field is a full rdf:RDF, we might need to extract 
        # the content inside <rdf:RDF> if we want a single valid RDF file, 
        # or wrap them in a specific way.
        # However, the user asked for a "collection as rdf collection".
        # Standard way is to have one <rdf:RDF> and many items inside.
        
        rdf_content = []
        rdf_content.append('<?xml version="1.0" encoding="UTF-8"?>')
        rdf_content.append('<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"')
        rdf_content.append('         xmlns:edm="http://www.europeana.eu/schemas/edm/"')
        rdf_content.append('         xmlns:dc="http://purl.org/dc/elements/1.1/"')
        rdf_content.append('         xmlns:dcterms="http://purl.org/dc/terms/"')
        rdf_content.append('         xmlns:ore="http://www.openarchives.org/ore/terms/"')
        rdf_content.append('         xmlns:cc="http://creativecommons.org/ns#"')
        rdf_content.append('         xmlns:odrl="http://www.w3.org/ns/odrl/2/"')
        rdf_content.append('         xmlns:svcs="http://rdfs.org/sioc/services#"')
        rdf_content.append('         xmlns:doap="http://usefulinc.com/ns/doap#">')

        for row in rows:
            edm_xml = row[0]
            if edm_xml:
                try:
                    import xml.etree.ElementTree as ET
                    # Parse the XML fragment
                    root = ET.fromstring(edm_xml)
                    
                    ns = {
                        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                        'edm': 'http://www.europeana.eu/schemas/edm/',
                        'ore': 'http://www.openarchives.org/ore/terms/'
                    }
                    # Register namespaces to keep prefixes clean
                    ET.register_namespace('rdf', ns['rdf'])
                    ET.register_namespace('edm', ns['edm'])
                    ET.register_namespace('ore', ns['ore'])
                    ET.register_namespace('dc', 'http://purl.org/dc/elements/1.1/')
                    ET.register_namespace('dcterms', 'http://purl.org/dc/terms/')
                    ET.register_namespace('cc', 'http://creativecommons.org/ns#')
                    ET.register_namespace('odrl', 'http://www.w3.org/ns/odrl/2/')
                    ET.register_namespace('svcs', 'http://rdfs.org/sioc/services#')
                    ET.register_namespace('doap', 'http://usefulinc.com/ns/doap#')

                    cho = root.find('.//edm:ProvidedCHO', ns)
                    agg = root.find('.//ore:Aggregation', ns)
                    
                    if agg is not None and cho is not None:
                        # Find the edm:aggregatedCHO element in Aggregation
                        aggregated_cho = agg.find('edm:aggregatedCHO', ns)
                        if aggregated_cho is not None:
                            # Remove rdf:resource attribute
                            res_attr = '{%s}resource' % ns['rdf']
                            if res_attr in aggregated_cho.attrib:
                                del aggregated_cho.attrib[res_attr]
                            # Append the ProvidedCHO element as a child
                            aggregated_cho.append(cho)
                        
                        # Convert back to string
                        entry_xml = ET.tostring(agg, encoding='unicode')
                        rdf_content.append(entry_xml)
                    elif edm_xml:
                        # Fallback to original logic if structure is unexpected
                        content = edm_xml.strip()
                        if content.startswith('<?xml'):
                            content = content[content.find('?>')+2:].strip()
                        start_tag = '<rdf:RDF'
                        end_tag = '</rdf:RDF>'
                        start_idx = content.find(start_tag)
                        if start_idx != -1:
                            content_start = content.find('>', start_idx) + 1
                            content_end = content.rfind(end_tag)
                            if content_start > 0 and content_end != -1:
                                rdf_content.append(content[content_start:content_end].strip())
                except Exception as e:
                    print(f"Warning: Could not nest XML for a row: {e}")
                    # Fallback to simple extraction
                    content = edm_xml.strip()
                    if content.startswith('<?xml'):
                        content = content[content.find('?>')+2:].strip()
                    rdf_content.append(content)

        rdf_content.append('</rdf:RDF>')

        print(f"Writing RDF collection to {output_path}...")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(rdf_content))
            
        print("Export completed successfully.")
        
        cur.close()
    except Exception as e:
        print(f"Error during RDF export: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    export_rdf_collection()
