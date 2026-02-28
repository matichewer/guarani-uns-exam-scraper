FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sync_turnos.py .

CMD ["python", "-u", "sync_turnos.py"]
