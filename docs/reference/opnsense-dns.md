# opnsense-dns.py

> Reference · [Documentation](../../README.md#documentation)

Registers DNS A records as Dnsmasq host entries on an OPNsense router. Set it
up: [Set up DNS registration](../how-to/set-up-dns-registration.md). Use it:
[Register DNS records](../how-to/register-dns-records.md). How it works:
[DNS registration](../explanation/dns-registration.md).

## Commands

| Command | Does |
|---|---|
| `opnsense-dns.py sync [-i FILE] [--dry-run] [--adopt]` | makes the owner's entries match the records JSON (stdin or `-i`) |
| `opnsense-dns.py list [--all]` | managed entries; `--all`: every host entry |
| `opnsense-dns.py remove --owner OWNER` | deletes the owner's entries |
| `--config FILE` | the settings file (any command) |

Requirements: Python 3.9+ with PyYAML; OPNsense with the Dnsmasq service.

## Records JSON

```json
{"owner": "deploy-talos.py:lab",
 "records": [{"name": "api.lab.example.org", "type": "A", "address": "192.0.2.200"},
             {"name": "*.apps.lab.example.org", "type": "A", "address": "192.0.2.204"}]}
```

| Field | Value |
|---|---|
| `owner` | `deploy-talos.py:<cluster>`, `infra-ansible:<vm>`, or a name of your own (`manual:storage`) |
| `records[].type` | `A` only |
| `records[].name` | a name; `*.<domain>` covers the domain and everything below |

## Settings file

Read from `--config FILE`, else `OPNSENSE_DNS_CONFIG`, else
`opnsense-dns.yaml` next to the script. YAML, no secrets; relative paths are
relative to the file.

| Key | Default | Meaning |
|---|---|---|
| `url` | required | API base URL without path, e.g. `https://192.0.2.1:443`: the web GUI's port |
| `keyFile` | required | OPNsense `apikey.txt` (`key=...`, `secret=...`), mode 600 |
| `tlsFingerprint` | — | SHA-256 fingerprint of the API's self-signed certificate (pinned) |
| `caFile` | — | instead of `tlsFingerprint`: CA of a CA-signed certificate |
| `dnsServer` | `null` | resolver the LAN uses, checked after each change; `null` skips checks |
| `dnsPort` | `53` | its port |
| `dnsmasqPort` | `null` | Dnsmasq's own port, when another resolver answers on `dnsPort` |

Exactly one of `tlsFingerprint` and `caFile`. The API user needs one
privilege: **Services: Dnsmasq DNS/DHCP: Settings**.

## This site

| Item | Value |
|---|---|
| Settings | `dns/opnsense-dns.yaml` (the default file; `opnsense-dns.example.yaml` is the template) |
| API | `https://192.0.2.1:8443` (port 443 is an nginx proxy that answers "Request Denied" to API calls) |
| Certificate | self-signed `OPNsense.example.org`, pinned; valid until **2026-11-12**, then update `tlsFingerprint` |
| Key | `/root/lab/opnsense_key` |
| DNS chain | Unbound on :53 forwards `example.org` to Dnsmasq on `127.0.0.1:53053`; Dnsmasq's local TTL 900 s |
| Owners in use | `deploy-talos.py:lab` (api, `*.apps` of `lab.example.org`), `infra-ansible:harbor`, `infra-ansible:artifact_keeper`, `infra-ansible:<vm>` (static VMs) |
| Hand-made entries | `unify`, `nas`, `forge`, ...: never touched |
