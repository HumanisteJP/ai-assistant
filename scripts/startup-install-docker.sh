#!/usr/bin/env bash
set -eux
# Docker + docker compose plugin + ffmpeg
apt-get update -y
apt-get install -y ca-certificates curl gnupg lsb-release ffmpeg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# ---------- Google Cloud SDK (gcloud) ----------
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
  | tee /etc/apt/sources.list.d/google-cloud-sdk.list
curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
  | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
apt-get update -y
apt-get install -y google-cloud-cli

# Configure Artifact Registry credential helper (once is enough)
gcloud auth configure-docker asia-northeast1-docker.pkg.dev --quiet

systemctl enable --now docker
# non-root user (optional)
useradd -m -s /bin/bash yata || true
usermod -aG docker yata
mkdir -p /opt/yata && chown yata:yata /opt/yata