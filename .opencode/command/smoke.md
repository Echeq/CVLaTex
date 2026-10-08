---
description: Smoke test for the agent pipeline — runs planner then orchestrator on a synthetic task and validates both JSON contracts. Run after restarting opencode or changing agents.
agent: build
---

Run the pipeline smoke test. Execute the steps exactly, then report a PASS/FAIL
table. Never fix or edit outputs — report failures with raw JSON.

1. Verify these files exist (Read or Glob):
   - `.opencode/agents/evaluator-optimizer.md`
   - `.opencode/agents/planner.md`
   - `.opencode/agents/orchestrator.md`
   If any is missing, report FAIL and stop: agent changes only load after
   restarting opencode.

2. Invoke the planner subagent via the Task tool (`subagent_type: "planner"`)
   with exactly:
   TASK: Write a two-line story about a lighthouse (t1). Translate that story to Spanish (t2, depends on t1). Count the words in the original story (t3, depends on t1).
   Do not add CONTEXT or CONSTRAINTS.

3. Parse the planner output as strict JSON and check each item:
   - parses, with no surrounding prose or fences
   - schema_version == "1"
   - needs_clarification == false and subtasks is a non-empty list
   - ids unique; every depends_on references an existing id; acyclic
   - every subtask has non-empty title, description, and expected_output
   Record PASS/FAIL per check; on FAIL, show the raw output.

4. Invoke the orchestrator subagent via the Task tool
   (`subagent_type: "orchestrator"`) with:
   PLAN: <the planner JSON verbatim>
   AVAILABLE_AGENTS: worker, evaluator-optimizer

5. Parse the orchestrator output as strict JSON and check each item:
   - parses, with no surrounding prose or fences
   - schema_version == "1"; status in completed|partial|failed|invalid_plan
   - one subtask entry per plan subtask, status in
     completed|failed|skipped
   - at least one subtask completed with `agent == "worker"` (proves dispatch
     and the worker contract); every completed subtask has attempts >= 1 and
     non-empty output
   - final_output non-empty when status != "invalid_plan"
   - evaluation.performed == true (the gate ran)
   Record PASS/FAIL per check; on FAIL, show the raw output.

6. Report: compact table (check -> PASS/FAIL) and an overall PASS only if all
   checks pass. Also state that each run consumes several model calls and that
   the smoke test is structural, not deterministic.
