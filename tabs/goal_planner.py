"""
Goal Planner — Interactive tool for determining precision goals.

Helps users understand how to choose appropriate precision goals and ROPE
widths based on their domain and use case, with scenario-based presets
and live visualizations.

Main area: scenario selector, parameters, visualization, sample size estimator
"""
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import beta, norm, t as student_t

from utils.stats import CI_FRACTION


# ══════════════════════════════════════════════════════════════
# Scenario Presets
# ══════════════════════════════════════════════════════════════

SCENARIOS = {
    "political_polling": {
        "name": "📊 Political Polling",
        "description": "Pre-election poll comparing two candidates",
        "variable_type": "Binary",
        "analysis_mode": "Between Groups",
        "effect_of_interest": 0.05,
        "rope_width": 0.06,
        "precision_goal": 0.04,
        "null_value": 0.0,
        "rationale": """
**Context:** Pre-election poll, Candidate A vs B
- **Effect of interest:** 5% lead (meaningful margin)
- **ROPE:** ±3% (statistical tie, within margin of error)
- **Goal:** 2% (tighter than ROPE to confidently call a lead)
- **Why it matters:** Media calls races; wrong call damages credibility. 
  A 5% lead with ±2% precision means you can confidently report "Candidate A leads."
        """,
    },
    "ab_testing": {
        "name": "🛒 A/B Testing (E-commerce)",
        "description": "New checkout flow vs old, measuring conversion rate lift",
        "variable_type": "Binary",
        "analysis_mode": "Between Groups",
        "effect_of_interest": 0.008,
        "rope_width": 0.01,
        "precision_goal": 0.006,
        "null_value": 0.0,
        "rationale": """
**Context:** New checkout flow vs old
- **Effect of interest:** 0.8% absolute conversion lift
- **ROPE:** ±0.5% (not worth engineering cost to implement)
- **Goal:** 0.3% (narrow enough to detect 0.6%+ lifts)
- **Why it matters:** At scale (1M visitors/month), 0.5% lift = $1M+ annual revenue.
  But implementing new flow costs dev time, so you need to be sure the lift is real.
        """,
    },
    "clinical_trial": {
        "name": "💊 Clinical Trial (Blood Pressure)",
        "description": "New drug vs placebo, measuring systolic BP reduction (mmHg)",
        "variable_type": "Continuous",
        "analysis_mode": "Between Groups",
        "effect_of_interest": 5.0,
        "rope_width": 4.0,
        "precision_goal": 3.0,
        "null_value": 0.0,
        "rationale": """
**Context:** New drug vs placebo, systolic BP reduction
- **Effect of interest:** 5 mmHg reduction (clinically meaningful per AHA)
- **ROPE:** ±2 mmHg (too small to change clinical practice)
- **Goal:** 1.5 mmHg (tight enough to detect 3+ mmHg effects)
- **Why it matters:** FDA approval requires demonstrable benefit. 
  Underpowered trial wastes years + $100M. Too wide precision = inconclusive result.
        """,
    },
    "quality_control": {
        "name": "🏭 Quality Control (Manufacturing)",
        "description": "Production line defect rate monitoring",
        "variable_type": "Binary",
        "analysis_mode": "Single Group",
        "effect_of_interest": 0.01,
        "rope_width": 0.02,
        "precision_goal": 0.015,
        "null_value": 0.02,
        "rationale": """
**Context:** Production line, acceptable defect rate is 2%
- **Effect of interest:** 1% deviation (triggers investigation)
- **ROPE:** [0.5%, 3.5%] around 2% spec (within tolerance)
- **Goal:** 0.75% (detect departures from 2% quickly)
- **Why it matters:** Catching drift early prevents costly recalls. 
  Wide HDI means you won't notice problems until hundreds of defective units shipped.
        """,
    },
    "customer_satisfaction": {
        "name": "😊 Customer Satisfaction (NPS)",
        "description": "New support chatbot vs human agents, measuring NPS change",
        "variable_type": "Continuous",
        "analysis_mode": "Between Groups",
        "effect_of_interest": 8.0,
        "rope_width": 10.0,
        "precision_goal": 6.0,
        "null_value": 0.0,
        "rationale": """
**Context:** New support chatbot vs human agents (NPS scale -100 to +100)
- **Effect of interest:** 8 point NPS increase (good outcome)
- **ROPE:** ±5 points (business considers equivalent performance)
- **Goal:** 3 points (detect 6+ point differences confidently)
- **Why it matters:** NPS linked to churn rate. Wrong decision = retention cost.
  If chatbot is 10 points worse but you can't detect it, customer loss compounds.
        """,
    },
    "financial_forecasting": {
        "name": "💰 Portfolio Return (Quant Strategy)",
        "description": "New trading strategy vs benchmark annual return",
        "variable_type": "Continuous",
        "analysis_mode": "Single Group",
        "effect_of_interest": 0.02,
        "rope_width": 0.02,
        "precision_goal": 0.014,
        "null_value": 0.10,
        "rationale": """
**Context:** Quant strategy vs S&P 500 benchmark (≈10% annual return)
- **Effect of interest:** 2% alpha (meaningful outperformance)
- **ROPE:** [9%, 11%] around 10% benchmark (not worth fees/risk)
- **Goal:** 0.7% (detect 1.5%+ alpha with confidence)
- **Why it matters:** Institutional clients demand high Sharpe ratios.
  If you claim 2% alpha but HDI is ±3%, clients won't trust the strategy.
        """,
    },
    "educational_intervention": {
        "name": "📚 Educational Intervention",
        "description": "New teaching method vs traditional, measuring test scores",
        "variable_type": "Continuous",
        "analysis_mode": "Between Groups",
        "effect_of_interest": 5.0,
        "rope_width": 6.0,
        "precision_goal": 4.0,
        "null_value": 0.0,
        "rationale": """
**Context:** New teaching method vs traditional (100-point test scale)
- **Effect of interest:** 5 point improvement (Cohen's d ≈ 0.5, medium effect)
- **ROPE:** ±3 points (educationally insignificant per Cohen's d < 0.2)
- **Goal:** 2 points (detect medium effects confidently)
- **Why it matters:** School budgets are tight. Ineffective programs waste resources
  and teacher training time. Need tight precision to distinguish real improvements
  from noise.
        """,
    },
    "vaccine_efficacy": {
        "name": "💉 Vaccine Efficacy (Public Health)",
        "description": "Vaccinated vs unvaccinated infection rates",
        "variable_type": "Binary",
        "analysis_mode": "Between Groups",
        "effect_of_interest": 0.15,
        "rope_width": 0.10,
        "precision_goal": 0.06,
        "null_value": 0.0,
        "rationale": """
**Context:** Vaccinated vs unvaccinated infection rate difference
- **Effect of interest:** 15% absolute risk reduction (good vaccine)
- **ROPE:** ±5% efficacy (too small to justify public health mandate)
- **Goal:** 3% (confidently detect 8%+ efficacy)
- **Why it matters:** Vaccine mandates require strong evidence of benefit.
  Wide confidence intervals = public distrust. Need tight precision for policy decisions.
        """,
    },
}


# ══════════════════════════════════════════════════════════════
# Sample Size Estimation
# ══════════════════════════════════════════════════════════════

def estimate_sample_size_binary(
    precision_goal: float,
    ci_fraction: float = 0.95,
    baseline_rate: float = 0.5,
) -> int:
    """
    Estimate sample size needed for binary proportion to achieve precision goal.
    
    NOTE: This is PRECISION-based, not power-based. We calculate the sample size
    needed to achieve a target HDI width, NOT to detect a specific effect size.
    
    Uses conservative formula: n ≈ (z * sqrt(p(1-p)) / (goal/2))^2
    where p is the expected proportion.
    """
    from scipy.stats import norm
    z = norm.ppf((1 + ci_fraction) / 2)
    
    # Use baseline rate as expected proportion (conservative)
    p = baseline_rate
    se_target = precision_goal / (2 * z)  # Target SE
    n = p * (1 - p) / (se_target ** 2)
    
    return int(np.ceil(n))


def estimate_sample_size_continuous(
    precision_goal: float,
    ci_fraction: float = 0.95,
    std_dev: float = 1.0,
) -> int:
    """
    Estimate sample size for continuous variable to achieve precision goal.
    
    NOTE: This is PRECISION-based, not power-based. We calculate the sample size
    needed to achieve a target HDI width, NOT to detect a specific effect size.
    
    Uses: n ≈ (t * s / (goal/2))^2
    Iterates because t depends on df = n-1.
    """
    from scipy.stats import t as student_t
    
    # Start with z approximation
    n = 30
    for _ in range(10):  # Iterate to convergence
        df = n - 1
        t_crit = student_t.ppf((1 + ci_fraction) / 2, df)
        se_target = precision_goal / (2 * t_crit)
        n_new = int(np.ceil((std_dev / se_target) ** 2))
        if abs(n_new - n) < 2:
            break
        n = n_new
    
    return n


# ══════════════════════════════════════════════════════════════
# Visualization
# ══════════════════════════════════════════════════════════════

def plot_precision_comparison(
    variable_type: str,
    effect_size: float,
    rope_width: float,
    precision_goal: float,
    null_value: float,
    ci_fraction: float = 0.95,
):
    """
    Visualize "too wide" vs "acceptable" HDI for teaching precision goals.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    rope_min = null_value - rope_width / 2
    rope_max = null_value + rope_width / 2
    
    # Simulate two scenarios: wide HDI (needs more data) vs narrow HDI (goal met)
    hdi_wide = effect_size + np.array([-rope_width * 0.9, rope_width * 0.9])
    hdi_narrow = effect_size + np.array([-precision_goal / 2, precision_goal / 2])
    
    for ax, hdi, title, verdict_color in [
        (ax1, hdi_wide, "❌ Too Wide (Needs More Data)", "orange"),
        (ax2, hdi_narrow, "✅ Acceptable (Goal Met)", "green"),
    ]:
        # ROPE region
        ax.axvspan(rope_min, rope_max, alpha=0.2, color='gray', label='ROPE')
        ax.axvline(rope_min, color='gray', linestyle='--', linewidth=1)
        ax.axvline(rope_max, color='gray', linestyle='--', linewidth=1)
        
        # Null line
        ax.axvline(null_value, color='black', linestyle=':', linewidth=1.5, alpha=0.4)
        
        # HDI
        hdi_min, hdi_max = hdi
        ax.plot([hdi_min, hdi_max], [0.5, 0.5], linewidth=8, 
                color=verdict_color, alpha=0.7, label=f'HDI: [{hdi_min:.3f}, {hdi_max:.3f}]')
        
        # Point estimate
        ax.plot(effect_size, 0.5, 'D', markersize=12, color='darkblue',
                markerfacecolor='white', markeredgewidth=2)
        
        # Precision goal markers
        goal_markers = effect_size + np.array([-precision_goal/2, precision_goal/2])
        ax.plot(goal_markers, [0.3, 0.3], 'g|', markersize=20, markeredgewidth=3,
                label=f'Precision Goal: {precision_goal:.3f}')
        ax.plot([goal_markers[0], goal_markers[1]], [0.3, 0.3], 'g--', linewidth=1, alpha=0.5)
        
        # Labels
        ax.set_ylim(0, 1)
        ax.set_yticks([])
        ax.set_xlabel('Effect Size', fontsize=11)
        ax.set_title(title, fontsize=12, fontweight='bold', color=verdict_color)
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(axis='x', alpha=0.3)
        
        # Text annotations
        hdi_width = hdi_max - hdi_min
        status = "Goal Met ✓" if hdi_width <= precision_goal else "Needs More Data"
        ax.text(0.05, 0.85, f"HDI width: {hdi_width:.3f}\n{status}",
                transform=ax.transAxes, fontsize=10,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    fig.suptitle('Precision Goal Comparison', fontsize=14, fontweight='bold', y=1.02)
    fig.tight_layout()
    return fig


# ══════════════════════════════════════════════════════════════
# Main Render
# ══════════════════════════════════════════════════════════════

def render_main():
    """Main entry point for goal planner tab."""
    
    st.markdown("## 🎯 Precision Goal Planner")
    st.markdown("""
Welcome to the **Precision Goal Planner**! This interactive tool helps you understand
how to choose appropriate precision goals and ROPE widths for your analysis.

**How it works:**
1. Select a scenario similar to your use case
2. Adjust parameters to match your domain
3. See how precision requirements affect sample size
4. Apply settings to your analysis
    """)
    
    st.divider()
    
    # ── Scenario Selection ──
    st.markdown("### 1️⃣ Choose Your Scenario")
    
    scenario_keys = list(SCENARIOS.keys())
    scenario_names = [SCENARIOS[k]["name"] for k in scenario_keys]
    
    selected_idx = st.selectbox(
        "Select a scenario similar to your use case:",
        range(len(scenario_keys)),
        format_func=lambda i: scenario_names[i],
        key="goal_planner_scenario",
    )
    
    scenario_key = scenario_keys[selected_idx]
    scenario = SCENARIOS[scenario_key]
    
    # Show scenario description and rationale
    with st.expander(f"📖 About: {scenario['name']}", expanded=True):
        st.markdown(scenario['description'])
        st.markdown(scenario['rationale'])
    
    st.divider()
    
    # ── Parameter Adjustment ──
    st.markdown("### 2️⃣ Adjust Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📊 Analysis Configuration**")
        variable_type = st.selectbox(
            "Variable type",
            ["Binary", "Continuous"],
            index=0 if scenario["variable_type"] == "Binary" else 1,
            key="goal_planner_var_type",
        )
        
        analysis_mode = st.selectbox(
            "Analysis mode",
            ["Single Group", "Between Groups"],
            index=0 if scenario["analysis_mode"] == "Single Group" else 1,
            key="goal_planner_analysis_mode",
        )
    
    with col2:
        st.markdown("**🎯 Statistical Parameters**")
        ci_fraction = st.slider(
            "HDI mass",
            min_value=0.80,
            max_value=0.99,
            value=CI_FRACTION,
            step=0.01,
            format="%.2f",
            key="goal_planner_ci_fraction",
        )
    
    st.markdown("---")
    
    # Clarification box
    with st.expander("💡 What's the difference between these three values?"):
        st.markdown("""
**Effect of Interest** = What you're trying to measure
- "I want to know if there's at least a 5% conversion lift"
- Used for planning and context setting
- Determines what effect size the visualization shows

**ROPE Width** = What you consider negligible  
- "Differences smaller than ±3% don't matter to me"
- Defines practical equivalence boundary
- Used for ePitG verdicts (inside ROPE = equivalent)

**Precision Goal** = How narrow your HDI must be
- "My confidence interval needs to be ≤2% wide"
- Determines when you have enough data
- Drives sample size estimation

**Key insight:** Sample size estimation uses **precision goal** and **variance**, 
NOT effect size. We're asking "how much data for this precision?" not 
"how much data to detect this effect?"
        """)
    
    col_p1, col_p2, col_p3 = st.columns(3)
    
    with col_p1:
        st.markdown("**Effect of Interest**")
        effect_size = st.number_input(
            "Minimum meaningful difference",
            value=float(scenario["effect_of_interest"]),
            format="%.4f",
            key="goal_planner_effect",
            help="The smallest effect size you care about detecting",
        )
    
    with col_p2:
        st.markdown("**ROPE Width**")
        rope_width = st.number_input(
            "Region of Practical Equivalence",
            min_value=0.001,
            value=float(scenario["rope_width"]),
            format="%.4f",
            key="goal_planner_rope",
            help="Differences smaller than this are considered negligible",
        )
    
    with col_p3:
        st.markdown("**Precision Goal**")
        precision_goal = st.number_input(
            "Target HDI width",
            min_value=0.001,
            value=float(scenario["precision_goal"]),
            format="%.4f",
            key="goal_planner_goal",
            help="How narrow your confidence interval should be",
        )
    
    # Validation
    if precision_goal >= rope_width:
        st.warning("⚠️ **Precision goal must be narrower than ROPE width!** "
                  "Otherwise you can never make a conclusive decision.")
    
    null_value = scenario["null_value"]
    
    st.divider()
    
    # ── Visualization ──
    st.markdown("### 3️⃣ See the Difference")
    
    fig = plot_precision_comparison(
        variable_type=variable_type,
        effect_size=effect_size,
        rope_width=rope_width,
        precision_goal=precision_goal,
        null_value=null_value,
        ci_fraction=ci_fraction,
    )
    st.pyplot(fig)
    
    st.markdown("""
**💡 Key Insight:**  
The left plot shows an HDI that's too wide — it overlaps the ROPE boundaries, making 
the result inconclusive. The right plot shows an HDI narrow enough to meet the precision 
goal, enabling a clear decision.
    """)
    
    st.divider()
    
    # ── Sample Size Estimation ──
    st.markdown("### 4️⃣ Estimate Sample Size")
    
    st.markdown("""
How much data do you need to achieve this precision goal? This is a **rough estimate** 
assuming typical conditions (balanced groups for between-groups, moderate variance for continuous).
    """)
    
    col_s1, col_s2 = st.columns(2)
    
    with col_s1:
        if variable_type == "Binary":
            baseline_rate = st.slider(
                "Expected rate (for planning)",
                min_value=0.1,
                max_value=0.9,
                value=0.5,
                step=0.05,
                key="goal_planner_baseline",
                help="Used for sample size calculation; 0.5 is most conservative",
            )
            n_estimate = estimate_sample_size_binary(
                precision_goal=precision_goal,
                ci_fraction=ci_fraction,
                baseline_rate=baseline_rate,
            )
        else:  # Continuous
            std_dev = st.number_input(
                "Expected standard deviation",
                min_value=0.1,
                value=15.0,
                step=0.5,
                key="goal_planner_std",
                help="Estimate of population SD for planning",
            )
            n_estimate = estimate_sample_size_continuous(
                precision_goal=precision_goal,
                ci_fraction=ci_fraction,
                std_dev=std_dev,
            )
    
    with col_s2:
        if analysis_mode == "Single Group":
            st.metric("Estimated Sample Size", f"{n_estimate:,}")
            st.caption("Total observations needed")
        else:  # Between Groups
            n_per_group = int(np.ceil(n_estimate * 1.2))  # Rough adjustment for 2 groups
            st.metric("Estimated Sample Size", f"{n_per_group:,} per group")
            st.caption(f"Total: {n_per_group * 2:,} observations")
    
    st.info("📝 **Note:** These are approximate estimates. Actual sample size may vary "
           "based on observed variance, group imbalance, and other factors. Use this as "
           "a starting point for planning.")
    
    st.divider()
    
    # ── Apply to Analysis ──
    st.markdown("### 5️⃣ Apply These Settings")
    
    st.markdown("""
Ready to use these values in your analysis? Copy them to the appropriate tab:
    """)
    
    col_a1, col_a2, col_a3 = st.columns(3)
    
    # Store in session state for other tabs to access
    if st.button("📋 Copy Settings to Clipboard", key="goal_planner_copy"):
        settings_text = f"""
Precision Goal Settings (from Goal Planner):
- Variable Type: {variable_type}
- Analysis Mode: {analysis_mode}
- ROPE width: {rope_width}
- Precision Goal: {precision_goal}
- HDI mass: {ci_fraction:.0%}
- Estimated sample size: {n_estimate if analysis_mode == "Single Group" else f"{n_per_group} per group"}
        """
        st.code(settings_text, language="text")
        st.success("✅ Settings displayed above! Copy and save for your records.")
    
    st.markdown("---")
    
    with st.expander("ℹ️ Learn More: Why Precision Goals Matter"):
        st.markdown("""
### The Problem with Traditional NHST

Traditional null hypothesis significance testing (NHST) only asks: "Is there an effect?"
But it doesn't tell you:
- **How certain are you about the effect size?**
- **Is the effect large enough to matter?**
- **When should you stop collecting data?**

### The ePitG Solution

**Enhanced Precision is the Goal (ePitG)** requires both:
1. **Precision Met**: HDI width < Precision Goal (narrow enough to be useful)
2. **Conclusive Location**: HDI fully inside or outside ROPE (clear practical significance)

This ensures you stop collecting data when you have both:
- **Adequate precision** (not too much uncertainty)
- **Clear practical implications** (effect is big enough to matter, or clearly negligible)

### Choosing Values

**Precision Goal:** Should be narrower than ROPE, but not unnecessarily tight.
- Too wide → Inconclusive results even with lots of data
- Too narrow → Need huge sample sizes

**ROPE Width:** Reflects domain expertise about what differences matter.
- Clinical trials: Use established minimal clinically important difference (MCID)
- Business: Calculate from cost-benefit analysis
- Policy: Based on stakeholder consensus

**Rule of thumb:** Precision Goal ≈ 60-80% of ROPE width works well for most applications.
        """)
