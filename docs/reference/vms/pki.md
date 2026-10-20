# pki: step-ca

> Reference · [Documentation](../../../README.md#documentation)

The site's certificate authority. Why it is set up this way:
[PKI](../../explanation/pki.md).

| | |
|---|---|
| VM | `pki`, 1 vCPU, 1.5 GiB, 10 GB, AlmaLinux 10; MAC `52:54:00:00:00:01` |
| Address | 192.0.2.162 (DHCP, name registered by the router) |
| Runs | step-ca 0.30.2 on :443 (systemd unit `step-ca`, user `step`, data in `/etc/step-ca`) |
| Playbook | `ansible/pki.yml` (role `step_ca`) |
| SSH | `ssh -i /root/lab/lab-secrets/pki/id_ed25519 almalinux@pki.example.org` |

## The CA

| Item | Value |
|---|---|
| Name | `example.org CA` |
| URL | `https://pki.example.org` |
| Root certificate | `/root/lab/infra/pki/root_ca.crt` (public); fingerprint: `step certificate fingerprint pki/root_ca.crt` |
| Validity | root and intermediate until 2036 |
| Name constraint | intermediate: critical `permittedDNSDomains: example.org` (the domain and its subdomains at any depth) |
| Wildcards | not issued by default |
| Certificate lifetime | 24 h by default |
| Key protection | CA keys encrypted with `/etc/step-ca/password.txt` |

## Provisioners

| Provisioner | Type | Use |
|---|---|---|
| `acme` | ACME | automatic certificates (Caddy, cert-manager, certbot): `https://pki.example.org/acme/acme/directory` |
| `admin@example.org` | JWK | manual issuance; password in `/etc/step-ca/provisioner-password.txt` on the VM |

## What the playbook does

| Situation | Action |
|---|---|
| VM without a CA, a backup exists | restores the newest `step-ca-*.tar.gz` from `/root/lab/lab-secrets/pki/backup/` |
| VM without a CA, no backup | creates a new CA |
| root on the VM differs from `pki/root_ca.crt` | stops |
| after a creation, restore or re-issued intermediate | writes a new backup |

## Files

| `/root/lab/lab-secrets/` | Contents |
|---|---|
| `pki/id_ed25519` (+ `.pub`) | SSH key of the VM |
| `pki/backup/` | CA backups: `/etc/step-ca` with keys, passwords, database (root-only) |

The previous intermediate is kept on the VM as
`/etc/step-ca/certs/intermediate_ca.crt.pre-nameconstraints`.
