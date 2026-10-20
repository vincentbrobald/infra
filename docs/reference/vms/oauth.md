# oauth: Keycloak

> Reference · [Documentation](../../../README.md#documentation)

The site's identity provider: the clusters, Argo CD, Headlamp, the
registries, Forgejo and Omni log in through it.

| | |
|---|---|
| VM | `oauth`, 2 vCPU, 4 GiB, 20 GB, AlmaLinux 10 |
| Address | 192.0.2.111 (DHCP, name registered by the router) |
| Runs | Keycloak 26.8.1, PostgreSQL 16, Caddy (release binary, `caddy_version`) |
| Playbook | `ansible/keycloak.yml` (roles `keycloak`, `keycloak_realm`; settings in `ansible/inventory/group_vars/keycloak.yml`) |
| SSH | `ssh -i /root/lab/lab-secrets/oauth/id_ed25519 almalinux@oauth.example.org` |

## Service

| Item | Value |
|---|---|
| Admin console | `https://oauth.example.org/admin/`, user `admin` (password in `/root/lab/lab-secrets/oauth/keycloak-admin-password`, not on the VM) |
| OIDC discovery | `https://oauth.example.org/realms/<realm>/.well-known/openid-configuration` |
| Caddy | :80 (redirect), :443; certificate from step-ca over ACME |
| Keycloak | HTTP on `127.0.0.1:8080`, management/health on `127.0.0.1:9000`; proxy headers trusted from `127.0.0.1` only; single node (`cache=local`) |
| Files | `/opt/keycloak` → `/opt/keycloak-<version>`; config `/opt/keycloak/conf/keycloak.conf` (mode 640); service `keycloak` |
| PostgreSQL | local only; database and user `keycloak`, password `/etc/keycloak/db-password` |

## Realm `example`

| Kind | Name | Managed by |
|---|---|---|
| group | `k8s-admins` (cluster-admin; Tekton Dashboard) | Ansible (`keycloak_realm`) |
| group | `argocd-admins` (Argo CD admin) | Ansible |
| group | `registry-admins` (Harbor and Artifact Keeper admins) | Ansible |
| group | `grafana-admins` (Grafana admin) | deploy-talos.py; on `lab` a Crossplane object it writes (`oidc.crossplane`) |
| group | `team-<team>` and members | Crossplane (gitops `applications/`); authoritative |
| client | `forgejo`, `omni` | Ansible; secrets from files, or from gitops first (`gitops: {topic, key}`) |
| client | `k8s-<cluster>`, `argocd-<cluster>` | deploy-talos.py (API) |
| client | `headlamp-<cluster>`, `grafana-<cluster>` | deploy-talos.py; on `lab` Crossplane objects it writes |
| client | `tekton-lab` (Tekton Dashboard's oauth2-proxy) | Crossplane (gitops `clusters/lab/tekton/dashboard/keycloak-client.yaml`) |
| client | `harbor`, `artifact-keeper` | Crossplane (gitops `clusters/lab/registries/`) |
| client | `argocd-lab-team-<team>`, `tekton-lab-team-<team>` | Crossplane (gitops `base/team`) |
| users | everyone else | by hand |

Settings made in the console that the inventory doesn't list are kept.

## Crossplane's account

| Item | Value |
|---|---|
| Client | `crossplane-lab`, realm **master** (provider-keycloak reads `/admin/serverinfo`, served only there); no browser login |
| Roles | of master's `example-realm` client: `view-clients`, `manage-clients`, `view-users`, `manage-users` |
| Secret | `/root/lab/lab-secrets/oauth/crossplane-lab-client-secret`, also gitops `crossplane-system/keycloak-credentials` (key `client_secret`) |

Any client can be a service account the same way:
`service_account_roles: [{client, role}]`, `realm` in the inventory.

## Files

| `/root/lab/lab-secrets/` | Contents |
|---|---|
| `oauth/id_ed25519` (+ `.pub`) | SSH key of the VM |
| `oauth/keycloak-admin-password` | Keycloak `admin` |
| `oauth/omni-client-secret` | client `omni` |
| `oauth/crossplane-lab-client-secret` | client `crossplane-lab` in master |
| `oauth/tekton-lab-client-secret` | client `tekton-lab` as Ansible last set it (unused, kept for handing it back) |
| `oauth/backups/tekton-lab-20261015.json` | client `tekton-lab` (settings, ID, secret, mappers) before Crossplane took it over |
| `oauth/backups/headlamp-grafana-lab-20261016.json` | clients `headlamp-lab`, `grafana-lab` and group `grafana-admins` before Crossplane took them over |
| `forgejo/oidc-client-secret` | client `forgejo` |
