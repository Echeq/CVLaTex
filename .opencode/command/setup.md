---
description: Interactive init — picks the project default model and subagent depth, writes opencode.json. Also triggered by typing --init.
agent: build
---

You are the interactive project setup for Atelier. Follow these steps exactly.

1. Check if `opencode.json` exists in the project root.
   - If it exists, warn: "⚠️ opencode.json already exists. Back it up first. Type `continue` to overwrite or `cancel` to abort."
   - Wait for the user's answer. If `cancel`, stop. Only proceed on `continue`.
2. Verify `.opencode/agents/evaluator-optimizer.md`, `.opencode/agents/planner.md`, and `.opencode/agents/orchestrator.md` exist. If any is missing, tell the user and stop.
3. Detect your own model ID from your system prompt ("You are powered by the model named X. The exact model ID is Y"). This model is guaranteed available — always include it as the recommended option.
4. Ask the user one question (question tool, single question) for the project default model:
   - Detected model (recommended) — the exact model ID from step 3
   - DeepSeek V4 Pro — `opencode-go/deepseek-v4-pro`
   - DeepSeek V4 Flash — `opencode-go/deepseek-v4-flash`
   - DeepSeek V4 Flash Free — `opencode/deepseek-v4-flash-free`
   - Custom — allow a free-form model ID
5. Ask a second question (question tool) for the subagent nesting depth (`subagent_depth`):
   - 1 (default) — subagents cannot launch subagents; the planner → orchestrator → worker pipeline will not work. Lowest consumption.
   - 2 — enables one nesting level so the orchestrator can dispatch workers.
   - Custom — free-form integer >= 0; each extra level multiplies consumption.
   If the answer is 2 or a custom value greater than 1, show this warning explicitly: "⚠️ Depth <n> enables nested subagents. Consumption will be higher: each orchestrator run spawns multiple worker calls plus the final evaluation gate."
6. Write `opencode.json` in the project root with exactly:
   {
     "$schema": "https://opencode.ai/config.json",
     "model": "<chosen model ID>",
     "subagent_depth": <chosen depth integer>
   }
7. Validate the written file is parseable JSON (read it back and parse it). If parsing fails, fix it before continuing.
8. Confirm: "Atelier is ready. Default model: <id>. subagent_depth: <n>. Restart opencode for the changes to take effect, then run /smoke to verify the agent pipeline."
