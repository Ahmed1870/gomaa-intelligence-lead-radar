import pathlib
import subprocess
import sys
from unittest.mock import patch

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))

from app.discovery.engine import runtime_budget_exceeded


def test_runtime_budget_exceeded_checks_elapsed_time():
    with patch("app.discovery.engine.time.monotonic", return_value=105.0):
        assert runtime_budget_exceeded(100.0, 10) is False
    with patch("app.discovery.engine.time.monotonic", return_value=111.0):
        assert runtime_budget_exceeded(100.0, 10) is True


def test_discover_cli_exposes_runtime_budget_flag():
    repo_root = pathlib.Path(__file__).parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "app", "discover", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--max-runtime-seconds" in result.stdout


def test_discovery_workflow_has_bounded_inputs_and_updated_actions():
    workflow_path = pathlib.Path(__file__).parents[1] / ".github/workflows/discovery.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    trigger = workflow.get("on", workflow.get(True))
    inputs = trigger["workflow_dispatch"]["inputs"]
    assert inputs["task_limit"]["default"] == "60"
    assert inputs["max_pages"]["default"] == "12"
    assert inputs["max_runtime_seconds"]["default"] == "2400"

    job = workflow["jobs"]["discovery"]
    assert job["runs-on"] == "ubuntu-24.04"

    steps = job["steps"]
    assert any(step.get("uses") == "actions/checkout@v5" for step in steps)
    assert any(step.get("uses") == "actions/setup-python@v6" for step in steps)
    assert any(step.get("uses") == "actions/cache@v5" for step in steps)

    discover_step = next(step for step in steps if "python -m app discover" in step.get("run", ""))
    assert "--max-runtime-seconds" in discover_step["run"]
