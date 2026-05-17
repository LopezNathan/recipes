#cloud-config

package_update: true

packages:
  - curl
  - git

write_files:
  - path: /opt/recipes-env
    permissions: "0600"
    content: |
      DB_PASSWORD=${db_password}

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
  # Clone repo and deploy
  - git clone ${repo_url} /opt/recipes
  - chown -R ubuntu:ubuntu /opt/recipes
  - mv /opt/recipes-env /opt/recipes/.env
  - cd /opt/recipes && docker compose -f docker-compose.prod.yml up -d --build
