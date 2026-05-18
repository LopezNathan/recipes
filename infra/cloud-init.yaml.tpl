#cloud-config

package_update: true

packages:
  - curl
  - git

write_files:
  - path: /opt/recipes-env
    permissions: "0600"
    content: |
      DATABASE_URL=${database_url}

  - path: /etc/systemd/system/cloudflared.service
    permissions: "0644"
    content: |
      [Unit]
      Description=Cloudflare Tunnel
      After=network.target

      [Service]
      ExecStart=/usr/local/bin/cloudflared tunnel run --token ${tunnel_token}
      Restart=on-failure
      RestartSec=5s

      [Install]
      WantedBy=multi-user.target

runcmd:
  # Swap file so the Docker build doesn't OOM on 1 GB instances
  - fallocate -l 1G /swapfile
  - chmod 600 /swapfile
  - mkswap /swapfile
  - swapon /swapfile
  - echo '/swapfile none swap sw 0 0' >> /etc/fstab
  # Install Docker (includes Compose plugin)
  - curl -fsSL https://get.docker.com | sh
  - systemctl enable docker
  - systemctl start docker
  # Install cloudflared
  - curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
  - chmod +x /usr/local/bin/cloudflared
  - systemctl enable cloudflared
  - systemctl start cloudflared
  # Clone repo and deploy
  - git clone ${repo_url} /opt/recipes
  - chown -R ubuntu:ubuntu /opt/recipes
  - mv /opt/recipes-env /opt/recipes/.env
  - cd /opt/recipes && docker compose up -d
