# Use Omni

> How-to · [Documentation](../../README.md#documentation)

Look at the site's Talos clusters in Omni, and work with `omnictl`. Omni:
[omni](../reference/vms/omni.md). Importing a cluster is deploy-talos.py's
`omni` command (talos-install: [Import into Omni](https://github.com/vincentbrobald/talos-install/blob/main/docs/how-to/import-into-omni.md)).

## Log in

Open `https://omni.example.org` and log in through Keycloak. Omni admits only
users it knows: those in `omni_initial_users`
(`ansible/inventory/group_vars/omni.yml`, at its first start) and those an
admin adds in Settings > Users.

## Use `omnictl`

```sh
export OMNI_ENDPOINT=https://omni.example.org
export OMNI_SERVICE_ACCOUNT_KEY=$(cat /root/lab/lab-secrets/omni/automation-key)
cat /etc/pki/tls/certs/ca-bundle.crt /root/lab/infra/pki/root_ca.crt > /tmp/omni-ca.pem
export SSL_CERT_FILE=/tmp/omni-ca.pem
~/.cache/talos/v1.14.2/omnictl-v1.12.2 get clusters
```

You should see `lab`. deploy-talos.py downloads `omnictl` into its cache
directory (`omnictl-<version>`). The service account key expires 2027-10-15.

## Before unlocking a cluster

Imported clusters are **locked**: Omni changes nothing, and deploy-talos.py,
the GitOps repository and tuppr keep managing them. `omnictl cluster unlock
<name>` hands the machine configs and the Kubernetes endpoint to Omni. Decide
first how that fits with those tools.

## Undo an import still locked

```sh
deploy-talos.py omni --abort -f /root/lab/lab.yaml
talosctl apply-config ...   # each node's backed-up config, from <cluster>-backup-<time>.zip
```

The second step removes Omni's documents (SideroLinkConfig, EventSinkConfig,
KmsgLogConfig) from the nodes.
