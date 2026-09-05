# Reticuli skill suite

Skills that teach an agent to drive `ret` (Reticuli) in this repo. Each is
self-contained and operational; `docs/guide.md` is the deep reference.

| skill | when it fires | verbs |
|---|---|---|
| **reticuli-record** | you finished work and want it sealed as a verifiable claim | init · hooks · status · run · condense · verify |
| **reticuli-verify** | check a record reproduces and is sound (three-machine test) | export · import · audit · realize · prove |
| **reticuli-pack** | turn any codebase (yours or external) into a claim and regrow it from its spec | pack · realize --recursive · tree · records · pull |
| **reticuli-mint** | a record is ready to authorize, or you're checking authorizations | mint (no key) · attest --check · mint --check |

The one boundary that spans all of them: **an agent authors, verifies, and
prepares — it never signs.** The `--key` mint/attest step is the human
keyholder's act. See **reticuli-mint**.
