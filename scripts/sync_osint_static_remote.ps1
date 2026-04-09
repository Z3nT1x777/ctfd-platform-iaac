# Wrapper PowerShell pour lancer la synchronisation OSINT statique sur la VM Vagrant via SSH
# Usage : .\scripts\sync_osint_static_remote.ps1


$vmIp = "192.168.56.10"
$sshUser = "vagrant"
$target = "/var/www/osint/"
$scriptPath = "/vagrant/scripts/sync_osint_static.py"
$vagrantKey = "$env:USERPROFILE\.vagrant.d\insecure_private_key"

Write-Host "[INFO] Synchronisation OSINT statique sur la VM $vmIp..."



# Commande à exécuter sur la VM via vagrant ssh, avec le bon chemin challenges-root
$remoteCmd = "python3 $scriptPath --target $target --challenges-root /vagrant/challenges"
vagrant ssh -c $remoteCmd

Write-Host "[INFO] Synchronisation terminée."

# --- Mise à jour automatique de la conf nginx pour /osint/ ---
$nginxScript = "/vagrant/scripts/setup_osint_nginx.sh"
Write-Host "[INFO] Mise à jour de la configuration nginx pour /osint/ sur la VM..."
$nginxCmd = "bash $nginxScript"
vagrant ssh -c $nginxCmd
Write-Host "[INFO] Configuration nginx OSINT appliquée."
