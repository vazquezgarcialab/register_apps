# YAML Configuration Feature: Batch Installation

## Overview

Add support for installing multiple apps from a YAML configuration file, replacing the need for long bash scripts with repetitive commands.

## Use Case

**Current:** Long bash script with many individual `register_*` commands
**Proposed:** Single YAML file + `register_apps install --config apps.yaml`

## YAML Schema Design

### Structure

```yaml
# Global defaults (can be overridden per app)
defaults:
  bindir: /usersoftware/papaemme/isabl/bin
  optdir: /usersoftware/papaemme/isabl/local
  container_runtime: singularity  # or docker
  singularity_path: /usr/bin/singularity
  docker_path: docker
  volumes:  # List of volume mounts
    - /data1:/data1
  tmpvar: $TMP_DIR
  environment: production
  force: true

# App categories (optional, for filtering)
apps:
  containers:
    - name: mosdepth
      type: container
      target: mosdepth
      command: mosdepth
      image_repository: mosdepth
      image_version: 0.2.5
      image_url: quay.io/biocontainers/mosdepth:0.2.5--hb763d49_0
      # Optional overrides
      # bindir: /custom/bin
      # optdir: /custom/opt

    - name: fusioncatcher
      type: container
      target: fusioncatcher_v1.3.0
      command: /opt/fusioncatcher/v1.30/bin/fusioncatcher.py
      image_user: papaemmelab
      image_repository: docker-fusioncatcher
      image_version: v1.3.0

    - name: cellranger
      type: container
      target: cellranger
      command: cellranger
      image_user: papaemmelab
      image_repository: cellranger
      image_version: 3.1.0

    - name: cellranger_v5
      type: container
      target: cellranger
      command: cellranger
      image_user: papaemmelab
      image_repository: cellranger
      image_version: v5.0.1

  toil:
    - name: toil_battenberg
      type: toil
      pypi_name: toil_battenberg
      pypi_version: v1.0.7
      image_url: docker://papaemmelab/toil_battenberg:v1.0.7
      github_user: papaemmelab
      python: python2
      container: singularity
      # Optional: pre_install steps
      # pre_install:
      #   - pip uninstall -y toil_container
      #   - pip install git+https://github.com/papaemmelab/toil_container@v1.1.7#eggs=toil_container

    - name: toil_brass
      type: toil
      pypi_name: toil_brass
      pypi_version: v1.0.2
      image_url: docker://papaemmelab/toil_brass:v1.0.2
      github_user: papaemmelab
      python: python2
      container: singularity

    - name: toil_mutect
      type: toil
      pypi_name: toil_mutect
      pypi_version: v1.2.10
      image_url: docker://papaemmelab/toil_mutect:v1.2.10
      github_user: papaemmelab
      python: python3
      container: singularity

  python:
    - name: click_annotsv
      type: python
      pypi_name: click_annotsv
      pypi_version: v1.0.1
      github_user: papaemmelab
      python: python3

    - name: click_annotvcf
      type: python
      pypi_name: click_annotvcf
      pypi_version: v1.0.9
      github_user: papaemmelab
      python: python3

  # Special cases with pre-install steps
  special:
    - name: toil_caveman
      type: toil
      pypi_name: toil_caveman
      pypi_version: v1.0.6
      image_url: docker://papaemmelab/toil_caveman:v1.0.6
      github_user: papaemmelab
      python: python2
      container: singularity
      pre_install:
        - pip install git+https://github.com/papaemmelab/toil_cvflag@c224aa1#eggs=toil_cvflag

    - name: toil_formalinfixer
      type: toil
      pypi_name: toil_formalinfixer
      pypi_version: v0.0.2
      image_url: docker://papaemmelab/toil_formalinfixer:v0.0.2
      github_user: papaemmelab
      python: python3
      container: singularity
      pre_install:
        - pip install tensorflow==2.4.1 --no-cache-dir
```

### Alternative: Flat Structure (Simpler)

```yaml
defaults:
  bindir: /usersoftware/papaemme/isabl/bin
  optdir: /usersoftware/papaemme/isabl/local
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

  - type: container
    target: fusioncatcher_v1.3.0
    command: /opt/fusioncatcher/v1.30/bin/fusioncatcher.py
    image_user: papaemmelab
    image_repository: docker-fusioncatcher
    image_version: v1.3.0

  # Toil apps
  - type: toil
    pypi_name: toil_battenberg
    pypi_version: v1.0.7
    image_url: docker://papaemmelab/toil_battenberg:v1.0.7
    github_user: papaemmelab
    python: python2
    container: singularity

  # Python apps
  - type: python
    pypi_name: click_annotsv
    pypi_version: v1.0.1
    github_user: papaemmelab
    python: python3
```

**Recommendation: Flat structure** - Simpler, easier to parse, less nesting

## Implementation Plan

### Phase 1: YAML Parser & Schema

#### 1.1 Add Dependencies
- Add `pyyaml>=6.0` to `setup.json` `install_requires`

#### 1.2 Create YAML Schema Validator
- Define schema using `jsonschema` or simple validation
- Validate required fields per app type
- Provide helpful error messages

#### 1.3 Create Configuration Parser
```python
# register_apps/config.py

from pathlib import Path
import yaml
from typing import Dict, List, Any, Optional

def load_config(config_path: Path) -> Dict[str, Any]:
    """Load and validate YAML configuration."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    validate_config(config)
    return config

def validate_config(config: Dict[str, Any]) -> None:
    """Validate configuration schema."""
    # Check required top-level keys
    assert 'defaults' in config, "Missing 'defaults' section"
    assert 'apps' in config, "Missing 'apps' section"
    
    # Validate each app
    for app in config['apps']:
        validate_app(app)

def validate_app(app: Dict[str, Any]) -> None:
    """Validate individual app configuration."""
    app_type = app.get('type')
    assert app_type in ['container', 'toil', 'python'], \
        f"Invalid app type: {app_type}"
    
    if app_type == 'container':
        assert 'image_repository' in app or 'image_url' in app, \
            "Container app requires 'image_repository' or 'image_url'"
        assert 'image_version' in app, "Container app requires 'image_version'"
    elif app_type == 'toil':
        assert 'pypi_name' in app, "Toil app requires 'pypi_name'"
        assert 'pypi_version' in app, "Toil app requires 'pypi_version'"
    elif app_type == 'python':
        assert 'pypi_name' in app, "Python app requires 'pypi_name'"
        assert 'pypi_version' in app, "Python app requires 'pypi_version'"

def merge_defaults(app: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
    """Merge app config with defaults."""
    merged = defaults.copy()
    merged.update(app)
    return merged
```

### Phase 2: New CLI Command

#### 2.1 Add `register_apps install` Command
```python
# register_apps/cli.py

@click.group()
def cli():
    """Register versioned applications in a bin directory."""
    pass

@cli.command()
@click.option(
    '--config',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to YAML configuration file'
)
@click.option(
    '--filter',
    type=click.Choice(['containers', 'toil', 'python', 'all']),
    default='all',
    help='Filter apps by type'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Show what would be installed without actually installing'
)
@click.option(
    '--continue-on-error',
    is_flag=True,
    help='Continue installing other apps if one fails'
)
def install(config, filter, dry_run, continue_on_error):
    """Install apps from YAML configuration file."""
    from register_apps.config import load_config, merge_defaults
    
    click.echo(f"Loading configuration from {config}...")
    cfg = load_config(config)
    
    defaults = cfg.get('defaults', {})
    apps = cfg.get('apps', [])
    
    # Filter apps if requested
    if filter != 'all':
        apps = [app for app in apps if app.get('type') == filter]
    
    click.echo(f"Found {len(apps)} apps to install")
    
    failed = []
    for i, app in enumerate(apps, 1):
        app_name = app.get('name') or app.get('target') or app.get('pypi_name', 'unknown')
        click.echo(f"\n[{i}/{len(apps)}] Installing {app_name}...")
        
        try:
            merged = merge_defaults(app, defaults)
            
            if dry_run:
                click.echo(f"  Would install: {app_name}")
                continue
            
            install_app(merged)
            click.secho(f"  ✓ {app_name} installed successfully", fg='green')
        except Exception as e:
            error_msg = f"  ✗ Failed to install {app_name}: {e}"
            click.secho(error_msg, fg='red')
            if not continue_on_error:
                raise
            failed.append((app_name, str(e)))
    
    if failed:
        click.echo(f"\n{len(failed)} apps failed to install:")
        for name, error in failed:
            click.echo(f"  - {name}: {error}")
        sys.exit(1)

def install_app(app_config: Dict[str, Any]) -> None:
    """Install a single app based on configuration."""
    app_type = app_config['type']
    
    if app_type == 'container':
        install_container_app(app_config)
    elif app_type == 'toil':
        install_toil_app(app_config)
    elif app_type == 'python':
        install_python_app(app_config)
    else:
        raise ValueError(f"Unknown app type: {app_type}")

def install_container_app(app_config: Dict[str, Any]) -> None:
    """Install a container app."""
    # Determine container runtime
    runtime_type = app_config.get('container_runtime', 'singularity')
    runtime_path = app_config.get(
        f'{runtime_type}_path',
        runtime_type  # fallback to 'singularity' or 'docker'
    )
    
    # Build arguments for register_image
    kwargs = {
        'bindir': app_config['bindir'],
        'optdir': app_config['optdir'],
        'target': app_config.get('target'),
        'command': app_config.get('command', ''),
        'image_repository': app_config.get('image_repository'),
        'image_version': app_config.get('image_version'),
        'image_url': app_config.get('image_url'),
        'image_user': app_config.get('image_user'),
        'force': app_config.get('force', False),
        'tmpvar': app_config.get('tmpvar', '$TMP_DIR'),
        'volumes': app_config.get('volumes', []),
        'runtime': runtime_path,
        'image_type': runtime_type,
        'no_home': app_config.get('no_home', False),
    }
    
    # Remove None values
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    
    register_image(**kwargs)

def install_toil_app(app_config: Dict[str, Any]) -> None:
    """Install a toil app."""
    # Handle pre_install steps if any
    if 'pre_install' in app_config:
        # This would need to be handled in register_toil
        # For now, we'll pass it through
        pass
    
    kwargs = {
        'bindir': app_config['bindir'],
        'optdir': app_config['optdir'],
        'pypi_name': app_config['pypi_name'],
        'pypi_version': app_config['pypi_version'],
        'image_url': app_config.get('image_url'),
        'github_user': app_config.get('github_user'),
        'python': app_config.get('python', 'python3'),
        'container': app_config.get('container', 'singularity'),
        'singularity': app_config.get('singularity_path', 'singularity'),
        'docker': app_config.get('docker_path', 'docker'),
        'tmpvar': app_config.get('tmpvar', '$TMP_DIR'),
        'volumes': app_config.get('volumes', []),
        'environment': app_config.get('environment', 'production'),
        'force': app_config.get('force', False),
    }
    
    # Remove None values
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    
    register_toil(**kwargs)

def install_python_app(app_config: Dict[str, Any]) -> None:
    """Install a python app."""
    kwargs = {
        'bindir': app_config['bindir'],
        'optdir': app_config['optdir'],
        'pypi_name': app_config['pypi_name'],
        'pypi_version': app_config['pypi_version'],
        'github_user': app_config.get('github_user'),
        'command': app_config.get('command'),
        'python': app_config.get('python', 'python3'),
        'environment': app_config.get('environment', 'production'),
        'force': app_config.get('force', False),
    }
    
    # Remove None values
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    
    register_python(**kwargs)
```

### Phase 3: Pre-Install Steps Support

#### 3.1 Extend register_toil and register_python
Add support for pre-install commands that run before package installation:

```python
def register_toil(..., pre_install=None):
    """Register versioned toil container pipelines."""
    # ... existing code ...
    
    # Create venv
    venv_path = optdir / ".venv"
    subprocess.check_output([
        "uv", "venv",
        "--python", python,
        str(venv_path)
    ])
    
    # Run pre-install steps if any
    if pre_install:
        python_exe = venv_path / "bin" / "python"
        for cmd in pre_install:
            click.echo(f"Running pre-install: {cmd}")
            subprocess.check_output([
                "uv", "pip", "install",
                "--python", str(python_exe),
                cmd  # e.g., "tensorflow==2.4.1 --no-cache-dir"
            ])
    
    # Install main package
    # ... rest of code ...
```

### Phase 4: Testing

#### 4.1 Unit Tests
- Test YAML parsing
- Test configuration validation
- Test default merging
- Test app type routing

#### 4.2 Integration Tests
- Test full installation workflow
- Test error handling
- Test filtering
- Test dry-run mode

### Phase 5: Documentation

#### 5.1 Update README
- Add YAML configuration section
- Provide example YAML file
- Document all available options

#### 5.2 Create Example YAML
- Convert user's bash script to YAML
- Include comments explaining options
- Show different app types

## Migration from Bash Script

### Example Conversion

**Before (bash):**
```bash
$REGISTER_CONTAINER \
    --force \
    --target mosdepth \
    --command mosdepth \
    --image_repository mosdepth \
    --image_version 0.2.5 \
    --image_url quay.io/biocontainers/mosdepth:0.2.5--hb763d49_0 \
    $COMMON_ARGS $MOUNT_ARGS
```

**After (YAML):**
```yaml
apps:
  - type: container
    target: mosdepth
    command: mosdepth
    image_repository: mosdepth
    image_version: 0.2.5
    image_url: quay.io/biocontainers/mosdepth:0.2.5--hb763d49_0
```

**Usage:**
```bash
register_apps install --config apps.yaml
register_apps install --config apps.yaml --filter containers
register_apps install --config apps.yaml --dry-run
```

## Benefits

1. **Maintainability**: Single YAML file instead of long bash script
2. **Readability**: Clear structure, easy to understand
3. **Reusability**: Share configs across environments
4. **Validation**: Catch errors before installation
5. **Filtering**: Install only specific app types
6. **Dry-run**: Preview changes before applying
7. **Error handling**: Continue on error or fail fast

## Implementation Order

1. ✅ Add YAML parsing and validation
2. ✅ Create `install` command structure
3. ✅ Implement app type routing
4. ✅ Add pre-install support
5. ✅ Add filtering and dry-run
6. ✅ Write tests
7. ✅ Update documentation
8. ✅ Convert example bash script to YAML

## Estimated Effort

- YAML parser & validation: 2-3 hours
- CLI command implementation: 3-4 hours
- Pre-install support: 1-2 hours
- Testing: 2-3 hours
- Documentation: 1-2 hours
- **Total: 9-14 hours**

