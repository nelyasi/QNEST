from pathlib import Path
import matplotlib
matplotlib.use('Agg', force=True)
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator, MaxNLocator
PALETTE = {'afa': '#0072B2', 'hamfa': '#D55E00', 'memory': '#009E73', 'photonic': '#CC79A7', 'epr': '#332288', 'neutral': '#4D4D4D'}

def set_academic_style():
    plt.rcParams.update({'font.family': 'serif', 'font.serif': ['DejaVu Serif', 'Times New Roman', 'Times'], 'font.size': 11, 'axes.labelsize': 12, 'axes.titlesize': 12, 'legend.fontsize': 10, 'xtick.labelsize': 10, 'ytick.labelsize': 10, 'axes.linewidth': 0.9, 'lines.linewidth': 2.1, 'lines.markersize': 5.5, 'figure.dpi': 130, 'savefig.dpi': 600, 'savefig.bbox': 'tight', 'pdf.fonttype': 42, 'ps.fonttype': 42})

def _format_axis(ax, *, integer_y=False):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', alpha=0.22, linewidth=0.7)
    ax.tick_params(direction='out', length=4, width=0.8)
    ax.tick_params(which='minor', length=2.5, width=0.6)
    ax.xaxis.set_minor_locator(AutoMinorLocator(2))
    ax.yaxis.set_minor_locator(AutoMinorLocator(2))
    if integer_y:
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.margins(x=0.01)

def _save(fig, output_dir, stem, formats=('pdf', 'png')):
    if output_dir is None:
        return
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for extension in formats:
        fig.savefig(output_dir / f'{stem}.{extension}')

def plot_epr_pairs_vs_qubits(results, *, output_dir=None, formats=('pdf', 'png')):
    set_academic_style()
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    ax.plot(results['n_qubits'], results['epr_pairs'], color=PALETTE['epr'], marker='o', markevery=max(1, len(results) // 18), label='EPR pairs')
    ax.set_xlabel('Number of circuit qubits')
    ax.set_ylabel('Number of EPR pairs')
    _format_axis(ax, integer_y=True)
    _save(fig, output_dir, 'epr_pairs_vs_qubits', formats)
    return (fig, ax)

def plot_punishment_time_vs_qubits(results, *, output_dir=None, formats=('pdf', 'png'), time_unit='us'):
    factors = {'ns': 1.0, 'us': 1000.0, 'ms': 1000000.0}
    labels = {'ns': 'ns', 'us': 'µs', 'ms': 'ms'}
    if time_unit not in factors:
        raise ValueError("time_unit must be one of: 'ns', 'us', 'ms'.")
    scale = factors[time_unit]
    set_academic_style()
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    x = results['n_qubits'].to_numpy(dtype=float)
    for metric, label, color, marker in [('afa_punishment_time_ns', 'AFA-QSP', PALETTE['afa'], 'o'), ('hamfa_punishment_time_ns', 'HAMFA-QSP', PALETTE['hamfa'], 's')]:
        mean = results[metric].to_numpy(dtype=float) / scale
        line, = ax.plot(x, mean, color=color, marker=marker, markevery=max(1, len(results) // 18), label=label)
        std_col = metric + '_std'
        if std_col in results.columns:
            sd = results[std_col].fillna(0.0).to_numpy(dtype=float) / scale
            ax.fill_between(x, (mean - sd).clip(0.0), mean + sd, color=line.get_color(), alpha=0.18, linewidth=0)
    ax.set_xlabel('Number of circuit qubits')
    ax.set_ylabel(f'Overall punishment time ({labels[time_unit]})')
    ax.legend(frameon=False)
    _format_axis(ax)
    if any((c.endswith('_std') for c in results.columns)):
        ax.text(0.02, 0.98, 'Shaded band = mean ± 1 SD', transform=ax.transAxes, ha='left', va='top', fontsize='small')
    _save(fig, output_dir, 'punishment_time_vs_qubits', formats)
    return (fig, ax)

def plot_hamfa_resource_usage_vs_qubits(results, *, output_dir=None, formats=('pdf', 'png')):
    set_academic_style()
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    x = results['n_qubits'].to_numpy(dtype=float)
    for metric, label, color, marker in [('hamfa_memory_assisted_successful', 'Memory-assisted completion', PALETTE['memory'], 'o'), ('hamfa_all_photonic_used', 'All-photonic used', PALETTE['photonic'], 'D')]:
        mean = results[metric].to_numpy(dtype=float)
        line, = ax.plot(x, mean, color=color, marker=marker, markevery=max(1, len(results) // 18), label=label)
        std_col = metric + '_std'
        if std_col in results.columns:
            sd = results[std_col].fillna(0.0).to_numpy(dtype=float)
            ax.fill_between(x, (mean - sd).clip(0.0), mean + sd, color=line.get_color(), alpha=0.18, linewidth=0)
    ax.set_xlabel('Number of circuit qubits')
    ax.set_ylabel('Number of requests served')
    ax.legend(frameon=False)
    _format_axis(ax)
    if any((c.endswith('_std') for c in results.columns)):
        ax.text(0.02, 0.98, 'Shaded band = mean ± 1 SD', transform=ax.transAxes, ha='left', va='top', fontsize='small')
    _save(fig, output_dir, 'hamfa_resource_usage_vs_qubits', formats)
    return (fig, ax)

def plot_blocked_requests_vs_qubits(results, *, output_dir=None, formats=('pdf', 'png')):
    set_academic_style()
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    x = results['n_qubits'].to_numpy(dtype=float)
    for metric, label, color, marker in [('afa_blocked_requests', 'AFA-QSP', PALETTE['afa'], 'o'), ('hamfa_blocked_requests', 'HAMFA-QSP', PALETTE['hamfa'], 's')]:
        mean = results[metric].to_numpy(dtype=float)
        line, = ax.plot(x, mean, color=color, marker=marker, markevery=max(1, len(results) // 18), label=label)
        std_col = metric + '_std'
        if std_col in results.columns:
            sd = results[std_col].fillna(0.0).to_numpy(dtype=float)
            ax.fill_between(x, (mean - sd).clip(0.0), mean + sd, color=line.get_color(), alpha=0.18, linewidth=0)
    ax.set_xlabel('Number of circuit qubits')
    ax.set_ylabel('Number of blocked requests')
    ax.legend(frameon=False)
    _format_axis(ax)
    if any((c.endswith('_std') for c in results.columns)):
        ax.text(0.02, 0.98, 'Shaded band = mean ± 1 SD', transform=ax.transAxes, ha='left', va='top', fontsize='small')
    _save(fig, output_dir, 'blocked_requests_vs_qubits', formats)
    return (fig, ax)

def plot_all_results(results, *, output_dir=None, formats=('pdf', 'png')):
    figures = {}
    figures['epr'] = plot_epr_pairs_vs_qubits(results, output_dir=output_dir, formats=formats)[0]
    figures['delay'] = plot_punishment_time_vs_qubits(results, output_dir=output_dir, formats=formats)[0]
    figures['hamfa_usage'] = plot_hamfa_resource_usage_vs_qubits(results, output_dir=output_dir, formats=formats)[0]
    figures['blocked'] = plot_blocked_requests_vs_qubits(results, output_dir=output_dir, formats=formats)[0]
    return figures