from src.guarani import getHTMLandCookie, getCSRFcode, GuaraniDB, fetch_and_insert_all_mesas, getDptos

def main():
    html_code, cookie_code = getHTMLandCookie()
    csrf_code = getCSRFcode(html_code)
    db = GuaraniDB()

    # Ensure departamentos/turnos/materias are present
    dptos = getDptos(html_code)
    db.insert_departamentos(dptos)

    # Now fetch and insert mesas
    fetch_and_insert_all_mesas(db, cookie_code, csrf_code)

    db.close_connection()

if __name__ == '__main__':
    main()
