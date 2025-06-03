# Utilise une image Python complète
FROM python:3.10-slim

# Installation des dépendances système nécessaires pour face_recognition et OpenCV
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    libboost-python-dev \
    libboost-thread-dev \
    libssl-dev \
    python3-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Dossier de travail
WORKDIR /app

# Copie du code source dans le conteneur
COPY . .

# Installation des dépendances Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Lancement de l'application via Gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT app:app"]

