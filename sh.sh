#!/bin/bash

# Özel bir Docker network oluşturma (eğer yoksa)
docker network create votingapp_network || true

# PostgreSQL konteynerini başlatma
docker run -d \
    --name db \
    --network votingapp_network \
    -e POSTGRES_USER=user \
    -e POSTGRES_PASSWORD=password \
    -e POSTGRES_DB=votingapp_db \
    postgres:16

# PostgreSQL'in hazır olup olmadığını kontrol et
echo "Veritabanının hazır hale gelmesi bekleniyor..."
until docker exec postgres_db pg_isready -U user; do
  >&2 echo "Veritabanı henüz hazır değil - bekleniyor..."
  sleep 2
done

echo "Veritabanı hazır! Flask uygulaması başlatılıyor."

# Flask uygulamasını başlatma
