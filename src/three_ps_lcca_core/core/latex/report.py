"""
LaTeX Report Generator for 3psLCCA (Life Cycle Cost Analysis).

Generates a comprehensive, human-readable .tex file documenting all
lifecycle cost calculations for bridge infrastructure, including:
  - Formulas in LaTeX notation
  - Plain-English explanations
  - Input values
  - Step-by-step derivations
  - Final computed values
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# LaTeX escaping helpers
# ---------------------------------------------------------------------------

def _esc(text: Any) -> str:
    """Escape special LaTeX characters, converting non-string inputs to str first."""
    text = str(text)
    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _fmt(value: Any, decimals: int = 4) -> str:
    """Format a numeric value with commas and fixed decimals."""
    if isinstance(value, (int, float)):
        return f"{value:,.{decimals}f}"
    return _esc(str(value))


def _key_to_label(key: str) -> str:
    """Convert snake_case key to Title Case label."""
    return key.replace("_", " ").title()


# ---------------------------------------------------------------------------
# Formula conversion: text → LaTeX math
# ---------------------------------------------------------------------------

_FORMULA_MAP: Dict[str, str] = {
    # Initial stage
    "present_value_of_construction_costs":
        r"C_{pv} = C_0 \times \text{SPWF}",
    "present_value_of_carbon_costs":
        r"E_{pv} = E_0 \times \text{SPWF}",
    "initial_construction_cost":
        r"C_0",
    "initial_material_carbon_emission_cost":
        r"E_0",
    "initial_road_user_cost":
        r"RUC = \text{daily\_RUC} \times d_{construction}",
    "initial_vehicular_emission_cost":
        r"VEC = \text{emission\_kg/day} \times d_{construction} \times SCC \times \Gamma",
    "time_cost_of_loan":
        r"TCL = C_0 \times r_{interest} \times t_{construction} \times \rho_{invest} \times \text{SPWF}",
    # Use stage
    "routine_inspection_cost_per_year":
        r"C_{ri} = C_0 \times \frac{p_{ri}}{100}",
    "present_value_of_routine_inspection_costs":
        r"C_{ri,pv} = C_{ri} \times \text{SPWF}_{interval}",
    "routine_maintenance_cost_per_year":
        r"C_{rm} = C_0 \times \frac{p_{rm}}{100}",
    "routine_carbon_cost_per_year":
        r"E_{rm} = E_0 \times \frac{p_{ec}}{100}",
    "present_value_of_routine_maintenance_costs":
        r"C_{rm,pv} = C_{rm} \times \text{SPWF}_{interval}",
    "present_value_of_routine_carbon_costs":
        r"E_{rm,pv} = E_{rm} \times \text{SPWF}_{interval}",
    "major_inspection_cost":
        r"C_{mi} = C_0 \times \frac{p_{mi}}{100}",
    "present_value_of_major_inspection_costs":
        r"C_{mi,pv} = C_{mi} \times \text{SPWF}_{interval}",
    "major_repair_cost":
        r"C_{mr} = C_0 \times \frac{p_{mr}}{100}",
    "major_repair_carbon_cost":
        r"E_{mr} = E_0 \times \frac{p_{ec,mr}}{100}",
    "present_value_of_major_repair_costs":
        r"C_{mr,pv} = C_{mr} \times \text{SPWF}_{interval}",
    "present_value_of_major_repair_carbon_costs":
        r"E_{mr,pv} = E_{mr} \times \text{SPWF}_{interval}",
    "road_user_cost":
        r"RUC = \text{daily\_RUC} \times d_{disruption} \times \text{SPWF}",
    "vehicular_emission_cost":
        r"VEC = \text{emission\_kg/day} \times d_{disruption} \times SCC \times \Gamma \times \text{SPWF}",
    "replacement_cost":
        r"C_{rep} = C_{ss} \times \frac{p_{ss}}{100}",
    "present_value_of_replacement_costs":
        r"C_{rep,pv} = C_{rep} \times \text{SPWF}_{interval}",
    # Demolition / reconstruction
    "demolition_cost":
        r"C_{dem} = C_0 \times \frac{p_{dem}}{100}",
    "demolition_carbon_cost":
        r"E_{dem} = E_0 \times \frac{p_{ec,dem}}{100}",
    "present_value_of_demolition_costs":
        r"C_{dem,pv} = C_{dem} \times \text{SPWI}_{dem}",
    "present_value_of_demolition_carbon_costs":
        r"E_{dem,pv} = E_{dem} \times \text{SPWI}_{dem}",
    "cost_of_reconstruction_after_demolition":
        r"C_{recon} = C_0 \times \text{SPWI}_{recon}",
    "present_value_of_reconstruction_costs":
        r"C_{recon,pv} = C_0 \times \text{SPWI}_{recon}",
}

_FORMULA_EXPLANATIONS: Dict[str, str] = {
    "initial_construction_cost":
        "The direct initial construction cost of the bridge in the base year.",
    "initial_material_carbon_emission_cost":
        "Carbon emission cost associated with materials used during initial construction.",
    "initial_road_user_cost":
        "Cost imposed on road users (delay, vehicle operating costs) during the construction period, "
        "computed as the daily road user cost multiplied by the total construction days.",
    "initial_vehicular_emission_cost":
        "Cost of additional vehicular emissions generated by traffic disruption during construction, "
        "using the Social Cost of Carbon (SCC) converted to local currency.",
    "time_cost_of_loan":
        "The financing cost during construction — the interest on the investment portion of the loan "
        r"over the construction period, discounted to present value using the SPWF.",
    "present_value_of_construction_costs":
        "Present value of a future construction cost occurrence, obtained by multiplying "
        "the base cost by the Sum of Present Worth Factor (SPWF) for the relevant interval.",
    "present_value_of_carbon_costs":
        "Present value of carbon emission costs at a future construction occurrence.",
    "routine_inspection_cost_per_year":
        r"Annual cost of routine bridge inspections, as a percentage of the initial construction cost.",
    "present_value_of_routine_inspection_costs":
        r"Sum of present values of routine inspection costs across all occurrences in the analysis period.",
    "routine_maintenance_cost_per_year":
        r"Annual cost of routine maintenance activities, as a percentage of the initial construction cost.",
    "routine_carbon_cost_per_year":
        r"Annual carbon cost associated with routine maintenance, as a percentage of initial carbon emission cost.",
    "present_value_of_routine_maintenance_costs":
        r"Sum of present values of routine maintenance costs over the entire analysis period.",
    "present_value_of_routine_carbon_costs":
        r"Sum of present values of routine maintenance carbon costs over the analysis period.",
    "major_inspection_cost":
        r"Cost of a single major inspection event, as a percentage of the initial construction cost.",
    "present_value_of_major_inspection_costs":
        r"Sum of present values of all major inspection events over the analysis period.",
    "major_repair_cost":
        r"Cost of a single major repair/rehabilitation event, as a percentage of initial construction cost.",
    "major_repair_carbon_cost":
        r"Carbon emission cost for a major repair event, as a percentage of initial carbon emission cost.",
    "present_value_of_major_repair_costs":
        r"Sum of present values of all major repair cost occurrences.",
    "present_value_of_major_repair_carbon_costs":
        r"Sum of present values of all major repair carbon cost occurrences.",
    "road_user_cost":
        r"Total road user cost during a disruption event (repair, replacement, or demolition), "
        r"accounting for the present worth of the disruption timing.",
    "vehicular_emission_cost":
        r"Total vehicular emission cost during a disruption event, accounting for present worth.",
    "replacement_cost":
        r"Cost to replace bearings and expansion joints, as a percentage of the superstructure cost.",
    "present_value_of_replacement_costs":
        r"Sum of present values of all bearing and expansion joint replacement events.",
    "demolition_cost":
        r"Cost of demolition and disposal, as a percentage of the initial construction cost.",
    "demolition_carbon_cost":
        r"Carbon emission cost of demolition, as a percentage of the initial carbon emission cost.",
    "present_value_of_demolition_costs":
        r"Present value of demolition costs, discounted using the demolition Single Present Worth Interest (SPWI) factor.",
    "present_value_of_demolition_carbon_costs":
        r"Present value of demolition carbon costs.",
    "cost_of_reconstruction_after_demolition":
        r"Cost to rebuild the bridge after demolition (at reconstruction stage), discounted to present value.",
    "present_value_of_reconstruction_costs":
        r"Present value of reconstruction costs after end-of-life demolition.",
}


def _get_formula_latex(formula_key: str, formula_text: str) -> str:
    """Return LaTeX math string for a formula key, falling back to escaping the text."""
    if formula_key in _FORMULA_MAP:
        return _FORMULA_MAP[formula_key]
    # Fallback: convert text formula (using 'x' for multiplication) to ×
    tex = formula_text.replace(" x ", r" \times ")
    return tex


def _get_formula_explanation(formula_key: str, formula_text: str) -> str:
    """Return plain-English explanation for a formula key."""
    if formula_key in _FORMULA_EXPLANATIONS:
        return _FORMULA_EXPLANATIONS[formula_key]
    return _esc(formula_text)


# ---------------------------------------------------------------------------
# Low-level LaTeX fragment builders
# ---------------------------------------------------------------------------

def _begin_doc(title: str = "Life Cycle Cost Analysis Report") -> str:
    return r"""\documentclass[12pt,a4paper]{article}
\usepackage[margin=2.5cm]{geometry}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{xcolor}
\usepackage{fancyhdr}
\usepackage{hyperref}
\usepackage{caption}
\usepackage{float}
\usepackage{multirow}
\usepackage{tabularx}

\definecolor{headblue}{RGB}{0, 70, 127}
\definecolor{rowgray}{RGB}{240, 240, 240}
\definecolor{sectiongreen}{RGB}{0, 120, 0}

\hypersetup{
    colorlinks=true,
    linkcolor=headblue,
    urlcolor=headblue,
    pdftitle={""" + title + r"""},
}

\pagestyle{fancy}
\fancyhf{}
\rhead{\textcolor{headblue}{\small Life Cycle Cost Analysis}}
\lhead{\textcolor{headblue}{\small 3psLCCA Engine}}
\cfoot{\thepage}
\renewcommand{\headrulewidth}{0.4pt}

\setlength{\parindent}{0pt}
\setlength{\parskip}{6pt}

\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\newcolumntype{R}[1]{>{\raggedleft\arraybackslash}p{#1}}
\newcolumntype{C}[1]{>{\centering\arraybackslash}p{#1}}

\begin{document}
"""


def _end_doc() -> str:
    return r"\end{document}" + "\n"


def _title_page(general: Dict[str, Any]) -> str:
    lines = []
    lines.append(r"\begin{titlepage}")
    lines.append(r"\centering")
    lines.append(r"\vspace*{2cm}")
    lines.append(r"{\Huge\bfseries\color{headblue} Life Cycle Cost Analysis Report\\[0.5em]}")
    lines.append(r"{\large\color{headblue} Bridge Infrastructure --- 3psLCCA Engine\\[2em]}")
    lines.append(r"\rule{\linewidth}{0.4pt}\\[1em]")
    lines.append(r"{\large\bfseries Project Parameters}\\[1em]")
    lines.append(r"\begin{tabular}{L{8cm}R{5cm}}")
    lines.append(r"\toprule")
    lines.append(r"\textbf{Parameter} & \textbf{Value} \\")
    lines.append(r"\midrule")

    param_labels = [
        ("service_life_years", "Service Life (years)"),
        ("analysis_period_years", "Analysis Period (years)"),
        ("discount_rate_percent", "Discount Rate (\\%)"),
        ("inflation_rate_percent", "Inflation Rate (\\%)"),
        ("interest_rate_percent", "Interest Rate (\\%)"),
        ("currency_conversion", "Currency Conversion (INR/USD)"),
        ("social_cost_of_carbon_per_mtco2e", "Social Cost of Carbon (USD/MtCO$_2$e)"),
        ("construction_period_months", "Construction Period (months)"),
        ("investment_ratio", "Investment Ratio"),
    ]
    for key, label in param_labels:
        if key in general:
            val = general[key]
            lines.append(f"  {label} & {_fmt(val, 2)} \\\\")

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\vfill")
    lines.append(r"{\small\textit{Generated by the 3psLCCA Life Cycle Cost Analysis Engine}}")
    lines.append(r"\end{titlepage}")
    lines.append(r"\tableofcontents")
    lines.append(r"\newpage")
    return "\n".join(lines) + "\n\n"


def _section(title: str) -> str:
    return f"\\section{{{_esc(title)}}}\n"


def _subsection(title: str) -> str:
    return f"\\subsection{{{_esc(title)}}}\n"


def _subsubsection(title: str) -> str:
    return f"\\subsubsection{{{_esc(title)}}}\n"


def _kv_table(data: Dict[str, Any], caption: str = "", decimals: int = 4) -> str:
    lines = []
    lines.append(r"\begin{table}[H]")
    lines.append(r"\centering")
    if caption:
        lines.append(f"\\caption{{{_esc(caption)}}}")
    lines.append(r"\begin{tabular}{L{9cm}R{5cm}}")
    lines.append(r"\toprule")
    lines.append(r"\textbf{Item} & \textbf{Value} \\")
    lines.append(r"\midrule")
    for k, v in data.items():
        if isinstance(v, dict):
            continue  # skip nested dicts
        label = _key_to_label(str(k))
        lines.append(f"  {_esc(label)} & {_fmt(v, decimals)} \\\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    return "\n".join(lines) + "\n\n"


def _formula_block(
    formula_key: str,
    formula_text: str,
    inputs: Dict[str, Any],
    computed_values: Dict[str, Any],
    final_value_key: Optional[str] = None,
) -> str:
    """Render a full formula derivation block for one cost component."""
    lines = []

    latex_formula = _get_formula_latex(formula_key, formula_text)
    explanation = _get_formula_explanation(formula_key, formula_text)

    lines.append(r"\begin{itemize}")
    lines.append(f"  \\item \\textbf{{Formula:}} $${latex_formula}$$")
    lines.append(f"  \\item \\textbf{{Explanation:}} {explanation}")

    # Input values
    if inputs:
        lines.append(r"  \item \textbf{Input Values:}")
        lines.append(r"  \begin{itemize}")
        for k, v in inputs.items():
            lines.append(f"    \\item ${_esc(k)}$ = {_fmt(v)}")
        lines.append(r"  \end{itemize}")

    # Substitution and step-by-step
    if inputs and computed_values:
        lines.append(r"  \item \textbf{Substitution \& Derivation:}")
        lines.append(r"  \begin{itemize}")
        # Build substituted formula string
        sub_parts = []
        for k, v in inputs.items():
            sub_parts.append(f"{_fmt(v)}")
        if sub_parts:
            lines.append(
                f"    \\item Substituting values: $"
                + r" \times ".join(sub_parts)
                + "$"
            )
        # Show each computed value
        for cvk, cvv in computed_values.items():
            if isinstance(cvv, (int, float)):
                lines.append(
                    f"    \\item ${_esc(cvk)}$ = {_fmt(cvv)}"
                )
        lines.append(r"  \end{itemize}")

    # Final computed value
    if final_value_key and final_value_key in computed_values:
        fv = computed_values[final_value_key]
        lines.append(
            f"  \\item \\textbf{{Final Value:}} "
            f"${_esc(final_value_key)}$ = \\textbf{{{_fmt(fv)}}}"
        )

    lines.append(r"\end{itemize}")
    return "\n".join(lines) + "\n\n"


def _breakdown_section(
    component_title: str,
    breakdown: Optional[Dict[str, Any]],
    summary_value: Optional[Any] = None,
) -> str:
    """Render a complete breakdown sub-section for one cost component."""
    if not breakdown:
        lines = [_subsubsection(component_title)]
        if summary_value is not None:
            lines.append(f"Total: {_fmt(summary_value)}\n\n")
        return "\n".join(lines)

    lines = [_subsubsection(component_title)]

    formulae = breakdown.get("formulae", {})
    inputs = breakdown.get("inputs", {})
    computed_values = breakdown.get("computed_values", {})

    # Summary of computed values
    if computed_values:
        lines.append(r"\textbf{Computed Values:}" + "\n")
        lines.append(r"\begin{itemize}")
        for k, v in computed_values.items():
            if isinstance(v, (int, float)):
                lines.append(f"  \\item ${_esc(k)}$ = {_fmt(v)}")
        lines.append(r"\end{itemize}" + "\n")

    # For each formula, render the full derivation block
    if formulae:
        lines.append(r"\textbf{Detailed Derivations:}" + "\n\n")
        for fkey, ftext in formulae.items():
            lines.append(f"\\textit{{[{_esc(fkey)}]}}\n")
            lines.append(
                _formula_block(
                    formula_key=fkey,
                    formula_text=ftext,
                    inputs=inputs,
                    computed_values=computed_values,
                )
            )

    # Summary total
    if summary_value is not None:
        lines.append(
            f"\\textbf{{Component Total:}} \\textbf{{\\Large {_fmt(summary_value)}}}\n\n"
        )

    lines.append(r"\medskip\hrule\medskip" + "\n")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Stage-specific section builders
# ---------------------------------------------------------------------------

def _section_construction_inputs(construction_costs: Dict[str, Any]) -> str:
    lines = [_section("Construction Cost Inputs")]
    lines.append(
        "The following table summarises the initial construction cost breakdown "
        "provided as input to the LCCA engine.\n\n"
    )
    lines.append(r"\begin{table}[H]")
    lines.append(r"\centering")
    lines.append(r"\caption{Construction Cost Breakdown}")
    lines.append(r"\begin{tabular}{L{9cm}R{5cm}}")
    lines.append(r"\toprule")
    lines.append(r"\textbf{Cost Component} & \textbf{Amount} \\")
    lines.append(r"\midrule")

    cost_labels = [
        ("initial_construction_cost", "Initial Construction Cost"),
        ("initial_carbon_emissions_cost", "Carbon Emissions Cost"),
        ("superstructure_construction_cost", "Superstructure Construction Cost"),
        ("total_scrap_value", "Total Scrap Value (Salvage)"),
    ]
    for key, label in cost_labels:
        if key in construction_costs:
            val = construction_costs[key]
            lines.append(f"  {label} & {_fmt(val, 2)} \\\\")

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    lines.append("\n")
    return "\n".join(lines) + "\n"


def _section_initial_stage(initial_stage: Dict[str, Any]) -> str:
    lines = [_section("Stage 1 --- Initial Construction Stage")]
    lines.append(
        "This section covers all costs incurred at the time of initial construction: "
        "the direct construction cost, carbon emission cost, road user cost during "
        "construction, vehicular emission cost, and the time cost of the loan.\n\n"
    )

    # Summary table
    all_vals: Dict[str, Any] = {}
    for cat in ("economic", "environmental", "social"):
        d = initial_stage.get(cat, {})
        if isinstance(d, dict):
            all_vals.update(d)
    lines.append(_kv_table(all_vals, caption="Initial Stage --- Cost Summary"))

    breakdown = initial_stage.get("_debug_breakdown")
    if not breakdown:
        return "\n".join(lines)

    formulae = breakdown.get("formulae", {})
    inputs = breakdown.get("inputs", {})
    computed_values = breakdown.get("computed_values", {})

    # ---- Initial construction cost sub-section ----
    lines.append(_subsection("Initial Construction Cost"))
    lines.append(
        "The initial construction cost is taken directly as the input value. "
        "It represents the total capital cost to build the bridge structure.\n\n"
    )
    lines.append(r"\begin{itemize}")
    lines.append(
        f"  \\item \\textbf{{Formula:}} $C_0 = C_0$ (direct input)"
    )
    lines.append(
        f"  \\item \\textbf{{Input Value:}} $C_0$ = {_fmt(inputs.get('initial_construction_cost', 0))}"
    )
    lines.append(
        f"  \\item \\textbf{{Result:}} {_fmt(inputs.get('initial_construction_cost', 0))}"
    )
    lines.append(r"\end{itemize}" + "\n")

    # ---- Time Cost of Loan sub-section ----
    lines.append(_subsection("Time Cost of Loan"))
    lines.append(
        "The time cost of loan accounts for the interest expense on borrowed funds "
        "during the construction period. Only the invested portion (investment ratio) "
        "of the construction cost is assumed to be financed.\n\n"
    )
    tcl_breakdown = breakdown.get("total_time_cost_of_loan", {})
    tcl_formulae = tcl_breakdown.get("formulae", {}) if tcl_breakdown else {}
    tcl_inputs = tcl_breakdown.get("inputs", {}) if tcl_breakdown else {}
    tcl_computed = tcl_breakdown.get("computed_values", {}) if tcl_breakdown else {}

    if tcl_formulae:
        for fkey, ftext in tcl_formulae.items():
            lines.append(
                _formula_block(
                    formula_key=fkey,
                    formula_text=ftext,
                    inputs=tcl_inputs,
                    computed_values=tcl_computed,
                    final_value_key="time_cost_of_loan",
                )
            )

    # ---- Road User Cost sub-section ----
    lines.append(_subsection("Road User Cost and Vehicular Emission Cost (Construction)"))
    lines.append(
        "Road users experience delays and extra vehicle operating costs while the "
        "bridge is under construction. The road user cost (RUC) equals the daily RUC "
        "multiplied by the total construction duration in days. The vehicular emission "
        "cost is derived from the daily carbon emission volume, the Social Cost of Carbon "
        "(SCC), and the currency conversion rate.\n\n"
    )
    ruc_bd = breakdown.get("road_user_cost_breakdown", {})
    if ruc_bd:
        lines.append(r"\begin{itemize}")
        for k, v in ruc_bd.items():
            if v is not None:
                lines.append(f"  \\item ${_esc(k)}$ = {_fmt(v)}")
        lines.append(r"\end{itemize}")
    lines.append(
        f"\n\\textbf{{Total Road User Cost:}} "
        f"{_fmt(computed_values.get('initial_road_user_cost', 0))}\n\n"
    )
    lines.append(
        f"\\textbf{{Total Vehicular Emission Cost:}} "
        f"{_fmt(computed_values.get('initial_vehicular_emission_cost', 0))}\n\n"
    )

    return "\n".join(lines) + "\n"


def _section_use_stage(use_stage: Dict[str, Any]) -> str:
    lines = [_section("Stage 2 --- Use (Maintenance) Stage")]
    lines.append(
        "The use stage encompasses all costs associated with maintaining the bridge "
        "over its service life, including routine inspections and maintenance, major "
        "inspections and repairs, and periodic replacement of bearings and expansion joints.\n\n"
    )

    # Summary table
    all_vals: Dict[str, Any] = {}
    for cat in ("economic", "environmental", "social"):
        d = use_stage.get(cat, {})
        if isinstance(d, dict):
            all_vals.update(d)
    lines.append(_kv_table(all_vals, caption="Use Stage --- Cost Summary"))

    debug = use_stage.get("_debug_breakdown")
    if not debug:
        return "\n".join(lines)

    # ---- Routine Inspection ----
    routine = debug.get("routine_inspection_costs", {})
    ri_bd = routine.get("breakdown") if routine else None
    lines.append(_subsection("Routine Inspection"))
    lines.append(
        "Routine inspections are carried out at fixed intervals to monitor the "
        "structural health of the bridge. The present value of all inspection costs "
        "over the analysis period is calculated using the Sum of Present Worth Factor "
        "(SPWF) for the inspection interval.\n\n"
    )
    if ri_bd:
        lines.append(_breakdown_section("Routine Inspection Derivation", ri_bd,
                                        summary_value=routine.get("total")))

    # ---- Periodic Maintenance ----
    maint = debug.get("routine_maintenance_and_carbon_costs", {})
    rm_bd = maint.get("breakdown") if maint else None
    lines.append(_subsection("Periodic Maintenance"))
    lines.append(
        "Periodic (routine) maintenance tasks such as cleaning, minor repairs, and "
        "painting are carried out at regular intervals. Both the direct maintenance cost "
        "and the associated carbon emission cost are discounted to present values.\n\n"
    )
    if rm_bd:
        lines.append(_breakdown_section("Periodic Maintenance Derivation", rm_bd))

    # ---- Major Inspection ----
    maj_insp = debug.get("major_inspection_costs", {})
    mi_bd = maj_insp.get("breakdown") if maj_insp else None
    lines.append(_subsection("Major Inspection"))
    lines.append(
        "Major inspections involve detailed structural assessment at longer intervals "
        "and have a higher unit cost than routine inspections.\n\n"
    )
    if mi_bd:
        lines.append(_breakdown_section("Major Inspection Derivation", mi_bd,
                                        summary_value=maj_insp.get("total_major_inspection_costs")))

    # ---- Major Repair ----
    maj_rep = debug.get("major_repair_carbon_and_road_user_costs", {})
    mr_bd = maj_rep.get("breakdown") if maj_rep else None
    lines.append(_subsection("Major Repair"))
    lines.append(
        "Major repair and rehabilitation activities are carried out at fixed intervals "
        "over the analysis period. These events incur direct repair costs, carbon "
        "emission costs, and road user / vehicular emission costs during the disruption "
        "period when the bridge is partially or fully closed to traffic.\n\n"
    )
    if mr_bd:
        lines.append(_breakdown_section("Major Repair Derivation", mr_bd))

    # ---- Bearing and Expansion Joint Replacement ----
    rep = debug.get("replacement_costs_for_bearing_and_expansion_joint", {})
    rep_bd = rep.get("breakdown") if rep else None
    lines.append(_subsection("Bearing and Expansion Joint Replacement"))
    lines.append(
        "Bearings and expansion joints have a shorter design life than the main structure "
        "and require periodic replacement. Replacement costs are expressed as a percentage "
        "of the superstructure cost, and road user costs arise from the brief closure "
        "during replacement work.\n\n"
    )
    if rep_bd:
        lines.append(_breakdown_section("Replacement Derivation", rep_bd))

    return "\n".join(lines) + "\n"


def _section_reconstruction(reconstruction: Dict[str, Any]) -> str:
    lines = [_section("Stage 3 --- Reconstruction Stage")]

    if "Note" in reconstruction:
        lines.append(f"\\textit{{{_esc(reconstruction['Note'])}}}\n\n")
        return "\n".join(lines) + "\n"

    lines.append(
        "If the analysis period exceeds the service life of the bridge, a full "
        "reconstruction is required. This section accounts for the demolition and "
        "disposal of the existing structure, the cost of rebuilding, the time cost "
        "of the new financing, the scrap/salvage value recovered, and road user costs "
        "during both demolition and reconstruction.\n\n"
    )

    # Summary table
    all_vals: Dict[str, Any] = {}
    for cat in ("economic", "environmental", "social"):
        d = reconstruction.get(cat, {})
        if isinstance(d, dict):
            all_vals.update(d)
    lines.append(_kv_table(all_vals, caption="Reconstruction Stage --- Cost Summary"))

    debug = reconstruction.get("_debug_breakdown")
    if not debug:
        return "\n".join(lines)

    # Present Worth Factor for demolition
    lines.append(_subsection("Present Worth Factor for Reconstruction Demolition"))
    lines.append(
        "The Single Present Worth Interest (SPWI) factor discounts costs that occur "
        "at the end of the first service life to the base year of the analysis.\n\n"
    )
    pwf_data = debug.get("present_worth_factor_for_demolition", {})
    if pwf_data and isinstance(pwf_data, dict):
        lines.append(r"\begin{itemize}")
        for k, v in pwf_data.items():
            if isinstance(v, (int, float)):
                lines.append(f"  \\item ${_esc(k)}$ = {_fmt(v)}")
        lines.append(r"\end{itemize}" + "\n")

    # Demolition and Disposal
    lines.append(_subsection("Demolition and Disposal Costs"))
    lines.append(
        "Prior to reconstruction, the existing bridge must be demolished and the "
        "debris disposed of. The demolition cost and associated carbon cost are "
        "calculated as percentages of the original construction and carbon costs, "
        "then discounted to present value.\n\n"
    )
    dem_bd = debug.get("demolition_and_disposal_breakdown")
    if dem_bd:
        formulae = dem_bd.get("formulae", {})
        inputs = dem_bd.get("inputs", {})
        computed = dem_bd.get("computed_values", {})
        for fkey, ftext in formulae.items():
            lines.append(f"\\textit{{[{_esc(fkey)}]}}\n")
            lines.append(_formula_block(fkey, ftext, inputs, computed))

    # Reconstruction costs
    lines.append(_subsection("Reconstruction Costs"))
    lines.append(
        "After demolition, the bridge is rebuilt at the same specification as the "
        "original. The reconstruction cost equals the initial construction cost discounted "
        "to the point of reconstruction using the SPWI factor.\n\n"
    )
    rec_bd = debug.get("reconstruction_costs_breakdown")
    if rec_bd:
        rec_formulae = rec_bd.get("formulae", {})
        rec_inputs = rec_bd.get("inputs", {})
        rec_computed = rec_bd.get("computed_values", {})
        for fkey, ftext in rec_formulae.items():
            lines.append(f"\\textit{{[{_esc(fkey)}]}}\n")
            lines.append(_formula_block(fkey, ftext, rec_inputs, rec_computed))

    # RUC during demolition & reconstruction
    lines.append(_subsection("Road User and Vehicular Emission Costs"))
    lines.append(
        "Traffic disruption during demolition and reconstruction imposes road user and "
        "vehicular emission costs, computed from daily values and the respective "
        "disruption durations.\n\n"
    )
    ruc_bd = debug.get("road_user_and_vehicular_emission_costs_breakdown", {})
    if ruc_bd and isinstance(ruc_bd, dict):
        lines.append(r"\begin{itemize}")
        for k, v in ruc_bd.items():
            if isinstance(v, (int, float)):
                lines.append(f"  \\item ${_esc(k)}$ = {_fmt(v)}")
        lines.append(r"\end{itemize}" + "\n")

    # Scrap value
    lines.append(_subsection("Scrap / Salvage Value"))
    lines.append(
        "The scrap value represents the residual value of salvageable materials "
        "(steel, etc.) recovered at the time of demolition. It is subtracted from "
        "the total cost as a credit.\n\n"
    )
    sv = debug.get("total_scrap_value", {})
    if isinstance(sv, dict):
        if "formula" in sv:
            lines.append(
                f"\\textbf{{Formula:}} $\\text{{scrap\\_value}} \\times \\text{{SPWI}}$\n\n"
            )
        if "value" in sv:
            lines.append(f"\\textbf{{Value:}} {_fmt(sv['value'])}\n\n")
        if "note" in sv:
            lines.append(f"\\textit{{{_esc(sv['note'])}}}\n\n")

    return "\n".join(lines) + "\n"


def _section_end_of_life(end_of_life: Dict[str, Any]) -> str:
    lines = [_section("Stage 4 --- End-of-Life Stage")]
    lines.append(
        "At the end of the analysis period, the bridge undergoes final demolition. "
        "This stage captures the terminal demolition and disposal costs, the scrap "
        "salvage credit, and the road user / vehicular emission costs during the "
        "final demolition period.\n\n"
    )

    # Summary table
    all_vals: Dict[str, Any] = {}
    for cat in ("economic", "environmental", "social"):
        d = end_of_life.get(cat, {})
        if isinstance(d, dict):
            all_vals.update(d)
    lines.append(_kv_table(all_vals, caption="End-of-Life Stage --- Cost Summary"))

    debug = end_of_life.get("_debug_breakdown")
    if not debug:
        return "\n".join(lines)

    # Demolition and Disposal
    lines.append(_subsection("Demolition and Disposal"))
    lines.append(
        "The final demolition cost and associated carbon emission cost are computed "
        "as percentages of the initial construction and carbon costs, then discounted "
        "using the end-of-life SPWI factor.\n\n"
    )
    dem_bd = debug.get("demolition_and_disposal_breakdown")
    if dem_bd:
        formulae = dem_bd.get("formulae", {})
        inputs = dem_bd.get("inputs", {})
        computed = dem_bd.get("computed_values", {})
        for fkey, ftext in formulae.items():
            lines.append(f"\\textit{{[{_esc(fkey)}]}}\n")
            lines.append(_formula_block(fkey, ftext, inputs, computed))

    # Present Worth Factor
    lines.append(_subsection("Present Worth Factor for Final Demolition"))
    pwf = debug.get("present_worth_factor_for_demolition", {})
    if pwf and isinstance(pwf, dict):
        lines.append(r"\begin{itemize}")
        for k, v in pwf.items():
            if isinstance(v, (int, float)):
                lines.append(f"  \\item ${_esc(k)}$ = {_fmt(v)}")
        lines.append(r"\end{itemize}" + "\n")

    # Road user cost during final demolition
    lines.append(_subsection("Road User and Vehicular Emission Costs (Final Demolition)"))
    lines.append(
        "Traffic disruption during final demolition results in road user costs "
        "and vehicular emission costs over the demolition duration.\n\n"
    )
    lines.append(r"\begin{itemize}")
    lines.append(
        f"  \\item \\textbf{{Road User Cost:}} "
        f"{_fmt(debug.get('ruc_demolition', 0))}"
    )
    lines.append(
        f"  \\item \\textbf{{Vehicular Emission Cost:}} "
        f"{_fmt(debug.get('demolition_vehicular_emission_cost', 0))}"
    )
    lines.append(r"\end{itemize}" + "\n")

    # Scrap / salvage value
    lines.append(_subsection("Scrap / Salvage Value"))
    lines.append(
        "The residual salvage value of materials recovered from the final demolition "
        "is credited against the end-of-life stage costs.\n\n"
    )
    sv = debug.get("total_scrap_value", {})
    if isinstance(sv, dict):
        if "formula" in sv:
            lines.append(
                "\\textbf{Formula:} $\\text{scrap\\_value} \\times \\text{SPWI}_{final}$\n\n"
            )
        if "value" in sv:
            lines.append(f"\\textbf{{Value:}} {_fmt(sv['value'])}\n\n")

    return "\n".join(lines) + "\n"


def _section_summary(results: Dict[str, Any]) -> str:
    lines = [_section("Summary --- Total Life Cycle Costs")]
    lines.append(
        "The following table presents the aggregate cost totals for each lifecycle "
        "stage, broken down by economic, environmental, and social cost categories, "
        "along with the overall grand total.\n\n"
    )

    initial = results.get("initial_stage", {})
    use = results.get("use_stage", {})
    recon = results.get("reconstruction", {})
    eol = results.get("end_of_life", {})

    def _stage_total(stage: Dict[str, Any]) -> float:
        total = 0.0
        for cat in ("economic", "environmental", "social"):
            d = stage.get(cat, {})
            if isinstance(d, dict):
                for v in d.values():
                    if isinstance(v, (int, float)):
                        total += v
        return total

    totals = {
        "Initial Construction Stage": _stage_total(initial),
        "Use (Maintenance) Stage": _stage_total(use),
        "Reconstruction Stage": _stage_total(recon) if "Note" not in recon else 0.0,
        "End-of-Life Stage": _stage_total(eol),
    }
    grand_total = sum(totals.values())

    lines.append(r"\begin{table}[H]")
    lines.append(r"\centering")
    lines.append(r"\caption{Life Cycle Cost Summary}")
    lines.append(r"\begin{tabular}{L{9cm}R{5cm}}")
    lines.append(r"\toprule")
    lines.append(r"\textbf{Stage} & \textbf{Total Cost} \\")
    lines.append(r"\midrule")
    for stage_name, total in totals.items():
        lines.append(f"  {stage_name} & {_fmt(total, 2)} \\\\")
    lines.append(r"\midrule")
    lines.append(f"  \\textbf{{Grand Total}} & \\textbf{{{_fmt(grand_total, 2)}}} \\\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    lines.append("\n")

    # Per-category breakdown tables
    for category, label in [
        ("economic", "Economic Costs"),
        ("environmental", "Environmental Costs"),
        ("social", "Social Costs"),
    ]:
        lines.append(f"\\subsection{{{label}}}\n")
        lines.append(r"\begin{table}[H]")
        lines.append(r"\centering")
        lines.append(f"\\caption{{{label} by Stage}}")
        lines.append(r"\begin{tabular}{L{9cm}R{5cm}}")
        lines.append(r"\toprule")
        lines.append(r"\textbf{Line Item} & \textbf{Value} \\")
        lines.append(r"\midrule")

        cat_total = 0.0
        for stage_result, stage_name in [
            (initial, "Initial"),
            (use, "Use"),
            (recon, "Reconstruction"),
            (eol, "End-of-Life"),
        ]:
            d = stage_result.get(category, {})
            if isinstance(d, dict):
                for k, v in d.items():
                    if isinstance(v, (int, float)):
                        cat_total += v
                        lines.append(
                            f"  [{stage_name}] {_key_to_label(k)} & {_fmt(v, 2)} \\\\"
                        )
        lines.append(r"\midrule")
        lines.append(f"  \\textbf{{Subtotal}} & \\textbf{{{_fmt(cat_total, 2)}}} \\\\")
        lines.append(r"\bottomrule")
        lines.append(r"\end{tabular}")
        lines.append(r"\end{table}")
        lines.append("\n")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_latex_report(
    input_data: Dict[str, Any],
    construction_costs: Dict[str, Any],
    results: Dict[str, Any],
    output_path: str = "LCCA_Report.tex",
) -> None:
    """
    Generate a comprehensive LaTeX (.tex) report from LCCA results.

    The function assembles:
      - A title page with project parameters.
      - A construction cost inputs table.
      - Detailed derivation sections for all four lifecycle stages.
      - A final summary table.

    Args:
        input_data (dict): The normalised project input dictionary.
        construction_costs (dict): The construction cost breakdown dictionary.
        results (dict): The LCC results from ``run_full_lcc_analysis`` with
            ``_debug_breakdown`` keys present (requires internal debug mode).
        output_path (str): Destination path for the generated ``.tex`` file.
            Defaults to ``"LCCA_Report.tex"`` in the current directory.
    """
    general = input_data.get("general_parameters", {})

    parts: list[str] = []
    parts.append(_begin_doc())
    parts.append(_title_page(general))
    parts.append(_section_construction_inputs(construction_costs))
    parts.append(_section_initial_stage(results.get("initial_stage", {})))
    parts.append(_section_use_stage(results.get("use_stage", {})))
    parts.append(_section_reconstruction(results.get("reconstruction", {})))
    parts.append(_section_end_of_life(results.get("end_of_life", {})))
    parts.append(_section_summary(results))
    parts.append(_end_doc())

    tex_content = "\n".join(parts)

    # Ensure output directory exists
    out_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(out_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(tex_content)

    print(f"[3psLCCA] LaTeX report written to: {os.path.abspath(output_path)}")
