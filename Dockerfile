# Python 3.11 slim image kullan (güvenlik ve boyut için)
FROM python:3.11-slim

# Metadata
LABEL maintainer="Erkan"
LABEL description="Minibar Takip Sistemi - Docker Container"

# Çalışma dizini
WORKDIR /app

# Sistem bağımlılıkları (PostgreSQL client ve curl)
RUN apt-get update && apt-get install -y \
    libpq5 \
    postgresql-client \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Python bağımlılıklarını kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# ML models dizini oluştur
RUN mkdir -p /app/ml_models && \
    chmod 755 /app/ml_models

# Entrypoint script'ini executable yap
RUN chmod +x docker-entrypoint.sh

# Güvenlik: Non-root user oluştur
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Volume tanımla (persistent storage için)
VOLUME ["/app/ml_models"]

# Port expose et
EXPOSE 5000

# Health check ekle (startup süresi için start-period artırıldı)
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=5 \
    CMD curl -f http://localhost:5000/health || exit 1

# Entrypoint ve CMD (safe_deploy.py kaldırıldı - entrypoint zaten aynı işi yapıyor)
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
