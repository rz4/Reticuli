"""Attestation: a realization that speaks for itself to others.

Quarantine protects the verifier from a hostile record; attestation is the
converse — a keyholder's signed statement that *this* realization verified
fresh on their machine: the root, every output's hash, the gates' quarantine
record, the cost. Signed with `ssh-keygen -Y` (the key you already have), in
in-toto Statement shape so foreign tooling can read it. Attestations are
residue *about* the claim, never part of it — they live in .reticuli/attest/,
travel with the record (export carries them), and never enter the root.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import subprocess

from . import kernel

ATTEST = os.path.join(kernel.STORE, "attest")
NAMESPACE = "reticuli"
STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
PREDICATE_TYPE = "https://github.com/rz4/reticuli/attest/v1"


def _sh(argv: list[str], stdin: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(argv, input=stdin, capture_output=True, check=False)


def _slug(identity: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", identity.lower()).strip("-") or "signer"


def _gates(d: str) -> list[dict]:
    """The ledger's gate lines — the quarantine evidence the statement carries."""
    path = os.path.join(d, kernel.LEDGER)
    out = []
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if e.get("event") == "gate":
                    out.append(e)
    return out


def statement(d: str, identity: str) -> dict:
    """The in-toto statement for this realization, as it stands on disk."""
    m = kernel.read_manifest(d)
    recipe = kernel.load_recipe(d)
    outputs = {kernel._out(s): kernel._hf(os.path.join(d, kernel._out(s)))
               for s in recipe.get("step", [])
               if os.path.isfile(os.path.join(d, kernel._out(s)))}
    return {
        "_type": STATEMENT_TYPE,
        "subject": [{"name": m["name"], "digest": {"reticuliRoot": m["root"]}}],
        "predicateType": PREDICATE_TYPE,
        "predicate": {
            "identity": identity,
            "when": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
            "outputs": outputs,
            "gates": _gates(d),
            "cost": kernel.cost(d),
        },
    }


def attest(d: str, key: str, identity: str) -> dict:
    """Sign this realization. Refuses a broken record — an attestation is a
    statement that it verified fresh, here, now."""
    v = kernel.verify(d)
    if not v["ok"]:
        raise kernel.ReticuliError("attest: the record is broken — refusing to sign")
    st = statement(d, identity)
    os.makedirs(os.path.join(d, ATTEST), exist_ok=True)
    path = os.path.join(d, ATTEST, f"{_slug(identity)}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=2, sort_keys=True)
        f.write("\n")
    r = _sh(["ssh-keygen", "-Y", "sign", "-f", os.path.expanduser(key),
             "-n", NAMESPACE, path])
    if r.returncode != 0:
        raise kernel.ReticuliError(f"attest: signing failed: {r.stderr.decode().strip()[:200]}")
    rel = os.path.join(ATTEST, f"{_slug(identity)}.json")
    return {"name": v["name"], "root": v["root"], "identity": identity,
            "statement": rel, "signature": rel + ".sig"}


def check(d: str, signers: str | None = None) -> dict:
    """Verify this record's attestations. With an allowed-signers file the
    signer's identity is verified; without one, only that each signature is
    intact for the bytes it covers ("intact", signer untrusted). Either way the
    statement must name this record's current root."""
    v = kernel.verify(d)
    results = []
    base = os.path.join(d, ATTEST)
    for name in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        if not name.endswith(".json"):
            continue
        path = os.path.join(base, name)
        with open(path, "rb") as f:
            raw = f.read()
        st = json.loads(raw)
        identity = st.get("predicate", {}).get("identity", "")
        roots = {dg for s in st.get("subject", []) for dg in s.get("digest", {}).values()}
        if signers:
            r = _sh(["ssh-keygen", "-Y", "verify", "-f", os.path.expanduser(signers),
                     "-I", identity, "-n", NAMESPACE, "-s", path + ".sig"], stdin=raw)
            verdict = "signed" if r.returncode == 0 else "invalid"
        else:
            r = _sh(["ssh-keygen", "-Y", "check-novalidate", "-n", NAMESPACE,
                     "-s", path + ".sig"], stdin=raw)
            verdict = "intact" if r.returncode == 0 else "invalid"
        results.append({"identity": identity, "verdict": verdict,
                        "root_match": v["root"] in roots,
                        "when": st.get("predicate", {}).get("when"),
                        "ok": verdict in ("signed", "intact") and v["root"] in roots})
    return {"name": v["name"], "root": v["root"], "fresh": v["ok"],
            "attestations": results,
            "ok": v["ok"] and bool(results) and all(x["ok"] for x in results)}
