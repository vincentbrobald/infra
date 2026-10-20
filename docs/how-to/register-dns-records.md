# Register DNS records

> How-to · [Documentation](../../README.md#documentation)

Put a cluster's names, or names of your own, into the router's DNS, and take
them out again. The tool: [opnsense-dns.py](../reference/opnsense-dns.md).
How ownership works: [DNS registration](../explanation/dns-registration.md).

## A cluster's names

Register after `create`: the `*.apps` address is the ingress gateway's, read
from the running cluster.

1. See what would change:

   ```sh
   deploy-talos.py dns-records -f /root/lab/lab.yaml --domain example.org | /root/lab/infra/dns/opnsense-dns.py sync --dry-run
   ```

2. Apply:

   ```sh
   deploy-talos.py dns-records -f /root/lab/lab.yaml --domain example.org | /root/lab/infra/dns/opnsense-dns.py sync
   ```

3. Check:

   ```sh
   getent hosts api.lab.example.org
   /root/lab/infra/dns/opnsense-dns.py list
   ```

   ```
   NAME                          ADDRESS        OWNER
   *.apps.lab.example.org        192.0.2.204  deploy-talos.py:lab
   api.lab.example.org           192.0.2.200  deploy-talos.py:lab
   ```

The LAN's resolver may answer an older address, or "no such name", for up to
15 minutes (its cache); Dnsmasq itself has the new state at once.

## After destroying a cluster

```sh
/root/lab/infra/dns/opnsense-dns.py remove --owner deploy-talos.py:lab
```

## Names of your own

Write the records with an owner name of your own, so `sync` and `remove` only
touch your entries:

```sh
cat > storage.json <<'JSON'
{"owner": "manual:storage",
 "records": [{"name": "minio.example.org", "type": "A", "address": "192.0.2.20"},
             {"name": "*.s3.example.org",  "type": "A", "address": "192.0.2.20"}]}
JSON
/root/lab/infra/dns/opnsense-dns.py sync -i storage.json --dry-run
/root/lab/infra/dns/opnsense-dns.py sync -i storage.json
```

Later: `opnsense-dns.py remove --owner manual:storage`.

For an address a DHCP client holds (a VM named by its lease), also register
the VM's own name in the same records: a host entry for the address replaces
the lease's name.

## A name that exists already

`sync` refuses a name made by hand in OPNsense. Remove it there, or take it
over with `--adopt`.
