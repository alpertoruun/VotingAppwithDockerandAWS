FROM continuumio/miniconda3

WORKDIR /opt/votingapp

# Sistem paketleri
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \    
    cmake \
    build-essential \
    && apt-get clean


ARG GITHUB_TOKEN
RUN echo ""
RUN git clone https://${GITHUB_TOKEN}@github.com/alpertoruun/VotingAppwithDockerandAWS.git .
    
# Conda environment
COPY environment.yml .
RUN conda env create -f environment.yml

# Aktivasyon için shell init
SHELL ["conda", "run", "-n", "myenv", "/bin/bash", "-c"]

# Ortam değişkenleri
ENV PYTHONUNBUFFERED=1 \
    DATABASE_URL=postgresql://postgres:mypas!word@database-1.cvc6y2g2aoqc.eu-west-1.rds.amazonaws.com:5432/postgres \
    SECRET_KEY=928ee491f7ab3d6694821227fba3c33b \
    DEBUG=False \
    APP_SETTINGS=config.DevelopmentConfig \
    FLASK_APP=src \
    FLASK_DEBUG=0 \
    FERNET_KEY="H_KAHfq4pkq6AnlNwmzVHs2RrSzi9jGykPp8EkGc4BA=" \
    PREFERRED_URL_SCHEME=http
    SERVER_NAME="voting-app-lb-28816073.eu-west-1.elb.amazonaws.com"

EXPOSE 5000
CMD ["conda", "run", "-n", "myenv", "gunicorn", "--workers=1", "--threads=4", "--timeout", "120", "--worker-class=gthread", "--bind", "0.0.0.0:5000", "--forwarded-allow-ips=*", "--proxy-allow-from=*", "--log-level=debug", "--access-logfile", "-", "--error-logfile", "-", "src:app"]