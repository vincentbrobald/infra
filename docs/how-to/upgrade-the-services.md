# Upgrade the services

> How-to · [Documentation](../../README.md#documentation)

Update the VMs' operating systems, or move a service to a new release. Pick
releases at least 14 days old, unless they fix a security issue. Read the
release notes first: Keycloak, Harbor and Artifact Keeper migrate their
databases on start.

## Operating systems

```sh
cd /root/lab/infra/ansible && ansible-playbook upgrade.yml
```

One VM at a time: every package to its latest version, a reboot when needed,
and the service must answer before the next VM. Forgejo goes last, after a
`forgejo dump` fetched to `/root/lab/lab-secrets/forgejo/backup/`.

## Keycloak

1. Dump the database on `oauth`:

   ```sh
   sudo -u postgres pg_dump -Fc keycloak > /root/keycloak-before-<version>.dump
   ```

2. Set `keycloak_version` in `ansible/roles/keycloak/defaults/main.yml` and run
   `ansible-playbook keycloak.yml`. The release unpacks to
   `/opt/keycloak-<version>` and `/opt/keycloak` points at it.
3. Set the new version in Crossplane's credentials, gitops
   `crossplane-system/keycloak-credentials` key `keycloak_version` (its account
   can't read the server's version).
4. Check: `https://oauth.example.org/admin/` logs you in; the clusters' logins work.

To go back: point `/opt/keycloak` at the previous directory (it stays) and
restore the dump (`sudo -u postgres pg_restore -c -d keycloak <dump>`).

## Harbor

Set `harbor_version` and `harbor_installer_md5` (from the release's `md5sum`
file) in the inventory and run `ansible-playbook registry.yml`: it unpacks the
new installer, prepares and restarts. Check: `https://registry.example.org`
logs you in, and a node can pull through a proxy cache.

## Artifact Keeper

Set `artifact_keeper_backend_version` and `artifact_keeper_web_version` (the
web UI has its own versions) and run `ansible-playbook artifacts.yml`. Check:
`https://artifacts.example.org` logs you in through Keycloak.

## Caddy

Set `caddy_version` in `ansible/inventory/group_vars/all.yml` and run
`site.yml`: every VM with Caddy gets the release binary.
