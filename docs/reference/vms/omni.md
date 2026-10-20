# omni: Omni (optional)

> Reference · [Documentation](../../../README.md#documentation)

[Omni](https://docs.siderolabs.com/omni) (Sidero Labs): web console and API
for Talos clusters, `https://omni.example.org`. Exists only when the inventory
has a host in the group `omni`.

| | |
|---|---|
| VM | `omni`, 2 vCPU, 4 GiB, 30 GB, AlmaLinux 10 |
| Address | 192.0.2.177 (DHCP, name registered by the router) |
| Runs | Omni v1.12.2 in Podman (quadlet `/etc/containers/systemd/omni.container`, service `omni`), Caddy 2 |
| Playbook | `ansible/omni.yml` (role `omni`); needs `keycloak.yml` (client `omni`) and `registry.yml` (image through its mirror) first |
| SSH | `ssh -i /root/lab/lab-secrets/omni/id_ed25519 almalinux@omni.example.org` |
| License | Business Source License: free for non-production use, home labs included |

## Endpoints

| Port | What | Path |
|---|---|---|
| 443 | UI and API (gRPC, gRPC-Web) | Caddy (TLS, step-ca) → 127.0.0.1:8080 (h2c) |
| 8090 | SideroLink API (nodes join) | Caddy → 127.0.0.1:18090 (h2c) |
| 8100 | Kubernetes API proxy | Caddy → 127.0.0.1:18100 |
| 50180/udp | SideroLink WireGuard | Omni directly |
| 8091 | nodes' events | over WireGuard only |

## Login

Keycloak (client `omni`): `https://omni.example.org/login`. Omni admits only
users it knows: `omni_initial_users` (`ansible/inventory/group_vars/omni.yml`,
admins at first start), then those added in Omni (Settings > Users).

## Clusters

| Cluster | State | Backup of its node configs |
|---|---|---|
| `lab` | imported, **locked** (Omni changes nothing) | `/root/lab/lab-cluster/lab-backup-20261015-030423.zip` |

## Data and files

Data: `/var/lib/omni` (embedded etcd, SQLite).

| `/root/lab/lab-secrets/` | Contents |
|---|---|
| `omni/id_ed25519` (+ `.pub`) | SSH key of the VM |
| `oauth/omni-client-secret` | Keycloak client secret (Omni prints it in its startup log: journal, root only) |
| `omni/account-id` | Omni's account id: never change it |
| `omni/omni.asc` | GPG key encrypting Omni's etcd (no passphrase, as Omni requires) |
| `omni/automation-key` | key of service account `automation` (Admin, expires 2027-10-15); `deploy-talos.py omni` uses it |

## SELinux

One extra rule, `/etc/selinux/omni_wireguard.cil`: `container_t` may watch
`container_file_t` socket files (SideroLink's userspace WireGuard watches its
control socket). Without it Omni exits with "error listening on uapi socket:
permission denied".
