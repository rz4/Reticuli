"""Exchange conformance gate — the seed of the `exchange` layer.

Records meeting records — and other parties: the registry (drawers,
content-addressed component links, DAG-aware rehydrate), transfer
(deterministic tar, verify-on-import, volatile history stays home), and
attestation (a keyholder's signed statement of a realization: signs only
records whose verdicts reproduce from their own bytes — never a carried
verdict — refuses tampered statements, anchors identity to allowed signers).
Layers on kernel-core; knows nothing of authoring or the CLI. Writes
EXCHANGE_OK iff the layer conforms. Stdlib only, so it runs in any clean room.
"""
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

sys.path.insert(0, ".")
from reticuli import attest, kernel, registry, transfer

LIB = '''[record]
name = "lib"

[[step]]
kind = "gate"
output = "lib.txt"
run = "printf LIBDATA > lib.txt"
class = "validated"
'''

APP = '''[record]
name = "app"
inputs = ["dep.txt"]

[[step]]
kind = "produce"
output = "app.txt"
request = "any note"
class = "free"

[[step]]
kind = "gate"
output = "V"
run = "grep -qi implementation app.txt && grep -q LIBDATA dep.txt && printf ok > V"
class = "validated"
'''


def _write(d: str, files: dict) -> None:
    os.makedirs(d, exist_ok=True)
    for name, content in files.items():
        with open(os.path.join(d, name), "w") as f:
            f.write(content)


def battery() -> None:
    d = tempfile.mkdtemp()
    try:
        ws = os.path.join(d, "ws")
        lib = os.path.join(ws, ".reticuli", "liquid", "lib")
        _write(lib, {"reticuli.toml": LIB, "lib.txt": "LIBDATA"})
        kernel.seal(lib)

        # a dry seed that content-matches a record's output is a dependency
        _write(ws, {"dep.txt": "LIBDATA"})
        links = registry.detect_components(ws, ["dep.txt"])
        assert any(x["component"] == "lib" for x in links), "content-addressed link"

        app = os.path.join(ws, ".reticuli", "liquid", "app")
        _write(app, {"reticuli.toml": APP, "dep.txt": "LIBDATA",
                     "app.txt": "one implementation\n", "V": "ok"})
        kernel.seal(app, components=links)
        names = {r["name"] for r in registry.records(ws)}
        assert names == {"app", "lib"}, "the drawer"
        edges = registry.deps(ws)["records"]
        assert any(e["status"] == "ok" for n in edges for e in n["depends_on"]), "the DAG"

        # DAG-aware rehydrate: the chain reproduces from the leaves
        m3 = os.path.join(d, "m3")
        out = registry.rehydrate(app, "printf 'another implementation' > app.txt", m3, ws=ws)
        assert out["root"] == kernel.verify(app)["root"], "chain reproduces"
        assert any(c["component"] == "lib" for c in out["rehydrated_components"]), "leaf first"
        # a rehydrated record must keep its provenance: the manifest carries the
        # component links it was rebuilt from (else `ret tree` on a redo is blind)
        assert kernel.read_manifest(m3).get("components"), "rehydrate preserves provenance"

        # pull: a record becomes a dependency of a fresh session
        ws2 = os.path.join(d, "ws2")
        os.makedirs(ws2)
        pulled = registry.pull(app, ws2)
        assert pulled["materialized"] and os.path.isfile(os.path.join(ws2, "V")), "pull"

        # transfer: deterministic tar, verify-on-import, ledger stays home
        tar_path = os.path.join(d, "m3.tar")
        transfer.export(m3, tar_path)
        with tarfile.open(tar_path) as t:
            assert ".reticuli/ledger.jsonl" not in t.getnames(), "events don't travel"
        back = transfer.import_(tar_path, os.path.join(d, "back"))
        assert back["ok"] and back["root"] == out["root"], "identity travels"

        # declared content ONLY: a stray file dropped in the record's directory
        # must not ride along, and two exports of one record are byte-identical.
        # (An export that walks the tree instead of the recipe leaks the room.)
        with open(os.path.join(m3, "stray-residue.txt"), "w") as f:
            f.write("laptop junk that is not part of the claim\n")
        leak_tar = os.path.join(d, "leak.tar")
        transfer.export(m3, leak_tar)
        with tarfile.open(leak_tar) as t:
            assert "stray-residue.txt" not in t.getnames(), "undeclared bytes must not travel"
        det_tar = os.path.join(d, "det.tar")
        transfer.export(m3, det_tar)
        assert kernel._hf(leak_tar) == kernel._hf(det_tar), "export is byte-deterministic"
        os.remove(os.path.join(m3, "stray-residue.txt"))

        # attestation: a signed statement of this realization, for other parties
        key = os.path.join(d, "key")
        subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-q", "-f", key], check=True)
        a = attest.attest(m3, key, "checker@basin")
        assert os.path.isfile(os.path.join(m3, a["signature"])), "signed"
        assert attest.check(m3)["ok"], "intact and naming this root"
        # an attestation is residue ABOUT the claim that travels WITH it
        att_tar = os.path.join(d, "attested.tar")
        transfer.export(m3, att_tar)
        with tarfile.open(att_tar) as t:
            assert any(n.startswith(".reticuli/attest/") for n in t.getnames()), \
                "attestations travel with the record"
        signers = os.path.join(d, "allowed_signers")
        with open(key + ".pub") as f:
            keytype, blob = f.read().split()[:2]
        with open(signers, "w") as f:
            f.write(f"checker@basin {keytype} {blob}\n")
        checked = attest.check(m3, signers)
        assert checked["ok"] and checked["attestations"][0]["verdict"] == "signed", "identity anchored"
        # an attestation speaks for a REALIZATION, not just a claim: a free redo
        # after signing keeps the root (that freedom is the basin) but is a
        # different realization — the signed output hashes no longer match the
        # disk, and the old attestation must refuse. Restore the exact bytes
        # and it holds again.
        with open(os.path.join(m3, "app.txt")) as f:
            app_bytes = f.read()
        with open(os.path.join(m3, "app.txt"), "w") as f:
            f.write("a drifted implementation\n")
        drifted = attest.check(m3)
        assert not drifted["ok"] and drifted["attestations"][0]["drifted"], \
            "a drifted realization refuses the old attestation"
        with open(os.path.join(m3, "app.txt"), "w") as f:
            f.write(app_bytes)
        assert attest.check(m3)["ok"], "the frozen bytes restored, the attestation holds"
        st_path = os.path.join(m3, a["statement"])
        with open(st_path, "a") as f:
            f.write("\n")                                        # tamper the statement
        assert not attest.check(m3, signers)["ok"], "a tampered statement refuses"
        imported = os.path.join(d, "back")
        with open(os.path.join(imported, "app.txt"), "w") as f:
            f.write("no longer satisfies the gate\n")            # free bytes: root still fresh
        assert kernel.verify(imported)["ok"], "identity survives a free tamper"
        try:
            attest.attest(imported, key, "checker@basin")
            raise AssertionError("attest must never notarize a carried verdict")
        except kernel.ReticuliError:
            pass
        with open(os.path.join(imported, "V"), "w") as f:
            f.write("tampered")                                  # and a broken pin refuses too
        try:
            attest.attest(imported, key, "checker@basin")
            raise AssertionError("attest must refuse a broken record")
        except kernel.ReticuliError:
            pass

        # the mint chain: solid identity folds bottom-up over the DAG, and
        # localizes — a change at a rung moves its mint and every mint above,
        # never one below (the lowest mint that moves names the floor).
        lib_m = registry.mint_root(lib, ws)
        app_m = registry.mint_root(app, ws)
        assert app_m == kernel.mint_node(kernel.verify(app)["root"],
                                         kernel.realization_digest(app), [lib_m]), \
            "app's mint folds lib's mint (bottom-up)"
        with open(os.path.join(app, "app.txt"), "w") as f:
            f.write("one implementation, differently\n")          # a free redo of app
        assert registry.mint_root(app, ws) != app_m, "editing a rung's crystal moves its mint"
        assert registry.mint_root(lib, ws) == lib_m, "the floor's mint held (localization)"
        # a chain root over an incomplete DAG is not a chain root: a declared
        # component missing from the registry must refuse the fold, not elide.
        lib_aside = os.path.join(d, "lib-aside")
        shutil.move(lib, lib_aside)
        try:
            registry.mint_root(app, ws)
            raise AssertionError("mint_root must refuse a missing declared component")
        except kernel.ReticuliError:
            pass
        shutil.move(lib_aside, lib)
        assert registry.mint_root(lib, ws) == lib_m, "restored, the fold holds again"

        # the mint ceremony: accountable authorization over the chain. Refuses a
        # record whose verdicts do not reproduce (audit), signs the chain root and
        # the review packet, and verifies against a recomputed chain.
        mm = os.path.join(d, "mm")                                 # a fresh, clean realization
        registry.rehydrate(app, "printf 'yet another implementation' > app.txt", mm, ws=ws)
        pkt = attest.review_packet(mm, ws=ws)
        assert pkt["mint"] and pkt["root"] and pkt["audit"]["ok"], "the review packet is assembled"
        assert "proof" in pkt, "the packet carries proof status — the reviewer sees the ladder"
        minted = attest.mint(mm, key, "checker@basin", ws=ws)
        assert minted["ceremony"] == "RETICULI_CLAIM_BASIN_V1", "the ceremony is named"
        assert os.path.isfile(os.path.join(mm, minted["signature"])), "the mint is signed"
        assert attest.mint_check(mm, ws=ws)["ok"], "the mint verifies (chain recomputes, signature intact)"
        checked = attest.mint_check(mm, ws=ws, signers=signers)
        assert checked["authorizations"][0]["verdict"] == "authorized", "authorizer identity anchored"
        row = checked["authorizations"][0]
        assert row["packet_holds"], "the signed digest binds the stored review packet"
        assert row["proven"] is False, \
            "the statement says whether a three-machine proof existed (none here) — " \
            "authorization must never be mistaken for proof"
        assert kernel.phase(mm) == "solid", "a verifiable authorization is what solid means"
        # the packet is what the keyholder reviewed: swap it or delete it and
        # the mint must refuse — and the record is no longer solid.
        ppath = os.path.join(mm, minted["packet"])
        with open(ppath) as f:
            packet_bytes = f.read()
        with open(ppath, "w") as f:
            f.write('{"audit": {"ok": true}, "note": "forged after the ceremony"}\n')
        assert not attest.mint_check(mm, ws=ws)["ok"], "a forged review packet refuses"
        assert kernel.phase(mm) == "liquid", "and demotes: the reviewed bundle is gone"
        os.remove(ppath)
        assert not attest.mint_check(mm, ws=ws)["ok"], "a missing review packet refuses"
        with open(ppath, "w") as f:
            f.write(packet_bytes)
        assert attest.mint_check(mm, ws=ws)["ok"], "the exact packet restored, the mint holds"
        with open(os.path.join(mm, minted["statement"]), "a") as f:
            f.write("\n")                                          # tamper the mint statement
        assert not attest.mint_check(mm, ws=ws, signers=signers)["ok"], "a tampered mint refuses"
        broke = os.path.join(d, "broke")
        registry.rehydrate(app, "printf 'a broken implementation' > app.txt", broke, ws=ws)
        with open(os.path.join(broke, "V"), "w") as f:
            f.write("carried, not earned")
        try:
            attest.mint(broke, key, "checker@basin", ws=ws)
            raise AssertionError("mint must refuse a record whose verdicts do not reproduce")
        except kernel.ReticuliError:
            pass

        # the registry reports phase from the verifiable state, never from a
        # manifest bit: injecting "proof" into a drawer record's manifest must
        # not surface it as solid anywhere (records, deps, anatomy).
        forged = kernel.read_manifest(app)
        forged["proof"] = {"kind": "three-machine", "m2": "forged", "m3": "forged"}
        with open(os.path.join(app, kernel.STORE, "manifest.json"), "w") as f:
            json.dump(forged, f)
        assert all(r["phase"] == "liquid" for r in registry.records(ws)), \
            "an injected proof must not surface as solid in the registry"
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    battery()
    with open("EXCHANGE_OK", "w") as f:
        f.write("exchange-ok\n")
    print("exchange-ok")
