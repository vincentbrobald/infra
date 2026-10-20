# Infrastructure VMs

Shared services for the lab clusters, as VMs on the LAN, built and configured
by the Ansible playbooks in `ansible/`: the CA (`pki`), Keycloak (`oauth`),
Forgejo, S3 for backups (`backup`), Harbor (`registry`), Artifact Keeper
(`artifacts`) and optionally Omni. Also here: `dns/opnsense-dns.py`, which
registers the clusters' names on the router.

This directory holds code and public data only; credentials live in
`/root/lab/lab-secrets`. The documents use example names (`example.org`,
realm `example`); the real ones are inventory settings.

```sh
export PATH=~/.venvs/ansible/bin:$PATH
cd /root/lab/infra/ansible && ansible-playbook site.yml --check --diff
```

New here? Start with the tutorial [Getting started](docs/tutorials/getting-started.md).

## The lab at a glance

Eight repositories make the platform. New to it, read in this order:
this repository's [Getting started](docs/tutorials/getting-started.md) (use
the site as a person), talos-install's
[Getting started](https://github.com/vincentbrobald/talos-install/blob/main/docs/tutorials/getting-started.md)
(build a cluster), then gitops's tutorials (teams, changes, Crossplane).

| Repository | What | Start with |
|---|---|---|
| infra (this one) | the infrastructure VMs (`ansible/`), the site's DNS records (`dns/`) | [Getting started](docs/tutorials/getting-started.md), [Site](docs/reference/site.md) |
| [talos-install](https://github.com/vincentbrobald/talos-install) | `deploy-talos.py`: Kubernetes on Talos Linux | its [Getting started](https://github.com/vincentbrobald/talos-install/blob/main/docs/tutorials/getting-started.md) |
| [gitops](https://github.com/vincentbrobald/gitops) | what Argo CD deploys: platform services, teams, Crossplane objects | its [Onboard a team](https://github.com/vincentbrobald/gitops/blob/main/docs/tutorials/onboard-a-team.md); team members: [Ship your first change](https://github.com/vincentbrobald/gitops/blob/main/docs/tutorials/ship-your-first-change.md) |
| [gitops-scanner](https://github.com/vincentbrobald/gitops-scanner) | the gitops repository's merge check | its [How it works](https://github.com/vincentbrobald/gitops-scanner/blob/main/docs/explanation/how-it-works.md) |
| [provider-forgejo](https://github.com/vincentbrobald/provider-forgejo) | Crossplane provider for Forgejo | its [Kinds](https://github.com/vincentbrobald/provider-forgejo/blob/main/docs/reference/kinds.md) |
| [provider-artifact-keeper](https://github.com/vincentbrobald/provider-artifact-keeper) | Crossplane provider for Artifact Keeper | its [Kinds](https://github.com/vincentbrobald/provider-artifact-keeper/blob/main/docs/reference/kinds.md) |
| [pac-demo](https://github.com/vincentbrobald/pac-demo) | the smallest Pipelines-as-Code pipeline | its README |
| [lb](https://github.com/vincentbrobald/lb) | an SNI load balancer, not running | its README |

Credentials are in `/root/lab/lab-secrets`, never in Git
([Secrets tree](docs/reference/secrets.md)).

## Documentation

The documentation follows [Diátaxis](https://diataxis.fr/): tutorials to
learn, how-to guides for tasks, reference to look things up, explanation to
understand.

**Tutorials**
- [Getting started](docs/tutorials/getting-started.md): check the services, trust the CA, get an account, log in to a cluster
- [Change a service with Ansible](docs/tutorials/change-a-service.md): a setting previewed, applied, proved by a second run, put back

**How-to guides**

| Task | Guide |
|---|---|
| Apply the playbooks, change a setting, grow a disk | [Run the playbooks](docs/how-to/run-the-playbooks.md) |
| A new Talos cluster with this site's services | [Build a cluster on this site](docs/how-to/build-a-cluster-on-this-site.md) |
| A broken VM, or one no longer needed | [Rebuild or remove a VM](docs/how-to/rebuild-or-remove-a-vm.md) |
| OS updates, new service releases | [Upgrade the services](docs/how-to/upgrade-the-services.md) |
| Save what the playbooks can't restore | [Back up the services](docs/how-to/back-up-the-services.md) |
| A machine or tool rejects the site's certificates | [Trust the site CA](docs/how-to/trust-the-site-ca.md) |
| A certificate without ACME | [Issue a certificate by hand](docs/how-to/issue-a-certificate.md) |
| An account for a person | [Add a Keycloak user](docs/how-to/add-a-keycloak-user.md) |
| Undo a Crossplane takeover | [Hand an object back to Ansible](docs/how-to/hand-back-to-ansible.md) |
| A new webhook secret | [Rotate a webhook secret](docs/how-to/rotate-a-webhook-secret.md) |
| Another router for DNS registration | [Set up DNS registration](docs/how-to/set-up-dns-registration.md) |
| Names in the router's DNS | [Register DNS records](docs/how-to/register-dns-records.md) |
| The Talos console | [Use Omni](docs/how-to/use-omni.md) |
| Something fails | [Troubleshoot](docs/how-to/troubleshoot.md) |

**Reference**
- [Site](docs/reference/site.md): site values, VMs, addresses, access rules, clusters
- VMs: [pki](docs/reference/vms/pki.md), [oauth](docs/reference/vms/oauth.md), [forgejo](docs/reference/vms/forgejo.md), [backup](docs/reference/vms/backup.md), [registry](docs/reference/vms/registry.md), [artifacts](docs/reference/vms/artifacts.md), [omni](docs/reference/vms/omni.md)
- [Playbooks](docs/reference/playbooks.md): what each does, roles, the credential lookup, what isn't restored
- [Secrets tree](docs/reference/secrets.md): `/root/lab/lab-secrets`
- [opnsense-dns.py](docs/reference/opnsense-dns.md): commands, records, settings, this site's values
- [CI](docs/reference/ci.md): Pipelines-as-Code on the site

**Explanation**
- [Design decisions](docs/explanation/design-decisions.md): the choices, the alternatives considered, when to revisit them
- [The lab](docs/explanation/the-lab.md): the shared services, code and secrets apart, credentials that survive a rebuild
- [Ansible and Crossplane](docs/explanation/ansible-and-crossplane.md): who manages what inside the services
- [PKI](docs/explanation/pki.md): an internal CA, short-lived certificates, the name constraint
- [DNS registration](docs/explanation/dns-registration.md): records by owner, checks, caches
- [Pipelines on the cluster](docs/explanation/ci.md): the gate, building without privileges
- [Registries](docs/explanation/registries.md): mirrors, projects, packages, content from Git

## Files

| Path | Content |
|---|---|
| `ansible/` | playbooks, roles, the site inventory |
| `pki/root_ca.crt` | the public root CA certificate (the playbooks write it when it's missing) |
| `dns/opnsense-dns.py`, `dns/opnsense-dns.yaml` | the DNS registration tool and the site's settings (made from the template `opnsense-dns.example.yaml`) |
| `docs/` | the documentation |

## License

MIT (LICENSE), © 2026 Vincent Brobald.
