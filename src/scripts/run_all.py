"""Orquestador de scripts dentro de `src.scripts`.
"""
from scripts import populate_departamentos, populate_turnos, populate_materias


def main():
    populate_departamentos.main()
    populate_turnos.main()
    populate_materias.main()


if __name__ == '__main__':
    main()
