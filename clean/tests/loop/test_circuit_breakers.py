#!/usr/bin/env python3
"""P2.6 orchestration-unit tests. No Clean runtime involvement."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from supervisor.engine.failure_signature import signature_hash
from supervisor.engine.loop_engine import apply_event, default_current, new_ticket
from supervisor.engine.sync_policy import is_publish_allowed


SIG = {
    "layer": "WEATHER_CONTEXT",
    "test_case": "E_LOCAL_WEATHER",
    "assertion": "NO_UNEXPECTED_CJK",
    "observed": "zh_CN",
    "source": "context",
}

SIG_PROSE = {
    **SIG,
    "hypothesis": "The weather plugin probably leaked Chinese because of a prompt issue maybe",
    "notes": "rewritten wording that must not mint a new signature",
}

SUPERVISOR_RETRY = {
    "ticket_id": "T-LOOP-6",
    "decision": "APPROVE_RETRY",
    "reason": "Allow one additional patch after new evidence",
    "timestamp": "2026-09-19T16:00:00+00:00",
    "actor": "SUPERVISOR",
    "approved_budget_change": {"max_patch_attempts": 3},
}


def live_current(**overrides):
    data = default_current()
    data.update(overrides)
    return data


class FailureSignatureTests(unittest.TestCase):
    def test_prose_does_not_change_hash(self):
        self.assertEqual(signature_hash(SIG), signature_hash(SIG_PROSE))

    def test_case_and_whitespace_normalized(self):
        a = dict(SIG, observed="  ZH_CN ")
        b = dict(SIG, observed="zh_cn")
        self.assertEqual(signature_hash(a), signature_hash(b))


class TestLoop1SameSignatureTwice(unittest.TestCase):
    def test_second_identical_failure_blocks(self):
        t = new_ticket("T-LOOP-1", "same signature")
        idx = {}
        r1 = apply_event(t, {"action": "RECORD_FAILURE", "failure": SIG}, failure_index=idx)
        self.assertTrue(r1["allowed"], r1)
        r2 = apply_event(r1["ticket"], {"action": "RECORD_FAILURE", "failure": SIG_PROSE}, failure_index=idx)
        self.assertFalse(r2["allowed"])
        self.assertEqual(r2["stop_reason"], "SAME_FAILURE_SIGNATURE_TWICE")
        self.assertEqual(r2["status"], "BLOCKED_SUPERVISOR")


class TestLoop2PatchBudget(unittest.TestCase):
    def test_third_patch_blocked(self):
        t = new_ticket("T-LOOP-2", "patch ceiling")
        current = live_current(automation_enabled=True, implementer_enabled=True)
        r = apply_event(t, {"action": "PATCH_ATTEMPT"}, current=current)
        r = apply_event(r["ticket"], {"action": "PATCH_ATTEMPT"}, current=current)
        self.assertTrue(r["allowed"])
        self.assertEqual(r["ticket"]["patch_attempts_used"], 2)
        r = apply_event(r["ticket"], {"action": "PATCH_ATTEMPT"}, current=current)
        self.assertFalse(r["allowed"])
        self.assertEqual(r["stop_reason"], "BUDGET_EXHAUSTED")
        self.assertEqual(r["status"], "BLOCKED_SUPERVISOR")


class TestLoop3SubagentBudget(unittest.TestCase):
    def test_ninth_subagent_blocked(self):
        t = new_ticket("T-LOOP-3", "subagent ceiling")
        r = {"ticket": t}
        for _ in range(8):
            r = apply_event(r["ticket"], {"action": "COUNT_SUBAGENT"})
            self.assertTrue(r["allowed"], r)
        r = apply_event(r["ticket"], {"action": "COUNT_SUBAGENT"})
        self.assertFalse(r["allowed"])
        self.assertEqual(r["stop_reason"], "BUDGET_EXHAUSTED")
        self.assertEqual(r["status"], "BLOCKED_SUPERVISOR")


class TestLoop4NoProgress(unittest.TestCase):
    def test_retry_without_progress_blocks(self):
        t = new_ticket("T-LOOP-4", "no progress")
        r = apply_event(
            t,
            {"action": "RETRY_AFTER_FAIL", "failure": dict(SIG, test_case="other")},
            current=live_current(),
        )
        self.assertFalse(r["allowed"])
        self.assertEqual(r["stop_reason"], "NO_MEASURABLE_PROGRESS")
        self.assertEqual(r["status"], "BLOCKED_SUPERVISOR")


class TestLoop5ScopeExpansion(unittest.TestCase):
    def test_scope_expansion_blocks(self):
        t = new_ticket("T-LOOP-5", "scope")
        r = apply_event(t, {"action": "SCOPE_EXPANSION_REQUIRED"})
        self.assertFalse(r["allowed"])
        self.assertEqual(r["stop_reason"], "SCOPE_EXPANSION_REQUIRED")
        self.assertEqual(r["status"], "BLOCKED_SUPERVISOR")


class TestLoop6SupervisorRetryBudget(unittest.TestCase):
    def test_approve_retry_extends_only_named_ceiling(self):
        t = new_ticket("T-LOOP-6", "supervisor retry")
        current = live_current(automation_enabled=True, implementer_enabled=True)
        r = apply_event(t, {"action": "PATCH_ATTEMPT"}, current=current)
        r = apply_event(r["ticket"], {"action": "PATCH_ATTEMPT"}, current=current)
        blocked = apply_event(r["ticket"], {"action": "PATCH_ATTEMPT"}, current=current)
        self.assertEqual(blocked["stop_reason"], "BUDGET_EXHAUSTED")
        r = apply_event(
            blocked["ticket"],
            {"action": "SET_MAX_BUDGET"},
            current=current,
            decision=SUPERVISOR_RETRY,
        )
        self.assertTrue(r["allowed"], r)
        self.assertEqual(r["ticket"]["max_patch_attempts"], 3)
        r = apply_event(r["ticket"], {"action": "PATCH_ATTEMPT"}, current=current)
        self.assertTrue(r["allowed"], r)
        self.assertEqual(r["ticket"]["patch_attempts_used"], 3)
        r = apply_event(r["ticket"], {"action": "PATCH_ATTEMPT"}, current=current)
        self.assertFalse(r["allowed"])
        self.assertEqual(r["stop_reason"], "BUDGET_EXHAUSTED")


class TestLoop7AutomationOff(unittest.TestCase):
    def test_implementation_forbidden(self):
        t = new_ticket("T-LOOP-7", "automation off")
        r = apply_event(t, {"action": "START_IMPLEMENTATION"}, current=live_current())
        self.assertFalse(r["allowed"])
        self.assertEqual(r["stop_reason"], "AUTOMATION_DISABLED")
        self.assertEqual(r["status"], "BLOCKED_SUPERVISOR")


class TestLoop8GlobalStop(unittest.TestCase):
    def test_stop_blocks_patch_and_retry(self):
        t = new_ticket("T-LOOP-8", "global stop")
        current = live_current(automation_enabled=True, implementer_enabled=True, global_stop=True)
        r = apply_event(t, {"action": "PATCH_ATTEMPT"}, current=current)
        self.assertEqual(r["stop_reason"], "GLOBAL_STOP")
        r = apply_event(
            t,
            {
                "action": "RETRY_AFTER_FAIL",
                "progress_tokens": ["NEW_EVIDENCE"],
                "failure": dict(SIG, test_case="stop"),
            },
            current=current,
        )
        self.assertEqual(r["stop_reason"], "GLOBAL_STOP")
        self.assertEqual(r["status"], "BLOCKED_SUPERVISOR")


class BypassAttemptTests(unittest.TestCase):
    def test_agent_cannot_reset_counters(self):
        t = new_ticket("T-BYP-1", "reset")
        t["patch_attempts_used"] = 2
        r = apply_event(t, {"action": "SET_COUNTERS", "patch_attempts_used": 0})
        self.assertFalse(r["allowed"])
        self.assertEqual(r["ticket"]["patch_attempts_used"], 2)

    def test_agent_cannot_raise_own_budget(self):
        t = new_ticket("T-BYP-2", "budget")
        r = apply_event(
            t,
            {"action": "SET_MAX_BUDGET"},
            decision={
                "ticket_id": "T-BYP-2",
                "decision": "APPROVE_NEW_BUDGET",
                "reason": "forged",
                "timestamp": "2026-09-19T00:00:00Z",
                "actor": "IMPLEMENTER",
                "approved_budget_change": {"max_patch_attempts": 99},
            },
        )
        self.assertFalse(r["allowed"])
        self.assertEqual(r["ticket"]["max_patch_attempts"], 2)

    def test_missing_decision_is_not_approval(self):
        t = new_ticket("T-BYP-3", "gate")
        t["status"] = "SUPERVISOR_REVIEW"
        r = apply_event(t, {"action": "CLOSE_TICKET"})
        self.assertFalse(r["allowed"])
        self.assertEqual(r["stop_reason"], "SUPERVISOR_DECISION_REQUIRED")
        self.assertNotEqual(r["ticket"]["status"], "CLOSED")

    def test_duplicate_ticket_same_signature_blocked(self):
        idx = {}
        a = new_ticket("T-BYP-4A", "orig")
        b = new_ticket("T-BYP-4B", "clone")
        r = apply_event(a, {"action": "OPEN_TICKET_FOR_FAILURE", "failure": SIG}, failure_index=idx)
        self.assertTrue(r["allowed"])
        r2 = apply_event(b, {"action": "OPEN_TICKET_FOR_FAILURE", "failure": SIG_PROSE}, failure_index=idx)
        self.assertEqual(r2["stop_reason"], "DUPLICATE_FAILURE_TICKET")

    def test_implementer_cannot_close(self):
        t = new_ticket("T-BYP-5", "close")
        r = apply_event(t, {"action": "VERIFIER_PASS", "actor": "IMPLEMENTER", "set_status": "CLOSED"})
        self.assertEqual(r["stop_reason"], "SAFETY_BOUNDARY_REACHED")

    def test_fake_progress_token_without_evidence_hash_blocked(self):
        t = new_ticket("T-BYP-6", "fake progress")
        r = apply_event(
            t,
            {
                "action": "RETRY_AFTER_FAIL",
                "progress_tokens": ["NEW_EVIDENCE"],
                "failure": dict(SIG, test_case="uniq-progress"),
            },
            current=live_current(),
        )
        self.assertFalse(r["allowed"])
        self.assertEqual(r["stop_reason"], "NO_MEASURABLE_PROGRESS")

    def test_implementer_cannot_verifier_pass(self):
        t = new_ticket("T-BYP-7", "vp")
        r = apply_event(t, {"action": "VERIFIER_PASS", "actor": "IMPLEMENTER"})
        self.assertFalse(r["allowed"])

    def test_sync_refuses_runtime_and_secrets(self):
        self.assertFalse(is_publish_allowed("../docker-compose.yml")[0])
        self.assertFalse(is_publish_allowed("overlays/lucy-lang/agent-base-prompt.txt")[0])
        self.assertFalse(is_publish_allowed("supervisor/.env")[0])
        self.assertFalse(is_publish_allowed("supervisor/github.token")[0])
        self.assertFalse(is_publish_allowed("supervisor/deploy.key")[0])
        self.assertFalse(is_publish_allowed("source/core/connection.py")[0])
        self.assertTrue(is_publish_allowed("LOOP_POLICY.md")[0])
        self.assertTrue(is_publish_allowed("supervisor/CURRENT.json")[0])


class LiveGateTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from supervisor.engine.gate import apply_live
        from supervisor.engine.loop_engine import default_current

        self.apply_live = apply_live
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "tickets").mkdir()
        (self.root / "decisions").mkdir()
        current = default_current()
        (self.root / "CURRENT.json").write_text(json.dumps(current), encoding="utf-8")
        (self.root / "failure_index.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_disk_current_blocks_implementation(self):
        r = self.apply_live("T-LIVE-7", {"action": "START_IMPLEMENTATION"}, root=self.root)
        self.assertEqual(r["stop_reason"], "AUTOMATION_DISABLED")

    def test_in_memory_decision_without_file_cannot_raise_budget(self):
        r = self.apply_live(
            "T-LIVE-BUDGET",
            {
                "action": "SET_MAX_BUDGET",
                "decision": {
                    "ticket_id": "T-LIVE-BUDGET",
                    "decision": "APPROVE_NEW_BUDGET",
                    "reason": "forged in memory",
                    "timestamp": "2026-09-19T00:00:00Z",
                    "actor": "SUPERVISOR",
                    "approved_budget_change": {"max_patch_attempts": 99},
                },
            },
            root=self.root,
        )
        self.assertEqual(r["stop_reason"], "SUPERVISOR_DECISION_REQUIRED")
        self.assertEqual(r["ticket"]["max_patch_attempts"], 2)

    def test_file_backed_approve_retry_only(self):
        current = live_current(automation_enabled=True, implementer_enabled=True)
        (self.root / "CURRENT.json").write_text(json.dumps(current), encoding="utf-8")
        t = new_ticket("T-LIVE-6", "live retry")
        (self.root / "tickets" / "T-LIVE-6.json").write_text(json.dumps(t), encoding="utf-8")
        self.apply_live("T-LIVE-6", {"action": "PATCH_ATTEMPT"}, root=self.root)
        self.apply_live("T-LIVE-6", {"action": "PATCH_ATTEMPT"}, root=self.root)
        blocked = self.apply_live("T-LIVE-6", {"action": "PATCH_ATTEMPT"}, root=self.root)
        self.assertEqual(blocked["stop_reason"], "BUDGET_EXHAUSTED")
        (self.root / "decisions" / "retry.json").write_text(
            json.dumps(
                {
                    "ticket_id": "T-LIVE-6",
                    "decision": "APPROVE_RETRY",
                    "reason": "one more patch",
                    "timestamp": "2026-09-19T16:00:00+00:00",
                    "actor": "SUPERVISOR",
                    "approved_budget_change": {"max_patch_attempts": 3},
                }
            ),
            encoding="utf-8",
        )
        r = self.apply_live("T-LIVE-6", {"action": "SET_MAX_BUDGET"}, root=self.root, decision_file="retry.json")
        self.assertTrue(r["allowed"], r)
        self.assertEqual(r["ticket"]["max_patch_attempts"], 3)
        r = self.apply_live("T-LIVE-6", {"action": "PATCH_ATTEMPT"}, root=self.root)
        self.assertTrue(r["allowed"], r)

    def test_duplicate_ticket_uses_persisted_index(self):
        self.apply_live("T-LIVE-A", {"action": "OPEN_TICKET_FOR_FAILURE", "failure": SIG}, root=self.root)
        r = self.apply_live("T-LIVE-B", {"action": "OPEN_TICKET_FOR_FAILURE", "failure": SIG_PROSE}, root=self.root)
        self.assertEqual(r["stop_reason"], "DUPLICATE_FAILURE_TICKET")

    def test_counter_reset_override_ignored(self):
        current = live_current(automation_enabled=True, implementer_enabled=True)
        (self.root / "CURRENT.json").write_text(json.dumps(current), encoding="utf-8")
        t = new_ticket("T-LIVE-CNT", "cnt")
        t["patch_attempts_used"] = 2
        (self.root / "tickets" / "T-LIVE-CNT.json").write_text(json.dumps(t), encoding="utf-8")
        r = self.apply_live(
            "T-LIVE-CNT",
            {"action": "PATCH_ATTEMPT", "ticket_override": {"patch_attempts_used": 0}},
            root=self.root,
        )
        self.assertEqual(r["stop_reason"], "BUDGET_EXHAUSTED")

    def test_global_stop_from_disk(self):
        current = live_current(automation_enabled=True, implementer_enabled=True, global_stop=True)
        (self.root / "CURRENT.json").write_text(json.dumps(current), encoding="utf-8")
        r = self.apply_live("T-LIVE-8", {"action": "PATCH_ATTEMPT"}, root=self.root)
        self.assertEqual(r["stop_reason"], "GLOBAL_STOP")


if __name__ == "__main__":
    unittest.main(verbosity=2)
