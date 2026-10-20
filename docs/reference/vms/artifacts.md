# artifacts: Artifact Keeper

> Reference · [Documentation](../../../README.md#documentation)

[Artifact Keeper](https://github.com/artifact-keeper/artifact-keeper) (MIT,
Rust) serves packages at `https://artifacts.example.org`: Maven, npm, PyPI,
generic files and 40-odd other formats, each with hosted, proxy and virtual
repositories. Its content comes from gitops through provider-artifact-keeper:
[Registries](../../explanation/registries.md).

| | |
|---|---|
| VM | `artifacts`, 4 vCPU, 6 GiB, 60 GB, AlmaLinux 10 |
| Address | 192.0.2.176 (DHCP); `artifacts.example.org` is also a host entry on the router (owner `infra-ansible:artifact_keeper`) |
| Runs | backend 1.10.2 (127.0.0.1:8081), web UI 1.10.1 (127.0.0.1:3000), PostgreSQL 18.6; Docker compose; Caddy 2 |
| Playbook | `ansible/artifacts.yml` (roles `docker`, `artifact_keeper`) |
| Content | gitops `clusters/lab/registries/artifact-keeper` (login, shared caches) and `base/team` (teams' repositories, permissions, CI token) |
| SSH | `ssh -i /root/lab/lab-secrets/artifacts/id_ed25519 almalinux@artifacts.example.org` |

## Install

| Item | Value |
|---|---|
| Compose | `/opt/artifact-keeper/docker-compose.yml`, systemd unit `artifact-keeper`: PostgreSQL, backend, web UI; images through the registry's mirrors |
| Not installed | OpenSearch, Trivy, OpenSCAP, Dependency-Track (all optional) |
| Caddy | backend paths (`/api/*`, `/maven/*`, `/npm/*`, `/pypi/*`, ...: `artifact_keeper_backend_paths`) to the backend, the rest to the UI |
| Proxy trust | the backend trusts `X-Forwarded-For` from the compose network's gateway |
| Data | `/var/lib/artifact-keeper`: `database/` (uid 70), `storage/` (packages), `backups/`, `plugins/` (uid 1001) |
| Trust | the VM's CA bundle as `/opt/artifact-keeper/tls-ca-bundle.pem`, mounted as the backend's system bundle |
| SSRF guard | private addresses refused unless in `AK_SSRF_ALLOW_PRIVATE_CIDRS`; the role resolves `artifact_keeper_ssrf_allow_hosts` (Keycloak) |
| Version pins | `artifact_keeper_backend_version`, `artifact_keeper_web_version` (versioned separately) |

## API

| Item | Value |
|---|---|
| Base | `https://artifacts.example.org/api/v1/...` |
| Auth | bearer token: `POST /api/v1/auth/login`, or API tokens (`/api/v1/users/me/tokens`, `/api/v1/service-accounts/{id}/tokens`) |
| Login rate limit | a few attempts per user and address, then 429 for minutes, extended by each attempt: automation uses tokens |
| OpenAPI | `/api/v1/openapi.json` (signed in), Swagger UI `/swagger-ui/` |
| Generic files | `PUT /api/v1/repositories/<key>/artifacts/<path>`, `GET .../download/<path>`; a path is immutable (409 on re-upload) |
| Permissions | `/api/v1/permissions`: group → repository, actions `read`, `write`; effective at once |

## Login

Keycloak (OIDC, PKCE; client `artifact-keeper` from Crossplane). The `groups`
claim becomes Artifact Keeper groups (`map_groups_to_groups`: created on first
sight, memberships reconciled at each login); `admin_group: registry-admins`
makes admins.

## Files

| `/root/lab/lab-secrets/artifacts/` | Contents |
|---|---|
| `id_ed25519` (+ `.pub`) | SSH key of the VM |
| `admin-password` | the local `admin` (break-glass; set at every start) |
| `db-password` | PostgreSQL |
| `jwt-secret` | signs sessions (changing it signs everyone out) |
| `webhook-key` | encrypts webhook secrets in the database (keep it) |
| `crossplane-lab-token` | the admin API token Crossplane uses (no expiry; also gitops `crossplane-system/artifact-keeper-credentials`) |
| `peer-api-key` | replication between instances (unused; pinned) |
