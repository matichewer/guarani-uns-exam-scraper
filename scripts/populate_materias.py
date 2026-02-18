from src.auth import getHTMLandCookie, getCSRFcode
from src.guarani import getDptos, getMateriasFromDpto
from src.db_factory import get_db


def main():
    html, cookie = getHTMLandCookie()
    csrf = getCSRFcode(html)
    db = get_db()

    dptos = getDptos(html)

    total = 0
    for dpto_codigo in dptos.keys():
        materias = getMateriasFromDpto(dpto_codigo, cookie, csrf)
        if materias:
            db.insert_materias(materias, dpto_codigo)
            total += len(materias)
    print('Materias insertadas (total aprox):', total)
    db.close_connection()


if __name__ == '__main__':
    main()
