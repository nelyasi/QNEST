import numpy as np
import pandas as pd
C_LIGHT = 299792458.0
DEFAULT_ALL_PHOTONIC_PARAMS = {'fabric': 'tree', 'N': 40, 'eta_1': 0.79, 'delta_1': 1e-10, 'eta_c': 0.63, 'delta_c': 1e-10, 'T_conf': 1e-07, 'L_A_km': 0.1, 'L_B_km': 0.1, 'alpha_dB_km': 0.2, 'n_g': 1.47, 'eta_int_A': 0.69, 'eta_int_B': 0.69, 'eta_A': None, 'eta_B': None, 'eta_d': 0.88, 'V': 0.98, 'm': 1, 'P_d': 5e-08, 'eps_sw': 0.0001, 'nbar_1': 0.01, 'T_hrld_A': None, 'T_hrld_B': None, 'T_lo_A': 5.5e-06, 'T_lo_B': 5.5e-06, 'T_idle_A': 0.0, 'T_idle_B': 0.0, 'T1_A': 12000.0, 'T2_A': 2.8, 'T1_B': 12000.0, 'T2_B': 2.8, 'M': 8, 'M_BSM': 5, 'forest': True, 'xtalk_full_N': True, 'exact_ceil': True, 'target': 'heralded'}
_REQUIRED_AFA_COLUMNS = {'Request k', 'Time before deadline [ns]'}

def _params(params=None, **overrides):
    p = dict(DEFAULT_ALL_PHOTONIC_PARAMS)
    if params is not None:
        unknown = set(params) - set(p)
        if unknown:
            raise KeyError(f'Unknown all-photonic parameter(s): {sorted(unknown)}')
        p.update(dict(params))
    unknown = set(overrides) - set(p)
    if unknown:
        raise KeyError(f'Unknown all-photonic parameter(s): {sorted(unknown)}')
    p.update(overrides)
    return p

def _N_fab(p):
    N = np.asarray(p['N'], dtype=float)
    if p['fabric'] == 'tree' and p['forest']:
        return np.maximum(N / p['M_BSM'], 1.0)
    return N

def eta_sw(params=None, **overrides):
    p = _params(params, **overrides)
    Nf = _N_fab(p)
    if p['fabric'] == 'tree':
        return np.power(p['eta_1'], np.ceil(np.log2(Nf)))
    if p['fabric'] == 'crossbar':
        return np.asarray(p['eta_c'], dtype=float) * np.ones_like(Nf)
    raise ValueError("fabric must be 'tree' or 'crossbar'.")

def delta_sw(params=None, **overrides):
    p = _params(params, **overrides)
    Nf = _N_fab(p)
    if p['fabric'] == 'tree':
        return 2.0 * np.ceil(np.log2(Nf)) * p['delta_1']
    if p['fabric'] == 'crossbar':
        return 2.0 * np.asarray(p['delta_c'], dtype=float) * np.ones_like(Nf)
    raise ValueError("fabric must be 'tree' or 'crossbar'.")

def arm_eta(params=None, **overrides):
    p = _params(params, **overrides)

    def fib(length_km):
        return np.power(10.0, -np.asarray(p['alpha_dB_km'], dtype=float) * np.asarray(length_km, dtype=float) / 10.0)
    eA = p['eta_A'] if p['eta_A'] is not None else p['eta_int_A'] * fib(p['L_A_km'])
    eB = p['eta_B'] if p['eta_B'] is not None else p['eta_int_B'] * fib(p['L_B_km'])
    return (np.asarray(eA, dtype=float), np.asarray(eB, dtype=float))

def a_b(params=None, **overrides):
    p = _params(params, **overrides)
    eA, eB = arm_eta(p)
    e = eta_sw(p)
    return (eA * e, eB * e)

def P_eff_d(params=None, **overrides):
    p = _params(params, **overrides)
    N_xt = np.asarray(p['N'], dtype=float) if p['xtalk_full_N'] else _N_fab(p)
    return np.asarray(p['P_d'], dtype=float) + np.maximum(N_xt - 2.0, 0.0) * p['eps_sw'] * p['nbar_1']

def idle_windows(params=None, **overrides):
    p = _params(params, **overrides)
    vg = C_LIGHT / np.asarray(p['n_g'], dtype=float)
    Tp_A = np.asarray(p['L_A_km'], dtype=float) * 1000.0 / vg
    Tp_B = np.asarray(p['L_B_km'], dtype=float) * 1000.0 / vg
    Th_A = Tp_A if p['T_hrld_A'] is None else np.asarray(p['T_hrld_A'], dtype=float)
    Th_B = Tp_B if p['T_hrld_B'] is None else np.asarray(p['T_hrld_B'], dtype=float)
    d = delta_sw(p)
    return (Tp_A + d + Th_A + p['T_lo_A'] + p['T_idle_A'], Tp_B + d + Th_B + p['T_lo_B'] + p['T_idle_B'])

def gamma_nu(params=None, **overrides):
    p = _params(params, **overrides)
    T_A, T_B = idle_windows(p)
    for label, T1, T2 in (('A', p['T1_A'], p['T2_A']), ('B', p['T1_B'], p['T2_B'])):
        T1 = np.asarray(T1, dtype=float)
        T2 = np.asarray(T2, dtype=float)
        if np.any(T2 > 2 * T1 * (1 + 1e-12)):
            raise ValueError(f'Complete positivity requires T2 <= 2*T1; violated on qubit {label}.')
    return (1.0 - np.exp(-T_A / np.asarray(p['T1_A'], dtype=float)), 1.0 - np.exp(-T_B / np.asarray(p['T1_B'], dtype=float)), np.exp(-T_A / np.asarray(p['T2_A'], dtype=float)), np.exp(-T_B / np.asarray(p['T2_B'], dtype=float)))

def xstate(params=None, **overrides):
    p = _params(params, **overrides)
    a, b = a_b(p)
    x = P_eff_d(p)
    ed = np.asarray(p['eta_d'], dtype=float)
    d0_1 = 0.25 * a * b * ed ** 2
    d0_3 = 0.25 * (-1.0) ** np.asarray(p['m'], dtype=float) * a * b * ed ** 2 * np.asarray(p['V'], dtype=float) ** 2
    d1_1 = 0.5 * (1 - x) * ed * (a + b - 2 * a * b * ed) + x * (1 - a * ed) * (1 - b * ed)
    A0 = x * (1 - x) ** 2 * d1_1
    B0 = (1 - x) ** 4 * d0_1 + x * (1 - x) ** 2 * d1_1
    C0 = (1 - x) ** 4 * d0_3
    return (A0, B0, C0, A0, d0_1, d1_1, x)

def P_succ(params=None, **overrides):
    p = _params(params, **overrides)
    _, _, _, _, d0_1, d1_1, x = xstate(p)
    out = 2 * (1 - x) ** 4 * d0_1 + 4 * x * (1 - x) ** 2 * d1_1
    _validate_probability(out, 'P_succ')
    return out

def P_succ_clean(params=None, **overrides):
    p = _params(params, **overrides)
    eA, eB = arm_eta(p)
    return 0.5 * eA * eB * eta_sw(p) ** 2 * np.asarray(p['eta_d'], dtype=float) ** 2

def F_cond(params=None, **overrides):
    p = _params(params, **overrides)
    A0, B0, C0, _, _, _, _ = xstate(p)
    gA, gB, nA, nB = gamma_nu(p)
    if p['target'] == 'heralded':
        s = (-1.0) ** np.asarray(p['m'], dtype=float)
    elif p['target'] == '+':
        s = 1.0
    elif p['target'] == '-':
        s = -1.0
    else:
        raise ValueError("target must be 'heralded', '+' or '-'.")
    num = B0 * (2 - gA - gB) + A0 * (gA + gB - 2 * gA * gB) + s * 2 * nA * nB * C0
    out = num / (2 * P_succ(p))
    _validate_probability(out, 'F_cond')
    return out

def T_slot(params=None, **overrides):
    p = _params(params, **overrides)
    return np.asarray(p['T_conf'], dtype=float) + delta_sw(p)

def f_attempt(params=None, **overrides):
    p = _params(params, **overrides)
    reps = np.asarray(p['M'], dtype=float) / np.asarray(p['M_BSM'], dtype=float)
    if p['exact_ceil']:
        reps = np.ceil(reps)
    return 1.0 / (reps * T_slot(p))

def R_time(params=None, **overrides):
    p = _params(params, **overrides)
    return P_succ(p) * f_attempt(p)

def _validate_probability(value, name):
    arr = np.asarray(value, dtype=float)
    if np.any(~np.isfinite(arr)):
        raise ValueError(f'{name} contains non-finite values.')
    tol = 1e-10
    if np.any((arr < -tol) | (arr > 1 + tol)):
        lo = float(np.nanmin(arr))
        hi = float(np.nanmax(arr))
        raise ValueError(f'{name} must remain in [0, 1]; observed [{lo:.6g}, {hi:.6g}].')

def validate_model(params=None):
    p = _params(params)
    _validate_probability(P_eff_d(p), 'P_eff_d')
    _validate_probability(P_succ(p), 'P_succ')
    _validate_probability(F_cond(p), 'F_cond')
    return p

def request_fidelity_from_afa_table(afa_table, params=None):
    missing = _REQUIRED_AFA_COLUMNS - set(afa_table.columns)
    if missing:
        raise KeyError(f'AFA table is missing required column(s): {sorted(missing)}')
    p = validate_model(params)
    out = afa_table.copy()
    if out.empty:
        out['Gate-use idle [ns]'] = pd.Series(dtype=float)
        out['EPR fidelity at gate'] = pd.Series(dtype=float)
        return (out, {'total_requests': 0, 'average_epr_fidelity': np.nan, 'sum_epr_fidelity': 0.0})
    gate_idle_ns = np.maximum(out['Time before deadline [ns]'].to_numpy(dtype=float), 0.0)
    request_params = dict(p)
    request_params['T_idle_A'] = float(p['T_idle_A']) + gate_idle_ns * 1e-09
    request_params['T_idle_B'] = float(p['T_idle_B']) + gate_idle_ns * 1e-09
    fidelities = np.asarray(F_cond(request_params), dtype=float)
    if fidelities.ndim == 0:
        fidelities = np.full(len(out), float(fidelities))
    out['Gate-use idle [ns]'] = gate_idle_ns
    out['EPR fidelity at gate'] = fidelities
    fidelity_sum = float(np.sum(fidelities))
    n_requests = int(len(out))
    average = float(fidelity_sum / n_requests)
    return (out, {'total_requests': n_requests, 'sum_epr_fidelity': fidelity_sum, 'average_epr_fidelity': average, 'mean_gate_use_idle_ns': float(np.mean(gate_idle_ns)), 'base_success_probability': float(np.asarray(P_succ(p))), 'base_zero_scheduler_idle_fidelity': float(np.asarray(F_cond(p)))})