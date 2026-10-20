# Back up the services

> How-to · [Documentation](../../README.md#documentation)

Save what the playbooks can't restore. None of this is automated yet, except
the clusters' etcd backups and Forgejo's dump during `upgrade.yml`.
What is data and what is configuration: [Playbooks](../reference/playbooks.md#what-the-playbooks-dont-restore).

## The CA (`pki`)

After any change to the CA:

```sh
ssh -i /root/lab/lab-secrets/pki/id_ed25519 almalinux@pki.example.org 'sudo tar -C /etc -czf - step-ca' \
  > /root/lab/lab-secrets/pki/backup/step-ca-$(date +%F).tar.gz
```

The playbook writes one by itself after creating, restoring or re-issuing.
It is the only way to restore the CA.

## Keycloak (`oauth`)

```sh
ssh -i /root/lab/lab-secrets/oauth/id_ed25519 almalinux@oauth.example.org \
  'sudo -u postgres pg_dump -Fc keycloak' > keycloak-$(date +%F).dump
```

Users and their group memberships are only in this database.

## Forgejo (`forgejo`)

`forgejo dump` makes one archive of `/var/lib/forgejo` (repositories, SQLite)
and `/etc/forgejo`. `upgrade.yml` fetches one to
`/root/lab/lab-secrets/forgejo/backup/` before updating the VM. By hand, on
the VM, the same command as `ansible/tasks/upgrade.yml`:

```sh
sudo -u git /usr/local/bin/forgejo dump --config /etc/forgejo/app.ini --type tar.gz \
  --file /var/lib/forgejo/dump.tar.gz --tempdir /var/lib/forgejo --skip-log
```

## Omni

`/var/lib/omni` on `omni`, with the VM; or re-import the clusters after a
rebuild.

## Fetch an etcd backup

The clusters write their etcd snapshots to `backup` themselves. To get one
(the cluster's user may only write):

```sh
ssh -i /root/lab/lab-secrets/backup/id_ed25519 almalinux@backup.example.org
sudo /usr/local/bin/rc ls local/talos-backups/lab/
sudo /usr/local/bin/rc cat local/talos-backups/lab/lab-<time>.snap.zst.age > snap.age
```

Decrypt it with `/root/lab/lab-secrets/backup/talos-backup-age.key` and
restore it as talos-install's [Back up and restore etcd](https://github.com/vincentbrobald/talos-install/blob/main/docs/how-to/back-up-and-restore-etcd.md#restore) describes.

## Off this host

Everything above, the secrets tree and the backups bucket live on the same
host as the clusters. Copy `/root/lab/lab-secrets` (including
`sops/admin.agekey` and `backup/talos-backup-age.key`) to an encrypted store
elsewhere.
