#!/usr/bin/env python3
"""Verdict-differential fuzz: the committed kernel vs two regrown specimen
kernels (run-5 capstone draw, kc-validate draw), all three realizations of the
SAME kernel-core claim (root 2ec592de).

Two modes, separating two questions:

  INTEROP (@i)  records built and sealed by the COMMITTED kernel, judged by
                all three. Measures whether records TRAVEL across independent
                implementations of one claim — exact values compared.
  NATIVE  (@n)  each kernel re-seals its own pristine copy under its own
                canonicalization BEFORE the tamper, then judges. Measures the
                pure verdict semantics — decisions compared, not hash values.

The observation vector is the pinned decision surface of kernel_check: claim,
verify, phase, audit, realization digest, cost; for triples three_machine and
freeze_dry. Any disagreement is a counterexample — a region where the cage is
silent. Stakes buckets:

  ACCEPTS   a draw accepts what committed refuses — the dangerous quadrant
  REFUSES   a draw refuses what committed accepts — over-strict / breaks travel
  SHAPE     value-shape or exception-type differences — cosmetic, still width

Usage: python3 harness.py REF_KERNEL DRAW_KERNEL [DRAW_KERNEL ...]
                          [--smoke] [--fixed-only] [--n N]

The first kernel is the reference ("committed" in the rows); each further path
is a draw judged against it. Results land in ./divergences.jsonl.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import random
import re
import shutil
import signal
import subprocess
import tempfile

SEED = 20260905
CALL_TIMEOUT = 60          # per judgment call; a hung draw is an observation
WORK = tempfile.mkdtemp(prefix="vfuzz-")
RESULTS = os.path.join(os.getcwd(), "divergences.jsonl")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

FIXTURE = '''[record]
name = "fixture"

[[step]]
kind = "produce"
output = "g.txt"
request = "a greeting containing the word hello"
class = "free"

[[step]]
kind = "gate"
output = "V"
run = "grep -qi hello g.txt && printf v > V"
class = "validated"
'''

SEEDED = '''[record]
name = "seeded"
inputs = ["spec.txt"]

[[step]]
kind = "produce"
output = "impl.txt"
request = "any implementation that satisfies the spec"
class = "free"

[[step]]
kind = "gate"
output = "V"
run = "grep -q PASS impl.txt && printf v > V"
class = "validated"
'''


# ---------------------------------------------------------------- kernel load
def load_kernel(name, path):
    spec = importlib.util.spec_from_file_location(f"k_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CallTimeout(Exception):
    pass


def _alarm(_sig, _frm):
    raise CallTimeout()


def ask(fn, *a):
    """("ok", value) or ("exc", ExceptionTypeName). A hang becomes TIMEOUT."""
    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(CALL_TIMEOUT)
    try:
        return ("ok", fn(*a))
    except CallTimeout:
        return ("exc", "TIMEOUT")
    except BaseException as e:  # noqa: BLE001 — every failure mode is data here
        return ("exc", type(e).__name__)
    finally:
        signal.alarm(0)


# ------------------------------------------------------------- the questions
def judge_record(k, d, mode):
    """The pinned per-record decision surface. In native mode hash VALUES are
    opaque (each canon is its own coordinate system); decisions still compare."""
    obs = {}
    s, cv = ask(lambda: k.claim(k.load_recipe(d), d))
    if mode == "native":
        obs["claim"] = ("HEX" if s == "ok" and isinstance(cv, str) and HEX64.match(cv)
                        else f"EXC:{cv}" if s == "exc" else f"SHAPE:{type(cv).__name__}")
    else:
        obs["claim"] = cv if s == "ok" else f"EXC:{cv}"
    s, v = ask(k.verify, d)
    if s == "ok" and isinstance(v, dict):
        if mode == "native":
            obs["verify"] = {"ok": bool(v.get("ok")),
                             "root_eq_claim": v.get("root") == cv,
                             "move_detected": (None if v.get("ok")
                                               else v.get("recomputed") != v.get("root"))}
        else:
            obs["verify"] = {"ok": bool(v.get("ok")), "root": v.get("root"),
                             "recomputed": None if v.get("ok") else v.get("recomputed")}
    else:
        obs["verify"] = f"EXC:{v}" if s == "exc" else f"SHAPE:{type(v).__name__}"
    s, v = ask(k.phase, d)
    obs["phase"] = v if s == "ok" else f"EXC:{v}"
    s, v = ask(k.audit, d)
    obs["audit"] = (bool(v.get("ok")) if s == "ok" and isinstance(v, dict)
                    else f"EXC:{v}" if s == "exc" else f"SHAPE:{type(v).__name__}")
    s, v = ask(k.realization_digest, d)
    if mode == "native":
        obs["rdigest"] = ("HEX" if s == "ok" and isinstance(v, str) and HEX64.match(v)
                          else f"EXC:{v}" if s == "exc" else f"SHAPE:{type(v).__name__}")
    else:
        obs["rdigest"] = v if s == "ok" else f"EXC:{v}"
    s, v = ask(k.cost, d)
    if s == "ok":
        obs["cost"] = None if v is None else {kk: v.get(kk) for kk in ("calls", "tokens", "usd")}
    else:
        obs["cost"] = f"EXC:{v}"
    return obs


def judge_triple(k, m1, m2, m3):
    obs = {}
    s, v = ask(k.three_machine, m1, m2, m3)
    if s == "ok" and isinstance(v, dict):
        obs["satisfied"] = bool(v.get("satisfied"))
        obs["equivalence"] = bool(v.get("equivalence"))
        obs["audited"] = {m: bool(x) for m, x in (v.get("audited") or {}).items()}
        obs["one_root"] = len(set((v.get("roots") or {}).values())) == 1
        obs["independence_reported"] = "independence" in v
        obs["cost_comparable"] = (v.get("cost") or {}).get("comparable")
    else:
        obs["three_machine"] = f"EXC:{v}" if s == "exc" else f"SHAPE:{type(v).__name__}"
    return obs


def judge_freeze(k, m1, m2, m3):
    s, v = ask(k.freeze_dry, m1, m2, m3)
    if s == "ok" and isinstance(v, dict):
        return {"proof_recorded": bool(v.get("proof_recorded"))}
    return {"freeze_dry": f"EXC:{v}" if s == "exc" else f"SHAPE:{type(v).__name__}"}


# ------------------------------------------------------- prototype construction
def sh(cmd, cwd):
    subprocess.run(cmd, shell=True, cwd=cwd, check=True, capture_output=True)


def build_protos(k, proto):
    """Built once, by the committed kernel: sealed fixture, sealed seeded
    record, an honest proven triple, mint key material."""
    os.makedirs(proto, exist_ok=True)
    fx = os.path.join(proto, "fx")
    os.makedirs(fx)
    with open(os.path.join(fx, "reticuli.toml"), "w") as f:
        f.write(FIXTURE)
    with open(os.path.join(fx, "g.txt"), "w") as f:
        f.write("hello, world\n")
    sh("grep -qi hello g.txt && printf v > V", fx)
    k.seal(fx)

    sd = os.path.join(proto, "sd")
    os.makedirs(sd)
    with open(os.path.join(sd, "reticuli.toml"), "w") as f:
        f.write(SEEDED)
    with open(os.path.join(sd, "spec.txt"), "w") as f:
        f.write("acceptance criteria: v1\n")
    with open(os.path.join(sd, "impl.txt"), "w") as f:
        f.write("PASS — implementation one\n")
    sh("grep -q PASS impl.txt && printf v > V", sd)
    k.seal(sd)

    m2 = os.path.join(proto, "fx-m2")
    shutil.copytree(fx, m2)
    m3 = os.path.join(proto, "fx-m3")
    k.realize(fx, "printf 'why, hello!\\n' > g.txt", m3)
    assert k.three_machine(fx, m2, m3)["satisfied"], "proto triple must prove"
    k.freeze_dry(fx, m2, m3)
    proof = k.read_manifest(fx).get("proof")
    assert proof, "proto proof recorded"

    ekey = os.path.join(proto, "ekey")
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-q", "-f", ekey],
                   capture_output=True, check=True)
    okey = os.path.join(proto, "okey")   # a second, never-anchored key
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-q", "-f", okey],
                   capture_output=True, check=True)
    with open(ekey + ".pub") as f:
        ktype, blob = f.read().split()[:2]
    with open(os.path.join(proto, "allowed_signers"), "w") as f:
        f.write(f"signer@basin {ktype} {blob}\n")
    return {"fx": fx, "sd": sd, "m2": m2, "m3": m3, "proof": proof,
            "ekey": ekey, "okey": okey, "signers": os.path.join(proto, "allowed_signers")}


def hand_mint(k, record, ident, keypath, include_proof=True):
    """kernel_check's ceremony, verbatim, constructed WITH the given kernel —
    its digests, its mint directory. Ephemeral fuzz keys only."""
    mdir = os.path.join(record, k.MINT)
    os.makedirs(mdir, exist_ok=True)
    packet = {"root": k.verify(record)["root"],
              "realization_digest": k.realization_digest(record),
              "proof": k.read_manifest(record).get("proof") if include_proof else None}
    pdig = hashlib.sha256(json.dumps(packet, sort_keys=True).encode()).hexdigest()
    with open(os.path.join(mdir, "x.packet.json"), "w") as f:
        json.dump(packet, f, sort_keys=True)
    spath = os.path.join(mdir, "x.mint.json")
    with open(spath, "w") as f:
        json.dump({"identity": ident, "root": packet["root"], "packet_digest": pdig,
                   "proof_recorded": bool(packet["proof"])}, f, sort_keys=True)
    subprocess.run(["ssh-keygen", "-Y", "sign", "-f", keypath, "-n", "reticuli", spath],
                   capture_output=True, check=True)
    return spath


# ------------------------------------------------------------------- helpers
def manifest_path(d):
    return os.path.join(d, ".reticuli", "manifest.json")      # STORE agrees 3/3


def edit_manifest(d, fn):
    with open(manifest_path(d)) as f:
        m = json.load(f)
    fn(m)
    with open(manifest_path(d), "w") as f:
        json.dump(m, f)


def edit_json(path, fn):
    with open(path) as f:
        m = json.load(f)
    fn(m)
    with open(path, "w") as f:
        json.dump(m, f, sort_keys=True)


def _w(path, text):
    with open(path, "w") as f:
        f.write(text)


# ------------------------------------------------------------------- the cases
def fixed_cases(p):
    """(case_id, base_proto, setup(d, k) -> env_extra | None). setup mutates the
    already-copied (and in native mode, re-sealed) record dir d."""
    yield "s01-pristine-fx", p["fx"], lambda d, k: None
    yield "s02-pristine-sd", p["sd"], lambda d, k: None
    yield "s03-free-rewrite-passing", p["fx"], \
        lambda d, k: _w(os.path.join(d, "g.txt"), "hello again, differently\n")
    yield "s04-free-rewrite-failing", p["fx"], \
        lambda d, k: _w(os.path.join(d, "g.txt"), "goodbye, nothing to see\n")
    yield "s05-seed-edit", p["sd"], \
        lambda d, k: _w(os.path.join(d, "spec.txt"), "acceptance criteria: v2 (stricter)\n")
    yield "s06-seed-deleted", p["sd"], lambda d, k: os.remove(os.path.join(d, "spec.txt"))
    yield "s07-output-deleted", p["fx"], lambda d, k: os.remove(os.path.join(d, "g.txt"))
    yield "s08-manifest-deleted", p["fx"], lambda d, k: os.remove(manifest_path(d))

    def s09(d, k):
        with open(manifest_path(d)) as f:
            raw = f.read()
        _w(manifest_path(d), raw[:len(raw) // 2])
    yield "s09-manifest-truncated", p["fx"], s09
    yield "s10-manifest-root-zeroed", p["fx"], \
        lambda d, k: edit_manifest(d, lambda m: m.__setitem__("root", "0" * 64))
    yield "s11-manifest-proof-forged", p["fx"], \
        lambda d, k: edit_manifest(d, lambda m: m.__setitem__(
            "proof", {"kind": "three-machine", "m2": "FORGED", "m3": "FORGED"}))
    yield "s12-manifest-unknown-key", p["fx"], \
        lambda d, k: edit_manifest(d, lambda m: m.__setitem__("x_unknown", 42))
    yield "s13-manifest-rewritten-sorted", p["fx"], lambda d, k: edit_manifest(d, lambda m: None)

    def s14(d, k):
        with open(os.path.join(d, "reticuli.toml")) as f:
            t = f.read()
        _w(os.path.join(d, "reticuli.toml"),
           t.replace("grep -qi hello", "grep -qi HELLO_EDITED"))
    yield "s14-gate-cmd-edited", p["fx"], s14

    def s15(d, k):
        _w(os.path.join(os.path.dirname(d), "outside.txt"), "outside the record\n")
        with open(os.path.join(d, "reticuli.toml")) as f:
            t = f.read()
        _w(os.path.join(d, "reticuli.toml"),
           t.replace('name = "fixture"', 'name = "fixture"\ninputs = ["../outside.txt"]'))
    yield "s15-seed-escapes-dotdot", p["fx"], s15

    def s16(d, k):
        with open(os.path.join(d, "reticuli.toml")) as f:
            t = f.read()
        _w(os.path.join(d, "reticuli.toml"),
           t.replace('name = "fixture"', 'name = "fixture"\ninputs = ["/etc/hosts"]'))
    yield "s16-seed-absolute", p["fx"], s16

    def s17(d, k):
        _w(os.path.join(os.path.dirname(d), "target.txt"), "acceptance criteria: v1\n")
        os.remove(os.path.join(d, "spec.txt"))
        os.symlink(os.path.join(os.path.dirname(d), "target.txt"),
                   os.path.join(d, "spec.txt"))
    yield "s17-seed-symlink-out", p["sd"], s17

    def s18(d, k):
        _w(os.path.join(os.path.dirname(d), "gtarget.txt"), "hello, world\n")
        os.remove(os.path.join(d, "g.txt"))
        os.symlink(os.path.join(os.path.dirname(d), "gtarget.txt"),
                   os.path.join(d, "g.txt"))
    yield "s18-output-symlink-out", p["fx"], s18

    yield "s19-seed-emptied", p["sd"], lambda d, k: _w(os.path.join(d, "spec.txt"), "")

    def s21(d, k):
        with open(os.path.join(d, "reticuli.toml")) as f:
            t = f.read()
        _w(os.path.join(d, "reticuli.toml"), t + '''
[[step]]
kind = "produce"
output = "g.txt"
request = "the same output declared twice"
class = "free"
''')
    yield "s21-duplicate-output-step", p["fx"], s21

    def s22(d, k):
        _w(os.path.join(d, "reticuli.toml"), '''[record]
name = "fixture"

[[step]]
kind = "produce"
output = "g.txt"
request = "a greeting"
class = "free"
''')
    yield "s22-gateless-recipe", p["fx"], s22

    def s24(d, k):
        led = os.path.join(d, ".reticuli", "ledger.jsonl")   # LEDGER agrees 3/3
        os.makedirs(os.path.dirname(led), exist_ok=True)
        prev = ""
        if os.path.isfile(led):
            with open(led) as f:
                prev = f.read()
        _w(led, "this is not json\n" + prev)
    yield "s24-ledger-garbage-line", p["m3"], s24
    yield "s25-ledger-huge-calls", p["m3"], \
        lambda d, k: _w(os.path.join(d, ".reticuli", "ledger.jsonl"),
                        '{"event": "oracle", "calls": 1000000000}\n')


def mint_cases(p):
    """Native-mode mint battery: the ceremony is performed WITH the judging
    kernel (its digests, its mint directory), so what compares is the verdict
    semantics, not the coordinate system. Proof residue is re-injected after
    the native reseal (a reseal writes a fresh manifest)."""
    sgn = {"RETICULI_SIGNERS": p["signers"]}

    def with_proof(d, k):
        edit_manifest(d, lambda m: m.__setitem__("proof", p["proof"]))

    def base(d, k, ident="signer@basin", key=None, proof=True):
        with_proof(d, k)
        hand_mint(k, d, ident, key or p["ekey"], include_proof=proof)

    yield "m01-minted-trusted-proven", p["fx"], lambda d, k: (base(d, k), sgn)[-1]
    yield "m02-minted-no-anchor-env", p["fx"], lambda d, k: base(d, k)
    yield "m03-packet-root-swapped", p["fx"], lambda d, k: (
        base(d, k),
        edit_json(os.path.join(d, k.MINT, "x.packet.json"),
                  lambda m: m.__setitem__("root", "f" * 64)),
        sgn)[-1]
    yield "m04-statement-digest-swapped", p["fx"], lambda d, k: (
        base(d, k),
        edit_json(os.path.join(d, k.MINT, "x.mint.json"),
                  lambda m: m.__setitem__("packet_digest", "e" * 64)),
        sgn)[-1]
    yield "m05-signature-deleted", p["fx"], lambda d, k: (
        base(d, k), os.remove(os.path.join(d, k.MINT, "x.mint.json.sig")), sgn)[-1]
    yield "m06-untrusted-key", p["fx"], lambda d, k: (
        base(d, k, ident="stranger@elsewhere", key=p["okey"]), sgn)[-1]
    yield "m07-drift-after-mint", p["fx"], lambda d, k: (
        base(d, k),
        _w(os.path.join(d, "g.txt"), "hello, but drifted after the mint\n"),
        sgn)[-1]
    yield "m08-packet-without-proof", p["fx"], lambda d, k: (
        base(d, k, proof=False), sgn)[-1]

    def m09(d, k):
        base(d, k, ident="stranger@elsewhere", key=p["okey"])   # untrusted statement...
        for f in ("x.packet.json", "x.mint.json", "x.mint.json.sig"):
            os.rename(os.path.join(d, k.MINT, f),
                      os.path.join(d, k.MINT, "y" + f[1:]))
        base(d, k)                                              # ...beside a trusted one
        return sgn
    yield "m09-one-bad-one-good-statement", p["fx"], m09

    def m10(d, k):
        base(d, k, ident="impostor@basin")   # the ANCHORED key, the wrong name
        return sgn
    yield "m10-identity-mismatch", p["fx"], m10


# ------------------------------------------------------------------ execution
def run_case(kernels, cid, proto_dir, setup, results, klass, mode):
    tag = f"{cid}@{'n' if mode == 'native' else 'i'}"
    envs = {}
    obs = {}
    env_extra = None
    for name, k in kernels.items():
        d = os.path.join(WORK, f"{tag}--{name}", os.path.basename(proto_dir))
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copytree(proto_dir, d, symlinks=True)
        if mode == "native":
            s, v = ask(k.seal, d)
            if s == "exc":
                obs[name] = {"native_seal": f"EXC:{v}"}
                continue
        try:
            env_extra = setup(d, k) or env_extra
        except BaseException as e:  # noqa: BLE001 — a setup the kernel breaks is data
            obs[name] = {"setup": f"EXC:{type(e).__name__}"}
            continue
        envs[name] = d
    saved = os.environ.get("RETICULI_SIGNERS")
    os.environ.pop("RETICULI_SIGNERS", None)
    if env_extra:
        os.environ.update(env_extra)
    try:
        for name, k in kernels.items():
            if name in envs:
                obs[name] = judge_record(k, envs[name], mode)
    finally:
        os.environ.pop("RETICULI_SIGNERS", None)
        if saved is not None:
            os.environ["RETICULI_SIGNERS"] = saved
    record_divergences(tag, klass, obs, results)
    for name in kernels:
        shutil.rmtree(os.path.join(WORK, f"{tag}--{name}"), ignore_errors=True)


def record_divergences(cid, klass, obs, results):
    ref = obs.get("committed", {})
    for name, o in obs.items():
        if name == "committed":
            continue
        for field in sorted(set(ref) | set(o)):
            a, b = ref.get(field), o.get(field)
            if a == b:
                continue
            stakes = classify(field, a, b)
            row = {"case": cid, "class": klass, "kernel": name, "field": field,
                   "committed": a, "draw": b, "stakes": stakes}
            results.append(row)
            print(f"  ✗ {cid} [{name}] {field}: committed={_short(a)} draw={_short(b)} ({stakes})")


def _short(v):
    s = json.dumps(v, default=str)
    return s if len(s) <= 56 else s[:53] + "..."


def classify(field, committed_v, draw_v):
    def truthy(v):
        if isinstance(v, dict):
            return bool(v.get("ok", v.get("satisfied")))
        if isinstance(v, str) and v.startswith(("EXC:", "SHAPE:")):
            return False
        if field == "phase":
            return v == "solid"
        return bool(v)
    ct, dt = truthy(committed_v), truthy(draw_v)
    if not ct and dt:
        return "ACCEPTS"
    if ct and not dt:
        return "REFUSES"
    return "SHAPE"


def run_triples(kernels, p, results, mode):
    suffix = "n" if mode == "native" else "i"

    def triple_copies(cid):
        out = {}
        for name, k in kernels.items():
            base = os.path.join(WORK, f"{cid}--{name}")
            os.makedirs(base, exist_ok=True)
            t = {}
            for leg, src in (("m1", p["fx"]), ("m2", p["m2"]), ("m3", p["m3"])):
                d = os.path.join(base, leg)
                shutil.copytree(src, d, symlinks=True)
                t[leg] = d
            if mode == "native":
                for leg in ("m1", "m2", "m3"):
                    ask(k.seal, t[leg])
            out[name] = t
        return out

    def judge_all(cid, klass, copies, mutate=None, extra=None):
        obs = {}
        for name, k in kernels.items():
            t = copies[name]
            if mutate:
                try:
                    mutate(t, k)
                except BaseException as e:  # noqa: BLE001
                    obs[name] = {"setup": f"EXC:{type(e).__name__}"}
                    continue
            obs[name] = judge_triple(k, t["m1"], t["m2"], t["m3"])
            if extra == "freeze":
                obs[name].update(judge_freeze(k, t["m1"], t["m2"], t["m3"]))
        record_divergences(cid, klass, obs, results)
        for name in kernels:
            shutil.rmtree(os.path.join(WORK, f"{cid}--{name}"), ignore_errors=True)

    t = f"t01-honest-triple@{suffix}"
    judge_all(t, "triple", triple_copies(t), extra="freeze")

    t = f"t02-doctored-m2@{suffix}"
    def doctor_m2(tt, k):
        _w(os.path.join(tt["m2"], "reticuli.toml"),
           FIXTURE.replace("a greeting containing the word hello", "any bytes at all"))
        k.seal(tt["m2"])          # resealed under its own (different) claim
    judge_all(t, "triple", triple_copies(t), mutate=doctor_m2)

    t = f"t03-fabricated-m3@{suffix}"
    def fabricate_m3(tt, k):
        _w(os.path.join(tt["m3"], "g.txt"), "fabricated, does not satisfy the gate\n")
    judge_all(t, "triple", triple_copies(t), mutate=fabricate_m3, extra="freeze")

    # distinctness beyond the pinned literal case: a symlink alias of M1 as M2.
    # kernel_check pins only three_machine(m1, m1, m1); the alias is silent.
    t = f"t05-symlink-aliased-m2@{suffix}"
    def alias_m2(tt, k):
        shutil.rmtree(tt["m2"])
        os.symlink(tt["m1"], tt["m2"])
    judge_all(t, "triple", triple_copies(t), mutate=alias_m2)

    # cost bands: the check pins 1.5x comparable and 4x not; the edge is silent.
    for cid, a, b in (("t06a-band-1.5x", 2, 3), ("t06b-band-4x", 1, 4),
                      ("t06c-band-edge-2x", 2, 4), ("t06d-band-edge-3x", 1, 3),
                      ("t06e-band-zero", 0, 3), ("t06f-band-equal", 3, 3)):
        tcid = f"{cid}@{suffix}"
        def set_costs(tt, k, a=a, b=b):
            for leg, calls in (("m1", a), ("m3", b)):
                _w(os.path.join(tt[leg], ".reticuli", "ledger.jsonl"),
                   json.dumps({"event": "oracle", "calls": calls}) + "\n")
        judge_all(tcid, "cost-band", triple_copies(tcid), mutate=set_costs)


def random_cases(kernels, p, results, n, rng):
    """Seeded random byte flips, native mode (semantic focus)."""
    for i in range(n):
        base = p["fx"] if rng.random() < 0.6 else p["sd"]
        files = (["g.txt", "reticuli.toml", ".reticuli/manifest.json"]
                 if base == p["fx"]
                 else ["spec.txt", "impl.txt", "reticuli.toml", ".reticuli/manifest.json"])
        target = rng.choice(files)
        pos = rng.randint(0, 200)
        delta = rng.randint(1, 255)

        def flip(d, k, target=target, pos=pos, delta=delta):
            path = os.path.join(d, target)
            with open(path, "rb") as f:
                raw = bytearray(f.read())
            if not raw:
                return
            j = pos % len(raw)
            raw[j] = (raw[j] + delta) % 256
            with open(path, "wb") as f:
                f.write(raw)
        run_case(kernels, f"r-flip-{i:03d}-{os.path.basename(target)}",
                 base, flip, results, "random-flip", "native")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kernel", nargs="+",
                    help="reference kernel.py first, then one or more draws")
    ap.add_argument("--fixed-only", action="store_true")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--smoke", action="store_true", help="five fixed cases, both modes")
    args = ap.parse_args()
    if len(args.kernel) < 2:
        ap.error("need a reference kernel and at least one draw")
    paths = {"committed": args.kernel[0]}
    for kp in args.kernel[1:]:
        stem = os.path.splitext(os.path.basename(kp))[0]
        while stem in paths:
            stem += "'"
        paths[stem] = kp

    print("loading kernels (first is the reference):")
    kernels = {}
    for name, path in paths.items():
        with open(path, "rb") as f:
            print(f"  {name}: {hashlib.sha256(f.read()).hexdigest()[:12]} {path}")
        kernels[name] = load_kernel(name, path)

    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)
    proto = os.path.join(WORK, "proto")
    p = build_protos(kernels["committed"], proto)
    print("prototypes built (committed kernel is the builder)\n")

    results = []
    fixed = list(fixed_cases(p))
    if args.smoke:
        fixed = fixed[:5]
    for mode in ("interop", "native"):
        for cid, base, setup in fixed:
            print(f"[{mode[0]}] {cid}")
            run_case(kernels, cid, base, setup, results, "structural", mode)
    if not args.smoke:
        for cid, base, setup in mint_cases(p):
            print(f"[n] {cid}")
            run_case(kernels, cid, base, setup, results, "mint", "native")
        run_triples(kernels, p, results, "interop")
        run_triples(kernels, p, results, "native")
        if not args.fixed_only:
            random_cases(kernels, p, results, args.n, random.Random(SEED))

    with open(RESULTS, "w") as f:
        f.writelines(json.dumps(row) + "\n" for row in results)
    shutil.rmtree(WORK, ignore_errors=True)
    print(f"\n{len(results)} divergent observations -> {RESULTS}")
    tally = {}
    for row in results:
        mode = "native" if row["case"].endswith("@n") or row["class"] == "random-flip" else "interop"
        key = (mode, row["stakes"], row["kernel"], row["field"])
        tally[key] = tally.get(key, 0) + 1
    for (mode, stakes, kernel, field), c in sorted(tally.items()):
        print(f"  {mode:8s} {stakes:8s} {kernel:10s} {field:14s} {c}")


if __name__ == "__main__":
    main()
