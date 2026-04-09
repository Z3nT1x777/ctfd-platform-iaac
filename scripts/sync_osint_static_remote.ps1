# Synchronise les challenges OSINT statiques vers /var/www/osint/ dans la VM Vagrant.
# À utiliser après avoir ajouté ou modifié un challenge OSINT.
#
# La configuration nginx est gérée par Ansible (vagrant provision).
# Ce script ne fait que synchroniser les fichiers statiques.
#
# Usage : .\scripts\sync_osint_static_remote.ps1

$target = "/var/www/osint/"
$scriptPath = "/vagrant/scripts/sync_osint_static.py"
$remoteCmd = "python3 $scriptPath --target $target --challenges-root /vagrant/challenges"

Write-Host "[INFO] Synchronisation OSINT statique sur la VM..."
vagrant ssh -c $remoteCmd
Write-Host "[INFO] Synchronisation terminée."
