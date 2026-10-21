#!/usr/bin/env python3
"""Takes the JSON printed by `deploy-talos.py dns-records` (or any tool that
prints the same):

    {"owner": "deploy-talos.py:lab",
     "records": [{"name": "api.lab.example.com", "type": "A", "address": "192.0.2.200"},
                 {"name": "*.apps.lab.example.com", "type": "A", "address": "192.0.2.204"}]}

and makes OPNsense's Dnsmasq host entries match it: missing entries are
added, changed addresses updated, entries of the same owner that are no longer
wanted removed. Every entry the tool creates carries "managed-by:<owner>" in
its description; entries without that tag (or with another owner's tag) are
never changed or deleted.

A record a.b.c becomes host "a", domain "b.c"; a wildcard *.apps.b.c becomes
host "*", domain "apps.b.c", which OPNsense renders as dnsmasq
address=/apps.b.c/<ip> (the domain and every name below it).

Settings come from a YAML file: --config FILE, else $OPNSENSE_DNS_CONFIG, else
opnsense-dns.yaml next to this script (see opnsense-dns.example.yaml). They
give the API URL, the key file (OPNsense's apikey.txt: key=... / secret=...),
the pinned SHA-256 fingerprint of the API's (self-signed) certificate or a CA
file, and the DNS server used to verify the result. Relative paths in it are
relative to the settings file.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.client
import json
import os
import random
import re
import socket
import ssl
import struct
import sys
import time
from pathlib import Path

import yaml

PROG = "opnsense-dns.py"
# Prefix of the description of every entry this tool manages; the owner follows it.
TAG = "managed-by:"
CONFIG_ENV = "OPNSENSE_DNS_CONFIG"
DEFAULT_CONFIG = Path(__file__).resolve().with_name("opnsense-dns.yaml")


def default_config() -> Path:
    """The settings file when --config is not given: $OPNSENSE_DNS_CONFIG, else opnsense-dns.yaml here."""
    env = os.environ.get(CONFIG_ENV, "")
    return Path(env).expanduser() if env else DEFAULT_CONFIG


class DnsError(Exception):
    """An error to report as "ERROR: ..." with exit status 1."""
    pass


def log(msg: str) -> None:
    """Print a progress line ("==> msg") on stdout."""
    print(f"==> {msg}", flush=True)


def load_settings(path: Path) -> dict:
    """Read and check the settings file path; return them normalised.

    The URL loses a trailing slash, the fingerprint its colons and case,
    keyFile and caFile become paths (relative ones to the file's directory);
    dnsServer and dnsmasqPort default to None, dnsPort to 53. Raises DnsError
    for a missing or unreadable file, an unknown key, a missing url or keyFile,
    a URL with a path, or not exactly one of tlsFingerprint and caFile.
    """
    try:
        s = yaml.safe_load(path.read_text()) or {}
    except FileNotFoundError:
        raise DnsError(f"settings file {path} not found: pass --config FILE or set {CONFIG_ENV} "
                       f"(start from {DEFAULT_CONFIG.with_name('opnsense-dns.example.yaml')})") from None
    except OSError as e:
        raise DnsError(f"cannot read {path}: {e.strerror}") from e
    known = {"url", "keyFile", "tlsFingerprint", "caFile", "dnsServer", "dnsPort", "dnsmasqPort"}
    unknown = set(s) - known
    if unknown:
        raise DnsError(f"{path}: unknown key(s): {', '.join(sorted(unknown))}")
    for key in ("url", "keyFile"):
        if not s.get(key):
            raise DnsError(f"{path}: '{key}' is required")
    if not re.fullmatch(r"https://[^/]+", s["url"].rstrip("/")):
        raise DnsError(f"{path}: 'url' must look like https://192.0.2.1:8443 (no path)")
    if bool(s.get("tlsFingerprint")) == bool(s.get("caFile")):
        raise DnsError(f"{path}: set exactly one of 'tlsFingerprint' (pinned self-signed certificate) or 'caFile'")
    if s.get("tlsFingerprint"):
        fp = s["tlsFingerprint"].replace(":", "").lower()
        if not re.fullmatch(r"[0-9a-f]{64}", fp):
            raise DnsError(f"{path}: 'tlsFingerprint' must be a SHA-256 fingerprint (64 hex digits, colons allowed)")
        s["tlsFingerprint"] = fp
    s["url"] = s["url"].rstrip("/")
    s.setdefault("dnsServer", None)
    s.setdefault("dnsPort", 53)
    s.setdefault("dnsmasqPort", None)
    base = path.resolve().parent
    for key in ("keyFile", "caFile"):
        if s.get(key):
            p = Path(s[key]).expanduser()
            s[key] = p if p.is_absolute() else base / p
    return s


def read_api_key(path: Path) -> tuple[str, str]:
    """Return (key, secret) from OPNsense's apikey.txt (key=... / secret=...), or two lines: key, secret.

    Raises DnsError if the file can't be read or holds neither form; warns on
    stderr when group or others have any permission on it.
    """
    try:
        lines = [l.strip() for l in path.read_text().splitlines() if l.strip()]
    except OSError as e:
        raise DnsError(f"cannot read API key file {path}: {e.strerror}") from e
    kv = {}
    for line in lines:
        m = re.fullmatch(r"(key|secret)\s*=\s*(\S+)", line)
        if m:
            kv[m.group(1)] = m.group(2)
    if not kv and len(lines) == 2:
        kv = {"key": lines[0], "secret": lines[1]}
    if set(kv) != {"key", "secret"}:
        raise DnsError(f"{path}: expected 'key=...' and 'secret=...' lines (OPNsense apikey.txt)")
    if path.stat().st_mode & 0o077:
        print(f"WARNING: {path} is readable by others; chmod 600 it", file=sys.stderr)
    return kv["key"], kv["secret"]


class OPNsense:
    """OPNsense's API for Dnsmasq host entries, with the API key of the settings.

    Each call opens its own HTTPS connection. Methods raise DnsError on any
    failure.
    """

    def __init__(self, s: dict):
        """Read the API key and prepare TLS from settings s (load_settings()): verification
        against caFile, or no CA verification and the certificate's pinned fingerprint."""
        self.url = s["url"]
        key, secret = read_api_key(s["keyFile"])
        self.auth = "Basic " + base64.b64encode(f"{key}:{secret}".encode()).decode()
        if s.get("caFile"):
            self.ctx = ssl.create_default_context(cafile=str(s["caFile"]))
            self.pin = None
        else:
            self.ctx = ssl.create_default_context()
            self.ctx.check_hostname = False
            self.ctx.verify_mode = ssl.CERT_NONE
            self.pin = s["tlsFingerprint"]

    def connect(self) -> http.client.HTTPSConnection:
        """Open a connection to the API; with a pinned fingerprint, check the certificate first.

        Raises DnsError (with the command to read the new fingerprint) on a
        mismatch, OSError when the host can't be reached.
        """
        host, _, port = self.url.removeprefix("https://").partition(":")
        conn = http.client.HTTPSConnection(host, int(port or 443), timeout=30, context=self.ctx)
        conn.connect()
        if self.pin is None:
            return conn
        # The pinned certificate is checked on the connection that then carries
        # the API key, before anything is sent.
        got = hashlib.sha256(conn.sock.getpeercert(binary_form=True)).hexdigest()
        if got != self.pin:
            conn.close()
            pretty = ":".join(got[i:i + 2] for i in range(0, 64, 2)).upper()
            raise DnsError(f"the certificate of {self.url} does not match tlsFingerprint (it has {pretty}). "
                           "If OPNsense renewed its web certificate, check it and update opnsense-dns.yaml:\n"
                           f"  echo | openssl s_client -connect {host}:{port or 443} 2>/dev/null | "
                           "openssl x509 -noout -fingerprint -sha256")
        return conn

    def call(self, method: str, path: str, body: dict | None = None) -> dict:
        """Send body as JSON (a POST without one sends {}) and return the decoded answer.

        Raises DnsError when OPNsense can't be reached, answers HTTP 400 or more
        (with a hint for 401 and 403), or doesn't answer JSON.
        """
        data = json.dumps(body).encode() if body is not None else (b"{}" if method == "POST" else None)
        headers = {"Authorization": self.auth, "Content-Type": "application/json", "User-Agent": PROG}
        try:
            conn = self.connect()
        except OSError as e:
            raise DnsError(f"cannot reach OPNsense at {self.url}: {e}") from e
        try:
            conn.request(method, path, body=data, headers=headers)
            r = conn.getresponse()
            status, text = r.status, r.read()
        except OSError as e:
            raise DnsError(f"cannot reach OPNsense at {self.url}: {e}") from e
        finally:
            conn.close()
        if status >= 400:
            hint = {401: " (wrong key/secret)", 403: " (the key's user lacks the Dnsmasq privilege)"}.get(status, "")
            raise DnsError(f"OPNsense {method} {path}: HTTP {status}{hint}")
        try:
            return json.loads(text or b"{}")
        except ValueError:
            raise DnsError(f"OPNsense {method} {path}: not a JSON answer (wrong URL or port?)") from None

    def hosts(self) -> list[dict]:
        """All of Dnsmasq's host entries (rowCount -1: no paging), as the API's rows."""
        d = self.call("POST", "/api/dnsmasq/settings/search_host",
                      {"current": 1, "rowCount": -1, "searchPhrase": ""})
        return d.get("rows", [])

    def save(self, path: str, entry: dict) -> None:
        """POST a host entry to the add or set endpoint path; DnsError unless OPNsense saved it."""
        d = self.call("POST", path, {"host": entry})
        if d.get("result") != "saved":
            raise DnsError(f"OPNsense rejected {entry.get('host')}.{entry.get('domain')}: "
                           f"{d.get('validations') or d}")

    def add(self, entry: dict) -> None:
        """Add a host entry (not applied until apply())."""
        self.save("/api/dnsmasq/settings/add_host", entry)

    def update(self, uuid: str, entry: dict) -> None:
        """Replace host entry uuid with entry (not applied until apply())."""
        self.save(f"/api/dnsmasq/settings/set_host/{uuid}", entry)

    def delete(self, uuid: str) -> None:
        """Delete host entry uuid (not applied until apply()); DnsError unless OPNsense deleted it."""
        d = self.call("POST", f"/api/dnsmasq/settings/del_host/{uuid}")
        if d.get("result") != "deleted":
            raise DnsError(f"OPNsense did not delete host entry {uuid}: {d}")

    def apply(self) -> None:
        """Reconfigure Dnsmasq so that the saved entries take effect; DnsError unless it reports ok."""
        d = self.call("POST", "/api/dnsmasq/service/reconfigure")
        if d.get("status", "").strip().lower() != "ok":
            raise DnsError(f"OPNsense could not apply the Dnsmasq configuration: {d}")


# One lower-case DNS label: letters, digits and inner hyphens, 1 to 63 characters.
LABEL = r"[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?"


def split_name(name: str) -> tuple[str, str]:
    """Split a record name, lower-cased and without a final dot, into (host, domain) at the first dot.

    host is a label or "*"; domain one or more labels. Raises DnsError otherwise.
    """
    name = name.lower().rstrip(".")
    host, _, domain = name.partition(".")
    if not domain or not re.fullmatch(rf"({LABEL}\.)*{LABEL}", domain) or \
            not (host == "*" or re.fullmatch(LABEL, host)):
        raise DnsError(f"invalid record name '{name}'")
    return host, domain


def load_records(source: str) -> tuple[str, list[dict]]:
    """Read the records JSON from file source ("-": standard input) and return (owner, entries).

    entries are {"host", "domain", "ip"} dicts, one per distinct name (a name
    given twice with the same address counts once). Raises DnsError for
    unreadable input, invalid JSON, an invalid owner, a record that isn't type
    A with an IPv4 address, or a name given twice with different addresses.
    """
    try:
        text = sys.stdin.read() if source == "-" else Path(source).read_text()
    except OSError as e:
        raise DnsError(f"cannot read {source}: {e.strerror}") from e
    try:
        doc = json.loads(text)
    except ValueError:
        raise DnsError(f"{'standard input' if source == '-' else source} is not JSON "
                       "(expected the output of 'deploy-*.py dns-records')") from None
    owner = doc.get("owner") if isinstance(doc, dict) else None
    records = doc.get("records") if isinstance(doc, dict) else None
    if not isinstance(owner, str) or not re.fullmatch(r"[A-Za-z0-9._:/-]{1,100}", owner):
        raise DnsError("records: 'owner' missing or invalid")
    if not isinstance(records, list):
        raise DnsError("records: 'records' must be a list")
    seen = {}
    for r in records:
        if not isinstance(r, dict) or r.get("type") != "A":
            raise DnsError(f"unsupported record {r} (only type A)")
        try:
            socket.inet_aton(r.get("address", ""))
        except OSError:
            raise DnsError(f"record {r.get('name')}: '{r.get('address')}' is not an IPv4 address") from None
        key = split_name(r["name"])
        if key in seen and seen[key] != r["address"]:
            raise DnsError(f"record {r['name']} given twice with different addresses")
        seen[key] = r["address"]
    return owner, [{"host": h, "domain": d, "ip": ip} for (h, d), ip in seen.items()]


def fqdn(e: dict) -> str:
    """The full name host.domain of an entry or API row."""
    return f"{e['host']}.{e['domain']}"


def owner_of(row: dict) -> str | None:
    """The owner tagged in a row's description, None for an entry this tool doesn't manage."""
    descr = row.get("descr") or ""
    return descr[len(TAG):] if descr.startswith(TAG) else None


def row_ip(row: dict) -> str:
    """A row's address as text; the API may give a list, which is joined with commas."""
    ip = row.get("ip", "")
    return ",".join(ip) if isinstance(ip, list) else str(ip)


def query_a(name: str, server: str, port: int = 53) -> list[str] | None:
    """Ask server:port over UDP for the A records of name; return their addresses.

    [] means an answer without A records (e.g. NXDOMAIN); None no answer within
    3 seconds, a network error, an answer to another query, or one that can't be
    parsed (truncated or malformed). A minimal resolver: no retries, no TCP
    fallback.
    """
    # Header: random id, flags 0x0100 (recursion desired), one question. The
    # question: the name as length-prefixed labels, a 0 byte, type A, class IN.
    tid = random.randint(0, 65535)
    pkt = struct.pack(">HHHHHH", tid, 0x0100, 1, 0, 0, 0)
    pkt += b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\0" + struct.pack(">HH", 1, 1)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(3)
        try:
            s.sendto(pkt, (server, port))
            d, _ = s.recvfrom(4096)
        except OSError:
            return None
    if len(d) < 12 or struct.unpack(">H", d[:2])[0] != tid:
        return None
    try:
        return parse_a(d)
    except (IndexError, struct.error):
        return None


def skip_name(d: bytes, i: int) -> int:
    """Return the offset just past the domain name that starts at offset i of message d.

    A name is length-prefixed labels ending either in a 0 byte or in a 2-byte
    compression pointer (two top bits set, RFC 1035 4.1.4), which ends it too.
    Raises IndexError when d ends inside the name.
    """
    while True:
        n = d[i]
        if n & 0xC0 == 0xC0:
            return i + 2
        if n == 0:
            return i + 1
        i += n + 1


def parse_a(d: bytes) -> list[str]:
    """Return the addresses of the A records in the answer section of DNS response d.

    Skips the echoed question, then reads each answer: its name, type, class,
    TTL and data length (10 bytes), then the data; only type A (1) data of 4
    bytes is kept, CNAMEs and others are skipped. Raises IndexError or
    struct.error on a truncated or malformed message.
    """
    qdcount, ancount = struct.unpack(">HH", d[4:8])
    i = 12
    for _ in range(qdcount):
        i = skip_name(d, i) + 4  # type and class
    out = []
    for _ in range(ancount):
        i = skip_name(d, i)
        typ, _, _, length = struct.unpack(">HHIH", d[i:i + 10])
        i += 10
        if i + length > len(d):
            raise IndexError("answer data past the end of the message")
        if typ == 1 and length == 4:
            out.append(socket.inet_ntoa(d[i:i + 4]))
        i += length
    return out


def resolves(name: str, ip: str | None, server: str, port: int) -> bool:
    """Whether name resolves through server:port to exactly ip (None: to no address).

    A wildcard is checked through a random name below it ("*" -> probe-<n>).
    """
    probe = name.replace("*", f"probe-{random.randint(0, 10**6)}")
    got = query_a(probe, server, port)
    return got == ([ip] if ip else [])


def verify(records: list[dict], settings: dict, removed: list[str] = (), timeout: int = 60) -> None:
    """Check through dnsServer that the records resolve and the removed names don't.

    Dnsmasq itself (dnsmasqPort) must answer
    exactly the new state: an error otherwise. The LAN resolver (dnsPort, e.g.
    Unbound forwarding to Dnsmasq) is checked too, but it may serve an older
    answer from its cache until the TTL runs out: only a warning. Without a
    dnsmasqPort, dnsPort is the one that must answer (an error otherwise).
    Each name is retried every 3 seconds, for timeout seconds where an error
    is due, 10 seconds where only a warning. Without dnsServer nothing is checked.
    """
    server = settings.get("dnsServer")
    if not server:
        return
    want = {fqdn(e): e["ip"] for e in records} | {n: None for n in removed}
    checks = [(settings["dnsmasqPort"], True)] if settings.get("dnsmasqPort") else []
    checks.append((settings["dnsPort"], not settings.get("dnsmasqPort")))
    for port, fatal in checks:
        log(f"Checking the names through {server}:{port}{'' if fatal else ' (LAN resolver)'}")
        deadline = time.time() + (timeout if fatal else 10)
        pending = dict(want)
        while pending and time.time() < deadline:
            for name, ip in list(pending.items()):
                if resolves(name, ip, server, port):
                    print(f"      {name:<45} {'A ' + ip if ip else 'gone'}  ok")
                    del pending[name]
            if pending:
                time.sleep(3)
        if not pending:
            continue
        bad = ", ".join(f"{n} (want {ip or 'no answer'}, got "
                        f"{query_a(n.replace('*', 'probe'), server, port) or 'no answer'})" for n, ip in pending.items())
        if fatal:
            raise DnsError(f"not resolving as expected through {server}:{port} after {timeout}s: {bad}")
        print(f"WARNING: {server}:{port} still answers from its cache: {bad}. This clears when the cached "
              "answer expires (Dnsmasq's local TTL, 15 minutes by default on OPNsense).", file=sys.stderr)


def cmd_list(api: OPNsense, args) -> None:
    """The list command: print a table of the managed entries (--owner: one owner's; --all: every entry)."""
    rows = api.hosts()
    shown = [r for r in rows if args.all or (owner_of(r) and (not args.owner or owner_of(r) == args.owner))]
    if not shown:
        print("No matching host entries." if not args.all else "No host entries.")
        return
    rows_out = [("NAME", "ADDRESS", "OWNER")]
    for r in sorted(shown, key=lambda r: (owner_of(r) or "~", r["domain"], r["host"])):
        rows_out.append((f"{r['host']}.{r['domain']}", row_ip(r), owner_of(r) or "(not managed)"))
    widths = [max(len(x[i]) for x in rows_out) for i in range(3)]
    for x in rows_out:
        print("  ".join(c.ljust(widths[i]) for i, c in enumerate(x)).rstrip())


def plan_changes(rows: list[dict], owner: str, wanted: list[dict], adopt: bool):
    """Compare the API's rows with the wanted entries of owner; return (adds, updates, deletes, conflicts).

    updates are (row, wanted entry) pairs; deletes are rows; conflicts are
    messages. A name held by another owner, or by an unmanaged entry without
    adopt, is a conflict. With adopt, unmanaged entries of a wanted name are
    taken over (tagged with owner). Names are matched case-insensitively.
    """
    by_key: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        by_key.setdefault((r["host"].lower(), r["domain"].lower()), []).append(r)
    adds, updates, conflicts = [], [], []
    keep = set()
    for e in wanted:
        existing = by_key.get((e["host"], e["domain"]), [])
        mine = [r for r in existing if owner_of(r) == owner]
        others = [r for r in existing if owner_of(r) != owner]
        if others and not (adopt and all(owner_of(r) is None for r in others)):
            who = ", ".join(owner_of(r) or "not managed by this tool" for r in others)
            conflicts.append(f"{fqdn(e)} already exists ({who})")
            continue
        # The first matching row is kept (updated if its address or tag
        # differs); any other row of owner for the name is deleted below, as
        # are owner's rows for names no longer wanted. Adopted duplicates
        # beyond the first are left alone (they carry no tag).
        targets = mine + (others if adopt else [])
        if targets:
            first = targets[0]
            keep.add(first["uuid"])
            if row_ip(first) != e["ip"] or owner_of(first) != owner:
                updates.append((first, e))
        else:
            adds.append(e)
    deletes = [r for r in rows if owner_of(r) == owner and r["uuid"] not in keep]
    return adds, updates, deletes, conflicts


def entry(e: dict, owner: str) -> dict:
    """The API host entry for wanted entry e, tagged with owner."""
    return {"host": e["host"], "domain": e["domain"], "ip": e["ip"], "descr": f"{TAG}{owner}"}


def cmd_sync(api: OPNsense, settings: dict, args) -> None:
    """The sync command: plan, print and (unless --dry-run) apply the changes, then verify (unless --no-verify).

    Nothing is changed when there is a conflict (DnsError). The configuration
    is applied only when something changed; names deleted and not re-added
    are verified as gone.
    """
    owner, wanted = load_records(args.input)
    rows = api.hosts()
    adds, updates, deletes, conflicts = plan_changes(rows, owner, wanted, args.adopt)
    if conflicts:
        raise DnsError("not changing entries this tool doesn't own:\n  " + "\n  ".join(conflicts) +
                       "\n(remove them in OPNsense, or pass --adopt to take over entries not managed by any owner)")
    log(f"Owner {owner}: {len(wanted)} record(s) wanted")
    for e in adds:
        print(f"  add     {fqdn(e):<45} A {e['ip']}")
    for r, e in updates:
        print(f"  update  {fqdn(e):<45} A {row_ip(r)} -> {e['ip']}"
              + ("  (adopt)" if owner_of(r) != owner else ""))
    for r in deletes:
        print(f"  delete  {r['host']}.{r['domain']:<{44 - len(r['host'])}} A {row_ip(r)}")
    if not (adds or updates or deletes):
        print("  nothing to change")
    if args.dry_run:
        log("Dry run: nothing changed")
        return
    if adds or updates or deletes:
        for e in adds:
            api.add(entry(e, owner))
        for r, e in updates:
            api.update(r["uuid"], entry(e, owner))
        for r in deletes:
            api.delete(r["uuid"])
        log("Applying the Dnsmasq configuration")
        api.apply()
    if not args.no_verify:
        gone = [f"{r['host']}.{r['domain']}" for r in deletes]
        verify(wanted, settings, [n for n in gone if n not in {fqdn(e) for e in wanted}])


def cmd_remove(api: OPNsense, settings: dict, args) -> None:
    """The remove command: delete every entry of --owner, apply, and verify the names are gone."""
    rows = [r for r in api.hosts() if owner_of(r) == args.owner]
    if not rows:
        log(f"No host entries owned by {args.owner}")
        return
    log(f"Owner {args.owner}: removing {len(rows)} entry(ies)")
    for r in rows:
        print(f"  delete  {r['host']}.{r['domain']:<{44 - len(r['host'])}} A {row_ip(r)}")
    if args.dry_run:
        log("Dry run: nothing changed")
        return
    for r in rows:
        api.delete(r["uuid"])
    log("Applying the Dnsmasq configuration")
    api.apply()
    verify([], settings, [f"{r['host']}.{r['domain']}" for r in rows])


def build_parser() -> argparse.ArgumentParser:
    """The command line parser: global --config and the sync, remove and list commands."""
    parser = argparse.ArgumentParser(
        prog=PROG, formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Register cluster DNS records as Dnsmasq host entries on OPNsense.",
        epilog=f"""\
examples:
  deploy-talos.py dns-records -f lab.yaml --domain example.org | {PROG} sync --dry-run
  deploy-talos.py dns-records -f lab.yaml --domain example.org | {PROG} sync
  {PROG} list
  {PROG} remove --owner deploy-talos.py:lab

Entries are tagged '{TAG}<owner>' in their description; the tool only changes
or deletes entries with its own owner's tag.

settings (YAML: url, keyFile, tlsFingerprint or caFile, dnsServer, dnsPort,
dnsmasqPort): --config FILE, else ${CONFIG_ENV}, else {DEFAULT_CONFIG.name}
next to this script. Template: opnsense-dns.example.yaml.
The API key's user needs the privilege 'Services: Dnsmasq DNS/DHCP: Settings'.

exit status: 0 success, 1 error (printed as ERROR: ...)""")
    parser.add_argument("--config", type=Path, default=None, metavar="FILE",
                        help=f"settings file (default: ${CONFIG_ENV}, else {DEFAULT_CONFIG})")
    sub = parser.add_subparsers(dest="command", metavar="command", required=True)
    p = sub.add_parser("sync", help="make one owner's entries match a records file",
                       description="Add, update and remove the host entries of the owner named in the records "
                                   "(JSON from 'deploy-*.py dns-records'), apply the Dnsmasq configuration and "
                                   "check the names through dnsServer.")
    p.add_argument("-i", "--input", default="-", metavar="FILE", help="records JSON (default: standard input)")
    p.add_argument("--dry-run", action="store_true", help="show the changes, change nothing")
    p.add_argument("--adopt", action="store_true",
                   help="take over existing entries with the same names that no owner manages")
    p.add_argument("--no-verify", action="store_true", help="skip the DNS check after applying")
    p = sub.add_parser("remove", help="delete all entries of one owner",
                       description="Delete every host entry tagged with OWNER and apply the configuration "
                                   "(e.g. after destroying the cluster).")
    p.add_argument("--owner", required=True, help="e.g. deploy-talos.py:lab")
    p.add_argument("--dry-run", action="store_true", help="show the entries, change nothing")
    p = sub.add_parser("list", help="show managed host entries",
                       description="List the host entries managed by this tool (or all of them with --all).")
    p.add_argument("--owner", help="only this owner's entries")
    p.add_argument("--all", action="store_true", help="also entries not managed by this tool")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the command; return 0, or 1 after printing a DnsError (argparse exits 2 on usage errors)."""
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings(args.config or default_config())
        api = OPNsense(settings)
        if args.command == "sync":
            cmd_sync(api, settings, args)
        elif args.command == "remove":
            cmd_remove(api, settings, args)
        elif args.command == "list":
            cmd_list(api, args)
    except DnsError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
