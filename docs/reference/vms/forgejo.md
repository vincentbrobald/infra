# forgejo: Forgejo

> Reference · [Documentation](../../../README.md#documentation)

The Git server: the GitOps repository the clusters are deployed from
(`alice/gitops`), the infrastructure code, the CI's repositories, the teams'
repositories. **Never delete this VM or its data**: nothing restores the
repositories' content.

| | |
|---|---|
| VM | `forgejo`, 2 vCPU, 2 GiB, Fedora 44 (re-created by the playbook it would be AlmaLinux 10, same user and key) |
| Address | 192.0.2.100 (DHCP, name registered by the router) |
| Runs | Forgejo 16.0.5 on 127.0.0.1:8080 and SSH on :2222, behind Caddy |
| Playbook | `ansible/forgejo.yml` (role `forgejo`; settings in `ansible/inventory/group_vars/forgejo.yml`) |
| SSH (VM) | `ssh -i /root/lab/forgejo-test/vm/id_ed25519 fedora@forgejo.example.org` |
| Git | `https://forgejo.example.org` (sign-in required for everything), `ssh://git@forgejo.example.org:2222/<owner>/<repo>.git` |

## Service

| Item | Value |
|---|---|
| Binary | checksum-verified; systemd unit |
| Config | `app.ini`; its secrets as files `/etc/forgejo/{secret_key,internal_token,jwt_secret}` |
| Data | `/var/lib/forgejo` (repositories, SQLite in `data/`), `/etc/forgejo` |
| Caddy | certificate from step-ca; SELinux `httpd_can_network_relay` |
| firewalld | http, https, 2222/tcp |
| Login | OAuth2 source `keycloak` (client `forgejo`); accounts made at first login (`ENABLE_AUTO_REGISTRATION`) |
| Webhooks | `[webhook] ALLOWED_HOST_LIST = pac.apps.lab.example.org` (the section is singular; `[webhooks]` is ignored) |
| Webhook records | `/etc/forgejo/webhooks/`: hashes of the secrets the role set |

## Local users

| User | Purpose | Token |
|---|---|---|
| `gitadmin` | admin | — |
| `argocd-reader` | Argo CD reads `alice/gitops` (https) | `argocd` (`read:repository`) |
| `pac-bot` | Pipelines-as-Code: reads repositories, reports results | `pipelines-as-code` (`write:repository`, `write:issue`, `read:user`); also gitops Secrets `forgejo-pac` (SOPS) |
| `crossplane-lab` | Crossplane on `lab` (provider-forgejo): repository settings, organization `example` (owner), its teams, repositories and CI users; **site admin** (to create CI users), bounded by gitops admission policies | `crossplane` (`write:repository`, `write:organization`, `write:admin`, `read:user`); also gitops `crossplane-system/forgejo-credentials` |

## Repositories (Ansible)

| Repository | Collaborators | Deploy keys | Webhook | Other |
|---|---|---|---|---|
| `alice/gitops` | `argocd-reader` (read), `pac-bot` (write) | `argocd` (read), `deploy-talos.py push` (write) | Pipelines-as-Code | `main` protected: status `Pipelines as Code CI / gitops-check`, up-to-date branch; direct pushes by deploy keys only; `gitadmin` bypasses |
| `alice/provider-forgejo` | `pac-bot` | `push` | Pipelines-as-Code | |
| `alice/gitops-scanner` | `crossplane-lab` (admin) | | | other settings: Crossplane |
| `alice/pac-demo` | `crossplane-lab` (admin) | | | other settings: Crossplane; skipped while the owner has no account |
| `alice/provider-artifact-keeper` | | | | other settings: Crossplane (`crossplane-lab` reaches it as site admin) |

The role finds a repository's webhooks by URL. A webhook moved to a new URL
lists the old one under `replaces:` (`group_vars/forgejo.yml`): the role
creates the new hook, then deletes the one with the old URL. Without it, the
old hook would keep calling too. Webhooks to Pipelines-as-Code use
`https://pac.apps.lab.example.org`.

## Repository settings managed by Crossplane

From gitops `clusters/lab/ci/<repo>/repository.yaml`:

| Repository | Objects |
|---|---|
| `alice/pac-demo` (ID 8) | collaborator `pac-bot` (write), webhook to Pipelines-as-Code |
| `alice/gitops-scanner` (ID 10) | collaborator `pac-bot` (write), webhook, deploy key `push` |
| `alice/provider-artifact-keeper` (ID 19) | collaborator `pac-bot` (write), webhook |

Webhook config (url, content type, secret) from Secret `forgejo-webhook` in
each namespace, the same secret as `forgejo-pac`'s `webhook.secret`.

## Files

| Path | Contents |
|---|---|
| `/root/lab/forgejo-test/admin_password` | `gitadmin` |
| `/root/lab/forgejo-test/reader_password`, `reader_token` | `argocd-reader` and its token |
| `/root/lab/forgejo-test/deploy_key` (+ `.pub`) | read-only deploy key on `alice/gitops` |
| `/root/lab/forgejo-test/vm/` | the VM's SSH key and sudo password |
| `/root/lab/lab-secrets/forgejo/gitops-push_key` (+ `.pub`) | read-write deploy key on `alice/gitops` (deploy-talos.py) |
| `/root/lab/lab-secrets/forgejo/pac-bot-password`, `pac-bot-token` | `pac-bot` |
| `/root/lab/lab-secrets/forgejo/crossplane-lab-password`, `crossplane-lab-token` | `crossplane-lab` |
| `/root/lab/lab-secrets/forgejo/<repo>-webhook-secret` | webhook secrets (also in Git) |
| `/root/lab/lab-secrets/forgejo/oidc-client-secret` | Keycloak client `forgejo` |
| `/root/lab/lab-secrets/forgejo/backup/` | `forgejo dump` archives (`upgrade.yml`) |
| `/root/lab/lab-secrets/forgejo/backups/repos-20261015.json` | repository settings before Crossplane took them over (no secrets) |
