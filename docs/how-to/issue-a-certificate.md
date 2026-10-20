# Issue a certificate by hand

> How-to · [Documentation](../../README.md#documentation)

Get a certificate for a name in `example.org` without ACME. Prefer ACME
(`https://pki.example.org/acme/acme/directory`) wherever the client supports it:
certificates last 24 hours and ACME renews them.

1. On `pki`:

   ```sh
   ssh -i /root/lab/lab-secrets/pki/id_ed25519 almalinux@pki.example.org
   sudo STEPPATH=/etc/step-ca step ca certificate host.example.org host.crt host.key \
     --provisioner admin@example.org --provisioner-password-file /etc/step-ca/provisioner-password.txt
   ```

2. Check: `step certificate inspect host.crt --short` shows the name and the
   expiry.

Names outside `example.org` are refused: the intermediate's name constraint
doesn't allow them.
