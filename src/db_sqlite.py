import sqlite3
import os
try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv():
        return None


class GuaraniDB:
    def __init__(self):
        load_dotenv()

        db_file = os.getenv('DB_FILE', 'guarani.db')
        os.makedirs(os.path.dirname(db_file), exist_ok=True) if os.path.dirname(db_file) else None

        self.conn = sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        # Enable foreign keys in SQLite
        self.cursor.execute('PRAGMA foreign_keys = ON;')

        self._ensure_schema()

    def _ensure_schema(self):
        # Create tables adapted for SQLite
        schema = """
        CREATE TABLE IF NOT EXISTS departamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            modified_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            codigo VARCHAR(10) UNIQUE NOT NULL,
            nombre_completo VARCHAR(255) NOT NULL
        );

        CREATE TABLE IF NOT EXISTS materias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            modified_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            codigo_materia VARCHAR(20) UNIQUE NOT NULL,
            nombre_completo VARCHAR(255) NOT NULL,
            codigo_departamento VARCHAR(10) NOT NULL,
            FOREIGN KEY (codigo_departamento) REFERENCES departamentos(codigo) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS turnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            fecha DATE NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS mesas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            modified_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            id_materia INTEGER NOT NULL,
            id_turno INTEGER NOT NULL,
            fecha DATE NOT NULL,
            codigo VARCHAR(50) NOT NULL,
            profesor VARCHAR(255),
            hora_inicio TIME NOT NULL,
            hora_fin TIME NOT NULL,
            tipo VARCHAR(50),
            inscripcion_inicio DATETIME,
            inscripcion_fin DATETIME,
            cant_inscriptos INTEGER DEFAULT 0,
            carrera VARCHAR(100),
            plan VARCHAR(50),
            grupo_carrera VARCHAR(50),
            observaciones TEXT,
            capacidad VARCHAR(50),
            letra_desde VARCHAR(10),
            letra_hasta VARCHAR(10),
            sede VARCHAR(100),
            FOREIGN KEY (id_materia) REFERENCES materias(id) ON DELETE RESTRICT,
            FOREIGN KEY (id_turno) REFERENCES turnos(id) ON DELETE RESTRICT
        );

        CREATE INDEX IF NOT EXISTS idx_materias_departamento ON materias(codigo_departamento);
        CREATE INDEX IF NOT EXISTS idx_mesas_materia ON mesas(id_materia);
        CREATE INDEX IF NOT EXISTS idx_mesas_turno ON mesas(id_turno);
        """

        # Execute the schema (split statements)
        for stmt in [s.strip() for s in schema.split(';') if s.strip()]:
            self.cursor.execute(stmt)
        self.conn.commit()

    def close_connection(self):
        try:
            if hasattr(self, 'conn') and self.conn:
                self.conn.commit()
                self.cursor.close()
                self.conn.close()
        except Exception:
            pass

    def insert_departamentos(self, dptos):
        if not dptos:
            return {}

        insert_sql = '''
        INSERT INTO departamentos (codigo, nombre_completo, updated_at, modified_at)
        VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(codigo) DO UPDATE SET
            nombre_completo = excluded.nombre_completo,
            updated_at = CURRENT_TIMESTAMP,
            modified_at = CASE WHEN nombre_completo != excluded.nombre_completo THEN CURRENT_TIMESTAMP ELSE modified_at END;
        '''

        values = [(codigo, nombre) for codigo, nombre in dptos.items()]
        self.cursor.executemany(insert_sql, values)
        self.conn.commit()

        # Return a mapping codigo -> id
        placeholders = ','.join('?' for _ in dptos)
        query = f"SELECT codigo, id FROM departamentos WHERE codigo IN ({placeholders})"
        self.cursor.execute(query, list(dptos.keys()))
        rows = self.cursor.fetchall()
        return {row['codigo']: row['id'] for row in rows}

    def insert_materias(self, materias, dpto):
        if not materias:
            print("Error: No hay materias")
            return
        if not dpto:
            print("Error: No hay dpto")
            return

        insert_sql = '''
        INSERT INTO materias (codigo_materia, nombre_completo, codigo_departamento, updated_at, modified_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(codigo_materia) DO UPDATE SET
            nombre_completo = excluded.nombre_completo,
            codigo_departamento = excluded.codigo_departamento,
            updated_at = CURRENT_TIMESTAMP,
            modified_at = CASE WHEN materias.nombre_completo != excluded.nombre_completo
                                OR materias.codigo_departamento != excluded.codigo_departamento
                                THEN CURRENT_TIMESTAMP ELSE materias.modified_at END;
        '''

        values = [(str(codigo), nombre, dpto) for codigo, nombre in materias.items()]
        self.cursor.executemany(insert_sql, values)
        self.conn.commit()
        print(f"Inserted {len(values)} courses successfully")

    def insert_turnos(self, turnos):
        if not turnos:
            print("Error: No hay turnos para insertar.")
            return

        insert_sql = '''
        INSERT INTO turnos (fecha) VALUES (?)
        ON CONFLICT(fecha) DO NOTHING;
        '''

        self.cursor.executemany(insert_sql, turnos)
        self.conn.commit()
        print(f"Se insertaron {len(turnos)} turnos correctamente.")

    def insert_mesas(self, mesas):
        """
        Insert a list of mesas. Each item is a dict with keys matching the mesas columns.
        """
        if not mesas:
            print("No hay mesas para insertar.")
            return

        insert_sql = '''
        INSERT INTO mesas (
            id_materia, id_turno, fecha, codigo, profesor,
            hora_inicio, hora_fin, tipo, inscripcion_inicio, inscripcion_fin,
            cant_inscriptos, carrera, plan, grupo_carrera, observaciones,
            capacidad, letra_desde, letra_hasta, sede, modified_at, created_at, updated_at
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        );
        '''

        values = []
        for m in mesas:
            values.append((
                m.get('id_materia'),
                m.get('id_turno'),
                m.get('fecha'),
                m.get('codigo'),
                m.get('profesor'),
                m.get('hora_inicio'),
                m.get('hora_fin'),
                m.get('tipo'),
                m.get('inscripcion_inicio'),
                m.get('inscripcion_fin'),
                m.get('cant_inscriptos', 0),
                m.get('carrera'),
                m.get('plan'),
                m.get('grupo_carrera'),
                m.get('observaciones'),
                m.get('capacidad'),
                m.get('letra_desde'),
                m.get('letra_hasta'),
                m.get('sede')
            ))

        self.cursor.executemany(insert_sql, values)
        self.conn.commit()
        print(f"Inserted {len(values)} mesas successfully")

    # Minimal helper to match original API
    def __del__(self):
        self.close_connection()
