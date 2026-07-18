FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Corre migraciones y luego arranca la API (ver entrypoint.sh).
# Usamos bash explícito porque el bit de ejecución no sobrevive al montaje desde Windows.
CMD ["bash", "entrypoint.sh"]
