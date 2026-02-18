import argparse
from datetime import datetime

from src.auth import getHTMLandCookie, getCSRFcode
from src.guarani import getInfoMesa
from src.db_factory import get_db


def formato_turno_api(fecha):
    # fecha puede ser texto 'YYYY-MM-01' o datetime.date
    if hasattr(fecha, 'strftime'):
        year = fecha.year
        ym = fecha.strftime('%Y-%m')
    else:
        s = str(fecha)
        # asumir formato YYYY-MM-DD
        year = int(s.split('-')[0])
        ym = '-'.join(s.split('-')[:2])
    return f"{ym}|{year}"


def fetch_mesas_for_materia(db, cookie, csrf, dpto, materia_codigo):
    # obtener turnos desde la base
    db.cursor.execute('SELECT id, fecha FROM turnos')
    turnos = db.cursor.fetchall()

    total_inserted = 0

    for turno in turnos:
        turno_id = turno[0]
        turno_fecha = turno[1]
        turno_api = formato_turno_api(turno_fecha)

        try:
            resp = getInfoMesa(dpto, int(materia_codigo), turno_api, cookie, csrf)
            # If server returned a refreshed CSRF token inside an HTML response, update and retry once
            if isinstance(resp, dict) and 'csrf' in resp:
                csrf = resp['csrf']
                resp = getInfoMesa(dpto, int(materia_codigo), turno_api, cookie, csrf)
        except Exception as e:
            print(f"Error request {dpto} {materia_codigo} {turno_api}: {e}")
            continue

        if not isinstance(resp, (dict, list)):
            continue

        # Normalize possible response shapes: dict with 'mesas' or a direct list
        if isinstance(resp, dict):
            mesas_source = resp.get('mesas', [])
        else:
            mesas_source = resp

        mesas = []
        # mesas_source can be a dict (clave->detalle) or a list of detalle
        if isinstance(mesas_source, dict):
            iterator = mesas_source.items()
        else:
            iterator = enumerate(mesas_source)

        for _, details in iterator:
            try:
                fecha = datetime.strptime(details['fecha'], '%d/%m/%y').date()
                fecha_iso = fecha.isoformat()
            except Exception:
                fecha_iso = None

            insc_inicio = None
            insc_fin = None
            try:
                if details.get('insc_inicio'):
                    insc_inicio = datetime.strptime(details['insc_inicio'], '%d/%m/%y %H:%M').isoformat()
                if details.get('insc_fin'):
                    insc_fin = datetime.strptime(details['insc_fin'], '%d/%m/%y %H:%M').isoformat()
            except Exception:
                insc_inicio = None
                insc_fin = None

            mesa_row = {
                'id_materia': None,  # will be mapped below
                'id_turno': turno_id,
                'fecha': fecha_iso,
                'codigo': details.get('mesa_examen'),
                'profesor': ', '.join(details.get('docentes', [])) if details.get('docentes') else None,
                'hora_inicio': details.get('hora_inicio'),
                'hora_fin': details.get('hora_fin'),
                'tipo': details.get('tipo'),
                'inscripcion_inicio': insc_inicio,
                'inscripcion_fin': insc_fin,
                'cant_inscriptos': int(details.get('inscriptos', 0)) if details.get('inscriptos') else 0,
                'carrera': details.get('carrera', ''),
                'plan': details.get('plan', ''),
                'grupo_carrera': details.get('grupo_carrera', ''),
                'observaciones': details.get('observaciones', ''),
                'capacidad': details.get('capacidad', ''),
                'letra_desde': details.get('letra_desde', ''),
                'letra_hasta': details.get('letra_hasta', ''),
                'sede': details.get('sede', '')
            }

            mesas.append(mesa_row)

        if not mesas:
            continue

        # Map codigo_materia -> id
        db.cursor.execute('SELECT id FROM materias WHERE codigo_materia = ?', (str(materia_codigo),))
        row = db.cursor.fetchone()
        if row:
            materia_id = row[0]
        else:
            # materia no encontrada en la DB
            print(f"Materia {materia_codigo} no encontrada en la base. Inserta materias primero.")
            return 0

        # set id_materia for each mesa
        for m in mesas:
            m['id_materia'] = materia_id

        db.insert_mesas(mesas)
        total_inserted += len(mesas)

    return total_inserted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dpto', required=True, help='Código del departamento (ej: CO)')
    parser.add_argument('--materia', required=True, help='Código de la materia (ej: 7958)')
    args = parser.parse_args()

    html, cookie = getHTMLandCookie()
    csrf = getCSRFcode(html)
    db = get_db()

    inserted = fetch_mesas_for_materia(db, cookie, csrf, args.dpto, args.materia)
    print(f"Inserted total mesas: {inserted}")

    db.close_connection()


if __name__ == '__main__':
    main()
