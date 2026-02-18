import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv
import os

class GuaraniDB:
    def __init__(self):
        load_dotenv()

        db_config = {
            'dbname': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT')
        }

        try:
            self.conn = psycopg2.connect(**db_config)
            self.cursor = self.conn.cursor(cursor_factory=extras.DictCursor)
        except (Exception, psycopg2.Error) as error:
            print(f"Error connecting to PostgreSQL: {error}")
            raise

    def __del__(self):
        self.close_connection()

    def close_connection(self):
        if hasattr(self, 'conn') and self.conn:
            try:
                self.cursor.close()
                self.conn.close()
                print("Database connection closed")
            except Exception as error:
                print(f"Error closing database connection: {error}")

    def insert_departamentos(self, dptos):
        try:
            insert_query = """
                INSERT INTO departamentos (codigo, nombre_completo) 
                VALUES %s 
                ON CONFLICT (codigo) DO UPDATE 
                SET nombre_completo = EXCLUDED.nombre_completo, 
                    updated_at = CURRENT_TIMESTAMP,
                    modified_at = CASE 
                        WHEN departamentos.nombre_completo != EXCLUDED.nombre_completo 
                        THEN CURRENT_TIMESTAMP
                        ELSE departamentos.modified_at
                    END
                RETURNING id;
                """

            # Prepare data for batch insert
            dptos_values = [(codigo, nombre) for codigo, nombre in dptos.items()]

            # Execute batch insert
            extras.execute_values(self.cursor, insert_query, dptos_values)

            # Fetch the inserted department IDs
            dept_ids = {codigo: self.cursor.fetchone()[0] for codigo in dptos.keys()}

            self.conn.commit()
            print(f"Inserted {len(dptos)} departments")
            return dept_ids

        except (Exception, psycopg2.Error) as error:
            self.conn.rollback()
            print(f"Error inserting departments: {error}")
            raise

    def insert_materias(self, materias, dpto):
        try:
            # Validate input
            if not materias:
                print("Error: No hay materias")
                return
            if not dpto:
                print("Error: No hay dpto")
                return

            materias_to_insert = []
            for codigo, nombre in materias.items():
                materias_to_insert.append((
                    str(codigo),
                    nombre,
                    dpto
                ))

            insert_query = """
                INSERT INTO materias (codigo_materia, nombre_completo, codigo_departamento) 
                VALUES %s 
                ON CONFLICT (codigo_materia) DO UPDATE 
                SET nombre_completo = EXCLUDED.nombre_completo, 
                    codigo_departamento = EXCLUDED.codigo_departamento,
                    updated_at = CURRENT_TIMESTAMP,
                    modified_at = CASE 
                        WHEN materias.nombre_completo != EXCLUDED.nombre_completo 
                          OR materias.codigo_departamento != EXCLUDED.codigo_departamento 
                        THEN CURRENT_TIMESTAMP
                        ELSE materias.modified_at
                    END;
            """

            # Execute batch insert
            extras.execute_values(self.cursor, insert_query, materias_to_insert)

            # Commit the transaction
            self.conn.commit()

            print(f"Inserted {len(materias_to_insert)} courses successfully")

        except (Exception, psycopg2.Error) as error:
            # Rollback the transaction in case of error
            self.conn.rollback()
            print(f"Error inserting courses: {error}")
            raise

    def insert_turnos(self, turnos):
        try:
            if not turnos:
                print("Error: No hay turnos para insertar.")
                return

            # Query de inserción
            insert_query = """
                INSERT INTO turnos (fecha) 
                VALUES %s
                ON CONFLICT (fecha) DO NOTHING;
            """

            extras.execute_values(self.cursor, insert_query, turnos)

            self.conn.commit()

            print(f"Se insertaron {len(turnos)} turnos correctamente.")

        except (Exception, psycopg2.Error) as error:
            self.conn.rollback()
            print(f"Error al insertar turnos: {error}")
            raise

    def get_materias_por_departamento(self):
        """
        Obtiene un diccionario donde las claves son códigos de departamento
        y los valores son listas de códigos de materias.

        Ejemplo de retorno:
        {
            'CO': ['7958', '7959', ...],
            'DF': ['8001', '8002', ...],
            ...
        }
        """
        try:
            query = """
            SELECT codigo_departamento, codigo_materia
            FROM materias
            ORDER BY codigo_departamento, codigo_materia;
            """

            db.cursor.execute(query)
            materias_raw = db.cursor.fetchall()

            # Agrupar materias por departamento
            materias_por_departamento = {}
            for dpto, materia in materias_raw:
                if dpto not in materias_por_departamento:
                    materias_por_departamento[dpto] = []
                materias_por_departamento[dpto].append(materia)

            return materias_por_departamento

        except Exception as error:
            print(f"Error al obtener materias por departamento: {error}")
            return {}
