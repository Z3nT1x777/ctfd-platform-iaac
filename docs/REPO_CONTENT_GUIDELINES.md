# Repository Content Guidelines (EN)

This guide defines what should live in each of the three repository layers:

- Public repo: visible showcase and onboarding entrypoint.
- Private template repo: reusable baseline for new teams.
- Private custom repo: team-specific product layer and experiments.

## Content Checklist

| Area | Must Stay in Public Template | Optional in Public Template | Move to Custom Only |
|---|---|---|---|
| Infrastructure | Vagrant, Ansible, Docker Compose baseline | Monitoring extensions, Kubernetes roadmap docs | Org-specific infra shortcuts |
| CTFd integration | Plugin bootstrap, generic launch/status flows, security defaults | Dashboard styling details | Team branding, custom UX experiments |
| Security | HMAC signing, rate limits, quotas, Vault support, preflight checks | Alternative hardening modules | Secret values, environment-specific bypasses |
| Challenges | Family templates, validation scripts, challenge authoring docs | Extra sample challenges | Internal-only challenge packs |
| Documentation | Baseline install, challenge workflow, template/custom workflow | Advanced troubleshooting and ops docs | Internal runbooks, environment notes |
| Helper scripts | Generic sync/validation helpers | Migration helpers with clear warnings | One-off DB patches, local operator shortcuts |

## Template Rules

- Keep the baseline useful for a new clone without local context.
- Prefer configuration over hardcoded behavior.
- Avoid embedding team-specific language, branding, or shortcuts in the template path.
- If a script or doc only solves a one-time operational problem, move it to the custom repo or mark it as legacy.

## Review Questions

Before adding something to the template, ask:

1. Would a new team want this on day one?
2. Can it be configured without editing source code?
3. Does it make the baseline feel like a product, or like a template?
4. Is it generic enough to stay useful after multiple forks?

If the answer is no to any of the above, it probably belongs in the custom repo.
