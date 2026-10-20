# Registries

> Explanation · [Documentation](../../README.md#documentation)

Why the site has two registries, Harbor for images and Artifact Keeper for
packages, and how they are filled. The facts: [registry](../reference/vms/registry.md),
[artifacts](../reference/vms/artifacts.md).

## Mirrors for the clusters

Every node pulls through Harbor: a proxy-cache project per upstream
(`docker.io`, `ghcr.io`, ...), named after it, so that
`registry.example.org/docker.io/library/nginx` is `docker.io/library/nginx`.
containerd is pointed at those projects as mirrors, with the upstream as
fallback. Pulls are fast and survive upstream rate limits and outages; a
rebuilt registry refills on demand.

## Why Harbor

The site needs per-team registries: a project per team with a quota, roles
for Keycloak groups, a robot account per pipeline, scanning on push, and all
of it declared from Git. Harbor has each of these and a Crossplane provider
(provider-upjet-harbor) to manage them. The registry it replaced (zot) had
mirrors and OIDC but no per-project roles or robot accounts. Harbor is heavier
(a dozen containers, PostgreSQL, Redis), which is why it runs on a VM of its
own with 8 GiB.

## One project per producer

The platform's own images and each team's go to a project of their own, with
a robot account per pipeline that may push to that project only. Teams push
as themselves too (their Keycloak group is maintainer of their project), and
everything is public for pulls inside the site, so clusters need no pull
credentials.

## Packages need more than an OCI registry

Builds need Maven, npm and PyPI repositories: hosted ones to publish to, and
pull-through caches of the public indexes. Artifact Keeper (MIT) does all
formats with hosted, proxy and virtual repositories, OIDC login with groups,
and an API complete enough to manage it declaratively. Nexus, the usual
choice, no longer ships open-source builds. Each team gets a hosted repository
per format and a virtual one that resolves its own packages first, then the
shared caches.

## Content from Git

Neither registry is configured by hand. Projects, proxy caches, robots,
repositories, permissions and logins are Crossplane objects in the GitOps
repository: provider-upjet-harbor for Harbor, our own provider-artifact-keeper
for Artifact Keeper (no Terraform provider exists for it). A rebuilt VM gets
its structure back from Git; only its stored images and packages are data.

## Admins decided at login

Members of Keycloak's `registry-admins` are admins in both. Harbor decides it
at each login and doesn't store it (its user list shows them as non-admins);
Artifact Keeper maps the group at login. Local admin accounts remain for the
providers and as break-glass.
