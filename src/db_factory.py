import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

DB_BACKEND = os.getenv('DB_BACKEND', 'sqlite').lower()

def get_db():
    if DB_BACKEND in ('sqlite', 'sqlite3'):
        from .db_sqlite import GuaraniDB
        return GuaraniDB()
    else:
        # assume postgres
        from .db import GuaraniDB
        return GuaraniDB()
