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

ENV DATABASE_URL=postgresql://user:password@db:5432/votingapp_db
ENV SECRET_KEY=928ee491f7ab3d6694821227fba3c33b
ENV DEBUG=True
ENV APP_SETTINGS=config.DevelopmentConfig
ENV FLASK_APP=src
ENV FLASK_DEBUG=1
ENV FERNET_KEY="H_KAHfq4pkq6AnlNwmzVHs2RrSzi9jGykPp8EkGc4BA="
ENV SERVER_NAME=localhost:5000
ENV PREFERRED_URL_SCHEME=http

CMD ["flask", "run", "--host=0.0.0.0"]
EXPOSE 5000
