FROM debian:13.4

# Install system dependencies in one layer, clear APT cache
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential nodejs npm python3 python3-pip ripgrep ffmpeg gcc python3-dev libffi-dev curl unzip git && \
    rm -rf /var/lib/apt/lists/*

# Install bun (Bun/JS runtime for gbrain MCP server)
RUN curl -fsSL https://github.com/oven-sh/bun/releases/download/bun-v1.3.13/bun-linux-aarch64-profile.zip -o /tmp/bun.zip && \
    unzip -o /tmp/bun.zip -d /tmp/ && \
    cp /tmp/bun-linux-aarch64-profile/bun-profile /usr/local/bin/bun && \
    chmod +x /usr/local/bin/bun && \
    rm -rf /tmp/bun* && \
    ln -sf /usr/local/bin/bun /usr/local/bin/bunx

# Clone gbrain repository for knowledge graph
RUN git clone https://github.com/garrytan/gbrain.git /root/gbrain && \
    cd /root/gbrain && bun install --frozen-lockfile

# Create gbrain data directory
RUN mkdir -p /root/.gbrain

COPY . /opt/drewgent
WORKDIR /opt/drewgent

# Install Python and Node dependencies in one layer, no cache
RUN pip install --no-cache-dir -e ".[all]" --break-system-packages && \
    npm install --prefer-offline --no-audit && \
    npx playwright install --with-deps chromium --only-shell && \
    cd /opt/drewgent/scripts/whatsapp-bridge && \
    npm install --prefer-offline --no-audit && \
    npm cache clean --force

WORKDIR /opt/drewgent
RUN chmod +x /opt/drewgent/docker/entrypoint.sh

ENV HERMES_HOME=/opt/data
VOLUME [ "/opt/data" ]
ENTRYPOINT [ "/opt/drewgent/docker/entrypoint.sh" ]
