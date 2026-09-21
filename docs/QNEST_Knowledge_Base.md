# QNEST local knowledge base

This file is the factual reference used by the QNEST Assistant. Live workspace state takes precedence for current control values and experiment results. This file supplies the stable project and workflow facts that are not tied to one run.

## Project

QNEST means **Quantum Network End-to-End Simulation Toolkit**. It is a desktop research toolkit for end-to-end experiments with optical quantum data-centre and quantum-network workflows.

The integrated workflow is:

**Circuit → Network → Compile / Distribute → Schedule → Run / Analyse**

## People and institutions

Featured senior developers:

- Seyed Navid Elyasi — Chalmers University of Technology
- Sima Bahrani — University of Bristol

Project co-authors listed in the supplied QNEST material:

- Rui Wang — University of Bristol
- Dimitra Simeonidou — University of Bristol
- Paolo Monti — Chalmers University of Technology
- Rui Lin — Chalmers University of Technology

QNEST is presented as a collaboration between Chalmers University of Technology and the University of Bristol. Project/support marks include WACQT, University of Bristol, Smart Internet Lab and the Integrated Quantum Networks Hub. The project acknowledgement cites the Swedish Research Council (VR) and the UK EPSRC Integrated Quantum Networks Hub (EP/Z533208/1).

## Circuit

Circuit accepts imported QASM/Python sources, direct QASM editing and MQT Bench generation. Single-circuit and batch/sweep workflows are supported. Scalable MQT sweeps use an inclusive minimum/maximum/step sequence and are checked against the installed MQT Bench version before generation.

The assistant starter experiment uses GHZ circuits from 5 to 20 qubits in steps of 2.

## Network

Network defines QPU count, qubits per QPU, topology, interconnect and physical parameters. For an all-to-all topology the interconnect can be Direct QPU links or Shared switch. Shared switches can be All-photonic or Memory-assisted.

Link distance is editable. Success probability, fidelity, attempt rate, Ebit rate and propagation latency are calculated from the selected physical model.

For a memory-assisted switch, the photonic parameters still describe entanglement generation before storage. Stored-pair fidelity then evolves according to the HAMFA memory model during Run.

When the assistant is asked for an all-to-all network without an explicit interconnect, it should use Shared switch → Memory-assisted. An explicit researcher choice overrides this default.

## Compile / Distribute

Compile cleans the circuit, applies DQCPass preparation, runs pytket-DQC distribution, creates the EJPP representation and exports the bridge consumed by Qoala. The application retains Original, Cleaned, After DQCPass, Distributed circuit and EJPP representation views.

## Schedule

Schedule runs the Qoala/NetSquid timing workflow. It produces request tables and Timed/Layer Gantt visualisations. Interactive Gantt HTML is saved locally. User-facing schedule values are expressed in µs while backend artifacts may retain ns.

## Run / Analyse

AFA-QSP/HAMFA-QSP Monte Carlo is available only when the selected Network is **All-to-all → Shared switch**. A switch-free network ends the executable workflow after Schedule. In that case QNEST offers the artifacts from Circuit, Network, Compile and Schedule instead of running Monte Carlo.

Compile and Schedule run once per circuit. AFA/HAMFA is the stochastic repeated stage.

### Compact result tables

The normal Run UI intentionally presents only the result fields needed for per-request analysis. Internal HAMFA diagnostics remain available to validation and aggregation code but are not part of the researcher-facing table.

AFA columns:

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

HAMFA columns:

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

The GUI can display time columns in ns or µs. This conversion is presentation-only. Saved per-replicate result tables remain raw ns.

Batch mode retains the EPR-pairs, punishment-time, HAMFA-resource-use and blocked-request scaling plots.

### Reference values

The bundled Monte Carlo notebooks provide the initial reference settings used by the application where applicable:

- distribution method `PartitioningAnnealing`
- distribution seed `1`
- single-qubit gate `5.5 µs`
- two-qubit gate `66 µs`
- EPR + EJPP start `276.471 µs`
- ending process `71.99 µs`
- Qoala strategy `QOALA`
- `P_SUCC = 0.044426421303161545`
- protocol seed `42`
- 30 Monte Carlo repetitions
- `Δt_c = 2.8e9 ns`
- `F_I = 0.9796744718797619`
- `F_T = 0.9306907483`
- `alpha = 0.05`
- deadline equality counts as blocked
- background generation starts at `0 ns`

These values are defaults, not immutable constants. Explicit researcher input takes precedence.

## Assistant

The Assistant is a local-first planning, control and explanation layer. Qwen3 8B through Ollama is the default local model. It receives the current exposed controls and scientific state on each turn and should adapt immediately when the workspace changes.

The default assistant experiment is:

**GHZ 5→20 qubits, step 2, 7 QPUs × 4 qubits/QPU, All-to-all, Shared switch, Memory-assisted.**

The Assistant uses whitelisted QNEST actions only. It has no arbitrary shell/Python execution capability. Scientific validation and simulation remain in the deterministic backend.

## Runtime environments

QNEST keeps two environments:

- `qoala` for the GUI, Qoala/NetSquid, AFA/HAMFA, pandas and plotting;
- `pytket_dqc` for MQT Bench, Qiskit, pytket, DQCPass and pytket-DQC.

The GUI uses a persistent bridge to the `pytket_dqc` environment rather than merging the two scientific stacks.

## Bug reports

The Report a Bug dialog prepares an email for **elyasi@chalmers.se**. It can also create a diagnostic ZIP with report text, UI settings and current-run logs. The user's default mail application is responsible for sending the message.

## Answering QNEST-specific questions

Use this file and the current workspace state. Do not invent project authors, institutions, controls, results or scientific capabilities that are not present here or in the live application state.
