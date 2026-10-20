# PKI

> Explanation · [Documentation](../../README.md#documentation)

Why the site runs its own CA, and the choices that make it safe to trust.
The facts: [pki](../reference/vms/pki.md).

## An internal CA with ACME

Every service and every cluster gateway needs certificates for names that
exist only on the LAN, which public CAs can't issue for. step-ca issues them
over ACME, the protocol Caddy and cert-manager already speak, so no
certificate is ever made or renewed by hand.

## Short-lived certificates

Certificates last 24 hours. A leaked key is useless within a day, and nobody
has to revoke anything; the price is that every client must renew
automatically, and that `pki` must be reachable. ACME clients renew after
about two thirds of the lifetime.

## A name constraint on the intermediate

Trusting a CA normally means trusting it for every name. The intermediate
carries a critical X.509 name constraint, `permittedDNSDomains: example.org`:
clients enforce it, so even a certificate wrongly issued for another domain is
invalid. Importing the root into a browser or system trust store therefore
only affects `example.org` and its subdomains, at any depth. step-ca enforces
the same constraint when issuing.

## The root never changes by accident

The root certificate is pinned in this repository (`pki/root_ca.crt`).
`pki.yml` restores a lost CA from the newest backup rather than creating a new
one, and refuses a CA whose root differs from the pinned file: a rebuilt
`pki` VM is the same CA, and no trust store or cluster has to change. Moving
the site to a new CA is a deliberate act: replace the file, then every VM and
cluster.

## Trust on the hosts

Every infrastructure VM trusts the root (role `site_ca`). The hypervisor host
does not, deliberately: tools there are given the CA explicitly (`--cacert`,
`--cert-dir`).
