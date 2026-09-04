"""Surface conformance gate — the seed of the `surface` rung.

The human handshake: drives the CLI end-to-end through the layers beneath it
(init -> run -> condense -> verify -> realize -> prove) and claims the volatile
surface itself — argv grammar, exit codes, the shape of what a user sees (TOML
verdicts, the cost block, --json underneath). The functional depth is claimed
by the inner gates (kernel_check, exchange_check, authoring_check,
agents_check); above sits only contact — the README, claimed by
docs_check.py. Writes SURFACE_OK iff the toolchain a *user* touches is
conformant. Stdlib only, so it runs in any clean room.
"""
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, ".")
import reticuli.__main__   # the CLI entrypoint
from reticuli import cli

# --help is organized by process phase, not a flat verb dump — a mental map the
# user reads top to bottom as the workflow itself. The census showed structure
# evaporates unless a gate demands it, so the sections and their membership are
# ratified here; the wording of each line stays free.
SECTIONS = ("session (vapor):", "author (vapor -> liquid, M1):",
            "transfer (liquid, M2):", "redo (liquid -> solid, M3):", "compose:")
LISTED = {"init", "hooks", "status", "run", "condense", "verify", "export",
          "import", "audit", "realize", "prove", "attest", "mint", "pack", "pull",
          "tree", "records"}


def _help() -> str:
    r = subprocess.run([sys.executable, "-m", "reticuli", "--help"],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0, "the CLI answers --help"
    return r.stdout


def _run(argv: list[str]) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        code = cli.main(argv)
    return code, buf.getvalue()


def battery() -> None:
    assert reticuli.__main__.main is cli.main, "entrypoint"

    # the sectioned map: five phase groups in process order, every human verb
    # under exactly one, and `hook` present but unlisted (agent plumbing).
    help_out = _help()
    last = -1
    for s in SECTIONS:
        i = help_out.find(s)
        assert i > last, f"help section missing or out of order: {s!r}"
        last = i
    listed = set(re.findall(r"^\s{4}([a-z][a-z-]+)\s{2,}", help_out, re.MULTILINE))
    assert listed == LISTED, f"help verb map drifted: {listed ^ LISTED}"
    assert "hook" not in listed, "hook is internal — it must not be listed"

    d = tempfile.mkdtemp()
    try:
        ws = os.path.join(d, "ws")
        code, _ = _run(["init", ws])
        assert code == 0, "init exits 0"
        with open(os.path.join(ws, ".gitignore")) as f:
            assert "ledger.jsonl" in f.read(), "init is git-native"

        with open(os.path.join(ws, "answer.txt"), "w") as f:
            f.write("42\n")
        gate = "grep -qx 42 answer.txt && printf ok > OK"
        code, _ = _run(["run", gate, "-C", ws])
        assert code == 0 and os.path.isfile(os.path.join(ws, "OK")), "run authors a gate"
        events = [{"event": "prompt", "text": "write the answer", "ts": 5.0},
                  {"event": "write", "path": "answer.txt", "ts": 6.0},
                  {"event": "bash", "cmd": gate, "ts": 7.0}]
        with open(os.path.join(ws, ".reticuli", "vapor.jsonl"), "w") as f:
            f.write("\n".join(json.dumps(e) for e in events) + "\n")

        rec = os.path.join(ws, ".reticuli", "liquid", "answer")
        code, _ = _run(["condense", ws, "--accept", "OK", "--into", rec, "--name", "answer"])
        assert code == 0, "condense exits 0"
        code, out = _run(["verify", rec])
        assert code == 0 and "fresh" in out, "verify says fresh"
        code, out = _run(["verify", rec, "--json"])
        assert code == 0 and json.loads(out)["ok"], "--json underneath"

        m3 = os.path.join(d, "m3")
        code, out = _run(["realize", rec, "--producer", "printf '42\\n' > answer.txt",
                          "--into", m3])
        assert code == 0 and "calls" in out, "realize reports what it paid"
        m2 = os.path.join(d, "m2")
        shutil.copytree(rec, m2)
        code, out = _run(["prove", rec, m2, m3])
        assert code == 0, "prove exits 0"
        assert "satisfied = true" in out and "[cost]" in out, "the verdict and the bill"

        # the transfer and attestation verbs, end to end at the surface — the
        # census showed a redo can shrink the CLI to just what the gate drives,
        # so the whole README proof (export -> import -> audit -> attest) is
        # exercised here, not merely named.
        tar = os.path.join(d, "answer.tar")
        code, out = _run(["export", rec, tar])
        assert code == 0 and os.path.isfile(tar), "export writes the record's tar"
        imp = os.path.join(d, "imported")
        code, out = _run(["import", tar, imp])
        assert code == 0 and "fresh" in out, "import verifies from bytes alone"
        code, out = _run(["audit", rec])
        assert code == 0 and "earned" in out, "audit re-earns the verdict"
        key = os.path.join(d, "id")
        subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-q", "-f", key], check=True)
        code, out = _run(["attest", m3, "--key", key, "--as", "you@lab"])
        assert code == 0, "attest signs a realization"
        code, out = _run(["attest", m3, "--check"])
        assert code == 0 and "attested" in out, "attest --check verifies the signature"

        # the mint ceremony at the surface: no key reviews the chain + packet,
        # a key authorizes it, --check verifies the authorization
        code, out = _run(["mint", m3])
        assert code == 0 and "mint" in out, "mint (no key) emits the review packet"
        code, out = _run(["mint", m3, "--key", key, "--as", "you@lab"])
        assert code == 0 and "ceremony" in out, "mint --key authorizes the chain"
        code, out = _run(["mint", m3, "--check"])
        assert code == 0 and "authorized = true" in out, "mint --check verifies the authorization"

        code, out = _run(["records", ws])
        assert code == 0 and "answer" in out, "the drawer renders"

        # two lenses, one verb: a session's tree is dry/wet PLUS its drawer's
        # dependency graph (deps folded in); a record's tree is its anatomy —
        # seeds (the claim), free strata, pinned verdicts
        code, out = _run(["tree", ws])
        assert code == 0 and "vapor" in out, "the session lens"
        assert "answer" in out and "record(s)" in out, "the drawer graph rides in the session lens"
        code, out = _run(["tree", rec])
        assert code == 0 and "free  answer.txt" in out and "pin   OK" in out \
            and "rung(s)" in out, "the record lens"

        # the agent handshake at the surface: `ret hook` is silent, `ret hooks` wires
        payload = {"hook_event_name": "UserPromptSubmit", "prompt": "again", "cwd": ws}
        stdin, sys.stdin = sys.stdin, io.StringIO(json.dumps(payload))
        try:
            code, out = _run(["hook", "-C", ws])
        finally:
            sys.stdin = stdin
        assert code == 0 and out == "", "hook exits 0 and prints nothing"
        with open(os.path.join(ws, ".reticuli", "vapor.jsonl")) as f:
            assert '"prompt"' in f.readlines()[-1], "the payload became a trace event"
        code, _ = _run(["hooks", ws])
        assert code == 0 and os.path.isfile(
            os.path.join(ws, ".claude", "settings.json")), "hooks wires the agent"
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    battery()
    with open("SURFACE_OK", "w") as f:
        f.write("surface-ok\n")
    print("surface-ok")
