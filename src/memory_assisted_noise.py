import numpy as np
import pandas as pd
from src.all_photonic_noise import F_cond, validate_model
_REQUIRED_HAMFA_COLUMNS = {'Request k', 'Time before deadline [ns]', 'Effective pair age [ns]'}

def memory_pair_fidelity(F_I, total_memory_age_ns, delta_t_c_ns):
    F_I = float(F_I)
    delta_t_c_ns = float(delta_t_c_ns)
    if not 0.0 < F_I <= 1.0:
        raise ValueError('F_I must satisfy 0 < F_I <= 1.')
    if delta_t_c_ns <= 0.0:
        raise ValueError('delta_t_c_ns must be greater than zero.')
    age = np.maximum(np.asarray(total_memory_age_ns, dtype=float), 0.0)
    fidelity = F_I * np.exp(-age / delta_t_c_ns)
    return np.clip(fidelity, 0.0, 1.0)

def _memory_mask(table):
    if 'Memory-assisted successful' in table.columns:
        return table['Memory-assisted successful'].astype(str).eq('Yes').to_numpy()
    if 'Path Used' in table.columns:
        return table['Path Used'].astype(str).str.startswith('Memory').to_numpy()
    raise KeyError("HAMFA table must contain either 'Memory-assisted successful' or 'Path Used'.")

def request_fidelity_from_hamfa_table(hamfa_table, all_photonic_params=None, *, F_I, delta_t_c_ns):
    missing = _REQUIRED_HAMFA_COLUMNS - set(hamfa_table.columns)
    if missing:
        raise KeyError(f'HAMFA table is missing required column(s): {sorted(missing)}')
    p = validate_model(all_photonic_params)
    out = hamfa_table.copy()
    if out.empty:
        out['Gate-use idle [ns]'] = pd.Series(dtype=float)
        out['Noise-model path'] = pd.Series(dtype=str)
        out['EPR fidelity at gate'] = pd.Series(dtype=float)
        return (out, {'total_requests': 0, 'all_photonic_count': 0, 'memory_assisted_count': 0, 'all_photonic_average_epr_fidelity': np.nan, 'memory_assisted_average_epr_fidelity': np.nan, 'average_epr_fidelity': np.nan, 'sum_epr_fidelity': 0.0})
    gate_idle_ns = np.maximum(out['Time before deadline [ns]'].to_numpy(dtype=float), 0.0)
    mem_mask = _memory_mask(out)
    ap_mask = ~mem_mask
    request_params = dict(p)
    request_params['T_idle_A'] = float(p['T_idle_A']) + gate_idle_ns * 1e-09
    request_params['T_idle_B'] = float(p['T_idle_B']) + gate_idle_ns * 1e-09
    ap_fidelity_all_rows = np.asarray(F_cond(request_params), dtype=float)
    if ap_fidelity_all_rows.ndim == 0:
        ap_fidelity_all_rows = np.full(len(out), float(ap_fidelity_all_rows))
    effective_pair_age_ns = np.nan_to_num(out['Effective pair age [ns]'].to_numpy(dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    total_memory_age_ns = np.maximum(effective_pair_age_ns, 0.0) + gate_idle_ns
    mem_fidelity_all_rows = memory_pair_fidelity(F_I=F_I, total_memory_age_ns=total_memory_age_ns, delta_t_c_ns=delta_t_c_ns)
    fidelities = np.where(mem_mask, mem_fidelity_all_rows, ap_fidelity_all_rows)
    out['Gate-use idle [ns]'] = gate_idle_ns
    out['Noise-model path'] = np.where(mem_mask, 'Memory-assisted', 'All-photonic')
    out['Total memory decoherence age [ns]'] = np.where(mem_mask, total_memory_age_ns, np.nan)
    out['EPR fidelity at gate'] = fidelities
    n_total = int(len(out))
    n_ap = int(np.sum(ap_mask))
    n_mem = int(np.sum(mem_mask))
    ap_mean = float(np.mean(fidelities[ap_mask])) if n_ap else np.nan
    mem_mean = float(np.mean(fidelities[mem_mask])) if n_mem else np.nan
    fidelity_sum = float(np.sum(fidelities))
    overall = float(fidelity_sum / n_total)
    weighted_numerator = 0.0
    if n_ap:
        weighted_numerator += n_ap * ap_mean
    if n_mem:
        weighted_numerator += n_mem * mem_mean
    weighted_average = float(weighted_numerator / n_total)
    return (out, {'total_requests': n_total, 'all_photonic_count': n_ap, 'memory_assisted_count': n_mem, 'all_photonic_average_epr_fidelity': ap_mean, 'memory_assisted_average_epr_fidelity': mem_mean, 'sum_epr_fidelity': fidelity_sum, 'average_epr_fidelity': overall, 'weighted_average_check': weighted_average, 'mean_gate_use_idle_ns': float(np.mean(gate_idle_ns))})