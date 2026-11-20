"""Offline evidence rules for the OpenCode compatibility probe."""

import json
import unittest

from tools.ai_fidelity import opencode_probe as probe
from tools.ai_fidelity.run import FidelityError


def listing():
    return (f"<available_skills><skill><id>{probe.SKILL}</id><name>{probe.SKILL}</name>"
            f"<description>{probe.DESCRIPTION}</description></skill></available_skills>")


class OpenCodeProbeTests(unittest.TestCase):
    def test_only_instruction_messages_provide_listing_evidence(self):
        fixture_listing = listing()
        self.assertIsNone(probe._wire_listing([{"role": "user", "content": fixture_listing}]))
        messages = [{"role": "system", "content": [{"type": "text", "text": fixture_listing}]}]
        self.assertEqual(probe._wire_listing(messages), (probe.SKILL, probe.SKILL, probe.DESCRIPTION))

    def test_ambiguous_or_partially_parsed_listing_is_refused(self):
        fixture_listing = listing()
        for text in (fixture_listing * 2, fixture_listing.replace("</skill>", "</skill> unexpected")):
            with self.subTest(text=text), self.assertRaises(ValueError):
                probe._wire_listing([{"role": "system", "content": text}])

    def test_skill_is_requested_before_tool_result_only(self):
        message = {"role": "system", "content": listing()}
        request = {"messages": [message], "tools": [{"function": {"name": "skill"}}]}
        delta, status, observation = probe._delta(request)
        self.assertEqual(status, "tool_calls")
        self.assertEqual(json.loads(delta["tool_calls"][0]["function"]["arguments"]), {"id": probe.SKILL})
        self.assertTrue(observation["called_skill"])
        request["messages"].append({"role": "user", "content": probe.BODY_MARKER})
        self.assertFalse(probe._delta(request)[2]["received_body"])
        request["messages"].append({"role": "tool", "content": probe.BODY_MARKER})
        _, status, observation = probe._delta(request)
        self.assertEqual(status, "stop")
        self.assertTrue(observation["received_body"])
        self.assertFalse(observation["called_skill"])

    def test_completed_event_and_final_stop_are_required(self):
        def parse(*events):
            return probe._completed_skill_count("\n".join(map(json.dumps, events)).encode("utf-8"))

        state = {"status": "completed", "input": {"id": probe.SKILL}}
        called = {"type": "tool_use", "part": {"tool": "skill", "state": state}}
        finished = {"type": "step_finish", "part": {"reason": "stop"}}
        self.assertEqual(parse(called, finished), 1)
        for events in ((), (finished,), (called,), (called, called, finished),
                       (called, {"type": "error"}, finished),
                       (called, {"type": "step_finish", "part": {"reason": "length"}})):
            with self.subTest(events=events), self.assertRaises(FidelityError):
                parse(*events)
        state["status"] = "error"
        with self.assertRaises(FidelityError):
            parse(called, finished)
