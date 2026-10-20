# Site

> Reference · [Documentation](../../README.md#documentation)

The site's names, addresses and VMs. The documents use example names; the
real values are settings, so the same code serves another domain.

## Site values

| In the documents | Set in |
|---|---|
| `example.org` (the domain: `pki.example.org`, `oauth.example.org`, ...) | `site_domain` in `ansible/inventory/group_vars/all.yml`, and the host names in `ansible/inventory/hosts.yml` |
| realm `example` | `site_keycloak_realm` (same file) |
| `example.org CA` (the CA's name) | `step_ca_name` (default `<site_domain> CA`) |
| `site-root-ca.crt` (the CA's file in the VMs' trust stores) | `site_ca_anchor_name` (same file); names in `site_ca_retired_anchor_names` are removed |
| `alice` (a person's account, owner of `alice/pac-demo`) | `forgejo_repos` in `ansible/inventory/group_vars/forgejo.yml` |
| `pac.apps.lab.example.org`, `*.apps.<cluster>.example.org` | the cluster files (`/root/<cluster>.yaml`) |

The roles contain no site name: changing these settings and
`dns/opnsense-dns.yaml` moves the site to another domain.

## VMs

All are AlmaLinux 10 VMs on `bridge0` (the LAN), started with the host
(`virsh autostart`), with a fixed MAC so a re-created VM keeps its address and
name.

| VM | Name | Address | Size | Runs | Details |
|---|---|---|---|---|---|
| `pki` | pki.example.org | 192.0.2.162 | 1 vCPU, 1.5 GiB, 10 GB | step-ca 0.30.2 | [pki](vms/pki.md) |
| `oauth` | oauth.example.org | 192.0.2.111 | 2 vCPU, 4 GiB, 20 GB | Keycloak 26.8.1, PostgreSQL 16, Caddy | [oauth](vms/oauth.md) |
| `forgejo` | forgejo.example.org | 192.0.2.100 | 2 vCPU, 2 GiB | Forgejo 16.0.5, Caddy (Fedora 44) | [forgejo](vms/forgejo.md) |
| `backup` | backup.example.org | 192.0.2.193 | 2 vCPU, 2 GiB, 60 GB | RustFS 1.0.1 (S3), Caddy | [backup](vms/backup.md) |
| `registry` | registry.example.org | 192.0.2.136 | 4 vCPU, 8 GiB, 100 GB | Harbor 2.15.4, Caddy | [registry](vms/registry.md) |
| `artifacts` | artifacts.example.org | 192.0.2.176 | 4 vCPU, 6 GiB, 60 GB | Artifact Keeper 1.10.2, PostgreSQL 18, Caddy | [artifacts](vms/artifacts.md) |
| `omni` (optional) | omni.example.org | 192.0.2.177 | 2 vCPU, 4 GiB, 30 GB | Omni v1.12.2 (Podman), Caddy | [omni](vms/omni.md) |

The SNI load balancer `lb` (HAProxy, not used by the clusters) has its code and
playbook in `/root/lab/lb` (`alice/lb`); its VM doesn't exist.

## Addresses (192.0.2.0/24)

| Range | Use |
|---|---|
| .1 | OPNsense: router, DHCP, DNS (Unbound :53, Dnsmasq :53053 for `example.org`) |
| .100-.199 | DHCP pool (infrastructure VMs, other machines) |
| .200-.229 | Talos cluster `lab` (`/root/lab/lab.yaml`): API VIP .200, ingress gateway .204 |

## Access to the VMs

| Rule | Value |
|---|---|
| SSH user | `almalinux` (Forgejo: `fedora`), key `/root/lab/lab-secrets/<vm>/id_ed25519`, passwordless sudo |
| Login | SSH key only; no password or root login, also on the console (`virsh console <vm>`) |
| Firewall | firewalld isn't running; only the services listed per VM listen on the network |
| SELinux | enforcing |
| CA | every VM trusts the site CA (role `site_ca`); the hypervisor host doesn't |

## Clusters

| Cluster | Files | Uses |
|---|---|---|
| Talos `lab` | `/root/lab/lab.yaml`, `/root/lab/lab-cluster/` | 9 VMs: 3 × 8 GiB / 2 vCPU control planes (disks on the host's NVMe SSD, `/var/lib/libvirt/images-ssd`: etcd), 3 × 12 GiB / 4 vCPU workers, 3 × 4 GiB / 2 vCPU storage nodes (72 GiB of the host's 125 GiB; the other disks on its hard disk, `/var/lib/libvirt/images`); deployed from `alice/gitops` `clusters/lab` |

| URL | What |
|---|---|
| `https://argocd.apps.lab.example.org` | Argo CD |
| `https://headlamp.apps.lab.example.org` | Headlamp |
| `https://grafana.apps.lab.example.org` | Grafana |
| `https://tekton.apps.lab.example.org` | Tekton Dashboard (read-only, group `k8s-admins`) |
| `https://pac.apps.lab.example.org` | Pipelines-as-Code's webhook |
