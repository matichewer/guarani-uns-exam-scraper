from src.auth import getHTMLandCookie, getCSRFcode
from src.guarani import getTurnos, format_turnos
from src.db_factory import get_db


def main():
    html, cookie = getHTMLandCookie()
    csrf = getCSRFcode(html)
    db = get_db()

    turnos = getTurnos(html)
    formatted = format_turnos(turnos)
    db.insert_turnos(formatted)
    print('Turnos insertados:', len(formatted))
    db.close_connection()


if __name__ == '__main__':
    main()
