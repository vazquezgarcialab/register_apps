"""register_apps cli tests."""

# pylint: disable=E1135
import os
import subprocess

from click.testing import CliRunner
import pytest

from register_apps import cli
from register_apps import utils as register_utils
from tests import utils


SKIP_SINGULARITY = pytest.mark.skipif(
    not utils.is_executable_available("singularity"),
    reason="singularity is not available.",
)


SKIP_DOCKER = pytest.mark.skipif(
    not utils.is_executable_available("docker"), reason="docker is not installed."
)


def _require_virtualenvwrapper():
    """Require virtualenvwrapper to be available, fail if not."""
    if not register_utils.is_virtualenvwrapper_configured():
        pytest.fail(
            "virtualenvwrapper is not available. "
            "Please install virtualenvwrapper and ensure it's configured."
        )


def run_register_container(tmpdir, container_runtime):
    runner = CliRunner()
    optdir = tmpdir.mkdir("opt")
    bindir = tmpdir.mkdir("bin")
    optexe = optdir.join("alpine", "latest", "test_cmd")
    binexe = bindir.join("test_cmd")
    container_cli = (
        cli.register_docker
        if container_runtime == "docker"
        else cli.register_singularity
    )

    args = [
        "--image_url",
        "alpine:latest",
        "--image_repository",
        "alpine",
        "--image_version",
        "latest",
        "--volumes",
        "/tmp",
        "/tmp",
        "--optdir",
        optdir.strpath,
        "--bindir",
        bindir.strpath,
        "--tmpvar",
        "$TMPDIR",
        "--command",
        "echo",
        "--target",
        "test_cmd",
    ]
    result = runner.invoke(container_cli, args, catch_exceptions=False)
    assert result.exit_code == 0, (
        f"Failed to register container: {result.exception}\n" f"Output: {result.output}"
    )

    # Check if the executable files were created
    assert os.path.exists(
        optexe.strpath
    ), "Container registration failed - optexe not created"
    assert os.path.exists(
        binexe.strpath
    ), "Container registration failed - binexe not created"

    # Try to run the command - should fail if Docker isn't running or image unavailable
    for i in optexe.strpath, binexe.strpath:
        try:
            output = subprocess.check_output(
                args=[i, "test-output"],
                env={"TMP": "/tmp", "USER": "root"},
                stderr=subprocess.STDOUT,
                timeout=10,
            )
            # Alpine's echo should output the argument
            assert b"test-output" in output
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ) as e:
            # Fail if container execution fails - Docker should be running
            pytest.fail(f"Container command execution failed: {e}. ")

    assert (
        "--volume /tmp:/tmp"
        if container_runtime == "docker"
        else "--bind /tmp:/tmp" in optexe.read()
    )
    assert "--workdir $TMP" in optexe.read()
    assert not runner.invoke(container_cli, ["--help"]).exit_code


@SKIP_DOCKER
def test_register_docker(tmpdir):
    """Sample test for register_docker command."""
    run_register_container(tmpdir, container_runtime="docker")


@SKIP_SINGULARITY
def test_register_singularity(tmpdir):
    """Sample test for register_singularity command."""
    run_register_container(tmpdir, container_runtime="singularity")


@SKIP_SINGULARITY
def test_register_toil(tmpdir):
    """Sample test for register_toil command."""
    _require_virtualenvwrapper()
    runner = CliRunner()
    optdir = tmpdir.mkdir("opt")
    bindir = tmpdir.mkdir("bin")
    optexe = optdir.join("toil_container", "v2.0.3", "toil_container")
    binexe = bindir.join("toil_container_v2.0.3")
    result = runner.invoke(
        cli.register_toil,
        [
            "--pypi_name",
            "toil_container",
            "--pypi_version",
            "v2.0.3",
            "--image_user",
            "leukgen",
            "--volumes",
            "/tmp",
            "/carlos",
            "--optdir",
            optdir.strpath,
            "--bindir",
            bindir.strpath,
            "--tmpvar",
            "$TMP",
            "--python",
            "python3",
        ],
    )

    assert result.exit_code == 0, (
        f"Failed to register toil: {result.exception}\n" f"Output: {result.output}"
    )

    # Check that virtualenvwrapper environment was created
    # Venvs are stored in ~/.virtualenvs/ with name production__toil_container__v2.0.3
    import os

    workon_home = os.getenv("WORKON_HOME", os.path.expanduser("~/.virtualenvs"))
    venv_path = os.path.join(workon_home, "production__toil_container__v2.0.3")
    assert os.path.exists(venv_path), f"Virtual environment not created at {venv_path}"

    for i in optexe.strpath, binexe.strpath:
        assert b"0.1.2" in subprocess.check_output(
            args=[i, "--version"], env={"TMP": "/tmp"}, stderr=subprocess.STDOUT
        )

    assert "--volumes /tmp /carlos" in optexe.read()
    assert "--workDir $TMP" in optexe.read()
    assert not runner.invoke(cli.register_toil, ["--help"]).exit_code


def test_register_python(tmpdir):
    """Sample test for register_python command."""
    _require_virtualenvwrapper()
    runner = CliRunner()
    optdir = tmpdir.mkdir("opt")
    bindir = tmpdir.mkdir("bin")
    # Use 'black' which is a code formatter tool with a CLI command
    optexe = optdir.join("black", "23.12.1", "black")
    binexe = bindir.join("black_23.12.1")
    result = runner.invoke(
        cli.register_python,
        [
            "--pypi_name",
            "black",
            "--pypi_version",
            "23.12.1",
            "--optdir",
            optdir.strpath,
            "--bindir",
            bindir.strpath,
            "--python",
            "python3",
        ],
    )

    if result.exit_code != 0:
        # Print more detailed error information
        error_msg = "Package installation failed:\n"
        error_msg += f"  Exit code: {result.exit_code}\n"
        if result.exception:
            error_msg += f"  Exception: {result.exception}\n"
        error_msg += f"  Output: {result.output}\n"
        if hasattr(result, "stderr_bytes") and result.stderr_bytes:
            stderr_text = result.stderr_bytes.decode("utf-8", errors="ignore")
            error_msg += f"  Stderr: {stderr_text}\n"
        if hasattr(result, "stdout_bytes") and result.stdout_bytes:
            stdout_text = result.stdout_bytes.decode("utf-8", errors="ignore")
            error_msg += f"  Stdout: {stdout_text}\n"
        pytest.fail(error_msg)

    # Check that virtualenvwrapper environment was created
    import os

    workon_home = os.getenv("WORKON_HOME", os.path.expanduser("~/.virtualenvs"))
    venv_path = os.path.join(workon_home, "production__black__23.12.1")
    assert os.path.exists(venv_path), f"Virtual environment not created at {venv_path}"

    # Check that wrapper script was created
    assert os.path.exists(optexe.strpath), "Wrapper script not created"
    assert os.path.exists(binexe.strpath), "Symlink not created"

    # Verify the script content is correct
    script_content = optexe.read()
    assert "#!/bin/bash" in script_content
    assert "black" in script_content

    # Try to run the executable to verify it works
    for i in optexe.strpath, binexe.strpath:
        try:
            output = subprocess.check_output(
                args=[i, "--version"],
                stderr=subprocess.STDOUT,
                timeout=10,
            )
            assert b"black" in output.lower() or b"23.12" in output
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ) as e:
            pytest.fail(f"Cannot execute command (package may not be available): {e}")

    assert not runner.invoke(cli.register_python, ["--help"]).exit_code


def test_register_python_github(tmpdir):
    """Sample test for register_python command with GitHub source."""
    _require_virtualenvwrapper()
    runner = CliRunner()
    optdir = tmpdir.mkdir("opt")
    bindir = tmpdir.mkdir("bin")
    # Use 'black' which is a code formatter tool with a CLI command
    optexe = optdir.join("black", "23.12.1", "black")
    binexe = bindir.join("black_23.12.1")
    result = runner.invoke(
        cli.register_python,
        [
            "--pypi_name",
            "black",
            "--pypi_version",
            "23.12.1",
            "--optdir",
            optdir.strpath,
            "--bindir",
            bindir.strpath,
            "--github_user",
            "psf",
            "--python",
            "python3",
        ],
    )

    if result.exit_code != 0:
        # Print more detailed error information
        error_msg = "Package installation failed:\n"
        error_msg += f"  Exit code: {result.exit_code}\n"
        if result.exception:
            error_msg += f"  Exception: {result.exception}\n"
        error_msg += f"  Output: {result.output}\n"
        if hasattr(result, "stderr_bytes") and result.stderr_bytes:
            stderr_text = result.stderr_bytes.decode("utf-8", errors="ignore")
            error_msg += f"  Stderr: {stderr_text}\n"
        if hasattr(result, "stdout_bytes") and result.stdout_bytes:
            stdout_text = result.stdout_bytes.decode("utf-8", errors="ignore")
            error_msg += f"  Stdout: {stdout_text}\n"
        pytest.fail(error_msg)

    # Check that virtualenvwrapper environment was created
    import os

    workon_home = os.getenv("WORKON_HOME", os.path.expanduser("~/.virtualenvs"))
    venv_path = os.path.join(workon_home, "production__black__23.12.1")
    assert os.path.exists(venv_path), f"Virtual environment not created at {venv_path}"

    # Check that wrapper script was created
    assert os.path.exists(optexe.strpath), "Wrapper script not created"
    assert os.path.exists(binexe.strpath), "Symlink not created"

    # Verify the script content is correct
    script_content = optexe.read()
    assert "#!/bin/bash" in script_content
    assert "black" in script_content

    # Try to run the executable to verify it works
    for i in optexe.strpath, binexe.strpath:
        try:
            output = subprocess.check_output(
                args=[i, "--version"],
                stderr=subprocess.STDOUT,
                timeout=10,
            )
            assert b"black" in output.lower() or b"23.12" in output
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ) as e:
            pytest.fail(f"Cannot execute command (package may not be available): {e}")

    assert not runner.invoke(cli.register_python, ["--help"]).exit_code
