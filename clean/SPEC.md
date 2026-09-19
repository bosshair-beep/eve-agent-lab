# CLEAN_VI_MIGRATION — spec (bootstrap)

## Goal (later)

Closed-loop Vietnamese migration of Clean XiaoZhi language surfaces. **Not started in this phase.**

## Non-goals (this phase)

- No translation
- No prompt rewrite
- No provider/credential change
- No deploy / restart / DB write
- No Eve production work
- No firmware / COM ports

## Live sources of truth

1. Process: Docker container `xz-clean-server`
2. Prompt: `overlays/lucy-lang/agent-base-prompt.txt` (sha must match in-container file)
3. Other live overlays currently bind-mounted into the container (compose): ASR realtime modules, `prompt_manager.py`, `connection.py`
4. Image code under `/opt/xiaozhi-esp32-server/` inside the container for everything not overlaid

## Evidence standard

- FACT: observed file:line, mount, hash, or live introspection
- STRONG_INFERENCE: consistent with multiple facts, not directly executed
- HYPOTHESIS: unproven

Prompt text is **not** evidence of registered tools.

## Workflow

MANAGER → AUDITOR  
MANAGER → VERIFIER (independent)  
MANAGER compares; on disagreement, re-investigate with runtime evidence.  
Later: AUDITOR → IMPLEMENTER → VERIFIER; FAIL returns to AUDITOR.
