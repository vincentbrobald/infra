# Troubleshoot

> How-to · [Documentation](../../README.md#documentation)

Find the cause of a problem with the shared services, DNS registration or CI.

## A service

| Symptom | Check |
|---|---|
| a URL doesn't answer | `virsh list --all` (the VM runs?), then on the VM `systemctl status caddy <service>` |
| certificate errors from a service | `pki` must be reachable: certificates last 24 h and renew over ACME; `curl --cacert /root/lab/infra/pki/root_ca.crt https://pki.example.org/health` |
| a playbook stops in preflight | a name already answers on the network, the bridge is missing, or image files belong to another VM: read the message |
| a playbook can't read a credential from Git | Forgejo is down: `gitops.yml` uses `~/.cache/infra-ansible/gitops` if it exists, or stops |
| Omni exits with "error listening on uapi socket: permission denied" | the SELinux rule `/etc/selinux/omni_wireguard.cil` isn't loaded: run `omni.yml` |
| Artifact Keeper answers 429 on login | its login rate limit: wait, and use an API token for automation |
| Artifact Keeper refuses an upstream or the OIDC issuer | its SSRF guard: add the host to `artifact_keeper_ssrf_allow_hosts` |
| npm can't authenticate to Artifact Keeper | npm matches tokens by URL: one `//artifacts.example.org/npm/<repo>/:_authToken` per repository |
| a test user added to `team-<team>` in Keycloak disappears | Crossplane owns the teams' memberships: test with a group of your own |
| `registry.example.org` stops resolving | a host entry for the registry's address must exist (role `harbor`); a second name for the same DHCP address replaces the lease's name |

## DNS registration

| Symptom | Cause / fix |
|---|---|
| `settings file ... not found` | pass `--config FILE` or set `OPNSENSE_DNS_CONFIG` |
| `the certificate of ... does not match tlsFingerprint` | OPNsense renewed its certificate: check the new fingerprint in the GUI (the message prints the command), update the settings |
| HTTP 401 | wrong key file, or it holds only `key=` without `secret=` |
| HTTP 403 | the API user lacks **Services: Dnsmasq DNS/DHCP: Settings** |
| HTML or "Request Denied" instead of JSON | `url` points at a reverse proxy: use the web GUI's port (here 8443) |
| `... already exists (not managed by this tool)` | made by hand: remove it in OPNsense, or `--adopt` |
| warning: the LAN resolver still answers the old address | its cache, cleared within the TTL (15 min); Dnsmasq already has the new state |

## CI

| Symptom | Check |
|---|---|
| no run after a push | Forgejo: repository Settings > Webhooks > the hook > Recent deliveries. "webhook can only call allowed HTTP servers": `ALLOWED_HOST_LIST` missing from `[webhook]` in `app.ini`, or Forgejo not restarted |
| delivery answered 4xx | `kubectl -n pipelines-as-code logs deploy/pipelines-as-code-controller`: signature mismatch (secret differs) or no `Repository` for the URL |
| run starts, no status in Forgejo | the watcher's logs; the account must be a write collaborator with the token scopes above |
| clone fails with a certificate error | the namespace lacks ConfigMap `site-root-ca` (trust-manager) |
| `scan` step fails | the table in the log: packages with a FIXED VERSION; update the base image or package, or drop what the image doesn't need |
| `push` step: 401/403 | Secret `registry-push` missing or stale, or the robot not ready (`kubectl -n <ns> get accounts.robot.harbor.m.crossplane.io`); a robot pushes to its own project only |
| `build` step: `RUN` fails with permission errors | kaniko runs as root in its container without privileges: no mounts, no user namespaces |

From the host:

```sh
kubectl -n <ns> get pipelineruns
kubectl -n <ns> logs -l tekton.dev/pipelineRun=<name> --all-containers --prefix
```

In a pull request, `/retest` runs again, `/cancel` stops.
