# QNEST Assistant

The QNEST Assistant is the natural-language control and explanation layer built into the desktop application. It is deliberately separate from the scientific backend: the model can plan and request validated QNEST actions, but the numerical work remains in the existing Circuit, Network, Compile, Schedule and Run code.

## Local setup

The default local configuration uses Qwen3 8B through Ollama. Run:

```bash
./setup_qwen.sh
```

Then open **Settings → AI Assistant** to test the endpoint and model.

The default endpoint is `http://127.0.0.1:11434` and the default model is `qwen3:8b`. QNEST also accepts an OpenAI-compatible endpoint when configured by the user.

## Live workspace context

Every assistant request is accompanied by a fresh snapshot of the QNEST workspace. The context includes the active stage, circuit set, network configuration, exposed controls, compilation state, schedule state, Run availability and available scientific results. The assistant should therefore react to the current application state rather than relying on an earlier conversational assumption.

The control catalogue includes stable identifiers, current values, enum choices, ranges and whether a control is currently active. Settings and scientific controls use the same validated action path.

## Planning and execution

For a full experiment request, the dependency order is:

**Circuit / MQT → Network → Compile / Distribute → Schedule → Run**

QNEST resolves downstream circuit scopes only after the preceding asynchronous stage has finished. This matters in batch mode because `All circuits`, `All compiled circuits` and `All scheduled circuits` refer to different live eligibility sets.

The assistant cannot bypass stage prerequisites. If a stage fails, the remaining plan is stopped and the error from that stage is reported.

## Network defaults and Run gating

For an all-to-all network where the researcher has not named an interconnect, the assistant uses:

**Shared switch → Memory-assisted**

An explicit request for direct QPU links or an all-photonic switch overrides that default.

AFA-QSP/HAMFA-QSP Monte Carlo is available only when the Network is configured as **All-to-all → Shared switch**. When the network is switch-free, the valid workflow ends after Schedule. In that case the Run page provides the earlier-stage artifacts instead of starting Monte Carlo, and the assistant must not include a protocol-run action in the plan.

## Default experiment suggestion

The main starter suggestion is:

- benchmark: GHZ State;
- qubit sweep: 5 to 20, step 2;
- network: 7 QPUs;
- computation capacity: 4 qubits per QPU;
- topology: All-to-all;
- interconnect: Shared switch;
- switch type: Memory-assisted.

Unspecified physical, scheduling and Monte Carlo settings retain the application's reference values unless the researcher asks to change them.

## Results available to the assistant

The assistant can inspect the actual outputs already produced by each stage. Result interpretation should distinguish configuration, measured/simulated output and derived analysis.

For Run, the assistant receives the same compact per-request tables displayed in the GUI for the selected circuit and Monte Carlo replicate. It must not replace these with the simulator's internal HAMFA diagnostic fields.

AFA result fields are Request, Control QPU, Target QPU, Control link, Target link, Wait window, Deadline, Punishment, Trials, Time to success, Blocked and Deadline margin.

HAMFA result fields are Request, Control QPU, Target QPU, Control link, Target link, Wait window, Deadline, Case, Path, Completion, Time to success, Punishment, Blocked and Deadline margin.

The GUI can display timing columns in ns or µs. The selected display unit is part of the assistant context. Saved per-replicate result tables remain raw ns.

Batch mode retains the standard scaling plots for EPR pairs, punishment time, HAMFA resource use and blocked requests.

## Safety and validation model

The assistant acts only through the QNEST action catalogue. It does not receive an unrestricted Python interpreter or shell. All action arguments are validated against the same application controls used by the desktop UI.

The scientific backend remains authoritative. The model may explain a result or propose a configuration, but it does not substitute its own numerical answer for a simulator result that QNEST has not produced.

When approval is enabled, proposed changes are shown in the plan card before they are applied.

## Local factual grounding

QNEST-specific factual questions use `docs/QNEST_Knowledge_Base.md` plus the current workspace context. That file contains project identity, people, institutions, workflow, runtime architecture, result-table contract and current assistant defaults. If a fact is not documented there or in live state, the assistant should say that it is not available rather than inventing it.
