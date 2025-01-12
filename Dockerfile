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
RUN echo "cloning"
RUN git clone https://${GITHUB_TOKEN}@github.com/alpertoruun/VotingAppwithDockerandAWS.git .
    
# Conda environment
COPY environment.yml .
RUN conda env create -f environment.yml

# Aktivasyon için shell init
SHELL ["conda", "run", "-n", "myenv", "/bin/bash", "-c"]

# Ortam değişkenleri
ENV PYTHONUNBUFFERED=1 \
    DATABASE_URL=postgresql://postgres:mypassword1.@votingdb.cvc6y2g2aoqc.eu-west-1.rds.amazonaws.com:5432/postgres \
    SECRET_KEY=928ee491f7ab3d6694821227fba3c33b \
    DEBUG=False \
    APP_SETTINGS=config.DevelopmentConfig \
    FLASK_APP=src \
    FLASK_DEBUG=0 \
    FERNET_KEY="H_KAHfq4pkq6AnlNwmzVHs2RrSzi9jGykPp8EkGc4BA=" \
    PREFERRED_URL_SCHEME=http \
    SERVER_NAME="voting-elb-1942491963.eu-west-1.elb.amazonaws.com"

RUN mkdir -p /opt/votingapp/logs

RUN chmod +x /opt/votingapp/cron_wrapper.sh

# Cron ayarları
RUN touch /var/log/cron.log
COPY <<'EOF' /etc/cron.d/vote-counter
* * * * * /opt/votingapp/cron_wrapper.sh >> /var/log/cron.log
EOF

RUN chmod 0644 /etc/cron.d/vote-counter
RUN crontab /etc/cron.d/vote-counter

# Başlangıç scripti
RUN chmod +x /opt/votingapp/start.sh

EXPOSE 5000
CMD ["/opt/votingapp/start.sh"]