from bs4 import BeautifulSoup
import requests
import re

import logging
from logging.config import fileConfig
from pathlib import Path

fileConfig('logs/config.ini', defaults={ 'file-name': Path(__file__).stem })
log = logging.getLogger()


url = "https://g3w.uns.edu.ar/guarani3w/mesas_publica/buscar_mesas"

def getCookieAndCSRF():

    # Realizar la peticion GET
    response = requests.get(url)

    # Guardar la cookie en una variable
    cookie_code = response.cookies["siu_sess_guarani3w_UNS"]
    log.info('Cookie: ' + cookie_code) 

    # Parsear el HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    # Guardar el codigo CSRF en el HTML usando expresion regular
    match = re.findall(r'csrf[a-z0-9]*', soup.prettify())
    csrf_code = match[1]
    log.info('CSRF:   ' + csrf_code) 

    return (csrf_code, cookie_code)



def getJson(depto, materia, turno):

    (csrf_code, cookie_code) = getCookieAndCSRF()

    headers = {"Cookie": f"siu_sess_guarani3w_UNS={cookie_code}"}
    data = {"depto": depto, "materia": materia, "turno": turno, "__csrf": csrf_code}

    response = requests.post(url, headers=headers, data=data)

    log.info("Response: " + str(response.status_code))
    print("\n" + response.text)



if __name__ == "__main__":
    getJson("CO", 7911, "2022-12|2022")
