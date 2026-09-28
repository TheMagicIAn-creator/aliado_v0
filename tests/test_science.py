from __future__ import annotations

import copy
import csv
import json
import math

import pytest

from aliado.science import evaluate_scenario, export_result
from aliado.skills.library import load_skill


def scenario(kind="exponential", parameters=None, times=None):
    result = {
        "name": "Exemplo sintético, sem interpretação física",
        "kind": kind,
        "time_unit": "h",
        "parameters": {"rate": 0.01} if parameters is None else parameters,
        "sources": ["Valores sintéticos para teste; não representam um equipamento."],
        "assumptions": ["Condições constantes e tempos na mesma base."],
    }
    if kind != "availability_inherent":
        result["times"] = [0, 100, 200] if times is None else times
    return result


def system(kind, rate=0.01):
    return scenario(kind, {
        "independent": True,
        "components": [
            {"name": name, "model": "exponential", "parameters": {"rate": rate}}
            for name in ("A", "B")
        ],
    })


def test_exponential_matches_published_nist_example():
    result = evaluate_scenario(scenario())
    assert result["summary"]["mttf"] == 100
    assert result["rows"][0] == {
        "time": 0.0, "reliability": 1.0, "failure_probability": 0.0,
        "hazard": 0.01, "hazard_status": "finite",
    }
    assert result["rows"][1]["failure_probability"] == pytest.approx(0.6321205588285577)
    assert result["rows"][1]["reliability"] == pytest.approx(0.36787944117144233)
    assert result["units"]["hazard"] == "1/h"
    assert result["units"]["mttf"] == "h"


def test_weibull_matches_nist_example_and_analytic_mean():
    result = evaluate_scenario(scenario("weibull", {"shape": 1.5, "scale": 5000}, [0, 1000]))
    assert result["rows"][1]["failure_probability"] == pytest.approx(0.085559356392783)
    rayleigh = evaluate_scenario(scenario("weibull", {"shape": 2, "scale": 10}, [0, 10]))
    assert rayleigh["summary"]["mttf"] == pytest.approx(5 * math.sqrt(math.pi))
    assert rayleigh["rows"][1]["hazard"] == pytest.approx(0.2)
    assert rayleigh["rows"][1]["reliability"] == pytest.approx(math.exp(-1))


def test_shape_one_reduces_to_exponential():
    exponential = evaluate_scenario(scenario())
    weibull = evaluate_scenario(scenario("weibull", {"shape": 1, "scale": 100}))
    assert weibull["summary"]["mttf"] == pytest.approx(exponential["summary"]["mttf"])
    for exponential_row, weibull_row in zip(exponential["rows"], weibull["rows"]):
        for key in ("reliability", "failure_probability", "hazard"):
            assert weibull_row[key] == pytest.approx(exponential_row[key])


@pytest.mark.parametrize("shape,expected,status", [(0.5, None, "positive_infinity"), (1, 0.1, "finite"), (2, 0.0, "finite")])
def test_weibull_origin_hazard_is_explicit_and_json_portable(shape, expected, status):
    result = evaluate_scenario(scenario("weibull", {"shape": shape, "scale": 10}))
    assert result["rows"][0]["hazard"] == expected
    assert result["rows"][0]["hazard_status"] == status
    assert json.loads(json.dumps(result, allow_nan=False)) == result


@pytest.mark.parametrize("kind,expected", [("series", 0.25), ("parallel", 0.75)])
def test_independent_system_at_component_median(kind, expected):
    data = system(kind, rate=math.log(2))
    data["times"] = [0, 1]
    result = evaluate_scenario(data)
    assert result["rows"][1]["reliability"] == pytest.approx(expected)
    assert result["rows"][0]["reliability"] == 1
    assert result["rows"][1]["failure_probability"] == pytest.approx(1 - expected)


def test_system_accepts_different_component_models_and_records_method_sources():
    data = system("series")
    data["parameters"]["components"][1] = {
        "name": "B", "model": "weibull", "parameters": {"shape": 2, "scale": 100},
    }
    result = evaluate_scenario(data)
    assert result["rows"][1]["reliability"] == pytest.approx(math.exp(-2))
    assert any("apr162" in source for source in result["method_sources"])


def test_small_series_failure_and_parallel_survival_are_not_rounded_to_zero():
    series = system("series", rate=1e-20)
    series["times"] = [0, 1]
    assert evaluate_scenario(series)["rows"][1]["failure_probability"] == pytest.approx(2e-20, rel=1e-12, abs=0)
    parallel = system("parallel", rate=50)
    parallel["times"] = [0, 1]
    assert evaluate_scenario(parallel)["rows"][1]["reliability"] == pytest.approx(3.8574996959278356e-22, rel=1e-12, abs=0)


def test_exponential_repair_cdf():
    result = evaluate_scenario(scenario("maintainability_exponential", {"mttr": 4}, [0, 4, 8]))
    assert result["rows"][0]["maintainability"] == 0
    assert result["rows"][1]["maintainability"] == pytest.approx(0.6321205588285577)
    assert result["summary"] == {"mttr": 4}


@pytest.mark.parametrize("mtbf,mttr,expected", [(90, 10, 0.9), (90, 0, 1), (1e308, 1e308, 0.5)])
def test_inherent_availability_with_stationary_means(mtbf, mttr, expected):
    result = evaluate_scenario(scenario("availability_inherent", {"mtbf": mtbf, "mttr": mttr}))
    assert result["summary"]["availability_inherent"] == pytest.approx(expected)
    assert "times" not in result
    assert any("operacional" in item for item in result["limitations"])


@pytest.mark.parametrize("kind,parameters", [
    ("exponential", {"rate": 0.1}),
    ("weibull", {"shape": 0.5, "scale": 10}),
    ("weibull", {"shape": 2, "scale": 10}),
])
def test_lifetime_probabilities_are_complementary_and_monotonic(kind, parameters):
    result = evaluate_scenario(scenario(kind, parameters, [0, 0.1, 1, 10, 100, 1000]))
    reliability = [row["reliability"] for row in result["rows"]]
    assert reliability == sorted(reliability, reverse=True)
    for row in result["rows"]:
        assert 0 <= row["reliability"] <= 1
        assert 0 <= row["failure_probability"] <= 1
        assert row["reliability"] + row["failure_probability"] == pytest.approx(1)


def test_scenario_preserves_provenance_and_never_converts_units_or_mutates_inputs():
    data = scenario()
    original = copy.deepcopy(data)
    result = evaluate_scenario(data)
    assert data == original
    assert result["sources"] == data["sources"]
    result["sources"].append("alteração na saída")
    assert data == original
    data["time_unit"] = "year"
    annual = evaluate_scenario(data)
    assert annual["rows"] == result["rows"]
    assert annual["units"]["mttf"] == "year"


def hourly(hours=4015, basis="operation"):
    data = scenario(parameters={"rate": 63.7e-6}, times=[0, 1, 20])
    data["time_unit"] = "year"
    data["time_base"] = {"rate_unit": "h", "hours_per_year": hours, "basis": basis}
    return data


@pytest.mark.parametrize("hours,basis", [(4015, "operation"), (8760, "calendar")])
def test_hourly_rate_converted_to_years_by_the_service(hours, basis):
    data = hourly(hours, basis)
    original = copy.deepcopy(data)
    result = evaluate_scenario(data)
    assert data == original
    assert result["parameters"] == {"rate": 63.7e-6}
    assert result["summary"]["rate"] == pytest.approx(63.7e-6 * hours)
    assert result["units"]["rate"] == "1/year"
    assert result["units"]["parameters.rate"] == "1/h"
    assert result["rows"][1]["failure_probability"] == pytest.approx(1 - math.exp(-63.7e-6 * hours))
    assert result["rows"][2]["reliability"] == pytest.approx(math.exp(-63.7e-6 * hours * 20))
    assert result["summary"]["mttf"] == pytest.approx(1 / (63.7e-6 * hours))
    assert any(f"{hours} h/ano" in item for item in result["limitations"])
    assert not any("Nenhuma conversão" in item for item in result["limitations"])


def test_scenarios_without_time_base_are_unchanged():
    result = evaluate_scenario(scenario())
    assert result["summary"] == {"mttf": 100}
    assert "rate" not in result["units"]
    assert any("Nenhuma conversão" in item for item in result["limitations"])


@pytest.mark.parametrize("change", [
    ("time_unit", "h"), ("kind", "weibull"),
    ("rate_unit", "min"), ("basis", "uptime"), ("basis", ["operation"]),
    ("hours_per_year", 0), ("hours_per_year", 8785), ("hours_per_year", "4015"),
    ("extra", True), ("missing", "basis"),
])
def test_invalid_time_base_rejected(change):
    data = hourly()
    key, value = change
    if key in {"time_unit", "kind"}:
        data[key] = value
        if key == "kind":
            data["parameters"] = {"shape": 1, "scale": 100}
    elif key == "missing":
        del data["time_base"][value]
    else:
        data["time_base"][key] = value
    with pytest.raises(ValueError):
        evaluate_scenario(data)


@pytest.mark.parametrize("value", [True, "0.1", None, -1, 0, float("nan"), float("inf"), 10**400])
def test_invalid_or_unrepresentable_rate_rejected(value):
    with pytest.raises(ValueError):
        evaluate_scenario(scenario(parameters={"rate": value}))


@pytest.mark.parametrize("key,value", [
    ("name", " "), ("kind", "unknown"), ("time_unit", "hours"),
    ("sources", []), ("sources", [""]), ("assumptions", []),
    ("assumptions", "constant"), ("times", []), ("times", [-1]),
    ("times", [0, 0]), ("times", [1, 0]), ("times", [float("inf")]),
    ("times", [True]), ("parameters", []),
])
def test_invalid_common_fields_fail_before_calculation(key, value):
    data = scenario()
    data[key] = value
    with pytest.raises(ValueError):
        evaluate_scenario(data)


@pytest.mark.parametrize("data", [
    None, [], {}, scenario(parameters={"rate": 0.1, "unit": "day"}),
    scenario("weibull", {"shape": 0, "scale": 1}),
    scenario("weibull", {"shape": 1, "scale": -1}),
    scenario("weibull", {"shape": 0.001, "scale": 1}),
    scenario(parameters={"rate": 1e-320}),
    scenario("maintainability_exponential", {"mttr": 0}),
    scenario("availability_inherent", {"mtbf": 0, "mttr": 1}),
    scenario("availability_inherent", {"mtbf": 1, "mttr": -1}),
])
def test_invalid_shape_or_numeric_range_rejected(data):
    with pytest.raises(ValueError):
        evaluate_scenario(data)


@pytest.mark.parametrize("change", ["independence", "empty", "duplicate", "model", "units"])
def test_system_requires_explicit_valid_composition(change):
    data = system("series")
    params = data["parameters"]
    if change == "independence":
        params["independent"] = False
    elif change == "empty":
        params["components"] = []
    elif change == "duplicate":
        params["components"][1]["name"] = "A"
    elif change == "model":
        params["components"][0]["model"] = "normal"
    else:
        params["components"][0]["time_unit"] = "day"
    with pytest.raises(ValueError):
        evaluate_scenario(data)


def test_export_preserves_complete_result_and_refuses_existing_directory(tmp_path):
    result = evaluate_scenario(scenario())
    paths = export_result(result, tmp_path / "run")
    from pathlib import Path

    assert json.loads(Path(paths["json"]).read_text(encoding="utf-8")) == result
    with Path(paths["csv"]).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 3
    assert float(rows[1]["reliability"]) == result["rows"][1]["reliability"]
    report = Path(paths["markdown"]).read_text(encoding="utf-8")
    assert result["sources"][0] in report
    assert result["assumptions"][0] in report
    assert result["method_sources"][0] in report
    before = {path.name: path.read_bytes() for path in (tmp_path / "run").iterdir()}
    with pytest.raises(FileExistsError):
        export_result(result, tmp_path / "run")
    assert before == {path.name: path.read_bytes() for path in (tmp_path / "run").iterdir()}


@pytest.mark.parametrize("kind", ["exponential", "availability_inherent"])
def test_export_optional_plot_uses_headless_backend(tmp_path, kind):
    pytest.importorskip("matplotlib")
    data = scenario() if kind == "exponential" else scenario(kind, {"mtbf": 90, "mttr": 10})
    paths = export_result(evaluate_scenario(data), tmp_path / kind, plot=True)
    from pathlib import Path

    assert Path(paths["png"]).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "![Curvas]" in Path(paths["markdown"]).read_text(encoding="utf-8")


def test_general_skill_has_no_physical_parameters_or_research_defaults():
    skill = load_skill("confiabilidade")
    assert skill.summary.name == "confiabilidade"
    content = skill.instructions
    assert not any(text in content for text in ("20 anos", "GPVS", "p99"))
    assert "MTTF" in content
    assert "MTBF" in content
