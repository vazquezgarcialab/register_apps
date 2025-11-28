# HPC Shared Environment Analysis: uv vs virtualenvwrapper

## Current Implementation (virtualenvwrapper)

### Directory Structure
```
/home/admin/.virtualenvs/
└── production__package_name__v1.2.3/
    └── bin/
        └── package_name  (actual executable)

/opt/package_name/v1.2.3/
└── package_name  (wrapper script)

/bin/
└── package_name_v1.2.3 -> /opt/package_name/v1.2.3/package_name
```

### Wrapper Script Content (Current)
```bash
#!/bin/bash
/home/admin/.virtualenvs/production__package_name__v1.2.3/bin/package_name "$@"
```

**Issues:**
- ❌ Hardcoded absolute path to admin's home directory
- ❌ Breaks if admin's home directory changes
- ❌ Not portable across systems
- ❌ Requires admin's home to be accessible to all users

### Execution Flow
1. User runs: `package_name_v1.2.3 --help`
2. Symlink resolves to: `/opt/package_name/v1.2.3/package_name`
3. Wrapper script executes: `/home/admin/.virtualenvs/.../bin/package_name`
4. All users execute the admin's venv (works if permissions allow)

---

## Proposed Implementation (uv with .venv in optdir)

### Directory Structure
```
/opt/package_name/v1.2.3/
├── .venv/              # Virtual environment (NEW)
│   ├── bin/
│   │   ├── python
│   │   ├── python3
│   │   └── package_name  (actual executable)
│   ├── lib/
│   └── pyvenv.cfg
└── package_name        # Wrapper script

/bin/
└── package_name_v1.2.3 -> /opt/package_name/v1.2.3/package_name
```

### Wrapper Script Content (Proposed)
```bash
#!/bin/bash
# Get directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Execute from co-located venv
"${SCRIPT_DIR}/.venv/bin/package_name" "$@"
```

**Benefits:**
- ✅ Uses relative path (portable)
- ✅ No dependency on admin's home directory
- ✅ Self-contained: delete `/opt/package_name/v1.2.3/` removes everything
- ✅ Works regardless of admin's username or home location

### Execution Flow
1. User runs: `package_name_v1.2.3 --help`
2. Symlink resolves to: `/opt/package_name/v1.2.3/package_name`
3. Wrapper script:
   - Resolves its own directory: `/opt/package_name/v1.2.3/`
   - Executes: `/opt/package_name/v1.2.3/.venv/bin/package_name`
4. All users execute the shared venv in `/opt/` (works with proper permissions)

---

## Permissions Setup for HPC Shared Environment

### Recommended Permissions
```bash
# Admin creates the structure
/opt/package_name/v1.2.3/          # drwxr-xr-x (755) - admin:admin
/opt/package_name/v1.2.3/.venv/    # drwxr-xr-x (755) - admin:admin
/opt/package_name/v1.2.3/package_name  # -rwxr-xr-x (755) - admin:admin

# All users can read/execute, only admin can write
```

### Setup Commands (Admin)
```bash
# Create directory structure
mkdir -p /opt/package_name/v1.2.3
cd /opt/package_name/v1.2.3

# Create venv with uv (as admin)
uv venv --python python3.9 .venv

# Install package
uv pip install --python .venv/bin/python package_name==1.2.3

# Create wrapper script
cat > package_name << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/.venv/bin/package_name" "$@"
EOF
chmod +x package_name

# Set permissions (readable/executable by all, writable by admin only)
chmod -R 755 /opt/package_name/v1.2.3
chown -R admin:admin /opt/package_name/v1.2.3
```

---

## Comparison: Current vs Proposed

| Aspect | Current (virtualenvwrapper) | Proposed (uv + .venv) |
|--------|----------------------------|----------------------|
| **Venv Location** | `~/.virtualenvs/` (admin's home) | `/opt/package/version/.venv/` |
| **Wrapper Path** | Absolute path to admin's home | Relative path to script directory |
| **Portability** | ❌ Depends on admin's home | ✅ Self-contained |
| **Cleanup** | Manual: delete venv separately | ✅ Delete `/opt/package/version/` removes all |
| **Permissions** | Requires admin's home accessible | ✅ Standard `/opt/` permissions |
| **Dependency** | virtualenvwrapper (shell functions) | uv (single binary) |
| **Speed** | Slow (pip-based) | ✅ 10-100x faster |
| **CI/CD** | Complex (shell sourcing) | ✅ Simple (direct commands) |

---

## Migration Path

### For Existing Installations

**Option 1: Clean Migration (Recommended)**
1. Re-register all packages with new `register_apps` version
2. Old venvs in `~/.virtualenvs/` can be cleaned up
3. New structure in `/opt/` is self-contained

**Option 2: Hybrid Approach (Temporary)**
1. Support both old and new structures
2. Check for `.venv/` first, fall back to `~/.virtualenvs/`
3. Gradually migrate packages

---

## Code Changes Required

### In `register_python()` and `register_toil()`

**Current:**
```python
# Venv in ~/.virtualenvs/
env = f"{environment}__{pypi_name}__{pypi_version}"
subprocess.check_output([
    "/bin/bash", "-c",
    f"source {virtualenvwrapper} && mkvirtualenv -p {python} {env}"
])

# Find executable
toolpath = subprocess.check_output([
    "/bin/bash", "-c",
    f"source {virtualenvwrapper} && workon {env} && which {command}"
])
toolpath = toolpath.decode("utf-8").strip()

# Wrapper script
optexe.write_text(f"#!/bin/bash\n{toolpath} \"$@\"\n")
```

**Proposed:**
```python
# Venv in optdir/.venv/
venv_path = optdir / ".venv"
subprocess.check_output([
    "uv", "venv",
    "--python", python,
    str(venv_path)
])

# Install package
python_exe = venv_path / "bin" / "python"
subprocess.check_output([
    "uv", "pip", "install",
    "--python", str(python_exe),
    f"{pypi_name}=={pypi_version}"
])

# Find executable (direct path)
toolpath = venv_path / "bin" / (command or pypi_name)

# Wrapper script with relative path
wrapper_script = f"""#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
"${{SCRIPT_DIR}}/.venv/bin/{command or pypi_name}" "$@"
"""
optexe.write_text(wrapper_script)
```

---

## Conclusion

**Yes, the proposed structure works perfectly for HPC shared environments!**

In fact, it's **better** than the current approach because:
1. ✅ **No home directory dependency** - works regardless of admin's username
2. ✅ **Self-contained** - each package version is isolated
3. ✅ **Easier management** - delete one directory removes everything
4. ✅ **Better permissions** - standard `/opt/` permissions work well
5. ✅ **More portable** - relative paths work across systems

The wrapper script uses a relative path to find `.venv/` in the same directory, making it completely portable and independent of the admin's home directory location.

