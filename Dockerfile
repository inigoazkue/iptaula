FROM python:3.12-slim
# Solo necesarios durante el build (red corporativa con proxy obligatorio
# para salir a Internet); se limpian antes de copiar la app para que no
# queden en la imagen final, que no necesita salir a Internet en runtime.
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ENV HTTP_PROXY=${HTTP_PROXY} HTTPS_PROXY=${HTTPS_PROXY} NO_PROXY=${NO_PROXY} \
    http_proxy=${HTTP_PROXY} https_proxy=${HTTPS_PROXY} no_proxy=${NO_PROXY}

# El proxy corporativo (Zscaler) inspecciona el TLS y re-firma con su
# propio certificado raíz; sin él, pip no puede verificar la conexión a
# PyPI. Se instala en el almacén de confianza del sistema y se le indica
# a pip explícitamente que lo use (pip no confía en el almacén del SO por
# defecto, lleva su propia lista de certificados).
COPY certs/ZscalerRootCertificate-2048-SHA256.crt /usr/local/share/ca-certificates/zscaler.crt
RUN update-ca-certificates
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# iputils-ping: IP-tauletako ping botoiak `ping` bitarra behar du kontenitzailean.
RUN apt-get update && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
ENV HTTP_PROXY= HTTPS_PROXY= NO_PROXY= http_proxy= https_proxy= no_proxy=
COPY app/ /app/
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
