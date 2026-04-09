#!/usr/bin/env python3
"""
Synchronise les challenges OSINT statiques vers le dossier web nginx.

Pour chaque challenges/osint/<slug>/resources/ trouvé, copie le contenu vers
<target>/<slug>/resources/.

Usage (dans la VM via vagrant ssh ou depuis le playbook Ansible) :
    python3 /vagrant/scripts/sync_osint_static.py --target /var/www/osint/

Prérequis : le dossier cible doit exister et être accessible en écriture par
l'utilisateur courant. Ansible s'en charge à la création de la VM
(task "Create OSINT static web root").
"""
import argparse
import shutil
import sys
from pathlib import Path


def sync_osint_resources(challenges_root: Path, target_root: Path) -> int:
    """Copie chaque resources/ vers target_root/<slug>/resources/. Retourne le nb copiés."""
    osint_dir = challenges_root / "osint"
    if not osint_dir.exists():
        print(f"[ERREUR] Dossier osint introuvable : {osint_dir}", file=sys.stderr)
        return 0

    synced = 0
    for challenge in sorted(osint_dir.iterdir()):
        if not challenge.is_dir() or challenge.name.startswith("_"):
            continue
        resources = challenge / "resources"
        if not resources.is_dir():
            print(f"[SKIP]  {challenge.name} — pas de dossier resources/")
            continue

        dest = target_root / challenge.name / "resources"
        if dest.exists():
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(resources, dest)
        print(f"\033[36m[OK]\033[0m   {challenge.name}/resources → {dest}")
        synced += 1

    return synced


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync OSINT static challenges to nginx web root.")
    parser.add_argument("--target", required=True, help="Web root cible (ex: /var/www/osint/)")
    parser.add_argument(
        "--challenges-root",
        default=str(Path(__file__).resolve().parents[1] / "challenges"),
        help="Racine des challenges (défaut: <repo>/challenges)",
    )
    args = parser.parse_args()

    target_root = Path(args.target).resolve()
    challenges_root = Path(args.challenges_root).resolve()

    if not target_root.exists():
        print(
            f"[ERREUR] Le dossier cible n'existe pas : {target_root}\n"
            "         Lancez d'abord 'vagrant provision' pour le créer via Ansible.",
            file=sys.stderr,
        )
        return 1

    if not challenges_root.exists():
        print(f"[ERREUR] Dossier challenges introuvable : {challenges_root}", file=sys.stderr)
        return 1

    synced = sync_osint_resources(challenges_root, target_root)
    print(f"\nTerminé — {synced} challenge(s) OSINT synchronisé(s) vers {target_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
