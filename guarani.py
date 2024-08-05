from bs4 import BeautifulSoup
import requests
import re
import json

import logging
from logging.config import fileConfig
from pathlib import Path

fileConfig('logs/config.ini', defaults={ 'file-name': Path(__file__).stem })
log = logging.getLogger()


url = "https://g3w.uns.edu.ar/guarani3w/mesas_publica/buscar_mesas"


def getHTMLandCookie():
    # Realizar la peticion GET
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

    log.info(f'Cantidad de Dptos: {len(dptos_dict)}')
    log.info(f'Dptos del Guarani: {dptos_dict}')

    return dptos_dict

def getTurnos(html_code):    
    turnos_array = re.findall(r'[0-9]{4}-[0-9]{2}\|[0-9]{4}', html_code)
    log.info('Cantidad de Turnos: ' + str(len(turnos_array)))
    log.info('Turnos del Guarani: ' + str(turnos_array))
    return turnos_array

def getInfoMesa(dpto, materia, turno, cookie_code, csrf_code):

    headers = {"Cookie": f"siu_sess_guarani3w_UNS={cookie_code}"}
    data = {"depto": dpto, "materia": materia, "turno": turno, "__csrf": csrf_code}

    response = requests.post(url, headers=headers, data=data)

    return response.json()



if __name__ == "__main__":
    (html_code, cookie_code) = getHTMLandCookie()
    csrf_code = getCSRFcode(html_code)
    dptos = getDptos(html_code)
    turnos = getTurnos(html_code)

    mesas = getInfoMesa("CO", 5523, "2024-08|2024", cookie_code, csrf_code)
    print(json.dumps(mesas['mesas'], indent=4))