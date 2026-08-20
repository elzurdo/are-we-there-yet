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

N_GOAL_STR = r"$N_{\rm goal}$"
N_TOTAL_STR = r"$N_{\rm total}$"
N_TOTAL_GOAL_STR = r"$N_{\rm total,\, goal}$"

# HTML-safe equivalents for use inside raw HTML blocks (unsafe_allow_html=True)
GOAL_STR_HTML = "ω<sub>goal</sub>"
HDI_WIDTH_STR_HTML = "ω<sub>HDI</sub>"

ROPE_WIDTH_STR = r"$\omega_{\rm ROPE}$"
ROPE_WIDTH_STR_HTML = "ω<sub>ROPE</sub>"
ROPE_HALF_WIDTH_STR = r"$\omega_{\rm ROPE}/2$"

BINARY_SINGLE_PARAMETER_ESTIMATE_STR = r"$\hat{\theta}$"
# BINARY_SINGLE_PARAMETER_ESTIMATE_STR_HTML = "&theta;<sub>hat</sub>"

BINARY_SINGLE_NULL_STR = r"$\theta_{\rm null}$"
BINARY_SINGLE_NULL_STR_HTML = "&theta;<sub>null</sub>"
BINARY_SINGLE_OBSERVE_STR = r"$\hat{\theta}$"


ROPE_MODE_HELP = (
    "ROPE = Region of Practical Equivalence. "
    "Effects inside this band are considered practically equivalent to the null hypothesis. "
    "Choose a symmetric ROPE around the null, or specify explicit min/max bounds."
)

BINARY_SINGLE_MIN_EFFECT_STR = r"$\delta\theta$"
BINARY_SINGLE_MIN_EFFECT_STR_HTML = "δθ"

BINARY_BG_NULL_STR = r"$\Delta_0$"
BINARY_BG_PARAMETER_ESTIMATE_STR = r"$\hat{\Delta}$"

# Continuous null hypothesis
CONTINUOUS_NULL_STR = r"$\mu_{\rm null}$"
CONTINUOUS_BG_NULL_STR = r"$\Delta_0$"

# x-bar constant for use in markdown/info contexts
XBAR_STR = r"$\bar{x}$"


# Helper functions for dynamic LaTeX labels (use in markdown/info/warning contexts)
def theta_label(subscript: str) -> str:
    """LaTeX θ with a roman subscript: theta_label('A') → '$\\theta_{\\rm A}$'"""
    return r"$\theta_{\rm " + subscript + r"}$"

def theta_hat_label(subscript: str) -> str:
    """LaTeX θ̂ with a roman subscript."""
    return r"$\hat{\theta}_{\rm " + subscript + r"}$"

def mu_label(subscript: str) -> str:
    """LaTeX μ with a roman subscript."""
    return r"$\mu_{\rm " + subscript + r"}$"

def xbar_label(subscript: str) -> str:
    """LaTeX x̄ with a roman subscript."""
    return r"$\bar{x}_{\rm " + subscript + r"}$"

def s_label(subscript: str) -> str:
    """LaTeX s with a roman subscript."""
    return r"$s_{\rm " + subscript + r"}$"