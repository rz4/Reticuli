# Pre-audit data (retired)

These rows were measured **before** the soundness fix that added `audit` to the
three-machine test. That fix re-minted two claim roots:

| layer | pre-audit root | current root |
|---|---|---|
| kernel-core | `af831de0…` | `787c5fcd…` |
| exchange | `63fa5e75…` | `26a1f7a0…` |

So every `kernel-core` and `exchange` landing in `reflection_profile.jsonl`
here was measured against a claim that no longer exists, and none of these rows
carry a `claim_root` stamp. They are kept for the record, not for analysis —
**do not mix them with post-audit data.** The live sweep starts clean and
stamps every row with the root it was measured against, so this can't recur.

The findings the pilot established still hold in shape (negative control 0/6,
positive control 6/6, blind haiku 2/6, blind sonnet 4/6, agentic haiku 6/6 for
~$1) — but the exact per-cell numbers must be re-measured against the current
claim before they go in a paper. That is what the fresh full sweep is for.

`envelope.jsonl` here is the byte-copy control against the same pre-audit roots.
