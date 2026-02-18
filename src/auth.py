from bs4 import BeautifulSoup
import requests
import re
import logging
from logging.config import fileConfig
from pathlib import Path

fileConfig('logs/config.ini', defaults={ 'file-name': Path(__file__).stem })
log = logging.getLogger()

url_main = "https://g3w.uns.edu.ar/guarani3w/mesas_publica/buscar_mesas"


def getHTMLandCookie():
    response = requests.get(url_main)
    html = BeautifulSoup(response.text, 'html.parser')
    html_code = html.prettify()
    cookie_code = response.cookies.get("siu_sess_guarani3w_UNS")
    log.info('Cookie: ' + str(cookie_code))
    return (html_code, cookie_code)


def getCSRFcode(html_code):
    csrf_match = re.findall(r'csrf[a-z0-9]*', html_code)
    csrf_code = csrf_match[1]
    log.info('CSRF: ' + csrf_code)
    return csrf_code
