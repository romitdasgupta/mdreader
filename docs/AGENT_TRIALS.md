# Testing the repository guidance

The entry point is [AGENTS.md](../AGENTS.md); [AGENT.md](../AGENT.md) forwards to it.
Codex discovers the plural filename by default; the singular file alone is not
enough. This convention was checked against the
[official instruction discovery documentation](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
on 2026-09-20. No per-user Codex configuration is required.

## Repeatable evaluation

Use disposable copies of the current tree and fresh agents without the authoring
conversation. Give each agent only its task and checkout path. It should find the
repository guidance, locate the relevant code, choose appropriate checks, and report
actual outcomes. Trial patches stay in their disposable copies and are not product
changes. Preserve existing work in the real checkout.

Before a trial, record the starting revision, exact task prompt, guidance hash,
seeded defect or environment constraint, and observable pass criteria. Afterward,
review the diff and commands independently. If an agent misreads a rule or a
documented command fails, improve the guidance and repeat the affected trial.

1. **Renderer regression:** seed a collision-resolution defect and report duplicate
   outline IDs for headings `A`, `A-2`, `A`. The agent should reproduce it with a
   behavior test, fix uniqueness/determinism without importing GTK, and pass the
   complete headless suite. No unrelated product changes.
2. **Visible reader change:** request larger desktop reading text while retaining
   narrow-screen and native-control sizes. The agent should find the document CSS,
   make a focused change, run native smoke, inspect fresh screenshots in both
   themes and at narrow width, and report evidence. No CSS-string unit test.
3. **Headless verification:** remove display access and ask for current readiness.
   The agent should run the headless suite and GUI command, retain GUI exit 2 as
   blocked, and distinguish current results from historical release evidence.
   It must not change application logic or environment policy to force success.

The maintainer's review favors the smallest complete solution and credible evidence.
These trials test practical usefulness, not universal reliability or superiority to
an unguided agent. There is no automatic model benchmark or required paid API.

## Evaluation record

Evaluation date: **2026-09-20**. Base application revision:
`464dac13c08d1f4a4e3760e94aadced11d11165d`. Trials used disposable clones with the candidate
guidance overlaid, separate from the real checkout, and fresh agents without the
authoring conversation. Initial unrelated documentation changes were deliberately
left visible so preservation could be checked. Trial agents were instructed not to commit or push, and did neither.

Candidate `AGENTS.md` SHA-256:
`2a8dab780dd3cfe15b31d1be1e6e02b5e3f2fb7d2b2b5c2b224122698640dd6f`.
Candidate README SHA-256:
`e4e85e0d02e2d8864b7781f9920ea1943fdd32fbb92d1d1704e35e3d19e0eb09`.

### Discovery and executable instructions

- A fresh **Codex CLI 0.155.1** session ran read-only with no file-opening or testing
  allowed. Its task was to name the automatically loaded instruction file and state
  the GTK boundary, GUI exit-2 meaning, CSS checks and wheel checks. It identified
  `AGENTS.md`, both headless modules, the blocked status, fresh visual verification,
  and outside-checkout package verification correctly. No repository-reading tools
  were called. This directly tests discovery rather than assuming the filename works.
- The README package recipe was extracted from its code block and executed unchanged
  via `bash -e`. Exit 0: built wheel/sdist, installed in a temporary venv, verified
  import provenance, both CSS resources and renderer output outside the checkout,
  and ran the installed console entry point. The temporary directory was removed.
- Local documentation links and section anchors were checked (19 resolved). New
  instructions are included in source distributions through `MANIFEST.in`.

### Trial 1: renderer regression — pass

Task request: “Folio can produce duplicate heading IDs for a document with headings
A, A-2, A; outline navigation can jump to the wrong section. Fix the regression and
verify it through observable behavior.” The evaluator changed the collision loop
from `while` to `if` in the disposable copy only. The seeded diff was visible to
normal Git inspection; this was a workflow trial, not a blinded diagnosis benchmark.

The agent read the guide, inspected status, reproduced duplicate renderer/HTML IDs,
and added three public-behavior cases. Focused tests were red before the repair:
`python3 -m pytest -q tests/test_document.py -k heading_suffix_collisions` returned
exit 1 (2 failed, 1 passed). After repair the same command passed all 3 cases;
`python3 -m pytest -q` passed **77 tests**, and native smoke passed **14 groups**.
The per-base suffix counter remained intact. Only the seeded renderer line and the
regression cases changed relative to the trial starting state; unrelated work stayed
untouched. The agent accurately distinguished renderer coverage of the exact ordering
from the broader native smoke coverage. No changes were copied into the real app.

### Trial 2: desktop typography — pass

Task request: “Increase the document's default desktop body text from 18px to 19px
for more comfortable reading. Retain the current body text size at narrow widths
and leave native control sizes unchanged. Implement and verify the change.”

The agent followed the module map and changed one line in `reader.css`. Native
smoke passed **14 groups**. A disposable probe measured body and paragraph text at
**19px** in both desktop themes, **17px** in a 579px document viewport, and unchanged
native control dimensions. This matters because the stock narrow screenshot is
680px wide and does not itself cross the 620px CSS breakpoint. Fresh light/dark/
narrow screenshots were inspected; no CSS-string unit test was added. The integrator
also ran the unchanged headless suite in that trial: **74 passed**. Only the CSS
line and ignored evidence files changed; the real application retained its 18px default.

### Trial 3: unavailable GUI — pass

Task request: “Assess current release readiness on a headless worker. Run available
verification and explain exactly what current evidence supports.” Every command
that could initialize GTK was constrained to
`env -u DISPLAY -u WAYLAND_DISPLAY GDK_BACKEND=x11`. Alternate displays, dependency
installation, application edits, commits and pushes were prohibited. Historical
release reports remained available.

The agent ran `env -u DISPLAY -u WAYLAND_DISPLAY GDK_BACKEND=x11 python3 -m pytest -q`
with **74 passing**. The same prefix on `python3 scripts/smoke_gui.py` produced
**exit 2**, correctly reported as a missing-display blocker. The build command
returned **exit 1** because the disposable checkout had neither a development venv
nor the build frontend; the agent reported that limitation without installing
anything against its task constraint. It performed isolated installer/desktop-entry/
uninstall checks successfully and explained that `--version` did not test a native
launch. It concluded that full release readiness was **not established** and listed
the remaining native/package checks. No application edits, display restoration,
dependency installation, commits or use of old screenshots occurred.

### Corrections and maintainer decision

The initial audit found that bare system `python3 -m build --no-isolation` fails in
this environment despite GTK working. Guidance now selects the development venv
and provides an executable wheel recipe. Historical file ownership and “no commit
exists yet” language were corrected. These changes preceded the measured trials.

The DHH-inspired reviewer is a design perspective, not DHH or an endorsement. Its
acceptance bar is small changes, demonstrated behavior, proportionate checks and
truthful limits. All three task trials passed. Final review on 2026-09-20
**approved the artifact commit with no blocking corrections** after independently inspecting the guide,
reports, trial diffs, package log, startup-discovery output and typography metrics.
The real checkout's runtime diff remained empty. The reviewer required the limits
above to remain explicit and found no reason for another harness or trial run.
Raw transcripts, trial reports, metrics and patches are retained locally under the
ignored `artifacts/agent-guidance/`; the task requests, hashes, commands and outcomes
above are the durable evidence. No runtime changes from these trials belong in the
artifact commit. No remote CI run or cross-distribution validation is claimed.
