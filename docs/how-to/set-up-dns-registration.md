# Set up DNS registration on OPNsense

> How-to · [Documentation](../../README.md#documentation)

Prepare an OPNsense router and a settings file so that `opnsense-dns.py` can
register names. This site is set up already ([its settings](../reference/opnsense-dns.md#this-site));
these steps are for another router, or to redo it. The examples use
`192.0.2.1` for the router and `example.org` for the domain.

1. **Enable Dnsmasq** (Services > Dnsmasq DNS & DHCP), and make sure the LAN's
   resolver asks it for your domain. When Unbound answers on port 53, run
   Dnsmasq on another port (e.g. 53053) and add a query forward for the domain
   to `127.0.0.1:53053` (Services > Unbound DNS > Query Forwarding).
2. **Create an API user** (System > Access > Users) without login shell, with
   one privilege: **Services: Dnsmasq DNS/DHCP: Settings**.
3. **Create its API key** (the user's "API keys", "+"). Store the downloaded
   `apikey.txt` outside any Git tree, readable only by you:

   ```sh
   install -m 600 apikey.txt ~/secrets/opnsense-api-key.txt
   ```

4. **Pin the web GUI's certificate.** Find the GUI's port (System > Settings >
   Administration), then:

   ```sh
   echo | openssl s_client -connect 192.0.2.1:443 2>/dev/null | openssl x509 -noout -fingerprint -sha256 -subject -enddate
   ```

   Compare the fingerprint with the one in the GUI (System > Trust >
   Certificates) before trusting it.
5. **Write the settings file** from `dns/opnsense-dns.example.yaml`:

   ```yaml
   url: https://192.0.2.1:443           # the web GUI's port, not a reverse proxy
   keyFile: ~/secrets/opnsense-api-key.txt
   tlsFingerprint: AB:CD:...
   dnsServer: 192.0.2.1
   dnsmasqPort: 53053                   # only when Dnsmasq has its own port
   ```

6. **Point the tool at it** (or pass `--config FILE` each time) and test:

   ```sh
   export OPNSENSE_DNS_CONFIG=~/site/opnsense-dns.yaml
   opnsense-dns.py list --all
   ```

   You should see the router's existing host entries.

When OPNsense renews its web certificate, repeat step 4 and update
`tlsFingerprint`. This site's certificate is valid until 2026-11-12.

Next: [Register DNS records](register-dns-records.md).
