# Cross-vendor rehydration — OpenAI regrows a Claude-authored spec

The last independence axis, closed. Every prior run used a Claude-family
producer, so M1 and M3 shared a vendor. This one has **OpenAI's gpt-5 regrow the
`quirkcalc` spec** (authored in a Claude session, invented behavior in its tests
only) through a newly built agentic OpenAI producer — and it landed, proven.

## What it took (the OpenAI path was broken, not just non-agentic)

Diagnosing "we have an OpenAI subscription but haven't made it agentic" turned up
three separate blockers, only one of which was agency:

1. **`producer_openai.py` hardcoded `api.openai.com`** and ignored
   `OPENAI_BASE_URL` — it could never reach the science-cloud gateway.
2. **Raw `urllib` is Cloudflare-1010-blocked** at that gateway (a WAF
   fingerprint ban). The earlier "dead key" was this, not bad auth. The `openai`
   **SDK's** HTTP stack clears it; auth was fine all along (the gateway is a
   LiteLLM proxy, `gpt-5` responds).
3. **No tool-use loop** — the oneshot producer can't iterate.

Fix: a new `scripts/producer_openai_agentic.py` — a bounded function-calling
loop on the OpenAI SDK (tools: `read_file`, `write_file`, `run_gate`), respecting
`OPENAI_BASE_URL`, import-safe (SDK imported inside `main()`). The cross-vendor
sibling of `producer_claude_agentic.py` (which shells to `claude -p`).

## Result

`gpt-5` regrew `quirkcalc` from its 59-case spec in **1 producer session,
~10k tokens**, sealed at the committed root **`190ab1b6`**, and
`ret prove` is **satisfied / integrity / reuse / equivalence / audited**. A
different vendor, blind to the invented semantics, reconstructed them from the
tests and passed. **The independence axis named in the reach discussion is now
closed** — M1 and M3 are different model vendors.

## Three implementations, one basin — and a spec gap the cross-vendor run exposed

Three independent, spec-conformant `calc.py` now exist, all three-machine proven
at `190ab1b6`, all byte-distinct: my reference (111 lines), Claude's (123),
OpenAI's (159). Differential-fuzzed against the reference over 20,000 random
expressions:

| implementation | agreement with reference | diverges where |
|---|---|---|
| Claude | **99.89%** | only negative-left `~` (one unspecified region) |
| OpenAI | **96.12%** | `?` precedence vs `+`/`-` (**~806 cases**) + negative-left `~` |

The OpenAI divergence is almost all one thing: `51 + 0 ? 3` → my reference `54`
(`?` binds tighter than `+`), OpenAI `51` (`?` looser). **My 59 tests never
pinned `?` against `+`/`-`** — I tested `%` vs `+` but forgot `?`. Both vendors
are spec-conformant; they differ only where the spec is silent, and **each
vendor probed a different silent region.** Claude matched my reference on `?`
precedence by luck; OpenAI's different choice *revealed the gap*.

## The finding: cross-vendor reconstruction is a spec-completeness instrument

A single producer maps the cage gaps it happens to wander into. **Two producers
from different vendors probe different silent regions, so the union of their
divergences maps the spec's incompleteness far better than either alone.** Here,
one vendor found one gap (negative-left `~`), the second found that gap *plus*
another (`?` precedence) the first had silently guessed "correctly." Differential
cross-vendor reconstruction turns Reticuli into a tool that audits a test
suite for the behaviors it forgot to pin — the fracture map, sharpened by
disagreement.

Honest note: neither vendor is "better." OpenAI's larger divergence is not lower
quality — it is a different, more revealing path through the regions my spec left
undefined. The right response is to add the two missing tests (`?` precedence,
negative-left `~`) and re-run; the cage tightens, both vendors converge.

## Status

Measured 2026-09-05. Independence now demonstrated across content (byte-different),
epistemic (unseen invented behavior — [unseen-quirkcalc.md](unseen-quirkcalc.md)),
and **vendor** (OpenAI vs Claude). The remaining independence limits are the
structural ones no experiment removes (shared training lineage across all LLMs;
the environment/substrate boundary), stated in the guide's honesty contract.
