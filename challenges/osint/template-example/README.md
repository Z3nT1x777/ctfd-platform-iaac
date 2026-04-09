# OSINT Template Example (statique)

Ce template montre comment structurer un challenge OSINT statique servi par nginx.

- Accès : `/osint/template-example/` sur le serveur web
- Page principale : `index.html`
- Assets : `assets/clue.png`, `assets/final.jpg`

## Déploiement

1. Copier le dossier `osint-static/template-example/` sur le serveur dans `/var/www/osint/template-example/`
2. Vérifier que le lien dans `challenge.yml` pointe vers :
   `connection_info: http://<domaine>/osint/template-example/`

## Pour créer un nouveau challenge à partir du template

- Duplique le dossier `template-example/`
- Modifie `index.html` et les fichiers dans `assets/`
- Mets à jour le `challenge.yml` correspondant

---

Voir le README général dans `osint-static/` pour la procédure complète.
