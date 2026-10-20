# The lab

> Explanation · [Documentation](../../README.md#documentation)

What the shared services are for, how they depend on each other, and the
principles behind how they are built. The inventory: [Site](../reference/site.md).

## Shared services around the clusters

The Talos clusters (deploy-talos.py) run workloads; everything they depend on
that should outlive a cluster runs beside them, as VMs on the LAN:

| Service | What the clusters use it for |
|---|---|
| `pki` (step-ca) | certificates: every HTTPS endpoint of the site, the clusters' gateways over ACME |
| `oauth` (Keycloak) | logins: `kubectl`, Argo CD, Headlamp, Grafana, Harbor, Artifact Keeper, Forgejo, Omni |
| `forgejo` | Git: the GitOps repository the clusters are deployed from, all code, CI |
| `backup` (RustFS) | etcd backups, off the cluster |
| `registry` (Harbor) | images: pull-through mirrors for every node, the platform's and teams' images |
| `artifacts` (Artifact Keeper) | packages: Maven, npm, PyPI, generic |
| `omni` (optional) | a console for Talos clusters |

Rebuilding a cluster then loses nothing that matters: its configuration is in
Git, its images and packages in the registries, its etcd in the backup bucket,
its users in Keycloak.

**Order matters.** The CA comes first (every other service gets its
certificate from it), then Keycloak (everyone logs in through it), then
Forgejo (it uses both). `site.yml` runs them in that order.

## Code and secrets apart

This repository holds code and public data only and could be published as
is. Credentials live in a separate tree, `/root/lab/lab-secrets`, never
committed ([Secrets tree](../reference/secrets.md)); the inventory names files,
never values, and `site_guard` refuses inline passwords. The same separation
runs through the clusters: the cluster files name credential files, and the
GitOps repository holds Secrets only SOPS-encrypted.

## The same credentials after a rebuild

A rebuilt VM should come back as it was, so that nothing depending on it
breaks. The playbooks therefore never invent a credential that already
exists somewhere: a credential the clusters also hold is taken from the
GitOps repository first, then from the secrets tree, and only generated when
neither has it. A rebuilt RustFS gets the same keys (the clusters' backups
keep working), a rebuilt Keycloak the same client secrets, a rebuilt Forgejo
even the same tokens, written back into its database. deploy-talos.py follows
the same rule for the Secrets it keeps in Git.

What can't be regenerated is data: repositories, users, objects, images.
The playbooks restore configuration, never content, and those need backups
([Back up the services](../how-to/back-up-the-services.md)).

## Choosing components

Open-source components are preferred, and a pinned version must be at least
14 days old unless it fixes a security issue (release dates are noted next to
the pins). The platform-wide decisions and the alternatives considered are
collected in the gitops repository's [Design decisions](https://github.com/vincentbrobald/gitops/blob/main/docs/explanation/design-decisions.md).

## Example names, real settings

The documents use `example.org`, realm `example`, user `alice`; the real
values are settings in the inventory and the roles contain no site name. The
same code builds a second site, and was tested that way from zero on throwaway
VMs.

## Hardened by default

Every VM: SSH keys only, no password or root login (also on the console),
SELinux enforcing, only the listed services on the network, Caddy terminating
TLS in front of a service that listens on localhost. Downloads (the AlmaLinux
image, Caddy, Forgejo, RustFS) are checked against signed or published
checksums.

## Related

- [Ansible and Crossplane](ansible-and-crossplane.md): who manages what inside the services.
- [Getting started](../tutorials/getting-started.md): the services in use.
