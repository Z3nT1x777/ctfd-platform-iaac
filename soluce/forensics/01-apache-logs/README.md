# Soluce — 01-apache-logs

## Contexte

Un fichier de logs Apache (~500 lignes) est fourni. Il contient du trafic normal et une requête suspecte qui cache le flag encodé en base64.

## Étapes de résolution

### Méthode 1 — grep direct

```bash
# Chercher les requêtes POST (inhabituelles dans un log statique)
grep "POST" access.log

# Chercher les lignes avec status 200 sur des endpoints suspects
grep " 200 " access.log | grep -v "GET"
```

### Méthode 2 — recherche de chaînes base64

```bash
# Les flags CTF encodés en base64 commencent souvent par Q1RG (= CTF{ en b64)
grep "Q1RG" access.log

# Ou chercher un pattern de base64 (lettres + chiffres + = ou /)
grep -oE '[A-Za-z0-9+/]{20,}={0,2}' access.log
```

### Méthode 3 — décodage

```bash
# Une fois la chaîne base64 trouvée, la décoder
echo "Q1RGe2FwYWNoZV9sb2dfbmV2ZXJfbGllc30=" | base64 -d
```

### Méthode Python

```python
import re, base64

with open("access.log") as f:
    for line in f:
        # Chercher les valeurs de paramètres suspects
        m = re.search(r'data=([A-Za-z0-9+/]+=*)', line)
        if m:
            try:
                decoded = base64.b64decode(m.group(1)).decode()
                if decoded.startswith("CTF{"):
                    print("Flag trouvé:", decoded)
            except:
                pass
```

## Correction

Le flag se trouve dans un POST `/upload` avec un paramètre `data=` contenant le flag encodé en base64 :

```
POST /upload?data=Q1RGe2FwYWNoZV9sb2dfbmV2ZXJfbGllc30= HTTP/1.1
```

```bash
echo "Q1RGe2FwYWNoZV9sb2dfbmV2ZXJfbGllc30=" | base64 -d
# CTF{apache_log_never_lies}
```

**Flag : `CTF{apache_log_never_lies}`**
