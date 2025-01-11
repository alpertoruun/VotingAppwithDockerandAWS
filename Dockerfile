FROM continuumio/miniconda3

WORKDIR /opt/votingapp

# Sistem paketleri
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \    
    cmake \
    cron \
    build-essential \
    && apt-get clean

ARG GITHUB_TOKEN
RUN echo "cloningg"
RUN git clone https://${GITHUB_TOKEN}@github.com/alpertoruun/VotingAppwithDockerandAWS.git .
    
# Conda environment
COPY environment.yml .
RUN conda env create -f environment.yml

# Aktivasyon için shell init
SHELL ["conda", "run", "-n", "myenv", "/bin/bash", "-c"]

# Ortam değişkenleri
ENV PYTHONUNBUFFERED=1 \
    DATABASE_URL=postgresql://postgres:123@localhost/votingdb \
    SECRET_KEY=928ee491f7ab3d6694821227fba3c33b \
    DEBUG=True \
    APP_SETTINGS=config.DevelopmentConfig \
    FLASK_APP=src \
    FLASK_DEBUG=1 \
    FERNET_KEY="H_KAHfq4pkq6AnlNwmzVHs2RrSzi9jGykPp8EkGc4BA=" \
    PREFERRED_URL_SCHEME=http \
    SERVER_NAME="localhost:5000"

RUN mkdir -p /opt/votingapp/logs

# Cron ayarları
RUN chmod +x vote_counter.py
RUN touch /var/log/cron.log
RUN echo "* * * * * cd /opt/votingapp && conda run -n myenv python /opt/votingapp/vote_counter.py >> /var/log/cron.log 2>&1" > /etc/cron.d/vote-counter
RUN chmod 0644 /etc/cron.d/vote-counter
RUN crontab /etc/cron.d/vote-counter

# Başlangıç scripti oluştur
RUN echo '#!/bin/bash\n\
service cron start\n\
conda run -n myenv gunicorn --preload --workers=1 --threads=4 --timeout 120 --worker-class=gthread --bind 0.0.0.0:5000 --log-level=debug --access-logfile=/opt/votingapp/logs/gunicorn.log --error-logfile=/opt/votingapp/logs/gunicorn.log src:app' > /opt/votingapp/start.sh

RUN chmod +x /opt/votingapp/start.sh

EXPOSE 5000
CMD ["/opt/votingapp/start.sh"]