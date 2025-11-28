# Refactoring Plan: Replace virtualenvwrapper with uv

## What register_apps Does

`register_apps` is a **production deployment tool** that creates versioned, isolated executables for Python packages and containerized applications. It's designed for managing multiple versions of tools in a production environment.

### Core Functionality

1. **Versioned Package Management**: Creates separate virtual environments for each package version
2. **Executable Registration**: Creates wrapper scripts and symlinks in a centralized bin directory
3. **Container Integration**: Supports Docker and Singularity containers
4. **Isolated Environments**: Each version gets its own virtual environment to avoid conflicts

### Current Architecture

#### Directory Structure Created:
```
/opt/
└── package_name/
    └── v1.2.3/
        └── package_name (executable script)

/bin/
└── package_name_v1.2.3 -> /opt/package_name/v1.2.3/package_name
```

#### Virtual Environment Location:
Currently uses `virtualenvwrapper` which stores venvs in `~/.virtualenvs/`:
```
~/.virtualenvs/
└── production__package_name__v1.2.3/
    └── bin/
        └── package_name (actual executable)
```

#### Current Workflow (using virtualenvwrapper):

1. **Create venv**: `mkvirtualenv -p python3 production__package_name__v1.2.3`
2. **Activate venv**: `workon production__package_name__v1.2.3`
3. **Install package**: `pip install package_name==v1.2.3`
4. **Find executable**: `which package_name` → returns path to venv/bin/package_name
5. **Create wrapper**: Write script that calls the executable from venv
6. **Create symlink**: Link from /bin/package_name_v1.2.3 to wrapper script

### Why Replace virtualenvwrapper with uv?

**Benefits:**
- ✅ **Faster**: uv is 10-100x faster than pip/virtualenv
- ✅ **Modern**: Better dependency resolution, written in Rust
- ✅ **Simpler**: No shell functions, just commands
- ✅ **Better CI/CD**: Easier to set up in CI (no shell sourcing needed)
- ✅ **Cross-platform**: Works consistently across platforms
- ✅ **No dependencies**: uv is self-contained, no virtualenvwrapper needed

**Challenges:**
- ⚠️ **Breaking change**: Changes how venvs are managed
- ⚠️ **Migration**: Existing installations using virtualenvwrapper would need migration
- ⚠️ **Location change**: venvs would be in different location (could be optdir instead of ~/.virtualenvs)

## Refactoring Plan

### Phase 1: Analysis & Design

#### 1.1 Current virtualenvwrapper Usage

**Functions using virtualenvwrapper:**
- `register_toil()` - lines 83-117
- `register_python()` - lines 337-371

**What virtualenvwrapper provides:**
- `mkvirtualenv` - creates venv with a name
- `workon` - activates venv (shell function)
- `which <command>` - finds executable in activated venv
- Centralized venv storage in `~/.virtualenvs/`

#### 1.2 uv Equivalents

| virtualenvwrapper | uv equivalent |
|-------------------|----------------|
| `mkvirtualenv -p python3 env_name` | `uv venv --python python3 <path>` |
| `workon env_name && pip install pkg` | `uv pip install --python <venv_path> pkg` |
| `which command` (in activated venv) | `uv pip list --python <venv_path>` or direct path lookup |
| `~/.virtualenvs/env_name` | Can use `<optdir>/package/version/.venv` or custom location |

### Phase 2: Implementation Strategy

#### Option A: Store venvs in optdir (Recommended)
**Pros:**
- Self-contained: each package version has its own venv
- Easier cleanup: delete package version = delete venv
- No global state: no need for centralized venv directory

**Structure:**
```
/opt/package_name/v1.2.3/
├── .venv/              # Virtual environment
│   └── bin/
│       └── package_name
└── package_name        # Wrapper script
```

#### Option B: Keep centralized venv directory
**Pros:**
- Similar to current behavior
- Can share venvs if needed (though not recommended)

**Structure:**
```
~/.uv_venvs/production__package_name__v1.2.3/
└── bin/
    └── package_name

/opt/package_name/v1.2.3/
└── package_name        # Wrapper script pointing to venv
```

**Recommendation: Option A** - More modern, self-contained, easier to manage

### Phase 3: Code Changes

#### 3.1 Remove virtualenvwrapper dependency

**Files to modify:**
1. `register_apps/cli.py` - Replace virtualenvwrapper calls with uv
2. `register_apps/options.py` - Remove `VIRTUALENVWRAPPER` option
3. `setup.json` - Remove `virtualenvwrapper` from `install_requires`
4. `tests/test_cli.py` - Update tests to check for uv instead
5. `.github/workflows/tests.yml` - Remove virtualenvwrapper setup

#### 3.2 New Implementation Pattern

**Current (virtualenvwrapper):**
```python
# Create venv
subprocess.check_output([
    "/bin/bash", "-c",
    f"source {virtualenvwrapper} && mkvirtualenv -p {python} {env}"
])

# Install package
subprocess.check_output([
    "/bin/bash", "-c",
    f"source {virtualenvwrapper} && workon {env} && pip install {pkg}"
])

# Find executable
toolpath = subprocess.check_output([
    "/bin/bash", "-c",
    f"source {virtualenvwrapper} && workon {env} && which {command}"
])
```

**New (uv):**
```python
# Create venv
venv_path = optdir / ".venv"
subprocess.check_output([
    "uv", "venv", "--python", python, str(venv_path)
])

# Install package
subprocess.check_output([
    "uv", "pip", "install",
    "--python", str(venv_path / "bin" / "python"),
    f"{pkg}=={version}"
])

# Find executable (direct path)
toolpath = venv_path / "bin" / command
if not toolpath.exists():
    # Try to find it
    result = subprocess.check_output([
        "uv", "pip", "list", "--python", str(venv_path / "bin" / "python")
    ])
```

#### 3.3 Detailed Code Changes

**Function: `register_toil()` and `register_python()`**

**Before:**
```python
env = f"{environment}__{pypi_name}__{pypi_version}"
venv_env = os.environ.copy()
venv_env.setdefault("WORKON_HOME", os.path.expanduser("~/.virtualenvs"))
venv_env["VIRTUALENVWRAPPER_PYTHON"] = sys.executable

subprocess.check_output([
    "/bin/bash", "-c",
    f"export VIRTUALENVWRAPPER_PYTHON={sys.executable} && "
    f"export WORKON_HOME={venv_env['WORKON_HOME']} && "
    f"source {virtualenvwrapper} && mkvirtualenv -p {python} {env}"
], env=venv_env)
```

**After:**
```python
# Store venv in optdir for self-contained package
venv_path = optdir / ".venv"

# Create virtual environment
subprocess.check_output([
    "uv", "venv",
    "--python", python,
    str(venv_path)
])

# Install package
python_exe = venv_path / "bin" / "python"
if github_user:
    subprocess.check_output([
        "uv", "pip", "install",
        "--python", str(python_exe),
        f"git+https://github.com/{github_user}/{pypi_name}@{pypi_version}#egg={pypi_name}"
    ])
else:
    subprocess.check_output([
        "uv", "pip", "install",
        "--python", str(python_exe),
        f"{pypi_name}=={pypi_version}"
    ])

# Find executable (direct path)
toolpath = venv_path / "bin" / (command or pypi_name)
if not toolpath.exists():
    # Fallback: search in bin directory
    bin_dir = venv_path / "bin"
    matching = list(bin_dir.glob(f"{command or pypi_name}*"))
    if matching:
        toolpath = matching[0]
    else:
        raise FileNotFoundError(f"Executable {command or pypi_name} not found in {venv_path}")
```

### Phase 4: Migration Considerations

#### 4.1 Backward Compatibility

**Option 1: Clean break (Recommended)**
- Remove virtualenvwrapper support entirely
- Update documentation
- Users need to re-register packages

**Option 2: Dual support**
- Add `--use-uv` flag
- Keep virtualenvwrapper as default initially
- Deprecate virtualenvwrapper in next major version

**Recommendation: Option 1** - Cleaner, simpler codebase

#### 4.2 Migration Path for Users

1. **Document the change** in CHANGELOG
2. **Provide migration script** (optional):
   ```bash
   # Script to migrate existing registrations
   for venv in ~/.virtualenvs/production__*; do
       # Extract package info and re-register with uv
   done
   ```

#### 4.3 Testing Strategy

1. **Unit tests**: Test venv creation and package installation with uv
2. **Integration tests**: Test full registration workflow
3. **Migration tests**: Test that existing functionality works with uv

### Phase 5: Implementation Steps

#### Step 1: Add uv as dependency
- Add `uv` to `install_requires` (or make it optional with clear error)
- Update setup.json

#### Step 2: Create helper function
```python
def create_venv_with_uv(venv_path, python_interpreter):
    """Create virtual environment using uv."""
    subprocess.check_output([
        "uv", "venv",
        "--python", python_interpreter,
        str(venv_path)
    ])

def install_package_with_uv(venv_path, package_spec):
    """Install package in venv using uv."""
    python_exe = venv_path / "bin" / "python"
    subprocess.check_output([
        "uv", "pip", "install",
        "--python", str(python_exe),
        package_spec
    ])

def find_executable_in_venv(venv_path, command_name):
    """Find executable in venv."""
    exe_path = venv_path / "bin" / command_name
    if exe_path.exists():
        return str(exe_path)
    # Try variations
    bin_dir = venv_path / "bin"
    for pattern in [command_name, f"{command_name}*"]:
        matches = list(bin_dir.glob(pattern))
        if matches:
            return str(matches[0])
    raise FileNotFoundError(f"Executable {command_name} not found")
```

#### Step 3: Refactor register_toil()
- Replace virtualenvwrapper calls with uv helpers
- Update venv path to be in optdir
- Test thoroughly

#### Step 4: Refactor register_python()
- Same changes as register_toil
- Test thoroughly

#### Step 5: Update tests
- Remove virtualenvwrapper checks
- Add uv availability checks
- Update test expectations

#### Step 6: Update documentation
- README.md
- Remove virtualenvwrapper references
- Add uv requirements

#### Step 7: Update CI/CD
- Remove virtualenvwrapper setup
- Ensure uv is available (it should be via setup-uv action)

### Phase 6: Risk Assessment

**Low Risk:**
- ✅ uv is stable and well-tested
- ✅ Functionality is equivalent
- ✅ Can test thoroughly before release

**Medium Risk:**
- ⚠️ Breaking change for existing users
- ⚠️ Need to ensure uv is available on target systems

**Mitigation:**
- Clear migration guide
- Version bump (major version)
- Check for uv availability with helpful error messages

### Phase 7: Rollout Plan

1. **Development**: Implement changes in feature branch
2. **Testing**: Comprehensive test suite
3. **Documentation**: Update all docs
4. **Release**: Major version bump (e.g., 3.0.0)
5. **Migration guide**: Help users migrate existing installations

## Summary

**Current State:**
- Uses virtualenvwrapper (shell-based, requires sourcing)
- Venvs stored in `~/.virtualenvs/`
- Requires shell functions (`mkvirtualenv`, `workon`)

**Target State:**
- Uses uv (command-based, no shell sourcing)
- Venvs stored in `<optdir>/package/version/.venv/`
- Direct command execution

**Benefits:**
- Faster execution
- Simpler code
- Better CI/CD integration
- Modern tooling
- Self-contained packages

**Effort Estimate:**
- Code changes: 2-3 hours
- Testing: 2-3 hours
- Documentation: 1 hour
- **Total: 5-7 hours**

---

## Feature 2: YAML Configuration for Batch Installation

### Overview

Add support for installing multiple apps from a YAML configuration file, replacing the need for long bash scripts with repetitive commands.

### Motivation

**Current Problem:**
- Long bash scripts with many repetitive `register_*` commands
- Hard to maintain and update
- No validation before installation
- Difficult to filter or selectively install apps

**Solution:**
- Single YAML configuration file
- `register_apps install --config apps.yaml` command
- Validation, filtering, dry-run support

### YAML Schema

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

  # Toil apps
  - type: toil
    pypi_name: toil_battenberg
    pypi_version: v1.0.7
    image_url: docker://papaemmelab/toil_battenberg:v1.0.7
    github_user: papaemmelab
    python: python2
    container: singularity
    pre_install:  # Optional pre-install steps
      - pip install tensorflow==2.4.1 --no-cache-dir

  # Python apps
  - type: python
    pypi_name: click_annotsv
    pypi_version: v1.0.1
    github_user: papaemmelab
    python: python3
```

### Implementation Plan

#### Phase 1: YAML Parser & Validation
1. Add `pyyaml>=6.0` dependency
2. Create `register_apps/config.py` with:
   - `load_config()` - Load and parse YAML
   - `validate_config()` - Validate schema
   - `merge_defaults()` - Merge app config with defaults

#### Phase 2: New CLI Command
1. Add `register_apps install` command
2. Support options:
   - `--config` - Path to YAML file (required)
   - `--filter` - Filter by type (containers/toil/python/all)
   - `--dry-run` - Preview without installing
   - `--continue-on-error` - Continue if one app fails

#### Phase 3: App Installation Routers
1. `install_container_app()` - Route to `register_image()`
2. `install_toil_app()` - Route to `register_toil()`
3. `install_python_app()` - Route to `register_python()`
4. Support `pre_install` steps for toil/python apps

#### Phase 4: Testing & Documentation
1. Unit tests for YAML parsing and validation
2. Integration tests for full workflow
3. Convert example bash script to YAML
4. Update README with YAML examples

### Files to Modify

1. `setup.json` - Add `pyyaml>=6.0` dependency
2. `register_apps/config.py` - **NEW** - YAML parsing and validation
3. `register_apps/cli.py` - Add `install` command and routing functions
4. `register_apps/cli.py` - Extend `register_toil()` and `register_python()` to support `pre_install`
5. `tests/test_cli.py` - Add tests for YAML installation
6. `README.md` - Add YAML configuration documentation

### Benefits

- ✅ **Maintainability**: Single YAML file vs long bash script
- ✅ **Validation**: Catch errors before installation
- ✅ **Filtering**: Install only specific app types
- ✅ **Dry-run**: Preview changes
- ✅ **Reusability**: Share configs across environments

### Effort Estimate

- YAML parser & validation: 2-3 hours
- CLI command implementation: 3-4 hours
- Pre-install support: 1-2 hours
- Testing: 2-3 hours
- Documentation: 1-2 hours
- **Total: 9-14 hours**

### See Also

See `YAML_CONFIG_FEATURE.md` for detailed design and examples.

