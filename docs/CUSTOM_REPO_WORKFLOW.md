# Custom Repository Workflow (EN)

This project uses a single repository workflow centered on `ctfd-platform-custom`.

## Branch Model

- `main`: stable branch used for deployment.
- `feature/*`: short-lived branches for implementation work.
- `hotfix/*`: urgent fixes that are merged back quickly into `main`.

## Local Git Remote Setup

Keep one primary remote:

```bash
git remote -v
# origin -> https://github.com/<owner>/ctfd-platform-custom.git
```

If your local clone still has legacy remotes:

```bash
git remote remove template || true
git remote remove upstream || true
git remote remove custom || true
git remote set-url origin https://github.com/<owner>/ctfd-platform-custom.git
```

## Daily Workflow

```bash
git checkout main
git pull --ff-only origin main
git checkout -b feature/<short-topic>
# implement + test
git commit -m "feat: <summary>"
git push -u origin feature/<short-topic>
```

Open a PR to `main`, run CI checks, and merge when green.

## Release Workflow

```bash
git checkout main
git pull --ff-only origin main
git tag -a vX.Y.Z -m "release vX.Y.Z"
git push origin main --tags
```

## Decision Rule

- If a change helps the current platform, keep it here.
- Avoid maintaining parallel forks for the same runtime.
