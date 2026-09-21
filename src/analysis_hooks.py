import ast
import importlib
import importlib.util
import sys
from src.config import COMPILER
_REQUIRED = ('analyse_ebits', 'extract_placement', 'compute_circuit_depth')

def _load_from_compiler():
    if not COMPILER.exists():
        return None
    for path in sorted(COMPILER.rglob('*.py')):
        if path.name.startswith('_'):
            continue
        try:
            tree = ast.parse(path.read_text(errors='ignore'))
        except Exception:
            continue
        defined = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        if not set(_REQUIRED).issubset(defined):
            continue
        module_name = f'_switchsim_analysis_{path.stem}'
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(module_name, None)
            continue
        return module
    return None

def _fallback_analyse_ebits(dist_circ):
    from pytket_dqc.utils.circuit_analysis import ebit_cost
    return {'count': int(ebit_cost(dist_circ)), 'source': 'pytket_dqc.ebit_cost'}

def _fallback_extract_placement(dist, n_qubits):
    placement = getattr(dist, 'placement', None)
    if callable(placement):
        try:
            placement = placement()
        except TypeError:
            placement = None
    if placement is None:
        return {}
    return placement

def _fallback_compute_circuit_depth(dist_circ, n_ebits):
    return int(dist_circ.depth())
_FALLBACKS = {'analyse_ebits': _fallback_analyse_ebits, 'extract_placement': _fallback_extract_placement, 'compute_circuit_depth': _fallback_compute_circuit_depth}
_resolved = {}
for _candidate in ('analysis', 'ebit_analysis', 'dqc_analysis', 'circuit_analysis', 'utils'):
    if len(_resolved) == len(_REQUIRED):
        break
    try:
        _module = importlib.import_module(_candidate)
    except Exception:
        continue
    for _name in _REQUIRED:
        if _name not in _resolved and hasattr(_module, _name):
            _resolved[_name] = getattr(_module, _name)
if len(_resolved) != len(_REQUIRED):
    _module = _load_from_compiler()
    if _module is not None:
        for _name in _REQUIRED:
            if hasattr(_module, _name):
                _resolved[_name] = getattr(_module, _name)
analyse_ebits = _resolved.get('analyse_ebits', _FALLBACKS['analyse_ebits'])
extract_placement = _resolved.get('extract_placement', _FALLBACKS['extract_placement'])
compute_circuit_depth = _resolved.get('compute_circuit_depth', _FALLBACKS['compute_circuit_depth'])