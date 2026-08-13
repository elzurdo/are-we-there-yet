# Are We There Yet — TODO

Items to bring the app in sync with the published preprint
(Kazin 2026, arXiv:2608.05301).

---

## 1. Rename ePitG → DPitG throughout the codebase

There is an existing `# TODO: rename all ePitG → DPitG` comment in `app.py:144`.
The paper uses **DPitG (Decisive Precision is the Goal)**; the old name was
**ePitG (Enhanced Precision is the Goal)**. These files still use the old name:

### `utils/tutorials.py`

| Location | Current text | Should be |
|----------|-------------|-----------|
| Module docstring (line 4) | `"Tutorial text constants for the ePitG Decision Advisor."` | `"... DPitG Decision Advisor."` |
| `NHST_LIMITATIONS` (line 27) | `"**ePitG combines:**"` | `"**DPitG combines:**"` |
| `MATHS_BINARY_SINGLE_GROUP` (line 65) | `"The ePitG algorithm checks whether the HDI width meets the precision goal..."` | `"The DPitG algorithm checks..."` |
| `MATHS_CONTINUOUS_SINGLE_GROUP` (line 232) | `"The ePitG algorithm ensures both precision (HDI width ≤ Goal) and conclusiveness"` | `"The DPitG algorithm ensures..."` |
| `MATHS_CONTINUOUS_BETWEEN_GROUPS` (line 295) | `"the ePitG algorithm checks whether it's below the precision goal"` | `"the DPitG algorithm checks..."` |
| `BAYES_FACTOR_INTERPRETATION` (line 384) | `"**Key differences from ePitG:**"` | `"**Key differences from DPitG:**"` |

### `utils/decision.py`

- Function `epitg_decision()` → consider renaming to `dpitg_decision()`
- Update the docstring, which refers to "ePitG two-condition stopping rule"
- Update all callers (tabs and tests)

### `CLAUDE.md` (already updated)

- Project overview fixed in this session ✓

---

## 2. Quantitative claims in the About section

The "When is this calculator most useful?" expander is accurate in spirit but contains
no numbers. Consider adding the headline result from the paper:

> At ω_goal = 0.08, DPitG reduces PitG's 62% inconclusive rate to 2% at a median
> cost of only 5% more samples, with zero false positives.

---

## 3. NHST_LIMITATIONS content — minor conceptual gap

`NHST_LIMITATIONS` in `utils/tutorials.py` says (point 3):
> "The ePitG method explicitly plans for a precision goal."

This is true of both PitG and DPitG. The text should clarify that DPitG additionally
requires a conclusive verdict — that is what distinguishes it from plain PitG. Suggested
revision for point 3:

> "Unlike NHST, DPitG plans for a precision goal **and** requires a conclusive verdict
> before stopping — eliminating the high inconclusive rate of plain Precision-is-the-Goal."

---

## 4. Glossary — missing ROPE and HDI entries

`utils/tutorials.py` has a `# TODO: add entries for: ROPE, HDI` comment on line 341.
These are the two most important concepts in the framework; add them:

| Term | Definition | Role |
|------|-----------|------|
| HDI | Highest Density Interval | Shortest credible interval containing the target posterior mass (e.g. 95%). Used as the precision and location metric. |
| ROPE | Region of Practical Equivalence | Pre-specified interval [ROPE_min, ROPE_max] around the null. Effects inside are considered practically equivalent to the null. |

---

## 5. Extensions not yet implemented in the app

The paper's appendices derive (but do not simulate) extensions to:
- Continuous single group (implemented ✓)
- Continuous between groups (implemented ✓)
- Binary between groups (implemented ✓)

The paper notes these are *theoretical derivations*; stopping-property validation
via simulation is future work. Consider adding a note in the relevant tab
tooltips/disclaimers that the validated empirical guarantees are from the
single-group Bernoulli setting.

---

## 6. Fix the ROPE Advisor dialog → sidebar population (in progress, blocked)

**Scope:** Binary single-group only first; once solved, apply the same fix to the other
three cases (binary between-groups, continuous single-group, continuous between-groups).

**Problem:** Opening the 🧭 dialog (`rope_advisor_dialog_binary_single`), filling in
Custom values (Steps 1–3), clicking ✅ Apply, and closing the dialog leaves the
sidebar ROPE width and Precision Goal boxes **empty** — the values never reach the widgets.

**Root cause hypothesis:** `@st.dialog` in Streamlit 1.54 is implemented as a fragment.
Session-state writes made *during* the fragment render are not reliably committed to
global session state across reruns — particularly when `st.rerun()` / `st.rerun(scope="app")`
is called, which interrupts the fragment execution (via exception) before any buffered
writes can be flushed.

**Attempts made (all failed to populate the sidebar boxes):**

| Attempt | What was tried | Outcome |
|---------|---------------|---------|
| A | `_pending_example` staging + `st.rerun()` (original code) | Sidebar stays empty |
| B | Direct widget-key writes + `st.rerun(scope="app")` | Sidebar stays empty |
| C | `on_click` callback writes `_rope_advisor_result` (non-widget key); dialog detects it on fragment rerun and calls `st.rerun(scope="app")`; sidebar flushes before ROPE widgets render | Sidebar stays empty |

**What does work:**  The 📋 Example button (runs in main-app context, not a fragment)
uses the same `_pending_example` + flush pattern and correctly populates the sidebar.

**Next ideas to try:**

- Confirm empirically whether `_rope_advisor_result` even survives the rerun
  (add a temporary `st.write(st.session_state)` debug line in `_sidebar_single_group`).
- Try replacing `@st.dialog` with an inline sidebar expander so there is no fragment
  boundary — values would be set in the main-app context with no rerun needed.
- Try `st.fragment(run_every=None)` alternatives or check Streamlit 1.54 release notes
  for known dialog/session-state interaction bugs.

---

## 7. (Optional) Build a skill for the app

Consider creating a `.claude/skills/run-app.md` skill for the are-we-there-yet repo
that tells Claude Code how to launch and test the Streamlit app (`streamlit run app.py`),
what the golden-path test cases are, and how to verify the DPitG stopping logic
against the paper's hand-picked sequence (N_stop=804, Accept, fair coin experiment).
This would make future AI-assisted development faster and more reliable.
