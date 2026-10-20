# Build a cluster on this site

> How-to · [Documentation](../../README.md#documentation)

Build another Talos cluster with this site's services. The procedure is
talos-install's tutorial, [Getting started](https://github.com/vincentbrobald/talos-install/blob/main/docs/tutorials/getting-started.md);
this page lists what to put in the cluster file here. `/root/lab/lab.yaml`
is a complete working example.

1. Pick an unused LAN address block from `.200` upwards, not overlapping
   `lab`'s `.200-.229`, and add it to the address table of
   [Site](../reference/site.md#addresses-19202024).
2. In the cluster file:

   | Setting | Value |
   |---|---|
   | `lan.bridge` | `bridge0` |
   | `network.nameservers` (existing bridge only) | `[192.0.2.1]` |
   | domain (`template --domain`) | `example.org` |
   | `oidc.issuer` | `https://oauth.example.org/realms/example` |
   | `oidc.caFile` | `/root/lab/infra/pki/root_ca.crt` |
   | `oidc.keycloakAdminPasswordFile` | `/root/lab/lab-secrets/oauth/keycloak-admin-password` |
   | `certManager.acmeServer` | `https://pki.example.org/acme/acme/directory` |
   | `registry.mirror` | `https://registry.example.org` |
   | `talosBackup.s3.endpoint` | `https://backup.example.org`, bucket `talos-backups` |

3. Build it, then register its names:

   ```sh
   deploy-talos.py dns-records -f <cluster>.yaml --domain example.org | /root/lab/infra/dns/opnsense-dns.py sync
   ```

4. To deploy it from the GitOps repository like `lab`, prepare its folder
   there first: the gitops repository's [Add a cluster](https://github.com/vincentbrobald/gitops/blob/main/docs/how-to/add-a-cluster.md).
5. Check: `getent hosts api.<cluster>.example.org` answers the VIP, and
   `KUBECONFIG=<cluster>-cluster/kubeconfig-oidc kubectl get nodes` logs you in
   through Keycloak.
