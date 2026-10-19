FROM ghcr.io/home-assistant/amd64-base-debian:bookworm

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive WINEDEBUG=-all WINEARCH=win64 WINEPREFIX=/data/wine
ENV S6_CMD_RECEIVE_SIGNALS=1

RUN dpkg --add-architecture i386 \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates curl tar bash python3 xvfb xauth wine wine32 wine64 \
       lib32gcc-s1 lib32stdc++6 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/steamcmd \
    && curl -4 -fL --retry 8 --connect-timeout 15 \
       https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz \
       -o /tmp/steamcmd.tgz \
    && tar -xzf /tmp/steamcmd.tgz -C /opt/steamcmd \
    && rm /tmp/steamcmd.tgz

COPY run.sh configure.py services.py update.py /
RUN chmod +x /run.sh
CMD ["/run.sh"]
