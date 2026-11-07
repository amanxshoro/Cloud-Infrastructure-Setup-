#!/usr/bin/env bash
# Cloud Notes (MySQL) - one-shot setup for Ubuntu 22.04/24.04 (AWS EC2, GCP, Azure).
# Run from inside the project folder:  sudo DB_PASS='YourPassword' bash setup.sh
set -euo pipefail

DB_NAME="cloudnotes"
DB_USER="cloudnotes"
DB_PASS="${DB_PASS:-CloudNotes2026}"
APP_DIR="/opt/cloudnotes"

echo "==> Installing packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y nginx mysql-server python3-venv python3-pip

echo "==> Configuring MySQL"
systemctl enable --now mysql
mysql -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4;"
mysql -e "CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';"
mysql -e "ALTER USER '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';"
mysql -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost'; FLUSH PRIVILEGES;"

echo "==> Deploying application to ${APP_DIR}"
mkdir -p "${APP_DIR}"
cp app.py requirements.txt "${APP_DIR}/"
python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --upgrade pip
"${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"
chown -R www-data:www-data "${APP_DIR}"

echo "==> Creating systemd service"
cat > /etc/systemd/system/cloudnotes.service <<EOF
[Unit]
Description=Cloud Notes (gunicorn)
After=network.target mysql.service

[Service]
User=www-data
WorkingDirectory=${APP_DIR}
Environment="DB_HOST=localhost"
Environment="DB_NAME=${DB_NAME}"
Environment="DB_USER=${DB_USER}"
Environment="DB_PASSWORD=${DB_PASS}"
ExecStart=${APP_DIR}/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable cloudnotes
systemctl restart cloudnotes

echo "==> Configuring nginx reverse proxy"
cat > /etc/nginx/sites-available/cloudnotes <<'EOF'
server {
    listen 80 default_server;
    server_name _;
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF
ln -sf /etc/nginx/sites-available/cloudnotes /etc/nginx/sites-enabled/cloudnotes
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

echo "==> Done. Test with:  curl http://localhost/health"
