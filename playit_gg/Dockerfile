FROM ghcr.io/home-assistant/amd64-base-debian:bookworm

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl python3 \
    && rm -rf /var/lib/apt/lists/*

# Official amd64 agent, pinned so rebuilds do not silently change versions.
RUN curl -fL --retry 8 --connect-timeout 15 \
       https://github.com/playit-cloud/playit-agent/releases/download/v1.0.10/playit-linux-amd64 \
       -o /usr/local/bin/playit \
    && echo "2df7d9f10227ab312b1ad341853db4e8a8243df5cfcdbae58713a4271711c339  /usr/local/bin/playit" | sha256sum -c - \
    && chmod 755 /usr/local/bin/playit

COPY run.py /run.py
CMD ["python3", "/run.py"]
