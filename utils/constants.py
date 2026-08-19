# ── Preprint / citation metadata ─────────────────────────────────────────────
PREPRINT_URL = "https://arxiv.org/abs/2608.05301"
PREPRINT_YEAR = "2026"
PREPRINT_AUTHOR_SHORT = "Kazin"
PREPRINT_AUTHOR_FULL = "Eyal A. Kazin"
PREPRINT_TITLE = "Precision and Decisiveness as Goals: Reliable Sequential Hypothesis Testing with a Dual Stopping Criterion"
PREPRINT_ARXIV_ID = "2608.05301"

PREPRINT_CITE_INLINE = f"{PREPRINT_AUTHOR_SHORT} (preprint, {PREPRINT_YEAR})"
PREPRINT_APA = (
    f"{PREPRINT_AUTHOR_FULL} ({PREPRINT_YEAR}). *{PREPRINT_TITLE}*. "
    f"arXiv preprint arXiv:{PREPRINT_ARXIV_ID}. {PREPRINT_URL}"
)
PREPRINT_BIBTEX = f"""@misc{{{PREPRINT_AUTHOR_SHORT.lower()}{PREPRINT_YEAR}dpitg,
  author  = {{{PREPRINT_AUTHOR_FULL}}},
  title   = {{{{{PREPRINT_TITLE}}}}},
  year    = {{{PREPRINT_YEAR}}},
  note    = {{Preprint}},
  eprint  = {{{PREPRINT_ARXIV_ID}}},
  archivePrefix = {{arXiv}},
  url     = {{{PREPRINT_URL}}}
}}"""

GOAL_STR = r"$\omega_{\rm goal}$"
HDI_WIDTH_STR = r"$\omega_{\rm HDI}$"

# HTML-safe equivalents for use inside raw HTML blocks (unsafe_allow_html=True)
GOAL_STR_HTML = "ω<sub>goal</sub>"
HDI_WIDTH_STR_HTML = "ω<sub>HDI</sub>"

ROPE_WIDTH_STR = r"$\Delta_{\rm ROPE}$"
ROPE_WIDTH_STR_HTML = "Δ<sub>ROPE</sub>"

BINARY_SINGLE_PARAMETER_ESTIMATE_STR = r"$\hat{\theta}$"
# BINARY_SINGLE_PARAMETER_ESTIMATE_STR_HTML = "&theta;<sub>hat</sub>"

BINARY_SINGLE_NULL_STR = r"$\theta_{\rm null}$"
BINARY_SINGLE_NULL_STR_HTML = "&theta;<sub>null</sub>"
BINARY_SINGLE_OBSERVE_STR = r"$\hat{\theta}$"


BINARY_SINGLE_MIN_EFFECT_STR = r"$\delta\theta$"
BINARY_SINGLE_MIN_EFFECT_STR_HTML = "δθ"

BINARY_BG_NULL_STR = r"$\delta_0$"
BINARY_BG_PARAMETER_ESTIMATE_STR = r"$\hat{\delta}$"