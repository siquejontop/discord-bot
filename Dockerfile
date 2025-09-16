# Usar una imagen base con Python 3.11
FROM python:3.11-slim

# Instalar libopus
RUN apt-get update && apt-get install -y libopus0

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar archivos
COPY . .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Comando para iniciar la app
CMD ["python", "main.py"]
