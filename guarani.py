from bs4 import BeautifulSoup
import requests
import re
import json

import logging
from logging.config import fileConfig
from pathlib import Path

from datetime import datetime

from db import GuaraniDB

fileConfig('logs/config.ini', defaults={ 'file-name': Path(__file__).stem })
log = logging.getLogger()


url = "https://g3w.uns.edu.ar/guarani3w/mesas_publica/buscar_mesas"


def getHTMLandCookie():
    response = requests.get(url)

    # Parsear el HTML
    html = BeautifulSoup(response.text, 'html.parser')
    html_code = html.prettify()

    # Guardar la cookie en una variable
    cookie_code = response.cookies["siu_sess_guarani3w_UNS"]
    log.info('Cookie: ' + cookie_code) 

    return (html_code, cookie_code)

def getCSRFcode(html_code):
    # Buscar y retornar el codigo CSRF del codigo HTML usando expresion regular
    csrf_match = re.findall(r'csrf[a-z0-9]*', html_code)
    csrf_code = csrf_match[1]
    log.info('CSRF: ' + csrf_code) 
    return csrf_code


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
    headers = {"Cookie": f"siu_sess_guarani3w_UNS={cookie_code}"}
    data = {"depto": dpto, "materia": materia, "turno": turno, "__csrf": csrf_code}
    response = requests.post(url, headers=headers, data=data)
    return response.json()

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