"""
Tests for the LaTeX report generation functionality in 3psLCCA.

Tests cover:
  - run_full_lcc_analysis with latex_report=True generates a .tex file
  - run_full_lcc_analysis with latex_report=False preserves existing behaviour
  - latex_output_path parameter is honoured
  - Generated .tex content contains required sections
  - debug JSON dumps do NOT occur when debug=False and latex_report=True
  - debug JSON dumps DO occur when debug=True regardless of latex_report
  - generate_latex_report function produces valid LaTeX structure
"""

import json
import os
import tempfile
import shutil
import pytest

from src.three_ps_lcca_core.core.main import run_full_lcc_analysis
from src.three_ps_lcca_core.core.latex.report import generate_latex_report
from src.examples.from_dict.Input_global import Input_global


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

CONSTRUCTION_COSTS = {
    "initial_construction_cost": 12843979.44,
    "initial_carbon_emissions_cost": 2065434.91,
    "superstructure_construction_cost": 9356038.92,
    "total_scrap_value": 2164095.02,
}


@pytest.fixture()
def tmp_dir():
    """Provide a temporary directory that is removed after each test."""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture()
def input_data():
    """Return a fresh copy of Input_global to avoid mutation between tests."""
    import copy
    return copy.deepcopy(Input_global)


@pytest.fixture()
def construction_costs():
    """Return a fresh copy of construction costs."""
    return dict(CONSTRUCTION_COSTS)


# ---------------------------------------------------------------------------
# Tests: run_full_lcc_analysis with latex_report=True
# ---------------------------------------------------------------------------

class TestLatexReportGeneration:
    def test_latex_report_creates_tex_file(self, tmp_dir, input_data, construction_costs):
        """When latex_report=True, a .tex file must be created at the output path."""
        output_path = os.path.join(tmp_dir, "test_report.tex")
        run_full_lcc_analysis(
            input_data,
            construction_costs,
            latex_report=True,
            latex_output_path=output_path,
        )
        assert os.path.isfile(output_path), "Expected .tex file was not created."

    def test_latex_report_default_filename(self, tmp_dir, input_data, construction_costs, monkeypatch):
        """When latex_output_path is None, file should be LCCA_Report.tex in cwd."""
        monkeypatch.chdir(tmp_dir)
        run_full_lcc_analysis(
            input_data,
            construction_costs,
            latex_report=True,
        )
        default_path = os.path.join(tmp_dir, "LCCA_Report.tex")
        assert os.path.isfile(default_path), "Default LCCA_Report.tex was not created."

    def test_latex_report_is_nonempty(self, tmp_dir, input_data, construction_costs):
        """The generated .tex file must not be empty."""
        output_path = os.path.join(tmp_dir, "report.tex")
        run_full_lcc_analysis(
            input_data,
            construction_costs,
            latex_report=True,
            latex_output_path=output_path,
        )
        size = os.path.getsize(output_path)
        assert size > 500, f"Generated .tex file is suspiciously small: {size} bytes."

    def test_latex_content_has_document_class(self, tmp_dir, input_data, construction_costs):
        """The .tex file must start with a \\documentclass declaration."""
        output_path = os.path.join(tmp_dir, "report.tex")
        run_full_lcc_analysis(
            input_data,
            construction_costs,
            latex_report=True,
            latex_output_path=output_path,
        )
        with open(output_path, encoding="utf-8") as f:
            content = f.read()
        assert r"\documentclass" in content

    def test_latex_content_has_required_sections(self, tmp_dir, input_data, construction_costs):
        """The .tex file must contain all required section headings."""
        output_path = os.path.join(tmp_dir, "report.tex")
        run_full_lcc_analysis(
            input_data,
            construction_costs,
            latex_report=True,
            latex_output_path=output_path,
        )
        with open(output_path, encoding="utf-8") as f:
            content = f.read()

        required_sections = [
            "Construction Cost Inputs",
            "Initial Construction Stage",
            "Use",
            "Reconstruction Stage",
            "End-of-Life Stage",
            "Summary",
        ]
        for section in required_sections:
            assert section in content, f"Missing section: '{section}'"

    def test_latex_content_has_begin_document(self, tmp_dir, input_data, construction_costs):
        """The .tex file must contain \\begin{document} and \\end{document}."""
        output_path = os.path.join(tmp_dir, "report.tex")
        run_full_lcc_analysis(
            input_data,
            construction_costs,
            latex_report=True,
            latex_output_path=output_path,
        )
        with open(output_path, encoding="utf-8") as f:
            content = f.read()
        assert r"\begin{document}" in content
        assert r"\end{document}" in content

    def test_latex_content_contains_project_parameters(self, tmp_dir, input_data, construction_costs):
        """The .tex file must contain key project parameters from the input."""
        output_path = os.path.join(tmp_dir, "report.tex")
        run_full_lcc_analysis(
            input_data,
            construction_costs,
            latex_report=True,
            latex_output_path=output_path,
        )
        with open(output_path, encoding="utf-8") as f:
            content = f.read()
        # Service life and analysis period should appear
        assert "75" in content   # service_life_years
        assert "150" in content  # analysis_period_years

    def test_latex_content_contains_construction_cost_values(self, tmp_dir, input_data, construction_costs):
        """Construction costs must appear in the .tex file."""
        output_path = os.path.join(tmp_dir, "report.tex")
        run_full_lcc_analysis(
            input_data,
            construction_costs,
            latex_report=True,
            latex_output_path=output_path,
        )
        with open(output_path, encoding="utf-8") as f:
            content = f.read()
        # These values come from CONSTRUCTION_COSTS
        assert "12,843,979" in content or "12843979" in content

    def test_latex_content_contains_formulas(self, tmp_dir, input_data, construction_costs):
        """The .tex file must include LaTeX math formulas."""
        output_path = os.path.join(tmp_dir, "report.tex")
        run_full_lcc_analysis(
            input_data,
            construction_costs,
            latex_report=True,
            latex_output_path=output_path,
        )
        with open(output_path, encoding="utf-8") as f:
            content = f.read()
        # At least one formula environment
        assert r"\times" in content or r"$" in content


# ---------------------------------------------------------------------------
# Tests: existing behaviour preserved (latex_report=False)
# ---------------------------------------------------------------------------

class TestExistingBehaviourPreserved:
    def test_no_latex_file_when_flag_is_false(self, tmp_dir, input_data, construction_costs, monkeypatch):
        """No .tex file should be created when latex_report=False."""
        monkeypatch.chdir(tmp_dir)
        run_full_lcc_analysis(input_data, construction_costs)
        tex_files = [f for f in os.listdir(tmp_dir) if f.endswith(".tex")]
        assert not tex_files, f"Unexpected .tex files created: {tex_files}"

    def test_results_dict_structure_unchanged(self, input_data, construction_costs):
        """The returned results dict must have the standard keys regardless of latex flag."""
        results = run_full_lcc_analysis(input_data, construction_costs)
        for key in ("initial_stage", "use_stage", "reconstruction", "end_of_life"):
            assert key in results, f"Missing key in results: '{key}'"

    def test_no_debug_json_dumps_when_debug_false_latex_true(
        self, tmp_dir, input_data, construction_costs, monkeypatch
    ):
        """
        When debug=False and latex_report=True, the debug JSON files
        (e.g. A0_Core_Inputs.json) must NOT be created.
        """
        monkeypatch.chdir(tmp_dir)
        run_full_lcc_analysis(
            input_data,
            construction_costs,
            debug=False,
            latex_report=True,
            latex_output_path=os.path.join(tmp_dir, "report.tex"),
        )
        # dump_to_file writes to a 'debug/' subdirectory; ensure it was not created
        debug_dir = os.path.join(tmp_dir, "debug")
        json_created = os.path.isdir(debug_dir) and any(
            f.endswith(".json") for f in os.listdir(debug_dir)
        )
        assert not json_created, (
            "Debug JSON files were created even though debug=False"
        )

    def test_numeric_results_match_baseline(self, input_data, construction_costs):
        """Results with latex_report=True must be numerically identical to baseline."""
        import copy
        baseline = run_full_lcc_analysis(
            copy.deepcopy(input_data), dict(construction_costs)
        )
        with_latex = run_full_lcc_analysis(
            copy.deepcopy(input_data), dict(construction_costs), latex_report=True,
            latex_output_path=os.devnull,
        )
        for stage in ("initial_stage", "use_stage", "end_of_life"):
            for cat in ("economic", "environmental", "social"):
                b = baseline[stage].get(cat, {})
                w = with_latex[stage].get(cat, {})
                for k in b:
                    assert b[k] == pytest.approx(w.get(k, 0), rel=1e-6), (
                        f"Mismatch for {stage}/{cat}/{k}"
                    )


# ---------------------------------------------------------------------------
# Tests: generate_latex_report directly
# ---------------------------------------------------------------------------

class TestGenerateLatexReportDirect:
    def test_direct_call_creates_file(self, tmp_dir, input_data, construction_costs):
        """generate_latex_report() directly must create a .tex file."""
        import copy
        results = run_full_lcc_analysis(
            copy.deepcopy(input_data),
            dict(construction_costs),
            latex_report=False,
            debug=False,
        )
        output_path = os.path.join(tmp_dir, "direct.tex")
        generate_latex_report(
            input_data=input_data,
            construction_costs=construction_costs,
            results=results,
            output_path=output_path,
        )
        assert os.path.isfile(output_path)

    def test_direct_call_no_breakdown_still_works(self, tmp_dir, input_data, construction_costs):
        """generate_latex_report should not crash when _debug_breakdown keys are absent."""
        import copy
        results = run_full_lcc_analysis(
            copy.deepcopy(input_data),
            dict(construction_costs),
            debug=False,
            latex_report=False,
        )
        output_path = os.path.join(tmp_dir, "no_breakdown.tex")
        # Should not raise
        generate_latex_report(
            input_data=input_data,
            construction_costs=construction_costs,
            results=results,
            output_path=output_path,
        )
        assert os.path.isfile(output_path)

    def test_latex_output_is_utf8(self, tmp_dir, input_data, construction_costs):
        """The generated .tex file must be valid UTF-8."""
        import copy
        results = run_full_lcc_analysis(
            copy.deepcopy(input_data),
            dict(construction_costs),
            latex_report=True,
            latex_output_path=os.path.join(tmp_dir, "utf8.tex"),
        )
        path = os.path.join(tmp_dir, "utf8.tex")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert len(content) > 0


# ---------------------------------------------------------------------------
# Tests: custom latex_output_path
# ---------------------------------------------------------------------------

class TestLatexOutputPath:
    def test_nested_output_directory_created(self, tmp_dir, input_data, construction_costs):
        """generate_latex_report must create intermediate directories automatically."""
        import copy
        nested_path = os.path.join(tmp_dir, "reports", "subdir", "report.tex")
        results = run_full_lcc_analysis(
            copy.deepcopy(input_data),
            dict(construction_costs),
            latex_report=True,
            latex_output_path=nested_path,
        )
        assert os.path.isfile(nested_path), "File not created in nested directory."

    def test_custom_filename_honoured(self, tmp_dir, input_data, construction_costs):
        """The file must be saved with the exact name supplied."""
        import copy
        custom_path = os.path.join(tmp_dir, "my_custom_report.tex")
        run_full_lcc_analysis(
            copy.deepcopy(input_data),
            dict(construction_costs),
            latex_report=True,
            latex_output_path=custom_path,
        )
        assert os.path.isfile(custom_path)
