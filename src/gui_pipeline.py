from datetime import datetime
from pathlib import Path
import contextlib
import io
import json
import math
import re
import shutil
import subprocess
import sys
import traceback
import zipfile
NOTEBOOK_AFA_TABLE_COLUMNS = ['Request k', 'QPU C (i)', 'QPU T (j)', 'QPU C Link (m)', 'QPU T Link (n)', 'Δt_w(k)^(C_m,T_n) [ns]', 't_D(k)^(C_m,T_n) [ns]', 'Δt_P(k)^(C_m,T_n) [ns]', 'Number of trials', 'Time duration until success [ns]', 'Blocked', 'Time before deadline [ns]']
NOTEBOOK_HAMFA_TABLE_COLUMNS = ['Request k', 'QPU C (i)', 'QPU T (j)', 'QPU C Link (m)', 'QPU T Link (n)', 'Δt_w(k)^(C_m,T_n) [ns]', 't_D(k)^(C_m,T_n) [ns]', 'HAMFA Case', 'Path Used', 'Completion time [ns]', 'Time duration until success [ns]', 'Δt_P(k)^(C_m,T_n) [ns]', 'Blocked', 'Time before deadline [ns]']
_SHARED_PYTKET_BRIDGES = {}

def _noop_log(_msg):
    pass

def _slug(text):
    text = re.sub('[^A-Za-z0-9._-]+', '_', str(text).strip()).strip('_')
    return text or 'circuit'

def _json_default(value):
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, 'item'):
        try:
            return value.item()
        except Exception:
            pass
    if hasattr(value, 'tolist'):
        try:
            return value.tolist()
        except Exception:
            pass
    if isinstance(value, set):
        return sorted(value, key=str)
    return str(value)

def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=_json_default), encoding='utf-8')
    return path

def _write_clean_result_html(path, df, title):
    table_html = df.to_html(index=False, border=0, classes='qnest-results', justify='center')
    css = '\n    <style>\n      body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:24px;color:#101828;background:#fff;}\n      h2{font-size:20px;margin:0 0 6px;}\n      p{color:#667085;margin:0 0 16px;font-size:13px;}\n      .table-wrap{overflow:auto;border:1px solid #d0d5dd;border-radius:8px;}\n      table.qnest-results{border-collapse:collapse;width:max-content;min-width:100%;font-size:13px;}\n      table.qnest-results th{background:#f2f4f7;font-weight:600;color:#344054;text-align:center;padding:10px 12px;border-bottom:1px solid #d0d5dd;white-space:nowrap;}\n      table.qnest-results td{text-align:center;padding:9px 12px;border-bottom:1px solid #eaecf0;white-space:nowrap;}\n      table.qnest-results tbody tr:nth-child(even){background:#f9fafb;}\n      table.qnest-results tbody tr:last-child td{border-bottom:0;}\n    </style>\n    '
    html = f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title>{css}</head><body><h2>{title}</h2><p>Per-request Monte Carlo results. Time columns are stored in nanoseconds.</p><div class='table-wrap'>{table_html}</div></body></html>"
    path.write_text(html, encoding='utf-8')
    return path

def _presentation_table_us(df):
    try:
        import pandas as pd
        out = df.copy()
        rename = {}
        for col in list(out.columns):
            name = str(col)
            if '[ns]' in name or '_ns' in name:
                numeric = pd.to_numeric(out[col], errors='coerce')
                mask = numeric.notna()
                if mask.any():
                    out[col] = out[col].astype(object)
                    out.loc[mask, col] = numeric.loc[mask].astype(float) / 1000.0
                new = name.replace('[ns]', '[µs]').replace('_ns', '_us')
                rename[col] = new
        return out.rename(columns=rename) if rename else out
    except Exception:
        return df

class PipelineState:

    def __init__(self, run_dir=None, circuit_name='circuit', input_qasm=None, network_json=None, bridge_file=None, compile_metadata=None, qoala_result=None, request_table=None, afa_table=None, afa_summary=None, afa_run_summaries=None, afa_exact_run_tables=None, hamfa_table=None, hamfa_summary=None, hamfa_run_summaries=None, hamfa_exact_run_tables=None, validation=None):
        self.run_dir = run_dir
        self.circuit_name = circuit_name
        self.input_qasm = input_qasm
        self.network_json = network_json
        self.bridge_file = bridge_file
        self.compile_metadata = {} if compile_metadata is None else compile_metadata
        self.qoala_result = qoala_result
        self.request_table = request_table
        self.afa_table = afa_table
        self.afa_summary = afa_summary
        self.afa_run_summaries = [] if afa_run_summaries is None else afa_run_summaries
        self.afa_exact_run_tables = [] if afa_exact_run_tables is None else afa_exact_run_tables
        self.hamfa_table = hamfa_table
        self.hamfa_summary = hamfa_summary
        self.hamfa_run_summaries = [] if hamfa_run_summaries is None else hamfa_run_summaries
        self.hamfa_exact_run_tables = [] if hamfa_exact_run_tables is None else hamfa_exact_run_tables
        self.validation = validation

    def __repr__(self):
        values = (self.run_dir, self.circuit_name, self.input_qasm, self.network_json, self.bridge_file, self.compile_metadata, self.qoala_result, self.request_table, self.afa_table, self.afa_summary, self.afa_run_summaries, self.afa_exact_run_tables, self.hamfa_table, self.hamfa_summary, self.hamfa_run_summaries, self.hamfa_exact_run_tables, self.validation)
        names = ('run_dir', 'circuit_name', 'input_qasm', 'network_json', 'bridge_file', 'compile_metadata', 'qoala_result', 'request_table', 'afa_table', 'afa_summary', 'afa_run_summaries', 'afa_exact_run_tables', 'hamfa_table', 'hamfa_summary', 'hamfa_run_summaries', 'hamfa_exact_run_tables', 'validation')
        return 'PipelineState(' + ', '.join((f'{name}={value!r}' for name, value in zip(names, values))) + ')'

    def __eq__(self, other):
        if other.__class__ is not self.__class__:
            return NotImplemented
        return self.__dict__ == other.__dict__

    def clear_after_compile(self):
        self.qoala_result = None
        self.request_table = None
        self.afa_table = None
        self.afa_summary = None
        self.afa_run_summaries = []
        self.afa_exact_run_tables = []
        self.hamfa_table = None
        self.hamfa_summary = None
        self.hamfa_run_summaries = []
        self.hamfa_exact_run_tables = []
        self.validation = None

    def clear_after_schedule(self):
        self.afa_table = None
        self.afa_summary = None
        self.afa_run_summaries = []
        self.afa_exact_run_tables = []
        self.hamfa_table = None
        self.hamfa_summary = None
        self.hamfa_run_summaries = []
        self.hamfa_exact_run_tables = []
        self.validation = None

class PipelineController:

    def __init__(self, project_root=None):
        self.project_root = Path(project_root or Path(__file__).resolve().parents[1]).resolve()
        self.runs_dir = self.project_root / 'runs'
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.state = PipelineState()
        self._pytket_bridge = None

    def new_run(self, circuit_name='circuit'):
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        run_dir = self.runs_dir / f'{stamp}_{_slug(circuit_name)}'
        for sub in ('01_circuit', '02_network', '03_compile', '04_schedule', '05_run', 'logs'):
            (run_dir / sub).mkdir(parents=True, exist_ok=True)
        self.state = PipelineState(run_dir=run_dir, circuit_name=_slug(circuit_name))
        _write_json(run_dir / 'session.json', {'created': datetime.now().isoformat(timespec='seconds'), 'circuit_name': self.state.circuit_name, 'pipeline': ['circuit', 'network', 'compile', 'schedule', 'run']})
        return run_dir

    def ensure_run(self, circuit_name='circuit'):
        if self.state.run_dir is None:
            return self.new_run(circuit_name)
        return self.state.run_dir

    def artifact_files(self):
        run_dir = self.state.run_dir
        if run_dir is None or not run_dir.exists():
            return []
        return sorted((p for p in run_dir.rglob('*') if p.is_file()), key=lambda p: (str(p.parent), p.name.lower()))

    def export_session_zip(self, destination):
        run_dir = self.state.run_dir
        if run_dir is None:
            raise RuntimeError('There is no active QNEST run to export.')
        destination = Path(destination).expanduser().resolve()
        if destination.suffix.lower() != '.zip':
            destination = destination.with_suffix('.zip')
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for path in run_dir.rglob('*'):
                if path.is_file():
                    zf.write(path, path.relative_to(run_dir))
        return destination

    @staticmethod
    def copy_artifact(source, destination):
        source = Path(source)
        destination = Path(destination)
        if destination.is_dir():
            destination = destination / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return destination

    def save_inputs(self, qasm_text, network_data, circuit_name='circuit', *, new_run=False):
        if new_run or self.state.run_dir is None:
            self.new_run(circuit_name)
        run_dir = self.ensure_run(circuit_name)
        qasm_path = run_dir / '01_circuit' / 'input.qasm'
        network_path = run_dir / '02_network' / 'gui_network.json'
        qasm_path.write_text(qasm_text, encoding='utf-8')
        _write_json(network_path, network_data)
        self.state.input_qasm = qasm_path
        self.state.network_json = network_path
        self.state.circuit_name = _slug(circuit_name)
        return (qasm_path, network_path)

    def _bridge(self, log):
        key = str(self.project_root)
        if self._pytket_bridge is None:
            cached = _SHARED_PYTKET_BRIDGES.get(key)
            if cached is not None:
                self._pytket_bridge = cached
            else:
                log('[INFO] Starting persistent pytket_dqc kernel …')
                from src.kernel_bridge import start_bridge
                self._pytket_bridge = start_bridge(register_magics=False, quiet=True)
                _SHARED_PYTKET_BRIDGES[key] = self._pytket_bridge
                log('[OK] pytket_dqc kernel ready.')
        return self._pytket_bridge
    MQT_ALIASES = {'Amplitude Estimation (AE)': 'ae', 'Deutsch-Jozsa': 'dj', 'Graph State': 'graphstate', 'GHZ State': 'ghz', "Grover's (no ancilla)": 'grover', "Grover's (v-chain)": 'grover', 'Quantum Approximation Optimization Algorithm (QAOA)': 'qaoa', 'Quantum Fourier Transformation (QFT)': 'qft', 'QFT Entangled': 'qftentangled', 'Quantum Neural Network (QNN)': 'qnn', 'Quantum Phase Estimation (QPE) exact': 'qpeexact', 'Quantum Phase Estimation (QPE) inexact': 'qpeinexact', 'Quantum Walk (no ancilla)': 'qwalk', 'Quantum Walk (v-chain)': 'qwalk', 'Random Circuit': 'randomcircuit', 'Efficient SU2 ansatz with Random Parameters': 'vqe_su2', 'Real Amplitudes ansatz with Random Parameters': 'vqe_real_amp', 'Two Local ansatz with Random Parameters': 'vqe_two_local', 'W-State': 'wstate', "Shor's": 'shor'}

    def validate_mqt_requests(self, *, benchmark_names, qubit_count=None, qubit_counts=None, non_scalable_names=None, log=None):
        log = log or _noop_log
        names = list(benchmark_names)
        non_scalable = set(non_scalable_names or [])
        if qubit_counts is not None:
            scalable_sizes = [int(q) for q in qubit_counts]
        elif qubit_count is not None:
            scalable_sizes = [int(qubit_count)]
        else:
            scalable_sizes = [5]
        if any((q < 1 for q in scalable_sizes)):
            raise ValueError('MQT circuit sizes must be positive integers.')
        requests = []
        for display_name in names:
            alias = self.MQT_ALIASES.get(display_name, display_name)
            if display_name in non_scalable:
                continue
            for nq in scalable_sizes:
                requests.append({'display': display_name, 'benchmark': alias, 'nq': int(nq)})
        if not requests:
            return {'rows': [], 'valid': [], 'invalid': [], 'all_valid': True, 'mqt_version': None, 'note': 'No scalable benchmark points require sweep validation.'}
        cache = self.project_root / 'generated_mqt' / 'validation'
        cache.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        result_file = cache / f'validation_{stamp}.json'
        code = f"import json\nfrom pathlib import Path\nfrom importlib.metadata import version, PackageNotFoundError\nfrom mqt.bench import BenchmarkLevel, get_benchmark\n\n_requests = {requests!r}\n_result_file = Path({str(result_file)!r})\ntry:\n    _mqt_version = version('mqt-bench')\nexcept PackageNotFoundError:\n    try:\n        _mqt_version = version('mqt.bench')\n    except Exception:\n        _mqt_version = 'unknown'\nexcept Exception:\n    _mqt_version = 'unknown'\n\nrows = []\nfor req in _requests:\n    try:\n        qc = get_benchmark(\n            benchmark=req['benchmark'],\n            level=BenchmarkLevel.INDEP,\n            circuit_size=int(req['nq']),\n        )\n        rows.append({{\n            'ok': True, **req,\n            'actual_qubits': int(qc.num_qubits),\n            'gates': int(qc.size()),\n            'depth': int(qc.depth()),\n        }})\n    except Exception as exc:\n        rows.append({{\n            'ok': False, **req,\n            'error_type': type(exc).__name__,\n            'error': str(exc),\n        }})\n_result_file.write_text(json.dumps({{'mqt_version': _mqt_version, 'rows': rows}}, indent=2), encoding='utf-8')\n"
        bridge = self._bridge(log)
        bridge.execute(code, show_output=False, timeout=3600)
        if not result_file.exists():
            raise RuntimeError('MQT compatibility validation did not produce a result file.')
        payload = json.loads(result_file.read_text(encoding='utf-8'))
        rows = list(payload.get('rows') or [])
        valid = [r for r in rows if r.get('ok')]
        invalid = [r for r in rows if not r.get('ok')]
        return {'rows': rows, 'valid': valid, 'invalid': invalid, 'all_valid': not invalid, 'mqt_version': payload.get('mqt_version'), 'result_file': str(result_file)}

    def generate_mqt_qasm(self, *, benchmark_names, qubit_count=None, qubit_counts=None, non_scalable_names=None, log=None):
        log = log or _noop_log
        cache = self.project_root / 'generated_mqt'
        cache.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        out_dir = cache / stamp
        out_dir.mkdir(parents=True, exist_ok=True)
        result_file = out_dir / 'generation_result.json'
        names = list(benchmark_names)
        non_scalable = set(non_scalable_names or [])
        if qubit_counts is not None:
            scalable_sizes = sorted({int(q) for q in qubit_counts})
        elif qubit_count is not None:
            scalable_sizes = [int(qubit_count)]
        else:
            scalable_sizes = [5]
        if any((q < 1 for q in scalable_sizes)):
            raise ValueError('MQT scalable-circuit sizes must be positive integers.')
        requests = []
        for display_name in names:
            alias = self.MQT_ALIASES.get(display_name, display_name)
            if display_name in non_scalable:
                requests.append({'display': display_name, 'benchmark': alias, 'nq': None})
            else:
                for nq in scalable_sizes:
                    requests.append({'display': display_name, 'benchmark': alias, 'nq': int(nq)})
        if not requests:
            raise ValueError('Select at least one MQT benchmark.')
        if len(scalable_sizes) > 1:
            log(f'[INFO] MQT batch profile: target-independent (Qiskit); sizes={scalable_sizes[0]}..{scalable_sizes[-1]} ({len(scalable_sizes)} point(s)).')
        else:
            log('[INFO] MQT profile: target-independent (Qiskit); one circuit per selected benchmark.')
        code = f"""import json, re\nfrom pathlib import Path\nfrom mqt.bench import BenchmarkLevel, get_benchmark\nfrom qiskit import qasm2\nfrom pytket.qasm import circuit_from_qasm\nfrom pytket.circuit.display import render_circuit_as_html\n\n_requests = {requests!r}\n_out = Path({str(out_dir)!r})\n_result_file = Path({str(result_file)!r})\nrows = []\nfor req in _requests:\n    try:\n        nq = req['nq']\n        kwargs = {{\n            'benchmark': req['benchmark'],\n            'level': BenchmarkLevel.INDEP,\n        }}\n        if nq is not None:\n            kwargs['circuit_size'] = int(nq)\n        qc = get_benchmark(**kwargs)\n        safe = re.sub(r'[^A-Za-z0-9._-]+', '_', req['benchmark']).strip('_')\n        suffix = f"_q{{nq}}" if nq is not None else ""\n        path = _out / f"{{safe}}{{suffix}}.qasm"\n        qasm2.dump(qc, path)\n\n        # Keep the Qiskit text drawing as a lightweight diagnostic artifact,\n        # but use the SAME pytket HTML renderer as the research notebook for\n        # the authoritative visual representation.\n        text_path = path.with_suffix('.circuit.txt')\n        text_path.write_text(str(qc.draw(output='text', fold=120)), encoding='utf-8')\n\n        pytket_html_path = path.with_suffix('.pytket.html')\n        pytket_html_error = None\n        try:\n            try:\n                tk_circ = circuit_from_qasm(str(path), maxwidth=max(128, int(qc.num_qubits) * 4))\n            except TypeError:\n                tk_circ = circuit_from_qasm(str(path))\n            try:\n                html = render_circuit_as_html(tk_circ, jupyter=False)\n            except TypeError:\n                html = render_circuit_as_html(tk_circ)\n            if isinstance(html, str) and html.strip():\n                pytket_html_path.write_text(html, encoding='utf-8')\n            else:\n                pytket_html_error = 'pytket returned an empty HTML representation'\n                pytket_html_path = None\n        except Exception as draw_exc:\n            pytket_html_error = f"{{type(draw_exc).__name__}}: {{draw_exc}}"\n            pytket_html_path = None\n\n        rows.append({{\n            'ok': True, **req, 'path': str(path),\n            'qubits': int(qc.num_qubits), 'gates': int(qc.size()), 'depth': int(qc.depth()),\n            'text_drawing_path': str(text_path),\n            'pytket_html_path': str(pytket_html_path) if pytket_html_path is not None else None,\n            'pytket_html_error': pytket_html_error,\n        }})\n    except Exception as exc:\n        rows.append({{'ok': False, **req, 'error': f"{{type(exc).__name__}}: {{exc}}"}})\n_result_file.write_text(json.dumps(rows, indent=2), encoding='utf-8')\n"""
        bridge = self._bridge(log)
        bridge.execute(code, show_output=False, timeout=3600)
        if not result_file.exists():
            raise RuntimeError('MQT generation did not produce a result file.')
        rows = json.loads(result_file.read_text(encoding='utf-8'))
        try:
            from src.circuit_visuals import snapshot_pytket_html
            for r in rows:
                if not r.get('ok') or not r.get('pytket_html_path'):
                    continue
                html_path = Path(r['pytket_html_path'])
                snap_path = html_path.with_suffix('.renderer.png')
                snap, snap_error = snapshot_pytket_html(html_path, snap_path)
                r['pytket_snapshot_path'] = str(snap) if snap else None
                r['pytket_snapshot_error'] = snap_error
        except Exception as exc:
            log(f'[WARN] Exact pytket inline snapshot unavailable: {type(exc).__name__}: {exc}')
        result_file.write_text(json.dumps(rows, indent=2), encoding='utf-8')
        ok = [r for r in rows if r.get('ok')]
        for r in rows:
            if r.get('ok'):
                size_text = f" q={r.get('nq')}" if r.get('nq') is not None else ' (fixed size)'
                log(f"[OK] {r['display']}{size_text} → {Path(r['path']).name}")
                if r.get('pytket_snapshot_path'):
                    log('[OK] Exact pytket notebook-style circuit representation ready.')
                elif r.get('pytket_html_path'):
                    log('[WARN] Exact pytket HTML saved; inline snapshot unavailable, using native fallback.')
            else:
                size_text = f" q={r.get('nq')}" if r.get('nq') is not None else ' (fixed size)'
                log(f"[ERR] {r['display']}{size_text}: {r.get('error')}")
        if not ok:
            raise RuntimeError('No MQT circuits were generated. See the MQT log for per-benchmark errors.')
        return {'rows': rows, 'successful': ok, 'output_dir': str(out_dir)}

    def compile(self, *, qasm_text, network_data, circuit_name, distribution_method, seed, qubits_per_qpu, log=None):
        log = log or _noop_log
        qasm_path, network_path = self.save_inputs(qasm_text, network_data, circuit_name, new_run=True)
        run_dir = self.state.run_dir
        assert run_dir is not None
        compile_dir = run_dir / '03_compile'
        meta_path = compile_dir / 'compile_metadata.json'
        bridge_path = compile_dir / 'pytket_qoala_events.json'
        remote_log_path = run_dir / 'logs' / 'compile_remote.log'
        network_mapping_path = compile_dir / 'network_mapping.json'
        log(f'[INFO] Run folder: {run_dir}')
        log('[INFO] Preparing circuit (cleaning + DQCPass) …')
        log(f'[INFO] Distribution method: {distribution_method}; seed={seed}')
        code = f"""import contextlib, io, json, traceback\nfrom pathlib import Path\n\nfrom pytket.qasm import circuit_from_qasm, circuit_to_qasm\nfrom pytket_dqc.utils import DQCPass\nfrom src.circuit_prep import clean_qasm_file\nfrom src.network import build_network_from_gui\nfrom src.distribution import distribute_circuit\nfrom src.bridge_export import export_distributed_circuit_for_qoala\n\n_qasm_path = Path({str(qasm_path)!r})\n_network_path = Path({str(network_path)!r})\n_compile_dir = Path({str(compile_dir)!r})\n_meta_path = Path({str(meta_path)!r})\n_bridge_path = Path({str(bridge_path)!r})\n_remote_log_path = Path({str(remote_log_path)!r})\n_mapping_path = Path({str(network_mapping_path)!r})\n_qppq = int({int(qubits_per_qpu)!r})\n_seed = int({int(seed)!r})\n_method = {distribution_method!r}\n_name = {circuit_name!r}\n\n_compile_dir.mkdir(parents=True, exist_ok=True)\n\ndef _save_json(path, obj):\n    def _d(v):\n        if hasattr(v, 'item'):\n            try: return v.item()\n            except Exception: pass\n        if hasattr(v, 'tolist'):\n            try: return v.tolist()\n            except Exception: pass\n        if isinstance(v, set): return sorted(v, key=str)\n        return str(v)\n    Path(path).write_text(json.dumps(obj, indent=2, default=_d), encoding='utf-8')\n\ndef _save_circuit(circ, stem):\n    base = _compile_dir / stem\n    try:\n        circuit_to_qasm(circ, str(base.with_suffix('.qasm')))\n    except Exception as exc:\n        base.with_suffix('.qasm.error.txt').write_text(str(exc), encoding='utf-8')\n    try:\n        _save_json(base.with_suffix('.json'), circ.to_dict())\n    except Exception as exc:\n        base.with_suffix('.json.error.txt').write_text(str(exc), encoding='utf-8')\n    # Best-effort standalone visual circuit representation.  Different pytket\n    # versions expose slightly different renderer signatures, so this is\n    # deliberately optional and never blocks the scientific pipeline.\n    try:\n        from pytket.circuit.display import render_circuit_as_html\n        try:\n            _html = render_circuit_as_html(circ, jupyter=False)\n        except TypeError:\n            _html = render_circuit_as_html(circ)\n        if isinstance(_html, str) and _html.strip():\n            base.with_suffix('.html').write_text(_html, encoding='utf-8')\n    except Exception as exc:\n        base.with_suffix('.html.error.txt').write_text(str(exc), encoding='utf-8')\n    try:\n        lines = [\n            f"Qubits: {{circ.n_qubits}}",\n            f"Gates: {{circ.n_gates}}",\n            f"Depth: {{circ.depth()}}",\n            "",\n            "Commands:",\n        ]\n        lines.extend(str(cmd) for cmd in circ.get_commands())\n        base.with_suffix('.txt').write_text('\\n'.join(lines), encoding='utf-8')\n    except Exception as exc:\n        base.with_suffix('.txt').write_text(f"Could not serialise command list: {{exc}}", encoding='utf-8')\n\n_buffer = io.StringIO()\ntry:\n    with contextlib.redirect_stdout(_buffer), contextlib.redirect_stderr(_buffer):\n        # Parse original with a wide classical-register limit so MQT circuits >32\n        # qubits work exactly as in the notebooks' compatibility patch.\n        _maxwidth = max(128, _qppq * 64)\n        try:\n            _original = circuit_from_qasm(str(_qasm_path), maxwidth=_maxwidth)\n        except TypeError:\n            _original = circuit_from_qasm(str(_qasm_path))\n        _save_circuit(_original, '01_original')\n\n        _cleaned_path = _compile_dir / '02_cleaned.qasm'\n        clean_qasm_file(_qasm_path, _cleaned_path)\n        try:\n            _cleaned = circuit_from_qasm(str(_cleaned_path), maxwidth=_maxwidth)\n        except TypeError:\n            _cleaned = circuit_from_qasm(str(_cleaned_path))\n        _save_circuit(_cleaned, '02_cleaned')\n\n        _prepared = _cleaned.copy()\n        DQCPass().apply(_prepared)\n        _save_circuit(_prepared, '03_dqc_prepared')\n\n        _graph = json.loads(_network_path.read_text(encoding='utf-8'))\n        _network, _links, _server_qubits, _qpu_map, _network_meta = build_network_from_gui(\n            _graph,\n            qubits_per_qpu=_qppq,\n            print_output=False,\n        )\n        _save_json(_mapping_path, _network_meta)\n\n        if _prepared.n_qubits > sum(len(v) for v in _server_qubits.values()):\n            raise ValueError(\n                f"Circuit needs {{_prepared.n_qubits}} computational qubits but the GUI network "\n                f"provides only {{sum(len(v) for v in _server_qubits.values())}}. "\n                "Increase QPUs or qubits/QPU."\n            )\n\n        _result = distribute_circuit(\n            _prepared.copy(), _network, len(_server_qubits),\n            seed=_seed, name=_name, distribution_method=_method,\n        )\n        if 'error' in _result:\n            raise RuntimeError(f"{{_result.get('error_type')}}: {{_result.get('error')}}")\n\n        _dist = _result['distributed_circuit']\n        _repr = _result['representation_circuit']\n        _save_circuit(_dist, '04_distributed_real')\n        _save_circuit(_repr, '05_ejpp_representation')\n\n        export_distributed_circuit_for_qoala(\n            dist_circ=_dist,\n            qubits_per_qpu=_qppq,\n            filename=str(_bridge_path),\n        )\n\n        # Keep the real objects alive in the persistent kernel for inspection or\n        # subsequent GUI actions without attempting to pickle them across envs.\n        _qnest_original = _original\n        _qnest_cleaned = _cleaned\n        _qnest_prepared = _prepared\n        _qnest_distribution_result = _result\n        _qnest_network = _network\n\n        _primitive_keys = [\n            'name', 'distribution_method', 'n_qubits', 'n_gates_original',\n            'depth_original', 'n_qubits_distributed', 'n_gates_distributed',\n            'depth_distributed_pytket', 'n_qubits_representation',\n            'n_gates_representation', 'distributed_depth', 'ebits',\n            'ebits_builtin', 'ebit_memory', 'source_link_qubits_required',\n            'link_map', 'placement', 'ebit_info',\n        ]\n        _meta = {{k: _result.get(k) for k in _primitive_keys if k in _result}}\n        _meta.update({{\n            'n_qpus': len(_server_qubits),\n            'qubits_per_qpu': _qppq,\n            'dqc_links': _links,\n            'bridge_file': str(_bridge_path),\n            'circuit_artifacts': [\n                '01_original', '02_cleaned', '03_dqc_prepared',\n                '04_distributed_real', '05_ejpp_representation'\n            ],\n        }})\n        _save_json(_meta_path, _meta)\nfinally:\n    _remote_log_path.write_text(_buffer.getvalue(), encoding='utf-8')\n"""
        bridge = self._bridge(log)
        try:
            bridge.execute(code, show_output=False, timeout=3600)
        except Exception:
            log('[ERROR] Compilation/distribution failed in pytket_dqc.')
            if remote_log_path.exists():
                tail = remote_log_path.read_text(encoding='utf-8', errors='replace').splitlines()[-25:]
                for line in tail:
                    log(line)
            raise
        if not meta_path.exists():
            raise RuntimeError('pytket_dqc completed without producing compile_metadata.json')
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        renderer_snapshots = {}
        try:
            from src.circuit_visuals import snapshot_pytket_html
            for stem in meta.get('circuit_artifacts', []):
                base = compile_dir / stem
                html_path = base.with_suffix('.html')
                if not html_path.exists():
                    continue
                snap_path = base.with_suffix('.renderer.png')
                snap, snap_error = snapshot_pytket_html(html_path, snap_path)
                renderer_snapshots[stem] = {'html': str(html_path), 'snapshot': str(snap) if snap else None, 'error': snap_error}
            if renderer_snapshots:
                meta['renderer_snapshots'] = renderer_snapshots
                _write_json(meta_path, meta)
        except Exception as exc:
            log(f'[WARN] Exact pytket inline snapshots could not be prepared: {type(exc).__name__}: {exc}')
        self.state.compile_metadata = meta
        self.state.bridge_file = bridge_path
        self.state.clear_after_compile()
        self._save_compile_tables(meta, compile_dir)
        log(f"[OK] Distribution complete: {meta.get('n_gates_distributed', '—')} gates, {meta.get('ebits_builtin', meta.get('ebits', '—'))} EPR/ebit cost.")
        log('[OK] Original, cleaned, DQC-prepared, distributed, and EJPP representations were saved.')
        return meta

    @staticmethod
    def _save_compile_tables(meta, compile_dir):
        try:
            import pandas as pd
            pd.DataFrame([{'metric': k, 'value': v} for k, v in meta.items() if isinstance(v, (str, int, float, bool)) or v is None]).to_csv(compile_dir / 'compile_summary.csv', index=False)
            ebit_memory = meta.get('ebit_memory') or {}
            if isinstance(ebit_memory, dict):
                pd.DataFrame([{'qpu': qpu, 'ebit_memory_required': value} for qpu, value in ebit_memory.items()]).to_csv(compile_dir / 'ebit_memory.csv', index=False)
            source_links = meta.get('source_link_qubits_required') or {}
            if isinstance(source_links, dict):
                pd.DataFrame([{'qpu': qpu, 'source_link_qubits_required': value} for qpu, value in source_links.items()]).to_csv(compile_dir / 'source_link_resources.csv', index=False)
        except Exception:
            pass

    def schedule(self, *, single_qubit_time_ns, two_qubit_time_ns, starting_process_time_ns, ending_process_time_ns, strategy='QOALA', log=None):
        log = log or _noop_log
        run_dir = self.state.run_dir
        bridge_file = self.state.bridge_file
        if run_dir is None or bridge_file is None or (not bridge_file.exists()):
            raise RuntimeError('Compile the circuit first; no pytket→Qoala bridge file is available.')
        schedule_dir = run_dir / '04_schedule'
        schedule_dir.mkdir(parents=True, exist_ok=True)
        log('[INFO] Starting isolated Qoala/NetSquid scheduler process …')
        worker_script = self.project_root / 'src' / 'schedule_worker.py'
        result_file = schedule_dir / 'qoala_result.json'
        if result_file.exists():
            result_file.unlink()
        cmd = [sys.executable, str(worker_script), '--bridge-file', str(bridge_file), '--result-file', str(result_file), '--single-qubit-time', str(float(single_qubit_time_ns)), '--two-qubit-time', str(float(two_qubit_time_ns)), '--starting-process-time', str(float(starting_process_time_ns)), '--ending-process-time', str(float(ending_process_time_ns)), '--strategy', str(strategy)]
        proc = subprocess.run(cmd, cwd=str(self.project_root), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
        worker_output = proc.stdout or ''
        (run_dir / 'logs' / 'schedule.log').write_text(worker_output, encoding='utf-8')
        for line in worker_output.splitlines():
            if line.strip():
                log(line)
        if proc.returncode != 0:
            tail = '\n'.join(worker_output.splitlines()[-20:])
            raise RuntimeError('Qoala/NetSquid scheduling failed in the isolated process.' + (f'\n\n{tail}' if tail else ''))
        if not result_file.exists():
            raise RuntimeError('Qoala/NetSquid worker finished without producing qoala_result.json.')
        result = json.loads(result_file.read_text(encoding='utf-8'))
        from src.quantum_gantt_qoalan import draw_qoala_gantt
        from src.quantum_gantt_qoala_timedn import draw_qoala_gantt_timed
        from src.request_table import build_qoala_request_table
        timed_path = draw_qoala_gantt_timed(result, output=str(schedule_dir / 'qoala_timed.html'), show=False, title='QNEST — Qoala execution schedule (timed)', time_unit='µs')
        layer_path = draw_qoala_gantt(result, output=str(schedule_dir / 'qoala_schedule.html'), show=False, title='QNEST — Qoala execution schedule')
        request_table = build_qoala_request_table(result)
        gantt_previews = {}
        try:
            from src.schedule_visuals import snapshot_schedule_html
            for key, html_path in (('timed', timed_path), ('layer', layer_path)):
                preview_path = schedule_dir / f'qoala_{key}.preview.png'
                snap, snap_error = snapshot_schedule_html(html_path, preview_path)
                gantt_previews[key] = {'html': str(html_path), 'preview': str(snap) if snap else None, 'error': snap_error}
                if snap_error:
                    log(f'[WARN] {key.title()} Gantt inline preview: {snap_error}')
        except Exception as exc:
            log(f'[WARN] Gantt inline previews could not be prepared: {type(exc).__name__}: {exc}')
        result['gantt_previews'] = gantt_previews
        self.state.qoala_result = result
        self.state.request_table = request_table
        self.state.clear_after_schedule()
        schedule = result.get('schedule', [])
        _write_json(schedule_dir / 'schedule.json', schedule)
        _write_json(schedule_dir / 'schedule_summary.json', {'strategy': result.get('strategy'), 'total_execution_time_ns': result.get('total_execution_time_ns'), 'n_original_events': result.get('n_original_events'), 'used_qpus': result.get('used_qpus'), 'single_qubit_time_ns': float(single_qubit_time_ns), 'two_qubit_time_ns': float(two_qubit_time_ns), 'starting_process_time_ns': float(starting_process_time_ns), 'ending_process_time_ns': float(ending_process_time_ns), 'timed_gantt': str(timed_path), 'layer_gantt': str(layer_path), 'gantt_previews': gantt_previews, 'execution_mode': 'isolated_child_process', 'html_security': 'local QNEST-generated HTML; no external font/CDN dependency'})
        try:
            request_table.to_csv(schedule_dir / 'request_table_raw_ns.csv', index=False)
            request_table.to_html(schedule_dir / 'request_table_raw_ns.html', index=False, border=0)
            request_table_us = _presentation_table_us(request_table)
            request_table_us.to_csv(schedule_dir / 'request_table.csv', index=False)
            request_table_us.to_html(schedule_dir / 'request_table.html', index=False, border=0)
        except Exception:
            pass
        log(f"[OK] Qoala schedule complete: {float(result.get('total_execution_time_ns', 0)) / 1000.0:,.3f} µs, {len(result.get('used_qpus', []))} used QPU(s).")
        log(f'[OK] Request table: {len(request_table)} row(s). Interactive Gantt files saved.')
        return result

    def run_protocols(self, *, p_succ, time_per_trial_ns, t_cut_ns, delta_t_c_ns, F_I, F_T, alpha, seed, deadline_equal_is_blocked=True, background_start_ns=0.0, p_succ_ap=None, hedge_mode='race', monte_carlo_runs=1, afa_fidelity=None, progress=None, log=None):
        log = log or _noop_log
        run_dir = self.state.run_dir
        qoala_result = self.state.qoala_result
        if run_dir is None or qoala_result is None:
            raise RuntimeError('Generate the Qoala schedule first.')
        n_runs = int(monte_carlo_runs)
        if n_runs < 1:
            raise ValueError('monte_carlo_runs must be at least 1.')
        run_out = run_dir / '05_run'
        log(f'[INFO] Running coupled AFA-QSP and HAMFA-QSP Monte Carlo simulations: {n_runs} run(s) …')
        from src.afa_qsp import simulate_afa_qsp
        from src.hamfa_qsp import simulate_hamfa_qsp, validate_hamfa_run
        import pandas as pd
        import numpy as np
        afa_tables = []
        hamfa_tables = []
        afa_exact_tables = []
        hamfa_exact_tables = []
        afa_summaries = []
        hamfa_summaries = []
        validations = []
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            for rep in range(n_runs):
                rep_seed = int(seed) + rep
                afa_table, afa_summary = simulate_afa_qsp(qoala_result=qoala_result, p_succ=float(p_succ), time_per_trial_ns=float(time_per_trial_ns), seed=rep_seed)
                afa_exact = afa_table.reindex(columns=NOTEBOOK_AFA_TABLE_COLUMNS).copy()
                afa_summary = dict(afa_summary)
                n_afa = max(1, int(afa_summary.get('total_requests', len(afa_table))))
                afa_summary['B_blocking'] = float(afa_summary.get('total_blocked_requests', 0) / n_afa)
                if 'Time duration until success [ns]' in afa_table.columns and len(afa_table):
                    afa_summary['mean_completion_latency_ns'] = float(afa_table['Time duration until success [ns]'].mean())
                    afa_summary['p95_completion_latency_ns'] = float(afa_table['Time duration until success [ns]'].quantile(0.95))
                if afa_fidelity is not None:
                    fid = float(afa_fidelity)
                    afa_table = afa_table.copy()
                    afa_table['Delivered fidelity F_del'] = fid
                    afa_summary['mean_delivered_fidelity'] = fid
                hamfa_table, hamfa_summary = simulate_hamfa_qsp(qoala_result=qoala_result, p_succ=float(p_succ), time_per_trial_ns=float(time_per_trial_ns), t_cut_ns=float(t_cut_ns), delta_t_c_ns=float(delta_t_c_ns), F_I=float(F_I), F_T=float(F_T), alpha=float(alpha), seed=rep_seed, deadline_equal_is_blocked=bool(deadline_equal_is_blocked), background_start_ns=float(background_start_ns), verbose=False, p_succ_ap=None if p_succ_ap is None else float(p_succ_ap), hedge_mode=hedge_mode)
                validation = validate_hamfa_run(hamfa_table, hamfa_summary, F_T=float(F_T))
                hamfa_exact = hamfa_table.reindex(columns=NOTEBOOK_HAMFA_TABLE_COLUMNS).copy()
                afa_exact_tables.append(afa_exact)
                hamfa_exact_tables.append(hamfa_exact)
                afa_table = afa_table.copy()
                hamfa_table = hamfa_table.copy()
                afa_table.insert(0, 'Monte Carlo run', rep + 1)
                hamfa_table.insert(0, 'Monte Carlo run', rep + 1)
                afa_table.insert(1, 'Simulation seed', rep_seed)
                hamfa_table.insert(1, 'Simulation seed', rep_seed)
                afa_tables.append(afa_table)
                hamfa_tables.append(hamfa_table)
                afa_summaries.append(dict(afa_summary, simulation_seed=rep_seed))
                hamfa_summaries.append(dict(hamfa_summary, simulation_seed=rep_seed))
                validations.append(validation)
                if progress is not None:
                    try:
                        progress(rep + 1, n_runs)
                    except Exception:
                        pass

        def aggregate(summaries):
            keys = set().union(*(x.keys() for x in summaries))
            out = {'simulation_runs': n_runs, 'seed_first': int(seed), 'seed_last': int(seed) + n_runs - 1}
            for key in sorted(keys):
                vals = []
                for item in summaries:
                    value = item.get(key)
                    if isinstance(value, (int, float, np.integer, np.floating)) and (not isinstance(value, bool)):
                        try:
                            fv = float(value)
                            if np.isfinite(fv):
                                vals.append(fv)
                        except Exception:
                            pass
                if vals:
                    arr = np.asarray(vals, dtype=float)
                    mean = float(arr.mean())
                    std = float(arr.std(ddof=1)) if len(arr) > 1 else 0.0
                    if abs(std) < 1e-15:
                        std = 0.0
                    out[key] = mean
                    out[key + '_std'] = std
                elif summaries:
                    out[key] = summaries[0].get(key)
            return out
        afa_table = pd.concat(afa_tables, ignore_index=True) if afa_tables else pd.DataFrame()
        hamfa_table = pd.concat(hamfa_tables, ignore_index=True) if hamfa_tables else pd.DataFrame()
        afa_summary = aggregate(afa_summaries)
        hamfa_summary = aggregate(hamfa_summaries)
        validation = {}
        for key in set().union(*(v.keys() for v in validations)) if validations else set():
            validation[key] = all((bool(v.get(key, False)) for v in validations))
        (run_dir / 'logs' / 'protocols.log').write_text(buffer.getvalue(), encoding='utf-8')
        self.state.afa_table = afa_table
        self.state.afa_summary = afa_summary
        self.state.afa_run_summaries = afa_summaries
        self.state.afa_exact_run_tables = afa_exact_tables
        self.state.hamfa_table = hamfa_table
        self.state.hamfa_summary = hamfa_summary
        self.state.hamfa_run_summaries = hamfa_summaries
        self.state.hamfa_exact_run_tables = hamfa_exact_tables
        self.state.validation = validation
        exact_root = run_out / 'result_tables'
        exact_root.mkdir(parents=True, exist_ok=True)
        exact_manifest = []
        for rep, (afa_exact, hamfa_exact) in enumerate(zip(afa_exact_tables, hamfa_exact_tables), 1):
            rep_dir = exact_root / f'run_{rep:03d}'
            rep_dir.mkdir(parents=True, exist_ok=True)
            afa_csv = rep_dir / 'afa_qsp_results.csv'
            hamfa_csv = rep_dir / 'hamfa_qsp_results.csv'
            afa_html = rep_dir / 'afa_qsp_results.html'
            hamfa_html = rep_dir / 'hamfa_qsp_results.html'
            afa_exact.to_csv(afa_csv, index=False)
            hamfa_exact.to_csv(hamfa_csv, index=False)
            try:
                _write_clean_result_html(afa_html, afa_exact, 'AFA-QSP Monte Carlo results')
                _write_clean_result_html(hamfa_html, hamfa_exact, 'HAMFA-QSP Monte Carlo results')
            except Exception:
                pass
            exact_manifest.append({'monte_carlo_run': rep, 'simulation_seed': int(seed) + rep - 1, 'afa_csv': str(afa_csv.relative_to(run_dir)), 'hamfa_csv': str(hamfa_csv.relative_to(run_dir)), 'afa_columns': list(NOTEBOOK_AFA_TABLE_COLUMNS), 'hamfa_columns': list(NOTEBOOK_HAMFA_TABLE_COLUMNS)})
        _write_json(exact_root / 'manifest.json', {'format': 'clean researcher-facing Monte Carlo result tables', 'units': 'raw notebook units; time columns remain nanoseconds [ns]', 'runs': exact_manifest})
        afa_table_us = _presentation_table_us(afa_table)
        hamfa_table_us = _presentation_table_us(hamfa_table)
        pd.DataFrame(afa_summaries).to_csv(run_out / 'afa_mc_runs_raw_ns.csv', index=False)
        pd.DataFrame(hamfa_summaries).to_csv(run_out / 'hamfa_mc_runs_raw_ns.csv', index=False)
        _presentation_table_us(pd.DataFrame(afa_summaries)).to_csv(run_out / 'afa_mc_runs.csv', index=False)
        _presentation_table_us(pd.DataFrame(hamfa_summaries)).to_csv(run_out / 'hamfa_mc_runs.csv', index=False)
        _write_json(run_out / 'afa_summary.json', afa_summary)
        _write_json(run_out / 'hamfa_summary.json', hamfa_summary)
        _write_json(run_out / 'hamfa_validation.json', validation)
        _write_json(run_out / 'run_parameters.json', {'physical_inputs_source': 'Network panel', 'p_succ': p_succ, 'p_succ_ap': p_succ_ap, 'time_per_trial_ns': time_per_trial_ns, 'afa_fidelity': afa_fidelity, 't_cut_ns': t_cut_ns, 'delta_t_c_ns': delta_t_c_ns, 'F_I': F_I, 'F_T': F_T, 'alpha': alpha, 'seed': seed, 'monte_carlo_runs': n_runs, 'deadline_equal_is_blocked': deadline_equal_is_blocked, 'background_start_ns': background_start_ns, 'hedge_mode': hedge_mode})
        comparison = self._comparison_table(afa_summary, hamfa_summary)
        comparison.to_csv(run_out / 'protocol_comparison.csv', index=False)
        try:
            comparison.to_html(run_out / 'protocol_comparison.html', index=False, border=0)
        except Exception:
            pass
        plot_paths = self._make_protocol_plots(afa_table, afa_summary, hamfa_table, hamfa_summary, run_out)
        log(f"[OK] AFA-QSP mean blocked requests: {afa_summary.get('total_blocked_requests', 0):.3g} over {n_runs} Monte Carlo run(s).")
        log(f"[OK] HAMFA-QSP mean blocked requests: {hamfa_summary.get('total_blocked_requests', 0):.3g} over {n_runs} Monte Carlo run(s).")
        log(f'[OK] Saved Monte Carlo request tables, summaries, validation, and {len(plot_paths)} plot file(s).')
        return {'afa_table': afa_table, 'afa_summary': afa_summary, 'hamfa_table': hamfa_table, 'hamfa_summary': hamfa_summary, 'validation': validation, 'comparison': comparison, 'plots': plot_paths, 'monte_carlo_runs': n_runs, 'afa_run_summaries': afa_summaries, 'hamfa_run_summaries': hamfa_summaries, 'afa_exact_run_tables': afa_exact_tables, 'hamfa_exact_run_tables': hamfa_exact_tables}

    @staticmethod
    def _comparison_table(afa, hamfa):
        import pandas as pd
        excluded = {'P_on', 'total_photon_budget', 'photon_budget_per_request', 'total_photonic_trials_during_requests', 'total_direct_AP_trials', 'background_trials', 'critical_path_trials_per_request', 'min_delivered_fidelity', 'mean_effective_fidelity'}
        preferred = ['total_requests', 'total_blocked_requests', 'B_blocking', 'total_punishment_time_ns', 'mean_completion_latency_ns', 'p95_completion_latency_ns', 'makespan_ns', 'mean_delivered_fidelity', 'all_photonic_used', 'memory_assisted_successful', 'memory_assisted_not_successful', 'passed_t_cut']
        keys = []
        for key in preferred + sorted(set(afa) | set(hamfa)):
            if key in excluded or key.endswith('_std'):
                continue
            if key not in keys and (isinstance(afa.get(key), (int, float, bool)) or isinstance(hamfa.get(key), (int, float, bool))):
                keys.append(key)
        aggregate_view = bool((afa.get('simulation_runs', 1) or 1) > 1 or (hamfa.get('simulation_runs', 1) or 1) > 1)
        count_keys = {'total_requests', 'total_blocked_requests', 'case_A_requests', 'case_B_requests', 'case_C_requests', 'case_E_requests', 'memory_assisted_successful', 'memory_assisted_not_successful', 'passed_t_cut', 'all_photonic_used', 'stale_refreshed', 'swap_failures'}
        rows = []
        for key in keys:
            av = afa.get(key, math.nan)
            hv = hamfa.get(key, math.nan)
            if not aggregate_view and key in count_keys:

                def _count_text(v):
                    if isinstance(v, (int, float)) and math.isfinite(float(v)):
                        return str(int(round(float(v))))
                    return '—'
                av, hv = (_count_text(av), _count_text(hv))
            rows.append({'metric': key, 'AFA-QSP': av, 'HAMFA-QSP': hv})
        return pd.DataFrame(rows)

    @staticmethod
    def _make_protocol_plots(afa_table, afa, hamfa_table, hamfa, output_dir):
        paths = []
        try:
            import matplotlib
            matplotlib.use('Agg', force=True)
            import matplotlib.pyplot as plt
            import numpy as np
            import pandas as pd
        except Exception:
            return paths
        plot_dir = output_dir / 'plots'
        plot_dir.mkdir(parents=True, exist_ok=True)

        def save(fig, stem):
            for ext in ('png', 'pdf'):
                p = plot_dir / f'{stem}.{ext}'
                fig.savefig(p, dpi=220, bbox_inches='tight')
                paths.append(p)
            plt.close(fig)
        fig, ax = plt.subplots(figsize=(7.0, 4.3))
        vals = np.asarray([float(afa.get('total_punishment_time_ns', 0.0)) / 1000.0, float(hamfa.get('total_punishment_time_ns', 0.0)) / 1000.0])
        errs = np.asarray([float(afa.get('total_punishment_time_ns_std', 0.0)) / 1000.0, float(hamfa.get('total_punishment_time_ns_std', 0.0)) / 1000.0])
        ax.bar(['AFA-QSP', 'HAMFA-QSP'], vals, yerr=errs, capsize=5)
        ax.set_ylabel('Total punishment time (µs)')
        ax.set_title('Protocol delay comparison (mean ± 1 SD)')
        ax.grid(axis='y', alpha=0.2)
        save(fig, '01_punishment_time')
        fig, ax = plt.subplots(figsize=(7.0, 4.3))
        vals = np.asarray([float(afa.get('total_blocked_requests', 0)), float(hamfa.get('total_blocked_requests', 0))])
        errs = np.asarray([float(afa.get('total_blocked_requests_std', 0)), float(hamfa.get('total_blocked_requests_std', 0))])
        ax.bar(['AFA-QSP', 'HAMFA-QSP'], vals, yerr=errs, capsize=5)
        ax.set_ylabel('Blocked requests')
        ax.set_title('Blocked entanglement requests (mean ± 1 SD)')
        ax.grid(axis='y', alpha=0.2)
        save(fig, '02_blocked_requests')

        def request_stats(table, column):
            if column not in getattr(table, 'columns', []) or table.empty:
                return None
            if 'Request k' in table.columns:
                g = table.groupby('Request k', sort=True)[column]
                mean = g.mean()
                std = g.std(ddof=1).fillna(0.0)
                return (np.arange(1, len(mean) + 1), mean.to_numpy(dtype=float), std.to_numpy(dtype=float))
            arr = table[column].to_numpy(dtype=float)
            return (np.arange(1, len(arr) + 1), arr, np.zeros_like(arr))
        latency_col = 'Time duration until success [ns]'
        ast = request_stats(afa_table, latency_col)
        hst = request_stats(hamfa_table, latency_col)
        if ast or hst:
            fig, ax = plt.subplots(figsize=(8.0, 4.5))
            if ast:
                x, m, sd = ast
                ax.errorbar(x, m / 1000.0, yerr=sd / 1000.0, marker='o', markersize=3, capsize=2, label='AFA-QSP')
            if hst:
                x, m, sd = hst
                ax.errorbar(x, m / 1000.0, yerr=sd / 1000.0, marker='s', markersize=3, capsize=2, label='HAMFA-QSP')
            ax.set_xlabel('Request index')
            ax.set_ylabel('Completion latency (µs)')
            ax.set_title('Request completion latency (mean ± 1 SD)')
            ax.legend(frameon=False)
            ax.grid(axis='y', alpha=0.2)
            save(fig, '03_request_latency')
        fidelity_col = 'Delivered fidelity F_del'
        ast = request_stats(afa_table, fidelity_col)
        hst = request_stats(hamfa_table, fidelity_col)
        if ast or hst:
            fig, ax = plt.subplots(figsize=(8.0, 4.5))
            if ast:
                x, m, sd = ast
                ax.errorbar(x, m, yerr=sd, marker='o', markersize=3, capsize=2, label='AFA-QSP')
            if hst:
                x, m, sd = hst
                ax.errorbar(x, m, yerr=sd, marker='s', markersize=3, capsize=2, label='HAMFA-QSP')
            ax.set_xlabel('Request index')
            ax.set_ylabel('Mean delivered fidelity')
            ax.set_ylim(0.0, 1.02)
            ax.set_title('Delivered fidelity (mean ± 1 SD)')
            ax.legend(frameon=False)
            ax.grid(axis='y', alpha=0.2)
            save(fig, '04_delivered_fidelity')
        labels = ['Memory assisted', 'All-photonic', 'Blocked']
        vals = [float(hamfa.get('memory_assisted_successful', 0)), float(hamfa.get('all_photonic_used', 0)), float(hamfa.get('total_blocked_requests', 0))]
        errs = [float(hamfa.get('memory_assisted_successful_std', 0)), float(hamfa.get('all_photonic_used_std', 0)), float(hamfa.get('total_blocked_requests_std', 0))]
        fig, ax = plt.subplots(figsize=(7.2, 4.3))
        ax.bar(labels, vals, yerr=errs, capsize=5)
        ax.set_ylabel('Requests')
        ax.set_title('HAMFA-QSP outcome mix (mean ± 1 SD)')
        ax.grid(axis='y', alpha=0.2)
        save(fig, '05_hamfa_outcomes')
        return paths

    def write_manifest(self):
        run_dir = self.state.run_dir
        if run_dir is None:
            return None
        files = [{'path': str(p.relative_to(run_dir)), 'bytes': p.stat().st_size, 'suffix': p.suffix.lower()} for p in self.artifact_files() if p.name != 'manifest.json']
        return _write_json(run_dir / 'manifest.json', {'generated': datetime.now().isoformat(timespec='seconds'), 'circuit_name': self.state.circuit_name, 'files': files})