# Technical Setup & Data Processing

This guide provides instructions for setting up the DeVill metadata extraction pipeline and processing the data.
Please note that this works only for the DeVill instance of OpenAtlas and will not work as desired for other instances.
So consider this guide as technical documentation for the DeVill developer team. 

## Technical Setup


### Prerequisites

- **Python 3.x**
- **PostgreSQL Database** (with [OpenAtlas](https://openatlas.eu) schema)
- Python library for the pipeline: `psycopg2-binary`
- Additional Python libraries only for `scripts/fetch_api_data.py` (see below): `pandas`, `requests`, `rdflib`


### Installation

1. Clone the repository.
2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install the dependencies:
   ```bash
   pip install psycopg2-binary
   ```
   To also run `scripts/fetch_api_data.py`:
   ```bash
   pip install pandas requests rdflib
   ```


### Configuration

1. Default values are in `config/default.py`.
2. Create `instance/production.py` to override settings:
   ```python
   OPENATLAS_DATABASE_NAME = 'your_database'
   DATABASE_USER = 'your_user'
   DATABASE_PASS = 'your_password'
   DATABASE_HOST = 'localhost'
   DATABASE_PORT = 5432
   ```


## Data Processing (Scripts)

To regenerate the metadata from the database, use the pipeline script:

```bash
python scripts/pipeline.py
```

The pipeline executes the following steps:
1. Database collection update (`create_xml_collection`, including the image bounding boxes from `web.map_overlay`).
2. Export of the file metadata to RDF/XML.
3. Export of the file metadata to Turtle.
4. Export of the file metadata to JSON-LD.
5. Export of the file metadata to CSV (`data/files/file-metadata.csv`).
6. Export of the archaeological objects to CSV (`data/archaeological_objects/archaeological_objects.csv`).
7. Export of the object-file relations to CSV (`data/crossrefs/object_file_relation.csv`).
8. Export of the archaeological places to GeoJSON (`data/archaeological_objects/archaeological_objects.geojson`).
9. Export of the georeferenced files to GeoJSON (`data/files/file-metadata.geojson`).

### Files not created by the pipeline

The RDF/XML, Turtle and JSON-LD files of the archaeological objects (`data/archaeological_objects/archaeological_objects.rdf`, `.ttl`, `.jsonld`) are **not** created by `scripts/pipeline.py`. They are generated from the OpenAtlas API with:

```bash
python scripts/fetch_api_data.py
```

The script reads the IDs from `data/archaeological_objects/archaeological_objects.csv`, so run the pipeline first. Run it again whenever the object data has changed, so that these files stay in sync with the CSV and GeoJSON files.
