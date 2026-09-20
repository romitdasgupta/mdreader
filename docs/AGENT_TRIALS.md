# Testing the repository guidance

The entry point is [AGENTS.md](../AGENTS.md); [AGENT.md](../AGENT.md) forwards to it.
Codex discovers the plural filename by default; the singular file alone is not
enough. This convention was checked against the
[official instruction discovery documentation](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
on 2026-09-20 and rechecked for the public release. No per-user Codex configuration
is required. `AGENT.md` stays a pointer so contributor instructions have one source.

The public-release guidance also covers the Flatpak manifest and runtime,
installed-package provenance, original document paths from the GTK chooser, and
hosted CI results. Test screenshots remain ignored; curated screenshots in
`docs/images/` are published documentation assets.

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
4. **Installed-package release check:** give a fresh agent the current checkout
   and a development interpreter, without the authoring conversation. Ask it to
   verify packaging on a headless worker. It should use the installed-package
   verifier, reject source imports as package evidence, preserve GUI exit 2, and
   distinguish a wheel result from Flatpak runtime and hosted workflow validation.

The maintainer's review favors the smallest complete solution and credible evidence.
These trials test practical usefulness, not universal reliability or superiority to
an unguided agent. There is no automatic model benchmark or required paid API.

## Public-release guidance evaluation

On **2026-09-20**, a fresh agent received a disposable snapshot of the public-release
documentation and a development interpreter, without this release's authoring
conversation. The task was to assess package readiness on a headless worker.
GUI commands had to unset both display variables and select X11; source changes,
alternative displays, network dependency downloads, system installation, commits,
pushes and publication were prohibited. Temporary package environments were allowed.

The tested `AGENTS.md` SHA-256 was
`cfcad0a9637664c1b723da1fca0cd55fcc094fd413e11d50547ab5e3aa3b262d`;
the README SHA-256 was
`091f9a8388c95e880b1562fd6385caa910f9ef641f54df4d73e184ece6c0aaf0`.

From the disposable checkout, the agent ran:

```sh
env -u DISPLAY -u WAYLAND_DISPLAY GDK_BACKEND=x11 PIP_NO_INDEX=1 .venv/bin/python -m pytest -q
env -u DISPLAY -u WAYLAND_DISPLAY GDK_BACKEND=x11 .venv/bin/python scripts/smoke_gui.py
env -u DISPLAY -u WAYLAND_DISPLAY GDK_BACKEND=x11 PIP_NO_INDEX=1 .venv/bin/python scripts/verify_package.py --gui
```

The core suite passed **76 tests**. Source GUI verification returned **2** for the
missing display. The package verifier built the source archive and wheel, installed
into a temporary environment, and passed installed provenance, CSS, renderer and
launcher checks outside the checkout. Its installed GUI check also returned **2**.
The agent correctly separated those successful headless checks from unavailable
GUI, Flatpak, desktop and hosted-release verification; it did not claim release
readiness based on prior reports. The disposable checkout remained clean.

This trial passed its guidance criteria. It validates instruction use and honest
handling of unavailable evidence, not GUI behavior. Actual graphical and consumer
package results are documented separately in [RELEASE.md](RELEASE.md).

## Initial guidance evaluation (historical)

The results below describe the initial guidance revision, not the current release's
test count. Current application verification is recorded in [RELEASE.md](RELEASE.md).

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

All three task trials passed. An independent review on 2026-09-20 inspected the
guide, reports, trial diffs, package log, startup-discovery output and typography
metrics and found no blocking corrections.
The real checkout's runtime diff remained empty. The reviewer required the limits
above to remain explicit and found no reason for another harness or trial run.
Raw transcripts, trial reports, metrics and patches are retained locally under the
ignored `artifacts/agent-guidance/`; the task requests, hashes, commands and outcomes
above are the durable evidence. No runtime changes from these trials belong in the
artifact commit. These historical trials did not establish remote CI or
cross-distribution validation.
