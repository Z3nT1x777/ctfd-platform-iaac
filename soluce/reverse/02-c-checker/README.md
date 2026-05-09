# Soluce — 02-c-checker

## Contexte

Un binaire Linux x86-64 vérifie une clé de licence. Le flag est divisé en trois tableaux de caractères statiques, assemblés à l'exécution via `snprintf`.

## Étapes de résolution

### Méthode 1 — strings (la plus simple)

```bash
strings ./crackme
# Rechercher les chaînes ASCII dans .rodata
# On devrait voir : CTF{comp  are_hard  coded}
```

Les trois parties sont adjacentes en mémoire et souvent visibles avec `strings`.

### Méthode 2 — ltrace (interception des appels libc)

```bash
ltrace ./crackme
# Entrer n'importe quelle chaîne, ex: "test"
# ltrace intercepte strcmp() et montre les deux arguments :
# strcmp("test", "CTF{compare_hardcoded}") = ...
```

`ltrace` affiche en temps réel la comparaison `strcmp(input, "CTF{compare_hardcoded}")`.

### Méthode 3 — Ghidra (décompilation)

1. Ouvrir le binaire dans Ghidra
2. Analyser avec les options par défaut
3. Naviguer dans `main()` → trouver l'appel `snprintf`
4. Identifier les trois tableaux initialisés : `p1`, `p2`, `p3`
5. Lire les valeurs : `CTF{comp`, `are_hard`, `coded}`

Dans le code décompilé :
```c
char p1[] = {'C','T','F','{','c','o','m','p','\0'};
char p2[] = {'a','r','e','_','h','a','r','d','\0'};
char p3[] = {'c','o','d','e','d','}','\0'};
// snprintf(key, 32, "%s%s%s", p1, p2, p3);
// → "CTF{compare_hardcoded}"
```

### Méthode 4 — radare2

```bash
r2 -A ./crackme
# Dans r2 :
afl              # lister les fonctions
s main           # aller à main
pdf              # désassembler
# Chercher les chaînes dans .rodata :
iz               # strings dans les sections data
```

### Méthode 5 — gdb (débogage dynamique)

```bash
gdb ./crackme
break strcmp
run
# Entrer n'importe quoi quand demandé
# À l'arrêt dans strcmp :
x/s $rsi         # 2e argument = la clé attendue
```

## Correction

Quelle que soit la méthode, le flag est assemblé depuis trois parties hardcodées :

```
p1 = "CTF{comp"
p2 = "are_hard"
p3 = "coded}"
→ "CTF{compare_hardcoded}"
```

**Flag : `CTF{compare_hardcoded}`**
