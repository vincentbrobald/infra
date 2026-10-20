# Getting started

> Tutorial · [Documentation](../../README.md#documentation)

In this tutorial you check that the shared services run, make your browser
trust the site's certificates, get a Keycloak account, and log in to the
cluster `lab` with it. At the end you use `kubectl`, Argo CD and Headlamp as
yourself, not as an admin certificate.

You need a shell on the hypervisor host as root, and a workstation with a
browser. The commands use the example domain `example.org` and realm
`example`: replace them with the site's (`site_domain` and
`site_keycloak_realm` in `ansible/inventory/group_vars/all.yml`).

## 1. Check the shared services

```sh
virsh list --all
curl -sf --cacert /root/lab/infra/pki/root_ca.crt https://pki.example.org/health
curl -sf --cacert /root/lab/infra/pki/root_ca.crt \
    https://oauth.example.org/realms/example/.well-known/openid-configuration | head -c 80; echo
/root/lab/infra/dns/opnsense-dns.py list
```

You should see `pki`, `oauth`, `forgejo` and the other VMs `running`,
`{"status":"ok"}` from step-ca, the beginning of Keycloak's OIDC
configuration, and the DNS names registered on the router. A VM that is shut
off starts with `virsh start <vm>`.

## 2. Trust the site's CA on your workstation

Every service and every cluster UI has a certificate from the site's own CA.
Copy `/root/lab/infra/pki/root_ca.crt` to your workstation and import it into
your browser or system trust store. On Fedora, RHEL or AlmaLinux:

```sh
sudo cp root_ca.crt /etc/pki/ca-trust/source/anchors/site-root-ca.crt && sudo update-ca-trust
```

Open `https://oauth.example.org` in your browser: you should see Keycloak's
page without a certificate warning.

## 3. Get a Keycloak account

Log in to `https://oauth.example.org/admin/` as `admin` (the password is in
`/root/lab/lab-secrets/oauth/keycloak-admin-password`) and switch to realm
**example**:

1. Users > Add user: a username, e-mail verified. Then Credentials > Set
   password, not temporary.
2. Groups: join `k8s-admins` (cluster-admin on the clusters) and
   `argocd-admins` (Argo CD admin).

You should see the user with both groups under its Groups tab.

## 4. Log in to the cluster

Start the cluster if it is stopped (it normally starts with the host):

```sh
for v in $(virsh list --all --name | grep ^lab-); do virsh start $v; done
```

Then, as yourself:

```sh
KUBECONFIG=/root/lab/lab-cluster/kubeconfig-oidc kubectl get nodes
```

`kubectl` prints a URL and a code. Open the URL in your browser, enter the
code, log in with your new account. You should see the nine nodes of `lab`.

Now open `https://argocd.apps.lab.example.org` and choose "Log in via
Keycloak": you should see the Applications, all Synced. Then
`https://headlamp.apps.lab.example.org`: you see the cluster with your own
rights.

## What you did

You used the CA (`pki`), the identity provider (`oauth`) and DNS (the router)
the way every person and cluster on the site does, and logged in to a
cluster through them.

## Next steps

- The services and their addresses: [Site](../reference/site.md).
- Build another cluster: talos-install's tutorial,
  [Getting started](https://github.com/vincentbrobald/talos-install/blob/main/docs/tutorials/getting-started.md), with
  [this site's settings](../how-to/build-a-cluster-on-this-site.md).
- Change a service: [Change a service with Ansible](change-a-service.md).
- How the pieces fit: [The lab](../explanation/the-lab.md).
