"""
Module that contains the command line app.

Why does this file exist, and why not put this in __main__?
You might be tempted to import things from __main__ later, but that will
cause problems, the code will get executed twice:

    - When you run `python -m register_apps` python will execute
      `__main__.py` as a script. That means there won't be any
      `register_apps.__main__` in `sys.modules`.

    - When you import __main__ it will get executed again (as a module) because
      there's no `register_apps.__main__` in `sys.modules`.

Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration
"""

from pathlib import Path
import os
import shutil
import subprocess
import sys
from typing import Any, Dict

import click

from register_apps import config
from register_apps import options
from register_apps import utils


@click.command()
@options.PYPI_NAME
@options.PYPI_VERSION
@options.IMAGE_USER
@options.IMAGE_URL
@options.GITHUB_USER
@options.BINDIR
@options.OPTDIR
@options.PYTHON2
@options.TMPVAR
@options.VOLUMES
@options.SINGULARITY
@options.CONTAINER
@options.ENVIRONMENT
@click.option(
    "--pre-install",
    multiple=True,
    help=(
        "Package specifications to install before main package "
        "(can be used multiple times)"
    ),
)
def register_toil(  # pylint: disable=R0917
    pypi_name,
    pypi_version,
    bindir,
    optdir,
    python,
    volumes,
    tmpvar,
    image_url,
    image_user,
    github_user,
    singularity,
    container,
    environment,
    pre_install,
):
    """Register versioned toil container pipelines in a bin directory."""
    python = shutil.which(python)
    optdir = Path(optdir) / pypi_name / pypi_version
    bindir = Path(bindir)
    optexe = optdir / pypi_name
    binexe = bindir / f"{pypi_name}_{pypi_version}"
    workdir = f"{tmpvar}/{pypi_name}_{pypi_version}_`uuidgen`"
    image_url = image_url or f"{image_user}/{pypi_name}:{pypi_version}"
    if container == "singularity" and not image_url.startswith("docker://"):
        image_url = f"docker://{image_url}"
    if container == "docker" and image_url.startswith("docker://"):
        image_url = image_url.replace("docker://", "")

    # check paths
    assert python, "Could not determine the python path."

    # make sure dirs exist
    optdir.mkdir(exist_ok=True, parents=True)
    bindir.mkdir(exist_ok=True, parents=True)

    # create virtual environment using uv
    venv_path = optdir / ".venv"
    click.echo(f"Creating virtual environment at {venv_path}...")
    utils.create_venv_with_uv(venv_path, python)

    # Install package using uv
    if github_user:
        package_spec = (
            f"git+https://github.com/{github_user}/"
            f"{pypi_name}@{pypi_version}#egg={pypi_name}"
        )
    else:
        package_spec = f"{pypi_name}=={pypi_version}"

    click.echo(f"Installing package '{package_spec}'...")
    pre_install_list = list(pre_install) if pre_install else None
    utils.install_package_with_uv(venv_path, package_spec, pre_install=pre_install_list)

    # Verify executable exists in venv
    utils.find_executable_in_venv(venv_path, pypi_name)

    # build command - use relative path to venv
    script_dir = '$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)'
    relative_toolpath = f"{script_dir}/.venv/bin/{pypi_name}"
    command = [
        relative_toolpath,
        '"$@"',
    ]

    if container == "singularity":
        command += [
            "--singularity",
            _get_or_create_image(optdir, singularity, image_url),
        ]
    else:  # container == "docker"
        command += [
            "--docker",
            image_url,
        ]

    command += [
        " ".join(f"--volumes {i} {j}" for i, j in volumes),
        "--workDir",
        workdir,
        "\n",
    ]

    # link executables
    click.echo("Creating and linking executable...")
    optexe.write_text(f"#!/bin/bash\n{' '.join(command)}")
    optexe.chmod(mode=0o755)
    utils.force_symlink(optexe, binexe)
    click.secho(
        f"\nExecutables available at:\n" f"\n\t{str(optexe)}" f"\n\t{str(binexe)}\n",
        fg="green",
    )


def register_image(  # pylint: disable=R0913,R0917
    bindir,
    command,
    force,
    image_repository,
    image_type,
    image_url,
    image_user,
    image_version,
    no_home,
    optdir,
    runtime,
    target,
    tmpvar,
    volumes,
):
    """
    Register a container image (Docker or Singularity) as an executable.

    Creates versioned executables that run commands inside container images.
    The function sets up the directory structure, creates wrapper scripts,
    and links executables in the bin directory.

    Args:
        bindir: Directory where executable symlinks will be created.
        command: Command to execute inside the container.
        force: If True, overwrite existing targets.
        image_repository: Docker hub repository name.
        image_type: Type of container ("docker" or "singularity").
        image_url: Full image URL (optional, will be constructed if not provided).
        image_user: Docker hub user/organization name.
        image_version: Version tag of the image.
        no_home: If True, use --no-home option for Singularity.
        optdir: Directory where images and scripts will be stored.
        runtime: Path to container runtime executable.
        target: Name of the target executable to create.
        tmpvar: Environment variable for work directory.
        volumes: List of (source, destination) volume mappings.

    Raises:
        click.UsageError: If targets already exist and force is False.
    """
    optdir = Path(optdir) / image_repository / image_version
    bindir = Path(bindir)
    optexe = optdir / target
    binexe = bindir / target
    workdir = f"{tmpvar}/${{USER}}_{image_repository}_{image_version}_`uuidgen`"
    image_url = image_url or f"{image_user}/{image_repository}:{image_version}"
    if image_type == "singularity" and not image_url.startswith("docker://"):
        image_url = f"docker://{image_url}"
    if image_type == "docker" and image_url.startswith("docker://"):
        image_url = image_url.replace("docker://", "")

    # do not overwrite targets
    if not force and (
        os.path.isfile(optexe) or os.path.isfile(binexe)
    ):  # pragma: no cover
        raise click.UsageError(f"Targets exist, exiting...\n\t{optexe}\n\t{binexe}")

    # make sure dirs exist
    optdir.mkdir(exist_ok=True, parents=True)
    bindir.mkdir(exist_ok=True, parents=True)

    # build command
    if image_type == "singularity":
        command = [
            runtime,
            "exec",
            "--workdir",
            workdir,
            " ".join(f"--bind {i}:{j}" for i, j in volumes),
            "--no-home" if no_home else "",
            _get_or_create_image(optdir, runtime, image_url),
            command,
            '"$@"\n',
        ]
    else:  # image_type == "docker"
        command = [
            runtime,
            "run",
            "-it",
            "--rm",
            "-u",
            "$(id -u):$(id -g)",
            "--workdir",
            workdir,
            " ".join(f"--volume {i}:{j}" for i, j in volumes),
            "--entrypoint ''" if command else "",
            image_url,
            command,
            '"$@"\n',
        ]

    # link executables
    click.echo("Creating and linking executable...")
    command = " ".join(list(filter(None, command)))
    optexe.write_text(f"#!/bin/bash\n{command}")
    optexe.chmod(mode=0o755)
    utils.force_symlink(optexe, binexe)
    click.secho(
        f"\nExecutables available at:\n" f"\n\t{str(optexe)}" f"\n\t{str(binexe)}\n",
        fg="green",
    )


@click.command()
@options.TARGET
@options.COMMAND
@options.IMAGE_REPOSITORY
@options.IMAGE_USER
@options.IMAGE_VERSION
@options.IMAGE_URL
@options.BINDIR
@options.OPTDIR
@options.TMPVAR
@options.VOLUMES
@options.SINGULARITY
@options.FORCE
@options.VERSION
@options.NO_HOME
def register_singularity(singularity, *args, **kwargs):
    """Register versioned singularity command in a bin directory."""
    register_image(image_type="singularity", runtime=singularity, *args, **kwargs)


@click.command()
@options.TARGET
@options.COMMAND
@options.IMAGE_REPOSITORY
@options.IMAGE_USER
@options.IMAGE_VERSION
@options.IMAGE_URL
@options.BINDIR
@options.OPTDIR
@options.TMPVAR
@options.VOLUMES
@options.DOCKER
@options.FORCE
@options.VERSION
def register_docker(docker, *args, **kwargs):
    """Register versioned docker command in a bin directory."""
    register_image(image_type="docker", runtime=docker, no_home=False, *args, **kwargs)


@click.command()
@options.PYPI_NAME
@options.PYPI_VERSION
@options.GITHUB_USER
@options.COMMAND
@options.BINDIR
@options.OPTDIR
@options.PYTHON3
@options.VERSION
@options.ENVIRONMENT
@click.option(
    "--pre-install",
    multiple=True,
    help=(
        "Package specifications to install before main package "
        "(can be used multiple times)"
    ),
)
def register_python(  # pylint: disable=R0917
    pypi_name,
    pypi_version,
    github_user,
    command,
    bindir,
    optdir,
    python,
    environment,
    pre_install,
):
    """Register versioned python pipelines in a bin directory."""
    python = shutil.which(python)
    optdir = Path(optdir) / pypi_name / pypi_version
    bindir = Path(bindir)
    optexe = optdir / pypi_name
    binexe = bindir / command or f"{pypi_name}_{pypi_version}"

    # check paths
    assert python, "Could not determine the python path."

    # make sure dirs exist
    optdir.mkdir(exist_ok=True, parents=True)
    bindir.mkdir(exist_ok=True, parents=True)

    # create virtual environment using uv
    venv_path = optdir / ".venv"
    click.echo(f"Creating virtual environment at {venv_path}...")
    utils.create_venv_with_uv(venv_path, python)

    # Install package using uv
    if github_user:
        package_spec = (
            f"git+https://github.com/{github_user}/"
            f"{pypi_name}@{pypi_version}#egg={pypi_name}"
        )
    else:
        package_spec = f"{pypi_name}=={pypi_version}"

    click.echo(f"Installing package '{package_spec}'...")
    pre_install_list = list(pre_install) if pre_install else None
    utils.install_package_with_uv(venv_path, package_spec, pre_install=pre_install_list)

    # Verify executable exists in venv
    command_name = command or pypi_name
    utils.find_executable_in_venv(venv_path, command_name)

    # build command - use relative path to venv
    script_dir = '$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)'
    relative_toolpath = f"{script_dir}/.venv/bin/{command_name}"
    cmd = [relative_toolpath, '"$@"', "\n"]

    # link executables
    click.echo("Creating and linking executable...")
    optexe.write_text(f"#!/bin/bash\n{' '.join(cmd)}")
    optexe.chmod(mode=0o755)
    utils.force_symlink(optexe, binexe)
    click.secho(
        f"\nExecutables available at:\n" f"\n\t{str(optexe)}" f"\n\t{str(binexe)}\n",
        fg="green",
    )


def _get_or_create_image(optdir, singularity, image_url):
    """Pull image if it's not locally available and store it."""
    singularity_images = list(optdir.glob("*.sif")) + list(optdir.glob("*.simg"))
    if len(singularity_images) > 1:
        click.echo(f"Found multiple images at {optdir}. Using {singularity_images[0]}.")

    if singularity_images:
        click.echo(f"Image exists at: {singularity_images[0]}")
    else:
        subprocess.check_call(
            ["/bin/bash", "-c", f"umask 22 && {singularity} pull {image_url}"],
            cwd=optdir,
        )
        singularity_images = list(optdir.glob("*.sif")) + list(optdir.glob("*.simg"))
        assert singularity_images, f"Image not found: {optdir}"

    singularity_image = singularity_images[0]
    # fix singularity permissions
    singularity_image.chmod(mode=0o755)
    return str(singularity_image)


@click.command()
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to YAML configuration file",
)
@click.option(
    "--filter",
    type=click.Choice(["container", "toil", "python", "all"]),
    default="all",
    help="Filter apps by type",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be installed without actually installing",
)
@click.option(
    "--continue-on-error",
    is_flag=True,
    help="Continue installing other apps if one fails",
)
def install(config_path, filter, dry_run, continue_on_error):
    """Install apps from YAML configuration file."""
    click.echo(f"Loading configuration from {config_path}...")
    cfg = config.load_config(config_path)

    defaults = cfg.get("defaults", {})
    apps = config.get_apps_by_type(cfg, filter if filter != "all" else None)

    click.echo(f"Found {len(apps)} apps to install")

    if dry_run:
        click.echo("\n[DRY RUN] Would install the following apps:")
        for i, app in enumerate(apps, 1):
            app_name = (
                app.get("name") or app.get("target") or app.get("pypi_name", "unknown")
            )
            click.echo(f"  {i}. {app_name} ({app.get('type')})")
        return

    failed = []
    for i, app in enumerate(apps, 1):
        app_name = (
            app.get("name") or app.get("target") or app.get("pypi_name", "unknown")
        )
        click.echo(f"\n[{i}/{len(apps)}] Installing {app_name}...")

        try:
            merged = config.merge_defaults(app, defaults)
            install_app(merged)
            click.secho(f"  ✓ {app_name} installed successfully", fg="green")
        except Exception as e:  # pylint: disable=broad-except
            error_msg = f"  ✗ Failed to install {app_name}: {e}"
            click.secho(error_msg, fg="red")
            if not continue_on_error:
                raise
            failed.append((app_name, str(e)))

    if failed:
        click.echo(f"\n{len(failed)} apps failed to install:")
        for name, error in failed:
            click.echo(f"  - {name}: {error}")
        sys.exit(1)


def install_app(app_config: Dict[str, Any]) -> None:  # type: ignore
    """
    Install a single app based on configuration.

    Args:
        app_config: App configuration dictionary with defaults merged.

    Raises:
        ValueError: If app type is unknown.
    """
    app_type = app_config["type"]

    if app_type == "container":
        install_container_app(app_config)
    elif app_type == "toil":
        install_toil_app(app_config)
    elif app_type == "python":
        install_python_app(app_config)
    else:
        raise ValueError(f"Unknown app type: {app_type}")


def install_container_app(app_config: Dict[str, Any]) -> None:  # type: ignore
    """Install a container app."""
    # Determine container runtime
    runtime_type = app_config.get("container_runtime", "singularity")
    runtime_path = app_config.get(
        f"{runtime_type}_path", runtime_type  # fallback to 'singularity' or 'docker'
    )

    # Build arguments for register_image
    kwargs = {
        "bindir": app_config["bindir"],
        "optdir": app_config["optdir"],
        "target": app_config.get("target"),
        "command": app_config.get("command", ""),
        "image_repository": app_config.get("image_repository"),
        "image_version": app_config.get("image_version"),
        "image_url": app_config.get("image_url"),
        "image_user": app_config.get("image_user"),
        "force": app_config.get("force", False),
        "tmpvar": app_config.get("tmpvar", "$TMP_DIR"),
        "volumes": app_config.get("volumes", []),
        "runtime": runtime_path,
        "image_type": runtime_type,
        "no_home": app_config.get("no_home", False),
    }

    # Remove None values
    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    register_image(**kwargs)


def install_toil_app(app_config: Dict[str, Any]) -> None:  # type: ignore
    """Install a toil app."""
    kwargs = {
        "bindir": app_config["bindir"],
        "optdir": app_config["optdir"],
        "pypi_name": app_config["pypi_name"],
        "pypi_version": app_config["pypi_version"],
        "image_url": app_config.get("image_url"),
        "github_user": app_config.get("github_user"),
        "python": app_config.get("python", "python3"),
        "container": app_config.get("container", "singularity"),
        "singularity": app_config.get("singularity_path", "singularity"),
        "docker": app_config.get("docker_path", "docker"),
        "tmpvar": app_config.get("tmpvar", "$TMP_DIR"),
        "volumes": app_config.get("volumes", []),
        "environment": app_config.get("environment", "production"),
        "force": app_config.get("force", False),
        "pre_install": app_config.get("pre_install"),
    }

    # Remove None values
    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    register_toil(**kwargs)


def install_python_app(app_config: Dict[str, Any]) -> None:  # type: ignore
    """Install a python app."""
    kwargs = {
        "bindir": app_config["bindir"],
        "optdir": app_config["optdir"],
        "pypi_name": app_config["pypi_name"],
        "pypi_version": app_config["pypi_version"],
        "github_user": app_config.get("github_user"),
        "command": app_config.get("command"),
        "python": app_config.get("python", "python3"),
        "environment": app_config.get("environment", "production"),
        "force": app_config.get("force", False),
        "pre_install": app_config.get("pre_install"),
    }

    # Remove None values
    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    register_python(**kwargs)
