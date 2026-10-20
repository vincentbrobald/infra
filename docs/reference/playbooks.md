# Playbooks

> Reference · [Documentation](../../README.md#documentation)

The Ansible playbooks in `ansible/` that create and configure every VM. To
run them: [Run the playbooks](../how-to/run-the-playbooks.md). Why Ansible
stops where Crossplane starts: [Ansible and Crossplane](../explanation/ansible-and-crossplane.md).

| Playbook | Hosts | Does |
|---|---|---|
| `pki.yml` | `pki` | step-ca: CA, ACME and JWK provisioners, the intermediate's name constraint; restores a missing CA from the newest backup; refuses a root differing from `pki/root_ca.crt`; writes a backup after a creation, restore or re-issue |
| `keycloak.yml` | `keycloak` | Keycloak, PostgreSQL, Caddy; realm `example`, its groups, clients `forgejo`, `omni` and `crossplane-lab` |
| `forgejo.yml` | `forgejo` | Forgejo binary, `app.ini` and its secret files, Caddy, the Keycloak login, users `gitadmin`, `argocd-reader`, `pac-bot`, `crossplane-lab` and their tokens, the repositories' Ansible settings (collaborators, deploy keys, webhooks, branch protection) |
| `backup.yml` | `s3` | RustFS, `rc`, Caddy; bucket `talos-backups` (object lock, lifecycle); user `talos-backup` (write-only) |
| `registry.yml` | `registry` | Docker, Harbor (its installer); removes the former registry |
| `artifacts.yml` | `artifacts` | Docker, Artifact Keeper (compose: backend, web UI, PostgreSQL), Caddy |
| `omni.yml` | `omni` | only with a host in group `omni`: Omni in Podman, Caddy, Keycloak login, its etcd key and service account key |
| `site.yml` | all | all of the above, in that order |
| `upgrade.yml` | all | OS updates, one VM at a time, Forgejo last after a `forgejo dump`; latest packages, a reboot when `dnf needs-restarting -r` asks, the service must answer before the next VM |
| `gitops.yml` | localhost | imported by the others: a read-only checkout of `alice/gitops` and `sops`, for credentials kept in Git |

Every playbook is safe to re-run; a run on VMs in line with it reports no
change. Each service playbook first creates its VM when missing.

## Layout

| Path | Content |
|---|---|
| `ansible/inventory/hosts.yml` | hosts, VM sizes (`vm:`) |
| `ansible/inventory/group_vars/` | settings per service; `all.yml` the site values |
| `ansible/roles/` | `libvirt_vm`, `site_guard`, `site_ca`, `caddy`, `docker`, `step_ca`, `keycloak`, `keycloak_realm`, `forgejo`, `rustfs`, `harbor`, `artifact_keeper`, `omni` |
| `ansible/tasks/` | shared task files (e.g. `zot-removed.yml`) |
| `ansible/plugins/lookup/site_secret.py` | the credential lookup |

Service host names come from the inventory groups, so the same playbooks
deploy a second set of VMs from another inventory.

## Role `libvirt_vm`

| Step | Behaviour |
|---|---|
| Preflight | refuses a name that already answers on the network, a missing bridge, image files of another VM |
| Image | newest AlmaLinux 10 GenericCloud, checked against AlmaLinux's GPG-signed `CHECKSUM` (pinned key `EE6DB7B9…C2A1E572`), cached in `~/.cache/alma10` |
| Seed | cloud-init: host name, user (`ansible_user`, passwordless sudo), SSH key (generated next to `ansible_ssh_private_key_file` when missing) |
| Addressing (`vm.network`, default `site_vm_network: dhcp`) | `dhcp`: the router's DHCP gives the address and registers the name; `static`: `vm.address` via cloud-init with the site's gateway and nameservers, and an A record on the router (`dns/opnsense-dns.py`, owner `infra-ansible:<vm>`), checked every run. Applies at creation only |
| MAC | derived from the host name unless given: a re-created VM gets the same lease and name |
| Wait | guest agent address, cloud-init, DNS, SSH |
| Disk | a larger `vm.disk` grows a running VM (`virsh blockresize`); smaller is reported, never applied |
| Root file system | grown to fill the disk on every run (partition; with LVM the PV and root LV too) |
| Autostart | set on every VM |
| Existing VMs | never touched otherwise; an interrupted creation resumes; in `--check` a missing VM is "would create" and its service play is skipped |

## Role `caddy`

Caddy's release binary (`caddy_version` in `group_vars/all.yml`, SHA-512
checked) in `/usr/local/bin`, run by the package's unit through a drop-in
(`caddy.service.d/release-binary.conf`), with the packaged binary's SELinux
type (on Fedora `httpd_exec_t`). The package still provides the unit, user and
directories.

## Credential lookup (`site_secret`)

No credential is written in the inventory (`site_guard` refuses inline
passwords). Each is a file under `/root/lab/lab-secrets`, read in this order:

| Order | Source | Applies to |
|---|---|---|
| 1 | the gitops repository: a SOPS Secret of a cluster (`gitops: {topic: <namespace>/<name>, key}`), searched in every cluster folder, decrypted with `sops/admin.agekey`; the local file is made to match (previous content kept as `<file>.pre-gitops`) | `talos-backup/talos-backup-s3`, pac-bot's token and webhook secrets (`*/forgejo-pac`), credentials Crossplane also holds |
| 2 | the file | everything else |
| 3 | generated into the file | credentials the playbooks create (RustFS keys, client secrets, passwords); a missing Forgejo token is created by Forgejo and written |

If Forgejo is down, `gitops.yml` uses the previous checkout in
`~/.cache/infra-ansible/gitops` with a warning, and stops without one.

## What the playbooks don't restore

| Data | Back it up with |
|---|---|
| the Git repositories' content | `forgejo dump` ([Back up the services](../how-to/back-up-the-services.md)) |
| Keycloak's users and group memberships (teams' come back from Crossplane) | `pg_dump keycloak` |
| RustFS objects (the etcd backups) | a second copy elsewhere (not set up) |
| Harbor's database (users' CLI secrets) and pushed images | the VM's disk; projects and robots come back from Crossplane |
| Artifact Keeper's packages and database | the VM's disk; repositories and permissions come back from Crossplane |
| Omni's data | `/var/lib/omni`, or re-import the clusters |
