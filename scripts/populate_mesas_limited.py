"""Temporal: poblar mesas limitado a un pequeño conjunto de materias x turnos.
Uso:
  python scripts/populate_mesas_limited.py --dpto CO --materias 7655,7958 --run

Por defecto no ejecuta las inserciones salvo que se pase `--run`.
"""
import argparse
import time
from datetime import datetime

from src.auth import getHTMLandCookie, getCSRFcode
from src.guarani import getInfoMesa
from src.db_factory import get_db


def formato_turno_api(fecha):
    if hasattr(fecha, 'strftime'):
        year = fecha.year
        ym = fecha.strftime('%Y-%m')
    else:
        s = str(fecha)
        year = int(s.split('-')[0])
        ym = '-'.join(s.split('-')[:2])
    return f"{ym}|{year}"


def fetch_for_limited(db, cookie, csrf, dpto, materias, do_run=False, retries=2):
    db.cursor.execute('SELECT id, fecha FROM turnos')
    turnos = db.cursor.fetchall()

    total_inserted = 0
    details = []

    for materia_codigo in materias:
        # map materia codigo -> id
        db.cursor.execute('SELECT id FROM materias WHERE codigo_materia = ?', (str(materia_codigo),))
        row = db.cursor.fetchone()
        if row:
            materia_id = row[0]
        else:
            print(f"Materia {materia_codigo} no encontrada en la DB; saltando.")
            continue

        for t in turnos:
            turno_id = t[0]
            turno_fecha = t[1]
            turno_api = formato_turno_api(turno_fecha)

            attempt = 0
            resp = None
            while attempt <= retries:
                attempt += 1
                resp = getInfoMesa(dpto, int(materia_codigo), turno_api, cookie, csrf)
                # CSRF refresh handling
                if isinstance(resp, dict) and 'csrf' in resp:
                    csrf = resp['csrf']
                    resp = getInfoMesa(dpto, int(materia_codigo), turno_api, cookie, csrf)

                if isinstance(resp, (dict, list)):
                    break

                sleep = 0.5 * (2 ** (attempt - 1))
                time.sleep(sleep)

            if not isinstance(resp, (dict, list)):
                print(f"No hubo respuesta válida para {dpto} {materia_codigo} {turno_api}")
                continue

            # normalize
            if isinstance(resp, dict):
                mesas_src = resp.get('mesas', [])
            else:
                mesas_src = resp

            if not mesas_src:
                continue

            # build rows list
            rows = []
            if isinstance(mesas_src, dict):
                iterator = mesas_src.items()
            else:
                iterator = enumerate(mesas_src)

            for _, details_m in iterator:
                fecha_iso = None
                try:
                    fecha = datetime.strptime(details_m['fecha'], '%d/%m/%y').date()
                    fecha_iso = fecha.isoformat()
                except Exception:
                    fecha_iso = None

                insc_inicio = None
                insc_fin = None
                try:
                    if details_m.get('insc_inicio'):
                        insc_inicio = datetime.strptime(details_m['insc_inicio'], '%d/%m/%y %H:%M').isoformat()
                    if details_m.get('insc_fin'):
                        insc_fin = datetime.strptime(details_m['insc_fin'], '%d/%m/%y %H:%M').isoformat()
                except Exception:
                    insc_inicio = None
                    insc_fin = None

                row = {
                    'id_materia': materia_id,
                    'id_turno': turno_id,
                    'fecha': fecha_iso,
                    'codigo': details_m.get('mesa_examen'),
                    'profesor': ', '.join(details_m.get('docentes', [])) if details_m.get('docentes') else None,
                    'hora_inicio': details_m.get('hora_inicio'),
                    'hora_fin': details_m.get('hora_fin'),
                    'tipo': details_m.get('tipo'),
                    'inscripcion_inicio': insc_inicio,
                    'inscripcion_fin': insc_fin,
                    'cant_inscriptos': int(details_m.get('inscriptos', 0)) if details_m.get('inscriptos') else 0,
                    'carrera': details_m.get('carrera', ''),
                    'plan': details_m.get('plan', ''),
                    'grupo_carrera': details_m.get('grupo_carrera', ''),
                    'observaciones': details_m.get('observaciones', ''),
                    'capacidad': details_m.get('capacidad', ''),
                    'letra_desde': details_m.get('letra_desde', ''),
                    'letra_hasta': details_m.get('letra_hasta', ''),
                    'sede': details_m.get('sede', '')
                }
                rows.append(row)

            if rows:
                print(f"Encontradas {len(rows)} mesas para materia {materia_codigo} turno {turno_api}")
                if do_run:
                    db.insert_mesas(rows)
                    total_inserted += len(rows)

    return total_inserted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dpto', required=True, help='Código de departamento (ej: CO)')
    parser.add_argument('--materias', required=False, help='Lista de materias separadas por coma (ej: 7655,7958)')
    parser.add_argument('--run', action='store_true', help='Si se indica, ejecuta las inserciones en la DB')
    args = parser.parse_args()

    materias = [m.strip() for m in (args.materias or '7655,7958').split(',') if m.strip()]

    html, cookie = getHTMLandCookie()
    csrf = getCSRFcode(html)
    db = get_db()

    inserted = fetch_for_limited(db, cookie, csrf, args.dpto, materias, do_run=args.run)

    print('Inserted total mesas (this run):', inserted)
    db.close_connection()


if __name__ == '__main__':
    main()
