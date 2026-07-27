# Security Policy

## Supported versions

This is an open-source reference implementation of an MLOps platform on Amazon EKS. Security fixes are applied to the `main` branch only; there are no LTS release lines.

| Version | Supported |
|---------|-----------|
| `main` (latest) | ✅ |
| Tagged releases | ⚠️ Best-effort, update to `main` for security fixes |

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Instead, use **GitHub Private Security Reporting**:

1. Go to the [Security advisory page](https://github.com/JoseJulianMosqueraFuli/E2E-EKS-GitOps/security/advisories/new).
2. Click **"Report a vulnerability"** to open a private advisory.
3. Include:
   - Affected file(s) / path(s)
   - Description of the issue and impact
   - Reproduction steps (PoC if available)
   - Suggested fix (optional)

You should receive an acknowledgement within **72 hours**. Vulnerabilities are tracked in `critical.md` once confirmed.

## Known security posture

The project maintains a living inventory of security findings in:

- [`critical.md`](critical.md) — CRITICAL and HIGH severity issues with fix status.
- [`backlog.md`](backlog.md) — MEDIUM/LOW severity findings across security, infra, GitOps, ML platform, monitoring and CI/CD.

Open items of note (see `critical.md` for details):

- **CRIT-004**: ArgoCD `mlops-core` AppProject is permissive — slated for restriction.
- **HIGH-001**: Terraform backend is local by default; S3 backend activation blocked on AWS account setup.
- **HIGH-006 / HIGH-007**: `latest` image tags in Evidently and Argo workflow templates.
- **HIGH-013**: CI pipelines intentionally tolerate test/lint failures (`|| true`). Do not remove without explicit request.

## Security measures already in place

- **Pre-commit**: `detect-secrets` scans staged files; baseline tracked in `.secrets.baseline`.
- **Gatekeeper/OPA**: `no-latest-tag` constraint enforced in production namespaces; Pod Security Standards enforced.
- **Istio mTLS**: mutual TLS between MLOps services (STRICT rollout in progress — see `backlog.md` Istio section).
- **Argo Workflows**: hardened — TLS enabled, SSO auth, `emissary` executor (no `docker.sock` mounts).
- **Image tagging policy**: pin to semantic versions or SHAs; `latest` is disallowed in production namespaces.

## Disclosure policy

- Coordinated disclosure preferred.
- Public advisory published after a fix is merged to `main` (or after 90 days if no fix is feasible).
- Credits given to reporters in the advisory unless they prefer to remain anonymous.

## Security hardening checklist (for contributors)

Before submitting a change that touches security-sensitive areas:

- [ ] No secrets/credentials in manifests, env vars, or commits.
- [ ] Image tags pinned (no `:latest` in non-dev namespaces).
- [ ] RBAC scopes are least-privilege.
- [ ] NetworkPolicies defined for new namespaces.
- [ ] Pod Security Standards satisfied (`restricted` in prod).
- [ ] Update `.secrets.baseline` if new false-positives appear: `detect-secrets scan -u .secrets.baseline`.
- [ ] If the change affects `critical.md`/`backlog.md`, update those files accordingly.

*Last updated: July 2026*