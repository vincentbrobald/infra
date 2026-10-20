# Design decisions

> Explanation · [Documentation](../../README.md#documentation)

The choices the shared services are built on, what else was considered, and
when to look at them again. The platform-wide decisions (GitOps, teams,
Crossplane) are in the gitops repository's [Design decisions](https://github.com/vincentbrobald/gitops/blob/main/docs/explanation/design-decisions.md).

## Principles

- **Open source** components, **pinned versions at least 14 days old**
  unless they fix a security issue (release dates next to the pins).
- **Code and secrets apart:** this repository could be published; credentials
  live in `/root/lab/lab-secrets`.
- **Example names in the documents, real values in the inventory:** the roles
  contain no site name.

## Where the services run

### VMs beside the clusters, not workloads in them

**Decision.** The CA, Keycloak, Forgejo, S3, Harbor, Artifact Keeper and Omni
run as VMs on the LAN.
**Why.** The clusters depend on them to be built (certificates, logins, the
GitOps repository, images): they must exist before a cluster and outlive it.
A rebuilt cluster loses nothing. See [The lab](the-lab.md).
**Alternatives.** Running them in a cluster: a cluster would depend on itself
to start.

### Ansible for VMs and services

**Decision.** Ansible playbooks create the VMs (libvirt) and install and
configure the services; every playbook is idempotent and safe to re-run.
**Why.** Agentless, readable, and the same playbooks rebuild a VM from
nothing or bring it back in line.
**Alternatives.** Terraform with a libvirt provider for the VMs plus a
configuration tool: two tools and a state file for a handful of VMs.
**Limit.** Ansible stops at the service's bootstrap; content inside the
services is Crossplane's ([Ansible and Crossplane](ansible-and-crossplane.md)).

### AlmaLinux 10 cloud images, verified

**Decision.** VMs boot AlmaLinux 10 GenericCloud images, checked against
AlmaLinux's GPG-signed checksums with a pinned key; cloud-init seeds the user
and key.
**Why.** An enterprise-stable base with SELinux enforcing; a verified image
without a custom build.
**Exception.** The Forgejo VM is Fedora 44 from before the role existed; a
rebuild would make it AlmaLinux.

### Fixed MACs and DHCP

**Decision.** A VM's MAC is derived from its name; addresses come from the
router's DHCP, which registers the name. Static addressing is available per
VM, with an A record kept on the router.
**Why.** A re-created VM gets the same address and name without any address
bookkeeping here.

### Caddy in front of every service

**Decision.** Each service listens on localhost behind Caddy, which gets its
certificate from step-ca over ACME; Caddy's release binary is used, run by
the packaged unit.
**Why.** TLS and renewal (24-hour certificates) without per-service setup;
the distribution packages lag upstream.

### Docker compose where the vendor ships it

**Decision.** Harbor and Artifact Keeper run with Docker compose, as their
projects ship them; Omni runs in Podman (a systemd quadlet).
**Why.** Harbor's installer and Artifact Keeper's compose file are the
supported deployments; following them keeps upgrades simple.
**Cost.** Docker on two VMs, with its own firewall rules (nftables) and ports
pinned to loopback so that only Caddy is reachable.

## The services

### step-ca with a name-constrained intermediate

**Decision.** The site's CA is step-ca with ACME; the intermediate is
constrained to `example.org`; certificates last 24 hours; a lost CA is
restored from backup, never re-created silently.
**Why.** Trusting the root only affects the site's domain, leaked keys expire
within a day, and a rebuilt `pki` is the same CA. See [PKI](pki.md).

### Keycloak, one realm for the site

**Decision.** Keycloak (single node, PostgreSQL) with one realm for people;
Crossplane's account lives in `master` with roles on that realm only.
**Why.** One login for clusters, Git, registries and consoles; group
membership decides admin rights everywhere.

### Forgejo for Git

**Decision.** Forgejo (SQLite), sign-in required for everything, login through
Keycloak.
**Why.** A lightweight, community-governed Git server with an API complete
enough for a Crossplane provider, webhooks for Pipelines-as-Code, and branch
protection with required statuses.
**Alternatives.** GitLab: much heavier for one site.

### RustFS for S3

**Decision.** RustFS (Apache-2.0) holds the etcd backups, with object lock
and a write-only user.
**Why.** S3 with versioning, object lock and fine-grained policies on a small
VM. **Cost.** A young project; the backups have no second copy yet.

### Harbor and Artifact Keeper

See [Registries](registries.md): Harbor for its per-project roles, robots and
scanning; Artifact Keeper because Nexus's prebuilt editions are no longer open
source.

### Omni, optional and locked

**Decision.** Omni runs only when the inventory has an `omni` host; clusters
are imported locked.
**Why.** A console for Talos clusters without giving it control. Its license
(Business Source License) allows home-lab use.

## Credentials

### Git first, then the file, then generated

**Decision.** The playbooks read a credential from the GitOps repository when
a cluster holds it there, else from its file, else generate it.
**Why.** The cluster and the service always agree, and a rebuilt VM gets the
same credentials back. See [The lab](the-lab.md#the-same-credentials-after-a-rebuild).

## DNS

### Host entries on the router, by owner

**Decision.** `opnsense-dns.py` writes Dnsmasq host entries on OPNsense, tagged
with an owner; deploy-talos.py prints the records.
**Why.** The router is the LAN's DNS; owners keep each writer to its own
entries, and hand-made entries are never touched. See [DNS registration](dns-registration.md).
**Alternatives.** external-dns: it would derive names from cluster objects,
while here the names come from the cluster file.

## Retired

### The SNI load balancer

**Decision.** `lb` (HAProxy, SNI passthrough) is kept as code in its own
repository, its VM not running.
**Why.** LAN-mode clusters have their own addresses (API VIP, gateway), so
the site doesn't need it. **Revisit if** private clusters must be reached
from the LAN, or one public entry point must serve several clusters.
