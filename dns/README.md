# opnsense-dns.py

Registers DNS A records as Dnsmasq host entries on an OPNsense router, by
owner: `deploy-talos.py dns-records` prints a cluster's names, this tool
applies them and removes them again.

```sh
deploy-talos.py dns-records -f lab.yaml --domain example.org | opnsense-dns.py sync --dry-run
deploy-talos.py dns-records -f lab.yaml --domain example.org | opnsense-dns.py sync
opnsense-dns.py remove --owner deploy-talos.py:lab
```

Requirements: Python 3.9+ with PyYAML, OPNsense with the Dnsmasq service.
`opnsense-dns.yaml` next to the script holds the site's settings, made from
the template `opnsense-dns.example.yaml`.

| What | Where |
|---|---|
| set up a router | [docs/how-to/set-up-dns-registration.md](../docs/how-to/set-up-dns-registration.md) |
| register and remove names | [docs/how-to/register-dns-records.md](../docs/how-to/register-dns-records.md) |
| commands, records, settings, this site | [docs/reference/opnsense-dns.md](../docs/reference/opnsense-dns.md) |
| how ownership and checks work | [docs/explanation/dns-registration.md](../docs/explanation/dns-registration.md) |
| errors | [docs/how-to/troubleshoot.md](../docs/how-to/troubleshoot.md#dns-registration) |
