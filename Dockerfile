# Temel Python imajını kullanıyoruz
FROM python:3.12-slim

# Gerekli bağımlılıkları kuruyoruz
RUN apt-get update && apt-get install -y \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    build-essential \
    cmake \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizinini ayarlıyoruz
WORKDIR /opt/votingapp

ENV GITHUB_TOKEN=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
RUN echo "cloning" && git clone https://$GITHUB_TOKEN@github.com/alpertoruun/VotingAppwithDockerandAWS.git .

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=postgresql://postgres:mypas!word@voting-app.cn0segwuk4m7.eu-central-1.rds.amazonaws.com:5432/postgres

ENV SECRET_KEY=928ee491f7ab3d6694821227fba3c33b
ENV DEBUG=False
ENV APP_SETTINGS=config.DevelopmentConfig
ENV FLASK_APP=src
ENV FLASK_DEBUG=0
ENV FERNET_KEY="H_KAHfq4pkq6AnlNwmzVHs2RrSzi9jGykPp8EkGc4BA="
# Load balancer endpoint'ini kullan
ENV SERVER_NAME=voting-app-alb-1059205030.eu-central-1.elb.amazonaws.com
ENV PREFERRED_URL_SCHEME=http

CMD ["gunicorn", "--workers=1", "--threads=4", "--timeout", "120", "--worker-class=gthread", "--bind", "0.0.0.0:5000", "--log-level=info", "src:app"]
EXPOSE 5000