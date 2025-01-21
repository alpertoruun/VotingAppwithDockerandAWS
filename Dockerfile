FROM continuumio/miniconda3

WORKDIR /opt/votingapp

RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \    
    cmake \
    build-essential \
    cmake \
    ffmpeg \
    cron \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/votingapp

ENV GITHUB_TOKEN="xxxxxxxx"
RUN echo "cloning" && git clone https://$GITHUB_TOKEN@github.com/alpertoruun/VotingAppwithDockerandAWS.git .

RUN pip install --no-cache-dir -r requirements.txt

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

RUN mkdir -p /opt/votingapp/static/uploads && \
    chmod 777 /opt/votingapp/static/uploads

EXPOSE 5000
CMD ["/opt/votingapp/start.sh"]