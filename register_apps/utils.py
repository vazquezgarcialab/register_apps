"""register_apps utils."""

import os
import shutil
import subprocess
import tarfile
from pathlib import Path


def force_link(src, dst):
    """Force a link between src and dst."""
    try:
        os.unlink(dst)
        os.link(src, dst)
    except OSError:
        os.link(src, dst)


def force_symlink(src, dst):
    """Force a symlink between src and dst."""
    try:
        os.unlink(dst)
        os.symlink(src, dst)
    except OSError:
        os.symlink(src, dst)


def tar_dir(output_path, source_dir):
    """Compress a `source_dir` in `output_path`."""
    with tarfile.open(output_path, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))


def check_uv_available():
    """Check if uv is available in PATH."""
    uv_path = shutil.which("uv")
    if not uv_path:
        raise RuntimeError(
            "uv is not available. Please install uv: "
            "https://github.com/astral-sh/uv#installation"
        )
    return uv_path


def create_venv_with_uv(venv_path, python_interpreter):
    """
    Create virtual environment using uv.

    Args:
        venv_path: Path where the virtual environment will be created.
        python_interpreter: Python interpreter to use (e.g., 'python3', 'python3.9').

    Raises:
        subprocess.CalledProcessError: If uv command fails.
        RuntimeError: If uv is not available.
    """
    check_uv_available()
    venv_path = Path(venv_path)
    venv_path.parent.mkdir(parents=True, exist_ok=True)

    subprocess.check_output(
        [
            "uv",
            "venv",
            "--python",
            python_interpreter,
            str(venv_path),
        ],
        stderr=subprocess.STDOUT,
    )


def install_package_with_uv(venv_path, package_spec, pre_install=None):
    """
    Install package in venv using uv.

    Args:
        venv_path: Path to the virtual environment.
        package_spec: Package specification (e.g., 'package==1.0.0' or
                     'git+https://github.com/user/repo@tag#egg=package').
        pre_install: Optional list of package specs to install before main package.

    Raises:
        subprocess.CalledProcessError: If uv command fails.
        RuntimeError: If uv is not available.
    """
    check_uv_available()
    venv_path = Path(venv_path)
    python_exe = venv_path / "bin" / "python"

    if not python_exe.exists():
        raise FileNotFoundError(f"Python executable not found: {python_exe}")

    # Install pre-install packages if specified
    if pre_install:
        for pre_pkg in pre_install:
            subprocess.check_output(
                [
                    "uv",
                    "pip",
                    "install",
                    "--python",
                    str(python_exe),
                    pre_pkg,
                ],
                stderr=subprocess.STDOUT,
            )

    # Install main package
    subprocess.check_output(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python_exe),
            package_spec,
        ],
        stderr=subprocess.STDOUT,
    )


def find_executable_in_venv(venv_path, command_name):
    """
    Find executable in virtual environment.

    Args:
        venv_path: Path to the virtual environment.
        command_name: Name of the command/executable to find.

    Returns:
        Path: Path to the executable.

    Raises:
        FileNotFoundError: If executable is not found.
    """
    venv_path = Path(venv_path)
    exe_path = venv_path / "bin" / command_name

    if exe_path.exists():
        return exe_path

    # Try variations (e.g., with different extensions or prefixes)
    bin_dir = venv_path / "bin"
    if bin_dir.exists():
        # Look for exact match first
        for pattern in [command_name, f"{command_name}*"]:
            matches = list(bin_dir.glob(pattern))
            if matches:
                return matches[0]

    raise FileNotFoundError(
        f"Executable '{command_name}' not found in {venv_path}/bin"
    )
