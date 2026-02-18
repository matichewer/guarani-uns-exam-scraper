from src.auth import getHTMLandCookie, getCSRFcode
from src.guarani import getDptos
from src.db_factory import get_db


def main():
    html, cookie = getHTMLandCookie()
    csrf = getCSRFcode(html)
    db = get_db()

    dptos = getDptos(html)
    db.insert_departamentos(dptos)
    print('Departamentos insertados:', len(dptos))
    db.close_connection()


if __name__ == '__main__':
    main()
