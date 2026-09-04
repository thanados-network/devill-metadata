import psycopg2
import sys
import os

# Add project root to path to be able to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def get_config():
    config = {}
    
    # Load default values
    try:
        import config.default as default_settings
        for item in dir(default_settings):
            if item.isupper():
                config[item] = getattr(default_settings, item)
    except ImportError:
        print("Warning: config/default.py not found.")

    # Load production values (override)
    try:
        import instance.production as prod_settings
        for item in dir(prod_settings):
            if item.isupper():
                config[item] = getattr(prod_settings, item)
    except ImportError:
        print("Note: instance/production.py not found, using default values.")
    
    return config

def connect():
    cfg = get_config()
    
    # DATABASE_NAME vs OPENATLAS_DATABASE_NAME handling based on production.py observations
    dbname = cfg.get('OPENATLAS_DATABASE_NAME')
    
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=cfg.get('DATABASE_USER'),
            password=cfg.get('DATABASE_PASS'),
            host=cfg.get('DATABASE_HOST', 'localhost'),
            port=cfg.get('DATABASE_PORT', 5432)
        )
        print("Successfully connected to the database!")
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None

if __name__ == "__main__":
    connection = connect()
    if connection:
        connection.close()
