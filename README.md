# Register Apps

[![pypi badge][pypi_badge]][pypi_base]
[![Tests](https://github.com/papaemmelab/register_apps/actions/workflows/tests.yml/badge.svg)](https://github.com/papaemmelab/register_apps/actions/workflows/tests.yml)
[![codecov badge][codecov_badge]][codecov_base]
[![docker badge][docker_badge]][docker_base]
[![docker badge][automated_badge]][docker_base]
[![code formatting][black_badge]][black_base]

👾 Register versioned [toil container] pipelines, [singularity] containers, and python packages.

## Installation

This package is available at [PyPi][pypi_base]:

```bash
pip install register_apps
# or with the latest version
pip install git+https://github.com/papaemmelab/register_apps.git#egg=register_apps
```

## Development Setup

### Setting up the development environment

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

### Running Tests

With the virtual environment activated:

```bash
# Run tests with coverage
pytest --cov=register_apps --cov-report=term-missing
# Run linting
pylint register_apps
pydocstyle register_apps
```

Note: Some tests require Docker or Singularity to be installed and running. These tests will be skipped if the required tools are not available.

## Usage

This package is used to register versionized and containerized applications within a production environment. It provides 4 commands:

* 🍡 `register_toil` - Register Toil containerized pipelines
* 📦 `register_singularity` - Register Singularity container commands
* 🐍 `register_python` - Register Python packages
* 📋 `register_apps` - Install multiple apps from YAML configuration

⚠️ **WARNING:** This package only works with singularity 2.4+

⚠️ **NOTE:** This package requires `virtualenvwrapper` to be installed and configured for managing virtual environments.

### Register a toil containerized application

* 🍡 **`register_toil`** will install [toil container] pipelines in separate virtual environments (using `virtualenvwrapper`), pull a singularity image from the dockerhub and create executables that call the pipeline with the right parameters:

```bash
register_toil \
    --pypi_name toil_disambiguate \
    --pypi_version v0.1.2 \
    --bindir /example/bin \
    --optdir /example/opt \
    --tmpvar $TMP \
    --volumes /ifs /ifs
```

Given this call, the following directory structure is created:

```bash
/example/
├── bin
│   └── toil_disambiguate_v0.1.2 -> /example/opt/toil_disambiguate/v0.1.2/toil_disambiguate
└── opt
    └── toil_disambiguate
        └── v0.1.2
            ├── .venv/              # Virtual environment (NEW)
            │   └── bin/
            │       └── toil_disambiguate
            ├── toil_disambiguate
            └── toil_disambiguate-v0.1.2.simg
```

And the executables look like this:

```bash
cat /example/bin/toil_disambiguate

#!/bin/bash
$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.venv/bin/toil_disambiguate "$@" \
    --singularity /example/opt/toil_disambiguate/v0.1.2/toil_disambiguate-v0.1.2.simg \
    --volumes /ifs /ifs \
    --workDir $TMP_DIR
```

* 📦 **`register_singularity`** provides a similar usage to register regular commands that will run inside a container, it will create the same directory structure but the executables created will execute commands inside the container:

```bash
register_singularity \
    --target svaba \
    --command svaba \
    --image_url docker://papaemmelab/docker-svaba:v1.0.0 \
    --bindir /example/bin \
    --optdir /example/opt \
    --tmpvar $TMP \
    --volumes /ifs /ifs
```

Given this call, the following directory structure is created:

```bash
/example/
├── bin
│   └── svaba -> /example/opt/docker-svaba/v1.0.0/svaba
└── opt
    └── docker_svaba
        └── v1.0.0
            ├── svaba
            └── docker-svaba-v1.0.0
```

And the executables look like this:

```bash
cat /example/bin/svaba

#!/bin/bash
singularity exec \
    --workdir $TMP_DIR/${USER}_docker-svaba_v1.0.0_`uuidgen` \
    --pwd `pwd` \
    --bind /ifs:/ifs \
    /example/opt/docker-svaba/v1.0.0/docker-svaba-v1.0.0.simg svaba "$@"
```

* 🐍 **`register_python`** provides a method to register python packages without registering to run inside a container. It will create a similar versionized directory structure and install the python package and its dependencies within a virtual environment (using `virtualenvwrapper`):

```bash
register_python \
    --pypi_name click_annotvcf \
    --pypi_version v1.0.7
    --bindir /example/bin \
    --optdir /example/opt
```

Given this call, the following directory structure is created:

```bash
/example/
├── bin
│   └── click_annotvcf_v1.0.7 -> /example/opt/click_annotvcf/v1.0.7/click_annotvcf
└── opt
    └── click_annotvcf
        └── v1.0.7
            ├── .venv/              # Virtual environment (NEW)
            │   └── bin/
            │       └── click_annotvcf
            └── click_annotvcf
```

And the executables look like this:

```bash
cat /example/bin/click_annotvcf_v1.0.7

#!/bin/bash
$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.venv/bin/click_annotvcf "$@"
```

### Batch Installation with YAML Configuration

You can install multiple apps from a YAML configuration file instead of running individual commands:

```bash
register_apps install --config apps.yaml
```

**Example YAML configuration:**

```yaml
defaults:
  bindir: /example/bin
  optdir: /example/opt
  container_runtime: singularity
  singularity_path: /usr/bin/singularity
  force: true

apps:
  # Container apps
  - type: container
    target: mosdepth
    command: mosdepth
    image_repository: mosdepth
    image_version: 0.2.5
    image_url: quay.io/biocontainers/mosdepth:0.2.5--hb763d49_0

  # Toil apps
  - type: toil
    pypi_name: toil_battenberg
    pypi_version: v1.0.7
    image_url: docker://papaemmelab/toil_battenberg:v1.0.7
    github_user: papaemmelab
    python: python2
    container: singularity
    pre_install:  # Optional pre-install steps
      - tensorflow==2.4.1 --no-cache-dir

  # Python apps
  - type: python
    pypi_name: click_annotsv
    pypi_version: v1.0.1
    github_user: papaemmelab
    python: python3
```

**Options:**
- `--config` - Path to YAML configuration file (required)
- `--filter` - Filter apps by type: `container`, `toil`, `python`, or `all` (default: `all`)
- `--dry-run` - Preview what would be installed without actually installing
- `--continue-on-error` - Continue installing other apps if one fails

See `example_apps.yaml` for a complete example configuration file.

### Environment Variables

Some default values can be set using environment variables:

| Variable | Default value for | Description | Example |
| --- | --- | --- | --- |
| `REGISTER_APPS_BIN` | `--bindir` | Path to the directory where the executables symlinks will be created | i.e. `/apps/local/bin` |
| `REGISTER_APPS_OPT` | `--optdir` | Path to the directory where the containers and scripts will be installed | i.e. `/apps/opt` |
| `REGISTER_APPS_VOLUMES` | `--volumes` | Comma-separated volumes in the format `{src}:{dst}` or just `{src}` | i.e. `/mnt/data,/scratch,/usr/local/data:/data` will mount in docker as `-v /mnt/data:/mnt/data -v /scratch:/scratch -v /usr/local/data:/data`.|

## Contributing

Contributions are welcome, and they are greatly appreciated, check our [contributing guidelines](.github/CONTRIBUTING.md)!

## Credits

This package was created using [Cookiecutter] and the
[papaemmelab/cookiecutter-toil] project template.

[toil container]: https://github.com/papaemmelab/toil_container
[singularity]: http://singularity.lbl.gov/
[cookiecutter]: https://github.com/audreyr/cookiecutter
[papaemmelab/cookiecutter-toil]: https://github.com/papaemmelab/cookiecutter-toil
[docker_base]: https://hub.docker.com/r/papaemmelab/register_apps
[docker_badge]: https://img.shields.io/docker/cloud/build/papaemmelab/register_apps.svg
[automated_badge]: https://img.shields.io/docker/cloud/automated/papaemmelab/register_apps.svg
[codecov_badge]: https://codecov.io/gh/papaemmelab/register_apps/branch/master/graph/badge.svg
[codecov_base]: https://codecov.io/gh/papaemmelab/register_apps
[pypi_badge]: https://img.shields.io/pypi/v/register_apps.svg
[pypi_base]: https://pypi.org/pypi/register_apps
[black_badge]: https://img.shields.io/badge/code%20style-black-000000.svg
[black_base]: https://github.com/ambv/black
