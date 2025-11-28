"""Tests for install command."""

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from register_apps import cli


@pytest.fixture
def sample_config(tmpdir):
    """Create a sample YAML configuration file."""
    config_file = Path(tmpdir) / "apps.yaml"
    config_data = {
        "defaults": {
            "bindir": str(Path(tmpdir) / "bin"),
            "optdir": str(Path(tmpdir) / "opt"),
            "force": True,
            "container_runtime": "singularity",
            "singularity_path": "singularity",
        },
        "apps": [
            {
                "type": "container",
                "target": "test_tool",
                "command": "test_command",
                "image_repository": "test_repo",
                "image_version": "v1.0.0",
            }
        ],
    }
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")
    return config_file


def test_install_dry_run(sample_config):
    """Test install command with dry-run flag."""
    runner = CliRunner()
    result = runner.invoke(
        cli.install,
        ["--config", str(sample_config), "--dry-run"],
    )

    assert result.exit_code == 0
    assert "DRY RUN" in result.output
    assert "test_tool" in result.output


def test_install_missing_config():
    """Test install command with missing config file."""
    runner = CliRunner()
    result = runner.invoke(
        cli.install,
        ["--config", "/nonexistent/path/apps.yaml"],
    )

    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "error" in result.output.lower()


def test_install_invalid_config(tmpdir):
    """Test install command with invalid config."""
    config_file = Path(tmpdir) / "apps.yaml"
    config_file.write_text("invalid: yaml: content: [", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli.install,
        ["--config", str(config_file)],
    )

    assert result.exit_code != 0


def test_install_filter_containers(tmpdir):
    """Test install command with container filter."""
    config_file = Path(tmpdir) / "apps.yaml"
    config_data = {
        "defaults": {
            "bindir": str(Path(tmpdir) / "bin"),
            "optdir": str(Path(tmpdir) / "opt"),
        },
        "apps": [
            {"type": "container", "target": "tool1", "image_repository": "repo", "image_version": "v1"},
            {"type": "toil", "pypi_name": "tool2", "pypi_version": "v1"},
        ],
    }
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli.install,
        ["--config", str(config_file), "--filter", "container", "--dry-run"],
    )

    assert result.exit_code == 0
    assert "tool1" in result.output
    assert "tool2" not in result.output


def test_install_help():
    """Test install command help."""
    runner = CliRunner()
    result = runner.invoke(cli.install, ["--help"])

    assert result.exit_code == 0
    assert "Install apps from YAML" in result.output
    assert "--config" in result.output
    assert "--filter" in result.output
    assert "--dry-run" in result.output

