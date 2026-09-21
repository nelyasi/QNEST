<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0f62fe&height=220&section=header&text=QNEST&fontSize=72&fontColor=ffffff&fontAlignY=38&fontAlign=50&desc=End-to-End%20Quantum-Network%20Experiment%20Toolkit&descAlignY=60&descSize=16&descAlign=50&animation=fadeIn" width="100%"/>

<br/>

<img src="https://img.shields.io/badge/version-0.3.12-42be65?style=flat-square&labelColor=161616"/>
<img src="https://img.shields.io/badge/Python-3.10-0f62fe?style=flat-square&labelColor=161616"/>
<img src="https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows%20(WSL)-8a3ffc?style=flat-square&labelColor=161616"/>
<img src="https://img.shields.io/badge/NetSquid-account%20required-da1e28?style=flat-square&labelColor=161616"/>
<img src="https://img.shields.io/badge/Conda-Miniforge-42be65?style=flat-square&labelColor=161616"/>

<br/><br/>

<img src="./qnest-logo-core-50fps.gif" alt="QNEST" width="360"/>

<br/><br/>

> **A unified desktop workspace for distributed quantum computing and quantum-network experiments**
> *Seyed Navid Elyasi · Sima Bahrani — Chalmers University of Technology · University of Bristol*

<br/>

</div>

---

> [!IMPORTANT]
> **NetSquid and Qoala are not part of QNEST and are not included in any QNEST release.**
> They are downloaded **directly from their official sources** during installation. NetSquid is retrieved from its private package index using **the NetSquid account credentials that you provide**. Every user must hold their own NetSquid account and must accept NetSquid's terms of use. See [Section 03](#03--third-party-software-and-licensing) before installing.

---

## `01` &nbsp; Overview

QNEST is a desktop toolkit for building and running end-to-end quantum-network experiments. The complete experiment lives in a single workspace. Circuit preparation, physical-network definition, distributed compilation, Qoala/NetSquid scheduling and protocol analysis are connected stages of one pipeline rather than a collection of separate scripts.

```
 ┌────────────┐   ┌────────────┐   ┌──────────────────┐   ┌────────────┐   ┌─────────────────┐
 │  CIRCUIT   │ → │  NETWORK   │ → │ COMPILE /        │ → │  SCHEDULE  │ → │  RUN / ANALYSE  │
 │            │   │            │   │ DISTRIBUTE       │   │            │   │                 │
 │ QASM · MQT │   │ QPUs · topo│   │ DQCPass ·        │   │ Qoala +    │   │ AFA-QSP ·       │
 │ Bench ·    │   │ links ·    │   │ pytket-DQC ·     │   │ NetSquid · │   │ HAMFA-QSP       │
 │ sweeps     │   │ switches   │   │ EJPP · bridge    │   │ Gantt views│   │ Monte Carlo     │
 └────────────┘   └────────────┘   └──────────────────┘   └────────────┘   └─────────────────┘
        └───────────────────────── pytket_dqc env ──────┘ └──────────── qoala env ──────────┘
```

---

## `02` &nbsp; Key Capabilities

| &nbsp; | Capability | Description |
|:---:|---|---|
| ⚛ | **Circuit workspace** | QASM/Python import, direct QASM editing, MQT Bench generation, and single-circuit or batch/sweep execution |
| ⊞ | **Physical network designer** | Tabular and graphical design of QPUs, topologies, direct links and shared switches (all-photonic or memory-assisted) |
| ⇄ | **Distributed compilation** | Circuit cleaning, DQCPass preparation, pytket-DQC distribution, EJPP representation and scheduler bridge export |
| ⏱ | **Qoala/NetSquid scheduling** | Discrete-event scheduling in an isolated process, with request tables and Timed and Layer Gantt views |
| ∿ | **Protocol analysis** | AFA-QSP and HAMFA-QSP Monte Carlo with per-request result tables and batch scaling plots |
| ◈ | **QNEST Assistant** | A local LLM (Qwen3 8B through Ollama) that plans and configures experiments through validated controls only |

---

## `03` &nbsp; Third-Party Software and Licensing

QNEST is an orchestration and analysis layer. It depends on several independent scientific packages, each of which remains the property of its authors and is governed by its **own licence**. QNEST does **not** bundle, relicense or redistribute any of them.

### NetSquid and Qoala — mandatory reading

| Component | Owner | How QNEST obtains it | What the user must do |
|---|---|---|---|
| **NetSquid** | QuTech / TU Delft | Installed at setup time from the official NetSquid private package index (`pypi.netsquid.org`), authenticated with **the user's own credentials** | Register a personal account at the [NetSquid forum](https://forum.netsquid.org/ucp.php?mode=register), read and accept the NetSquid terms of use, and supply those credentials to the installer |
| **Qoala** (`qoala-sim`) | QuTech | Installed at setup time directly from the official repository [`QuTech-Delft/qoala-sim`](https://github.com/QuTech-Delft/qoala-sim) (`dev` branch) | Comply with the upstream licence of `qoala-sim` (MIT at the time of writing) |

**What this means in practice:**

1. **No NetSquid code is shipped with QNEST.** The installers in `rel/` and the source repository contain no NetSquid binaries, wheels or source.
2. **Access is personal.** NetSquid is installed only after the package server accepts *your* credentials. You may not share your account, and you may not redistribute the NetSquid package that is installed on your machine.
3. **Your use of NetSquid is governed by NetSquid's terms, not by QNEST.** It is your responsibility to confirm that your intended use (for example academic, commercial or institutional) is permitted under those terms.
4. **Credentials are handled locally.** The guided setup keeps the password only in the running setup process, forwards it to the authenticated NetSquid download, redacts it from logs, and discards it when setup finishes. The script installer (`install.sh`) likewise redacts credentials from its output.

> [!CAUTION]
> **Never commit your NetSquid credentials.** If you use `netsquid_credentials.txt`, keep it strictly local. The preferred method is to export `NETSQUIDPYPI_USER` and `NETSQUIDPYPI_PWD` as environment variables, which leaves no credential on disk. To stop Git from tracking local edits to the template, run:
> ```bash
> git update-index --skip-worktree netsquid_credentials.txt
> ```

### Other upstream components

These packages are also fetched from their official sources at installation time and keep their own licences:

| Component | Source | Used in environment |
|---|---|---|
| pytket-DQC | [`Quantinuum/pytket-dqc`](https://github.com/Quantinuum/pytket-dqc) (`main` branch) | `pytket_dqc` |
| pytket, Qiskit, MQT Bench, KaHyPar, HyperNetX | PyPI | `pytket_dqc` |
| NumPy, pandas, Matplotlib, Pillow, Jupyter, Playwright | PyPI | `qoala` |
| Chromium (circuit preview renderer) | Playwright | `qoala` |
| Miniforge | [`conda-forge/miniforge`](https://github.com/conda-forge/miniforge) | Host system |
| Ollama and Qwen3 8B *(optional)* | Official Ollama installer and model registry | Host system |

Users are responsible for reviewing and complying with the licence of every third-party component they install.

---

## `04` &nbsp; System Requirements

| Requirement | Details |
|---|---|
| Operating system | Linux (x86-64, arm64) or macOS (Intel, Apple Silicon). Windows is supported **only through WSL 2** (WSLg is required for the desktop GUI) |
| Package manager | Conda, preferably [Miniforge](https://github.com/conda-forge/miniforge). The guided setup can provide Miniforge automatically |
| Python | 3.10 (the default for both environments) |
| Accounts | A personal, activated **NetSquid** account |
| Network access | PyPI, GitHub, `pypi.netsquid.org`, conda-forge |
| Build tools *(macOS)* | `cmake` and `boost-cpp` from conda-forge, needed if KaHyPar must compile from source. The installer adds them automatically |
| Optional | Ollama for the local assistant (about 5 GB for `qwen3:8b`) |

> NetSquid itself supports only Linux and macOS. This is why Windows users must run QNEST inside WSL.

---

## `05` &nbsp; Installation

QNEST can be installed in two ways. **Option A** is recommended for most users. **Option B** is intended for developers and for users who want full control over the environments.

### Before you begin: create your NetSquid account

1. Register at **https://forum.netsquid.org/ucp.php?mode=register**.
2. Activate the account using the confirmation e-mail.
3. Sign in to the forum once to confirm that the account works.
4. Note your **forum username**. The package server may reject an e-mail address, so use the username.

---

### Option A — Guided installer (recommended)

Ready-made setup programs are provided in [`rel/`](./rel). They create the complete runtime and ask for your NetSquid credentials during setup.

| Platform | File |
|---|---|
| Linux (x86-64 and arm64) | `rel/QNEST-Setup-0.3.12.8-Linux-x86_64-and-arm64.run` |
| macOS (universal) | `rel/QNEST-Setup-0.3.12.8-macOS-universal.app.zip` |
| Windows 10/11 (via WSL 2) | `rel/QNEST-Setup-0.3.12.8-Windows-x86_64.exe` |

**Linux**

```bash
chmod +x QNEST-Setup-0.3.12.8-Linux-x86_64-and-arm64.run
./QNEST-Setup-0.3.12.8-Linux-x86_64-and-arm64.run
```

**macOS:** unzip the archive and open **QNEST Setup.app**. If Gatekeeper blocks it, right-click the app and choose **Open**.

**Windows:** make sure WSL 2 with WSLg is installed (`wsl --install` in an administrator PowerShell, then restart), and run the `.exe`.

The guided setup then:

1. opens a local setup page in your browser;
2. asks for your **NetSquid username and password**;
3. installs Miniforge if needed, then builds the Qoala + NetSquid environment, the pytket-DQC environment, the Chromium preview engine and the Jupyter kernels;
4. optionally installs the local Qwen assistant; and
5. creates a QNEST launcher.

---

### Option B — Installation from source

#### Step 1 — Install Miniforge

Skip this step if `conda --version` already works.

```bash
# Linux / WSL
curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
bash Miniforge3-$(uname)-$(uname -m).sh

# macOS (Homebrew)
brew install --cask miniforge
```

Close and reopen the terminal, then confirm:

```bash
conda --version
```

#### Step 2 — Clone the repository

```bash
git clone https://github.com/nelyasi/QNEST.git
cd QNEST
```

#### Step 3 — Provide your NetSquid credentials

**Recommended: environment variables** (nothing is written to disk)

```bash
export NETSQUIDPYPI_USER="your-forum-username"
export NETSQUIDPYPI_PWD="your-password"
```

**Alternative: local credentials file.** Edit `netsquid_credentials.txt`, and do not commit it:

```ini
NETSQUIDPYPI_USER=your-forum-username
NETSQUIDPYPI_PWD=your-password
```

If both are present, the environment variables take precedence.

#### Step 4 — Run the installer

```bash
chmod +x install.sh launch_qnest.sh setup_qwen.sh
./install.sh
```

The installer builds two isolated Conda environments and registers both as Jupyter kernels:

| Environment | Purpose | Main contents |
|---|---|---|
| `qoala` | Desktop GUI, scheduling, protocol analysis | NetSquid, qoala-sim, Tk, NumPy, pandas, Matplotlib, Pillow, Jupyter, Playwright + Chromium |
| `pytket_dqc` | Circuit generation and distributed compilation | pytket, pytket-DQC, Qiskit, MQT Bench, KaHyPar, HyperNetX, ipykernel |

The two environments are kept separate on purpose, because their dependency stacks conflict. The GUI runs in `qoala` and communicates with `pytket_dqc` through a persistent kernel bridge.

**Installer options**

| Option | Effect |
|---|---|
| `--qoala-only` | Build only the `qoala` environment |
| `--pytket-only` | Build only the `pytket_dqc` environment |
| `--python 3.10` | Choose the Python version (default `3.10`) |
| `--force` | Delete and rebuild existing environments |
| `--verify` | Skip installation and only run the checks |
| `-h`, `--help` | Show usage |

#### Step 5 — Verify

```bash
./install.sh --verify
```

A successful run confirms that all imports resolve in both environments, that the `pytket_dqc` kernel is visible from `qoala`, and that the project paths are portable. It ends with **INSTALLATION COMPLETE**.

#### Step 6 — Optional: the local AI assistant

Install [Ollama](https://ollama.com) from its official installer, then run:

```bash
./setup_qwen.sh              # pulls qwen3:8b by default
./setup_qwen.sh <model-tag>  # or another Ollama model
```

Confirm the connection under **Settings → AI Assistant → Test connection**.

---

<details>
<summary><b>Manual installation (equivalent to <code>install.sh</code>)</b></summary>

<br/>

Use these commands if you cannot run the installer or need to debug a single step.

**Environment 1: `qoala`**

```bash
conda create -n qoala python=3.10 -y
conda install -n qoala -c conda-forge tk -y
conda activate qoala

python -m pip install --upgrade pip wheel setuptools
python -m pip install -r requirements/qoala.txt
python -m playwright install chromium

# NetSquid: authenticated with YOUR credentials.
# URL-encode the username and password if they contain special characters (@, :, /, #, ...).
python -m pip install \
  --extra-index-url "https://${NETSQUIDPYPI_USER}:${NETSQUIDPYPI_PWD}@pypi.netsquid.org" \
  netsquid

# Qoala: from the official QuTech repository
python -m pip install \
  --extra-index-url "https://${NETSQUIDPYPI_USER}:${NETSQUIDPYPI_PWD}@pypi.netsquid.org" \
  "git+https://github.com/QuTech-Delft/qoala-sim.git@dev"

python -m ipykernel install --user --name qoala --display-name "Python (qoala)"
conda deactivate
```

**Environment 2: `pytket_dqc`**

```bash
conda create -n pytket_dqc python=3.10 -y

# macOS only: toolchain for KaHyPar
conda install -n pytket_dqc -c conda-forge cmake boost-cpp -y

conda activate pytket_dqc
python -m pip install --upgrade pip wheel setuptools
python -m pip install -r requirements/pytket_dqc.txt
python -m pip install "git+https://github.com/Quantinuum/pytket-dqc.git@main"

python -m ipykernel install --user --name pytket_dqc --display-name "Python (pytket_dqc)"
conda deactivate
```

Finally, run `./install.sh --verify`.

</details>

---

## `06` &nbsp; Launching QNEST

```bash
./launch_qnest.sh
```

The launcher locates the `qoala` interpreter directly and falls back to `conda run` if necessary. Direct launch is also possible:

```bash
conda activate qoala
python app_gui.py
```

**Launcher overrides**

| Variable | Purpose |
|---|---|
| `QNEST_PYTHON` | Full path to the Python interpreter to use |
| `QNEST_CONDA_ENV` | Name of the main environment (default `qoala`) |
| `QNEST_OLLAMA_ENDPOINT` | Assistant endpoint (default `http://127.0.0.1:11434`) |

---

## `07` &nbsp; Workflow

| Stage | What happens |
|---|---|
| **Circuit** | Import QASM/Python, edit QASM directly, or generate MQT Bench circuits. Batch mode runs inclusive qubit sweeps, and each requested benchmark/qubit combination is checked against the installed MQT Bench version |
| **Network** | The authoritative source for architecture and QPU capacity. Set the number of QPUs, qubits per QPU, topology and link distance. Success probability, fidelity, attempt rate, Ebit rate and latency are **derived from the physical model**, not entered by hand |
| **Compile / Distribute** | ① clean and normalise → ② prepare with `DQCPass` → ③ distribute with pytket-DQC → ④ build the EJPP representation → ⑤ export bridge data. Previews cover Original, Cleaned, After DQCPass, Distributed and EJPP |
| **Schedule** | Qoala/NetSquid runs in a child process and produces request tables plus **Timed Gantt** and **Layer Gantt** views. **Open interactive** opens the saved HTML without rerunning. Timing controls are in µs, while the backend may keep ns internally |
| **Run / Analyse** | AFA-QSP and HAMFA-QSP Monte Carlo. Compile and Schedule are **not** repeated per sample; only the stochastic protocol stage is |

### Run gating

> [!NOTE]
> AFA-QSP/HAMFA-QSP Monte Carlo is available **only** for an **All-to-all → Shared switch** network. For switch-free networks the workflow ends after Schedule, and the Run page is used to collect and export the artifacts of the earlier stages.

### Reference configuration

These are the initial values used by the bundled notebooks. Changing a control in the GUI changes the experiment, and QNEST never silently resets values chosen by the researcher.

| Parameter | Value |
|---|---|
| Distribution method | `PartitioningAnnealing` |
| Distribution seed | `1` |
| Single-qubit gate | `5.5 µs` |
| Two-qubit gate | `66 µs` |
| EPR + EJPP start | `276.471 µs` |
| Ending process | `71.99 µs` |
| Qoala strategy | `QOALA` |
| Protocol seed | `42` |
| Monte Carlo repetitions | `30` |
| Memory coherence constant | `2.8e9 ns` |
| Initial stored-pair fidelity | `0.9796744718797619` |
| Fidelity threshold | `0.9306907483` |
| Cutoff fraction | `0.05` |

### Result tables

| AFA-QSP columns | HAMFA-QSP columns |
|---|---|
| Request · Control QPU · Target QPU · Control link · Target link · Wait window · Deadline · Punishment · Trials · Time to success · Blocked · Deadline margin | Request · Control QPU · Target QPU · Control link · Target link · Wait window · Deadline · Case · Path · Completion · Time to success · Punishment · Blocked · Deadline margin |

Times can be displayed in **ns** or **µs**. The saved per-replicate tables always stay in raw nanoseconds, so the display unit never changes the data. In batch mode, scaling plots show EPR pairs, punishment time, HAMFA resource use and blocked requests versus circuit size.

---

## `08` &nbsp; QNEST Assistant

The assistant is a planning, configuration and explanation layer on the right side of the workspace. It receives the live state of the workspace with every request and can operate only the validated controls that the application exposes. It has **no shell or Python execution rights**, and all scientific computation stays in the deterministic QNEST backend.

- For an all-to-all network with no interconnect specified, it defaults to **Shared switch → Memory-assisted**. Explicit choices take precedence.
- It respects the Run gating rule and never proposes Monte Carlo for a switch-free network.
- Its default starter experiment is **GHZ 5 → 20 qubits (step 2), 7 QPUs, 4 qubits/QPU, All-to-all, Shared switch, Memory-assisted**.

---

## `09` &nbsp; Repository Structure

```
QNEST/
│
├── app_gui.py                   # Desktop application entry point
├── src/                         # Scientific and pipeline backend
│   ├── circuit_prep.py          # Circuit cleaning and normalisation
│   ├── distribution.py          # DQCPass + pytket-DQC distribution
│   ├── ejpp_representation.py   # Explicit EJPP circuit representation
│   ├── bridge_export.py         # Compiler → scheduler bridge data
│   ├── kernel_bridge.py         # Persistent bridge to the pytket_dqc kernel
│   ├── network.py               # Physical network model
│   ├── all_photonic_noise.py    # All-photonic switch model
│   ├── memory_assisted_noise.py # Memory-assisted switch model
│   ├── qoala_*.py, scheduler.py # Qoala/NetSquid scheduling
│   ├── schedule_worker.py       # Isolated scheduling process
│   ├── afa_qsp.py, hamfa_qsp.py # Protocol Monte Carlo
│   ├── llm_assistant.py         # QNEST Assistant
│   └── ...                      # Plotting, reports, Gantt views, configuration
│
├── requirements/                # Per-environment pip requirements
│   ├── qoala.txt
│   └── pytket_dqc.txt
├── rel/                         # Guided installers (no third-party binaries included)
├── docs/                        # User guide, assistant notes, knowledge base
├── assets/                      # Logos and credits imagery
├── results/, results.ipynb      # Reference Monte Carlo notebooks and figures
├── batch_runs/, generated_mqt/  # Example batch output and generated circuits
│
├── install.sh                   # Environment installer and verifier
├── launch_qnest.sh              # Application launcher
├── setup_qwen.sh                # Optional local assistant setup
└── netsquid_credentials.txt     # LOCAL credential template (never commit values)
```

### Output layout

```
runs/<experiment>/
├── 01_circuit/
├── 02_network/
├── 03_compile/
├── 04_schedule/
├── 05_run/
│   └── result_tables/run_XXX/   # Clean per-replicate AFA/HAMFA tables (ns)
└── logs/
```

Batch experiments are collected under `batch_runs/`. User-interface preferences are stored in `~/.qnest/ui_settings.json` and never alter scientific data.

---

## `10` &nbsp; Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `netsquid installation failed` | Wrong credentials, the account is not yet activated, or there is no NetSquid wheel for your Python/platform. Check that you can sign in at [forum.netsquid.org](https://forum.netsquid.org), use the **username** rather than the e-mail address, and keep Python 3.10 |
| Credentials rejected although the password is correct | Special characters in the password. Use `install.sh`, which URL-encodes credentials automatically, or encode them yourself for manual installation |
| `conda not found on PATH` | Install Miniforge and reopen the terminal |
| `Unsupported platform` | Native Windows detected. Run QNEST inside WSL 2 |
| KaHyPar fails to build | Missing toolchain. Run `conda install -n pytket_dqc -c conda-forge cmake boost-cpp` |
| `kernel "pytket_dqc" NOT visible` | Re-register it: `conda run -n pytket_dqc python -m ipykernel install --user --name pytket_dqc` |
| GUI does not start / `tkinter` missing | Run `conda install -n qoala -c conda-forge tk`. On WSL, confirm that WSLg is available |
| Circuit previews missing | Chromium install failed. Run `conda run -n qoala python -m playwright install chromium`; QNEST otherwise falls back to a system Chrome/Chromium or the native QASM preview |
| Launcher cannot find Python | Set `QNEST_PYTHON=/full/path/to/envs/qoala/bin/python` |
| Assistant unreachable | Start `ollama serve` and test under **Settings → AI Assistant** |

---

## `11` &nbsp; Documentation and Support

| Resource | Location |
|---|---|
| User guide | [`docs/QNEST_User_Guide.html`](./docs/QNEST_User_Guide.html), also available from the **Documentation** button in the application |
| Assistant notes | [`docs/QNEST_AI_Assistant.md`](./docs/QNEST_AI_Assistant.md) |
| Assistant knowledge base | [`docs/QNEST_Knowledge_Base.md`](./docs/QNEST_Knowledge_Base.md) |

**Bug reports:** choose **Report a Bug** in the toolbar. QNEST prepares an e-mail to **elyasi@chalmers.se** and can save a diagnostic ZIP with the report text, UI settings and current-run logs. Attach the ZIP before sending. Diagnostic archives never contain NetSquid credentials, but please review any file before sharing it.

For problems with NetSquid or Qoala themselves, including accounts, licensing and package availability, contact their maintainers directly through the [NetSquid forum](https://forum.netsquid.org) or the [qoala-sim repository](https://github.com/QuTech-Delft/qoala-sim).

---

## `12` &nbsp; Credits and Acknowledgements

QNEST is a collaboration between **Chalmers University of Technology** and the **University of Bristol**.

| Role | Names |
|---|---|
| Senior developers | Seyed Navid Elyasi · Sima Bahrani |
| Co-authors | Rui Wang · Dimitra Simeonidou · Paolo Monti · Rui Lin |

<div align="center">

<img src="./assets/about-logo-wacqt.png" height="48"/> &nbsp;&nbsp;
<img src="./assets/about-logo-bristol.png" height="48"/> &nbsp;&nbsp;
<img src="./assets/about-logo-smart-internet-lab.png" height="48"/> &nbsp;&nbsp;
<img src="./assets/about-logo-iqn-hub.png" height="48"/>

</div>

This work acknowledges support from the **Swedish Research Council (VR)** and the **UK EPSRC Integrated Quantum Networks Hub (EP/Z533208/1)**.

NetSquid and Qoala are developed by QuTech. pytket-DQC is developed by Quantinuum. QNEST is an independent project and is not affiliated with or endorsed by these organisations.

---

<div align="center">

Made at **Chalmers University of Technology** and the **University of Bristol**

<img src="https://capsule-render.vercel.app/api?type=waving&color=0f62fe&height=100&section=footer" width="100%"/>

</div>
