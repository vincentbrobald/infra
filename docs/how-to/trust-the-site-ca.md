# Trust the site CA

> How-to · [Documentation](../../README.md#documentation)

Make a machine or a tool accept the site's certificates. The root:
`/root/lab/infra/pki/root_ca.crt` (public). Why trusting it is limited to the
site's domain: [PKI](../explanation/pki.md#a-name-constraint-on-the-intermediate).

| Where | How |
|---|---|
| Fedora, RHEL, AlmaLinux | `sudo cp root_ca.crt /etc/pki/ca-trust/source/anchors/site-root-ca.crt && sudo update-ca-trust` |
| a browser | import `root_ca.crt` as a certificate authority (Settings > Certificates) |
| with `step` | `step ca bootstrap --ca-url https://pki.example.org --fingerprint <root fingerprint>` (`step certificate fingerprint root_ca.crt`) |
| `curl` on the host | `--cacert /root/lab/infra/pki/root_ca.crt` |
| `podman` on the host | `--cert-dir <dir>` with the root as `<dir>/ca.crt` |
| Go programs (`omnictl`, ...) | `SSL_CERT_FILE` = the system bundle plus `root_ca.crt` in one file |
| an infrastructure VM | nothing: role `site_ca` does it |
| a cluster workload | mount ConfigMap `site-root-ca` (gitops: [Site CA](https://github.com/vincentbrobald/gitops/blob/main/docs/reference/site-ca.md#using-it-in-a-workload)) |

Check: `curl https://oauth.example.org` (without `--cacert` on a machine that
trusts it) answers without a certificate error.
