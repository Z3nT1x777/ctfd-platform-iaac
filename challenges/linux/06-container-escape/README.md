# Container Escape via Docker Socket

**Catégorie** : Linux / Privilege Escalation  
**Difficulté** : Hard  
**Points** : 500

## Description

Tu es dans un container Docker. Le flag n'est pas dans ce container.
Inspecte ton environnement, trouve comment interagir avec le host et récupère le flag sur la machine hôte.
Tout ce dont tu as besoin est déjà dans le container.

## Connexion

```bash
ssh player@<TARGET_IP> -p 5025
# password: player2026
```

## Objectif

Récupérer le flag situé sur le HOST (machine Vagrant) à `/opt/ctf-flags/container-escape.txt`.

## Note pour les organisateurs

Avant de lancer ce challenge, créer le flag sur la machine hôte (VM Vagrant) :

```bash
sudo mkdir -p /opt/ctf-flags
echo 'CTF{docker_socket_escape_to_host}' | sudo tee /opt/ctf-flags/container-escape.txt
sudo chmod 644 /opt/ctf-flags/container-escape.txt
```
