# Ajoute une configuration nginx pour servir /osint/ depuis /var/www/osint
# À exécuter dans la VM (via vagrant ssh ou ansible)

$nginxConfPath = "/etc/nginx/conf.d/osint-static.conf"

$nginxConf = @'
server {
    listen 80;
    server_name _;

    location /osint/ {
        alias /var/www/osint/;
        autoindex on;
        try_files $uri $uri/ =404;
    }
}
'@

# Sauvegarde l'ancienne conf si elle existe
if (Test-Path $nginxConfPath) {
    Copy-Item $nginxConfPath "$nginxConfPath.bak" -Force
}

# Écrit la nouvelle conf
Set-Content -Path $nginxConfPath -Value $nginxConf -Force

# Recharge nginx
sudo nginx -t
if ($LASTEXITCODE -eq 0) {
    sudo systemctl reload nginx
    Write-Host "[OK] Nginx rechargé avec la conf statique OSINT."
} else {
    Write-Host "[ERREUR] Erreur de syntaxe dans la conf nginx, revert..."
    if (Test-Path "$nginxConfPath.bak") {
        Move-Item "$nginxConfPath.bak" $nginxConfPath -Force
        sudo systemctl reload nginx
    }
}
