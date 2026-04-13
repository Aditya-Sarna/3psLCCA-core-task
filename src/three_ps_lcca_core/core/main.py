from .stage_cost.stage_cost import StageCostCalculator
from .utils.dump_to_file import dump_to_file
from .utils.input_validator import ironclad_validator
from ..inputs.input_global import InputGlobalMetaData


def run_full_lcc_analysis(
    input_data,
    construction_costs,
    debug=False,
    latex_report=False,
    latex_output_path=None,
):
    """
    Entry point for the OSDAG LCC module (global RUC mode only).
    Validates input, and computes Life Cycle Stage Costs using the
    pre-computed daily_road_user_cost_with_vehicular_emissions.

    Args:
        input_data (dict | InputGlobalMetaData): Project input.
        construction_costs (dict): Initial construction costs.
        debug (bool, optional): If True, dumps intermediate inputs to JSON files.
        latex_report (bool, optional): If True, generates a .tex report file.
            Internally enables debug data collection even if debug=False.
        latex_output_path (str | None, optional): Path for the .tex file.
            Defaults to "LCCA_Report.tex" in the current working directory.

    Returns:
        dict: Stage-wise LCC results (initial, use, reconstruction, end-of-life).

    Raises:
        TypeError: If input_data is of an unexpected type.
        ValueError: If input fails validation or required fields are missing.
    """

    # --- 1. Normalise input_data to dict ---
    if isinstance(input_data, dict):
        gp = input_data.get("general_parameters")
        if gp is None:
            raise ValueError("Missing 'general_parameters' block.")
        InputGlobalMetaData.from_dict(input_data)  # validate structure early

    elif isinstance(input_data, InputGlobalMetaData):
        input_data = input_data.to_dict()

    else:
        raise TypeError("input_data must be a dict or InputGlobalMetaData.")

    # When latex_report=True, enable debug internally to collect breakdown data.
    # File dumps (JSON) only happen when the caller explicitly passed debug=True.
    _effective_debug = debug or latex_report

    # --- 3. Dump all normalised inputs for debugging ---
    if debug:
        dump_to_file(
            "A0_Core_Inputs.json",
            {"input_data": input_data, "construction_costs": construction_costs},
        )

    # --- 4. Validate Input ---
    validation_report = ironclad_validator(input_data)

    if validation_report["errors"]:
        raise ValueError(
            f"Input validation failed with errors:\n{validation_report['errors']}"
        )

    # --- 5. Fetch RUC from input ---
    ruc_results = input_data.get("daily_road_user_cost_with_vehicular_emissions", {})

    # --- 6. Prepare Stage Cost Parameters ---
    stage_params = input_data.get("maintenance_and_stage_parameters", {}).copy()
    stage_params["general"] = input_data.get("general_parameters", {})

    construction_costs["daily_road_user_cost_with_vehicular_emissions"] = ruc_results

    if debug:
        dump_to_file(
            "Stage_Cost_Calculator_Inputs.json",
            {"stage_params": stage_params, "construction_costs": construction_costs},
        )
        dump_to_file("A0_Validation_report.json", validation_report)

    # --- 7. Initialize and Run LCC Calculations ---
    # dump_files=debug ensures JSON dumps only happen when caller set debug=True,
    # while _effective_debug enables breakdown data collection for latex reports.
    stage_calc = StageCostCalculator(
        stage_params, construction_costs, _effective_debug, dump_files=debug
    )

    results = {
        "initial_stage": stage_calc.initial_cost_calculator(),
        "use_stage": stage_calc.use_stage_cost_calculator(),
        "reconstruction": stage_calc.reconstruction(),
        "end_of_life": stage_calc.end_of_life_stage_costs(),
        "warnings": validation_report["warnings"],
        "notes": validation_report["info"],
    }

    # --- 8. Generate LaTeX Report if requested ---
    if latex_report:
        from .latex.report import generate_latex_report

        output_path = latex_output_path if latex_output_path is not None else "LCCA_Report.tex"
        generate_latex_report(
            input_data=input_data,
            construction_costs=construction_costs,
            results=results,
            output_path=output_path,
        )

    return results
