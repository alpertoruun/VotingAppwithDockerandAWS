# Temel Python imajını kullanıyoruz
FROM python:3.12-slim

# Gerekli bağımlılıkları kuruyoruz (cron ekledik)
RUN apt-get update && apt-get install -y \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    build-essential \
    cmake \
    ffmpeg \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizinini ayarlıyoruz
WORKDIR /opt/votingapp

ENV GITHUB_TOKEN=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
RUN echo "cloning" && git clone -b comeBack https://$GITHUB_TOKEN@github.com/alpertoruun/VotingAppwithDockerandAWS.git .

RUN pip install --no-cache-dir -r requirements.txt

# Cron için gerekli dizin ve log dosyaları
RUN mkdir -p /opt/votingapp/logs
RUN touch /var/log/cron.log

# Cron ayarları
COPY <<'EOF' /etc/cron.d/vote-counter
* * * * * /opt/votingapp/cron_wrapper.sh >> /var/log/cron.log
EOF

RUN chmod 0644 /etc/cron.d/vote-counter
RUN crontab /etc/cron.d/vote-counter
RUN chmod +x /opt/votingapp/cron_wrapper.sh
RUN chmod +x /opt/votingapp/start.sh

ENV DATABASE_URL="postgresql://postgres:mypassword1.@votingdb.cvc6y2g2aoqc.eu-west-1.rds.amazonaws.com:5432/postgres"
ENV SECRET_KEY=928ee491f7ab3d6694821227fba3c33b
ENV DEBUG=False
ENV APP_SETTINGS=config.DevelopmentConfig
ENV FLASK_APP=src
ENV FLASK_DEBUG=0
ENV FERNET_KEY="H_KAHfq4pkq6AnlNwmzVHs2RrSzi9jGykPp8EkGc4BA="
ENV PREFERRED_URL_SCHEME=http

EXPOSE 5000
CMD ["/opt/votingapp/start.sh"]