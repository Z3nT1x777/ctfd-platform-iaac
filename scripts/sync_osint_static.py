#!/usr/bin/env python3
"""
Synchronise tous les challenges OSINT statiques (dossiers resources/) vers un dossier web cible (ex: /var/www/osint/).
Usage :
    python scripts/sync_osint_static.py --target /var/www/osint/

- Parcourt tous les dossiers challenges/osint/*/resources/
- Copie chaque dossier dans <target>/<challenge>/
- Écrase les fichiers existants
"""
import argparse
import shutil
from pathlib import Path
import sys

def sync_osint_resources(challenges_root: Path, target_root: Path):
    osint_dir = challenges_root / "osint"
    if not osint_dir.exists():
        print(f"[ERREUR] Dossier {osint_dir} introuvable.")
        sys.exit(1)
    for challenge in osint_dir.iterdir():
        resources = challenge / "resources"
        if resources.exists() and resources.is_dir():
            dest_dir = target_root / challenge.name
            dest = dest_dir / "resources"

            # Nettoyage automatique de tout sauf resources/ dans le dossier cible
            if dest_dir.exists():
                for item in dest_dir.iterdir():
                    if item.name != "resources":
                        try:
                            if item.is_dir():
                                shutil.rmtree(item)
                            else:
                                item.unlink()
                            print(f"[CLEAN] {item} supprimé du dossier cible.")
                        except PermissionError:
                            import subprocess
                            print(f"[WARN] Permission refusée pour supprimer {item}, tentative avec sudo rm -rf...")
                            result = subprocess.run(["sudo", "rm", "-rf", str(item)])
                            if result.returncode == 0:
                                print(f"[INFO] {item} supprimé avec sudo.")
                            else:
                                print(f"[ERREUR] Impossible de supprimer {item} même avec sudo.")
                                continue
            # Suppression du dossier resources/ cible s'il existe
            if dest.exists():
                try:
                    shutil.rmtree(dest)
                except PermissionError:
                    import subprocess
                    print(f"[WARN] Permission refusée pour supprimer {dest}, tentative avec sudo rm -rf...")
                    result = subprocess.run(["sudo", "rm", "-rf", str(dest)])
                    if result.returncode == 0:
                        print(f"[INFO] Dossier {dest} supprimé avec sudo.")
                    else:
                        print(f"[ERREUR] Impossible de supprimer {dest} même avec sudo.")
                        continue
                    # Correction des droits sur tout /var/www/osint après suppression sudo
                    chown_result = subprocess.run([
                        "sudo", "chown", "-R", "vagrant:vagrant", str(target_root)
                    ])
                    if chown_result.returncode == 0:
                        print(f"[INFO] Droits corrigés sur {target_root} (vagrant:vagrant)")
                        # Correction des permissions pour permettre la création de sous-dossiers
                        chmod_result = subprocess.run([
                            "sudo", "chmod", "775", str(target_root)
                        ])
                        if chmod_result.returncode == 0:
                            print(f"[INFO] Permissions corrigées (775) sur {target_root}")
                        else:
                            print(f"[WARN] Impossible de corriger les permissions sur {target_root}")
                    else:
                        print(f"[WARN] Impossible de corriger les droits sur {target_root}")
            # Ne surtout pas créer le dossier cible avant copytree (sinon FileExistsError)
            shutil.copytree(resources, dest)
            print(f"[OK] {resources} -> {dest}")
        else:
            print(f"[WARN] Pas de dossier resources/ pour {challenge.name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synchronise les challenges OSINT statiques vers un dossier web cible.")
    parser.add_argument("--target", required=True, help="Dossier cible (ex: /var/www/osint/)")
    parser.add_argument("--challenges-root", default="challenges", help="Racine des challenges (défaut: challenges)")
    args = parser.parse_args()

    challenges_root = Path(args.challenges_root).resolve()
    target_root = Path(args.target).resolve()


    # Création automatique du dossier cible si absent
    if not target_root.exists():
        try:
            target_root.mkdir(parents=True, exist_ok=True)
            print(f"[INFO] Dossier cible {target_root} créé automatiquement.")
        except PermissionError as e:
            # Tente avec sudo si PermissionError
            import subprocess
            print(f"[WARN] Permission refusée pour créer {target_root}, tentative avec sudo...")
            result = subprocess.run([
                "sudo", "mkdir", "-p", str(target_root)
            ])
            if result.returncode == 0:
                print(f"[INFO] Dossier cible {target_root} créé avec sudo.")
                # Correction des droits pour l'utilisateur vagrant
                chown_result = subprocess.run([
                    "sudo", "chown", "-R", "vagrant:vagrant", str(target_root)
                ])
                if chown_result.returncode == 0:
                    print(f"[INFO] Droits corrigés sur {target_root} (vagrant:vagrant)")
                else:
                    print(f"[WARN] Impossible de corriger les droits sur {target_root}")
            else:
                print(f"[ERREUR] Impossible de créer le dossier cible {target_root} même avec sudo.")
                sys.exit(1)
        except Exception as e:
            print(f"[ERREUR] Impossible de créer le dossier cible {target_root} : {e}")
            sys.exit(1)

    sync_osint_resources(challenges_root, target_root)
    print("Synchronisation OSINT statique terminée.")
