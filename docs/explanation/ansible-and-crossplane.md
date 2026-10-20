# Ansible and Crossplane

> Explanation · [Documentation](../../README.md#documentation)

Why the services are installed by Ansible but their content is managed by
Crossplane from the GitOps repository, and where the line is.

## Bootstrap here, content in Git

Ansible builds the VMs and installs the services: binaries, configuration
files, databases, TLS, the accounts the platform itself needs to start. What
lives *inside* the services and belongs to what runs on the clusters (Keycloak
clients and groups, Forgejo organizations, teams, repositories and
collaborators, Harbor projects and robots, Artifact Keeper repositories and
permissions) is declared in the GitOps repository and reconciled by Crossplane
on cluster `lab`.

That puts each object next to what needs it: a team's Keycloak group,
Forgejo team and Harbor project come from the team's folder, and go with it.
The same pull request and merge check govern a Deployment and the Keycloak
client it logs in with, and a change made by hand in a service's console is
undone.

## What stays with Ansible

| Object | Why |
|---|---|
| the services, their databases, TLS | Crossplane needs them running first |
| Keycloak's realm, the admin groups, clients `forgejo`, `omni`, `crossplane-lab` | needed before the clusters exist, or by services outside them |
| Forgejo's users `gitadmin`, `argocd-reader`, `pac-bot`, `crossplane-lab` | the accounts the platform starts with |
| `alice/gitops`'s settings | Crossplane mustn't be able to lock the platform out of its own repository |
| `alice/provider-forgejo`'s settings | Crossplane managing its own provider's repository would be circular |
| `crossplane-lab`'s own access | it can't grant itself access |
| the clusters' `k8s-<name>` and `argocd-<name>` clients | deploy-talos.py's: needed before Crossplane exists in the cluster |

## Crossplane's reach is bounded

Crossplane signs in with accounts made here, each with the least it needs:
Keycloak's `crossplane-lab` administers realm `example` only; Forgejo's
`crossplane-lab` is a site admin (to create the teams' CI users), which the
GitOps repository bounds with admission policies on what may be created in
the cluster; Harbor's and Artifact Keeper's admin accounts are local.

## Taking over, and handing back

Objects Ansible used to manage were taken over without change: Crossplane
first observed them and its view was compared with the service's, then it
started managing them. Its first writes only made defaults explicit. A backup
of each object as it was, and a way to hand it back to Ansible, exist for
every takeover ([Hand an object back to Ansible](../how-to/hand-back-to-ansible.md)).

Crossplane never deletes those objects (no `Delete` policy): removing one from
Git leaves it in the service, so a mistaken removal can't destroy a repository
or a client others depend on.
