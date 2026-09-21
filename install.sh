#!/usr/bin/env bash

set -euo pipefail

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

CRED_FILE="${HERE}/netsquid_credentials.txt"

QOALA_ENV="qoala"
PYTKET_ENV="pytket_dqc"

PY_VERSION="3.10"

NETSQUID_INDEX="pypi.netsquid.org"

QOALA_SIM_REPO="https://github.com/QuTech-Delft/qoala-sim.git@dev"
PYTKET_DQC_REPO="https://github.com/Quantinuum/pytket-dqc.git@main"

DO_QOALA=1
DO_PYTKET=1
FORCE=0
VERIFY_ONLY=0

usage() {
    cat <<'EOF'
============================================================
QNEST — automated installation
============================================================

Builds BOTH environments the notebook needs and registers
both Jupyter kernels:

    qoala        main kernel      steps 0, 5-9
    pytket_dqc   secondary kernel steps 1-4 (%%pytket cells)

USAGE
------------------------------------------------------------

    1. Fill in netsquid_credentials.txt
    2. ./install.sh

OPTIONS
------------------------------------------------------------

    --qoala-only        build only the qoala env
    --pytket-only       build only the pytket_dqc env
    --python 3.10       Python version (default 3.10)
    --force             delete and rebuild existing envs
    --verify            skip install, only run the checks
    -h | --help

NOTE
------------------------------------------------------------

NetSquid supports Linux and macOS only. On Windows use WSL.

============================================================
EOF
}

if [ -t 1 ]; then
    C_BOLD="$(printf '\033[1m')"
    C_RED="$(printf '\033[31m')"
    C_GREEN="$(printf '\033[32m')"
    C_YELLOW="$(printf '\033[33m')"
    C_OFF="$(printf '\033[0m')"
else
    C_BOLD=""; C_RED=""; C_GREEN=""; C_YELLOW=""; C_OFF=""
fi

banner() {
    echo
    echo "============================================================"
    echo " $1"
    echo "============================================================"
}

info()  { echo "  $1"; }
ok()    { echo "  ${C_GREEN}OK${C_OFF}    $1"; }
warn()  { echo "  ${C_YELLOW}WARN${C_OFF}  $1"; }
fail()  { echo "  ${C_RED}FAIL${C_OFF}  $1"; }

die() {
    echo
    fail "$1"
    echo
    exit 1
}

while [ $# -gt 0 ]; do
    case "$1" in
        --qoala-only)   DO_PYTKET=0 ;;
        --pytket-only)  DO_QOALA=0 ;;
        --force)        FORCE=1 ;;
        --verify)       VERIFY_ONLY=1 ;;
        --python)       PY_VERSION="${2:-}"; shift ;;
        -h|--help)
            usage
            exit 0
            ;;
        *) die "Unknown option: $1  (try --help)" ;;
    esac
    shift
done

banner "PLATFORM"

OS="$(uname -s)"

case "$OS" in
    Linux)   ok "Linux detected" ;;
    Darwin)  ok "macOS detected" ;;
    *)
        fail "Unsupported platform: $OS"
        info "NetSquid supports Linux and macOS only."
        info "On Windows, run this inside WSL."
        exit 1
        ;;
esac

banner "CONDA"

if ! command -v conda >/dev/null 2>&1; then
    fail "conda not found on PATH"
    info "Install miniforge:  https://github.com/conda-forge/miniforge"
    exit 1
fi

ok "conda: $(command -v conda)"

CONDA_BASE="$(conda info --base)"

source "${CONDA_BASE}/etc/profile.d/conda.sh"

env_exists() {
    conda env list | awk '{print $1}' | grep -qx "$1"
}

read_credentials() {

    if [ -n "${NETSQUIDPYPI_USER:-}" ] && [ -n "${NETSQUIDPYPI_PWD:-}" ]; then
        ok "using NETSQUIDPYPI_USER / NETSQUIDPYPI_PWD from the environment"
        return 0
    fi

    if [ ! -f "$CRED_FILE" ]; then
        fail "missing $CRED_FILE"
        info "Create it, or export NETSQUIDPYPI_USER and NETSQUIDPYPI_PWD."
        exit 1
    fi

    NETSQUIDPYPI_USER="$(
        grep -E '^[[:space:]]*NETSQUIDPYPI_USER[[:space:]]*=' "$CRED_FILE" \
        | tail -n 1 | cut -d '=' -f 2- | sed 's/^[[:space:]]*//; s/[[:space:]]*$//'
    )"

    NETSQUIDPYPI_PWD="$(
        grep -E '^[[:space:]]*NETSQUIDPYPI_PWD[[:space:]]*=' "$CRED_FILE" \
        | tail -n 1 | cut -d '=' -f 2- | sed 's/^[[:space:]]*//; s/[[:space:]]*$//'
    )"

    if [ -z "$NETSQUIDPYPI_USER" ] || [ -z "$NETSQUIDPYPI_PWD" ]; then
        fail "NETSQUIDPYPI_USER / NETSQUIDPYPI_PWD are empty in:"
        info "$CRED_FILE"
        echo
        info "Register a free account at:"
        info "  https://forum.netsquid.org/ucp.php?mode=register"
        info "then paste the same username and password into that file."
        exit 1
    fi

    export NETSQUIDPYPI_USER NETSQUIDPYPI_PWD

    ok "credentials loaded for user: ${NETSQUIDPYPI_USER}"
}

build_netsquid_index_url() {

    NETSQUID_USER_ENC="$(
        python3 -c 'import sys;from urllib.parse import quote;print(quote(sys.argv[1],safe=""))' \
            "$NETSQUIDPYPI_USER"
    )"

    NETSQUID_PWD_ENC="$(
        python3 -c 'import sys;from urllib.parse import quote;print(quote(sys.argv[1],safe=""))' \
            "$NETSQUIDPYPI_PWD"
    )"

    NETSQUID_URL="https://${NETSQUID_USER_ENC}:${NETSQUID_PWD_ENC}@${NETSQUID_INDEX}"
}

redact() {
    sed -e "s|${NETSQUID_PWD_ENC}|********|g" \
        -e "s|${NETSQUIDPYPI_PWD}|********|g" \
        -e "s|${NETSQUID_USER_ENC}|<user>|g" \
        -e "s|${NETSQUIDPYPI_USER}|<user>|g"
}

create_env() {
    local name="$1"

    if env_exists "$name"; then
        if [ "$FORCE" -eq 1 ]; then
            warn "removing existing env: $name"
            conda env remove -n "$name" -y >/dev/null
        else
            ok "env already exists: $name  (use --force to rebuild)"
            return 0
        fi
    fi

    info "creating env $name (python ${PY_VERSION}) ..."
    conda create -n "$name" "python=${PY_VERSION}" -y >/dev/null
    ok "created: $name"
}

register_kernel() {
    local env="$1"
    local kernel_name="$2"
    local display="$3"

    conda run -n "$env" python -m ipykernel install \
        --user \
        --name "$kernel_name" \
        --display-name "$display" >/dev/null

    ok "kernel registered: $kernel_name  (\"$display\")"
}

install_qoala_env() {

    banner "ENVIRONMENT 1/2:  ${QOALA_ENV}"

    read_credentials
    build_netsquid_index_url

    create_env "$QOALA_ENV"

    info "installing Tk runtime for the QNEST desktop GUI ..."
    conda install -n "$QOALA_ENV" -c conda-forge tk -y >/dev/null 2>&1 \
        || warn "tk install skipped; verify tkinter is available before launching the GUI"

    info "upgrading pip ..."
    conda run -n "$QOALA_ENV" python -m pip install --upgrade pip wheel setuptools >/dev/null

    info "installing base requirements ..."
    conda run -n "$QOALA_ENV" python -m pip install \
        -r "${HERE}/requirements/qoala.txt"

    info "installing Chromium for exact pytket circuit previews ..."
    if ! conda run -n "$QOALA_ENV" python -m playwright install chromium >/dev/null 2>&1; then
        warn "Playwright Chromium install failed; QNEST will use a system Chrome/Chromium if available, otherwise the native QASM preview fallback."
    else
        ok "Chromium renderer installed"
    fi

    info "installing netsquid from the private index ..."

    if ! conda run -n "$QOALA_ENV" python -m pip install \
            --extra-index-url "$NETSQUID_URL" \
            netsquid 2>&1 | redact; then

        fail "netsquid installation failed"
        echo
        info "Most common causes:"
        info "  - wrong username or password in netsquid_credentials.txt"
        info "  - account not yet activated on the NetSquid forum"
        info "  - no wheel for python ${PY_VERSION} on this platform"
        echo
        info "Check your login works at: https://forum.netsquid.org"
        exit 1
    fi

    ok "netsquid installed"

    info "installing qoala-sim from GitHub ..."

    conda run -n "$QOALA_ENV" python -m pip install \
        --extra-index-url "$NETSQUID_URL" \
        "git+${QOALA_SIM_REPO}" 2>&1 | redact

    ok "qoala-sim installed"

    register_kernel "$QOALA_ENV" "$QOALA_ENV" "Python (qoala)"
}

install_pytket_env() {

    banner "ENVIRONMENT 2/2:  ${PYTKET_ENV}"

    create_env "$PYTKET_ENV"

    info "upgrading pip ..."
    conda run -n "$PYTKET_ENV" python -m pip install --upgrade pip wheel setuptools >/dev/null

    if [ "$OS" = "Darwin" ]; then
        info "installing build toolchain for kahypar (cmake, boost) ..."
        conda install -n "$PYTKET_ENV" -c conda-forge cmake boost-cpp -y >/dev/null 2>&1 \
            || warn "toolchain install skipped; kahypar may fail to build"
    fi

    info "installing base requirements ..."

    if ! conda run -n "$PYTKET_ENV" python -m pip install \
            -r "${HERE}/requirements/pytket_dqc.txt"; then

        fail "requirements install failed"
        echo
        info "If the failing package is kahypar, it has no prebuilt wheel"
        info "for this platform and compiles from source. Install a"
        info "compiler toolchain and retry:"
        info "  conda install -n ${PYTKET_ENV} -c conda-forge cmake boost-cpp"
        exit 1
    fi

    info "installing pytket-dqc from GitHub ..."

    conda run -n "$PYTKET_ENV" python -m pip install "git+${PYTKET_DQC_REPO}"

    ok "pytket-dqc installed"

    register_kernel "$PYTKET_ENV" "$PYTKET_ENV" "Python (pytket_dqc)"
}

verify() {

    banner "VERIFICATION"

    local failures=0

    if [ "$DO_QOALA" -eq 1 ]; then

        info "checking ${QOALA_ENV} ..."

        if conda run -n "$QOALA_ENV" python - <<'PYEOF'
import sys
mods = [
    ("netsquid",                    "netsquid"),
    ("qoala.lang.parse",            "qoala-sim"),
    ("qoala.runtime.config",        "qoala-sim"),
    ("qoala.util.runner",           "qoala-sim"),
    ("numpy",                       "numpy"),
    ("pandas",                      "pandas"),
    ("jupyter_client.manager",      "jupyter_client"),
    ("tkinter",                     "tk"),
    ("matplotlib",                  "matplotlib"),
    ("PIL",                         "pillow"),
]
bad = []
for mod, pkg in mods:
    try:
        __import__(mod)
    except Exception as e:
        bad.append(f"    {mod:26s} <- {pkg}: {type(e).__name__}: {e}")
if bad:
    print("  missing in qoala env:")
    print("\n".join(bad))
    sys.exit(1)
print("  all qoala imports resolved")
PYEOF
        then
            ok "${QOALA_ENV} environment"
        else
            fail "${QOALA_ENV} environment"
            failures=$((failures + 1))
        fi
    fi

    if [ "$DO_PYTKET" -eq 1 ]; then

        info "checking ${PYTKET_ENV} ..."

        if conda run -n "$PYTKET_ENV" python - <<'PYEOF'
import sys
mods = [
    ("pytket",                          "pytket"),
    ("pytket.qasm",                     "pytket"),
    ("pytket_dqc.utils",                "pytket-dqc"),
    ("pytket_dqc.networks",             "pytket-dqc"),
    ("pytket_dqc.distributors",         "pytket-dqc"),
    ("hypernetx",                       "hypernetx"),
    ("kahypar",                         "kahypar"),
    ("mqt.bench",                       "mqt.bench"),
    ("qiskit",                          "qiskit"),
]
bad = []
for mod, pkg in mods:
    try:
        __import__(mod)
    except Exception as e:
        bad.append(f"    {mod:30s} <- {pkg}: {type(e).__name__}: {e}")
if bad:
    print("  missing in pytket_dqc env:")
    print("\n".join(bad))
    sys.exit(1)
print("  all pytket_dqc imports resolved")
PYEOF
        then
            ok "${PYTKET_ENV} environment"
        else
            fail "${PYTKET_ENV} environment"
            failures=$((failures + 1))
        fi
    fi

    info "checking registered Jupyter kernels ..."

    if conda run -n "$QOALA_ENV" jupyter kernelspec list 2>/dev/null \
        | grep -q "$PYTKET_ENV"; then
        ok "kernel \"${PYTKET_ENV}\" is visible to the ${QOALA_ENV} env"
    else
        fail "kernel \"${PYTKET_ENV}\" NOT visible to the ${QOALA_ENV} env"
        info "The %%pytket magic cannot start without it."
        failures=$((failures + 1))
    fi

    info "checking portable QNEST project configuration ..."
    if conda run -n "$QOALA_ENV" python - "$HERE" <<'PYEOF'
import sys, pathlib
here = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(here))
from src.config import PROJECT_ROOT, SWITCHSIM, COMPILER
assert PROJECT_ROOT == here, (PROJECT_ROOT, here)
print(f"  PROJECT_ROOT: {PROJECT_ROOT}")
print(f"  QNEST_SWITCHSIM override: {SWITCHSIM}")
print(f"  optional Compiler path: {COMPILER}")
PYEOF
    then
        ok "portable project paths"
    else
        fail "project path configuration"
        failures=$((failures + 1))
    fi

    echo

    if [ "$failures" -eq 0 ]; then
        banner "INSTALLATION COMPLETE"
        echo "  Launch the QNEST desktop application:"
        echo
        echo "      conda activate ${QOALA_ENV}"
        echo "      python app_gui.py"
        echo
        echo "  Notebook workflows remain supported; the GUI uses the same"
        echo "  ${PYTKET_ENV} secondary kernel automatically."
        echo
    else
        banner "INSTALLATION INCOMPLETE"
        echo "  ${failures} check(s) failed. See the messages above."
        echo
        exit 1
    fi
}

banner "QNEST INSTALLER"
info "project root : ${HERE}"
info "python       : ${PY_VERSION}"
info "environments : $( [ $DO_QOALA -eq 1 ] && printf '%s ' "$QOALA_ENV" )$( [ $DO_PYTKET -eq 1 ] && printf '%s' "$PYTKET_ENV" )"

if [ "$VERIFY_ONLY" -eq 0 ]; then
    [ "$DO_QOALA"  -eq 1 ] && install_qoala_env
    [ "$DO_PYTKET" -eq 1 ] && install_pytket_env
fi

verify
