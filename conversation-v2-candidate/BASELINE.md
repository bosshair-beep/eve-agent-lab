# Baseline record

WORK_ID=EVE_CONVERSATION_CORE_V2_BUILD
V2_WORK_ROOT=conversation-v2-candidate/
INTENDED_DEPLOY_ROOT=/opt/eve/releases/conversation-v2-candidate/  # not created tonight

## Production / live Eve

BASELINE_SOURCE=UNAVAILABLE_IN_THIS_ENVIRONMENT
REASON=Production eve.ai is READ_ONLY. This control repo has no Eve application tree. VPS SSH was not used.

BASELINE_BEHAVIORAL_CONTRACT=mission EVE_CONVERSATION_CORE_V2_BUILD §1 A/B/C
ASR_BASELINE language=vi threshold=0.2 prefix_padding_ms=600 silence_duration_ms=1000

Do not re-interpret historical evidence. Wake/Câm failure chain and current fix are copied from the mission, not from a live re-trace of production files.

## This control repository (at candidate branch time)

Recorded after first commit via `git rev-parse HEAD` on branch `cursor/conversation-v2-candidate-8431`.
The parent `main` commit that was not modified:

CONTROL_REPO_MAIN=79a657e  # P2.8 WS handshake forensic (Clean lab, not Eve production)

Clean P2.7/P2.8 evidence in `clean/` is **Clean XiaoZhi**, not Eve production. It is not used as Eve hashes.

## Hashes of this candidate tree

See `docs/FINAL_REPORT.md` after tests. Compute with:

```bash
find conversation-v2-candidate -type f ! -path '*/__pycache__/*' ! -name '*.egg-info*' -print0 | sort -z | xargs -0 sha256sum
```
