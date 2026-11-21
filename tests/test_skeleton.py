"""Basic skeleton tests verifying package metadata and configuration integrity."""

from pathlib import Path

import yaml

import auditiq


def test_package_version() -> None:
    assert auditiq.__version__ == "0.1.0"


def test_config_files_exist_and_valid() -> None:
    config_dir = Path(__file__).parent.parent / "config"
    assert config_dir.exists(), "config directory must exist"

    # Verify ai_bots.yaml
    ai_bots_path = config_dir / "ai_bots.yaml"
    assert ai_bots_path.exists()
    with open(ai_bots_path, encoding="utf-8") as f:
        bots_data = yaml.safe_load(f)
    assert "bots" in bots_data
    assert len(bots_data["bots"]) >= 5

    # Verify scoring.yaml
    scoring_path = config_dir / "scoring.yaml"
    assert scoring_path.exists()
    with open(scoring_path, encoding="utf-8") as f:
        scoring_data = yaml.safe_load(f)
    assert "layer_weights" in scoring_data
    assert round(sum(scoring_data["layer_weights"].values()), 2) == 1.0
