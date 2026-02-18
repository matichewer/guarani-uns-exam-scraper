from bs4 import BeautifulSoup
import requests
import re
import json

import logging
from logging.config import fileConfig
from pathlib import Path

from datetime import datetime
import time

try:
    from .db_sqlite import GuaraniDB
except Exception:
    from .db import GuaraniDB

fileConfig('logs/config.ini', defaults={ 'file-name': Path(__file__).stem })
log = logging.getLogger()

from .auth import getHTMLandCookie, getCSRFcode

url = "https://g3w.uns.edu.ar/guarani3w/mesas_publica/buscar_mesas"


def getDptos(html_code):
    dptos_dict = {}

    # Extraer el contenido del script
    script_content = re.search(r'kernel\.renderer\.on_arrival\((.*?)\);', html_code, re.DOTALL)

    if script_content:
        # Parsear el JSON
        try:
            data = json.loads(script_content.group(1))
            html_content = data.get('content', '')

            # Buscar las opciones de departamentos en el HTML extraído
            options = re.findall(r'<option value="([A-Z]{2})">([^<]+)</option>', html_content)

            for abbr, name in options:
                if name != "-- Seleccione un Departamento Académico --":
                    dptos_dict[abbr] = name.strip()

        except json.JSONDecodeError:
            log.error("Error al decodificar JSON")

    # Eliminar el departamento PG si existe, ya que da error en Guarani
    if 'PG' in dptos_dict:
        del dptos_dict['PG']

    log.info(f'Dptos del Guarani: {dptos_dict}')
    log.info(f'Cantidad de Dptos: {len(dptos_dict)}')

    return dptos_dict

def getMateriasFromDpto(dpto, cookie_code, csrf_code):
    headers = {"Cookie": f"siu_sess_guarani3w_UNS={cookie_code}"}
    url = 'https://g3w.uns.edu.ar/guarani3w/mesas_publica/buscar_materias'
    data = {
        'depto': dpto
    }

    response = requests.post(url, headers=headers, data=data)
    # Verificar si la solicitud fue exitosa
    if response.status_code == 200:
        materias = response.json()
        materias_dict = {materia['materia']: materia['mat_nombre'] for materia in materias['materias']}
        cant_materias = len(materias_dict)
        log.info(f'Materias del departamento {dpto}: {materias_dict}')
        log.info(f'Cantidad de Materias: {cant_materias}')
        return materias_dict
    else:
        print(f"Error en la solicitud: {response.status_code}")


def getTurnos(html_code):    
    turnos_array = re.findall(r'[0-9]{4}-[0-9]{2}\|[0-9]{4}', html_code)
    log.info('Turnos del Guarani: ' + str(turnos_array))
    log.info('Cantidad de Turnos: ' + str(len(turnos_array)))
    return turnos_array

def format_turnos(turnos):
    # Formatear los turnos para inserción en la base de datos
    # Usar una lista de tuplas, no de strings
    formatted_turnos = [(f"{turno.split('|')[0]}-01",) for turno in turnos]
    return formatted_turnos

def getInfoMesa(dpto, materia, turno, cookie_code, csrf_code):
    headers = {
        "Cookie": f"siu_sess_guarani3w_UNS={cookie_code}",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://g3w.uns.edu.ar/guarani3w/mesas_publica",
        "User-Agent": "Mozilla/5.0 (compatible)"
    }
    data = {"depto": dpto, "materia": materia, "turno": turno, "__csrf": csrf_code}

    try:
        response = requests.post(url, headers=headers, data=data, timeout=15)
    except Exception as e:
        log.error(f"Request error fetching mesas for {dpto} {materia} {turno}: {e}")
        return {}

    if response.status_code != 200:
        log.warning(f"Non-200 response for {dpto} {materia} {turno}: {response.status_code}")
        return {}

    # Prefer JSON; if server returns HTML (e.g. refreshed page), try to extract a new CSRF token
    try:
        return response.json()
    except ValueError:
        # Try to extract a refreshed CSRF token from the HTML and return it so caller can update
        m = re.search(r'name="__csrf" value="(csrf[0-9a-zA-Z]+)"', response.text)
        if m:
            new_csrf = m.group(1)
            log.info(f"Refreshed CSRF token obtained from HTML response: {new_csrf}")
            return {"csrf": new_csrf}
        log.warning(f"Non-JSON response for {dpto} {materia} {turno}")
        return {}

def getAllMesas(db, cookie_code, csrf_code):
    try:
        # Consulta para obtener departamentos, materias y turnos
        query = """
          SELECT 
              codigo_materia, 
              codigo_departamento
          FROM materias
          ORDER BY id;
          """

        db.cursor.execute(query)
        registros = db.cursor.fetchall()

        # Almacenar mesas para inserción
        todas_las_mesas = []

        # Iterar sobre los registros
        for registro in registros:
            dpto_codigo, materia_id, materia_codigo, turno_id, turno_fecha = registro

            # Convertir la fecha del turno al formato requerido por la API
            turno_api = f"{turno_fecha.strftime('%Y-%m')}|{turno_fecha.year}"

            try:
                # Obtener información de la mesa
                mesa_info = getInfoMesa(
                    dpto_codigo,
                    int(materia_codigo),
                    turno_api,
                    cookie_code,
                    csrf_code
                )

                # Procesar cada mesa del resultado
                for mesa_key, mesa_details in mesa_info.get('mesas', {}).items():
                    # Preparar datos para inserción
                    mesa_data = {
                        'id_materia': materia_id,
                        'id_turno': turno_id,
                        'fecha': datetime.strptime(mesa_details['fecha'], '%d/%m/%y').date(),
                        'codigo': mesa_details['mesa_examen'],
                        'profesor': ', '.join(mesa_details.get('docentes', [])) if mesa_details.get(
                            'docentes') else None,
                        'hora_inicio': mesa_details['hora_inicio'],
                        'hora_fin': mesa_details['hora_fin'],
                        'tipo': mesa_details['tipo'],
                        'inscripcion_inicio': datetime.strptime(mesa_details['insc_inicio'], '%d/%m/%y %H:%M'),
                        'inscripcion_fin': datetime.strptime(mesa_details['insc_fin'], '%d/%m/%y %H:%M'),
                        'cant_inscriptos': int(mesa_details.get('inscriptos', 0)),
                        'carrera': mesa_details.get('carrera', ''),
                        'plan': mesa_details.get('plan', ''),
                        'grupo_carrera': mesa_details.get('grupo_carrera', ''),
                        'observaciones': mesa_details.get('observaciones', ''),
                        'capacidad': mesa_details.get('capacidad', ''),
                        'letra_desde': mesa_details.get('letra_desde', ''),
                        'letra_hasta': mesa_details.get('letra_hasta', ''),
                        'sede': mesa_details.get('sede', '')
                    }

                    todas_las_mesas.append(mesa_data)

            except Exception as e:
                print(
                    f"Error obteniendo mesa para dpto {dpto_codigo}, materia {materia_codigo}, turno {turno_api}: {e}")

        return todas_las_mesas

    except Exception as error:
        print(f"Error general en get_mesas_info: {error}")
        return []


def fetch_and_insert_all_mesas(db, cookie_code, csrf_code):
    """
    Itera sobre todas las materias y turnos en la DB, consulta la API
    y almacena las mesas en la tabla `mesas`.
    """
    try:
        # Obtener materias (id, codigo_materia, codigo_departamento)
        db.cursor.execute("SELECT id, codigo_materia, codigo_departamento FROM materias")
        materias = db.cursor.fetchall()

        # Obtener turnos (id, fecha)
        db.cursor.execute("SELECT id, fecha FROM turnos")
        turnos = db.cursor.fetchall()

        todas = []

        for m in materias:
            materia_id = m[0]
            codigo_materia = m[1]
            dpto_codigo = m[2]

            for t in turnos:
                turno_id = t[0]
                turno_fecha = t[1]
                # formato API: YYYY-MM|YYYY
                if hasattr(turno_fecha, 'strftime'):
                    turno_api = f"{turno_fecha.strftime('%Y-%m')}|{turno_fecha.year}"
                else:
                    # fall back if string
                    turno_api = str(turno_fecha)

                try:
                    try:
                        mesa_info = getInfoMesa(dpto_codigo, int(codigo_materia), turno_api, cookie_code, csrf_code)
                        # If the server returned a refreshed CSRF token, update and retry once
                        if isinstance(mesa_info, dict) and 'csrf' in mesa_info:
                            csrf_code = mesa_info['csrf']
                            mesa_info = getInfoMesa(dpto_codigo, int(codigo_materia), turno_api, cookie_code, csrf_code)
                    except Exception as e:
                        # problemas con la respuesta (no JSON, HTML, etc.)
                        print(f"Respuesta inválida para {dpto_codigo} {codigo_materia} {turno_api}: {e}")
                        time.sleep(0.05)
                        continue

                    # Asegurar que la respuesta sea un dict con 'mesas'
                    if not isinstance(mesa_info, dict):
                        time.sleep(0.02)
                        continue

                    mesas_iter = mesa_info.get('mesas') if isinstance(mesa_info.get('mesas'), dict) else {}
                    for mesa_key, mesa_details in mesas_iter.items():
                        try:
                            fecha = datetime.strptime(mesa_details['fecha'], '%d/%m/%y').date()
                        except Exception:
                            fecha = None

                        insc_inicio = None
                        insc_fin = None
                        try:
                            if mesa_details.get('insc_inicio'):
                                insc_inicio = datetime.strptime(mesa_details['insc_inicio'], '%d/%m/%y %H:%M')
                            if mesa_details.get('insc_fin'):
                                insc_fin = datetime.strptime(mesa_details['insc_fin'], '%d/%m/%y %H:%M')
                        except Exception:
                            insc_inicio = None
                            insc_fin = None

                        mesas_row = {
                            'id_materia': materia_id,
                            'id_turno': turno_id,
                            'fecha': fecha.isoformat() if fecha else None,
                            'codigo': mesa_details.get('mesa_examen'),
                            'profesor': ', '.join(mesa_details.get('docentes', [])) if mesa_details.get('docentes') else None,
                            'hora_inicio': mesa_details.get('hora_inicio'),
                            'hora_fin': mesa_details.get('hora_fin'),
                            'tipo': mesa_details.get('tipo'),
                            'inscripcion_inicio': insc_inicio.isoformat() if insc_inicio else None,
                            'inscripcion_fin': insc_fin.isoformat() if insc_fin else None,
                            'cant_inscriptos': int(mesa_details.get('inscriptos', 0)) if mesa_details.get('inscriptos') else 0,
                            'carrera': mesa_details.get('carrera', ''),
                            'plan': mesa_details.get('plan', ''),
                            'grupo_carrera': mesa_details.get('grupo_carrera', ''),
                            'observaciones': mesa_details.get('observaciones', ''),
                            'capacidad': mesa_details.get('capacidad', ''),
                            'letra_desde': mesa_details.get('letra_desde', ''),
                            'letra_hasta': mesa_details.get('letra_hasta', ''),
                            'sede': mesa_details.get('sede', '')
                        }

                        todas.append(mesas_row)

                except Exception as e:
                    print(f"Error obteniendo mesa para {dpto_codigo} {codigo_materia} {turno_api}: {e}")
                finally:
                    # pequeño delay para no saturar el servidor
                    time.sleep(0.02)

        # Insertar en batch
        if todas:
            db.insert_mesas(todas)
        else:
            print('No se encontraron mesas para insertar.')

    except Exception as error:
        print(f"Error en fetch_and_insert_all_mesas: {error}")

if __name__ == "__main__":
    (html_code, cookie_code) = getHTMLandCookie()
    csrf_code = getCSRFcode(html_code)
    db = GuaraniDB()

    dptos = getDptos(html_code)
    db.insert_departamentos(dptos)

    turnos = getTurnos(html_code)
    formatted_turnos = format_turnos(turnos)
    print(formatted_turnos)
    db.insert_turnos(formatted_turnos)

    for dpto_codigo, dpto_nombre in dptos.items():
        materias = getMateriasFromDpto(dpto_codigo, cookie_code, csrf_code)
        db.insert_materias(materias, dpto_codigo)

    mesas = getInfoMesa("CO", 7958, "2024-12|2024", cookie_code, csrf_code)
    print(json.dumps(mesas['mesas'], indent=4))


    db.close_connection()
