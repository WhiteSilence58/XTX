FROM python:3.11-slim

# LibreOffice + Fonts (Helvetica = URW Nimbus Sans)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    libreoffice-common \
    fonts-liberation \
    fonts-liberation2 \
    fonts-dejavu \
    fonts-dejavu-core \
    fonts-urw-base35 \
    fontconfig \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ /app/
COPY frontend /frontend

# LibreOffice braucht ein Home-Verzeichnis
ENV HOME=/tmp

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8053"]
