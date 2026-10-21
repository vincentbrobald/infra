from __future__ import annotations

DOCUMENTATION = r"""
name: site_secret
short_description: A credential from gitops (SOPS), its file, or generated
description:
  - "Returns one credential. The gitops repository wins. When a Secret for the
    topic (namespace/name, and the key) exists there, SOPS-encrypted, its
    value is used and never replaced. The local file is then made to match it
    (the previous content is kept as <file>.pre-gitops)."
  - "Without it in gitops, the file's content is used (trailing newline
    stripped)."
  - "Without either, I(default) or a generated value (I(generate)) is
    written to the file (mode 0600); with I(optional) an empty string is
    returned; otherwise the lookup fails."
  - "The gitops checkout is the one gitops.yml keeps up to date
    (site_gitops_checkout); it is read here, never written."
options:
  _terms:
    description: File of the credential, relative to site_secrets_dir or absolute.
    required: true
  topic:
    description: "Secret in the gitops repository, as namespace/name (every cluster folder is searched)."
  key:
    description: Key in the Secret's stringData or data.
  generate:
    description: "Generator when nothing exists yet: hex:N (N random bytes as hex), base64:N (N random bytes, base64) or alnum:N (N letters and digits)."
  default:
    description: "Value written to the file when nothing exists yet (a name rather than a secret, e.g. an access key ID)."
  optional:
    description: "Return an empty string when nothing exists yet (the caller makes the credential)."
    type: bool
    default: false
"""

import base64
import os
import secrets
import string
import subprocess
from pathlib import Path

import yaml
from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
from ansible.utils.display import Display

display = Display()

# Decrypted Secret values by file path, so that each file is decrypted once
# per process (one ansible-playbook run).
_DECRYPTED: dict[str, dict] = {}


def _generate(spec: str) -> str:
    """Return a new random value as spec says (hex:N, base64:N or alnum:N, N >= 8 bytes or characters).

    Raises AnsibleError for any other spec.
    """
    kind, _, n = spec.partition(":")
    if not n.isdigit() or int(n) < 8:
        raise AnsibleError(f"site_secret: generate must be hex:N, base64:N or alnum:N with N >= 8, not {spec!r}")
    if kind == "hex":
        return secrets.token_hex(int(n))
    if kind == "base64":
        return base64.b64encode(secrets.token_bytes(int(n))).decode()
    if kind == "alnum":
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(int(n)))
    raise AnsibleError(f"site_secret: unknown generator {kind!r} (hex, base64 or alnum)")


def _write(path: Path, value: str) -> None:
    """Write value and a newline to path, replacing its content.

    A new file gets mode 0600 and missing directories 0700; an existing file
    keeps its mode.
    """
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(value + "\n")


class LookupModule(LookupBase):
    """The site_secret lookup (see DOCUMENTATION)."""

    def _gitops_files(self, checkout: Path, topic: str) -> list[Path]:
        """Return the *.enc.yaml files of checkout (outside .git) holding Secret topic
        (namespace/name; no namespace counts as "default"), sorted.

        Only data and stringData are encrypted, so names are read without
        decrypting; unreadable or invalid files are skipped.
        """
        ns, _, name = topic.partition("/")
        found = []
        for p in sorted(checkout.rglob("*.enc.yaml")):
            if ".git" in p.parts:
                continue
            try:
                doc = yaml.safe_load(p.read_text()) or {}
            except (OSError, yaml.YAMLError):
                continue
            if not isinstance(doc, dict):
                continue
            md = doc.get("metadata") or {}
            if doc.get("kind") == "Secret" and md.get("name") == name and md.get("namespace", "default") == ns:
                found.append(p)
        return found

    def _decrypt(self, path: Path, sops: str, age_key: str) -> dict:
        """Return the values of the SOPS-encrypted Secret in path, data base64-decoded and
        stringData (which wins on a shared key) as strings.

        sops runs with SOPS_AGE_KEY_FILE=age_key; the result is cached in
        _DECRYPTED. Raises AnsibleError if sops fails.
        """
        if str(path) not in _DECRYPTED:
            p = subprocess.run([sops, "decrypt", "--input-type", "yaml", "--output-type", "yaml", str(path)],
                               capture_output=True, text=True, env={**os.environ, "SOPS_AGE_KEY_FILE": age_key},
                               cwd=path.parent)
            if p.returncode != 0:
                raise AnsibleError(f"site_secret: cannot decrypt {path} with {age_key}: {p.stderr.strip()[-300:]}")
            doc = yaml.safe_load(p.stdout) or {}
            data = {k: base64.b64decode(v).decode() for k, v in (doc.get("data") or {}).items()}
            data.update({k: str(v) for k, v in (doc.get("stringData") or {}).items()})
            _DECRYPTED[str(path)] = data
        return _DECRYPTED[str(path)]

    def _from_gitops(self, variables: dict, topic: str, key: str) -> str | None:
        """Return the value of key in Secret topic in the gitops checkout, or None when no
        Secret there has it or site_gitops_checkout is unset.

        Every cluster folder is searched. Raises AnsibleError when the checkout is
        missing or the copies of the Secret disagree on the value.
        """
        checkout = self._templar.template(variables.get("site_gitops_checkout", ""))
        if not checkout:
            return None
        checkout = Path(checkout)
        if not checkout.is_dir():
            raise AnsibleError(f"site_secret: gitops checkout {checkout} is missing; run gitops.yml first "
                               "(site.yml and every service playbook import it)")
        sops = self._templar.template(variables["site_sops_bin"])
        age_key = self._templar.template(variables["site_sops_age_key_file"])
        values = {}
        for p in self._gitops_files(checkout, topic):
            data = self._decrypt(p, sops, age_key)
            if key in data:
                values[str(p.relative_to(checkout))] = data[key]
        if len(set(values.values())) > 1:
            raise AnsibleError(f"site_secret: Secret {topic} key {key} differs between {', '.join(values)} "
                               "in the gitops repository; make them agree first")
        return next(iter(values.values()), None)

    def run(self, terms, variables=None, **kwargs):
        """Return one credential per term (a file path), as DOCUMENTATION describes.

        Precedence: the gitops value (the file is rewritten to match, the old
        content backed up), the file, optional's empty string, default, generate.
        Raises AnsibleError when nothing applies or the value is empty.
        """
        self.set_options(var_options=variables, direct=kwargs)
        topic, key = self.get_option("topic"), self.get_option("key")
        generate, default = self.get_option("generate"), self.get_option("default")
        if bool(topic) != bool(key):
            raise AnsibleError("site_secret: topic and key go together")
        base = Path(self._templar.template(variables["site_secrets_dir"]))
        out = []
        for term in terms:
            path = Path(term) if os.path.isabs(term) else base / term
            local = path.read_text().rstrip("\n") if path.is_file() else None
            value = self._from_gitops(variables, topic, key) if topic else None
            if value is not None:
                if local != value:
                    if local is not None:
                        backup = path.with_name(path.name + ".pre-gitops")
                        _write(backup, local)
                        display.warning(f"{path} differed from Secret {topic} ({key}) in the gitops repository: "
                                        f"replaced by the gitops value (previous content in {backup})")
                    _write(path, value)
            elif local is not None:
                value = local
            elif self.get_option("optional"):
                out.append("")
                continue
            elif default:
                value = str(default)
                _write(path, value)
            elif generate:
                value = _generate(generate)
                _write(path, value)
                display.display(f"site_secret: generated {path}", color="yellow")
            else:
                raise AnsibleError(f"site_secret: {path} does not exist"
                                   + (f" and Secret {topic} has no key {key} in the gitops repository" if topic else ""))
            if not value:
                raise AnsibleError(f"site_secret: {path} is empty")
            out.append(value)
        return out
