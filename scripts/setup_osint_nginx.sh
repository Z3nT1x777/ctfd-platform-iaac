#!/bin/bash
# Ajoute une configuration nginx pour servir /osint/ depuis /var/www/osint
# À exécuter dans la VM (via vagrant ssh ou ansible)

NGINX_CONF_PATH="/etc/nginx/conf.d/osint-static.conf"
BACKUP_PATH="${NGINX_CONF_PATH}.bak"

sudo tee "$NGINX_CONF_PATH" > /dev/null <<'EOF'
server {
    listen 80;
    server_name _;

    location /osint/ {
        alias /var/www/osint/;
        autoindex on;
        try_files $uri $uri/ =404;
    }
}
EOF

# Teste la conf nginx
sudo nginx -t
if [ $? -eq 0 ]; then
    sudo systemctl reload nginx
    echo "[OK] Nginx rechargé avec la conf statique OSINT."
else
    echo "[ERREUR] Erreur de syntaxe dans la conf nginx, revert..."
    if [ -f "$BACKUP_PATH" ]; then
        sudo mv "$BACKUP_PATH" "$NGINX_CONF_PATH"
        sudo systemctl reload nginx
    fi
fi
