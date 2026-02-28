# Sync Turnos

Script independiente que sincroniza los **turnos de examen del sistema Guaraní (UNS)** con una base de datos externa a través de una API REST.

## Descripción

El script se ejecuta de forma continua con un intervalo configurable (por defecto cada 1 hora). En cada ciclo:

1. **Obtiene los turnos actuales de Guaraní** mediante scraping de la página pública de mesas de examen.
2. **Consulta los turnos almacenados** en la base de datos del proyecto destino a través de la API.
3. **Compara ambas listas** y realiza las acciones necesarias para mantener la base de datos sincronizada.

### Lógica de sincronización

| Situación | Acción |
|---|---|
| Turno aparece en Guaraní pero **no existe** en la DB | Se inserta con `is_active = true` |
| Turno **desaparece** de Guaraní pero sigue en la DB como activo | Se actualiza a `is_active = false` |
| Turno **reaparece** en Guaraní pero estaba en la DB como inactivo | Se reactiva a `is_active = true` |
| Turno existe en la DB con el estado correcto | No se modifica |

### Ejemplo de flujo en el tiempo

- **Semana 1:** Guaraní muestra `2026-01`, `2026-02`, `2026-03` → se insertan los tres con `is_active = true`.
- **Semana 3:** Guaraní ahora muestra `2026-02`, `2026-03`, `2026-04` → se desactiva `2026-01`, se inserta `2026-04`. La DB queda con los cuatro turnos, solo `2026-01` en `false`.
- **Semana 5:** Guaraní muestra `2026-03`, `2026-04`, `2026-06` → se desactiva `2026-02`, se inserta `2026-06`.

De esta manera la base de datos conserva el **historial completo** de todos los turnos que existieron, diferenciando cuáles son los actualmente vigentes.

## Estructura de archivos

```
sync_turnos/
├── docker-compose.yml   # Configuración de Docker Compose
├── Dockerfile           # Imagen Docker del servicio
├── README.md            # Este archivo
├── requirements.txt     # Dependencias de Python
└── sync_turnos.py       # Script principal
```

## API utilizada

El script se comunica con la API del proyecto destino en `https://guarani.chewer.net`:

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/turnos/` | Obtiene todos los turnos almacenados |
| `POST` | `/api/turnos/` | Inserta un turno nuevo |
| `DELETE` | `/api/turnos/?fecha=YYYY-MM` | Elimina un turno por fecha |

Todas las peticiones requieren el header `X-API-Key` para autenticación.

### Formato del body (POST)

```json
{
  "fecha": "2026-03",
  "is_active": true
}
```

> **Nota:** Como la API no tiene un endpoint de actualización (PUT/PATCH), para cambiar el `is_active` de un turno se realiza un `DELETE` seguido de un `POST` con el nuevo estado.

## Variables de entorno

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `SYNC_INTERVAL_HOURS` | Intervalo entre sincronizaciones (en horas). Acepta decimales (ej: `0.5` = 30 min) | `1` |
| `TZ` | Zona horaria del contenedor | `America/Argentina/Buenos_Aires` |

## Ejecución

### Con Docker (recomendado)

```bash
docker compose up -d
```

Para ver los logs en tiempo real:

```bash
docker compose logs -f
```

Para detener el servicio:

```bash
docker compose down
```

### Sin Docker

Requiere Python 3.10+.

```bash
pip install -r requirements.txt
python sync_turnos.py
```

Opcionalmente se puede configurar el intervalo:

```bash
SYNC_INTERVAL_HOURS=0.5 python sync_turnos.py
```

## Dependencias

- **Python 3.10+**
- **requests** — para las peticiones HTTP (scraping de Guaraní y llamadas a la API)
