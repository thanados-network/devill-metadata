# Technical Setup & Data Processing

This guide provides instructions for setting up the DeVill metadata extraction pipeline and processing the data.
Please note that this works only for the DeVill instance of OpenAtlas and will not work as desired for other instances.
So consider this guide as technical documentation for the DeVill developer team. 

## Technical Setup


### Prerequisites

- **Python 3.x**
- **PostgreSQL Database** (with [OpenAtlas](https://openatlas.eu) schema)
- Python libraries: `psycopg2-binary`, `rdflib`


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
1. Database collection update.
2. Export to RDF/XML, Turtle, and JSON-LD.
3. Export to CSV (Metadata, Objects, and Object-File Relations).
