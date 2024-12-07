# Guaraní UNS Exam Scraper

This project is a Python script designed to get final exam information from Guaraní system of Universidad Nacional del Sur (UNS).


## Features

- Retrieves HTML and session cookie from the UNS Guaraní system.
- Extracts CSRF token for secure requests.
- Fetches list of academic departments.
- Retrieves available exam periods.
- Allows to make a request of exam schedules for specific departments, subjects, and periods.

## Create DB
```bash
psql --host localhost --port 5432 --username postgres --dbname guarani --file db.sql  
```