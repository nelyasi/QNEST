# QNEST

QNEST is a desktop toolkit for building and running end-to-end quantum-network experiments. The application keeps the complete experiment in one workspace: circuit preparation, physical-network definition, distributed compilation, Qoala/NetSquid scheduling, and protocol analysis are connected rather than treated as separate scripts.

The current release is **v0.3.12**.

## What is included

The main workflow is:

**Circuit → Network → Compile / Distribute → Schedule → Run / Analyse**

QNEST uses two Python environments on purpose. The `qoala` environment runs the desktop interface, Qoala/NetSquid scheduling, pandas/plotting, AFA-QSP and HAMFA-QSP. The `pytket_dqc` environment handles MQT Bench, Qiskit, pytket, pytket-DQC, DQCPass and bridge generation. The GUI communicates with the second environment through a persistent kernel bridge.

The repository also contains the reference Monte Carlo notebooks and saved example figures used to check the desktop implementation.

## Installation

QNEST expects Conda or Miniforge and a NetSquid account. Put the NetSquid credentials in `netsquid_credentials.txt`, then run:

```bash
./install.sh
```

To verify an existing installation without rebuilding the environments:

```bash
./install.sh --verify
```

Useful installer options are:

```text
--qoala-only
--pytket-only
--python 3.10
--force
--verify
```

NetSquid supports Linux and macOS. Windows users should run the project inside WSL.

## Launching QNEST

The normal launcher is:

```bash
./launch_qnest.sh
```

It looks for the `qoala` interpreter directly and falls back to `conda run` when necessary. You can override the interpreter with `QNEST_PYTHON=/full/path/to/python` or the environment name with `QNEST_CONDA_ENV`.

Direct launch is also possible after activating the Qoala environment:

```bash
conda activate qoala
python app_gui.py
```

## Circuit workspace

The Circuit workspace supports imported QASM/Python sources, direct QASM editing, and MQT Bench generation. Experiments can be run as a single circuit or as a batch/sweep.

In batch mode, scalable MQT benchmarks use an inclusive qubit sweep. The built-in assistant starter experiment is a GHZ sweep from **5 to 20 qubits in steps of 2**. QNEST checks the requested benchmark/qubit combinations against the installed MQT Bench version before generation.

The Circuit page keeps two benchmark columns at normal and docked workspace widths. Long benchmark names wrap rather than changing the scientific selection.

## Network workspace

The Network page is the authoritative source for physical architecture and QPU capacity. It contains a tabular configuration view and a graphical designer.

For predefined topologies, the Table view controls the number of QPUs, qubits per QPU and topology. An all-to-all network may use either direct QPU links or a shared switch. Shared switches support **All-photonic** and **Memory-assisted** operation.

Link distance is editable. Success probability, fidelity, attempt rate, Ebit rate and propagation latency are calculated from the selected physical model. They are not arbitrary user-entered result fields.

For the memory-assisted model, the memory parameters are presented together with the photonic generation parameters used before storage. The Run stage applies the HAMFA memory-age law to stored pairs.

The Network page is responsive: descriptive text remains left aligned and wraps to the available workspace width, including when the AI Assistant dock is open.

## Compile / Distribute

Compile performs the sequence used by the research workflow:

1. clean/normalise the circuit input;
2. prepare it with `DQCPass`;
3. distribute it with pytket-DQC;
4. create the explicit EJPP representation; and
5. export the bridge data consumed by the scheduler.

The Compile preview retains the main circuit stages: Original, Cleaned, After DQCPass, Distributed circuit and EJPP representation. Interactive HTML and QASM representations are saved when available.

## Schedule

Schedule runs the Qoala/NetSquid workflow in a child process. The user-facing timing controls are expressed in microseconds while the scientific backend may retain nanoseconds internally.

The scheduler produces request tables and two Gantt views: Timed Gantt and Layer Gantt. QNEST stores the local HTML representation and shows a preview in the desktop application. **Open interactive** launches the live local HTML without rerunning the scheduler.

## Run / Analyse

AFA-QSP and HAMFA-QSP Monte Carlo analysis is enabled only for an **All-to-all → Shared switch** network. If the network is switch-free, QNEST stops the valid workflow after Schedule and the Run page is used to collect/export the artifacts produced by the earlier stages.

When Run is available, Compile and Schedule are not repeated for every Monte Carlo sample. The stochastic AFA/HAMFA protocol stage is the repeated portion.

The standard reference configuration used by the bundled notebooks includes:

- distribution method: `PartitioningAnnealing`;
- distribution seed: `1`;
- single-qubit gate: `5.5 µs`;
- two-qubit gate: `66 µs`;
- EPR + EJPP start: `276.471 µs`;
- ending process: `71.99 µs`;
- Qoala strategy: `QOALA`;
- protocol seed: `42`;
- Monte Carlo repetitions: `30`;
- memory coherence constant: `2.8e9 ns`;
- initial stored-pair fidelity: `0.9796744718797619`;
- fidelity threshold: `0.9306907483`;
- cutoff fraction: `0.05`.

These are initial reference values. Changing a control in the GUI changes the experiment; QNEST does not silently reset researcher-selected values.

### Result tables

The normal Run view shows compact per-request tables rather than the simulator's internal diagnostic state.

AFA-QSP displays:

- Request
- Control QPU
- Target QPU
- Control link
- Target link
- Wait window
- Deadline
- Punishment
- Trials
- Time to success
- Blocked
- Deadline margin

HAMFA-QSP displays:

- Request
- Control QPU
- Target QPU
- Control link
- Target link
- Wait window
- Deadline
- Case
- Path
- Completion
- Time to success
- Punishment
- Blocked
- Deadline margin

The tables are centred, use alternating row shading, and keep compact readable numeric formatting. Simulator-only HAMFA diagnostics remain internal for validation and aggregation and are not presented as requested scientific output.

The result selector can display time columns in **ns** or **µs**. The saved per-replicate result tables remain in raw nanoseconds so changing the display unit never changes the simulation data.

### Batch plots

Batch mode retains the scaling figures used by the notebook workflow, including EPR pairs, punishment time, HAMFA resource use and blocked requests versus circuit size.

## QNEST Assistant

The right-side QNEST Assistant is a planning, configuration and explanation layer. The local default is Qwen3 8B through Ollama. It receives the current exposed QNEST controls and current scientific state on every request and must use that live state rather than assuming the workspace has not changed.

For an all-to-all network where the researcher does not specify the interconnect, the assistant uses **Shared switch → Memory-assisted**. Explicit choices such as direct links or an all-photonic switch take precedence.

The assistant understands the Run gating rule. It will not propose AFA/HAMFA Monte Carlo for a switch-free network. When the user asks for result interpretation, the assistant receives the same compact result tables shown in the Run page, together with the selected display unit.

The default assistant experiment is:

**GHZ 5→20 qubits, step 2, 7 QPUs, 4 qubits/QPU, All-to-all, Shared switch, Memory-assisted.**

The assistant can manipulate the validated controls exposed by the application. It does not receive unrestricted shell or Python execution privileges. Scientific computation remains in the deterministic QNEST backend.

To prepare the local model:

```bash
./setup_qwen.sh
```

The model and endpoint can then be checked under **Settings → AI Assistant**.

## Output layout

Each compiled circuit receives a run directory with stage-specific artifacts:

```text
runs/<experiment>/
  01_circuit/
  02_network/
  03_compile/
  04_schedule/
  05_run/
  logs/
```

Batch experiments are collected under `batch_runs/`. Per-circuit scientific run folders are preserved when a complete batch archive is exported.

Run stores clean per-replicate AFA/HAMFA result tables under `05_run/result_tables/run_XXX/`. Aggregate Monte Carlo summaries and plot inputs are retained separately for analysis.

## Settings and appearance

The Settings window controls theme, UI scale, startup behaviour and AI configuration. User interface preferences are stored in:

```text
~/.qnest/ui_settings.json
```

They do not alter the scientific data unless the corresponding scientific control is explicitly changed.

## Bug reports

Choose **Report a Bug** from the top toolbar. QNEST prepares an email addressed to:

**elyasi@chalmers.se**

The dialog can also save a diagnostic ZIP containing the report text, UI settings and current-run logs. The default mail application is opened with the recipient, subject and report text filled in. If a diagnostic ZIP is created, attach it before sending the message.

## Documentation

The formatted user guide is `docs/QNEST_User_Guide.html`. The assistant-specific notes are in `docs/QNEST_AI_Assistant.md`. `docs/QNEST_Knowledge_Base.md` is the local factual reference supplied to the assistant for QNEST-specific questions.

## Project credits

QNEST is presented as a collaboration between Chalmers University of Technology and the University of Bristol. The featured senior developers are Seyed Navid Elyasi and Sima Bahrani. Project co-authors listed in the local project material are Rui Wang, Dimitra Simeonidou, Paolo Monti and Rui Lin.

Project/support marks include WACQT, University of Bristol, Smart Internet Lab and the Integrated Quantum Networks Hub. The project acknowledgement cites the Swedish Research Council (VR) and the UK EPSRC Integrated Quantum Networks Hub (EP/Z533208/1).
