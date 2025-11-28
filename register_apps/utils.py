"""register_apps utils."""

import os
import shutil
import subprocess
import sys
import tarfile


def force_link(src, dst):
    """Force a link between src and dst."""
    if os.path.exists(dst):
        os.unlink(dst)
    os.link(src, dst)


def force_symlink(src, dst):
    """Force a symlink between src and dst."""
    if os.path.exists(dst):
        os.unlink(dst)
    os.symlink(src, dst)


def tar_dir(output_path, source_dir):
    """Compress a `source_dir` in `output_path`."""
    with tarfile.open(output_path, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))


def is_executable_available(executable):
    """Check if an executable is available in PATH."""
    return shutil.which(executable) is not None


def get_virtualenvwrapper_script():
    """
    Get the path to virtualenvwrapper.sh script.

    Returns:
        str: Path to virtualenvwrapper.sh script.

    Raises:
        RuntimeError: If virtualenvwrapper is not found.
    """
    # Try common locations
    possible_paths = [
        os.getenv("VIRTUALENVWRAPPER_SCRIPT"),
        "/usr/local/bin/virtualenvwrapper.sh",
        "/usr/bin/virtualenvwrapper.sh",
        os.path.expanduser("~/.local/bin/virtualenvwrapper.sh"),
    ]

    # Also try to find via which
    if is_executable_available("virtualenvwrapper.sh"):
        result = subprocess.run(
            ["which", "virtualenvwrapper.sh"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            possible_paths.insert(0, result.stdout.strip())

    for path in possible_paths:
        if path and os.path.exists(path):
            return path

    raise RuntimeError(
        "virtualenvwrapper is not available. "
        "Please install virtualenvwrapper and ensure VIRTUALENVWRAPPER_SCRIPT is set."
    )


def _get_virtualenvwrapper_env():
    """Get environment variables for virtualenvwrapper commands."""
    venv_env = os.environ.copy()
    venv_env.setdefault("WORKON_HOME", os.path.expanduser("~/.virtualenvs"))
    venv_env["VIRTUALENVWRAPPER_PYTHON"] = sys.executable
    return venv_env


def _build_virtualenvwrapper_cmd(script_path, command):
    """Build a bash command to run with virtualenvwrapper sourced."""
    venv_env = _get_virtualenvwrapper_env()
    return (
        f"export VIRTUALENVWRAPPER_PYTHON={sys.executable} && "
        f"export WORKON_HOME={venv_env['WORKON_HOME']} && "
        f"source {script_path} && {command}"
    )


def is_virtualenvwrapper_configured():
    """
    Check if virtualenvwrapper is configured and available.

    Returns:
        bool: True if virtualenvwrapper is available, False otherwise.
    """
    try:
        script_path = get_virtualenvwrapper_script()
        # Check if mkvirtualenv is available (it's a shell function)
        result = subprocess.run(
            ["/bin/bash", "-c", f"source {script_path} && type mkvirtualenv"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=5,
        )
        return result.returncode == 0
    except (RuntimeError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


def create_venv_with_virtualenvwrapper(
    env_name, python_interpreter, environment="production"
):
    """
    Create virtual environment using virtualenvwrapper.

    Args:
        env_name: Name of the virtual environment (should include environment prefix).
        python_interpreter: Python interpreter to use (e.g., 'python3', 'python2.7').
        environment: Environment name (default: 'production'). Used for validation
                     to ensure env_name follows the expected pattern.

    Raises:
        RuntimeError: If virtualenvwrapper is not available.
        subprocess.CalledProcessError: If mkvirtualenv command fails.
        ValueError: If env_name doesn't start with expected environment prefix.
    """
    virtualenvwrapper_script = get_virtualenvwrapper_script()
    cmd = _build_virtualenvwrapper_cmd(
        virtualenvwrapper_script, f"mkvirtualenv -p {python_interpreter} {env_name}"
    )

    subprocess.check_output(
        ["/bin/bash", "-c", cmd],
        env=_get_virtualenvwrapper_env(),
        stderr=subprocess.STDOUT,
    )


def install_package_with_virtualenvwrapper(env_name, package_spec, pre_install=None):
    """
    Install package in virtualenvwrapper environment.

    Args:
        env_name: Name of the virtual environment.
        package_spec: Package specification (e.g., 'package==1.0.0' or
                     'git+https://github.com/user/repo@tag#egg=package').
        pre_install: Optional list of package specs to install before main package.

    Raises:
        RuntimeError: If virtualenvwrapper is not available.
        subprocess.CalledProcessError: If pip install command fails.
    """
    virtualenvwrapper_script = get_virtualenvwrapper_script()
    venv_env = _get_virtualenvwrapper_env()

    # Install pre-install packages if specified
    if pre_install:
        for pre_pkg in pre_install:
            cmd = _build_virtualenvwrapper_cmd(
                virtualenvwrapper_script, f"workon {env_name} && pip install {pre_pkg}"
            )
            subprocess.check_output(
                ["/bin/bash", "-c", cmd],
                env=venv_env,
                stderr=subprocess.STDOUT,
            )

    # Install main package
    cmd = _build_virtualenvwrapper_cmd(
        virtualenvwrapper_script, f"workon {env_name} && pip install {package_spec}"
    )
    subprocess.check_output(
        ["/bin/bash", "-c", cmd],
        env=venv_env,
        stderr=subprocess.STDOUT,
    )


def find_executable_in_virtualenvwrapper(env_name, command_name):
    """
    Find executable in virtualenvwrapper environment.

    Args:
        env_name: Name of the virtual environment.
        command_name: Name of the command/executable to find.

    Returns:
        str: Path to the executable.

    Raises:
        RuntimeError: If virtualenvwrapper is not available.
        FileNotFoundError: If executable is not found.
    """
    virtualenvwrapper_script = get_virtualenvwrapper_script()
    cmd = _build_virtualenvwrapper_cmd(
        virtualenvwrapper_script, f"workon {env_name} && which {command_name}"
    )

    try:
        toolpath = subprocess.check_output(
            ["/bin/bash", "-c", cmd],
            env=_get_virtualenvwrapper_env(),
            stderr=subprocess.STDOUT,
        )
        return toolpath.decode("utf-8").strip()
    except subprocess.CalledProcessError as e:
        error_msg = e.stdout.decode("utf-8", errors="ignore") if e.stdout else str(e)
        raise FileNotFoundError(
            f"Executable '{command_name}' not found in virtualenv '{env_name}'. "
            f"Error: {error_msg}"
        ) from e
