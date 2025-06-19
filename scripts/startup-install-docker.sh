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
systemctl enable --now docker
# non-root user (optional)
useradd -m -s /bin/bash yata || true
usermod -aG docker yata
mkdir -p /opt/yata && chown yata:yata /opt/yata