"""
Script independiente para sincronizar turnos de Guaraní con la API del proyecto B.

Se ejecuta cada 1 hora de forma continua:
1. Obtiene los turnos actuales del Guaraní (scraping)
2. Obtiene los turnos almacenados en la API del proyecto B
3. Inserta turnos nuevos con is_active=True
4. Marca como is_active=False los turnos que ya no están en Guaraní
5. Reactiva (is_active=True) turnos que vuelvan a aparecer en Guaraní
"""

import os
import re
import time
import logging
import requests
from datetime import datetime

# ── Configuración ──────────────────────────────────────────────────────────────
GUARANI_URL = "https://g3w.uns.edu.ar/guarani3w/mesas_publica/buscar_mesas"

API_BASE_URL = "https://guarani.chewer.net"
API_TURNOS_URL = f"{API_BASE_URL}/api/turnos/"
API_KEY = "clave-super-secreta-para-usar-api-de-turnos"
API_HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json",
}

INTERVALO_HORAS = float(os.getenv("SYNC_INTERVAL_HOURS", "1"))

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Funciones de Guaraní ───────────────────────────────────────────────────────

def obtener_turnos_guarani() -> list[str]:
    """
    Hace scraping a Guaraní y devuelve la lista de turnos actuales.
    Cada turno es un string con formato 'YYYY-MM' (ej: '2026-03').
    """
    response = requests.get(GUARANI_URL, timeout=30)
    response.raise_for_status()

    html = response.text
    # Los turnos en el HTML tienen formato: 2026-03|2026
    raw = re.findall(r'[0-9]{4}-[0-9]{2}\|[0-9]{4}', html)
    # Extraer solo la parte YYYY-MM
    turnos = list({t.split("|")[0] for t in raw})
    turnos.sort()

    log.info(f"Turnos en Guaraní: {turnos}")
    return turnos


# ── Funciones de la API (proyecto B) ──────────────────────────────────────────

def api_get_turnos() -> list[dict]:
    """
    GET /api/turnos/ → devuelve lista de turnos almacenados.
    Cada elemento tiene al menos: { "fecha": "2026-03", "is_active": true/false }
    """
    response = requests.get(API_TURNOS_URL, headers=API_HEADERS, timeout=15)
    response.raise_for_status()
    data = response.json()
    log.info(f"Turnos en API: {len(data)} registros")
    return data


def api_post_turno(fecha: str, is_active: bool = True) -> bool:
    """
    POST /api/turnos/ → inserta un turno. Devuelve True si fue exitoso.
    """
    body = {"fecha": fecha, "is_active": is_active}
    response = requests.post(API_TURNOS_URL, headers=API_HEADERS, json=body, timeout=15)
    if response.ok:
        log.info(f"POST turno '{fecha}' (is_active={is_active}) → {response.status_code}")
        return True
    else:
        log.warning(f"POST turno '{fecha}' falló → {response.status_code}: {response.text}")
        return False


def api_delete_turno(fecha: str) -> bool:
    """
    DELETE /api/turnos/?fecha=YYYY-MM → elimina un turno. Devuelve True si fue exitoso.
    """
    response = requests.delete(
        API_TURNOS_URL, headers=API_HEADERS, params={"fecha": fecha}, timeout=15
    )
    if response.ok:
        log.info(f"DELETE turno '{fecha}' → {response.status_code}")
        return True
    else:
        log.warning(f"DELETE turno '{fecha}' falló → {response.status_code}: {response.text}")
        return False


# ── Lógica de sincronización ──────────────────────────────────────────────────

def sincronizar():
    """
    Sincroniza los turnos de Guaraní con la base de datos del proyecto B.

    - Turnos nuevos en Guaraní → se insertan con is_active=True
    - Turnos que ya no están en Guaraní pero sí en la DB con is_active=True
      → se eliminan y reinsertan con is_active=False
    - Turnos que reaparecen en Guaraní pero estaban en la DB con is_active=False
      → se eliminan y reinsertan con is_active=True
    - Turnos que ya existen con el estado correcto → no se tocan
    """
    log.info("═" * 60)
    log.info("Iniciando sincronización de turnos")

    # 1. Obtener turnos actuales de Guaraní
    try:
        turnos_guarani = set(obtener_turnos_guarani())
    except Exception as e:
        log.error(f"Error obteniendo turnos de Guaraní: {e}")
        return

    # 2. Obtener turnos actuales de la API
    try:
        turnos_api = api_get_turnos()
    except Exception as e:
        log.error(f"Error obteniendo turnos de la API: {e}")
        return

    # Mapear los turnos de la API: fecha → is_active
    db_map: dict[str, bool] = {t["fecha"]: t["is_active"] for t in turnos_api}
    fechas_db = set(db_map.keys())

    # 3. Turnos nuevos: están en Guaraní pero NO en la DB → insertar con is_active=True
    nuevos = turnos_guarani - fechas_db
    for fecha in sorted(nuevos):
        log.info(f"  [NUEVO] Insertando turno '{fecha}' con is_active=True")
        api_post_turno(fecha, is_active=True)

    # 4. Turnos que ya no están en Guaraní pero están activos en DB → desactivar
    for fecha in sorted(fechas_db - turnos_guarani):
        if db_map[fecha] is True:
            log.info(f"  [DESACTIVAR] Turno '{fecha}' ya no está en Guaraní → is_active=False")
            api_delete_turno(fecha)
            api_post_turno(fecha, is_active=False)

    # 5. Turnos que reaparecen en Guaraní pero están inactivos en DB → reactivar
    for fecha in sorted(turnos_guarani & fechas_db):
        if db_map[fecha] is False:
            log.info(f"  [REACTIVAR] Turno '{fecha}' volvió a Guaraní → is_active=True")
            api_delete_turno(fecha)
            api_post_turno(fecha, is_active=True)

    log.info("Sincronización finalizada")
    log.info("═" * 60)


# ── Loop principal ────────────────────────────────────────────────────────────

def main():
    log.info("Iniciando servicio de sincronización de turnos")
    log.info(f"Intervalo: cada {INTERVALO_HORAS} hora(s)")

    while True:
        try:
            sincronizar()
        except Exception as e:
            log.error(f"Error inesperado durante la sincronización: {e}")

        proxima = datetime.now().strftime("%H:%M:%S")
        log.info(f"Próxima ejecución en {INTERVALO_HORAS}h (esperando desde {proxima})")
        time.sleep(INTERVALO_HORAS * 3600)


if __name__ == "__main__":
    main()
