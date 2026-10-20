# registry: Harbor

> Reference · [Documentation](../../../README.md#documentation)

[Harbor](https://goharbor.io) serves container images at
`https://registry.example.org` (web UI at the same address) and mirrors the
public registries for the clusters. What it holds comes from gitops through
Crossplane: [Registries](../../explanation/registries.md).

| | |
|---|---|
| VM | `registry`, 4 vCPU, 8 GiB, 100 GB, AlmaLinux 10 |
| Address | 192.0.2.136 (DHCP); `registry.example.org` is also a host entry on the router (owner `infra-ansible:harbor`) |
| Runs | Harbor 2.15.4 (Docker compose) on 127.0.0.1:8080, Caddy 2 |
| Playbook | `ansible/registry.yml` (roles `docker`, `harbor`; `tasks/zot-removed.yml` removes the former registry) |
| Content | gitops `clusters/lab/registries/harbor` and `base/team`, through Crossplane (provider-upjet-harbor, as Harbor's admin) |
| SSH | `ssh -i /root/lab/lab-secrets/registry/id_ed25519 almalinux@registry.example.org` |

## Projects

All public for pulls; pushing needs a member or a robot; Trivy scans on push.

| Project | What | Who pushes |
|---|---|---|
| `docker.io`, `ghcr.io`, `quay.io`, `registry.k8s.io`, `gcr.io`, `factory.talos.dev` | proxy caches: `registry.example.org/docker.io/library/nginx` is `docker.io/library/nginx`, filled on first pull | nobody |
| `providers`, `gitops-scanner`, `pac-demo` | the platform's images | the repository's CI robot (`robot$<project>+<robot>`) |
| `<team>` (one per gitops team) | the team's images, 20 GB | the group `team-<team>` (maintainer) and `robot$<team>+<team>-ci` |

The Talos clusters use the proxy caches as containerd mirrors (`registry`
section of the cluster file).

## Login

| Item | Value |
|---|---|
| Browser | Keycloak (client `harbor`, from Crossplane); users appear at first login |
| Admins | members of `registry-admins`, decided at each login (`admin_role_in_auth`, not stored: the user list shows them as non-admins) |
| CLI | `podman login` with the CLI secret from the user's profile |
| Local `admin` | kept; Crossplane uses it |
| CI | robot accounts; their secrets from gitops Secrets `registry-push` (platform) and `harbor-push` of `ci-<team>` (teams) |

## Install

| Item | Value |
|---|---|
| Docker | Docker Engine 29.8.2, compose 5.6.0 (Docker's RHEL 10 repository); nftables firewall backend; `net.ipv4.ip_forward=1` (`/etc/sysctl.d/90-docker.conf`); published ports on loopback |
| Harbor | online installer in `/opt/harbor` → `/opt/harbor-<version>`; `harbor.yml` from the role; `./prepare --with-trivy`; systemd unit `harbor`; `8080:8080` rewritten to `127.0.0.1:8080:8080` after each `prepare` |
| Data | `/var/lib/harbor` (images, PostgreSQL, Redis, Trivy cache); logs `/var/log/harbor` |
| Trust | the site CA in Harbor's `trust-certificates` |
| Webhooks | `network.allow_private_network_access: false` |
| Version pins | `harbor_version`, `harbor_installer_md5` |

The hypervisor host doesn't trust the site CA system-wide: podman needs
`--cert-dir` with the root CA as `ca.crt`, curl `--cacert`.

## Files

| `/root/lab/lab-secrets/` | Contents |
|---|---|
| `registry/id_ed25519` (+ `.pub`) | SSH key of the VM |
| `registry/harbor-admin-password` | Harbor's `admin` (also gitops `crossplane-system/harbor-credentials`, which wins) |
| `registry/harbor-db-password` | Harbor's PostgreSQL |
