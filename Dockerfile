# Temel Python imajını kullanıyoruz
FROM python:3.12-slim

# Çalışma dizinini ayarlıyoruz
WORKDIR /opt/votingapp

# Git'i yükleyin
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Private GitHub repo'yu clone etmek için GITHUB_TOKEN ortam değişkenini kullanın
ARG GITHUB_TOKEN
RUN git clone https://$GITHUB_TOKEN@github.com/alpertoruun/VotingAppwithDockerandAWS.git .

# Gereksinimleri yükleyin
RUN pip install --no-cache-dir -r requirements.txt

# Alembic ve veritabanı bağlantısı için ortam değişkenlerini ayarlayın
ENV DATABASE_URL=postgresql://user:password@db:5432/votingapp_db

# Alembic migration dosyalarını uygula
RUN alembic init migrations && alembic revision --autogenerate -m "The first Commit" && alembic upgrade head

# Uygulamayı başlat
CMD ["flask", "run", "--host=0.0.0.0"]
EXPOSE 5000
