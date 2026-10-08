---
name: ai-docs
description: Use when creating or updating GitHub-facing Markdown documentation (README, CONTRIBUTING, CHANGELOG) in this or any project. Defines the documentation standard: lean required sections, zero empty sections, optional sections commented out, badges only when true, English-only, and small legible Mermaid diagrams.
---

# ai-docs — GitHub documentation standard

Standard for GitHub-facing Markdown documentation, built around one rule:
a document must never contain empty or placeholder sections.

## Workflow

1. Copy `README-TEMPLATE.md` (same folder as this skill) to the target as
   `README.md`.
2. Replace every `<...>` placeholder with real content.
3. Delete any base section that does not apply (e.g. no Installation in a
   config-only repo). Never leave a section empty or with `...`.
4. Uncomment optional sections only when they have real content.
5. Keep badges commented unless the fact they claim is true (a LICENSE file
   exists, releases exist).
6. Verify: links point to real targets, index anchors resolve on the target
   platform, and every Mermaid block renders.

## Rules

- All docs are written in English. For another language, add
  `README.<lang>.md` and document the exception in AGENTS.md first.
- No index for short READMEs (roughly under 15 sections). For long ones,
  verify anchors: accented or non-ASCII anchors do not resolve everywhere.
- One summary only: the blockquote under the title. Do not duplicate it in a
  Description/Overview section.
- Badges are claims: add one only when the underlying file or release exists.
- Sections:
  - Base (delete if not applicable): Requirements, Installation, Usage,
    License.
  - Optional (commented, enable only when useful): Demo, Features,
    Architecture, Configuration, Project structure, Tests, Technologies,
    Project status, Roadmap, Contributing, Contact.
- Contact is unnecessary by default; GitHub Issues already provides a
  channel.
- Contributing moves to `CONTRIBUTING.md` once it grows beyond a few lines.

## Diagrams (Mermaid)

Use Mermaid when relationships or flow are genuinely non-obvious: architecture
and components; behavior (how a feature, pipeline, or function works); states;
and data models. Never diagram what plain text already explains, and never
mirror the folder tree.

Legibility rules:
- One idea per diagram; if it needs a paragraph to explain, split it or raise
  the abstraction level.
- Hard caps: <= 15 nodes, <= 20 edges, <= 3 diagrams per document. A
  high-level overview stays around 5-9 nodes. If the real system does not fit,
  split by concern or show only the high-level view.
- Labels: <= 5 words, no sentences. Quote labels containing punctuation:
  `A["API (v2)"]`.
- Prefer widely supported types: flowchart/graph, sequenceDiagram,
  stateDiagram-v2, erDiagram. Use flowchart LR for flows and TD for
  hierarchies; subgraphs at most 2 levels deep.
- Use the default theme: GitHub renders light and dark backgrounds. Do not add
  classDef or colors unless color encodes meaning.
- Fence blocks exactly as ` ```mermaid ` and add a one-line caption before or
  after.
- Keep diagrams conceptual, not line-by-line: detailed diagrams go stale fast;
  update them when behavior changes.
- Placement: README shows the project-level view (at most one high-level
  how-it-works diagram); function-level flows belong in `docs/<topic>.md`
  next to the module they describe.
- Verify the diagram renders (GitHub preview or mermaid.live) before
  committing.
