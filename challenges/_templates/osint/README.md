# OSINT Challenge Template (statique)

Ce dossier sert de squelette pour tout nouveau challenge OSINT statique.

---

## Structure recommandée

```
challenges/osint/<challenge-slug>/
├── challenge.yml           # Métadonnées
├── README.md               # Description, indices, instructions
└── resources/              # Documents, images, index.html, etc.
    ├── index.html
    └── assets/
        ├── clue.png
        └── final.jpg
```

- `resources/index.html` : page principale du challenge (modifiable)
- `resources/assets/` : images, documents, etc.

---

## Création d'un nouveau challenge

1. **Générer le challenge** (depuis la racine du repo) :
   ```powershell
   ./scripts/new-challenge.ps1 -Name [mon-challenge-osint] -Family osint
   ```
   ou
   ```bash
   bash ./scripts/new-challenge.sh [mon-challenge-osint] --family osint
   ```
2. **Personnaliser** :
   - Renomme le challenge dans `challenge.yml`
   - Modifie `resources/index.html` et ajoute tes propres assets
   - Mets à jour le flag, la description, etc.
3. **Déployer les fichiers statiques** sur le serveur web (voir ci-dessous)

---

## Publication web via nginx

Pour exposer tous les challenges OSINT statiques sur le web :

1. **Synchronise automatiquement** les dossiers `resources/` de chaque challenge OSINT dans un dossier web, par exemple `/var/www/osint/<challenge-slug>/`, avec :
   ```bash
   python scripts/sync_osint_static.py --target /var/www/osint/
   ```
   - Ce script copie tous les dossiers `resources/` de chaque challenge OSINT dans le dossier cible, prêt à être servi par nginx.
   - À intégrer dans ton workflow de déploiement (juste après le script de sync CTFd).

2. **Configure nginx** pour servir `/osint/` :
   ```nginx
   location /osint/ {
       alias /var/www/osint/;
       autoindex off;
       try_files $uri $uri/ =404;
   }
   ```

3. **Dans le `challenge.yml`**, renseigne :
   ```yaml
   connection_info: http://<domaine>/osint/<challenge-slug>/index.html
   ```

---

## Commandes utiles

- Synchroniser les fichiers statiques OSINT :
  ```bash
  python scripts/sync_osint_static.py --target /var/www/osint/
  ```
- Déployer la configuration CTFd :
  ```bash
  python scripts/sync_challenges_ctfd.py --ctfd-url ... --api-token ...
  ```

---

## Troubleshooting

- **Page inaccessible ?**
  - Vérifie que les fichiers sont bien copiés dans `/var/www/osint/<challenge>/`.
  - Vérifie la config nginx (voir ci-dessus).
  - Recharge nginx : `sudo systemctl reload nginx`
  - Vérifie l’URL dans `connection_info`.
- **Pas de dossier resources/** ? Le script affiche un warning, ajoute-le dans ton challenge.
- **Droits d’écriture** ? Le script doit avoir les droits pour écrire dans le dossier cible.

---

## Conseils

- Pour chaque nouveau challenge, duplique ce template.
- Ajoute tous les fichiers nécessaires dans `resources/`.
- Le workflow CI/CD peut automatiser la synchronisation des dossiers sur le serveur web.
- Documente bien le flag et les indices dans le README de chaque challenge.

---

**Pour toute question sur la configuration nginx ou l'automatisation, voir le README général ou demander à l'admin infra.**
