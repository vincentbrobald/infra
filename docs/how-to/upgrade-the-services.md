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

## Forgejo

1. Dump it (repositories, database, configuration) to
   `/root/lab/lab-secrets/forgejo/backup/`, without the OS updates:

   ```sh
   ansible-playbook upgrade.yml --limit forgejo --tags forgejo-dump
   ```

2. Set `forgejo_version` in `ansible/roles/forgejo/defaults/main.yml` (a
   release of the same major line, unless its notes say how to migrate; read
   them for a warning against upgrading), then `ansible-playbook forgejo.yml
   --check --diff`: the binary (checked against the release's `.sha256`) and a
   restart, nothing else. Run it without `--check`.
3. Check: `/api/v1/version` shows the version; the login page still offers
   Keycloak; a clone and a push over SSH, a clone over HTTPS; a push to a
   repository with a pipeline starts it (the webhook); Crossplane's Forgejo
   objects stay Ready (`kubectl get managed`).

To go back: set the previous version and run `forgejo.yml` again; if the
database was migrated, restore the dump on a rebuilt VM
([Back up the services](back-up-the-services.md)).

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
