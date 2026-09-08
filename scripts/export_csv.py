import sys
import os
import xml.etree.ElementTree as ET
import csv

# Add project root to path to be able to import db_connect
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.db_connect import connect

def export_csv():
    """
    Fetches data from devill_meta.xml_export and saves it as a CSV file
    in data/files/file-metadata.csv.
    """
    conn = connect()
    if conn is None:
        return

    # Define project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    output_path = os.path.join(project_root, 'data', 'files', 'file-metadata.csv')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        cur = conn.cursor()
        sql = "SELECT id, edm FROM devill_meta.xml_export;"
        print("Fetching data from devill_meta.xml_export...")
        cur.execute(sql)
        rows = cur.fetchall()

        # Namespaces for parsing XML
        ns = {
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'edm': 'http://www.europeana.eu/schemas/edm/',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'dcterms': 'http://purl.org/dc/terms/',
            'ore': 'http://www.openarchives.org/ore/terms/'
        }

        # Fields to extract for CSV
        csv_headers = [
            'id', 'title', 'description_de', 'description_en', 
            'subjects', 'spatial', 'temporal', 'created', 'filetype', 'mimetype', 'rights',
            'dataProvider', 'isShownAt', 'isShownBy', 'API_Endpoint'
        ]

        print(f"Writing CSV export to {output_path}...")
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_headers)
            writer.writeheader()

            for row in rows:
                db_id, edm_xml = row
                if not edm_xml:
                    continue

                try:
                    root = ET.fromstring(edm_xml)
                    cho = root.find('.//edm:ProvidedCHO', ns)
                    agg = root.find('.//ore:Aggregation', ns)

                    data = {h: '' for h in csv_headers}
                    data['id'] = db_id

                    if cho is not None:

                        # dc:title
                        title = cho.find('dc:title', ns)
                        if title is not None: data['title'] = title.text

                        # dc:description (de/en)
                        descriptions = cho.findall('dc:description', ns)
                        for desc in descriptions:
                            lang = desc.get('{http://www.w3.org/XML/1998/namespace}lang')
                            if lang == 'de':
                                data['description_de'] = desc.text
                            elif lang == 'en':
                                data['description_en'] = desc.text
                            elif not data['description_de']: # Fallback
                                data['description_de'] = desc.text

                        # dc:subject (multiple)
                        subjects = []
                        for sub in cho.findall('dc:subject', ns):
                            res = sub.get('{%s}resource' % ns['rdf'])
                            if res:
                                subjects.append(res)
                            elif sub.text:
                                subjects.append(sub.text)
                        data['subjects'] = ' | '.join(subjects)

                        # dcterms:spatial (multiple)
                        spatial = [s.text for s in cho.findall('dcterms:spatial', ns) if s.text]
                        data['spatial'] = ' | '.join(spatial)

                        # dcterms:temporal (multiple)
                        temporal = [t.text for t in cho.findall('dcterms:temporal', ns) if t.text]
                        data['temporal'] = ' | '.join(temporal)

                        # dcterms:created
                        created = cho.find('dcterms:created', ns)
                        if created is not None: data['created'] = created.text

                        # dc:rights
                        rights = cho.find('dc:rights', ns)
                        if rights is not None: data['rights'] = rights.text

                    if agg is not None:
                        # edm:isShownAt
                        at = agg.find('edm:isShownAt', ns)
                        if at is not None:
                            data['isShownAt'] = at.get('{%s}resource' % ns['rdf'])

                        # edm:isShownBy
                        by = agg.find('edm:isShownBy', ns)
                        if by is not None:
                            data['isShownBy'] = by.get('{%s}resource' % ns['rdf'])
                            
                        # Extract filetype and mimetype from URLs
                        url_for_ext = data['isShownAt'] or data['isShownBy']
                        if url_for_ext:
                            # Try to find a file extension in the URL
                            import posixpath
                            from urllib.parse import urlparse
                            path = urlparse(url_for_ext).path
                            ext = posixpath.splitext(path)[1].lower().replace('.', '')
                            
                            if ext:
                                data['filetype'] = ext
                                # Common mimetypes mapping
                                mime_map = {
                                    'pdf': 'application/pdf',
                                    'svg': 'image/svg+xml',
                                    'png': 'image/png',
                                    'jpg': 'image/jpeg',
                                    'jpeg': 'image/jpeg',
                                    'tif': 'image/tiff',
                                    'tiff': 'image/tiff',
                                    'glb': 'model/gltf-binary',
                                    'webp': 'image/webp'
                                }
                                data['mimetype'] = mime_map.get(ext, 'application/octet-stream')

                        # edm:dataProvider
                        dp = agg.find('edm:dataProvider', ns)
                        if dp is not None: data['dataProvider'] = dp.text

                    # API_Endpoint
                    data['API_Endpoint'] = f"https://thanados.openatlas.eu/api/entity/{db_id}"

                    writer.writerow(data)

                except Exception as parse_err:
                    print(f"Error parsing row {db_id}: {parse_err}")

        print(f"CSV export completed successfully.")
        cur.close()
    except Exception as e:
        print(f"Error during CSV export: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    export_csv()
