# metro-memory-trail (OSINT statique)

Ce challenge est désormais servi en statique via nginx.

- Accès : `/osint/metro-memory-trail/` sur le serveur web
- Page principale : `index.html`
- Assets : `assets/clue.png`, `assets/final.jpg`

## Déploiement

1. Copier le dossier `osint-static/metro-memory-trail/` sur le serveur dans `/var/www/osint/metro-memory-trail/`
2. Vérifier que le lien dans `challenge.yml` pointe vers :
   `connection_info: http://<domaine>/osint/metro-memory-trail/`

## Pour ajouter/modifier des indices

- Ajoute ou remplace les fichiers dans `assets/`
- Modifie le texte ou la structure dans `index.html`

---

Voir le README général dans `osint-static/` pour la procédure complète.
