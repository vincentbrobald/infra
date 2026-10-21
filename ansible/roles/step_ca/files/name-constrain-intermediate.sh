#!/usr/bin/env bash
# Re-issue the intermediate CA with an X.509 name constraint for $1 (the
# domain and subdomains at any depth; every TLS client enforces it). Same
# root, same key: the root stays and existing certificates stay valid.
# (step-ca's own policy rules match a fixed number of labels, so '*.domain'
# would allow only one level.)
#
# Usage: name-constrain-intermediate DOMAIN (the step_ca role installs it in
# /usr/local/sbin and runs it as root). Environment: STEPPATH, step-ca's
# directory (default /etc/step-ca). Needs step, openssl and jq. Idempotent:
# exits 0 at once when the intermediate already carries the constraint.
# Otherwise it replaces certs/intermediate_ca.crt (the previous one kept as
# intermediate_ca.crt.pre-nameconstraints) and prints "reissued"; step-ca
# must be restarted to use it.
# -e/-u/pipefail: any failing command aborts the script.
set -euo pipefail
DOMAIN=$1
STEPPATH=${STEPPATH:-/etc/step-ca}
INT=$STEPPATH/certs/intermediate_ca.crt
# constrained CERT succeeds when a line of CERT's name constraints is exactly
# "DNS:$DOMAIN" after indentation, compared literally.
constrained() { openssl x509 -in "$1" -noout -ext nameConstraints 2>/dev/null | sed 's/^[[:space:]]*//' | grep -qxF "DNS:$DOMAIN"; }
constrained "$INT" && exit 0
# Template of the new intermediate: the current subject, CA usages, no
# sub-CAs (maxPathLen 0) and a critical constraint permitting DOMAIN and its
# subdomains. It is signed by the root with the current intermediate key and
# keeps the current expiry; step's own output is discarded.
info=$(step certificate inspect "$INT" --format json)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
jq --arg d "$DOMAIN" '{subject: {commonName: .subject.common_name[0], organization: .subject.organization},
        keyUsage: ["certSign", "crlSign"], basicConstraints: {isCA: true, maxPathLen: 0},
        nameConstraints: {critical: true, permittedDNSDomains: [$d]}}' <<<"$info" > "$tmp/intermediate.tpl"
step certificate create "$(jq -r '.subject.common_name[0]' <<<"$info")" "$tmp/intermediate.crt" \
    --template "$tmp/intermediate.tpl" \
    --ca "$STEPPATH/certs/root_ca.crt" --ca-key "$STEPPATH/secrets/root_ca_key" \
    --ca-password-file "$STEPPATH/password.txt" \
    --key "$STEPPATH/secrets/intermediate_ca_key" --password-file "$STEPPATH/password.txt" \
    --not-after "$(jq -r '.validity.end' <<<"$info")" --force >/dev/null 2>&1
# Before replacing anything: same key as the current intermediate, signed by
# the root, and the constraint present.
[[ $(openssl x509 -in "$tmp/intermediate.crt" -noout -pubkey) == $(openssl x509 -in "$INT" -noout -pubkey) ]] \
    || { echo "new intermediate has a different key" >&2; exit 1; }
openssl verify -CAfile "$STEPPATH/certs/root_ca.crt" "$tmp/intermediate.crt" >/dev/null
constrained "$tmp/intermediate.crt" || { echo "new intermediate lacks the name constraint" >&2; exit 1; }
cp -p "$INT" "$INT.pre-nameconstraints"
install -m 600 -o step -g step "$tmp/intermediate.crt" "$INT"
echo reissued
