# DNS registration

> Explanation · [Documentation](../../README.md#documentation)

How `opnsense-dns.py` keeps cluster names in the router's DNS without
touching anything else. The tool: [opnsense-dns.py](../reference/opnsense-dns.md).

## Records as data, applied by owner

deploy-talos.py knows which names a cluster needs (`api.<cluster>`,
`*.apps.<cluster>`) and prints them as a records JSON with an **owner**
(`deploy-talos.py:<cluster>`). `sync` makes that owner's entries in OPNsense
match the list exactly: it adds, updates and deletes, but only entries tagged
with that owner (description `managed-by:<owner>`). Entries made by hand, or
by another owner, are never changed; a name clash with one is an error, unless
`--adopt` takes over an untagged entry. Removing a cluster's names is then one
command for its owner, and can't take anything else with it.

Ansible uses the same tool and the same rule for the VMs it gives a host entry
(`infra-ansible:<vm>`).

## How names map to Dnsmasq

`api.lab.example.org` becomes host `api` in domain `lab.example.org`;
`*.apps.lab.example.org` becomes host `*` in domain `apps.lab.example.org`,
which OPNsense writes as `address=/apps.lab.example.org/<ip>`: the name and
everything below it. One wildcard serves every application on the cluster's
gateway.

## Checking that DNS really answers

After a change the tool asks Dnsmasq itself for the new state and fails if it
doesn't answer it. The LAN's resolver (Unbound, forwarding to Dnsmasq) is
checked too, but only warned about: it may serve a cached older answer,
including a cached "no such name", until Dnsmasq's local TTL (900 s) runs out,
and OPNsense has no API to flush single names. Registering names before
anything looks them up avoids that.

Applying the configuration makes OPNsense reload Dnsmasq, which pauses its
DHCP and DNS for about a second.

## Host entries and DHCP leases

A host entry for an address a DHCP client holds takes over the name Dnsmasq
gives that lease. Adding an alias for a VM known by its lease name makes the
lease name disappear, so the VM's own name must be a host entry too, in the
same records.

## Pinned, not trusted

OPNsense's API has a self-signed certificate. The tool pins its fingerprint
rather than trusting it (or takes a CA file for a CA-signed one), and the API
key lives in a file outside any Git tree; the settings file holds no secret.
