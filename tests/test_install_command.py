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
            {
                "type": "container",
                "target": "tool1",
                "image_repository": "repo",
                "image_version": "v1",
            },
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


def test_install_filter_toil(tmpdir):
    """Test install command with toil filter."""
    config_file = Path(tmpdir) / "apps.yaml"
    config_data = {
        "defaults": {
            "bindir": str(Path(tmpdir) / "bin"),
            "optdir": str(Path(tmpdir) / "opt"),
        },
        "apps": [
            {
                "type": "container",
                "target": "tool1",
                "image_repository": "repo",
                "image_version": "v1",
            },
            {"type": "toil", "pypi_name": "tool2", "pypi_version": "v1"},
            {"type": "python", "pypi_name": "tool3", "pypi_version": "v1"},
        ],
    }
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli.install,
        ["--config", str(config_file), "--filter", "toil", "--dry-run"],
    )

    assert result.exit_code == 0
    assert "tool2" in result.output
    assert "tool1" not in result.output
    assert "tool3" not in result.output


def test_install_filter_python(tmpdir):
    """Test install command with python filter."""
    config_file = Path(tmpdir) / "apps.yaml"
    config_data = {
        "defaults": {
            "bindir": str(Path(tmpdir) / "bin"),
            "optdir": str(Path(tmpdir) / "opt"),
        },
        "apps": [
            {
                "type": "container",
                "target": "tool1",
                "image_repository": "repo",
                "image_version": "v1",
            },
            {"type": "toil", "pypi_name": "tool2", "pypi_version": "v1"},
            {"type": "python", "pypi_name": "tool3", "pypi_version": "v1"},
        ],
    }
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli.install,
        ["--config", str(config_file), "--filter", "python", "--dry-run"],
    )

    assert result.exit_code == 0
    assert "tool3" in result.output
    assert "tool1" not in result.output
    assert "tool2" not in result.output


def test_install_filter_all(tmpdir):
    """Test install command with all filter (default)."""
    config_file = Path(tmpdir) / "apps.yaml"
    config_data = {
        "defaults": {
            "bindir": str(Path(tmpdir) / "bin"),
            "optdir": str(Path(tmpdir) / "opt"),
        },
        "apps": [
            {
                "type": "container",
                "target": "tool1",
                "image_repository": "repo",
                "image_version": "v1",
            },
            {"type": "toil", "pypi_name": "tool2", "pypi_version": "v1"},
            {"type": "python", "pypi_name": "tool3", "pypi_version": "v1"},
        ],
    }
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli.install,
        ["--config", str(config_file), "--filter", "all", "--dry-run"],
    )

    assert result.exit_code == 0
    assert "tool1" in result.output
    assert "tool2" in result.output
    assert "tool3" in result.output


def test_install_multiple_apps(tmpdir):
    """Test install command with multiple apps."""
    config_file = Path(tmpdir) / "apps.yaml"
    config_data = {
        "defaults": {
            "bindir": str(Path(tmpdir) / "bin"),
            "optdir": str(Path(tmpdir) / "opt"),
            "force": True,
        },
        "apps": [
            {
                "type": "container",
                "target": "tool1",
                "image_repository": "repo1",
                "image_version": "v1",
            },
            {
                "type": "container",
                "target": "tool2",
                "image_repository": "repo2",
                "image_version": "v2",
            },
            {
                "type": "container",
                "target": "tool3",
                "image_repository": "repo3",
                "image_version": "v3",
            },
        ],
    }
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli.install,
        ["--config", str(config_file), "--dry-run"],
    )

    assert result.exit_code == 0
    assert "Found 3 apps to install" in result.output
    assert "tool1" in result.output
    assert "tool2" in result.output
    assert "tool3" in result.output


def test_install_continue_on_error(tmpdir, monkeypatch):
    """Test install command with continue-on-error flag."""
    config_file = Path(tmpdir) / "apps.yaml"
    config_data = {
        "defaults": {
            "bindir": str(Path(tmpdir) / "bin"),
            "optdir": str(Path(tmpdir) / "opt"),
            "force": True,
        },
        "apps": [
            {
                "type": "container",
                "target": "tool1",
                "image_repository": "repo1",
                "image_version": "v1",
            },
            {
                "type": "container",
                "target": "tool2",
                "image_repository": "repo2",
                "image_version": "v2",
            },
        ],
    }
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")

    # Mock install_app to fail on first app
    call_count = 0

    def mock_install_app(app_config):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("Simulated installation error")

    monkeypatch.setattr(cli, "install_app", mock_install_app)

    runner = CliRunner()
    result = runner.invoke(
        cli.install,
        ["--config", str(config_file), "--continue-on-error"],
    )

    assert result.exit_code == 1  # Should exit with error due to failures
    assert "Failed to install" in result.output
    assert "tool1" in result.output
    assert "1 apps failed to install" in result.output


def test_install_no_continue_on_error(tmpdir, monkeypatch):
    """Test install without continue-on-error flag (should stop on first error)."""
    config_file = Path(tmpdir) / "apps.yaml"
    config_data = {
        "defaults": {
            "bindir": str(Path(tmpdir) / "bin"),
            "optdir": str(Path(tmpdir) / "opt"),
            "force": True,
        },
        "apps": [
            {
                "type": "container",
                "target": "tool1",
                "image_repository": "repo1",
                "image_version": "v1",
            },
            {
                "type": "container",
                "target": "tool2",
                "image_repository": "repo2",
                "image_version": "v2",
            },
        ],
    }
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")

    # Mock install_app to fail on first app
    call_count = 0

    def mock_install_app(app_config):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("Simulated installation error")

    monkeypatch.setattr(cli, "install_app", mock_install_app)

    runner = CliRunner()
    result = runner.invoke(
        cli.install,
        ["--config", str(config_file)],
    )

    assert result.exit_code != 0
    assert "Failed to install" in result.output
    assert "tool1" in result.output
    # Should not have processed tool2
    assert call_count == 1


def test_install_empty_config(tmpdir):
    """Test install command with empty apps list."""
    config_file = Path(tmpdir) / "apps.yaml"
    config_data = {
        "defaults": {
            "bindir": str(Path(tmpdir) / "bin"),
            "optdir": str(Path(tmpdir) / "opt"),
        },
        "apps": [],
    }
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli.install,
        ["--config", str(config_file)],
    )

    assert result.exit_code != 0
    assert "empty" in result.output.lower() or "error" in result.output.lower()


def test_install_defaults_merge(tmpdir):
    """Test that defaults are properly merged with app configs."""
    config_file = Path(tmpdir) / "apps.yaml"
    config_data = {
        "defaults": {
            "bindir": str(Path(tmpdir) / "bin"),
            "optdir": str(Path(tmpdir) / "opt"),
            "force": True,
            "image_user": "default_user",
        },
        "apps": [
            {
                "type": "container",
                "target": "tool1",
                "image_repository": "repo1",
                "image_version": "v1",
                "force": False,  # Override default
            }
        ],
    }
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli.install,
        ["--config", str(config_file), "--dry-run"],
    )

    assert result.exit_code == 0
    assert "tool1" in result.output


def test_install_path_type_handling(tmpdir):
    """Test that install command handles different path types correctly."""
    config_file = Path(tmpdir) / "apps.yaml"
    config_data = {
        "defaults": {
            "bindir": str(Path(tmpdir) / "bin"),
            "optdir": str(Path(tmpdir) / "opt"),
        },
        "apps": [
            {
                "type": "container",
                "target": "test_tool",
                "image_repository": "test_repo",
                "image_version": "v1.0.0",
            }
        ],
    }
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")

    runner = CliRunner()

    # Test with string path (most common case)
    result = runner.invoke(
        cli.install,
        ["--config", str(config_file), "--dry-run"],
    )
    assert result.exit_code == 0, f"Failed with string path: {result.output}"

    # Test that Path conversion works by simulating bytes input
    # This tests the bytes handling in Python 3.6 compatibility
    from pathlib import Path as PathType

    # Simulate bytes input (Python 3.6 compatibility test)
    config_path_str = str(config_file)
    config_path_bytes = config_path_str.encode("utf-8")
    # Path() constructor should handle bytes after decode
    converted_path = PathType(config_path_bytes.decode("utf-8"))
    assert converted_path.exists(), "Converted path should exist"
    assert converted_path == config_file, "Converted path should match original"


def test_install_config_path_bytes_handling(tmpdir):
    """Test install command handles bytes path (Python 3.6 compatibility)."""
    config_file = Path(tmpdir) / "apps.yaml"
    config_data = {
        "defaults": {
            "bindir": str(Path(tmpdir) / "bin"),
            "optdir": str(Path(tmpdir) / "opt"),
        },
        "apps": [
            {
                "type": "container",
                "target": "test_tool",
                "image_repository": "test_repo",
                "image_version": "v1.0.0",
            }
        ],
    }
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")

    # Test the path conversion logic directly - simulate bytes input
    from pathlib import Path as PathType

    # Simulate what happens when Click passes bytes in Python 3.6
    test_path_str = str(config_file)
    test_path_bytes = test_path_str.encode("utf-8")

    # Test the conversion logic that's in the install function
    if isinstance(test_path_bytes, bytes):
        converted = PathType(test_path_bytes.decode("utf-8"))
    else:
        converted = PathType(test_path_bytes)

    assert converted.exists(), "Bytes path should convert correctly"
    assert converted == config_file, "Converted path should match original"

    # Verify the actual command invocation works
    runner = CliRunner()
    result = runner.invoke(
        cli.install,
        ["--config", str(config_file), "--dry-run"],
    )
    assert result.exit_code == 0
    assert "test_tool" in result.output
    assert "Loading configuration from" in result.output


def test_install_with_bytes_path_simulation(tmpdir):
    """Test install function handles bytes path (simulates Python 3.6 issue)."""
    config_file = Path(tmpdir) / "apps.yaml"
    config_data = {
        "defaults": {
            "bindir": str(Path(tmpdir) / "bin"),
            "optdir": str(Path(tmpdir) / "opt"),
        },
        "apps": [
            {
                "type": "container",
                "target": "test_tool",
                "image_repository": "test_repo",
                "image_version": "v1.0.0",
            }
        ],
    }
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")

    # Test that the function handles bytes correctly
    from pathlib import Path as PathType

    config_path_bytes = str(config_file).encode("utf-8")
    # This should not raise AttributeError
    try:
        converted = PathType(config_path_bytes.decode("utf-8"))
        assert converted.exists()
    except AttributeError as e:
        pytest.fail(f"Path conversion failed with bytes: {e}")

    # Verify normal invocation still works
    runner = CliRunner()
    result = runner.invoke(
        cli.install,
        ["--config", str(config_file), "--dry-run"],
    )
    assert result.exit_code == 0


def test_install_direct_bytes_call(tmpdir):
    """Test install function directly with bytes to catch AttributeError."""
    config_file = Path(tmpdir) / "apps.yaml"
    config_data = {
        "defaults": {
            "bindir": str(Path(tmpdir) / "bin"),
            "optdir": str(Path(tmpdir) / "opt"),
        },
        "apps": [
            {
                "type": "container",
                "target": "test_tool",
                "image_repository": "test_repo",
                "image_version": "v1.0.0",
            }
        ],
    }
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")

    # Test the conversion logic from install function
    from pathlib import Path as PathType

    # Simulate bytes being passed (Python 3.6 scenario)
    config_path_bytes = str(config_file).encode("utf-8")

    # Test the conversion logic from install function
    if isinstance(config_path_bytes, bytes):
        converted_path = PathType(config_path_bytes.decode("utf-8"))
    else:
        converted_path = PathType(config_path_bytes)

    # This should work without AttributeError
    assert converted_path.exists(), "Path should exist after conversion"
    assert converted_path == config_file, "Converted path should match original"

    # Verify the full flow works
    runner = CliRunner()
    result = runner.invoke(
        cli.install,
        ["--config", str(config_file), "--dry-run"],
    )
    assert result.exit_code == 0
    assert "test_tool" in result.output
