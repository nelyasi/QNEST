import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox, simpledialog
import threading
import time
import math
import json
import sys
import os
import shutil
import webbrowser
from urllib.parse import quote
import platform
import zipfile
import re
import queue
import numbers
from datetime import datetime
from pathlib import Path
from src.gui_pipeline import PipelineController, NOTEBOOK_AFA_TABLE_COLUMNS, NOTEBOOK_HAMFA_TABLE_COLUMNS
from src.llm_assistant import QNESTAssistantClient, LLMConnectionError
APP_NAME = 'QNEST'
APP_VERSION = '0.3.12'
APP_SUBTITLE = 'Quantum Network End-to-End Simulation Toolkit'
BUG_REPORT_EMAIL = 'elyasi@chalmers.se'
PROJECT_ROOT = Path(__file__).resolve().parent
UI_SETTINGS_PATH = Path.home() / '.qnest' / 'ui_settings.json'
NOTEBOOK_REFERENCE_DEFAULTS = {'n_qpus': 14, 'qubits_per_qpu': 10, 'distribution_method': 'PartitioningAnnealing', 'distribution_seed': 1, 'single_qubit_time_us': 5.5, 'two_qubit_time_us': 66.0, 'epr_attempt_time_us': 198.981, 'starting_process_time_us': 276.471, 'ending_process_time_us': 71.99, 'scheduling_strategy': 'QOALA', 'p_succ': 0.044426421303161545, 'protocol_seed': 42, 'monte_carlo_runs': 30, 'delta_t_c_ns': 2800000000.0, 'F_I': 0.9796744718797619, 'F_T': 0.9306907483, 'alpha': 0.05, 'deadline_equal_is_blocked': True, 'background_start_ns': 0.0}
ASSISTANT_DEFAULT_EXPERIMENT = {'benchmark': 'GHZ State', 'workflow': 'Batch / sweep', 'min_qubits': 5, 'max_qubits': 20, 'step': 2, 'n_qpus': 7, 'qubits_per_qpu': 4, 'topology': 'All-to-all', 'interconnect': 'Shared switch', 'switch_mode': 'Memory-assisted'}
THEMES = {'Executive Slate': {'bg': '#F5F7FA', 'bg2': '#FFFFFF', 'bg3': '#F2F4F7', 'bg4': '#E4E7EC', 'border': '#D0D5DD', 'sep': '#EAECF0', 'accent': '#175CD3', 'accent2': '#0E9384', 'success': '#027A48', 'warning': '#B54708', 'danger': '#B42318', 'comm': '#6941C6', 'text': '#101828', 'muted': '#475467', 'hint': '#98A2B3', 'menu_sel': '#EAF2FF', 'menu_hover': '#F2F4F7', 'splash_bg': '#FFFFFF', 'sidebar_bg': '#101828', 'sidebar_text': '#D0D5DD', 'sidebar_muted': '#98A2B3', 'sidebar_sel': '#1D2939', 'toolbar_bg': '#FFFFFF', 'toolbar_hover': '#F2F4F7'}, 'Blue Steel': {'bg': '#F3F6F9', 'bg2': '#FFFFFF', 'bg3': '#EEF2F6', 'bg4': '#E1E8EF', 'border': '#C9D3DE', 'sep': '#E2E8F0', 'accent': '#1F5A94', 'accent2': '#287D7A', 'success': '#2F6F4E', 'warning': '#9A6200', 'danger': '#A43F3F', 'comm': '#5C5AA7', 'text': '#17212B', 'muted': '#52606D', 'hint': '#8A99A8', 'menu_sel': '#E8F0F8', 'menu_hover': '#EEF3F7', 'splash_bg': '#FFFFFF', 'sidebar_bg': '#172A3A', 'sidebar_text': '#D9E2EC', 'sidebar_muted': '#9FB3C8', 'sidebar_sel': '#243B53', 'toolbar_bg': '#FFFFFF', 'toolbar_hover': '#EEF3F7'}, 'Neutral Graphite': {'bg': '#F6F6F7', 'bg2': '#FFFFFF', 'bg3': '#F0F1F2', 'bg4': '#E5E7E9', 'border': '#D2D5D9', 'sep': '#E7E9EC', 'accent': '#2F5F98', 'accent2': '#347A72', 'success': '#3C6F54', 'warning': '#8A6116', 'danger': '#9E3F45', 'comm': '#625B9B', 'text': '#1C1F23', 'muted': '#565D66', 'hint': '#9299A1', 'menu_sel': '#EBEFF4', 'menu_hover': '#F1F2F4', 'splash_bg': '#FFFFFF', 'sidebar_bg': '#20252B', 'sidebar_text': '#D8DCE1', 'sidebar_muted': '#9CA3AB', 'sidebar_sel': '#30363D', 'toolbar_bg': '#FFFFFF', 'toolbar_hover': '#F1F2F4'}}
C = dict(THEMES['Executive Slate'])

def _load_ui_preferences():
    defaults = {'theme': 'Executive Slate', 'scale': 1.0, 'show_splash': True, 'animate_splash': True, 'start_page': 'Circuit', 'ai_provider': 'Ollama (local)', 'ai_endpoint': 'http://127.0.0.1:11434', 'ai_model': 'qwen3:8b', 'ai_temperature': 0.2, 'ai_require_confirmation': True, 'ai_dock_open': True}
    try:
        if UI_SETTINGS_PATH.exists():
            data = json.loads(UI_SETTINGS_PATH.read_text(encoding='utf-8'))
            if data.get('theme') in THEMES:
                defaults['theme'] = data['theme']
            try:
                defaults['scale'] = min(1.3, max(0.85, float(data.get('scale', 1.0))))
            except Exception:
                pass
            defaults['show_splash'] = bool(data.get('show_splash', True))
            defaults['animate_splash'] = bool(data.get('animate_splash', True))
            if data.get('start_page') in {'Circuit', 'Network', 'Compile', 'Schedule', 'Run'}:
                defaults['start_page'] = data['start_page']
            if data.get('ai_provider') in {'Ollama (local)', 'OpenAI-compatible'}:
                defaults['ai_provider'] = data['ai_provider']
            endpoint = str(data.get('ai_endpoint', '')).strip()
            if endpoint.startswith(('http://', 'https://')):
                defaults['ai_endpoint'] = endpoint
            model = str(data.get('ai_model', '')).strip()
            if model:
                defaults['ai_model'] = model
            try:
                defaults['ai_temperature'] = min(1.0, max(0.0, float(data.get('ai_temperature', 0.2))))
            except Exception:
                pass
            defaults['ai_require_confirmation'] = bool(data.get('ai_require_confirmation', True))
            defaults['ai_dock_open'] = bool(data.get('ai_dock_open', True))
    except Exception:
        pass
    return defaults

def _save_ui_preferences(data):
    UI_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    UI_SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding='utf-8')

def _activate_theme(name):
    C.clear()
    C.update(THEMES.get(name, THEMES['Executive Slate']))
import tkinter.font as tkfont
_REF_W = 1400
_REF_H = 900
_MIN_SCALE = 0.65
_MAX_SCALE = 1.3
_BASE = {'title': 22, 'head': 15, 'subh': 13, 'body': 12, 'mono': 12, 'menu': 13, 'small': 11, 'small_mono': 11}

class _FontManager:

    def __init__(self):
        self._fonts = {}
        self._ready = False
        self._user_scale = 1.0
        self._current_ratio = 1.0
        self._last_window = (_REF_W, _REF_H)

    def set_user_scale(self, factor):
        self._user_scale = min(1.3, max(0.85, float(factor)))
        if self._ready:
            self.scale(*self._last_window)

    def _init(self):
        if self._ready:
            return
        specs = {'title': ('DM Sans', _BASE['title'], 'bold'), 'head': ('DM Sans', _BASE['head'], 'bold'), 'subh': ('DM Sans', _BASE['subh'], 'bold'), 'body': ('DM Sans', _BASE['body'], 'normal'), 'mono': ('DM Mono', _BASE['mono'], 'normal'), 'menu': ('DM Sans', _BASE['menu'], 'bold'), 'small': ('DM Sans', _BASE['small'], 'normal'), 'small_mono': ('DM Mono', _BASE['small_mono'], 'normal')}
        for key, (fam, size, weight) in specs.items():
            self._fonts[key] = tkfont.Font(family=fam, size=size, weight=weight)
        self._ready = True

    def scale(self, win_w, win_h):
        if not self._ready:
            self._init()
        self._last_window = (win_w, win_h)
        auto_ratio = min(1.0, win_w / _REF_W, win_h / _REF_H)
        ratio = auto_ratio * self._user_scale
        ratio = max(_MIN_SCALE, min(_MAX_SCALE, ratio))
        self._current_ratio = ratio
        for key, font in self._fonts.items():
            new_size = max(9, round(_BASE[key] * ratio))
            font.configure(size=new_size)

    @property
    def ratio(self):
        return self._current_ratio

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        if not self._ready:
            self._init()
        if name in self._fonts:
            return self._fonts[name]
        raise AttributeError(f"FontManager has no font '{name}'")
FM = _FontManager()

def _label(parent, text=None, font=None, fg=None, bg=None, **kw):
    if font is None:
        font = FM.body
    return tk.Label(parent, font=font, fg=fg or C['text'], bg=bg or C['bg2'], **{} if text is None else {'text': text}, **kw)

def _frame(parent, bg=None, **kw):
    return tk.Frame(parent, bg=bg or C['bg2'], **kw)

class _Frame(tk.Frame):

    def __init__(self, parent, bg=None, **kw):
        super().__init__(parent, bg=bg or C['bg2'], **kw)

def _sep(parent, bg=None):
    return tk.Frame(parent, bg=bg or C['sep'], height=1)

def _card(parent, **kw):
    f = tk.Frame(parent, bg=C['bg2'], highlightbackground=C['border'], highlightthickness=1, **kw)
    return f

def _entry(parent, width=22, accent=None, **kw):
    return tk.Entry(parent, width=width, font=FM.mono, bg=C['bg3'], fg=C['text'], insertbackground=accent or C['accent'], relief='flat', highlightbackground=C['border'], highlightthickness=1, **kw)

def _hex_rgb(value):
    value = str(value).lstrip('#')
    if len(value) != 6:
        return None
    try:
        return tuple((int(value[i:i + 2], 16) for i in (0, 2, 4)))
    except Exception:
        return None

def _mix_hex(a, b, amount):
    ra, rb = (_hex_rgb(a), _hex_rgb(b))
    if ra is None or rb is None:
        return a
    t = max(0.0, min(1.0, float(amount)))
    out = tuple((round(x * (1.0 - t) + y * t) for x, y in zip(ra, rb)))
    return '#%02X%02X%02X' % out

class _ProfessionalButton(tk.Label):

    def __init__(self, parent, text='', command=None, *, variant='secondary', accent=None, fg=None, state='normal', **kw):
        self._command = command
        self._state = str(state)
        self._variant = variant
        self._accent = accent or C['accent']
        self._pressed = False
        self._hovered = False
        user_bg = kw.pop('bg', kw.pop('background', None))
        user_fg = fg or kw.pop('fg', kw.pop('foreground', None))
        user_hover_bg = kw.pop('activebackground', None)
        user_hover_fg = kw.pop('activeforeground', None)
        self._disabled_fg = kw.pop('disabledforeground', C['muted'])
        self._disabled_bg = kw.pop('disabledbackground', C['bg4'])
        kw.pop('bd', None)
        kw.pop('borderwidth', None)
        kw.pop('default', None)
        kw.pop('overrelief', None)
        kw.pop('repeatdelay', None)
        kw.pop('repeatinterval', None)
        if variant == 'primary':
            self._normal_bg = user_bg or self._accent
            self._normal_fg = user_fg or '#FFFFFF'
            self._hover_bg = user_hover_bg or _mix_hex(self._accent, '#000000', 0.1)
            self._hover_fg = user_hover_fg or '#FFFFFF'
            self._pressed_bg = _mix_hex(self._accent, '#000000', 0.18)
            border = self._normal_bg
        elif variant == 'danger':
            self._normal_bg = user_bg or C['danger']
            self._normal_fg = user_fg or '#FFFFFF'
            self._hover_bg = user_hover_bg or _mix_hex(C['danger'], '#000000', 0.1)
            self._hover_fg = user_hover_fg or '#FFFFFF'
            self._pressed_bg = _mix_hex(C['danger'], '#000000', 0.18)
            border = self._normal_bg
        else:
            self._normal_bg = user_bg or C['bg2']
            self._normal_fg = user_fg or self._accent
            self._hover_bg = user_hover_bg or C['menu_sel']
            self._hover_fg = user_hover_fg or self._accent
            self._pressed_bg = C['bg4']
            border = kw.pop('highlightbackground', C['border'])
        kw.setdefault('font', FM.small)
        kw.setdefault('cursor', 'hand2')
        kw.setdefault('relief', 'flat')
        kw.setdefault('highlightthickness', 1)
        kw.setdefault('highlightbackground', border)
        kw.setdefault('highlightcolor', self._accent)
        kw.setdefault('padx', 14)
        kw.setdefault('pady', 7)
        kw.setdefault('takefocus', 1)
        kw.setdefault('anchor', 'center')
        super().__init__(parent, text=text, bg=self._normal_bg, fg=self._normal_fg, **kw)
        self.bind('<Enter>', self._on_enter, add='+')
        self.bind('<Leave>', self._on_leave, add='+')
        self.bind('<ButtonPress-1>', self._on_press, add='+')
        self.bind('<ButtonRelease-1>', self._on_release, add='+')
        self.bind('<Key-space>', self._on_key, add='+')
        self.bind('<Key-Return>', self._on_key, add='+')
        self.bind('<FocusIn>', lambda _e: self._paint(), add='+')
        self.bind('<FocusOut>', lambda _e: self._paint(), add='+')
        self._paint()

    def _paint(self):
        disabled = self._state == 'disabled'
        if disabled:
            bg, fg = (self._disabled_bg, self._disabled_fg)
            cursor = 'arrow'
        elif self._pressed:
            bg, fg = (self._pressed_bg, self._hover_fg)
            cursor = 'hand2'
        elif self._hovered:
            bg, fg = (self._hover_bg, self._hover_fg)
            cursor = 'hand2'
        else:
            bg, fg = (self._normal_bg, self._normal_fg)
            cursor = 'hand2'
        tk.Label.configure(self, bg=bg, fg=fg, cursor=cursor)
        try:
            focused = self.focus_get() is self and (not disabled)
            tk.Label.configure(self, highlightbackground=self._accent if focused else self._border_color())
        except Exception:
            pass

    def _border_color(self):
        if self._variant in {'primary', 'danger'}:
            return self._normal_bg if self._state != 'disabled' else C['border']
        return C['border']

    def _on_enter(self, _event=None):
        if self._state != 'disabled':
            self._hovered = True
            self._paint()

    def _on_leave(self, _event=None):
        self._hovered = False
        self._pressed = False
        self._paint()

    def _on_press(self, _event=None):
        if self._state != 'disabled':
            self.focus_set()
            self._pressed = True
            self._paint()

    def _on_release(self, event=None):
        was_pressed = self._pressed
        self._pressed = False
        self._paint()
        if not was_pressed or self._state == 'disabled':
            return
        if event is None or (0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height()):
            self.invoke()

    def _on_key(self, _event=None):
        if self._state != 'disabled':
            self.invoke()
        return 'break'

    def invoke(self):
        if self._state != 'disabled' and callable(self._command):
            return self._command()
        return None

    def configure(self, cnf=None, **kw):
        if cnf:
            kw.update(cnf)
        if 'command' in kw:
            self._command = kw.pop('command')
        if 'state' in kw:
            self._state = str(kw.pop('state'))
        if 'disabledforeground' in kw:
            self._disabled_fg = kw.pop('disabledforeground')
        if 'disabledbackground' in kw:
            self._disabled_bg = kw.pop('disabledbackground')
        if 'bg' in kw or 'background' in kw:
            self._normal_bg = kw.pop('bg', kw.pop('background', self._normal_bg))
        if 'fg' in kw or 'foreground' in kw:
            self._normal_fg = kw.pop('fg', kw.pop('foreground', self._normal_fg))
        if 'activebackground' in kw:
            self._hover_bg = kw.pop('activebackground')
        if 'activeforeground' in kw:
            self._hover_fg = kw.pop('activeforeground')
        if 'highlightbackground' in kw:
            hb = kw['highlightbackground']
            if self._variant == 'secondary':
                pass
        if kw:
            tk.Label.configure(self, **kw)
        self._paint()
    config = configure

    def cget(self, key):
        if key == 'state':
            return self._state
        if key == 'command':
            return self._command
        if key == 'disabledforeground':
            return self._disabled_fg
        if key == 'activebackground':
            return self._hover_bg
        if key == 'activeforeground':
            return self._hover_fg
        return tk.Label.cget(self, key)

    def __getitem__(self, key):
        return self.cget(key)

    def __setitem__(self, key, value):
        self.configure(**{key: value})

def _button(parent, text, accent=None, fg=None, command=None, **kw):
    ac = accent or C['accent']
    kw.setdefault('disabledforeground', C['muted'])
    kw.setdefault('disabledbackground', C['bg4'])
    return _ProfessionalButton(parent, text=text, command=command, variant='primary', accent=ac, fg=fg, **kw)

def _ghost_button(parent, text, accent=None, command=None, **kw):
    ac = accent or C['accent']
    kw.setdefault('disabledforeground', C['muted'])
    kw.setdefault('disabledbackground', C['bg3'])
    return _ProfessionalButton(parent, text=text, command=command, variant='secondary', accent=ac, **kw)

def _segmented_button(parent, text, command=None, *, selected=False, accent=None, **kw):
    ac = accent or C['accent']
    if selected:
        kw.setdefault('bg', C['menu_sel'])
        kw.setdefault('fg', ac)
        kw.setdefault('activebackground', _mix_hex(C['menu_sel'], ac, 0.08))
    else:
        kw.setdefault('bg', C['bg2'])
        kw.setdefault('fg', C['muted'])
        kw.setdefault('activebackground', C['menu_hover'])
    kw.setdefault('padx', 10)
    kw.setdefault('pady', 4)
    return _ProfessionalButton(parent, text=text, command=command, variant='secondary', accent=ac, **kw)

def _install_interaction_defaults(root):
    for pattern, value in (('*Button.activeForeground', C['text']), ('*Button.disabledForeground', C['muted']), ('*Checkbutton.activeForeground', C['text']), ('*Checkbutton.disabledForeground', C['muted']), ('*Radiobutton.activeForeground', C['text']), ('*Radiobutton.disabledForeground', C['muted']), ('*Menubutton.activeForeground', C['text']), ('*Menubutton.disabledForeground', C['muted']), ('*Menu.activeForeground', C['text']), ('*Menu.activeBackground', C['menu_sel'])):
        try:
            root.option_add(pattern, value)
        except Exception:
            pass

def _open_local_path(path):
    path = Path(path).expanduser().resolve()
    if not path.exists():
        messagebox.showwarning('QNEST', f'File not found:\n{path}')
        return
    try:
        if path.is_file() and path.suffix.lower() == '.html':
            try:
                head = path.read_text(encoding='utf-8', errors='replace')
                if 'pytket-circuit-renderer' in head or 'pytket-circuit-display-container' in head:
                    from src.circuit_visuals import make_responsive_pytket_html_file
                    make_responsive_pytket_html_file(path)
            except Exception:
                pass
        if os.name == 'nt':
            os.startfile(str(path))
        elif path.is_dir():
            import subprocess
            subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', str(path)])
        else:
            webbrowser.open(path.as_uri())
    except Exception as exc:
        messagebox.showerror('Open error', str(exc))

def _safe_text(value):
    if isinstance(value, (dict, list, tuple)):
        try:
            return json.dumps(value, indent=2, default=str)
        except Exception:
            return str(value)
    return str(value)

def _display_times_in_us(df):
    try:
        import pandas as pd
        import numbers
        out = df.copy()
        rename = {}
        for col in list(out.columns):
            name = str(col)
            if '[ns]' in name or '_ns' in name:
                try:
                    numeric = pd.to_numeric(out[col], errors='coerce')
                    mask = numeric.notna()
                    if mask.any():
                        out[col] = out[col].astype(object)
                        out.loc[mask, col] = numeric.loc[mask].astype(float) / 1000.0
                except Exception:
                    pass
                new = name.replace('[ns]', '[µs]').replace('_ns', '_us')
                rename[col] = new
        if rename:
            out = out.rename(columns=rename)
        if 'metric' in out.columns:
            for idx, metric in out['metric'].items():
                name = str(metric)
                if '[ns]' in name or '_ns' in name:
                    new = name.replace('[ns]', '[µs]').replace('_ns', '_us')
                    out.at[idx, 'metric'] = new
                    for col in out.columns:
                        if col == 'metric':
                            continue
                        value = out.at[idx, col]
                        if isinstance(value, numbers.Number) and (not isinstance(value, bool)):
                            out.at[idx, col] = float(value) / 1000.0
        return out
    except Exception:
        return df

class TableView(_Frame):

    def __init__(self, parent, max_preview_rows=1500, convert_times=True, center=True, heading_aliases=None, compact_numbers=True):
        super().__init__(parent)
        self.max_preview_rows = max_preview_rows
        self.convert_times = bool(convert_times)
        self.center = bool(center)
        self.heading_aliases = dict(heading_aliases or {})
        self.compact_numbers = bool(compact_numbers)
        self._data = None
        self._tree = ttk.Treeview(self, show='headings', selectmode='browse')
        y = ttk.Scrollbar(self, orient='vertical', command=self._tree.yview)
        x = ttk.Scrollbar(self, orient='horizontal', command=self._tree.xview)
        self._tree.configure(yscrollcommand=y.set, xscrollcommand=x.set)
        y.pack(side='right', fill='y')
        x.pack(side='bottom', fill='x')
        self._tree.pack(fill='both', expand=True)
        self._tree.tag_configure('even', background=C['bg2'])
        self._tree.tag_configure('odd', background=C['bg3'])
        self._empty = tk.Label(self, text='No data yet.', font=FM.small, fg=C['hint'], bg=C['bg2'])
        self._empty.place(relx=0.5, rely=0.5, anchor='center')

    def clear(self):
        self._data = None
        self._tree.delete(*self._tree.get_children())
        self._tree['columns'] = ()
        self._empty.place(relx=0.5, rely=0.5, anchor='center')

    def _heading_text(self, col):
        name = str(col)
        if name in self.heading_aliases:
            return self.heading_aliases[name]
        ns_name = name.replace('[µs]', '[ns]').replace('_us', '_ns')
        alias = self.heading_aliases.get(ns_name)
        if alias:
            return alias.replace('[ns]', '[µs]')
        return name

    def _format_value(self, value):
        try:
            import pandas as pd
            if pd.isna(value):
                return '—'
        except Exception:
            pass
        if self.compact_numbers and isinstance(value, numbers.Number) and (not isinstance(value, bool)):
            try:
                fv = float(value)
                if math.isfinite(fv):
                    if abs(fv - round(fv)) < 1e-10:
                        return f'{int(round(fv)):,}'
                    if abs(fv) >= 1000:
                        return f'{fv:,.3f}'.rstrip('0').rstrip('.')
                    return f'{fv:.6f}'.rstrip('0').rstrip('.')
            except Exception:
                pass
        txt = _safe_text(value).replace('\n', ' ')
        return txt if len(txt) <= 300 else txt[:297] + '…'

    def set_data(self, data):
        self.clear()
        if data is None:
            return
        try:
            import pandas as pd
            if isinstance(data, pd.DataFrame):
                df = data.copy()
            elif isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                df = pd.DataFrame(data)
        except Exception:
            return
        if self.convert_times:
            df = _display_times_in_us(df)
        self._data = df
        if df.empty and len(df.columns) == 0:
            return
        cols = [str(c) for c in df.columns]
        self._tree['columns'] = cols
        try:
            heading_font = FM.small
            body_font = FM.body
        except Exception:
            heading_font = body_font = None
        sample = df.head(min(60, self.max_preview_rows))
        for col in cols:
            anchor = 'center' if self.center else 'w'
            heading = self._heading_text(col)
            self._tree.heading(col, text=heading, anchor=anchor)
            try:
                measured = heading_font.measure(heading) + 30 if heading_font else len(heading) * 8 + 30
                for value in sample[col].tolist()[:30]:
                    txt = self._format_value(value)
                    w = body_font.measure(txt) + 28 if body_font else len(txt) * 8 + 28
                    measured = max(measured, w)
                width = max(82, min(220, int(measured)))
            except Exception:
                width = max(100, min(220, len(heading) * 8 + 30))
            self._tree.column(col, width=width, minwidth=70, anchor=anchor, stretch=False)
        for i, (_, row) in enumerate(df.head(self.max_preview_rows).iterrows()):
            vals = [self._format_value(value) for value in row.tolist()]
            self._tree.insert('', 'end', values=vals, tags=('even' if i % 2 == 0 else 'odd',))
        self._empty.place_forget()

class ArtifactBrowser(_Frame):

    def __init__(self, parent, stage_prefixes=None):
        super().__init__(parent)
        self.stage_prefixes = tuple(stage_prefixes or ())
        self._paths = {}
        top = _frame(self)
        top.pack(fill='x', pady=(0, 6))
        _ghost_button(top, '⟳ Refresh', command=self.refresh, padx=9, pady=4).pack(side='left')
        _ghost_button(top, 'Open', command=self._open, padx=9, pady=4).pack(side='left', padx=6)
        _ghost_button(top, 'Save copy…', command=self._save_copy, padx=9, pady=4).pack(side='left')
        _ghost_button(top, 'Open run folder', command=self._open_folder, padx=9, pady=4).pack(side='left', padx=6)
        self._tree = ttk.Treeview(self, columns=('stage', 'file', 'size'), show='headings')
        for col, text, width in [('stage', 'Stage', 140), ('file', 'Artifact', 520), ('size', 'Size', 90)]:
            self._tree.heading(col, text=text, anchor='center')
            self._tree.column(col, width=width, anchor='center')
        y = ttk.Scrollbar(self, orient='vertical', command=self._tree.yview)
        self._tree.configure(yscrollcommand=y.set)
        y.pack(side='right', fill='y')
        self._tree.pack(fill='both', expand=True)
        self._tree.bind('<Double-1>', lambda _e: self._open())

    def _controller(self):
        return self.winfo_toplevel().pipeline

    def refresh(self):
        self._tree.delete(*self._tree.get_children())
        self._paths.clear()
        ctl = self._controller()
        run_dir = ctl.state.run_dir
        if run_dir is None:
            return
        for path in ctl.artifact_files():
            rel = path.relative_to(run_dir)
            if self.stage_prefixes and (not any((str(rel).startswith(p) for p in self.stage_prefixes))):
                continue
            stage = rel.parts[0] if len(rel.parts) > 1 else 'session'
            size = path.stat().st_size
            size_txt = f'{size / 1024:.1f} KB' if size >= 1024 else f'{size} B'
            iid = self._tree.insert('', 'end', values=(stage, str(rel), size_txt))
            self._paths[iid] = path

    def selected_path(self):
        sel = self._tree.selection()
        return self._paths.get(sel[0]) if sel else None

    def _open(self):
        path = self.selected_path()
        if path:
            _open_local_path(path)

    def _save_copy(self):
        path = self.selected_path()
        if not path:
            return
        dest = filedialog.asksaveasfilename(initialfile=path.name)
        if dest:
            try:
                shutil.copy2(path, dest)
                messagebox.showinfo('Saved', f'Copied to:\n{dest}')
            except Exception as exc:
                messagebox.showerror('Save error', str(exc))

    def _open_folder(self):
        run_dir = self._controller().state.run_dir
        if run_dir:
            _open_local_path(run_dir)

class CircuitTrailView(_Frame):
    STAGES = [('01_original', '1 · Original circuit'), ('02_cleaned', '2 · Cleaned circuit'), ('03_dqc_prepared', '3 · After DQCPass'), ('04_distributed_real', '4 · Distributed circuit (real)'), ('05_ejpp_representation', '5 · Explicit EJPP representation')]

    def __init__(self, parent):
        super().__init__(parent)
        self._stage = tk.StringVar(value=self.STAGES[0][0])
        bar = _frame(self)
        bar.pack(fill='x', pady=(0, 4))
        for stem, label in self.STAGES:
            tk.Radiobutton(bar, text=label, variable=self._stage, value=stem, font=FM.small, bg=C['bg2'], fg=C['text'], selectcolor=C['bg3'], activebackground=C['bg4'], activeforeground=C['text'], disabledforeground=C['muted'], command=self.refresh).pack(side='left', padx=(0, 8))
        actions = _frame(self)
        actions.pack(fill='x', pady=(0, 6))
        _ghost_button(actions, 'Save representation…', command=self._save, padx=9, pady=4).pack(side='right')
        _ghost_button(actions, 'Open interactive', command=lambda: self._open_ext('.html'), padx=9, pady=4).pack(side='right', padx=6)
        _ghost_button(actions, 'Open QASM', command=lambda: self._open_ext('.qasm'), padx=9, pady=4).pack(side='right')
        self._meta = _label(self, 'Compile/distribute a circuit to populate this representation.', font=FM.small, fg=C['muted'])
        self._meta.pack(fill='x', pady=(0, 6))
        holder = tk.Frame(self, bg=C['bg3'], highlightbackground=C['border'], highlightthickness=1)
        holder.pack(fill='both', expand=True)
        self._viewer = _ExactPytketCircuitCanvas(holder)
        self._viewer.pack(fill='both', expand=True)

    def _base(self):
        run_dir = self.winfo_toplevel().pipeline.state.run_dir
        return run_dir / '03_compile' / self._stage.get() if run_dir else None

    def refresh(self):
        base = self._base()
        if not base:
            self._meta.config(text='Compile/distribute a circuit to populate this representation.')
            self._viewer._show_empty('Compile/distribute a circuit to populate the exact pytket representation.')
            return
        qasm = base.with_suffix('.qasm')
        html = base.with_suffix('.html')
        snapshot = base.with_suffix('.renderer.png')
        label = dict(self.STAGES).get(self._stage.get(), self._stage.get())
        bits = []
        txt = base.with_suffix('.txt')
        if txt.exists():
            try:
                for line in txt.read_text(encoding='utf-8', errors='replace').splitlines()[:6]:
                    if line.startswith(('Qubits:', 'Gates:', 'Depth:')):
                        bits.append(line.replace(':', ' ', 1))
            except Exception:
                pass
        self._meta.config(text=label + ('  •  ' + '  •  '.join(bits) if bits else ''))
        snapshot_error = None
        try:
            meta = self.winfo_toplevel().pipeline.state.compile_metadata or {}
            snapshot_error = ((meta.get('renderer_snapshots') or {}).get(self._stage.get()) or {}).get('error')
        except Exception:
            pass
        self._viewer.show(snapshot_path=snapshot if snapshot.exists() else None, html_path=html if html.exists() else None, qasm_path=qasm if qasm.exists() else None, error=snapshot_error)

    def _open_ext(self, ext):
        base = self._base()
        if base:
            p = base.with_suffix(ext)
            if p.exists():
                _open_local_path(p)
            else:
                messagebox.showwarning('QNEST', f'This representation has no {ext} export.\nCheck the .error.txt artifact for details.')

    def _save(self):
        base = self._base()
        if not base:
            return
        existing = [base.with_suffix(ext) for ext in ('.html', '.renderer.png', '.qasm', '.json', '.txt') if base.with_suffix(ext).exists()]
        if not existing:
            return
        src = existing[0]
        dest = filedialog.asksaveasfilename(initialfile=src.name, defaultextension=src.suffix, filetypes=[('Current representation', f'*{src.suffix}'), ('All files', '*.*')])
        if dest:
            shutil.copy2(src, dest)
            messagebox.showinfo('Saved', f'Representation copied to:\n{dest}')

class PlotGallery(_Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self._paths = []
        self._image_ref = None
        bar = _frame(self)
        bar.pack(fill='x', pady=(0, 6))
        _label(bar, 'Plot:', font=FM.small).pack(side='left')
        self._choice = ttk.Combobox(bar, state='readonly', width=42)
        self._choice.pack(side='left', padx=8)
        self._choice.bind('<<ComboboxSelected>>', lambda _e: self._show())
        _ghost_button(bar, 'Save plot…', command=self._save, padx=9, pady=4).pack(side='left')
        _ghost_button(bar, 'Open full size', command=self._open, padx=9, pady=4).pack(side='left', padx=6)
        self._holder = tk.Frame(self, bg=C['bg3'])
        self._holder.pack(fill='both', expand=True)
        self._label = tk.Label(self._holder, text='Run AFA/HAMFA to generate plots.', font=FM.small, fg=C['hint'], bg=C['bg3'])
        self._label.pack(fill='both', expand=True)
        self._holder.bind('<Configure>', lambda _e: self._show())

    def set_paths(self, paths, empty_text='Run AFA/HAMFA to generate plots.'):
        self._paths = [Path(p) for p in paths if Path(p).exists()]
        self._choice['values'] = [p.stem for p in self._paths]
        if self._paths:
            self._choice.current(0)
            self._show()
        else:
            self._label.config(image='', text=empty_text)
            self._image_ref = None

    def refresh(self):
        run_dir = self.winfo_toplevel().pipeline.state.run_dir
        paths = sorted((run_dir / '05_run' / 'plots').glob('*.png')) if run_dir else []
        self.set_paths(paths)

    def _selected(self):
        i = self._choice.current()
        return self._paths[i] if 0 <= i < len(self._paths) else None

    def _show(self):
        path = self._selected()
        if not path or not path.exists():
            return
        try:
            from PIL import Image, ImageTk
            im = Image.open(path)
            w = max(300, self._holder.winfo_width() - 20)
            h = max(220, self._holder.winfo_height() - 20)
            im.thumbnail((w, h), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(im)
            self._image_ref = photo
            self._label.config(image=photo, text='')
        except Exception as exc:
            self._label.config(image='', text=f'Preview unavailable: {exc}\nOpen full size to view the plot.')

    def _open(self):
        path = self._selected()
        if path:
            _open_local_path(path)

    def _save(self):
        path = self._selected()
        if not path:
            return
        dest = filedialog.asksaveasfilename(initialfile=path.name, defaultextension=path.suffix, filetypes=[('PNG image', '*.png'), ('All files', '*.*')])
        if dest:
            shutil.copy2(path, dest)
            messagebox.showinfo('Saved', f'Plot copied to:\n{dest}')

class SplashScreen(tk.Toplevel):
    DURATION_MS = 2800
    BAR_STEPS = 100

    def __init__(self, master, animate=True):
        super().__init__(master)
        self.overrideredirect(True)
        self.configure(bg=C['splash_bg'])
        self.attributes('-topmost', True)
        self._animate_enabled = bool(animate)
        self._gif_frames = []
        self._gif_index = 0
        self._gif_after = None
        w, h = (760, 360)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f'{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}')
        self.configure(highlightbackground=C['border'], highlightthickness=1)
        self._build_ui(w, h)
        self._start_progress()

    def _build_ui(self, w, h):
        self._logo_label = tk.Label(self, bg=C['splash_bg'], bd=0)
        self._logo_label.pack(fill='x', padx=34, pady=(34, 6))
        self._load_logo_gif(target_width=670)
        self._status = tk.Label(self, text='Initialising QNEST…', font=('DM Sans', 10), fg=C['muted'], bg=C['splash_bg'])
        self._status.pack(pady=(6, 8))
        bar_wrap = tk.Frame(self, bg=C['splash_bg'])
        bar_wrap.pack(fill='x', padx=86, pady=(0, 8))
        self._bar_canvas = tk.Canvas(bar_wrap, height=5, bg=C['bg3'], highlightthickness=0)
        self._bar_canvas.pack(fill='x')
        self._bar_fill = self._bar_canvas.create_rectangle(0, 0, 0, 5, fill=C['accent'], outline='')
        tk.Label(self, text=f'{APP_NAME}  ·  v{APP_VERSION}', font=('DM Sans', 9), fg=C['hint'], bg=C['splash_bg']).pack(pady=(4, 14))

    def _load_logo_gif(self, target_width=670):
        gif_path = PROJECT_ROOT / 'assets' / 'qnest-logo-splash.gif'
        if not gif_path.exists():
            gif_path = PROJECT_ROOT / 'qnest-logo-core-50fps.gif'
        if not gif_path.exists():
            self._logo_label.config(text=f'{APP_NAME}\n{APP_SUBTITLE}', fg=C['text'], font=('DM Sans', 26, 'bold'), justify='center')
            return
        try:
            from PIL import Image, ImageTk
            im = Image.open(gif_path)
            ratio = target_width / im.width
            target_h = max(1, int(im.height * ratio))
            resampling = getattr(Image, 'Resampling', Image).LANCZOS
            for idx in range(getattr(im, 'n_frames', 1)):
                im.seek(idx)
                frame = im.convert('RGBA')
                if frame.width != target_width:
                    frame = frame.resize((target_width, target_h), resampling)
                self._gif_frames.append(ImageTk.PhotoImage(frame))
            if self._gif_frames:
                self._logo_label.config(image=self._gif_frames[0])
                if self._animate_enabled and len(self._gif_frames) > 1:
                    self._animate_logo()
        except Exception as exc:
            self._logo_label.config(text=f'{APP_NAME}\n{APP_SUBTITLE}\n\nLogo preview unavailable: {exc}', fg=C['text'], bg=C['splash_bg'], font=('DM Sans', 18, 'bold'), justify='center')

    def _animate_logo(self):
        if not self.winfo_exists() or not self._gif_frames:
            return
        self._gif_index = (self._gif_index + 1) % len(self._gif_frames)
        self._logo_label.config(image=self._gif_frames[self._gif_index])
        self._gif_after = self.after(20, self._animate_logo)
    _MESSAGES = ['Loading circuit workspace…', 'Initialising network model…', 'Preparing distribution engine…', 'Connecting scheduling layer…', 'Preparing experiment workspace…']

    def _start_progress(self):
        self._step = 0
        self._tick()

    def _tick(self):
        if self._step > self.BAR_STEPS:
            self._finish()
            return
        pct = self._step / self.BAR_STEPS
        width = max(1, self._bar_canvas.winfo_width())
        self._bar_canvas.coords(self._bar_fill, 0, 0, int(width * pct), 5)
        msg_idx = min(int(pct * len(self._MESSAGES)), len(self._MESSAGES) - 1)
        self._status.config(text=self._MESSAGES[msg_idx])
        self._step += 1
        self.after(self.DURATION_MS // self.BAR_STEPS, self._tick)

    def _finish(self):
        try:
            if self._gif_after:
                self.after_cancel(self._gif_after)
        except Exception:
            pass
        self.destroy()
        self.master.deiconify()

def _panel_header(parent, title, subtitle, accent):
    hdr = _frame(parent, bg=C['bg2'])
    hdr.pack(fill='x', padx=0, pady=0)
    stripe = tk.Frame(hdr, bg=accent, width=4)
    stripe.pack(side='left', fill='y')
    inner = _frame(hdr, bg=C['bg2'])
    inner.pack(side='left', fill='x', expand=True, padx=20, pady=16)
    tk.Label(inner, text=title, font=FM.title, padx=3, fg=accent, bg=C['bg2']).pack(anchor='w')
    subtitle_lbl = tk.Label(inner, text=subtitle, font=FM.body, padx=3, fg=C['muted'], bg=C['bg2'], justify='left', anchor='w')
    subtitle_lbl.pack(anchor='w', fill='x', pady=(2, 0))

    def _sync_wrap(_e=None):
        try:
            subtitle_lbl.config(wraplength=max(260, int(inner.winfo_width()) - 12))
        except Exception:
            pass
    inner.bind('<Configure>', _sync_wrap, add='+')
    hdr.after_idle(_sync_wrap)
    _sep(parent, bg=C['sep']).pack(fill='x')

def _section_label(parent, text, accent, bg=None):
    tk.Label(parent, text=text, font=FM.subh, padx=3, fg=accent, bg=bg or C['bg2']).pack(anchor='w', padx=25, pady=(16, 4))

def _pad_pair(value):
    try:
        if isinstance(value, (tuple, list)):
            parts = [str(v) for v in value]
        else:
            parts = str(value).split()
        nums = [int(float(p)) for p in parts]
        if not nums:
            return (0, 0)
        return (nums[0], nums[-1]) if len(nums) > 1 else (nums[0], nums[0])
    except Exception:
        return (0, 0)

def _internal_border(widget, axis='x'):
    total = 0
    for opt in ('bd', 'highlightthickness', 'padx' if axis == 'x' else 'pady'):
        try:
            total += int(float(widget.cget(opt)))
        except Exception:
            pass
    return total

def _scaled(px):
    try:
        return round(px * max(0.85, min(1.3, FM.ratio)))
    except Exception:
        return px

def _text_extra(widget):
    total = 0
    for opt in ('padx', 'bd', 'highlightthickness'):
        try:
            total += 2 * int(float(widget.cget(opt)))
        except Exception:
            pass
    return total + 4
_FONT_CACHE = {}

def _natural_text_width(widget):
    try:
        text = str(widget.cget('text'))
        spec = widget.cget('font')
        key = str(spec)
        font = _FONT_CACHE.get(key)
        if font is None:
            try:
                font = tkfont.nametofont(spec) if isinstance(spec, str) and ' ' not in spec else tkfont.Font(root=widget, font=spec)
            except Exception:
                font = tkfont.Font(root=widget, font=spec)
            _FONT_CACHE[key] = font
        widest = max((font.measure(line) for line in text.split('\n')), default=0)
        return widest + _text_extra(widget)
    except Exception:
        return widget.winfo_reqwidth()

def _is_true(value):
    return str(value).lower() in {'1', 'true', 'yes'}

def _fluid_available(label):
    try:
        manager = label.winfo_manager()
        if manager == 'pack':
            info = label.pack_info()
            side = str(info.get('side', 'top'))
            if side in ('top', 'bottom'):
                master = info.get('in')
                if not hasattr(master, 'winfo_width'):
                    master = label.nametowidget(str(master))
                width = int(master.winfo_width())
                if width <= 1:
                    return None
                left, right = _pad_pair(info.get('padx', 0))
                ipad = 2 * _pad_pair(info.get('ipadx', 0))[0]
                return width - 2 * _internal_border(master, 'x') - left - right - ipad
            if _is_true(info.get('expand', 0)) and str(info.get('fill', 'none')) in ('x', 'both'):
                width = int(label.winfo_width())
                return width if width > 1 else None
            return None
        if manager == 'grid':
            info = label.grid_info()
            sticky = str(info.get('sticky', ''))
            if 'e' not in sticky or 'w' not in sticky:
                return None
            master = info.get('in')
            if not hasattr(master, 'grid_columnconfigure'):
                master = label.nametowidget(str(master))
            col = int(info.get('column', 0))
            span = int(info.get('columnspan', 1))
            weighted = False
            for c in range(col, col + span):
                try:
                    if int(master.grid_columnconfigure(c).get('weight', 0)) > 0:
                        weighted = True
                        break
                except Exception:
                    pass
            if not weighted and span < 2:
                return None
            width = int(label.winfo_width())
            return width if width > 1 else None
    except Exception:
        return None
    return None

def _fluid_apply(label):
    try:
        if not label.winfo_exists():
            return
        available = _fluid_available(label)
        if available is None:
            return
        wrap = max(80, int(available) - _text_extra(label))
        if _natural_text_width(label) <= available:
            wrap = max(wrap, 1)
        current = int(float(label.cget('wraplength') or 0))
        if abs(current - wrap) > 1:
            label.configure(wraplength=wrap)
        if str(label.cget('justify')) == 'center' and (not isinstance(label, _ProfessionalButton)):
            anchor = str(label.cget('anchor'))
            if label.winfo_manager() == 'pack':
                anchor = str(label.pack_info().get('anchor', anchor))
            if 'w' in anchor:
                label.configure(justify='left')
    except Exception:
        pass

def _fluid_candidate(widget):
    if getattr(widget, '_qnest_fluid', False):
        return False
    if type(widget) is not tk.Label and (not isinstance(widget, _ProfessionalButton)):
        return False
    try:
        if str(widget.cget('image')):
            return False
        text = str(widget.cget('text')).strip()
        has_wrap = int(float(widget.cget('wraplength') or 0)) > 0
    except Exception:
        return False
    if isinstance(widget, _ProfessionalButton):
        try:
            info = widget.pack_info() if widget.winfo_manager() == 'pack' else {}
            if str(info.get('side', 'left')) not in ('top', 'bottom') or str(info.get('fill', 'none')) not in ('x', 'both'):
                return False
        except Exception:
            return False
    if ' ' not in text and (not has_wrap):
        return False
    return has_wrap or _natural_text_width(widget) >= _scaled(230)

def _fluid_master_changed(event):
    for label in list(getattr(event.widget, '_qnest_fluid_labels', ())):
        try:
            if label.winfo_exists():
                _fluid_apply(label)
            else:
                event.widget._qnest_fluid_labels.discard(label)
        except Exception:
            try:
                event.widget._qnest_fluid_labels.discard(label)
            except Exception:
                pass

def _fluid_register(label):
    label._qnest_fluid = True
    try:
        label.bind('<Configure>', lambda _e, w=label: _fluid_apply(w), add='+')
        master = label.master
        if master is not None:
            if not hasattr(master, '_qnest_fluid_labels'):
                master._qnest_fluid_labels = set()
                master.bind('<Configure>', _fluid_master_changed, add='+')
            master._qnest_fluid_labels.add(label)
    except Exception:
        pass
    _fluid_apply(label)

def _fluid_wrap_tree(widget):
    try:
        children = widget.winfo_children()
    except Exception:
        return
    for child in children:
        if isinstance(child, tk.Toplevel):
            continue
        try:
            if _fluid_candidate(child):
                _fluid_register(child)
            elif getattr(child, '_qnest_fluid', False):
                _fluid_apply(child)
        except Exception:
            pass
        _fluid_wrap_tree(child)

def _flow_container_changed(event):
    flow = getattr(event.widget, '_qnest_flow', None)
    if flow is not None:
        flow.schedule()

class _FlowLayout:

    def __init__(self, container, specs, gap_y=6, report_width=False):
        self.container = container
        self.gap_y = gap_y
        self.report_width = report_width
        self.specs = []
        self._job = None
        container._qnest_flow = self
        if not getattr(container, '_qnest_flow_bound', False):
            container._qnest_flow_bound = True
            container.bind('<Configure>', _flow_container_changed, add='+')
        for spec in specs:
            self.add(spec)
        self.relayout()

    def add(self, spec):
        if not isinstance(spec, dict):
            spec = {'widget': spec}
        widget = spec['widget']
        for forget in ('pack_forget', 'grid_forget'):
            try:
                getattr(widget, forget)()
            except Exception:
                pass
        spec.setdefault('ml', 0)
        spec.setdefault('mr', 0)
        spec.setdefault('mt', 0)
        spec.setdefault('mb', 0)
        widget.bind('<Configure>', lambda _e: self.schedule(), add='+')
        self.specs.append(spec)

    def schedule(self, _event=None):
        if self._job is None:
            try:
                self._job = self.container.after_idle(self.relayout)
            except Exception:
                self._job = None

    def _live(self):
        out = []
        for spec in self.specs:
            try:
                if not spec['widget'].winfo_exists():
                    continue
            except Exception:
                continue
            visible = spec.get('visible')
            if callable(visible):
                try:
                    if not visible():
                        spec['widget'].place_forget()
                        continue
                except Exception:
                    pass
            out.append(spec)
        return out

    def relayout(self):
        self._job = None
        c = self.container
        try:
            if not c.winfo_exists():
                return
            cw = int(c.winfo_width())
        except Exception:
            return
        bx = _internal_border(c, 'x')
        by = _internal_border(c, 'y')
        items = self._live()
        for s in items:
            w = s['widget']
            nat = _natural_text_width(w) if s.get('wrap') else int(w.winfo_reqwidth())
            if s.get('stretch'):
                mn = min(nat, s.get('minw') or _scaled(170))
            elif s.get('wrap') or s.get('shrink'):
                mn = min(nat, s.get('minw') or _scaled(200))
            else:
                mn = nat
            s['_nat'] = nat
            s['_min'] = mn
            s['_m'] = s['ml'] + s['mr']
        natural_total = sum((s['_nat'] + s['_m'] for s in items))
        if self.report_width:
            try:
                want = natural_total + 2 * bx
                if int(float(c.cget('width') or 0)) != want:
                    c.configure(width=want)
            except Exception:
                pass
        avail = cw - 2 * bx if cw > 1 else natural_total
        avail = max(1, avail)
        blocks, cur = ([], [])
        for s in items:
            cur.append(s)
            if not s.get('glue'):
                blocks.append(cur)
                cur = []
        if cur:
            blocks.append(cur)
        rows, row, used = ([], [], 0)
        for blk in blocks:
            bmin = sum((s['_min'] + s['_m'] for s in blk))
            if row and (used + bmin > avail or blk[0].get('brk')):
                rows.append(row)
                row, used = ([], 0)
            row.extend(blk)
            used += bmin
        if row:
            rows.append(row)
        y = 0
        for row in rows:
            widths = [s['_min'] if s.get('stretch') else s['_nat'] for s in row]
            over = sum(widths) + sum((s['_m'] for s in row)) - avail
            extra = 0
            if over > 0:
                for i, s in enumerate(row):
                    if over <= 0:
                        break
                    if s.get('wrap') or s.get('shrink'):
                        take = min(widths[i] - s['_min'], over)
                        widths[i] -= take
                        over -= take
                if over > 0 and len(row) == 1:
                    widths[0] = max(1, avail - row[0]['_m'])
            else:
                extra = -over
                stretch = [i for i, s in enumerate(row) if s.get('stretch')]
                if stretch:
                    share, rem = divmod(extra, len(stretch))
                    for k, i in enumerate(stretch):
                        widths[i] += share + (1 if k < rem else 0)
                    extra = 0
            for i, s in enumerate(row):
                if s.get('wrap'):
                    w = s['widget']
                    wrap = max(1, widths[i] - _text_extra(w))
                    if widths[i] >= s['_nat']:
                        wrap = max(wrap, s['_nat'])
                    try:
                        if abs(int(float(w.cget('wraplength') or 0)) - wrap) > 1:
                            w.configure(wraplength=wrap)
                    except Exception:
                        pass
            heights = [int(s['widget'].winfo_reqheight()) + s['mt'] + s['mb'] for s in row if not s.get('fill_y')]
            rh = max(heights) if heights else max((int(s['widget'].winfo_reqheight()) for s in row))
            x = 0
            for i, s in enumerate(row):
                if s.get('push') and extra > 0:
                    x += extra
                    extra = 0
                x += s['ml']
                w = s['widget']
                inner = rh - s['mt'] - s['mb']
                if s.get('fill_y'):
                    h, yy = (inner, y + s['mt'])
                else:
                    h = int(w.winfo_reqheight())
                    yy = y + s['mt'] + max(0, (inner - h) // 2)
                sized = s.get('stretch') or s.get('fill_y') or widths[i] != int(w.winfo_reqwidth())
                try:
                    w.place(x=x, y=yy, width=widths[i] if sized else '', height=h if s.get('fill_y') else '', anchor='nw')
                except Exception:
                    pass
                x += widths[i] + s['mr']
            y += rh + self.gap_y
        total = max(1, y - self.gap_y if rows else 1) + 2 * by
        try:
            if int(float(c.cget('height') or 0)) != total:
                c.configure(height=total)
        except Exception:
            pass

def _flow_from_pack(frame, gap_y=6, report_width=False, overrides=None):
    left, right = ([], [])
    overrides = overrides or {}
    for w in frame.pack_slaves():
        info = w.pack_info()
        side = str(info.get('side', 'top'))
        ml, mr = _pad_pair(info.get('padx', 0))
        mt, mb = _pad_pair(info.get('pady', 0))
        fill = str(info.get('fill', 'none'))
        spec = {'widget': w, 'ml': ml, 'mr': mr, 'mt': mt, 'mb': mb}
        if fill in ('y', 'both') and w.winfo_class() == 'Frame' and (int(float(w.cget('width') or 0)) <= 4):
            spec['fill_y'] = True
        elif _is_true(info.get('expand', 0)) and fill in ('x', 'both'):
            spec['stretch'] = True
            if type(w) is tk.Label:
                spec['wrap'] = True
        elif type(w) is tk.Label:
            try:
                if ' ' in str(w.cget('text')) and _natural_text_width(w) > _scaled(180):
                    spec['wrap'] = True
            except Exception:
                pass
        spec.update(overrides.get(w, {}))
        (right if side == 'right' else left).append(spec)
    right.reverse()
    if right:
        right[0]['push'] = True
    return _FlowLayout(frame, left + right, gap_y=gap_y, report_width=report_width)

def _fit_columns(available, widths, gap=0, choices=(4, 3, 2)):
    n = len(widths)
    for cols in choices:
        if cols > n or cols < 2:
            continue
        need = sum((max(widths[c::cols]) for c in range(cols))) + gap * (cols - 1)
        if need <= available:
            return cols
    return 1

def _responsive_body_wheel(event):
    try:
        widget = event.widget.winfo_containing(event.x_root, event.y_root)
    except Exception:
        return
    while widget is not None:
        if isinstance(widget, _ResponsiveBody):
            if widget._overflow:
                if getattr(event, 'num', None) == 4:
                    step = -3
                elif getattr(event, 'num', None) == 5:
                    step = 3
                else:
                    delta = int(getattr(event, 'delta', 0) or 0)
                    step = -int(delta / 120) * 3 if abs(delta) >= 120 else -1 if delta > 0 else 1
                widget._canvas.yview_scroll(step, 'units')
            return
        if isinstance(widget, tk.Canvas) and isinstance(getattr(widget, 'master', None), _ResponsiveBody):
            widget = widget.master
            continue
        if isinstance(widget, (tk.Text, tk.Listbox, tk.Canvas, ttk.Treeview, tk.Spinbox, ttk.Combobox, tk.Toplevel)):
            return
        widget = getattr(widget, 'master', None)

class _ResponsiveBody(tk.Frame):
    _wheel_bound = False

    def __init__(self, parent, flex_min=300, bg=None):
        bg = bg or C['bg2']
        super().__init__(parent, bg=bg)
        self._flex_min = flex_min
        self._overflow = False
        self._job = None
        self._watched = set()
        self._canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0, yscrollincrement=20)
        self._canvas.pack(fill='both', expand=True)
        self._vsb = ttk.Scrollbar(self, orient='vertical', command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._vsb.set)
        self.inner = tk.Frame(self._canvas, bg=bg)
        self._win = self._canvas.create_window(0, 0, window=self.inner, anchor='nw')
        self._canvas.bind('<Configure>', self.schedule, add='+')
        self.inner.bind('<Configure>', self.schedule, add='+')
        if not _ResponsiveBody._wheel_bound:
            _ResponsiveBody._wheel_bound = True
            for seq in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
                self.bind_all(seq, _responsive_body_wheel, add='+')

    def schedule(self, _event=None):
        if self._job is None:
            try:
                self._job = self.after_idle(self._sync)
            except Exception:
                self._job = None

    def _needed(self):
        total = 0
        for child in self.inner.pack_slaves():
            if str(child) not in self._watched:
                self._watched.add(str(child))
                child.bind('<Configure>', self.schedule, add='+')
            info = child.pack_info()
            top, bottom = _pad_pair(info.get('pady', 0))
            if _is_true(info.get('expand', 0)):
                h = _scaled(self._flex_min)
            else:
                h = int(child.winfo_reqheight())
            total += h + top + bottom
        return total

    def _sync(self):
        self._job = None
        try:
            cw, ch = (int(self._canvas.winfo_width()), int(self._canvas.winfo_height()))
        except Exception:
            return
        if cw <= 1 or ch <= 1:
            return
        need = self._needed()
        overflow = need > ch + 1
        height = need if overflow else ch
        self._canvas.itemconfigure(self._win, width=cw, height=height)
        self._canvas.configure(scrollregion=(0, 0, cw, height))
        if overflow:
            self._vsb.place(relx=1.0, rely=0, relheight=1.0, anchor='ne')
            self._vsb.lift()
        elif self._overflow or self._vsb.winfo_manager():
            self._vsb.place_forget()
            self._canvas.yview_moveto(0)
        self._overflow = overflow

class _QasmCircuitCanvas(tk.Frame):
    WIRE_GAP = 34
    GATE_GAP = 64
    LEFT = 92
    TOP = 30
    BOX_W = 42
    BOX_H = 24

    def __init__(self, parent):
        super().__init__(parent, bg=C['bg3'])
        self._cv = tk.Canvas(self, bg=C['bg3'], highlightthickness=0, xscrollincrement=20, yscrollincrement=20)
        self._xbar = ttk.Scrollbar(self, orient='horizontal', command=self._cv.xview)
        self._ybar = ttk.Scrollbar(self, orient='vertical', command=self._cv.yview)
        self._cv.configure(xscrollcommand=self._xbar.set, yscrollcommand=self._ybar.set)
        self._ybar.pack(side='right', fill='y')
        self._xbar.pack(side='bottom', fill='x')
        self._cv.pack(side='left', fill='both', expand=True)
        self._qasm = ''
        self._cv.bind('<Configure>', self._on_resize)
        self._draw_empty('Generate a benchmark to preview its circuit here.')

    def _on_resize(self, _event=None):
        if not self._qasm and (not self._cv.find_all()):
            self._draw_empty('Generate a benchmark to preview its circuit here.')

    def _draw_empty(self, text):
        self._cv.delete('all')
        self._cv.create_text(24, 24, text=text, anchor='nw', fill=C['muted'], font=FM.small)
        self._cv.configure(scrollregion=(0, 0, 600, 260))

    @staticmethod
    def _clean_qasm(qasm):
        statements = []
        in_gate_def = False
        brace_depth = 0
        for raw in qasm.splitlines():
            line = raw.split('//', 1)[0].strip()
            if not line:
                continue
            low = line.lower()
            if in_gate_def:
                brace_depth += line.count('{') - line.count('}')
                if brace_depth <= 0:
                    in_gate_def = False
                continue
            if low.startswith('gate ') or low.startswith('opaque '):
                if '{' in line and '}' not in line:
                    in_gate_def = True
                    brace_depth = line.count('{') - line.count('}')
                continue
            statements.append(line)
        return statements

    @classmethod
    def _parse(cls, qasm):
        stmts = cls._clean_qasm(qasm)
        registers = {}
        labels = []
        offset = 0
        for line in stmts:
            m = re.match('qreg\\s+([A-Za-z_]\\w*)\\[(\\d+)\\]\\s*;', line, re.I)
            if not m:
                m3 = re.match('qubit\\[(\\d+)\\]\\s+([A-Za-z_]\\w*)\\s*;', line, re.I)
                if m3:
                    size, name = (int(m3.group(1)), m3.group(2))
                    registers[name] = (offset, size)
                    labels.extend([f'{name}[{i}]' for i in range(size)])
                    offset += size
                continue
            name, size = (m.group(1), int(m.group(2)))
            registers[name] = (offset, size)
            labels.extend([f'{name}[{i}]' for i in range(size)])
            offset += size

        def qindex(reg, idx):
            if reg not in registers:
                return None
            base, size = registers[reg]
            i = int(idx)
            return base + i if 0 <= i < size else None
        ops = []
        skip_prefixes = ('openqasm', 'include', 'qreg', 'creg', 'qubit', 'bit')
        for line in stmts:
            low = line.lower()
            if low.startswith(skip_prefixes):
                continue
            line2 = re.sub('^if\\s*\\([^)]*\\)\\s*', '', line, flags=re.I)
            low2 = line2.lower()
            if low2.startswith('measure'):
                qs = [(qindex(a, b), f'{a}[{b}]') for a, b in re.findall('([A-Za-z_]\\w*)\\[(\\d+)\\]', line2)]
                qids = [q for q, _ in qs if q is not None]
                if qids:
                    ops.append(('measure', 'M', qids))
                continue
            if low2.startswith('barrier'):
                qids = []
                indexed = re.findall('([A-Za-z_]\\w*)\\[(\\d+)\\]', line2)
                for a, b in indexed:
                    qi = qindex(a, b)
                    if qi is not None:
                        qids.append(qi)
                if not qids:
                    tail = line2[len('barrier'):].rstrip(';').strip()
                    for name in [x.strip() for x in tail.split(',') if x.strip()]:
                        if name in registers:
                            base, size = registers[name]
                            qids.extend(range(base, base + size))
                if qids:
                    ops.append(('barrier', '│', sorted(set(qids))))
                continue
            m = re.match('([A-Za-z_]\\w*)\\s*(\\([^;]*\\))?\\s+(.+?)\\s*;\\s*$', line2)
            if not m:
                continue
            gate, params, operands = (m.group(1), m.group(2), m.group(3))
            qids = []
            for a, b in re.findall('([A-Za-z_]\\w*)\\[(\\d+)\\]', operands):
                qi = qindex(a, b)
                if qi is not None:
                    qids.append(qi)
            if not qids:
                continue
            label = gate.upper()
            if params:
                compact = re.sub('\\s+', '', params)
                label += compact if len(compact) <= 18 else '(…)'
            ops.append((gate.lower(), label, qids))
        return (labels, ops)

    def render_qasm(self, qasm):
        self._qasm = qasm or ''
        self._cv.delete('all')
        if not self._qasm.strip():
            self._draw_empty('No QASM available for this generated circuit.')
            return
        labels, ops = self._parse(self._qasm)
        if not labels:
            self._draw_empty('QNEST could not find a qubit register in this QASM.')
            return
        n = len(labels)
        width = max(760, self.LEFT + 80 + max(1, len(ops)) * self.GATE_GAP)
        height = max(260, self.TOP * 2 + max(1, n - 1) * self.WIRE_GAP + 50)
        for qi, label in enumerate(labels):
            y = self.TOP + qi * self.WIRE_GAP
            self._cv.create_text(self.LEFT - 12, y, text=label, anchor='e', fill=C['text'], font=FM.small_mono)
            self._cv.create_line(self.LEFT, y, width - 36, y, fill=C['border'], width=1.2)
        self._cv.create_text(self.LEFT, height - 18, text='Native QNEST preview • horizontal scroll reveals the complete circuit', anchor='w', fill=C['muted'], font=FM.small)

        def yof(q):
            return self.TOP + q * self.WIRE_GAP
        for col, (gate, label, qids) in enumerate(ops):
            x = self.LEFT + 45 + col * self.GATE_GAP
            uniq = list(dict.fromkeys(qids))
            if gate == 'barrier':
                ys = [yof(q) for q in uniq]
                self._cv.create_line(x, min(ys) - 15, x, max(ys) + 15, fill=C['hint'], dash=(3, 3), width=1.2)
                continue
            if gate in {'cx', 'cnot'} and len(uniq) >= 2:
                c, t = (uniq[0], uniq[1])
                yc, yt = (yof(c), yof(t))
                self._cv.create_line(x, yc, x, yt, fill=C['accent'], width=1.8)
                self._cv.create_oval(x - 4, yc - 4, x + 4, yc + 4, fill=C['accent'], outline=C['accent'])
                r = 10
                self._cv.create_oval(x - r, yt - r, x + r, yt + r, outline=C['accent'], width=1.8, fill=C['bg2'])
                self._cv.create_line(x - r + 3, yt, x + r - 3, yt, fill=C['accent'], width=1.6)
                self._cv.create_line(x, yt - r + 3, x, yt + r - 3, fill=C['accent'], width=1.6)
                continue
            if gate == 'cz' and len(uniq) >= 2:
                ys = [yof(q) for q in uniq[:2]]
                self._cv.create_line(x, min(ys), x, max(ys), fill=C['accent'], width=1.8)
                for yy in ys:
                    self._cv.create_oval(x - 4, yy - 4, x + 4, yy + 4, fill=C['accent'], outline=C['accent'])
                continue
            if gate == 'swap' and len(uniq) >= 2:
                ys = [yof(q) for q in uniq[:2]]
                self._cv.create_line(x, min(ys), x, max(ys), fill=C['comm'], width=1.7)
                for yy in ys:
                    self._cv.create_line(x - 7, yy - 7, x + 7, yy + 7, fill=C['comm'], width=1.7)
                    self._cv.create_line(x - 7, yy + 7, x + 7, yy - 7, fill=C['comm'], width=1.7)
                continue
            if gate == 'measure':
                for q in uniq:
                    yy = yof(q)
                    self._box(x, yy, 'M', C['success'])
                continue
            if len(uniq) == 1:
                self._box(x, yof(uniq[0]), label, C['accent'])
            else:
                ys = [yof(q) for q in uniq]
                self._cv.create_line(x, min(ys), x, max(ys), fill=C['comm'], width=1.5)
                for q in uniq:
                    self._box(x, yof(q), label if len(label) <= 9 else gate.upper(), C['comm'])
        self._cv.configure(scrollregion=(0, 0, width, height))
        self._cv.xview_moveto(0.0)
        self._cv.yview_moveto(0.0)

    def _box(self, x, y, text, outline):
        w, h = (self.BOX_W, self.BOX_H)
        display = text if len(text) <= 10 else text[:9] + '…'
        self._cv.create_rectangle(x - w / 2, y - h / 2, x + w / 2, y + h / 2, fill=C['bg2'], outline=outline, width=1.5)
        self._cv.create_text(x, y, text=display, fill=C['text'], font=FM.small_mono)

class _ExactPytketCircuitCanvas(tk.Frame):
    MIN_VIEW_HEIGHT = 390

    def __init__(self, parent):
        super().__init__(parent, bg=C['bg3'], height=self.MIN_VIEW_HEIGHT)
        self.pack_propagate(False)
        self._photo = None
        self._source_image = None
        self._mode = 'empty'
        self._view_mode = 'fill'
        self._resize_after = None
        status_row = tk.Frame(self, bg=C['bg3'])
        status_row.pack(fill='x')
        self._notice = tk.Label(status_row, text='', font=FM.small, fg=C['muted'], bg=C['bg3'], anchor='w', padx=8, pady=5)
        self._notice.pack(side='left', fill='x', expand=True)
        self._fill_btn = _segmented_button(status_row, 'Fill', command=lambda: self._set_view_mode('fill'), selected=True, padx=10, pady=3)
        self._fill_btn.pack(side='right', padx=(4, 8), pady=3)
        self._actual_btn = _segmented_button(status_row, '100%', command=lambda: self._set_view_mode('100'), padx=10, pady=3)
        self._actual_btn.pack(side='right', pady=3)
        _flow_from_pack(status_row, gap_y=2)
        self._body = tk.Frame(self, bg=C['bg3'], height=self.MIN_VIEW_HEIGHT - 34)
        self._body.pack(fill='both', expand=True)
        self._body.pack_propagate(False)
        self._image_holder = tk.Frame(self._body, bg='#FFFFFF')
        self._image_holder.grid_rowconfigure(0, weight=1)
        self._image_holder.grid_columnconfigure(0, weight=1)
        self._image_canvas = tk.Canvas(self._image_holder, bg='#FFFFFF', highlightthickness=0, xscrollincrement=24, yscrollincrement=24, height=self.MIN_VIEW_HEIGHT - 54)
        self._xbar = ttk.Scrollbar(self._image_holder, orient='horizontal', command=self._image_canvas.xview)
        self._ybar = ttk.Scrollbar(self._image_holder, orient='vertical', command=self._image_canvas.yview)
        self._image_canvas.configure(xscrollcommand=self._xbar.set, yscrollcommand=self._ybar.set)
        self._image_canvas.grid(row=0, column=0, sticky='nsew')
        self._ybar.grid(row=0, column=1, sticky='ns')
        self._xbar.grid(row=1, column=0, sticky='ew')
        tk.Frame(self._image_holder, width=16, height=16, bg=C['bg3']).grid(row=1, column=1, sticky='nsew')
        self._image_canvas.bind('<MouseWheel>', self._on_mousewheel)
        self._image_canvas.bind('<Shift-MouseWheel>', self._on_shift_mousewheel)
        self._image_canvas.bind('<Button-4>', lambda _e: self._image_canvas.yview_scroll(-3, 'units'))
        self._image_canvas.bind('<Button-5>', lambda _e: self._image_canvas.yview_scroll(3, 'units'))
        self._image_canvas.bind('<Configure>', self._on_canvas_configure)
        self._fallback = _QasmCircuitCanvas(self._body)
        self._show_empty()

    def _hide_bodies(self):
        self._image_holder.pack_forget()
        self._fallback.pack_forget()

    def _show_empty(self, text='Generate or compile a circuit to view it here.'):
        self._hide_bodies()
        self._notice.config(text=text)
        self._image_canvas.delete('all')
        self._photo = None
        self._source_image = None
        self._mode = 'empty'
        self._update_view_buttons()

    @staticmethod
    def _wheel_units(delta):
        try:
            d = float(delta)
        except Exception:
            return 0
        if d == 0:
            return 0
        if abs(d) < 120:
            return -1 if d > 0 else 1
        return int(-d / 120) * 3

    def _on_mousewheel(self, event):
        units = self._wheel_units(getattr(event, 'delta', 0))
        if units:
            self._image_canvas.yview_scroll(units, 'units')
        return 'break'

    def _on_shift_mousewheel(self, event):
        units = self._wheel_units(getattr(event, 'delta', 0))
        if units:
            self._image_canvas.xview_scroll(units, 'units')
        return 'break'

    def _on_canvas_configure(self, _event=None):
        if self._mode != 'pytket' or self._source_image is None:
            return
        if self._resize_after is not None:
            try:
                self.after_cancel(self._resize_after)
            except Exception:
                pass
        self._resize_after = self.after(80, self._redraw_snapshot)

    def _set_view_mode(self, mode):
        if mode not in {'fill', '100'}:
            return
        self._view_mode = mode
        self._update_view_buttons()
        self._redraw_snapshot(reset_scroll=True)

    def _update_view_buttons(self):
        if not hasattr(self, '_fill_btn'):
            return
        self._fill_btn.config(fg=C['accent'] if self._view_mode == 'fill' else C['muted'], bg=C['bg2'])
        self._actual_btn.config(fg=C['accent'] if self._view_mode == '100' else C['muted'], bg=C['bg2'])
        state = 'normal' if self._mode == 'pytket' else 'disabled'
        self._fill_btn.config(state=state)
        self._actual_btn.config(state=state)

    def _redraw_snapshot(self, reset_scroll=False):
        self._resize_after = None
        if self._source_image is None or self._mode != 'pytket':
            return
        try:
            from PIL import Image, ImageTk
            source = self._source_image
            iw, ih = source.size
            self._image_canvas.update_idletasks()
            cw = max(100, self._image_canvas.winfo_width())
            ch = max(100, self._image_canvas.winfo_height())
            if self._view_mode == '100':
                scale = 1.0
            else:
                scale = max(cw / max(1, iw), ch / max(1, ih))
                scale = max(0.08, min(4.0, scale))
            dw = max(1, int(round(iw * scale)))
            dh = max(1, int(round(ih * scale)))
            if (dw, dh) == (iw, ih):
                display = source
            else:
                display = source.resize((dw, dh), Image.Resampling.LANCZOS)
            self._photo = ImageTk.PhotoImage(display)
            self._image_canvas.delete('all')
            self._image_canvas.create_image(0, 0, image=self._photo, anchor='nw')
            self._image_canvas.configure(scrollregion=(0, 0, dw, dh))
            if reset_scroll:
                self._image_canvas.xview_moveto(0.0)
                self._image_canvas.yview_moveto(0.0)
        except Exception as exc:
            self._notice.config(text=f'Could not resize exact pytket preview: {exc}')

    def show(self, *, snapshot_path=None, qasm_path=None, qasm_text=None, html_path=None, error=None):
        snapshot = Path(snapshot_path) if snapshot_path else None
        if snapshot is not None and snapshot.exists():
            try:
                from PIL import Image
                try:
                    from src.circuit_visuals import validate_pytket_snapshot
                    valid_snapshot, snapshot_reason = validate_pytket_snapshot(snapshot)
                    if not valid_snapshot:
                        raise ValueError(snapshot_reason or 'renderer snapshot is blank')
                except ImportError:
                    pass
                with Image.open(snapshot) as im:
                    image = im.convert('RGB').copy()
                    iw, ih = image.size
                    if iw < 160 or ih < 80:
                        raise ValueError(f'renderer snapshot is invalid ({iw}×{ih} px)')
                self._hide_bodies()
                self._source_image = image
                self._mode = 'pytket'
                self._image_holder.pack(fill='both', expand=True)
                self.update_idletasks()
                self._body.update_idletasks()
                self._image_holder.update_idletasks()
                self._notice.config(text='Exact pytket renderer • responsive interactive HTML is also saved' if html_path else 'Exact pytket renderer')
                self._update_view_buttons()
                self.after_idle(lambda: self._redraw_snapshot(reset_scroll=True))
                return
            except Exception as exc:
                error = error or f'Could not load pytket renderer snapshot: {exc}'
        qasm = qasm_text
        if qasm is None and qasm_path:
            try:
                qasm = Path(qasm_path).read_text(encoding='utf-8', errors='replace')
            except Exception:
                qasm = None
        self._hide_bodies()
        self._source_image = None
        if qasm:
            self._fallback.pack(fill='both', expand=True)
            self._fallback.render_qasm(qasm)
            suffix = f' ({error})' if error else ''
            self._notice.config(text='Native fallback preview • responsive pytket HTML can be opened separately' + suffix)
            self._mode = 'fallback'
            self._update_view_buttons()
        else:
            self._show_empty(error or 'No circuit representation is available.')

class CircuitPanel(_Frame):
    SCALABLE = ['Amplitude Estimation (AE)', 'Deutsch-Jozsa', 'Graph State', 'GHZ State', "Grover's (no ancilla)", "Grover's (v-chain)", 'Portfolio Optimization with QAOA', 'Portfolio Optimization with VQE', 'Quantum Approximation Optimization Algorithm (QAOA)', 'Quantum Fourier Transformation (QFT)', 'QFT Entangled', 'Quantum Neural Network (QNN)', 'Quantum Phase Estimation (QPE) exact', 'Quantum Phase Estimation (QPE) inexact', 'Quantum Walk (no ancilla)', 'Quantum Walk (v-chain)', 'Random Circuit', 'Variational Quantum Eigensolver (VQE)', 'Efficient SU2 ansatz with Random Parameters', 'Real Amplitudes ansatz with Random Parameters', 'Two Local ansatz with Random Parameters', 'W-State']
    NON_SCALABLE = ['Ground State', 'Pricing Call Option', 'Pricing Put Option', 'Routing', "Shor's", 'Travelling Salesman']

    def __init__(self, parent):
        super().__init__(parent)
        self._active_tab = tk.StringVar(value='Import')
        self._tab_frames = {}
        self._workflow_mode = tk.StringVar(value='Single circuit')
        self._circuits = {}
        self._circuit_order = []
        self._active_circuit_id = None
        self._record_counter = 0
        self._editor_loading = False
        self._mqt_validation_signature = None
        self._mqt_validation_result = None
        self._build()

    def is_batch_mode(self):
        return self._workflow_mode.get() == 'Batch / sweep'

    def _new_record_id(self):
        self._record_counter += 1
        return f'circuit_{self._record_counter:04d}'

    @staticmethod
    def _basic_qasm_stats(qasm):
        try:
            labels, ops = _QasmCircuitCanvas._parse(qasm)
            gates = [op for op in ops if op[0] != 'barrier']
            cx = sum((1 for op in gates if op[0] in {'cx', 'cnot'}))
            return {'qubits': len(labels), 'gates': len(gates), 'depth': None, 'cx': cx}
        except Exception:
            return {'qubits': None, 'gates': None, 'depth': None, 'cx': None}

    def _unique_name(self, name):
        base = re.sub('[^A-Za-z0-9._-]+', '_', str(name).strip()).strip('_') or 'circuit'
        used = {r.get('name') for r in self._circuits.values()}
        if base not in used:
            return base
        i = 2
        while f'{base}_{i}' in used:
            i += 1
        return f'{base}_{i}'

    def _add_circuit(self, *, name, qasm_text, source, path=None, benchmark=None, series=None, qubits=None, gates=None, depth=None, renderer_row=None, replace_single=False):
        if replace_single:
            self._circuits.clear()
            self._circuit_order.clear()
            self._active_circuit_id = None
        rid = self._new_record_id()
        stats = self._basic_qasm_stats(qasm_text)
        record = {'id': rid, 'name': self._unique_name(name), 'source': source, 'path': str(path) if path else None, 'qasm_text': qasm_text, 'benchmark': benchmark, 'series': series or benchmark or source, 'qubits': int(qubits) if qubits not in (None, '') else stats.get('qubits'), 'gates': int(gates) if gates not in (None, '') else stats.get('gates'), 'depth': int(depth) if depth not in (None, '') else stats.get('depth'), 'cx': stats.get('cx'), 'renderer_row': dict(renderer_row or {})}
        self._circuits[rid] = record
        self._circuit_order.append(rid)
        self._refresh_circuit_selectors()
        return record

    def _save_editor_to_active(self):
        if self._editor_loading or not self._active_circuit_id:
            return
        rec = self._circuits.get(self._active_circuit_id)
        if rec is None or not hasattr(self, '_editor_text'):
            return
        text = self._editor_text.get('1.0', 'end').rstrip() + '\n'
        rec['qasm_text'] = text
        stats = self._basic_qasm_stats(text)
        for key in ('qubits', 'gates', 'depth', 'cx'):
            if stats.get(key) is not None:
                rec[key] = stats[key]

    def get_circuit_records(self):
        self._save_editor_to_active()
        return [self._circuits[rid] for rid in self._circuit_order if rid in self._circuits]

    def get_active_record(self):
        self._save_editor_to_active()
        return self._circuits.get(self._active_circuit_id) if self._active_circuit_id else None

    def _circuit_label(self, rec):
        q = rec.get('qubits')
        qtxt = f'{q}q' if q not in (None, '') else '?q'
        return f"{rec.get('name', 'circuit')}  •  {qtxt}  •  {rec.get('source', '')}"

    def _refresh_circuit_selectors(self):
        records = [self._circuits[r] for r in self._circuit_order if r in self._circuits]
        labels = [self._circuit_label(r) for r in records]
        self._selector_ids = [r['id'] for r in records]
        for attr in ('_import_choice', '_editor_choice'):
            widget = getattr(self, attr, None)
            if widget is not None:
                widget['values'] = labels
                if self._active_circuit_id in self._selector_ids:
                    widget.current(self._selector_ids.index(self._active_circuit_id))
                elif labels:
                    widget.current(0)
        tree = getattr(self, '_import_tree', None)
        if tree is not None:
            tree.delete(*tree.get_children())
            for rec in records:
                tree.insert('', 'end', iid=rec['id'], values=(rec.get('name'), rec.get('source'), rec.get('qubits') or '—', rec.get('gates') or '—', rec.get('depth') or '—'))
        self._update_mode_widgets()

    def activate_record(self, rid, *, notify_root=True):
        if rid not in self._circuits:
            return
        self._save_editor_to_active()
        self._active_circuit_id = rid
        rec = self._circuits[rid]
        self._editor_loading = True
        try:
            if hasattr(self, '_editor_text'):
                self._editor_text.delete('1.0', 'end')
                self._editor_text.insert('1.0', rec.get('qasm_text', ''))
            if hasattr(self, '_import_path'):
                self._import_path.set(rec.get('path') or rec.get('name') or 'Circuit')
            if hasattr(self, '_import_preview'):
                self._import_preview.config(state='normal')
                self._import_preview.delete('1.0', 'end')
                self._import_preview.insert('1.0', rec.get('qasm_text', ''))
                self._import_preview.config(state='disabled')
            stats_map = {'Qubits': 'qubits', 'Gates': 'gates', 'Depth': 'depth', 'CX count': 'cx'}
            for label, key in stats_map.items():
                if hasattr(self, '_stat_vars') and label in self._stat_vars:
                    val = rec.get(key)
                    self._stat_vars[label].set('—' if val in (None, '') else str(val))
            self._refresh_circuit_selectors()
        finally:
            self._editor_loading = False
        if notify_root:
            root = self.winfo_toplevel()
            if hasattr(root, 'activate_circuit'):
                root.activate_circuit(rid, create=False)

    def _on_selector_changed(self, which='editor'):
        widget = self._editor_choice if which == 'editor' else self._import_choice
        idx = widget.current()
        if 0 <= idx < len(getattr(self, '_selector_ids', [])):
            self.activate_record(self._selector_ids[idx])

    def _remove_active_record(self):
        rid = self._active_circuit_id
        if not rid:
            return
        self._circuits.pop(rid, None)
        self._circuit_order = [x for x in self._circuit_order if x != rid]
        self._active_circuit_id = self._circuit_order[0] if self._circuit_order else None
        self._refresh_circuit_selectors()
        if self._active_circuit_id:
            self.activate_record(self._active_circuit_id)
        else:
            self._editor_loading = True
            self._editor_text.delete('1.0', 'end')
            self._editor_text.insert('1.0', '// QASM will appear here after import or generation\n')
            self._editor_loading = False

    def _build(self):
        _panel_header(self, '◈  Circuit', 'Import a circuit, generate one via MQT Bench, or edit QASM directly.', C['accent'])
        mode = _card(self, padx=14, pady=9)
        mode.pack(fill='x', padx=28, pady=(12, 8))
        self._mode_card = mode
        self._mode_title = _label(mode, 'Circuit workflow:', font=FM.subh, fg=C['text'])
        self._mode_title.grid(row=0, column=0, sticky='w')
        self._mode_radios = []
        for col, text in enumerate(('Single circuit', 'Batch / sweep'), start=1):
            rb = tk.Radiobutton(mode, text=text, variable=self._workflow_mode, value=text, command=self._on_mode_changed, font=FM.small, bg=C['bg2'], fg=C['text'], selectcolor=C['bg3'], activebackground=C['bg4'], activeforeground=C['text'], disabledforeground=C['muted'])
            rb.grid(row=0, column=col, sticky='w', padx=(16, 0))
            self._mode_radios.append(rb)
        self._mode_note = _label(mode, 'Single keeps the existing one-circuit workflow unchanged.', font=FM.small, fg=C['muted'], justify='left', anchor='w')
        self._mode_note.grid(row=0, column=3, sticky='ew', padx=(22, 0))
        mode.grid_columnconfigure(3, weight=1)
        self._mode_card.bind('<Configure>', self._layout_mode_card, add='+')
        tab_bar = _frame(self, bg=C['bg3'])
        tab_bar.pack(fill='x')
        for name in ('Import', 'MQT Bench', 'QASM Editor'):
            btn = tk.Label(tab_bar, text=name, font=FM.menu, fg=C['muted'], bg=C['bg3'], padx=20, pady=10, cursor='hand2')
            btn.pack(side='left')
            btn.bind('<Button-1>', lambda e, n=name: self._switch_tab(n))
            setattr(self, f"_tab_btn_{name.replace(' ', '_')}", btn)
        _sep(self, bg=C['sep']).pack(fill='x')
        container = _frame(self)
        container.pack(fill='both', expand=True)
        for name, builder in [('Import', self._build_import), ('MQT Bench', self._build_mqt), ('QASM Editor', self._build_editor)]:
            f = _frame(container)
            f.place(relx=0, rely=0, relwidth=1, relheight=1)
            builder(f)
            self._tab_frames[name] = f
        self._switch_tab('Import')
        self._on_mode_changed()

    def _switch_tab(self, name):
        if self._active_tab.get() == 'QASM Editor' and name != 'QASM Editor':
            self._save_editor_to_active()
        for n in ('Import', 'MQT Bench', 'QASM Editor'):
            btn = getattr(self, f"_tab_btn_{n.replace(' ', '_')}")
            btn.config(fg=C['accent'] if n == name else C['muted'], bg=C['bg2'] if n == name else C['bg3'])
        self._tab_frames[name].lift()
        self._active_tab.set(name)

    def _on_mode_changed(self):
        batch = self.is_batch_mode()
        if hasattr(self, '_mode_note'):
            self._mode_note.config(text='Batch keeps a circuit set and applies Network → Compile → Schedule → Run consistently to it.' if batch else 'Single keeps the existing one-circuit workflow unchanged.')
            self.after_idle(self._layout_mode_card)
        self._update_mode_widgets()
        self._mark_mqt_validation_stale()
        root = self.winfo_toplevel()
        if hasattr(root, 'on_circuit_set_changed'):
            root.on_circuit_set_changed()

    def _layout_mode_card(self, _event=None):
        if not hasattr(self, '_mode_note') or not hasattr(self, '_mode_card'):
            return
        try:
            self._mode_card.update_idletasks()
            width = max(220, int(self._mode_card.winfo_width()))
            controls = int(self._mode_title.winfo_reqwidth())
            controls += sum((int(rb.winfo_reqwidth()) + 16 for rb in self._mode_radios))
            full_note = int(FM.small.measure(self._mode_note.cget('text'))) + 34
            same_row = width >= controls + full_note + 70
            self._mode_note.grid_forget()
            if same_row:
                available = max(240, width - controls - 56)
                self._mode_note.config(wraplength=available)
                self._mode_note.grid(row=0, column=3, sticky='ew', padx=(22, 0), pady=0)
            else:
                self._mode_note.config(wraplength=max(240, width - 34))
                self._mode_note.grid(row=1, column=0, columnspan=4, sticky='ew', padx=(0, 0), pady=(7, 0))
        except Exception:
            pass

    def refresh_layout(self):
        self._layout_mode_card()
        try:
            width = max(320, int(self.winfo_width()))
        except Exception:
            width = 1000
        combo_chars = 46 if width >= 1100 else 34 if width >= 780 else 24
        for attr in ('_import_choice', '_editor_choice'):
            widget = getattr(self, attr, None)
            if widget is not None:
                try:
                    widget.config(width=combo_chars)
                except Exception:
                    pass
        if hasattr(self, '_mqt_scal_checks'):
            cols = 2
            try:
                self._mqt_scal_grid.update_idletasks()
                grid_width = max(260, int(self._mqt_scal_grid.winfo_width()))
            except Exception:
                grid_width = max(260, width - 56)
            cell_wrap = max(120, int((grid_width - 24) / 2) - 34)
            for i, cb in enumerate(self._mqt_scal_checks):
                cb.grid_forget()
                cb.config(wraplength=cell_wrap)
                cb.grid(row=i // 2, column=i % 2, sticky='ew', padx=(0, 12), pady=2)
            for c in range(3):
                try:
                    self._mqt_scal_grid.grid_columnconfigure(c, weight=1 if c < 2 else 0, uniform='mqt_scalable' if c < 2 else '', minsize=0)
                except Exception:
                    pass
        if hasattr(self, '_mqt_ns_checks'):
            cols = 3 if width >= 1050 else 2 if width >= 700 else 1
            cell_wrap = max(190, int((width - 100) / cols) - 24)
            for i, cb in enumerate(self._mqt_ns_checks):
                cb.grid_forget()
                cb.config(wraplength=cell_wrap)
                cb.grid(row=i // cols, column=i % cols, sticky='w', padx=(0, 20), pady=2)
            for c in range(4):
                try:
                    self._mqt_ns_grid.grid_columnconfigure(c, weight=1 if c < cols else 0)
                except Exception:
                    pass
        self._sync_mqt_panes()

    def _sync_mqt_panes(self):
        if hasattr(self, '_mqt_results') and hasattr(self, '_mqt_log_card'):
            try:
                pane_w = max(420, int(self._mqt_canvas.winfo_width()) - 56)
                left_min = max(190, min(300, int(pane_w * 0.38)))
                right_min = max(220, min(460, pane_w - left_min - 24))
                self._mqt_results.paneconfigure(self._mqt_log_card, minsize=left_min)
                self._mqt_results.paneconfigure(self._mqt_preview_card, minsize=right_min)
            except Exception:
                pass

    def _update_mode_widgets(self):
        batch = self.is_batch_mode()
        if hasattr(self, '_browse_btn'):
            self._browse_btn.config(text='Browse multiple…' if batch else 'Browse…')
        if hasattr(self, '_mqt_single_size') and hasattr(self, '_mqt_batch_size'):
            if batch:
                self._mqt_single_size.pack_forget()
                self._mqt_batch_size.pack(fill='x')
            else:
                self._mqt_batch_size.pack_forget()
                self._mqt_single_size.pack(fill='x')
            self._refresh_mqt_generation_plan()
        if hasattr(self, '_editor_batch_btn'):
            self._editor_batch_btn.config(state='normal' if batch else 'disabled')
        if hasattr(self, '_remove_btn'):
            self._remove_btn.config(state='normal' if batch and len(self._circuit_order) > 1 else 'disabled')

    def _build_import(self, parent):
        host = parent
        canvas = tk.Canvas(host, bg=C['bg2'], highlightthickness=0)
        vsb = ttk.Scrollbar(host, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        inner = _frame(canvas)
        win_id = canvas.create_window((0, 0), window=inner, anchor='nw')
        inner.bind('<Configure>', lambda _e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(win_id, width=e.width))
        self._import_canvas = canvas
        parent = inner
        _section_label(parent, 'Import Circuit File', C['accent'])
        _label(parent, 'Single mode imports one file. Batch mode accepts multiple QASM/Python files at once.', fg=C['muted']).pack(anchor='w', padx=28, pady=(0, 10))
        row = _frame(parent)
        row.pack(fill='x', padx=28, pady=(0, 10))
        self._import_path = tk.StringVar(value='No file selected')
        _label(row, 'File:', width=6, anchor='w').pack(side='left')
        _label(row, textvariable=self._import_path, fg=C['muted'], bg=C['bg3'], padx=10, pady=5, width=48, anchor='w', font=FM.mono).pack(side='left', padx=(0, 10))
        self._browse_btn = _ghost_button(row, 'Browse…', accent=C['accent'], command=self._browse_import, padx=12, pady=5)
        self._browse_btn.pack(side='left')
        _flow_from_pack(row, overrides={row.pack_slaves()[1]: {'shrink': True, 'minw': _scaled(160)}})
        sel = _frame(parent)
        sel.pack(fill='x', padx=28, pady=(0, 8))
        _label(sel, 'Active circuit:', font=FM.small).pack(side='left')
        self._import_choice = ttk.Combobox(sel, state='readonly', width=46)
        self._import_choice.pack(side='left', padx=(8, 0))
        self._import_choice.bind('<<ComboboxSelected>>', lambda _e: self._on_selector_changed('import'))
        _flow_from_pack(sel, overrides={self._import_choice: {'shrink': True, 'minw': _scaled(180)}})
        tree_wrap = _card(parent, padx=8, pady=8)
        tree_wrap.pack(fill='x', padx=28, pady=(0, 10))
        self._import_tree = ttk.Treeview(tree_wrap, columns=('name', 'source', 'qubits', 'gates', 'depth'), show='headings', height=4)
        for c, t, w in [('name', 'Circuit', 260), ('source', 'Source', 120), ('qubits', 'Qubits', 70), ('gates', 'Gates', 70), ('depth', 'Depth', 70)]:
            self._import_tree.heading(c, text=t, anchor='center')
            self._import_tree.column(c, width=w, anchor='center')
        self._import_tree.pack(fill='x', expand=True)
        _tree_base = {'name': 260, 'source': 120, 'qubits': 70, 'gates': 70, 'depth': 70}

        def _fit_import_columns(event, tree=self._import_tree, base=_tree_base):
            try:
                total = sum(base.values())
                avail = max(1, int(event.width) - 4)
                for col, bw in base.items():
                    width = max(_scaled(56), int(bw * avail / total))
                    if abs(int(tree.column(col, 'width')) - width) > 1:
                        tree.column(col, width=width)
            except Exception:
                pass
        self._import_tree.bind('<Configure>', _fit_import_columns, add='+')
        self._import_tree.bind('<<TreeviewSelect>>', lambda _e: self.activate_record(self._import_tree.selection()[0]) if self._import_tree.selection() else None)
        cards_row = _frame(parent)
        cards_row.pack(fill='x', padx=28, pady=(0, 12))
        self._stat_vars = {}
        for lbl in ('Qubits', 'Gates', 'Depth', 'CX count'):
            c = _card(cards_row, padx=18, pady=10)
            c.pack(side='left', padx=(0, 10))
            v = tk.StringVar(value='—')
            self._stat_vars[lbl] = v
            tk.Label(c, textvariable=v, font=FM.title, fg=C['accent'], bg=C['bg2']).pack()
            tk.Label(c, text=lbl, font=FM.small, fg=C['muted'], bg=C['bg2']).pack()
        _sep(parent).pack(fill='x', padx=28, pady=(0, 10))
        _label(parent, 'QASM / source preview:', font=FM.subh, fg=C['text']).pack(anchor='w', padx=28, pady=(0, 4))
        self._import_preview = scrolledtext.ScrolledText(parent, font=FM.mono, bg=C['bg3'], fg=C['text'], insertbackground=C['accent'], relief='flat', height=6, padx=10, pady=8, state='disabled')
        self._import_preview.pack(fill='both', expand=True, padx=28, pady=(0, 16))

    def _browse_import(self):
        types = [('QASM files', '*.qasm'), ('Python files', '*.py'), ('All files', '*.*')]
        paths = filedialog.askopenfilenames(filetypes=types) if self.is_batch_mode() else ()
        if not self.is_batch_mode():
            p = filedialog.askopenfilename(filetypes=types)
            paths = (p,) if p else ()
        if not paths:
            return
        first_rec = None
        for i, path in enumerate(paths):
            try:
                content = Path(path).read_text(encoding='utf-8')
                rec = self._add_circuit(name=Path(path).stem, qasm_text=content, source='Imported', path=path, series=Path(path).stem, replace_single=not self.is_batch_mode() and i == 0)
                first_rec = first_rec or rec
            except Exception as exc:
                messagebox.showerror('Load error', f'{path}\n\n{exc}')
        if first_rec:
            self.activate_record(first_rec['id'])
            self._switch_tab('Import')
        root = self.winfo_toplevel()
        if hasattr(root, 'on_circuit_set_changed'):
            root.on_circuit_set_changed()

    def _build_mqt(self, parent):
        canvas = tk.Canvas(parent, bg=C['bg2'], highlightthickness=0)
        self._mqt_canvas = canvas
        vsb = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        inner = _frame(canvas)
        win_id = canvas.create_window((0, 0), window=inner, anchor='nw')
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.bind_all('<MouseWheel>', lambda e: canvas.yview_scroll(-1 * (e.delta // 120), 'units'))
        P = 28
        _section_label(inner, 'MQT Bench — Benchmark Selection', C['accent'])
        _label(inner, 'Target-independent Qiskit generation. Batch mode expands scalable benchmarks over a qubit sweep.', fg=C['muted']).pack(anchor='w', padx=P, pady=(0, 12))
        _sep(inner).pack(fill='x', padx=P, pady=(0, 14))
        _label(inner, 'Scalable Benchmarks', font=FM.subh, fg=C['text']).pack(anchor='w', padx=P, pady=(0, 4))
        _label(inner, 'Single: one qubit count. Batch: inclusive min/max/step sweep for every selected scalable benchmark.', fg=C['muted'], font=FM.small).pack(anchor='w', padx=P, pady=(0, 6))
        self._sel_all_var = tk.BooleanVar(value=False)
        tk.Checkbutton(inner, text='Select all scalable benchmarks', variable=self._sel_all_var, font=FM.small, bg=C['bg2'], fg=C['text'], selectcolor=C['bg3'], activebackground=C['bg4'], activeforeground=C['text'], disabledforeground=C['muted'], command=self._toggle_all_scalable).pack(anchor='w', padx=P, pady=(0, 6))
        scal_grid = _frame(inner)
        scal_grid.pack(fill='x', padx=P, pady=(0, 10))
        self._scal_vars = {}
        self._mqt_scal_grid = scal_grid
        self._mqt_scal_checks = []
        for i, name in enumerate(self.SCALABLE):
            v = tk.BooleanVar(value=False)
            self._scal_vars[name] = v
            cb = tk.Checkbutton(scal_grid, text=name, variable=v, font=FM.small, bg=C['bg2'], fg=C['text'], selectcolor=C['bg3'], activebackground=C['bg4'], activeforeground=C['text'], disabledforeground=C['muted'], wraplength=260, justify='left', anchor='w', command=self._on_mqt_selection_changed)
            cb.grid(row=i // 2, column=i % 2, sticky='ew', padx=(0, 12), pady=2)
            self._mqt_scal_checks.append(cb)
        scal_grid.grid_columnconfigure(0, weight=1, uniform='mqt_scalable')
        scal_grid.grid_columnconfigure(1, weight=1, uniform='mqt_scalable')
        self._mqt_size_host = _card(inner, padx=14, pady=10)
        self._mqt_size_host.pack(fill='x', padx=P, pady=(4, 14))
        self._mqt_single_size = _frame(self._mqt_size_host)
        _label(self._mqt_single_size, 'Qubits:', font=FM.subh, fg=C['text']).pack(side='left')
        self._q_count = tk.IntVar(value=5)
        tk.Spinbox(self._mqt_single_size, from_=1, to=100000, textvariable=self._q_count, width=7, font=FM.mono, bg=C['bg3'], fg=C['text'], relief='flat').pack(side='left', padx=(10, 14))
        _label(self._mqt_single_size, 'Exact support is checked against the installed MQT Bench benchmark before generation.', font=FM.small, fg=C['muted']).pack(side='left')
        self._mqt_batch_size = _frame(self._mqt_size_host)
        _label(self._mqt_batch_size, 'Qubit sweep', font=FM.subh, fg=C['text']).pack(side='left', padx=(0, 14))
        self._q_min = tk.IntVar(value=4)
        self._q_max = tk.IntVar(value=20)
        self._q_step = tk.IntVar(value=2)
        for lab, var in [('Min:', self._q_min), ('Max:', self._q_max), ('Step:', self._q_step)]:
            _label(self._mqt_batch_size, lab, font=FM.small).pack(side='left', padx=(0, 5))
            tk.Spinbox(self._mqt_batch_size, from_=1, to=100000, textvariable=var, width=7, font=FM.mono, bg=C['bg3'], fg=C['text'], relief='flat').pack(side='left', padx=(0, 14))
        _label(self._mqt_batch_size, 'Rule: q = Min + k×Step, with q ≤ Max.', font=FM.small, fg=C['muted']).pack(side='left')
        _flow_from_pack(self._mqt_single_size)
        _flow_from_pack(self._mqt_batch_size, overrides={self._mqt_batch_size.pack_slaves()[-1]: {'wrap': True}})
        self._mqt_generation_plan = tk.StringVar(value='')
        _label(self._mqt_size_host, textvariable=self._mqt_generation_plan, font=FM.small, fg=C['muted'], justify='left', anchor='w', wraplength=1350).pack(fill='x', pady=(7, 0))
        validation_row = _frame(self._mqt_size_host)
        validation_row.pack(fill='x', pady=(8, 0))
        self._mqt_validate_btn = _ghost_button(validation_row, 'Check MQT compatibility', accent=C['accent'], command=self._validate_mqt_compatibility, padx=10, pady=4)
        self._mqt_validate_btn.pack(side='left')
        self._mqt_validation_status = tk.StringVar(value='MQT compatibility: not checked')
        _label(validation_row, textvariable=self._mqt_validation_status, font=FM.small, fg=C['muted']).pack(side='left', padx=(12, 0))
        _flow_from_pack(validation_row, overrides={validation_row.pack_slaves()[-1]: {'stretch': True, 'wrap': True, 'minw': _scaled(160)}})
        self._mqt_validation_detail = tk.StringVar(value='QNEST will ask the installed MQT Bench version to validate every selected benchmark/size pair before generation.')
        self._mqt_validation_detail_label = _label(self._mqt_size_host, textvariable=self._mqt_validation_detail, font=FM.small, fg=C['muted'], justify='left', anchor='w', wraplength=1350)
        self._mqt_validation_detail_label.pack(fill='x', pady=(5, 0))
        for _v in (self._q_count, self._q_min, self._q_max, self._q_step):
            _v.trace_add('write', self._refresh_mqt_generation_plan)
        _sep(inner).pack(fill='x', padx=P, pady=(0, 12))
        _label(inner, 'Non-Scalable Benchmarks', font=FM.subh, fg=C['text']).pack(anchor='w', padx=P, pady=(0, 4))
        _label(inner, 'These benchmarks use the fixed circuit size defined by MQT Bench and are generated once.', fg=C['muted'], font=FM.small).pack(anchor='w', padx=P, pady=(0, 6))
        ns_grid = _frame(inner)
        ns_grid.pack(fill='x', padx=P, pady=(0, 10))
        self._ns_vars = {}
        self._mqt_ns_grid = ns_grid
        self._mqt_ns_checks = []
        for i, name in enumerate(self.NON_SCALABLE):
            v = tk.BooleanVar(value=False)
            self._ns_vars[name] = v
            cb = tk.Checkbutton(ns_grid, text=name, variable=v, font=FM.small, bg=C['bg2'], fg=C['text'], selectcolor=C['bg3'], activebackground=C['bg4'], activeforeground=C['text'], disabledforeground=C['muted'], anchor='w', justify='left')
            cb.grid(row=i // 3, column=i % 3, sticky='w', padx=(0, 20), pady=2)
            self._mqt_ns_checks.append(cb)
        _sep(inner).pack(fill='x', padx=P, pady=(6, 14))
        profile = _card(inner, padx=14, pady=10)
        profile.pack(fill='x', padx=P, pady=(0, 14))
        _label(profile, 'Generation profile', font=FM.subh, fg=C['text']).pack(anchor='w')
        _label(profile, 'Target-independent level  •  Qiskit  •  each generated circuit is stored separately', font=FM.small, fg=C['muted']).pack(anchor='w', pady=(3, 0))
        btn_row = _frame(inner)
        btn_row.pack(fill='x', padx=P, pady=(0, 8))
        self._mqt_generate_btn = _button(btn_row, '▶  Generate QASM', accent=C['accent'], command=self._generate_mqt, padx=18, pady=7)
        self._mqt_generate_btn.pack(side='left')
        self._mqt_status = _label(btn_row, '', fg=C['muted'])
        self._mqt_status.pack(side='left', padx=16)
        _flow_from_pack(btn_row, overrides={self._mqt_status: {'stretch': True, 'wrap': True, 'minw': _scaled(160)}})
        results = tk.PanedWindow(inner, orient='horizontal', bg=C['sep'], bd=0, sashwidth=6, sashrelief='flat', showhandle=False, height=420)
        results.pack(fill='both', expand=True, padx=P, pady=(0, 20))
        self._mqt_results = results
        log_card = _card(results, padx=12, pady=10)
        preview_card = _card(results, padx=12, pady=10)
        self._mqt_log_card = log_card
        self._mqt_preview_card = preview_card
        results.add(log_card, minsize=300, stretch='always')
        results.add(preview_card, minsize=460, stretch='always')
        canvas.bind('<Configure>', lambda _e: self.after_idle(self._sync_mqt_panes), add='+')
        log_head = _frame(log_card)
        log_head.pack(fill='x', pady=(0, 7))
        _label(log_head, 'Generation Log', font=FM.subh, fg=C['text']).pack(side='left')
        _label(log_head, 'MQT / pytket_dqc', font=FM.small, fg=C['muted']).pack(side='right')
        _flow_from_pack(log_head)
        self._mqt_log = scrolledtext.ScrolledText(log_card, font=FM.mono, bg=C['bg3'], fg=C['text'], relief='flat', height=15, padx=10, pady=8, state='disabled', wrap='none')
        self._mqt_log.pack(fill='both', expand=True)
        preview_head = _frame(preview_card)
        preview_head.pack(fill='x', pady=(0, 8))
        _label(preview_head, 'Generated Circuit Preview', font=FM.subh, fg=C['text']).pack(anchor='w')
        preview_controls = _frame(preview_head)
        preview_controls.pack(fill='x', pady=(5, 0))
        self._mqt_preview_var = tk.StringVar(value='No circuit generated yet')
        self._mqt_preview_menu = ttk.Combobox(preview_controls, textvariable=self._mqt_preview_var, state='readonly', width=22)
        self._mqt_preview_menu.pack(side='left', fill='x', expand=True)
        self._mqt_preview_menu.bind('<<ComboboxSelected>>', lambda e: self._show_mqt_preview())
        _ghost_button(preview_controls, 'Open interactive', accent=C['accent'], command=self._open_mqt_interactive, padx=9, pady=4).pack(side='right', padx=(8, 0))
        _flow_from_pack(preview_controls)
        self._mqt_preview_meta = _label(preview_card, 'Generate a benchmark to preview its circuit here.', font=FM.small, fg=C['muted'])
        self._mqt_preview_meta.pack(anchor='w', pady=(0, 8))
        preview_body = _frame(preview_card, bg=C['bg3'])
        preview_body.pack(fill='both', expand=True)
        self._mqt_circuit_canvas = _ExactPytketCircuitCanvas(preview_body)
        self._mqt_circuit_canvas.pack(fill='both', expand=True)
        self._mqt_preview_rows = []

    def _mqt_sweep_values(self):
        if self.is_batch_mode():
            qmin = int(self._q_min.get())
            qmax = int(self._q_max.get())
            qstep = int(self._q_step.get())
            if qmin < 1:
                raise ValueError('Min must be at least 1.')
            if qmax < qmin:
                raise ValueError('Max must be greater than or equal to Min.')
            if qstep < 1:
                raise ValueError('Step must be at least 1.')
            return list(range(qmin, qmax + 1, qstep))
        q = int(self._q_count.get())
        if q < 1:
            raise ValueError('Qubits must be at least 1.')
        return [q]

    def _mqt_request_signature(self):
        selected = tuple(sorted((n for n, v in getattr(self, '_scal_vars', {}).items() if v.get())))
        try:
            values = tuple(self._mqt_sweep_values())
        except Exception:
            values = ()
        return (self._workflow_mode.get(), selected, values)

    def _mark_mqt_validation_stale(self):
        self._mqt_validation_signature = None
        self._mqt_validation_result = None
        if hasattr(self, '_mqt_validation_status'):
            self._mqt_validation_status.set('MQT compatibility: not checked')
            self._mqt_validation_detail.set('QNEST will ask the installed MQT Bench version to validate every selected benchmark/size pair before generation.')
            self._mqt_validation_detail_label.config(fg=C['muted'])

    def _on_mqt_selection_changed(self):
        self._mark_mqt_validation_stale()
        self._refresh_mqt_generation_plan()

    def _refresh_mqt_generation_plan(self, *_args):
        if not hasattr(self, '_mqt_generation_plan'):
            return
        self._mark_mqt_validation_stale()
        try:
            values = self._mqt_sweep_values()
            selected_count = sum((1 for v in getattr(self, '_scal_vars', {}).values() if v.get()))
            if self.is_batch_mode():
                qmax = int(self._q_max.get())
                grid_note = '' if values and values[-1] == qmax else f'  •  Max {qmax} is an upper bound and is not on the step grid; last generated size is {values[-1]}.'
                count_note = f'  •  {len(values)} size(s)' + (f' × {selected_count} selected scalable benchmark(s) = {len(values) * selected_count} circuit(s).' if selected_count else '.')
                text = f"Planned scalable sizes: {', '.join(map(str, values))}.{count_note}{grid_note}"
            else:
                text = f"Planned scalable size: {values[0]} qubit{('s' if values[0] != 1 else '')}. Exact benchmark-specific support will be checked by MQT Bench."
        except Exception as exc:
            text = f'Invalid qubit settings: {exc}'
        self._mqt_generation_plan.set(text)

    def _toggle_all_scalable(self):
        val = self._sel_all_var.get()
        for v in self._scal_vars.values():
            v.set(val)
        self._on_mqt_selection_changed()

    def _apply_mqt_validation_result(self, result, signature):
        self._mqt_validation_signature = signature
        self._mqt_validation_result = result
        version = result.get('mqt_version') or 'installed version'
        rows = result.get('rows') or []
        invalid = result.get('invalid') or []
        if not rows:
            self._mqt_validation_status.set('MQT compatibility: no scalable points to check')
            self._mqt_validation_detail.set('Only fixed-size/non-scalable benchmarks are selected; they are validated when generated.')
            self._mqt_validation_detail_label.config(fg=C['muted'])
            return
        if not invalid:
            self._mqt_validation_status.set(f'✓ MQT Bench {version}: all {len(rows)} requested point(s) supported')
            self._mqt_validation_detail.set('Validated with the same target-independent Qiskit generation call used by Generate QASM.')
            self._mqt_validation_detail_label.config(fg=C['success'])
            return
        self._mqt_validation_status.set(f'✕ MQT Bench {version}: {len(invalid)} unsupported point(s)')
        details = []
        for r in invalid[:8]:
            err = (r.get('error') or 'Unsupported').replace('\n', ' ')
            details.append(f"{r.get('display')} q={r.get('nq')}: {r.get('error_type', 'Error')}: {err}")
        if len(invalid) > 8:
            details.append(f'… and {len(invalid) - 8} more unsupported point(s).')
        self._mqt_validation_detail.set('  |  '.join(details))
        self._mqt_validation_detail_label.config(fg=C['danger'])

    def _validate_mqt_compatibility(self):
        selected_s = [n for n, v in self._scal_vars.items() if v.get()]
        if not selected_s:
            self._mqt_validation_status.set('MQT compatibility: select a scalable benchmark first')
            self._mqt_validation_detail.set('Sweep validation applies to scalable benchmarks. Fixed-size benchmarks are checked during generation.')
            return
        try:
            values = self._mqt_sweep_values()
        except Exception as exc:
            messagebox.showerror('MQT Bench', f'Invalid qubit settings: {exc}')
            return
        signature = self._mqt_request_signature()
        self._mqt_validate_btn.config(state='disabled')
        self._mqt_validation_status.set('Checking installed MQT Bench…')
        self._mqt_validation_detail.set('This checks every selected benchmark/size pair in the pytket_dqc environment.')

        def _worker():
            try:
                result = self.winfo_toplevel().pipeline.validate_mqt_requests(benchmark_names=selected_s, qubit_counts=values)
                self.after(0, lambda r=result, sig=signature: (self._mqt_validate_btn.config(state='normal'), self._apply_mqt_validation_result(r, sig)))
            except Exception as exc:
                self.after(0, lambda e=exc: (self._mqt_validate_btn.config(state='normal'), self._mqt_validation_status.set('MQT compatibility check failed'), self._mqt_validation_detail.set(f'{type(e).__name__}: {e}'), self._mqt_validation_detail_label.config(fg=C['danger'])))
        threading.Thread(target=_worker, daemon=True).start()

    def _scroll_mqt_results_into_view(self):
        try:
            self._mqt_canvas.update_idletasks()
            self._mqt_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _set_mqt_preview_rows(self, rows):
        self._mqt_preview_rows = list(rows or [])
        labels = []
        for row in self._mqt_preview_rows:
            labels.append(f"{row.get('display', row.get('benchmark', 'Circuit'))}  •  {row.get('qubits', '?')} qubits")
        self._mqt_preview_menu['values'] = labels
        if labels:
            self._mqt_preview_menu.current(0)
            self._show_mqt_preview()
        else:
            self._mqt_preview_var.set('No circuit generated yet')

    def _show_mqt_preview(self, resize_only=False):
        if not self._mqt_preview_rows:
            return
        idx = self._mqt_preview_menu.current()
        idx = idx if 0 <= idx < len(self._mqt_preview_rows) else 0
        row = self._mqt_preview_rows[idx]
        self._mqt_preview_meta.config(text=f"{row.get('display', 'Circuit')}  •  {row.get('qubits', '—')} qubits  •  {row.get('gates', '—')} gates  •  depth {row.get('depth', '—')}")
        self._mqt_circuit_canvas.show(snapshot_path=row.get('pytket_snapshot_path'), html_path=row.get('pytket_html_path'), qasm_path=row.get('path'), error=row.get('pytket_snapshot_error') or row.get('pytket_html_error'))

    def _open_mqt_interactive(self):
        if not self._mqt_preview_rows:
            return
        idx = self._mqt_preview_menu.current()
        idx = idx if 0 <= idx < len(self._mqt_preview_rows) else 0
        row = self._mqt_preview_rows[idx]
        html_path = row.get('pytket_html_path')
        if html_path and Path(html_path).exists():
            _open_local_path(Path(html_path))
            return
        messagebox.showwarning('QNEST', 'The exact pytket HTML representation is not available for this circuit.')

    def _generate_mqt(self):
        selected_s = [n for n, v in self._scal_vars.items() if v.get()]
        selected_ns = [n for n, v in self._ns_vars.items() if v.get()]
        selected = selected_s + selected_ns
        if not selected:
            messagebox.showwarning('MQT Bench', 'Please select at least one benchmark.')
            return
        if not self.is_batch_mode() and len(selected) != 1:
            messagebox.showwarning('MQT Bench', 'Single-circuit mode accepts one benchmark. Select one benchmark or switch to Batch / sweep.')
            return
        try:
            values = self._mqt_sweep_values()
            if self.is_batch_mode():
                qcounts = values
                qcount = None
            else:
                qcount = values[0]
                qcounts = None
        except Exception as exc:
            messagebox.showerror('MQT Bench', f'Invalid qubit settings: {exc}')
            return
        signature = self._mqt_request_signature()
        self._mqt_log.config(state='normal')
        self._mqt_log.delete('1.0', 'end')
        self._mqt_log.config(state='disabled')
        self._mqt_status.config(text='Validating with MQT Bench…', fg=C['warning'])
        self._mqt_generate_btn.config(state='disabled')

        def _log(msg):
            self._mqt_log.config(state='normal')
            self._mqt_log.insert('end', str(msg) + '\n')
            self._mqt_log.see('end')
            self._mqt_log.config(state='disabled')

        def _worker():
            try:
                validation = None
                if selected_s:
                    if self._mqt_validation_signature == signature and self._mqt_validation_result is not None:
                        validation = self._mqt_validation_result
                    else:
                        validation = self.winfo_toplevel().pipeline.validate_mqt_requests(benchmark_names=selected_s, qubit_count=qcount, qubit_counts=qcounts, log=lambda m: self.after(0, lambda msg=m: _log(msg)))
                    self.after(0, lambda r=validation, sig=signature: self._apply_mqt_validation_result(r, sig))
                    if validation.get('invalid'):
                        for r in validation['invalid']:
                            self.after(0, lambda row=r: _log(f"[UNSUPPORTED] {row.get('display')} q={row.get('nq')}: {row.get('error_type', 'Error')}: {row.get('error', '')}"))

                        def _blocked():
                            self._mqt_status.config(text='Fix unsupported MQT sweep points', fg=C['danger'])
                            self._mqt_generate_btn.config(state='normal')
                            messagebox.showerror('MQT Bench compatibility', f"{len(validation['invalid'])} benchmark/size point(s) are rejected by the installed MQT Bench version. Adjust Min / Max / Step or benchmark selection. Exact errors are shown above and in the generation log.")
                        self.after(0, _blocked)
                        return
                self.after(0, lambda: self._mqt_status.config(text='Generating in pytket_dqc…', fg=C['warning']))
                result = self.winfo_toplevel().pipeline.generate_mqt_qasm(benchmark_names=selected, qubit_count=qcount, qubit_counts=qcounts, non_scalable_names=selected_ns, log=lambda m: self.after(0, lambda msg=m: _log(msg)))

                def _done():
                    first_rec = None
                    for i, row in enumerate(result['successful']):
                        qasm_path = Path(row['path'])
                        qasm = qasm_path.read_text(encoding='utf-8')
                        display = row.get('display') or row.get('benchmark') or qasm_path.stem
                        suffix = f"_q{row.get('qubits')}" if row.get('nq') is not None else ''
                        rec = self._add_circuit(name=f'{display}{suffix}', qasm_text=qasm, source='MQT Bench', path=qasm_path, benchmark=display, series=display, qubits=row.get('qubits'), gates=row.get('gates'), depth=row.get('depth'), renderer_row=row, replace_single=not self.is_batch_mode() and i == 0)
                        first_rec = first_rec or rec
                    if first_rec:
                        self.activate_record(first_rec['id'])
                    self._mqt_status.config(text=f"✓ {len(result['successful'])} circuit(s) generated and added to the circuit set", fg=C['success'])
                    self._mqt_generate_btn.config(state='normal')
                    self._set_mqt_preview_rows(result['successful'])
                    _log(f"[INFO] Separate valid QASM files saved in: {result['output_dir']}")
                    self.after_idle(self._scroll_mqt_results_into_view)
                    root = self.winfo_toplevel()
                    if hasattr(root, 'on_circuit_set_changed'):
                        root.on_circuit_set_changed()
                self.after(0, _done)
            except Exception as exc:
                self.after(0, lambda e=exc: (self._mqt_generate_btn.config(state='normal'), self._mqt_status.config(text='Generation failed', fg=C['danger']), _log(f'[ERROR] {type(e).__name__}: {e}')))
        threading.Thread(target=_worker, daemon=True).start()

    def _build_editor(self, parent):
        _section_label(parent, 'QASM Editor', C['accent'])
        _label(parent, 'Edit the active circuit. In Batch mode use the selector to move between circuits without losing edits.', fg=C['muted']).pack(anchor='w', padx=28, pady=(0, 8))
        sel = _frame(parent)
        sel.pack(fill='x', padx=28, pady=(0, 8))
        _label(sel, 'Circuit:', font=FM.small).pack(side='left')
        self._editor_choice = ttk.Combobox(sel, state='readonly', width=48)
        self._editor_choice.pack(side='left', padx=(8, 8))
        self._editor_choice.bind('<<ComboboxSelected>>', lambda _e: self._on_selector_changed('editor'))
        self._editor_batch_btn = _ghost_button(sel, 'Add current as new circuit…', accent=C['accent'], command=self._add_editor_circuit, padx=10, pady=4)
        self._editor_batch_btn.pack(side='left', padx=(0, 6))
        self._remove_btn = _ghost_button(sel, 'Remove', accent=C['danger'], command=self._remove_active_record, padx=10, pady=4)
        self._remove_btn.pack(side='left')
        _flow_from_pack(sel, overrides={self._editor_choice: {'shrink': True, 'minw': _scaled(180)}})
        tb = _frame(parent)
        tb.pack(fill='x', padx=28, pady=(0, 8))
        for txt, cmd in [('Save as…', self._save_qasm), ('Clear', self._clear_editor)]:
            _ghost_button(tb, txt, accent=C['accent'], command=cmd, padx=10, pady=4).pack(side='left', padx=(0, 8))
        _flow_from_pack(tb)
        self._editor_text = scrolledtext.ScrolledText(parent, font=FM.mono, bg=C['bg3'], fg=C['text'], insertbackground=C['accent'], relief='flat', padx=10, pady=8)
        self._editor_text.pack(fill='both', expand=True, padx=28, pady=(0, 16))
        self._editor_text.insert('1.0', '// QASM will appear here after import or generation\n')

    def _add_editor_circuit(self):
        if not self.is_batch_mode():
            return
        self._save_editor_to_active()
        text = self._editor_text.get('1.0', 'end').strip()
        if not text:
            return
        name = simpledialog.askstring('Batch circuit', 'Name for the new circuit:', initialvalue=f'editor_{len(self._circuit_order) + 1}', parent=self)
        if not name:
            return
        rec = self._add_circuit(name=name, qasm_text=text + '\n', source='QASM Editor', series=name)
        self.activate_record(rec['id'])
        root = self.winfo_toplevel()
        if hasattr(root, 'on_circuit_set_changed'):
            root.on_circuit_set_changed()

    def _save_qasm(self):
        path = filedialog.asksaveasfilename(defaultextension='.qasm', filetypes=[('QASM files', '*.qasm'), ('All files', '*.*')])
        if path:
            try:
                text = self._editor_text.get('1.0', 'end')
                Path(path).write_text(text, encoding='utf-8')
                rec = self.get_active_record()
                if rec:
                    rec['path'] = path
                    rec['qasm_text'] = text
                messagebox.showinfo('Saved', f'QASM saved to:\n{path}')
            except Exception as exc:
                messagebox.showerror('Save error', str(exc))

    def _clear_editor(self):
        self._editor_text.delete('1.0', 'end')
        self._save_editor_to_active()

class NetworkModel:
    _id_counter = 0

    @classmethod
    def _new_id(cls, prefix):
        cls._id_counter += 1
        return f'{prefix}_{cls._id_counter:03d}'

    def __init__(self):
        self.nodes = {}
        self.links = {}
        self._listeners = []

    def subscribe(self, fn):
        self._listeners.append(fn)

    def _notify(self):
        for fn in self._listeners:
            fn()

    def add_node(self, kind, x=100, y=100):
        nid = self._new_id(kind.lower())
        defaults = {'QPU': {'qubits': '10', 'n_inputs': 2, 'n_outputs': 2}, 'Switch': {'switch_mode': 'All-photonic', 'n_inputs': 4, 'n_outputs': 4}}.get(kind, {'n_inputs': 2, 'n_outputs': 2})
        self.nodes[nid] = {'id': nid, 'kind': kind, 'x': x, 'y': y, 'label': nid, **defaults}
        self._notify()
        return nid

    def add_link(self, src_id, dst_id):
        lid = self._new_id('link')
        self.links[lid] = {'id': lid, 'src': src_id, 'dst': dst_id, 'src_port': 'out1', 'dst_port': 'in1', 'kind': 'Link', 'length': '0.2', 'success_probability': None, 'fidelity': None, 'attempt_rate_hz': None, 'ebit_rate_hz': None, 'propagation_latency_us': None}
        self._notify()
        return lid

    def remove_node(self, nid):
        self.nodes.pop(nid, None)
        dead = [lid for lid, l in self.links.items() if l['src'] == nid or l['dst'] == nid]
        for lid in dead:
            self.links.pop(lid)
        self._notify()

    def remove_link(self, lid):
        self.links.pop(lid, None)
        self._notify()

class SpecDialog(tk.Toplevel):
    _DROPDOWNS = {'switch_mode': ['All-photonic', 'Memory-assisted']}
    _HINTS = {'length': 'km', 'attenuation': 'dB/km', 'gamma': '(0-1)', 'depol_p': '(0-1)', 'fidelity': '(0-1)', 'splitting_ratio': '(0-1)', 'T1': 'µs', 'T2': 'µs', 'gate_error': '(0-1)', 'readout_error': '(0-1)', 'bandwidth': 'GHz', 'insertion_loss': 'dB', 'extinction_ratio': 'dB', 'num_bsm': 'count', 'bsm_efficiency': '(0-1)', 'bsm_dark_count': 'Hz', 'switching_time': 'µs', 'phase': 'rad', 'dispersion': 'ps/nm/km', 'n_index': '', 'phase_offset': 'rad', 'qubits': 'count', 'n_inputs': 'count', 'n_outputs': 'count', 'efficiency': '(0-1)', 'dark_count': 'Hz', 'src_port': '', 'dst_port': '', 'success_probability': 'derived', 'attempt_rate_hz': 'Hz (derived)', 'ebit_rate_hz': 'Hz (derived)', 'propagation_latency_us': 'µs (derived)'}
    _DERIVED_READONLY = {'success_probability', 'fidelity', 'attempt_rate_hz', 'ebit_rate_hz', 'propagation_latency_us'}

    def __init__(self, master, obj, title):
        super().__init__(master)
        self.title(title)
        self.configure(bg=C['bg'])
        self.resizable(False, False)
        self.grab_set()
        self._obj = obj
        self._vars = {}
        self._build(obj)
        self.update_idletasks()
        mx = master.winfo_rootx() + master.winfo_width() // 2
        my = master.winfo_rooty() + master.winfo_height() // 2
        w, h = (self.winfo_width(), self.winfo_height())
        self.geometry(f'+{mx - w // 2}+{my - h // 2}')

    def _build(self, obj):
        tk.Label(self, text=f"  {obj.get('kind', 'Link')}  —  {obj['id']}", font=FM.head, fg=C['accent'], bg=C['bg'], anchor='w', padx=12, pady=12).pack(fill='x')
        _sep(self).pack(fill='x')
        canvas = tk.Canvas(self, bg=C['bg'], highlightthickness=0, width=440, height=min(400, 60 + 34 * len(obj)))
        vsb = ttk.Scrollbar(self, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        inner = tk.Frame(canvas, bg=C['bg'])
        win = canvas.create_window((0, 0), window=inner, anchor='nw')
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(win, width=e.width))
        skip = {'id', 'kind', 'x', 'y', 'label'}
        for key, val in obj.items():
            if key in skip:
                continue
            row = tk.Frame(inner, bg=C['bg'])
            row.pack(fill='x', padx=14, pady=3)
            hint = self._HINTS.get(key, '')
            lbl_text = f'{key}' + (f'  [{hint}]' if hint else '')
            tk.Label(row, text=lbl_text, font=FM.small, fg=C['muted'], bg=C['bg'], width=26, anchor='w').pack(side='left')
            var = tk.StringVar(value='—' if val is None else str(val))
            if key in self._DERIVED_READONLY:
                tk.Label(row, textvariable=var, width=22, font=FM.mono, bg=C['bg4'], fg=C['muted'], anchor='w', padx=6).pack(side='left')
                continue
            self._vars[key] = var
            if key in self._DROPDOWNS:
                om = tk.OptionMenu(row, var, *self._DROPDOWNS[key])
                om.config(font=FM.small, bg=C['bg3'], fg=C['text'], activebackground=C['accent'], relief='flat', width=18)
                om['menu'].config(bg=C['bg3'], fg=C['text'])
                om.pack(side='left')
            else:
                e = tk.Entry(row, textvariable=var, width=22, font=FM.mono, bg=C['bg3'], fg=C['text'], insertbackground=C['accent'], relief='flat')
                e.pack(side='left')
        _sep(self).pack(fill='x')
        btn_row = tk.Frame(self, bg=C['bg'])
        btn_row.pack(fill='x', padx=14, pady=10)
        _button(btn_row, 'OK', command=self._ok, padx=18, pady=5).pack(side='left', padx=(0, 8))
        _ghost_button(btn_row, 'Cancel', command=self.destroy, padx=14, pady=5).pack(side='left')

    def _ok(self):
        for key, var in self._vars.items():
            self._obj[key] = var.get()
        self.destroy()

    def _fetch_ibm(self):
        backend = self._vars.get('ibm_backend', tk.StringVar()).get().strip()
        if not backend:
            self._ibm_status.config(text='Enter a backend name first.', fg=C['warning'])
            return
        self._ibm_status.config(text='Fetching…', fg=C['muted'])

        def _worker():
            try:
                from qiskit_ibm_runtime import QiskitRuntimeService
                svc = QiskitRuntimeService()
                be = svc.backend(backend)
                props = be.properties()
                noise_str = f'T1={props.t1(0):.1e}, T2={props.t2(0):.1e}'
                self._vars['noise_model'].set('IBM Calibration')
                self._vars['ibm_backend'].set(backend)
                self._ibm_status.after(0, lambda: self._ibm_status.config(text=f'✓ Loaded: {noise_str}', fg=C['success']))
            except Exception as exc:
                self._ibm_status.after(0, lambda: self._ibm_status.config(text=f'Error: {exc}', fg=C['danger']))
        threading.Thread(target=_worker, daemon=True).start()

class NetworkCanvas(tk.Frame):
    GRID = 20
    NODE_W = 100
    NODE_H = 64
    PORT_R = 7
    KIND_COLOR = {'QPU': '#185FA5', 'Switch': '#854F0B'}
    KIND_FILL = {'QPU': '#E8F1FB', 'Switch': '#FBF1E5'}
    KIND_ICON = {'QPU': '⬡', 'Switch': '⬢'}

    def __init__(self, parent, model):
        super().__init__(parent, bg=C['bg'])
        self._model = model
        self._clipboard = None
        hbar = ttk.Scrollbar(self, orient='horizontal')
        vbar = ttk.Scrollbar(self, orient='vertical')
        self._cv = tk.Canvas(self, bg=C['bg'], highlightthickness=0, xscrollcommand=hbar.set, yscrollcommand=vbar.set, scrollregion=(-500, -500, 4000, 3000))
        hbar.config(command=self._cv.xview)
        vbar.config(command=self._cv.yview)
        vbar.pack(side='right', fill='y')
        hbar.pack(side='bottom', fill='x')
        self._cv.pack(fill='both', expand=True)
        self._mode = 'select'
        self._selected_nid = None
        self._selected_lid = None
        self._drag_nid = None
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._drag_node_ox = 0
        self._drag_node_oy = 0
        self._wire_src_nid = None
        self._wire_src_port = None
        self._wire_src_px = 0
        self._wire_src_py = 0
        self._rubber_band = None
        self._node_items = {}
        self._node_ports = {}
        self._link_items = {}
        self._draw_grid()
        model.subscribe(self._full_redraw)
        self._bind_canvas_events()

    def fit_to_network(self, padding=100):
        if not self._model.nodes:
            return
        try:
            self.update_idletasks()
            xs = [float(nd['x']) for nd in self._model.nodes.values()]
            ys = [float(nd['y']) for nd in self._model.nodes.values()]
            x0, x1 = (min(xs) - padding, max(xs) + self.NODE_W + padding)
            y0, y1 = (min(ys) - padding, max(ys) + self.NODE_H + padding)
            self._cv.configure(scrollregion=(x0, y0, x1, y1))
            self._cv.xview_moveto(0.0)
            self._cv.yview_moveto(0.0)
        except Exception:
            pass

    def set_mode(self, mode):
        self._mode = mode
        cursors = {'select': 'arrow', 'link': 'crosshair', 'delete': 'X_cursor'}
        self._cv.config(cursor=cursors.get(mode, 'arrow'))
        self._cancel_wire()

    def add_component(self, kind):
        import random
        cx = self._cv.winfo_width() // 2 + random.randint(-40, 40)
        cy = self._cv.winfo_height() // 2 + random.randint(-40, 40)
        wx = round(int(self._cv.canvasx(cx)) / self.GRID) * self.GRID
        wy = round(int(self._cv.canvasy(cy)) / self.GRID) * self.GRID
        self._model.add_node(kind, wx, wy)

    def export_json(self):
        import json
        return json.dumps({'nodes': list(self._model.nodes.values()), 'links': list(self._model.links.values())}, indent=2)

    def import_json(self, data):
        import json
        obj = json.loads(data)
        self._model.nodes.clear()
        self._model.links.clear()
        for nd in obj.get('nodes', []):
            self._model.nodes[nd['id']] = nd
        for lk in obj.get('links', []):
            self._model.links[lk['id']] = lk
        self._model._notify()

    def _draw_grid(self):
        for x in range(-500, 4000, self.GRID):
            self._cv.create_line(x, -500, x, 3000, fill=C['sep'], tags='grid')
        for y in range(-500, 3000, self.GRID):
            self._cv.create_line(-500, y, 4000, y, fill=C['sep'], tags='grid')
        self._cv.tag_lower('grid')

    def _full_redraw(self):
        self._cv.delete('node', 'link', 'port', 'portlbl', 'linklbl', 'shadow')
        self._node_items.clear()
        self._node_ports.clear()
        self._link_items.clear()
        for lid, lk in self._model.links.items():
            self._draw_link(lid, lk)
        for nid, nd in self._model.nodes.items():
            self._draw_node(nid, nd)

    def _node_port_positions(self, nd):
        x, y = (int(nd['x']), int(nd['y']))
        w, h = (self.NODE_W, self.NODE_H)
        n_in = int(nd.get('n_inputs', 2))
        n_out = int(nd.get('n_outputs', 2))
        ports = {}
        for i in range(n_in):
            ports[f'in{i + 1}'] = (x, y + int(h * (i + 1) / (n_in + 1)))
        for i in range(n_out):
            ports[f'out{i + 1}'] = (x + w, y + int(h * (i + 1) / (n_out + 1)))
        return ports

    def _draw_node(self, nid, nd):
        x, y = (int(nd['x']), int(nd['y']))
        w, h = (self.NODE_W, self.NODE_H)
        kind = nd['kind']
        color = self.KIND_COLOR.get(kind, '#888')
        fill = self.KIND_FILL.get(kind, '#F0EEE9')
        icon = self.KIND_ICON.get(kind, '?')
        sel = nid == self._selected_nid
        items = []
        s = self._cv.create_rectangle(x + 3, y + 3, x + w + 3, y + h + 3, fill=C['border'], outline='', tags='shadow')
        items.append(s)
        body = self._cv.create_rectangle(x, y, x + w, y + h, fill=fill, outline=color if not sel else '#1A1A1A', width=3 if sel else 1.5, tags='node')
        items.append(body)
        hdr = self._cv.create_rectangle(x, y, x + w, y + 9, fill=color, outline='', tags='node')
        items.append(hdr)
        t1 = self._cv.create_text(x + w // 2, y + 28, text=f'{icon}  {kind}', font=(FM.small.cget('family'), FM.small.cget('size'), 'bold'), fill=color, tags='node')
        items.append(t1)
        t2 = self._cv.create_text(x + w // 2, y + h - 10, text=nd.get('label', nid), font=(FM.small_mono.cget('family'), max(8, FM.small_mono.cget('size') - 1)), fill=C['muted'], tags='node')
        items.append(t2)
        port_positions = self._node_port_positions(nd)
        self._node_ports[nid] = {}
        r = self.PORT_R
        for plabel, (px, py) in port_positions.items():
            side = 'left' if plabel.startswith('in') else 'right'
            circ = self._cv.create_oval(px - r, py - r, px + r, py + r, fill='#FFFFFF', outline=color, width=1.5, tags=('node', 'port'))
            items.append(circ)
            lx = px - r - 3 if side == 'left' else px + r + 3
            anchor = 'e' if side == 'left' else 'w'
            lt = self._cv.create_text(lx, py, text=plabel, font=(FM.small_mono.cget('family'), max(8, FM.small_mono.cget('size') - 2)), fill=C['muted'], anchor=anchor, tags=('node', 'portlbl'))
            items.append(lt)
            self._node_ports[nid][plabel] = (circ, px, py)
        self._node_items[nid] = items

    @staticmethod
    def _rect_edge_anchor(nd, toward_x, toward_y, node_w, node_h):
        x, y = (float(nd['x']), float(nd['y']))
        cx, cy = (x + node_w / 2.0, y + node_h / 2.0)
        dx, dy = (toward_x - cx, toward_y - cy)
        if abs(dx) < 1e-12 and abs(dy) < 1e-12:
            return (cx, cy)
        sx = node_w / 2.0 / abs(dx) if abs(dx) > 1e-12 else float('inf')
        sy = node_h / 2.0 / abs(dy) if abs(dy) > 1e-12 else float('inf')
        scale = min(sx, sy)
        return (cx + dx * scale, cy + dy * scale)

    def _draw_link(self, lid, lk):
        src_nd = self._model.nodes.get(lk['src'])
        dst_nd = self._model.nodes.get(lk['dst'])
        if not src_nd or not dst_nd:
            return
        if lk.get('auto_layout'):
            scx = float(src_nd['x']) + self.NODE_W / 2.0
            scy = float(src_nd['y']) + self.NODE_H / 2.0
            dcx = float(dst_nd['x']) + self.NODE_W / 2.0
            dcy = float(dst_nd['y']) + self.NODE_H / 2.0
            x1, y1 = self._rect_edge_anchor(src_nd, dcx, dcy, self.NODE_W, self.NODE_H)
            x2, y2 = self._rect_edge_anchor(dst_nd, scx, scy, self.NODE_W, self.NODE_H)
        else:
            sp = self._node_port_positions(src_nd).get(lk.get('src_port', 'out1'))
            dp = self._node_port_positions(dst_nd).get(lk.get('dst_port', 'in1'))
            if sp is None:
                sp = (int(src_nd['x']) + self.NODE_W, int(src_nd['y']) + self.NODE_H // 2)
            if dp is None:
                dp = (int(dst_nd['x']), int(dst_nd['y']) + self.NODE_H // 2)
            x1, y1 = sp
            x2, y2 = dp
        sel = lid == self._selected_lid
        color = C['accent2'] if sel else C['muted']
        width = 2.6 if sel else 1.7
        dx, dy = (x2 - x1, y2 - y1)
        length = max((dx * dx + dy * dy) ** 0.5, 1.0)
        bend = float(lk.get('visual_bend', 0.0) or 0.0)
        px, py = (-dy / length, dx / length)
        mx, my = ((x1 + x2) / 2.0 + px * bend, (y1 + y2) / 2.0 + py * bend)
        if abs(bend) > 0.01:
            line = self._cv.create_line(x1, y1, mx, my, x2, y2, smooth=True, splinesteps=24, width=width, fill=color, dash=(6, 3), tags='link')
        else:
            line = self._cv.create_line(x1, y1, x2, y2, width=width, fill=color, dash=(6, 3), tags='link')
        label = lk.get('label') or lid
        if lk.get('show_label', True):
            label_text = label
            mid = self._cv.create_text(mx + px * 12, my + py * 12, text=label_text, font=(FM.small_mono.cget('family'), max(8, FM.small_mono.cget('size') - 1)), fill=C['muted'], tags=('link', 'linklbl'))
            self._link_items[lid] = [line, mid]
        else:
            self._link_items[lid] = [line]
    PORT_HIT_R = 20

    def _find_port_at(self, cx, cy):
        best = None
        best_d = float('inf')
        for nid, ports in self._node_ports.items():
            for plabel, (_circ, px, py) in ports.items():
                d = ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5
                if d < self.PORT_HIT_R and d < best_d:
                    best_d = d
                    best = (nid, plabel, px, py)
        return best

    def _find_node_at(self, cx, cy):
        for nid, nd in self._model.nodes.items():
            x, y = (int(nd['x']), int(nd['y']))
            if x <= cx <= x + self.NODE_W and y <= cy <= y + self.NODE_H:
                return nid
        return None

    def _find_link_near(self, cx, cy):
        for lid, items in self._link_items.items():
            if not items:
                continue
            line_item = items[0]
            try:
                coords = self._cv.coords(line_item)
                for i in range(0, len(coords) - 1, 2):
                    lx, ly = (coords[i], coords[i + 1])
                    if ((cx - lx) ** 2 + (cy - ly) ** 2) ** 0.5 < 10:
                        return lid
            except Exception:
                pass
        return None

    def _on_canvas_press(self, e):
        self._cv.focus_set()
        cx = self._cv.canvasx(e.x)
        cy = self._cv.canvasy(e.y)
        port_hit = self._find_port_at(cx, cy)
        if port_hit:
            self._handle_port_click(*port_hit)
            return
        nid = self._find_node_at(cx, cy)
        if nid:
            self._handle_node_click(e, nid, cx, cy)
            return
        lid = self._find_link_near(cx, cy)
        if lid:
            self._handle_link_click(lid)
            return
        if self._wire_src_nid is not None:
            self._cancel_wire()
        else:
            self._selected_nid = None
            self._selected_lid = None

    def _handle_port_click(self, nid, plabel, px, py):
        if self._mode == 'delete':
            return
        if self._wire_src_nid is None:
            self._wire_src_nid = nid
            self._wire_src_port = plabel
            self._wire_src_px = px
            self._wire_src_py = py
            circ_info = self._node_ports.get(nid, {}).get(plabel)
            if circ_info:
                self._cv.itemconfig(circ_info[0], fill=C['warning'], outline=C['warning'])
        else:
            self._complete_wire(nid, plabel)

    def _handle_node_click(self, e, nid, cx, cy):
        if self._mode == 'delete':
            self._model.remove_node(nid)
            return
        if self._wire_src_nid is not None:
            self._cancel_wire()
            return
        prev = self._selected_nid
        self._selected_nid = nid
        self._selected_lid = None
        if prev != nid:
            self._full_redraw()
        nd = self._model.nodes[nid]
        self._drag_nid = nid
        self._drag_start_x = cx
        self._drag_start_y = cy
        self._drag_node_ox = nd['x']
        self._drag_node_oy = nd['y']
        for item in self._node_items.get(nid, []):
            self._cv.tag_raise(item)

    def _handle_link_click(self, lid):
        if self._mode == 'delete':
            self._model.remove_link(lid)
            return
        self._selected_lid = lid
        self._selected_nid = None
        self._full_redraw()

    def _complete_wire(self, dst_nid, dst_port):
        if self._wire_src_nid is None:
            return
        if dst_nid != self._wire_src_nid:
            lid = self._model.add_link(self._wire_src_nid, dst_nid)
            lk = self._model.links[lid]
            lk['src_port'] = self._wire_src_port
            lk['dst_port'] = dst_port
        self._wire_src_nid = None
        self._wire_src_port = None
        if self._rubber_band is not None:
            self._cv.delete(self._rubber_band)
            self._rubber_band = None
        self._full_redraw()

    def _cancel_wire(self):
        was_active = self._wire_src_nid is not None
        self._wire_src_nid = None
        self._wire_src_port = None
        if self._rubber_band is not None:
            self._cv.delete(self._rubber_band)
            self._rubber_band = None
        if was_active:
            self._full_redraw()

    def _bind_canvas_events(self):
        cv = self._cv
        cv.bind('<ButtonPress-1>', self._on_canvas_press)
        cv.bind('<B1-Motion>', self._on_canvas_drag)
        cv.bind('<ButtonRelease-1>', self._on_canvas_release)
        cv.bind('<Double-Button-1>', self._on_canvas_double)
        cv.bind('<Button-3>', self._on_canvas_right)
        cv.bind('<ButtonPress-2>', self._pan_start)
        cv.bind('<B2-Motion>', self._pan_move)
        cv.bind('<MouseWheel>', self._on_mousewheel)
        cv.bind('<Button-4>', lambda e: cv.yview_scroll(-1, 'units'))
        cv.bind('<Button-5>', lambda e: cv.yview_scroll(1, 'units'))
        cv.bind('<Motion>', self._on_mouse_move)
        cv.bind('<Delete>', lambda e: self._delete_selected())
        cv.bind('<BackSpace>', lambda e: self._delete_selected())
        cv.bind('<Escape>', lambda e: self._cancel_wire())
        cv.bind('<Control-c>', lambda e: self._copy())
        cv.bind('<Control-x>', lambda e: self._cut())
        cv.bind('<Control-v>', lambda e: self._paste())
        cv.focus_set()

    def _on_canvas_drag(self, e):
        if self._drag_nid is None:
            return
        nid = self._drag_nid
        cx = self._cv.canvasx(e.x)
        cy = self._cv.canvasy(e.y)
        dx = cx - self._drag_start_x
        dy = cy - self._drag_start_y
        new_x = round((self._drag_node_ox + dx) / self.GRID) * self.GRID
        new_y = round((self._drag_node_oy + dy) / self.GRID) * self.GRID
        nd = self._model.nodes[nid]
        move_dx = new_x - nd['x']
        move_dy = new_y - nd['y']
        if move_dx == 0 and move_dy == 0:
            return
        nd['x'], nd['y'] = (new_x, new_y)
        for item in self._node_items.get(nid, []):
            self._cv.move(item, move_dx, move_dy)
        for plabel, (circ, px, py) in self._node_ports.get(nid, {}).items():
            self._node_ports[nid][plabel] = (circ, px + move_dx, py + move_dy)
        for lid in [l for l, lk in self._model.links.items() if lk['src'] == nid or lk['dst'] == nid]:
            for item in self._link_items.get(lid, []):
                self._cv.delete(item)
            self._link_items.pop(lid, None)
            self._draw_link(lid, self._model.links[lid])

    def _on_canvas_release(self, e):
        self._drag_nid = None

    def _on_canvas_double(self, e):
        cx = self._cv.canvasx(e.x)
        cy = self._cv.canvasy(e.y)
        nid = self._find_node_at(cx, cy)
        if nid:
            self._edit_node(nid)
            return
        lid = self._find_link_near(cx, cy)
        if lid:
            self._edit_link(lid)

    def _on_canvas_right(self, e):
        cx = self._cv.canvasx(e.x)
        cy = self._cv.canvasy(e.y)
        nid = self._find_node_at(cx, cy)
        if nid:
            self._node_context(e, nid)
            return
        lid = self._find_link_near(cx, cy)
        if lid:
            self._link_context(e, lid)

    def _on_mouse_move(self, e):
        if self._wire_src_nid is None:
            return
        cx, cy = (self._cv.canvasx(e.x), self._cv.canvasy(e.y))
        if self._rubber_band is not None:
            self._cv.delete(self._rubber_band)
        x1, y1 = (self._wire_src_px, self._wire_src_py)
        ctrl = max(40, abs(cx - x1) // 2)
        self._rubber_band = self._cv.create_line(x1, y1, x1 + ctrl, y1, cx - ctrl, cy, cx, cy, smooth=True, width=2, fill=C['warning'], dash=(5, 3), tags='rubber')

    def _pan_start(self, e):
        self._cv.scan_mark(e.x, e.y)

    def _pan_move(self, e):
        self._cv.scan_dragto(e.x, e.y, gain=1)

    def _on_mousewheel(self, e):
        if e.state & 4:
            factor = 1.1 if e.delta > 0 else 0.9
            self._cv.scale('all', e.x, e.y, factor, factor)
        else:
            self._cv.yview_scroll(-1 if e.delta > 0 else 1, 'units')

    def _node_context(self, e, nid):
        nd = self._model.nodes[nid]
        kind = nd['kind']
        menu = tk.Menu(self._cv, tearoff=0, bg=C['bg2'], fg=C['text'], font=FM.small, activebackground=C['menu_sel'], activeforeground=C['text'])
        menu.add_command(label='✏  Edit specs…', command=lambda: self._edit_node(nid))
        menu.add_command(label='⚙  Set interfaces…', command=lambda: self._set_interfaces(nid))
        menu.add_separator()
        menu.add_command(label='⎘  Copy', command=lambda: self._copy_node(nid))
        menu.add_command(label='✂  Cut', command=lambda: self._cut_node(nid))
        menu.add_separator()
        menu.add_command(label='✕  Delete', command=lambda: self._model.remove_node(nid))
        menu.tk_popup(e.x_root, e.y_root)

    def _link_context(self, e, lid):
        menu = tk.Menu(self._cv, tearoff=0, bg=C['bg2'], fg=C['text'], font=FM.small, activebackground=C['menu_sel'], activeforeground=C['text'])
        menu.add_command(label='✏  Edit link specs…', command=lambda: self._edit_link(lid))
        menu.add_separator()
        menu.add_command(label='✕  Delete', command=lambda: self._model.remove_link(lid))
        menu.tk_popup(e.x_root, e.y_root)

    def _edit_node(self, nid):
        nd = self._model.nodes.get(nid)
        if nd:
            SpecDialog(self.winfo_toplevel(), nd, f"{nd['kind']} — {nid}")
            self._full_redraw()

    def _edit_link(self, lid):
        lk = self._model.links.get(lid)
        if lk:
            if 'kind' not in lk:
                lk['kind'] = 'Fiber'
            SpecDialog(self.winfo_toplevel(), lk, f'Fiber link — {lid}')
            self._full_redraw()

    def _set_interfaces(self, nid):
        nd = self._model.nodes[nid]
        dlg = tk.Toplevel(self.winfo_toplevel())
        dlg.title(f'Interfaces — {nid}')
        dlg.configure(bg=C['bg'])
        dlg.grab_set()
        dlg.resizable(False, False)
        n_in_var = tk.IntVar(value=int(nd.get('n_inputs', 2)))
        n_out_var = tk.IntVar(value=int(nd.get('n_outputs', 2)))
        for i, (lbl, var) in enumerate([('Input interfaces:', n_in_var), ('Output interfaces:', n_out_var)]):
            tk.Label(dlg, text=lbl, font=FM.small, fg=C['text'], bg=C['bg']).grid(row=i, column=0, padx=14, pady=8, sticky='w')
            tk.Spinbox(dlg, from_=1, to=16, textvariable=var, width=5, font=FM.mono, bg=C['bg3'], fg=C['text'], relief='flat').grid(row=i, column=1, padx=8)
        _sep(dlg).grid(row=2, columnspan=2, sticky='ew', pady=6)

        def _ok():
            nd['n_inputs'] = n_in_var.get()
            nd['n_outputs'] = n_out_var.get()
            dlg.destroy()
            self._full_redraw()
        _button(dlg, 'OK', command=_ok, padx=14, pady=4).grid(row=3, column=0, padx=14, pady=8, sticky='w')
        _ghost_button(dlg, 'Cancel', command=dlg.destroy, padx=10, pady=4).grid(row=3, column=1, sticky='w')

    def _delete_selected(self):
        if self._selected_nid and self._selected_nid in self._model.nodes:
            self._model.remove_node(self._selected_nid)
            self._selected_nid = None
        elif self._selected_lid and self._selected_lid in self._model.links:
            self._model.remove_link(self._selected_lid)
            self._selected_lid = None

    def _copy_node(self, nid):
        import copy
        self._clipboard = copy.deepcopy(self._model.nodes[nid])

    def _cut_node(self, nid):
        self._copy_node(nid)
        self._model.remove_node(nid)

    def _copy(self):
        if self._selected_nid:
            self._copy_node(self._selected_nid)

    def _cut(self):
        if self._selected_nid:
            self._cut_node(self._selected_nid)

    def _paste(self):
        if self._clipboard is None:
            return
        import copy
        new_nd = copy.deepcopy(self._clipboard)
        new_id = NetworkModel._new_id(new_nd['kind'].lower())
        new_nd['id'] = new_id
        new_nd['label'] = new_id
        new_nd['x'] = new_nd.get('x', 100) + self.GRID * 3
        new_nd['y'] = new_nd.get('y', 100) + self.GRID * 3
        self._model.nodes[new_id] = new_nd
        self._model._notify()
        self._selected_nid = new_id

class SwitchDesigner(tk.Toplevel):

    def __init__(self, master, switch_nd):
        super().__init__(master)
        self.title(f"Switch Advanced Design — {switch_nd['id']}")
        self.configure(bg=C['bg'])
        self.geometry('900x620')
        self._nd = switch_nd
        self._int_model = NetworkModel()
        self._build()

    def _build(self):
        tk.Label(self, text=f"  Internal design of {self._nd['id']}", font=FM.head, fg=C['warning'], bg=C['bg'], anchor='w', padx=12, pady=10).pack(fill='x')
        _sep(self).pack(fill='x')
        tb = tk.Frame(self, bg=C['bg'], height=40)
        tb.pack(fill='x')
        tb.pack_propagate(False)
        tk.Label(tb, text='  Add:', font=FM.small, fg=C['muted'], bg=C['bg']).pack(side='left')
        for kind, color in [('BS', C['accent2']), ('PBS', C['comm']), ('BSM', C['danger'])]:
            _ghost_button(tb, kind, accent=color, command=lambda k=kind: self._add(k), padx=8, pady=3).pack(side='left', padx=2, pady=4)
        self._mode_btns = {}
        self._canvas_widget = None
        for mode, lbl in [('select', '↖ Select'), ('link', '⟵ Wire'), ('delete', '✕ Del')]:
            b = _ghost_button(tb, lbl, command=lambda m=mode: self._set_mode(m), padx=7, pady=3)
            b.pack(side='left', padx=2, pady=4)
            self._mode_btns[mode] = b
        self._canvas_widget = NetworkCanvas(self, self._int_model)
        self._canvas_widget.pack(fill='both', expand=True)
        self._set_mode('select')
        self._draw_stubs()
        _sep(self).pack(fill='x')
        _ghost_button(self, 'Close', command=self.destroy, padx=14, pady=5).pack(side='right', padx=14, pady=8)

    def _set_mode(self, mode):
        if self._canvas_widget:
            self._canvas_widget.set_mode(mode)
        for m, b in self._mode_btns.items():
            b.config(bg=C['accent'] if m == mode else C['bg2'], fg=C['bg2'] if m == mode else C['accent'])

    def _add(self, kind):
        if self._canvas_widget:
            self._canvas_widget.add_component(kind)

    def _draw_stubs(self):
        n_in = int(self._nd.get('n_inputs', 2))
        n_out = int(self._nd.get('n_outputs', 2))
        for i in range(n_in):
            nid = self._int_model.add_node('BS', x=40, y=60 + i * 80)
            nd = self._int_model.nodes[nid]
            nd['label'] = f'EXT_IN{i + 1}'
            nd['n_inputs'] = 0
            nd['n_outputs'] = 1
        for i in range(n_out):
            nid = self._int_model.add_node('BS', x=700, y=60 + i * 80)
            nd = self._int_model.nodes[nid]
            nd['label'] = f'EXT_OUT{i + 1}'
            nd['n_inputs'] = 1
            nd['n_outputs'] = 0

class NetworkPanel(_Frame):
    OPTICAL_SPECS = [('Optical arm', 'arm_split_A', 'Arm-A share of total path', '0.5', '0–1', 'entry', None), ('Optical arm', 'alpha_dB_km', 'Fibre attenuation α', '0.2', 'dB/km', 'entry', None), ('Optical arm', 'n_g', 'Group refractive index nᵍ', '1.47', '', 'entry', None), ('Optical arm', 'eta_int_A', 'Interface efficiency ηint,A', '0.69', '0–1', 'entry', None), ('Optical arm', 'eta_int_B', 'Interface efficiency ηint,B', '0.69', '0–1', 'entry', None), ('Detection', 'eta_d', 'Detector efficiency ηd', '0.88', '0–1', 'entry', None), ('Detection', 'V', 'Interference visibility V', '0.98', '0–1', 'entry', None), ('Detection', 'm', 'Heralded Bell-state index m', '1', 'integer', 'entry', None), ('Excess noise', 'P_d', 'Dark-count probability Pd', '5e-8', '0–1', 'entry', None), ('Excess noise', 'nbar_1', 'Background photon number n̄₁', '1e-2', '', 'entry', None), ('Local timing', 'T_lo_A_us', 'Local latency Tlo,A', '5.5', 'µs', 'entry', None), ('Local timing', 'T_lo_B_us', 'Local latency Tlo,B', '5.5', 'µs', 'entry', None), ('Local timing', 'T_idle_A_us', 'Baseline idle Tidle,A', '0', 'µs', 'entry', None), ('Local timing', 'T_idle_B_us', 'Baseline idle Tidle,B', '0', 'µs', 'entry', None), ('Communication coherence', 'T1_A_us', 'Communication T1,A', '12000000000', 'µs', 'entry', None), ('Communication coherence', 'T2_A_us', 'Communication T2,A', '2800000', 'µs', 'entry', None), ('Communication coherence', 'T1_B_us', 'Communication T1,B', '12000000000', 'µs', 'entry', None), ('Communication coherence', 'T2_B_us', 'Communication T2,B', '2800000', 'µs', 'entry', None), ('Generation timing', 'direct_attempt_us', 'Direct-link attempt period', '0.1', 'µs', 'entry', None), ('Generation timing', 'target', 'Bell-state target', 'heralded', '', 'menu', ('heralded', '+', '-'))]
    ALL_PHOTONIC_SWITCH_SPECS = [('All-photonic switch', 'fabric', 'Switch fabric', 'tree', '', 'menu', ('tree', 'crossbar')), ('All-photonic switch', 'N', 'Fabric ports N', '40', 'ports', 'entry', None), ('All-photonic switch', 'eta_1', 'Tree-stage transmissivity η₁', '0.79', '0–1', 'entry', None), ('All-photonic switch', 'delta_1_us', 'Tree-stage delay δ₁', '0.0001', 'µs', 'entry', None), ('All-photonic switch', 'eta_c', 'Crossbar transmissivity ηc', '0.63', '0–1', 'entry', None), ('All-photonic switch', 'delta_c_us', 'Crossbar delay δc', '0.0001', 'µs', 'entry', None), ('All-photonic switch', 'T_conf_us', 'Configuration time Tconf', '0.1', 'µs', 'entry', None), ('All-photonic switch', 'eps_sw', 'Switch crosstalk εsw', '1e-4', '0–1', 'entry', None), ('Switch sharing', 'M', 'Concurrent requests M', '8', 'count', 'entry', None), ('Switch sharing', 'M_BSM', 'BSM modules MBSM', '5', 'count', 'entry', None), ('Switch sharing', 'forest', 'Split tree as forest', 'True', '', 'menu', ('True', 'False')), ('Switch sharing', 'xtalk_full_N', 'Crosstalk uses full N', 'True', '', 'menu', ('True', 'False')), ('Switch sharing', 'exact_ceil', 'Ceil request/BSM ratio', 'True', '', 'menu', ('True', 'False'))]
    MEMORY_SPECS = [('Memory-assisted switch', 'delta_t_c_us', 'Memory coherence constant Δtc', '2800000', 'µs', 'entry', None), ('Memory-assisted switch', 'F_I', 'Initial stored-pair fidelity FI', '0.9796744718797619', '0–1', 'entry', None), ('Memory-assisted switch', 'p_swap', 'Memory SWAP success probability', '1.0', '0–1', 'entry', None), ('Memory-assisted switch', 'n_memory_slots', 'Memory slots per link', '1', 'count', 'entry', None), ('Memory-assisted switch', 'warm_start_cycles', 'Warm-start cycles', '25', 'cycles', 'entry', None)]

    def __init__(self, parent):
        super().__init__(parent)
        self._model = NetworkModel()
        self._tab_frames = {}
        self._physical_vars = {}
        self._link_rows = []
        self._recalc_after = None
        self._build()

    def _build(self):
        _panel_header(self, '◈  Network', 'Configure QPU capacity and the physical entanglement architecture used by QNEST.', C['accent2'])
        tab_bar = _frame(self, bg=C['bg3'])
        tab_bar.pack(fill='x')
        for name in ('Table', 'Designer'):
            btn = tk.Label(tab_bar, text=name, font=FM.menu, fg=C['muted'], bg=C['bg3'], padx=20, pady=10, cursor='hand2')
            btn.pack(side='left')
            btn.bind('<Button-1>', lambda e, n=name: self._switch(n))
            setattr(self, f'_tab_{name}', btn)
        _sep(self).pack(fill='x')
        container = _frame(self)
        container.pack(fill='both', expand=True)
        t1 = _frame(container)
        t1.place(relx=0, rely=0, relwidth=1, relheight=1)
        t2 = _frame(container)
        t2.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._build_table(t1)
        self._tab_frames['Table'] = t1
        self._build_designer(t2)
        self._tab_frames['Designer'] = t2
        self._switch('Table')

    def _switch(self, name):
        self._active_assistant_tab = name
        for n in ('Table', 'Designer'):
            btn = getattr(self, f'_tab_{n}')
            btn.config(fg=C['accent2'] if n == name else C['muted'], bg=C['bg2'] if n == name else C['bg3'])
        self._tab_frames[name].lift()

    def _init_physical_vars(self):
        seen = set()
        for spec in self.OPTICAL_SPECS + self.ALL_PHOTONIC_SWITCH_SPECS + self.MEMORY_SPECS:
            _g, key, _l, default, _u, _k, _c = spec
            if key not in seen:
                self._physical_vars[key] = tk.StringVar(value=default)
                self._physical_vars[key].trace_add('write', lambda *_: self._schedule_recalc())
                seen.add(key)

    def _build_table(self, parent):
        self._init_physical_vars()
        canvas = tk.Canvas(parent, bg=C['bg2'], highlightthickness=0)
        vsb = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        hsb = ttk.Scrollbar(parent, orient='horizontal', command=canvas.xview)
        canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side='right', fill='y')
        hsb.pack(side='bottom', fill='x')
        canvas.pack(side='left', fill='both', expand=True)
        inner = _frame(canvas)
        win = canvas.create_window((0, 0), window=inner, anchor='nw')

        def _sync_table_view(_e=None):
            try:
                viewport = max(1, canvas.winfo_width())
                tables = [getattr(self, name, None) for name in ('_table_frame', '_physical_card')]
                table_need = max([int(t.winfo_reqwidth()) + 56 for t in tables if t is not None] or [0])
                required = max(viewport, table_need)
                extra = max(0, required - viewport)
                for name in ('_network_top', '_architecture_card', '_link_help', '_physical_title_row', '_physical_help', '_network_controls'):
                    widget = getattr(self, name, None)
                    if widget is None:
                        continue
                    try:
                        if _pad_pair(widget.pack_info().get('padx', 0)) != (28, 28 + extra):
                            widget.pack_configure(padx=(28, 28 + extra))
                    except Exception:
                        pass
                canvas.itemconfig(win, width=required)
                canvas.configure(scrollregion=canvas.bbox('all'))
            except Exception:
                pass
        inner.bind('<Configure>', _sync_table_view)
        canvas.bind('<Configure>', _sync_table_view)
        self._table_canvas = canvas
        top = _card(inner, padx=16, pady=12)
        top.pack(fill='x', padx=28, pady=(18, 10))
        self._network_top = top
        self._network_servers_label = _label(top, 'Servers:', bg=C['bg2'])
        self._n_srv = tk.IntVar(value=NOTEBOOK_REFERENCE_DEFAULTS['n_qpus'])
        srv = tk.Spinbox(top, from_=2, to=32, textvariable=self._n_srv, width=5, font=FM.mono, bg=C['bg3'], fg=C['text'], buttonbackground=C['bg3'], relief='flat', command=self._topology_changed)
        self._network_servers_widget = srv
        srv.bind('<FocusOut>', lambda _e: self._topology_changed())
        srv.bind('<Return>', lambda _e: self._topology_changed())
        self._network_qppq_label = _label(top, 'Qubits per QPU:', bg=C['bg2'])
        self._qppq = tk.IntVar(value=NOTEBOOK_REFERENCE_DEFAULTS['qubits_per_qpu'])
        qppq = tk.Spinbox(top, from_=1, to=10000, textvariable=self._qppq, width=7, font=FM.mono, bg=C['bg3'], fg=C['text'], buttonbackground=C['bg3'], relief='flat')
        self._network_qppq_widget = qppq
        self._network_topology_label = _label(top, 'Topology:', bg=C['bg2'])
        self._topo = tk.StringVar(value='All-to-all')
        om = tk.OptionMenu(top, self._topo, 'All-to-all', 'Linear chain', 'Star', 'Ring', 'Custom', command=lambda *_: self._topology_changed())
        om.config(font=FM.small, bg=C['bg3'], fg=C['text'], activebackground=C['accent2'], relief='flat')
        om['menu'].config(bg=C['bg3'], fg=C['text'])
        self._network_topology_widget = om
        self._capacity_text = tk.StringVar()
        self._capacity_label = tk.Label(top, textvariable=self._capacity_text, font=FM.small, fg=C['muted'], bg=C['bg2'], anchor='w', justify='left')
        self._network_top.bind('<Configure>', self._layout_network_top, add='+')
        self._n_srv.trace_add('write', lambda *_: self._update_capacity())
        self._qppq.trace_add('write', lambda *_: self._update_capacity())
        self._update_capacity()
        self._architecture_card = _card(inner, padx=16, pady=10)
        self._architecture_card.pack(fill='x', padx=28, pady=(0, 10))
        self._interconnect = tk.StringVar(value='Shared switch')
        self._switch_mode = tk.StringVar(value='Memory-assisted')
        self._interconnect.trace_add('write', lambda *_: self._architecture_changed())
        self._switch_mode.trace_add('write', lambda *_: self._architecture_changed())
        self._rebuild_architecture_controls()
        _section_label(inner, 'Physical links and calculated performance', C['accent2'])
        self._link_help = _label(inner, '', fg=C['muted'], font=FM.small, justify='left', anchor='w', wraplength=1150)
        self._link_help.pack(fill='x', anchor='w', padx=28, pady=(0, 8))
        self._table_frame = _card(inner)
        self._table_frame.pack(fill='x', padx=28, pady=(0, 14))
        self._physical_title = tk.StringVar()
        title_row = _frame(inner)
        title_row.pack(fill='x', padx=28, pady=(4, 4))
        self._physical_title_row = title_row
        self._physical_title_label = tk.Label(title_row, textvariable=self._physical_title, font=FM.subh, fg=C['accent2'], bg=C['bg2'], anchor='w')
        self._derived_memory = tk.StringVar()
        self._derived_memory_label = tk.Label(title_row, textvariable=self._derived_memory, font=FM.small_mono, fg=C['muted'], bg=C['bg2'], anchor='w', justify='left')
        self._physical_title_row.bind('<Configure>', self._layout_network_title_row, add='+')
        self._physical_help = _label(inner, '', fg=C['muted'], font=FM.small, wraplength=1450, justify='left', anchor='w')
        self._physical_help.pack(fill='x', anchor='w', padx=28, pady=(0, 8))
        self._physical_card = _card(inner)
        self._physical_card.pack(fill='x', padx=28, pady=(0, 10))
        controls = _frame(inner)
        controls.pack(fill='x', padx=28, pady=(0, 18))
        self._network_controls = controls
        self._network_defaults_btn = _ghost_button(controls, '↺  Model defaults', accent=C['accent2'], command=self._reset_physical_defaults, padx=10, pady=5)
        self._network_recalc_btn = _ghost_button(controls, '↻  Recalculate', accent=C['accent2'], command=self._recalculate_links, padx=10, pady=5)
        self._network_sync_btn = _button(controls, '⟳  Sync topology to Designer', accent=C['accent2'], command=self._sync_to_designer, padx=12, pady=6)
        self._model_status = _label(controls, '', fg=C['muted'], anchor='w', justify='left')
        self._network_controls.bind('<Configure>', self._layout_network_controls, add='+')
        self._topology_changed()

    def _layout_network_top(self, _event=None):
        if not hasattr(self, '_network_top'):
            return
        try:
            width = max(320, int(self._network_top.winfo_width()))
        except Exception:
            width = 1100
        widgets = [(self._network_servers_label, self._network_servers_widget), (self._network_qppq_label, self._network_qppq_widget), (self._network_topology_label, self._network_topology_widget)]
        cols = 3 if width >= 1020 else 2 if width >= 680 else 1
        for w in [x for pair in widgets for x in pair] + [self._capacity_label]:
            try:
                w.grid_forget()
            except Exception:
                pass
        for c in range(8):
            try:
                self._network_top.grid_columnconfigure(c, weight=0)
            except Exception:
                pass
        for i, (lbl, ctl) in enumerate(widgets):
            row = i // cols
            col = i % cols * 2
            lbl.grid(row=row, column=col, sticky='w', padx=(0, 5), pady=4)
            ctl.grid(row=row, column=col + 1, sticky='w', padx=(0, 20), pady=4)
        cap_row = (len(widgets) + cols - 1) // cols
        self._capacity_label.grid(row=cap_row, column=0, columnspan=max(2, cols * 2), sticky='ew', pady=(5, 0))
        try:
            self._network_top.grid_columnconfigure(max(1, cols * 2 - 1), weight=1)
        except Exception:
            pass

    def _layout_network_title_row(self, _event=None):
        if not hasattr(self, '_physical_title_row'):
            return
        try:
            width = max(320, int(self._physical_title_row.winfo_width()))
        except Exception:
            width = 900
        for widget in (self._physical_title_label, self._derived_memory_label):
            try:
                widget.grid_forget()
            except Exception:
                pass
        self._physical_title_label.grid(row=0, column=0, sticky='ew')
        self._derived_memory_label.grid(row=1, column=0, sticky='ew', pady=(3, 0))
        self._derived_memory_label.config(wraplength=max(260, width - 12))
        self._physical_title_row.grid_columnconfigure(0, weight=1)

    def _layout_network_controls(self, _event=None):
        if not hasattr(self, '_network_controls'):
            return
        try:
            width = max(320, int(self._network_controls.winfo_width()))
        except Exception:
            width = 900
        controls = [self._network_defaults_btn, self._network_recalc_btn, self._network_sync_btn]
        cols = 3 if width >= 850 else 2 if width >= 560 else 1
        for w in controls + [self._model_status]:
            try:
                w.grid_forget()
            except Exception:
                pass
        for i, w in enumerate(controls):
            r, c = divmod(i, cols)
            w.grid(row=r, column=c, sticky='w', padx=(0, 8), pady=(0, 6))
        status_row = (len(controls) + cols - 1) // cols
        self._model_status.grid(row=status_row, column=0, columnspan=cols, sticky='ew', pady=(2, 0))
        for c in range(cols):
            self._network_controls.grid_columnconfigure(c, weight=1)

    def refresh_layout(self):
        self._layout_network_top()
        self._layout_network_title_row()
        self._layout_network_controls()
        try:
            _fluid_apply(self._link_help)
            _fluid_apply(self._physical_help)
        except Exception:
            pass
        self._rebuild_architecture_controls()

    def _update_capacity(self):
        try:
            self._capacity_text.set(f'Total computation capacity: {int(self._n_srv.get()) * int(self._qppq.get())} qubits')
        except Exception:
            self._capacity_text.set('Total computation capacity: —')

    def _topology_changed(self):
        if self._topo.get() != 'All-to-all' and self._topo.get() != 'Custom':
            self._interconnect.set('Direct QPU links')
        self._rebuild_architecture_controls()
        self._refresh_table()
        self._rebuild_physical_table()
        self._notify_run_availability()

    def _architecture_changed(self):
        if not hasattr(self, '_physical_card'):
            return
        self._rebuild_architecture_controls()
        self._refresh_table()
        self._rebuild_physical_table()
        self._notify_run_availability()

    def _notify_run_availability(self):
        try:
            root = self.winfo_toplevel()
            run = getattr(root, '_panels', {}).get('Run')
            if run is not None and hasattr(run, 'refresh_run_mode'):
                run.after_idle(run.refresh_run_mode)
        except Exception:
            pass

    def _rebuild_architecture_controls(self):
        if not hasattr(self, '_architecture_card'):
            return
        card = self._architecture_card
        for w in card.winfo_children():
            w.destroy()
        topo = self._topo.get()
        heading = _label(card, 'Entanglement architecture:', font=FM.subh, bg=C['bg2'])
        specs = [{'widget': heading, 'mr': 16, 'mt': 3, 'mb': 3}]
        if topo == 'All-to-all':
            for value in ('Direct QPU links', 'Shared switch'):
                rb = tk.Radiobutton(card, text=value, variable=self._interconnect, value=value, font=FM.small, bg=C['bg2'], fg=C['text'], selectcolor=C['bg3'], activebackground=C['bg4'], activeforeground=C['text'], disabledforeground=C['muted'])
                specs.append({'widget': rb, 'mr': 14, 'mt': 3, 'mb': 3})
            if self._interconnect.get() == 'Shared switch':
                sl = _label(card, 'Switch type:', bg=C['bg2'], font=FM.small)
                sm = tk.OptionMenu(card, self._switch_mode, 'All-photonic', 'Memory-assisted')
                sm.config(font=FM.small, bg=C['bg3'], fg=C['text'], activebackground=C['accent2'], relief='flat', width=16)
                sm['menu'].config(bg=C['bg3'], fg=C['text'])
                specs.append({'widget': sl, 'glue': True, 'mr': 6, 'mt': 3, 'mb': 3})
                specs.append({'widget': sm, 'mt': 3, 'mb': 3})
        else:
            text = 'Defined by QPU / Switch / Link elements in Designer.' if topo == 'Custom' else 'Direct QPU-to-QPU links (switch-free predefined topology).'
            msg = _label(card, text, fg=C['muted'], bg=C['bg2'], font=FM.small, justify='left', anchor='w')
            specs.append({'widget': msg, 'stretch': True, 'wrap': True, 'minw': _scaled(220), 'mt': 3, 'mb': 3})
        self._architecture_flow = _FlowLayout(card, specs, gap_y=2)

    def _is_switched(self):
        return self._topo.get() == 'All-to-all' and self._interconnect.get() == 'Shared switch'

    def _active_model(self):
        if self._is_switched():
            return 'memory-assisted' if self._switch_mode.get() == 'Memory-assisted' else 'all-photonic-switch'
        return 'direct-all-photonic'

    def _active_specs(self):
        mode = self._active_model()
        if mode == 'all-photonic-switch':
            return self.ALL_PHOTONIC_SWITCH_SPECS + self.OPTICAL_SPECS
        if mode == 'memory-assisted':
            return self.MEMORY_SPECS + self.ALL_PHOTONIC_SWITCH_SPECS + self.OPTICAL_SPECS
        return self.OPTICAL_SPECS

    def _rebuild_physical_table(self):
        if not hasattr(self, '_physical_card'):
            return
        for w in self._physical_card.winfo_children():
            w.destroy()
        mode = self._active_model()
        if mode == 'all-photonic-switch':
            self._physical_title.set('All-photonic switch physical model')
            self._physical_help.config(text='Switch-fabric, optical-arm, detector, excess-noise, timing and coherence parameters are used directly by src/all_photonic_noise.py.')
        elif mode == 'memory-assisted':
            self._physical_title.set('Memory-assisted switch physical model')
            self._physical_help.config(text='Memory parameters are shown together with the one-arm all-photonic characteristics that create entanglement before storage. Static link Psucc is photonic; stored-pair fidelity then decays with the HAMFA memory law during Run.')
        else:
            self._physical_title.set('Direct all-photonic link model (no switch)')
            self._physical_help.config(text='The same optical/noise equations are used with switch loss, switch crosstalk and switch propagation delay bypassed. Each QPU pair is a direct physical entanglement link.')
        headers = ('Group', 'Parameter', 'Value', 'Unit')
        for c, text in enumerate(headers):
            tk.Label(self._physical_card, text=text, font=FM.subh, fg=C['accent2'], bg=C['bg3'], anchor='w', padx=8, pady=6).grid(row=0, column=c, sticky='nsew')
        self._physical_card.grid_columnconfigure(0, minsize=220, weight=1)
        self._physical_card.grid_columnconfigure(1, minsize=420, weight=3)
        self._physical_card.grid_columnconfigure(2, minsize=210, weight=1)
        self._physical_card.grid_columnconfigure(3, minsize=120, weight=1)
        last_group = None
        for r, (group, key, label, _default, unit, kind, choices) in enumerate(self._active_specs(), start=1):
            bg = C['bg2'] if r % 2 else C['bg3']
            gtext = group if group != last_group else ''
            last_group = group
            tk.Label(self._physical_card, text=gtext, font=FM.small, fg=C['muted'], bg=bg, anchor='w', padx=8, pady=4).grid(row=r, column=0, sticky='nsew')
            tk.Label(self._physical_card, text=label, font=FM.small, fg=C['text'], bg=bg, anchor='w', padx=8, pady=4).grid(row=r, column=1, sticky='nsew')
            var = self._physical_vars[key]
            cell = _frame(self._physical_card, bg=bg)
            cell.grid(row=r, column=2, sticky='nsew', padx=0, pady=0)
            if kind == 'menu':
                ww = tk.OptionMenu(cell, var, *choices)
                ww.config(font=FM.small, bg=C['bg2'] if bg == C['bg3'] else C['bg3'], fg=C['text'], relief='flat', width=17)
                ww['menu'].config(bg=C['bg3'], fg=C['text'])
            else:
                ww = tk.Entry(cell, textvariable=var, font=FM.mono, bg=C['bg2'] if bg == C['bg3'] else C['bg3'], fg=C['text'], insertbackground=C['accent2'], relief='flat')
                ww.bind('<FocusOut>', lambda _e: self._schedule_recalc())
                ww.bind('<Return>', lambda _e: self._schedule_recalc())
            ww.pack(fill='x', padx=6, pady=3)
            tk.Label(self._physical_card, text=unit, font=FM.small, fg=C['muted'], bg=bg, anchor='w', padx=8).grid(row=r, column=3, sticky='nsew')
        self._derived_memory.set('HAMFA cutoff/fidelity-threshold parameters are configured in Run; memory coherence is physical.' if mode == 'memory-assisted' else '')
        self._schedule_recalc()

    def _pairs(self):
        n = int(self._n_srv.get())
        topo = self._topo.get()
        if topo == 'All-to-all':
            return [(i, j) for i in range(n) for j in range(i + 1, n)]
        if topo == 'Star':
            return [(0, j) for j in range(1, n)]
        if topo == 'Ring':
            return [(i, i + 1) for i in range(n - 1)] + ([(n - 1, 0)] if n > 2 else [])
        if topo == 'Custom':
            return []
        return [(i, i + 1) for i in range(n - 1)]

    def _refresh_table(self):
        if not hasattr(self, '_table_frame'):
            return
        previous = {tuple(rd['pair']): rd['dist_var'].get() for _i, rd in self._link_rows if 'pair' in rd}
        for w in self._table_frame.winfo_children():
            w.destroy()
        pairs = self._pairs()
        headers = ('Link', 'Distance (km)', 'Psucc', 'Fidelity', 'Attempt rate (Hz)', 'Ebit rate (Hz)', 'Propagation (µs)')
        mins = (160, 175, 155, 155, 190, 190, 180)
        for c, (h, m) in enumerate(zip(headers, mins)):
            self._table_frame.grid_columnconfigure(c, minsize=m, weight=1 if c else 0)
            tk.Label(self._table_frame, text=h, font=FM.subh, fg=C['accent2'], bg=C['bg3'], anchor='w', padx=8, pady=7).grid(row=0, column=c, sticky='nsew')
        self._link_rows = []
        if not pairs:
            tk.Label(self._table_frame, text='Custom topology — create QPUs, switches and links in Designer.', font=FM.small, fg=C['muted'], bg=C['bg2'], anchor='w', padx=8, pady=12).grid(row=1, column=0, columnspan=7, sticky='ew')
            self._link_help.config(text='Custom graphs use the Designer as the authoritative physical topology.')
            return
        if self._active_model() == 'memory-assisted':
            self._link_help.config(text='Distance is editable. Psucc and attempt/Ebit rates come from the photonic generation model; Fidelity shows FI initially and HAMFA applies memory-age decay during Run.')
        else:
            self._link_help.config(text='Only physical distance is edited per link. Success probability, fidelity, attempt rate, Ebit rate and propagation delay are calculated from the selected QNEST physical model.')
        for r, pair in enumerate(pairs, start=1):
            a, b = pair
            bg = C['bg2'] if r % 2 else C['bg3']
            tk.Label(self._table_frame, text=f'S{a} ↔ S{b}', font=FM.small_mono, fg=C['text'], bg=bg, anchor='w', padx=8, pady=5).grid(row=r, column=0, sticky='nsew')
            dist_var = tk.StringVar(value=previous.get(pair, '0.2'))
            holder = _frame(self._table_frame, bg=bg)
            holder.grid(row=r, column=1, sticky='nsew')
            ent = tk.Entry(holder, textvariable=dist_var, font=FM.mono, bg=C['bg3'] if bg == C['bg2'] else C['bg2'], fg=C['text'], insertbackground=C['accent2'], relief='flat')
            ent.pack(fill='x', padx=7, pady=4)
            dist_var.trace_add('write', lambda *_: self._schedule_recalc())
            rd = {'pair': pair, 'dist_var': dist_var}
            for c, key in enumerate(('psucc', 'fidelity', 'attempt_rate', 'ebit_rate', 'latency'), start=2):
                var = tk.StringVar(value='—')
                rd[key] = var
                tk.Label(self._table_frame, textvariable=var, font=FM.small_mono, fg=C['text'], bg=bg, anchor='w', padx=8, pady=5).grid(row=r, column=c, sticky='nsew')
            self._link_rows.append((r, rd))
        self._schedule_recalc()

    @staticmethod
    def _bool_value(value):
        return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}

    def _f(self, key):
        return float(self._physical_vars[key].get())

    def get_physical_params(self, distance_km=None):
        distance = 0.2 if distance_km is None else float(distance_km)
        if distance < 0:
            raise ValueError('Link distance must be non-negative.')
        split = self._f('arm_split_A')
        if not 0 <= split <= 1:
            raise ValueError('Arm-A share must be between 0 and 1.')
        mode = self._active_model()
        switched = self._is_switched()
        return {'fabric': self._physical_vars['fabric'].get() if switched else 'crossbar', 'N': self._f('N') if switched else 2.0, 'eta_1': self._f('eta_1') if switched else 1.0, 'delta_1': self._f('delta_1_us') * 1e-06 if switched else 0.0, 'eta_c': self._f('eta_c') if switched else 1.0, 'delta_c': self._f('delta_c_us') * 1e-06 if switched else 0.0, 'T_conf': (self._f('T_conf_us') if switched else self._f('direct_attempt_us')) * 1e-06, 'L_A_km': distance * split, 'L_B_km': distance * (1 - split), 'alpha_dB_km': self._f('alpha_dB_km'), 'n_g': self._f('n_g'), 'eta_int_A': self._f('eta_int_A'), 'eta_int_B': self._f('eta_int_B'), 'eta_A': None, 'eta_B': None, 'eta_d': self._f('eta_d'), 'V': self._f('V'), 'm': int(self._f('m')), 'P_d': self._f('P_d'), 'eps_sw': self._f('eps_sw') if switched else 0.0, 'nbar_1': self._f('nbar_1'), 'T_hrld_A': None, 'T_hrld_B': None, 'T_lo_A': self._f('T_lo_A_us') * 1e-06, 'T_lo_B': self._f('T_lo_B_us') * 1e-06, 'T_idle_A': self._f('T_idle_A_us') * 1e-06, 'T_idle_B': self._f('T_idle_B_us') * 1e-06, 'T1_A': self._f('T1_A_us') * 1e-06, 'T2_A': self._f('T2_A_us') * 1e-06, 'T1_B': self._f('T1_B_us') * 1e-06, 'T2_B': self._f('T2_B_us') * 1e-06, 'M': self._f('M') if switched else 1.0, 'M_BSM': self._f('M_BSM') if switched else 1.0, 'forest': self._bool_value(self._physical_vars['forest'].get()) if switched else False, 'xtalk_full_N': self._bool_value(self._physical_vars['xtalk_full_N'].get()) if switched else False, 'exact_ceil': self._bool_value(self._physical_vars['exact_ceil'].get()) if switched else True, 'target': self._physical_vars['target'].get()}

    def memory_model_config(self):
        dt_us = self._f('delta_t_c_us')
        return {'delta_t_c_ns': dt_us * 1000.0, 'F_I': self._f('F_I'), 'p_swap': self._f('p_swap'), 'n_memory_slots': int(self._f('n_memory_slots')), 'warm_start_cycles': self._f('warm_start_cycles'), 'source': 'src/hamfa_qsp.py + src/memory_assisted_noise.py'}

    def protocol_physical_parameters(self):
        self._recalculate_links()
        metrics = []
        for _idx, rd in self._link_rows:
            m = rd.get('metrics')
            if m is None:
                try:
                    m = self._calculate_link_metrics(rd)
                except Exception:
                    continue
            metrics.append(m)
        if not metrics:
            for link in self._model.links.values():
                try:
                    metrics.append({'success_probability': float(link['success_probability']), 'fidelity': float(link['fidelity']), 'attempt_rate_hz': float(link['attempt_rate_hz'])})
                except Exception:
                    pass
        if not metrics:
            raise ValueError('The Network page has no valid physical link metrics. Recalculate or define the network first.')
        import statistics
        ps = [float(m['success_probability']) for m in metrics]
        fs = [float(m['fidelity']) for m in metrics]
        periods_ns = [1000000000.0 / float(m['attempt_rate_hz']) for m in metrics if float(m['attempt_rate_hz']) > 0]
        mem = self.memory_model_config()
        return {'p_succ': statistics.fmean(ps), 'p_succ_ap': statistics.fmean(ps), 'time_per_trial_ns': statistics.fmean(periods_ns), 'afa_fidelity': statistics.fmean(fs), 'delta_t_c_ns': float(mem['delta_t_c_ns']), 'F_I': float(mem['F_I']), 'link_count': len(metrics), 'p_succ_range': (min(ps), max(ps)), 'fidelity_range': (min(fs), max(fs)), 'trial_time_us_range': (min(periods_ns) / 1000.0, max(periods_ns) / 1000.0)}

    def physical_model_config(self):
        mode = self._active_model()
        out = {'model': mode, 'interconnect': self._interconnect.get(), 'switch_mode': self._switch_mode.get() if self._is_switched() else None, 'source': 'src/all_photonic_noise.py', 'editable': {key: var.get() for key, var in self._physical_vars.items()}, 'distance_mapping': 'L_A = distance * arm_split_A; L_B = distance * (1-arm_split_A)'}
        if mode == 'memory-assisted':
            out['memory'] = self.memory_model_config()
        return out

    def _schedule_recalc(self):
        if not hasattr(self, '_link_rows'):
            return
        try:
            if self._recalc_after is not None:
                self.after_cancel(self._recalc_after)
        except Exception:
            pass
        self._recalc_after = self.after(120, self._recalculate_links)

    def _calculate_link_metrics(self, rd):
        from src.all_photonic_noise import C_LIGHT, P_succ, F_cond, f_attempt, R_time
        distance = float(rd['dist_var'].get())
        params = self.get_physical_params(distance)
        ps = float(P_succ(params))
        attempts = float(f_attempt(params))
        rate = float(R_time(params))
        fidelity = self._f('F_I') if self._active_model() == 'memory-assisted' else float(F_cond(params))
        vg = float(C_LIGHT) / float(params['n_g'])
        latency_us = distance * 1000.0 / vg * 1000000.0
        return {'distance_km': distance, 'success_probability': ps, 'fidelity': fidelity, 'attempt_rate_hz': attempts, 'ebit_rate_hz': rate, 'propagation_latency_us': latency_us}

    @staticmethod
    def _fmt_metric(value, scientific=False):
        try:
            value = float(value)
        except Exception:
            return '—'
        if scientific or abs(value) >= 100000.0 or 0 < abs(value) < 0.0001:
            return f'{value:.4e}'
        return f'{value:.6g}'

    def _recalculate_links(self):
        self._recalc_after = None
        first_error = None
        if self._active_model() == 'memory-assisted':
            try:
                self._rebuild_physical_table_memory_derived_only()
            except Exception:
                pass
        for _idx, rd in self._link_rows:
            try:
                m = self._calculate_link_metrics(rd)
                rd['metrics'] = m
                rd['psucc'].set(self._fmt_metric(m['success_probability']))
                rd['fidelity'].set(self._fmt_metric(m['fidelity']))
                rd['attempt_rate'].set(self._fmt_metric(m['attempt_rate_hz'], True))
                rd['ebit_rate'].set(self._fmt_metric(m['ebit_rate_hz'], True))
                rd['latency'].set(self._fmt_metric(m['propagation_latency_us']))
            except Exception as exc:
                for key in ('psucc', 'fidelity', 'attempt_rate', 'ebit_rate', 'latency'):
                    rd[key].set('ERR')
                if first_error is None:
                    first_error = str(exc)
        if hasattr(self, '_model_status'):
            self._model_status.config(text=f'Physical-model error: {first_error}' if first_error else '✓ Physical performance recalculated', fg=C['danger'] if first_error else C['success'])

    def _rebuild_physical_table_memory_derived_only(self):
        if self._active_model() != 'memory-assisted':
            return
        self._derived_memory.set('HAMFA cutoff/fidelity-threshold parameters are configured in Run; memory coherence is physical.')

    def _reset_physical_defaults(self):
        for spec in self.OPTICAL_SPECS + self.ALL_PHOTONIC_SWITCH_SPECS + self.MEMORY_SPECS:
            _g, key, _l, default, _u, _k, _c = spec
            self._physical_vars[key].set(default)
        self._rebuild_physical_table()
        self._recalculate_links()

    def _layout_positions(self, n, topo):
        import math
        if topo == 'Linear chain':
            return [(120 + i * 210, 220) for i in range(n)]
        if topo == 'Star':
            pos = [(470, 300)]
            radius = max(220, 48 * n)
            for i in range(1, n):
                ang = -math.pi / 2 + 2 * math.pi * (i - 1) / max(1, n - 1)
                pos.append((470 + radius * math.cos(ang), 300 + radius * math.sin(ang)))
            return pos
        radius = max(200, 52 * n)
        cx, cy = (500, 330)
        return [(cx + radius * math.cos(-math.pi / 2 + 2 * math.pi * i / n), cy + radius * math.sin(-math.pi / 2 + 2 * math.pi * i / n)) for i in range(n)]

    def _table_network_data(self):
        n = int(self._n_srv.get())
        q = int(self._qppq.get())
        topo = self._topo.get()
        if n < 2:
            raise ValueError('At least two QPU servers are required.')
        if q < 1:
            raise ValueError('Qubits per QPU must be at least 1.')
        if topo == 'Custom':
            raise ValueError('Custom topology is defined in Designer.')
        pairs = self._pairs()
        pos = self._layout_positions(n, topo)
        nodes = []
        links = []
        if self._is_switched():
            for i, (x, y) in enumerate(pos):
                nodes.append({'id': f'qpu_{i}', 'kind': 'QPU', 'label': f'S{i}', 'x': round(x), 'y': round(y), 'qubits': str(q), 'n_inputs': 1, 'n_outputs': 1})
            sx = sum((x for x, _ in pos)) / n
            sy = sum((y for _, y in pos)) / n
            nodes.append({'id': 'switch_0', 'kind': 'Switch', 'label': f'{self._switch_mode.get()} switch', 'x': round(sx), 'y': round(sy), 'n_inputs': n, 'n_outputs': n, 'switch_mode': self._switch_mode.get()})
            per_qpu_dist = {i: [] for i in range(n)}
            for (_r, rd), (a, b) in zip(self._link_rows, pairs):
                d = float(rd['dist_var'].get())
                per_qpu_dist[a].append(d / 2)
                per_qpu_dist[b].append(d / 2)
            for i in range(n):
                arm_dist = sum(per_qpu_dist[i]) / len(per_qpu_dist[i]) if per_qpu_dist[i] else 0.1
                dummy = {'dist_var': tk.StringVar(value=str(2 * arm_dist))}
                m = self._calculate_link_metrics(dummy)
                links.append({'id': f'link_{i:03d}', 'label': f'S{i}↔SW', 'src': f'qpu_{i}', 'dst': 'switch_0', 'src_port': 'out1', 'dst_port': f'in{i + 1}', 'kind': 'Fiber', 'length': str(arm_dist), 'show_label': False, 'success_probability': m['success_probability'], 'fidelity': m['fidelity'], 'attempt_rate_hz': m['attempt_rate_hz'], 'ebit_rate_hz': m['ebit_rate_hz'], 'propagation_latency_us': m['propagation_latency_us']})
        else:
            deg = {i: 0 for i in range(n)}
            for a, b in pairs:
                deg[a] += 1
                deg[b] += 1
            for i, (x, y) in enumerate(pos):
                ports = max(2, deg[i])
                nodes.append({'id': f'qpu_{i}', 'kind': 'QPU', 'label': f'S{i}', 'x': round(x), 'y': round(y), 'qubits': str(q), 'n_inputs': ports, 'n_outputs': ports})
            out = {i: 0 for i in range(n)}
            inc = {i: 0 for i in range(n)}
            for k, ((a, b), (_r, rd)) in enumerate(zip(pairs, self._link_rows)):
                out[a] += 1
                inc[b] += 1
                m = self._calculate_link_metrics(rd)
                links.append({'id': f'link_{k:03d}', 'label': f'S{a}↔S{b}', 'src': f'qpu_{a}', 'dst': f'qpu_{b}', 'src_port': f'out{out[a]}', 'dst_port': f'in{inc[b]}', 'kind': 'Fiber', 'length': str(m['distance_km']), 'auto_layout': True, 'visual_bend': (k % 3 - 1) * 18.0 if topo == 'All-to-all' else 0, 'show_label': not (topo == 'All-to-all' and n >= 4), 'success_probability': m['success_probability'], 'fidelity': m['fidelity'], 'attempt_rate_hz': m['attempt_rate_hz'], 'ebit_rate_hz': m['ebit_rate_hz'], 'propagation_latency_us': m['propagation_latency_us']})
        return {'nodes': nodes, 'links': links, 'source': f'table:{topo}', 'settings': {'n_qpus': n, 'qubits_per_qpu': q, 'topology': topo, 'total_computation_qubits': n * q, 'interconnect': self._interconnect.get(), 'switch_mode': self._switch_mode.get() if self._is_switched() else None}, 'logical_links': [list(x) for x in pairs], 'physical_model': self.physical_model_config()}

    def get_network_data(self):
        if self._topo.get() != 'Custom':
            return self._table_network_data()
        if not self._model.nodes:
            raise ValueError('Custom topology is empty. Build it in Designer first.')
        q = int(self._qppq.get())
        nodes = [dict(v) for v in self._model.nodes.values()]
        for nd in nodes:
            if str(nd.get('kind', '')).upper() == 'QPU':
                nd['qubits'] = str(q)
        return {'nodes': nodes, 'links': [dict(v) for v in self._model.links.values()], 'source': 'designer:custom', 'settings': {'qubits_per_qpu': q, 'topology': 'Custom', 'n_qpus': sum((str(n.get('kind', '')).upper() == 'QPU' for n in nodes))}, 'physical_model': self.physical_model_config()}

    def _sync_to_designer(self):
        if self._topo.get() == 'Custom':
            self._switch('Designer')
            return
        try:
            data = self._table_network_data()
        except Exception as exc:
            messagebox.showerror('Network', str(exc))
            return
        self._model.nodes.clear()
        self._model.links.clear()
        for nd in data['nodes']:
            self._model.nodes[nd['id']] = dict(nd)
        for lk in data['links']:
            self._model.links[lk['id']] = dict(lk)
        self._model._notify()
        self._switch('Designer')
        try:
            self.after(80, self._canvas.fit_to_network)
        except Exception:
            pass

    def _build_designer(self, parent):
        tb = tk.Frame(parent, bg=C['bg'], height=44, highlightbackground=C['border'], highlightthickness=1)
        tb.pack(fill='x')
        tb.pack_propagate(False)
        _label(tb, '  Add:', fg=C['muted'], bg=C['bg'], font=FM.small).pack(side='left')
        for kind in ('QPU', 'Switch'):
            color = NetworkCanvas.KIND_COLOR[kind]
            icon = NetworkCanvas.KIND_ICON[kind]
            _ghost_button(tb, f'{icon} {kind}', accent=color, command=lambda k=kind: self._canvas.add_component(k), padx=8, pady=4).pack(side='left', padx=2, pady=4)
        tk.Frame(tb, bg=C['border'], width=1).pack(side='left', fill='y', padx=6)
        self._mode_btns = {}
        for mode, label in (('select', '↖ Select'), ('link', '⟵ Link'), ('delete', '✕ Delete')):
            b = _ghost_button(tb, label, accent=C['accent2'], command=lambda m=mode: self._set_mode(m), padx=8, pady=4)
            b.pack(side='left', padx=2, pady=4)
            self._mode_btns[mode] = b
        tk.Frame(tb, bg=C['border'], width=1).pack(side='left', fill='y', padx=6)
        _ghost_button(tb, 'Fit network', accent=C['accent2'], command=lambda: self._canvas.fit_to_network(), padx=8, pady=4).pack(side='left', padx=2, pady=4)
        _ghost_button(tb, '💾 Export JSON', command=self._export, padx=8, pady=4).pack(side='left', padx=2, pady=4)
        _ghost_button(tb, '📂 Import JSON', command=self._import, padx=8, pady=4).pack(side='left', padx=2, pady=4)
        _ghost_button(tb, '🗑 Clear all', accent=C['danger'], command=self._clear, padx=5, pady=4).pack(side='left', padx=2, pady=4)
        tb.configure(highlightthickness=1, pady=0)
        _flow_from_pack(tb, gap_y=0)
        self._canvas = NetworkCanvas(parent, self._model)
        self._canvas.pack(fill='both', expand=True)
        self._set_mode('select')

    def _set_mode(self, mode):
        self._canvas.set_mode(mode)
        for m, b in self._mode_btns.items():
            b.config(bg=C['accent2'] if m == mode else C['bg2'], fg=C['bg2'] if m == mode else C['accent2'])

    def _export(self):
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON', '*.json'), ('All', '*.*')])
        if path:
            try:
                import json
                with open(path, 'w', encoding='utf-8') as fh:
                    json.dump(self.get_network_data(), fh, indent=2)
                messagebox.showinfo('Saved', f'Network saved to:\n{path}')
            except Exception as exc:
                messagebox.showerror('Error', str(exc))

    def _import(self):
        path = filedialog.askopenfilename(filetypes=[('JSON', '*.json'), ('All', '*.*')])
        if not path:
            return
        try:
            import json
            with open(path, encoding='utf-8') as fh:
                obj = json.load(fh)
            settings = obj.get('settings', {})
            if 'qubits_per_qpu' in settings:
                self._qppq.set(int(settings['qubits_per_qpu']))
            self._topo.set('Custom')
            self._model.nodes.clear()
            self._model.links.clear()
            for nd in obj.get('nodes', []):
                self._model.nodes[nd['id']] = nd
            for lk in obj.get('links', []):
                self._model.links[lk['id']] = lk
            self._model._notify()
            self._rebuild_architecture_controls()
            self._refresh_table()
            self._rebuild_physical_table()
        except Exception as exc:
            messagebox.showerror('Import error', str(exc))

    def _clear(self):
        if messagebox.askyesno('Clear network', 'Remove all components and links?'):
            self._model.nodes.clear()
            self._model.links.clear()
            self._model._notify()

class CompileCircuitPreview(_Frame):
    STAGES = [('01_original', 'Original'), ('02_cleaned', 'Cleaned'), ('03_dqc_prepared', 'After DQCPass'), ('04_distributed_real', 'Distributed circuit'), ('05_ejpp_representation', 'EJPP representation')]

    def __init__(self, parent):
        super().__init__(parent)
        self._label_to_stem = {label: stem for stem, label in self.STAGES}
        self._stage_label = tk.StringVar(value='Distributed circuit')
        header = _frame(self)
        header.pack(fill='x', pady=(0, 6))
        _label(header, 'Compiled Circuit Representations', font=FM.subh, fg=C['text']).pack(side='left')
        _ghost_button(header, 'Save representation…', accent=C['success'], command=self._save_representation, padx=9, pady=4).pack(side='right')
        _ghost_button(header, 'Open QASM', accent=C['success'], command=self._open_qasm, padx=9, pady=4).pack(side='right', padx=6)
        _ghost_button(header, 'Open interactive', accent=C['success'], command=self._open_visual, padx=9, pady=4).pack(side='right')
        _flow_from_pack(header, overrides={header.pack_slaves()[0]: {'wrap': False}})
        stages = _frame(self, bg=C['bg3'])
        stages.pack(fill='x', pady=(0, 6))
        circuit_row = _frame(stages, bg=C['bg3'])
        circuit_row.pack(fill='x')
        tk.Label(circuit_row, text='Circuit', font=FM.small, fg=C['muted'], bg=C['bg3'], padx=8, pady=6).pack(side='left')
        self._circuit_choice = ttk.Combobox(circuit_row, state='readonly', width=26)
        self._circuit_choice.pack(side='left', padx=(0, 14), pady=4)
        self._circuit_choice.bind('<<ComboboxSelected>>', self._on_circuit_changed)
        _flow_from_pack(circuit_row, gap_y=0, overrides={self._circuit_choice: {'shrink': True, 'minw': _scaled(160)}})
        self._circuit_ids = []
        stage_row = _frame(stages, bg=C['bg3'])
        stage_row.pack(fill='x', pady=(0, 2))
        tk.Label(stage_row, text='Representation stage', font=FM.small, fg=C['muted'], bg=C['bg3'], padx=8, pady=6).pack(side='left')
        self._stage_buttons = {}
        for _stem, label in self.STAGES:
            btn = tk.Radiobutton(stage_row, text=label, variable=self._stage_label, value=label, indicatoron=False, command=self.refresh, font=FM.small, bg=C['bg3'], fg=C['text'], selectcolor=C['bg2'], activebackground=C['bg4'], activeforeground=C['text'], disabledforeground=C['muted'], relief='flat', bd=0, padx=8, pady=5, cursor='hand2')
            btn.pack(side='left', padx=(0, 2), pady=2)
            self._stage_buttons[label] = btn
        _flow_from_pack(stage_row, gap_y=0)
        self._meta = _label(self, 'Compile/distribute a circuit to populate the preview.', font=FM.small, fg=C['muted'])
        self._meta.pack(fill='x', pady=(0, 6))
        holder = tk.Frame(self, bg=C['bg3'], highlightbackground=C['border'], highlightthickness=1)
        holder.pack(fill='both', expand=True)
        self._canvas = _ExactPytketCircuitCanvas(holder)
        self._canvas.pack(fill='both', expand=True)

    def _stem(self):
        return self._label_to_stem.get(self._stage_label.get(), '04_distributed_real')

    def refresh_circuits(self):
        root = self.winfo_toplevel()
        records = root.circuit_records() if hasattr(root, 'circuit_records') else []
        available = []
        ids = []
        for rec in records:
            ctl = root.get_pipeline_for_circuit(rec.get('id'), create=False) if hasattr(root, 'get_pipeline_for_circuit') else None
            if ctl is None or ctl.state.run_dir is None:
                continue
            q = rec.get('qubits')
            available.append(f"{rec.get('name', 'circuit')}  •  {(q if q is not None else '?')} qubits  •  {rec.get('source', '')}")
            ids.append(rec.get('id'))
        self._circuit_ids = ids
        self._circuit_choice['values'] = available
        if ids:
            active = getattr(root, '_active_circuit_id', None)
            idx = ids.index(active) if active in ids else 0
            self._circuit_choice.current(idx)
        else:
            self._circuit_choice.set('')

    def _on_circuit_changed(self, _event=None):
        idx = self._circuit_choice.current()
        if 0 <= idx < len(self._circuit_ids):
            root = self.winfo_toplevel()
            root.activate_circuit(self._circuit_ids[idx], create=False)
            self.refresh()
            panel = root._panels.get('Compile') if hasattr(root, '_panels') else None
            if panel is not None and hasattr(panel, '_display_scope_data'):
                try:
                    panel._display_scope_data(force_specific=self._circuit_ids[idx])
                    panel._artifacts.refresh()
                except Exception:
                    pass

    def _base(self):
        run_dir = self.winfo_toplevel().pipeline.state.run_dir
        return run_dir / '03_compile' / self._stem() if run_dir else None

    def select_distributed(self):
        self._stage_label.set('Distributed circuit')
        self.refresh()

    def refresh(self):
        base = self._base()
        if not base:
            self._meta.config(text='Compile/distribute a circuit to populate the preview.')
            self._canvas._show_empty('Compile/distribute a circuit to populate the exact pytket preview.')
            return
        qasm_path = base.with_suffix('.qasm')
        if not qasm_path.exists():
            err = base.with_suffix('.qasm.error.txt')
            detail = ''
            if err.exists():
                try:
                    detail = '  •  ' + err.read_text(encoding='utf-8', errors='replace').splitlines()[0]
                except Exception:
                    pass
            self._meta.config(text=f'{self._stage_label.get()} • QASM representation unavailable{detail}')
            self._canvas._show_empty(f'{self._stage_label.get()} representation unavailable{detail}')
            return
        try:
            qasm = qasm_path.read_text(encoding='utf-8', errors='replace')
            bits = []
            txt_path = base.with_suffix('.txt')
            if txt_path.exists():
                for line in txt_path.read_text(encoding='utf-8', errors='replace').splitlines()[:6]:
                    if line.startswith(('Qubits:', 'Gates:', 'Depth:')):
                        bits.append(line.replace(':', ' ', 1))
            suffix = '  •  '.join(bits)
            label = self._stage_label.get()
            self._meta.config(text=label + (f'  •  {suffix}' if suffix else ''))
            html_path = base.with_suffix('.html')
            snapshot_path = base.with_suffix('.renderer.png')
            snapshot_error = None
            try:
                meta = self.winfo_toplevel().pipeline.state.compile_metadata or {}
                snapshot_error = ((meta.get('renderer_snapshots') or {}).get(self._stem()) or {}).get('error')
            except Exception:
                pass
            self._canvas.show(snapshot_path=snapshot_path if snapshot_path.exists() else None, html_path=html_path if html_path.exists() else None, qasm_text=qasm, error=snapshot_error)
        except Exception as exc:
            self._meta.config(text=f'Could not render {self._stage_label.get()}: {exc}')
            self._canvas._show_empty(str(exc))

    def _open_visual(self):
        base = self._base()
        if not base:
            return
        html = base.with_suffix('.html')
        if html.exists():
            _open_local_path(html)
            return
        qasm = base.with_suffix('.qasm')
        if qasm.exists():
            _open_local_path(qasm)
        else:
            messagebox.showwarning('QNEST', 'No visual or QASM representation is available for this stage.')

    def _open_qasm(self):
        base = self._base()
        if not base:
            return
        qasm = base.with_suffix('.qasm')
        if qasm.exists():
            _open_local_path(qasm)
        else:
            messagebox.showwarning('QNEST', 'This stage has no QASM representation.')

    def _save_representation(self):
        base = self._base()
        if not base:
            return
        existing = [base.with_suffix(ext) for ext in ('.html', '.renderer.png', '.qasm', '.json', '.txt') if base.with_suffix(ext).exists()]
        if not existing:
            messagebox.showwarning('QNEST', 'No saved representation is available for this stage.')
            return
        src = existing[0]
        dest = filedialog.asksaveasfilename(initialfile=src.name, defaultextension=src.suffix, filetypes=[('Current representation', f'*{src.suffix}'), ('All files', '*.*')])
        if dest:
            shutil.copy2(src, dest)
            messagebox.showinfo('Saved', f'Representation copied to:\n{dest}')

class CompilePanel(_Frame):
    DISTRIBUTION_METHODS = ['PartitioningAnnealing', 'PartitioningHeterogeneous', 'PartitioningHeterogeneousEmbedding', 'CoverEmbedding', 'CoverEmbeddingSteiner', 'CoverEmbeddingSteinerDetached']

    def __init__(self, parent):
        super().__init__(parent)
        self._busy = False
        self._scope_ids = []
        self._batch_results = []
        self._build()

    def _build(self):
        _panel_header(self, '◈  Compile', 'Prepare with DQCPass, distribute with pytket-dqc, and preserve every circuit stage.', C['success'])
        _body = _ResponsiveBody(self, flex_min=320)
        _body.pack(fill='both', expand=True)
        host = _body.inner
        self._responsive_body = _body
        opts = _card(host, padx=16, pady=12)
        opts.pack(fill='x', padx=28, pady=(16, 10))
        self._compile_opts = opts
        self._scope = tk.StringVar(value='Active circuit')
        self._compile_scope_label = tk.Label(opts, text='Circuit scope:', font=FM.small, fg=C['muted'], bg=C['bg2'])
        self._scope_combo = ttk.Combobox(opts, textvariable=self._scope, state='readonly', width=38)
        self._scope_combo.bind('<<ComboboxSelected>>', lambda _e: self._on_scope_changed())
        self._method = tk.StringVar(value=NOTEBOOK_REFERENCE_DEFAULTS['distribution_method'])
        self._seed = tk.StringVar(value=str(NOTEBOOK_REFERENCE_DEFAULTS['distribution_seed']))
        self._circuit_name = tk.StringVar(value='circuit')
        self._compile_method_label = tk.Label(opts, text='Distribution method:', font=FM.small, fg=C['muted'], bg=C['bg2'])
        self._compile_method_menu = tk.OptionMenu(opts, self._method, *self.DISTRIBUTION_METHODS)
        self._compile_method_menu.config(font=FM.small, bg=C['bg3'], fg=C['text'], relief='flat', width=34)
        self._compile_method_menu['menu'].config(bg=C['bg3'], fg=C['text'])
        self._compile_seed_label = tk.Label(opts, text='Seed:', font=FM.small, fg=C['muted'], bg=C['bg2'])
        self._compile_seed_entry = tk.Entry(opts, textvariable=self._seed, width=18, font=FM.mono, bg=C['bg3'], fg=C['text'], insertbackground=C['success'], relief='flat')
        self._compile_name_label = tk.Label(opts, text='Run name:', font=FM.small, fg=C['muted'], bg=C['bg2'])
        self._compile_name_entry = tk.Entry(opts, textvariable=self._circuit_name, width=18, font=FM.mono, bg=C['bg3'], fg=C['text'], insertbackground=C['success'], relief='flat')
        self._compile_option_pairs = [(self._compile_scope_label, self._scope_combo), (self._compile_method_label, self._compile_method_menu), (self._compile_seed_label, self._compile_seed_entry), (self._compile_name_label, self._compile_name_entry)]
        self._compile_opts.bind('<Configure>', self._layout_compile_options, add='+')
        action = _frame(host)
        action.pack(fill='x', padx=28, pady=(0, 10))
        self._compile_action = action
        self._compile_btn = _button(action, '▶  Prepare + Distribute', accent=C['success'], command=self._compile, padx=18, pady=7)
        self._compile_open_btn = _ghost_button(action, 'Open run folder', accent=C['success'], command=self._open_run, padx=11, pady=7)
        self._compile_export_btn = _ghost_button(action, 'Export whole run…', accent=C['success'], command=self._export_run, padx=11, pady=7)
        self._status = _label(action, 'Ready', fg=C['muted'], anchor='w')
        self._progress = ttk.Progressbar(action, mode='determinate', length=180)
        self._compile_action_flow = _FlowLayout(action, [{'widget': self._compile_btn, 'mr': 8}, {'widget': self._compile_open_btn, 'mr': 8}, {'widget': self._compile_export_btn, 'mr': 8}, {'widget': self._status, 'stretch': True, 'wrap': True, 'minw': _scaled(140), 'ml': 6, 'mr': 8}, {'widget': self._progress, 'stretch': True, 'minw': _scaled(160)}], gap_y=6)
        self._stats = {}
        statrow = _frame(host)
        statrow.pack(fill='x', padx=28, pady=(0, 10))
        self._compile_statrow = statrow
        self._compile_stat_cards = []
        for key, title in [('n_qubits', 'Input qubits'), ('n_gates_distributed', 'Distributed gates'), ('distributed_depth', 'Distributed depth'), ('ebits_builtin', 'EPR / ebits'), ('n_qpus', 'QPUs')]:
            card = _card(statrow, padx=14, pady=8)
            var = tk.StringVar(value='—')
            self._stats[key] = var
            tk.Label(card, textvariable=var, font=FM.head, fg=C['success'], bg=C['bg2']).pack()
            tk.Label(card, text=title, font=FM.small, fg=C['muted'], bg=C['bg2']).pack()
            self._compile_stat_cards.append(card)
        self._compile_statrow.bind('<Configure>', self._layout_compile_stats, add='+')
        self._nb = ttk.Notebook(host)
        self._nb.pack(fill='both', expand=True, padx=28, pady=(0, 18))
        preview_frame = _frame(self._nb)
        self._compile_preview = CompileCircuitPreview(preview_frame)
        self._compile_preview.pack(fill='both', expand=True, padx=6, pady=6)
        self._nb.add(preview_frame, text='Circuit preview')
        self._preview_tab = preview_frame
        f = _frame(self._nb)
        self._summary = TableView(f)
        self._summary.pack(fill='both', expand=True, padx=6, pady=6)
        self._nb.add(f, text='Overview')
        f = _frame(self._nb)
        self._artifacts = ArtifactBrowser(f, ('01_circuit', '02_network', '03_compile'))
        self._artifacts.pack(fill='both', expand=True, padx=6, pady=6)
        self._nb.add(f, text='Saved artifacts')
        f = _frame(self._nb)
        self._log = scrolledtext.ScrolledText(f, font=FM.mono, bg=C['bg3'], fg=C['text'], insertbackground=C['success'], relief='flat', padx=10, pady=8, state='disabled')
        self._log.pack(fill='both', expand=True, padx=6, pady=6)
        self._nb.add(f, text='Log')

    def _layout_compile_options(self, _event=None):
        if not hasattr(self, '_compile_opts'):
            return
        try:
            width = max(320, int(self._compile_opts.winfo_width()))
        except Exception:
            width = 900
        pairs = list(getattr(self, '_compile_option_pairs', []))
        if not pairs:
            return
        ctrl_min = _scaled(230)
        need = [int(lbl.winfo_reqwidth()) + 8 + min(int(widget.winfo_reqwidth()), ctrl_min) + 24 for lbl, widget in pairs]
        cols = _fit_columns(width - 2 * _internal_border(self._compile_opts, 'x'), need, choices=(2,))
        for col in range(max(8, cols * 2 + 1)):
            try:
                self._compile_opts.grid_columnconfigure(col, weight=0)
            except Exception:
                pass
        for index, (lbl, widget) in enumerate(pairs):
            lbl.grid_forget()
            widget.grid_forget()
            row = index // cols
            col = index % cols * 2
            lbl.grid(row=row, column=col, sticky='w', padx=(0, 8), pady=5)
            widget.grid(row=row, column=col + 1, sticky='ew', padx=(0, 24 if col == 0 else 0), pady=5)
            try:
                self._compile_opts.grid_columnconfigure(col + 1, weight=1)
            except Exception:
                pass

    def _layout_compile_stats(self, _event=None):
        if not hasattr(self, '_compile_statrow'):
            return
        try:
            width = max(320, int(self._compile_statrow.winfo_width()))
        except Exception:
            width = 1200
        cards = list(getattr(self, '_compile_stat_cards', []))
        if not cards:
            return
        need = [int(card.winfo_reqwidth()) + 8 for card in cards]
        cols = _fit_columns(width, need, choices=(5, 3, 2))
        for col in range(8):
            try:
                self._compile_statrow.grid_columnconfigure(col, weight=0)
            except Exception:
                pass
        for i, card in enumerate(cards):
            card.pack_forget()
            card.grid_forget()
            r, c = divmod(i, cols)
            card.grid(row=r, column=c, sticky='ew', padx=(0, 8), pady=(0, 8))
        for c in range(cols):
            try:
                self._compile_statrow.grid_columnconfigure(c, weight=1)
            except Exception:
                pass

    def _layout_compile_action(self, _event=None):
        flow = getattr(self, '_compile_action_flow', None)
        if flow is not None:
            flow.schedule()

    def refresh_layout(self):
        self._layout_compile_options()
        self._layout_compile_stats()
        self._layout_compile_action()

    def on_show(self):
        self.refresh_circuit_context()

    def refresh_circuit_context(self):
        root = self.winfo_toplevel()
        records = root.circuit_records() if hasattr(root, 'circuit_records') else []
        labels = []
        ids = []
        batch = getattr(root._panels.get('Circuit'), 'is_batch_mode', lambda: False)()
        if batch and len(records) > 1:
            labels.append(f'All circuits ({len(records)})')
            ids.append(None)
        for rec in records:
            labels.append(f"{rec.get('name')}  •  {(rec.get('qubits') if rec.get('qubits') is not None else '?')}q  •  {rec.get('source', '')}")
            ids.append(rec.get('id'))
        self._scope_ids = ids
        self._scope_combo['values'] = labels
        if labels:
            current = self._scope_combo.current()
            if current < 0 or current >= len(labels):
                self._scope_combo.current(0 if batch and len(records) > 1 else len(labels) - 1 if len(labels) == 1 else 0)
        self._compile_preview.refresh_circuits()
        self._display_scope_data()

    def _scope_id(self):
        i = self._scope_combo.current()
        return self._scope_ids[i] if 0 <= i < len(self._scope_ids) else None

    def _targets(self):
        records = self.winfo_toplevel().circuit_records()
        sid = self._scope_id()
        if sid is None and len(self._scope_ids) and (self._scope_ids[0] is None):
            return records
        return [r for r in records if r.get('id') == sid] if sid else records[:1]

    def _on_scope_changed(self):
        sid = self._scope_id()
        if sid:
            self.winfo_toplevel().activate_circuit(sid, create=False)
        self._display_scope_data()
        self._compile_preview.refresh_circuits()
        self._compile_preview.refresh()
        self._artifacts.refresh()

    def _log_write(self, msg):
        self._log.config(state='normal')
        self._log.insert('end', str(msg) + '\n')
        self._log.see('end')
        self._log.config(state='disabled')

    def _network_data(self, qppq=None):
        panel = self.winfo_toplevel()._panels['Network']
        data = panel.get_network_data()
        data.setdefault('settings', {})['qubits_per_qpu'] = int(panel._qppq.get())
        return data

    def _compile(self):
        if self._busy:
            return
        root = self.winfo_toplevel()
        circuit = root._panels['Circuit']
        records = circuit.get_circuit_records()
        if not records:
            qasm = circuit._editor_text.get('1.0', 'end').strip()
            if not qasm or qasm.startswith('// QASM will appear'):
                messagebox.showwarning('Compile', 'Import, generate, or paste a valid OpenQASM circuit first.')
                return
            name = self._circuit_name.get().strip() or 'circuit'
            rec = circuit._add_circuit(name=name, qasm_text=qasm + '\n', source='QASM Editor', series=name, replace_single=True)
            circuit.activate_record(rec['id'])
            root.on_circuit_set_changed()
            self.refresh_circuit_context()
            records = circuit.get_circuit_records()
        targets = self._targets()
        if not targets:
            messagebox.showwarning('Compile', 'No circuit is selected.')
            return
        try:
            seed = int(self._seed.get())
            qppq = int(root._panels['Network']._qppq.get())
            if qppq < 1:
                raise ValueError
            network_data = self._network_data(qppq)
        except Exception as exc:
            messagebox.showerror('Compile', f'Check Seed, Qubits per QPU, and Network settings.\n\n{exc}')
            return
        self._busy = True
        self._compile_btn.config(state='disabled')
        self._status.config(text=f'Working on {len(targets)} circuit(s)…', fg=C['warning'])
        self._progress['maximum'] = max(1, len(targets))
        self._progress['value'] = 0
        self._log.config(state='normal')
        self._log.delete('1.0', 'end')
        self._log.config(state='disabled')

        def worker():
            completed = []
            failed = []
            for idx, rec in enumerate(targets, 1):
                try:
                    self.after(0, lambda i=idx, n=rec.get('name'): self._status.config(text=f'Compiling {i}/{len(targets)} • {n}', fg=C['warning']))
                    ctl = root.get_pipeline_for_circuit(rec['id'], create=True)
                    run_name = rec.get('name') or 'circuit'
                    if len(targets) == 1 and (not circuit.is_batch_mode()):
                        typed = self._circuit_name.get().strip()
                        if typed and typed != 'circuit':
                            run_name = typed
                    meta = ctl.compile(qasm_text=rec.get('qasm_text', ''), network_data=network_data, circuit_name=run_name, distribution_method=self._method.get(), seed=seed, qubits_per_qpu=qppq, log=lambda m, n=rec.get('name'): self.after(0, lambda msg=m, name=n: self._log_write(f'[{name}] {msg}')))
                    completed.append((rec, meta, ctl))
                    self.after(0, lambda i=idx: self._progress.config(value=i))
                except Exception as exc:
                    failed.append((rec, exc))
                    self.after(0, lambda i=idx: self._progress.config(value=i))
                    self.after(0, lambda e=exc, n=rec.get('name'): self._log_write(f'[{n}] [ERROR] {type(e).__name__}: {e}'))
            self.after(0, lambda: self._compile_batch_done(completed, failed))
        threading.Thread(target=worker, daemon=True).start()

    def _compile_batch_done(self, completed, failed):
        self._busy = False
        self._compile_btn.config(state='normal')
        if completed:
            rec, meta, ctl = completed[0]
            self.winfo_toplevel().activate_circuit(rec['id'], create=False)
            for key, var in self._stats.items():
                var.set(str(meta.get(key, '—')))
            self._status.config(text=f'✓ {len(completed)}/{len(completed) + len(failed)} distribution(s) ready', fg=C['success'] if not failed else C['warning'])
        else:
            self._status.config(text='✕ Batch failed', fg=C['danger'])
        rows = []
        for rec, meta, _ctl in completed:
            rows.append({'circuit': rec.get('name'), 'source': rec.get('source'), 'series': rec.get('series'), 'n_qubits': meta.get('n_qubits', rec.get('qubits')), 'n_gates_original': meta.get('n_gates_original'), 'depth_original': meta.get('depth_original'), 'n_gates_distributed': meta.get('n_gates_distributed'), 'distributed_depth': meta.get('distributed_depth'), 'epr_pairs': meta.get('ebits_builtin'), 'n_qpus': meta.get('n_qpus'), 'status': 'ok', 'error': ''})
        for rec, exc in failed:
            rows.append({'circuit': rec.get('name'), 'source': rec.get('source'), 'series': rec.get('series'), 'n_qubits': rec.get('qubits'), 'status': 'failed', 'error': f'{type(exc).__name__}: {exc}'})
        self._batch_results = rows
        if len(rows) > 1:
            self.winfo_toplevel().save_batch_table('01_compile', rows, 'compile_summary.csv')
        self._display_scope_data(force_rows=rows if len(rows) > 1 else None)
        self._compile_preview.refresh_circuits()
        self._compile_preview.select_distributed()
        self._artifacts.refresh()
        try:
            self._nb.select(self._preview_tab)
        except Exception:
            pass
        for _r, _m, ctl in completed:
            ctl.write_manifest()
        if failed and (not completed):
            messagebox.showerror('QNEST compile/distribution', f'All {len(failed)} circuit(s) failed. See the Compile log for details.')

    def _display_scope_data(self, force_rows=None, force_specific=None):
        root = self.winfo_toplevel()
        sid = force_specific if force_specific is not None else self._scope_id()
        if force_rows is not None:
            self._summary.set_data(force_rows)
            return
        if sid is None and self._batch_results:
            self._summary.set_data(self._batch_results)
            return
        if sid:
            ctl = root.get_pipeline_for_circuit(sid, create=False)
            if ctl and ctl.state.compile_metadata:
                meta = ctl.state.compile_metadata
                preferred = ['distribution_method', 'n_qubits', 'n_gates_original', 'depth_original', 'n_qpus', 'qubits_per_qpu', 'n_gates_distributed', 'depth_distributed_pytket', 'distributed_depth', 'n_qubits_representation', 'n_gates_representation', 'ebits_builtin', 'ebit_memory', 'source_link_qubits_required', 'placement', 'dqc_links']
                self._summary.set_data([{'metric': k, 'value': _safe_text(meta[k])} for k in preferred if k in meta])
                for key, var in self._stats.items():
                    var.set(str(meta.get(key, '—')))
                return
        if not self._batch_results:
            self._summary.clear()

    def _open_run(self):
        run_dir = self.winfo_toplevel().pipeline.state.run_dir
        if run_dir:
            _open_local_path(run_dir)

    def _export_run(self):
        root = self.winfo_toplevel()
        circuit = root._panels['Circuit']
        if circuit.is_batch_mode() and len(root.circuit_records()) > 1 and (root._batch_dir is not None):
            dest = filedialog.asksaveasfilename(defaultextension='.zip', filetypes=[('ZIP archive', '*.zip')], initialfile=f'{root._batch_dir.name}.zip')
            if dest:
                try:
                    out = root.export_batch_zip(dest)
                    messagebox.showinfo('Exported', f'Complete QNEST batch saved to:\n{out}')
                except Exception as exc:
                    messagebox.showerror('Export error', str(exc))
            return
        if root.pipeline.state.run_dir is None:
            messagebox.showwarning('Export', 'There is no active run yet.')
            return
        dest = filedialog.asksaveasfilename(defaultextension='.zip', filetypes=[('ZIP archive', '*.zip')], initialfile=f'{root.pipeline.state.run_dir.name}.zip')
        if dest:
            try:
                root.pipeline.write_manifest()
                out = root.pipeline.export_session_zip(dest)
                messagebox.showinfo('Exported', f'Complete QNEST run saved to:\n{out}')
            except Exception as exc:
                messagebox.showerror('Export error', str(exc))

class _ScheduleHtmlPreview(tk.Frame):
    MIN_VIEW_HEIGHT = 430

    def __init__(self, parent):
        super().__init__(parent, bg=C['bg3'], height=self.MIN_VIEW_HEIGHT)
        self.pack_propagate(False)
        self._photo = None
        self._source_image = None
        self._view_mode = 'fit_width'
        self._resize_after = None
        status = tk.Frame(self, bg=C['bg3'])
        status.pack(fill='x')
        self._notice = tk.Label(status, text='Generate a schedule to view the Gantt here.', font=FM.small, fg=C['muted'], bg=C['bg3'], anchor='w', padx=8, pady=5)
        self._notice.pack(side='left', fill='x', expand=True)
        self._fit_btn = _segmented_button(status, 'Fit width', command=lambda: self._set_view_mode('fit_width'), selected=True, padx=10, pady=3)
        self._fit_btn.pack(side='right', padx=(4, 8), pady=3)
        self._actual_btn = _segmented_button(status, '100%', command=lambda: self._set_view_mode('100'), padx=10, pady=3)
        self._actual_btn.pack(side='right', pady=3)
        _flow_from_pack(status, gap_y=2)
        holder = tk.Frame(self, bg='#FFFFFF')
        holder.pack(fill='both', expand=True)
        holder.grid_rowconfigure(0, weight=1)
        holder.grid_columnconfigure(0, weight=1)
        self._canvas = tk.Canvas(holder, bg='#FFFFFF', highlightthickness=0, xscrollincrement=24, yscrollincrement=24, height=self.MIN_VIEW_HEIGHT - 42)
        self._xbar = ttk.Scrollbar(holder, orient='horizontal', command=self._canvas.xview)
        self._ybar = ttk.Scrollbar(holder, orient='vertical', command=self._canvas.yview)
        self._canvas.configure(xscrollcommand=self._xbar.set, yscrollcommand=self._ybar.set)
        self._canvas.grid(row=0, column=0, sticky='nsew')
        self._ybar.grid(row=0, column=1, sticky='ns')
        self._xbar.grid(row=1, column=0, sticky='ew')
        tk.Frame(holder, width=16, height=16, bg=C['bg3']).grid(row=1, column=1, sticky='nsew')
        self._canvas.bind('<Configure>', self._on_resize)
        self._canvas.bind('<MouseWheel>', self._on_wheel)
        self._canvas.bind('<Shift-MouseWheel>', self._on_shift_wheel)
        self._canvas.bind('<Button-4>', lambda _e: self._canvas.yview_scroll(-3, 'units'))
        self._canvas.bind('<Button-5>', lambda _e: self._canvas.yview_scroll(3, 'units'))
        self._update_buttons(enabled=False)

    @staticmethod
    def _wheel_units(delta):
        try:
            d = float(delta)
        except Exception:
            return 0
        if d == 0:
            return 0
        if abs(d) < 120:
            return -1 if d > 0 else 1
        return int(-d / 120) * 3

    def _on_wheel(self, event):
        units = self._wheel_units(getattr(event, 'delta', 0))
        if units:
            self._canvas.yview_scroll(units, 'units')
        return 'break'

    def _on_shift_wheel(self, event):
        units = self._wheel_units(getattr(event, 'delta', 0))
        if units:
            self._canvas.xview_scroll(units, 'units')
        return 'break'

    def _on_resize(self, _event=None):
        if self._source_image is None:
            return
        if self._resize_after is not None:
            try:
                self.after_cancel(self._resize_after)
            except Exception:
                pass
        self._resize_after = self.after(80, self._redraw)

    def _set_view_mode(self, mode):
        if mode not in {'fit_width', '100'}:
            return
        self._view_mode = mode
        self._update_buttons(enabled=self._source_image is not None)
        self._redraw(reset_scroll=True)

    def _update_buttons(self, *, enabled):
        state = 'normal' if enabled else 'disabled'
        self._fit_btn.config(state=state, fg=C['accent'] if self._view_mode == 'fit_width' else C['muted'])
        self._actual_btn.config(state=state, fg=C['accent'] if self._view_mode == '100' else C['muted'])

    def set_notice(self, text, *, error=False):
        self._notice.config(text=str(text), fg=C['danger'] if error else C['muted'])

    def clear(self, text='Generate a schedule to view the exact Gantt here.'):
        self._source_image = None
        self._photo = None
        self._canvas.delete('all')
        self._canvas.configure(scrollregion=(0, 0, 1, 1))
        self._notice.config(text=text, fg=C['muted'])
        self._update_buttons(enabled=False)

    def show(self, snapshot_path, *, label='Schedule', error=None, schedule_rows=None):
        path = Path(snapshot_path) if snapshot_path else None
        if path is not None and path.exists():
            try:
                from PIL import Image
                with Image.open(path) as im:
                    image = im.convert('RGB').copy()
                if image.width < 240 or image.height < 120:
                    raise ValueError(f'preview is unexpectedly small ({image.width}×{image.height} px)')
                self._source_image = image
                self._notice.config(text=f'Exact QNEST {label} HTML preview • Open interactive for hover details and controls', fg=C['muted'])
                self._update_buttons(enabled=True)
                self.after_idle(lambda: self._redraw(reset_scroll=True))
                return
            except Exception as exc:
                error = error or str(exc)
        rows = list(schedule_rows or [])
        if rows:
            self._draw_native_fallback(rows, label=label, error=error)
            return
        msg = f'{label} HTML is available, but its inline preview could not be rendered.'
        if error:
            msg += f'  {error}'
        msg += '  Use Open interactive to view the live schedule.'
        self.clear(msg)

    def _draw_native_fallback(self, rows, *, label, error=None):
        self._source_image = None
        self._photo = None
        self._canvas.delete('all')
        self._update_buttons(enabled=False)
        suffix = f' • HTML capture unavailable: {error}' if error else ''
        self._notice.config(text=f'Native schedule fallback • exact {label} HTML remains available via Open interactive{suffix}', fg=C['muted'])
        qubits = []
        seen = set()
        for row in rows:
            for q in row.get('qubits', []) or []:
                if q not in seen:
                    seen.add(q)
                    qubits.append(q)
        if not qubits:
            self._canvas.create_text(20, 20, anchor='nw', text='Schedule contains no qubit rows.', fill=C['muted'], font=FM.body)
            self._canvas.configure(scrollregion=(0, 0, 600, 200))
            return
        starts = [float(r.get('start_ns', 0) or 0) for r in rows]
        ends = [float(r.get('end_ns', r.get('start_ns', 0)) or 0) for r in rows]
        t0, t1 = (min(starts, default=0.0), max(ends, default=1.0))
        span = max(1.0, t1 - t0)
        label_w, top, row_h = (190, 48, 38)
        width = max(1100, 120 + len(rows) * 42)
        plot_w = width - label_w - 60
        height = top + len(qubits) * row_h + 54
        ymap = {q: top + i * row_h for i, q in enumerate(qubits)}
        self._canvas.create_text(18, 14, anchor='nw', text='Qoala execution timeline', fill=C['text'], font=FM.subh)
        for q in qubits:
            y = ymap[q]
            disp = str(q).replace('server_', 's').replace('_link_register', '_lnk')
            self._canvas.create_text(label_w - 12, y, anchor='e', text=disp, fill=C['muted'], font=FM.small_mono)
            self._canvas.create_line(label_w, y, width - 24, y, fill=C['border'], width=1)
        for row in rows:
            qs = list(row.get('qubits', []) or [])
            if not qs:
                continue
            st = float(row.get('start_ns', 0) or 0)
            en = float(row.get('end_ns', st) or st)
            x1 = label_w + 8 + (st - t0) / span * plot_w
            x2 = label_w + 8 + (max(en, st + span * 0.002) - t0) / span * plot_w
            x2 = max(x1 + 12, x2)
            typ = str(row.get('type', ''))
            op = str(row.get('operation', typ or 'op'))
            if typ in {'EJPP_START', 'EPR_GENERATION', 'EPR_END'}:
                outline, fill = (C['comm'], C['bg4'])
            elif len(qs) > 1:
                outline, fill = (C['accent'], C['bg4'])
            else:
                outline, fill = (C['accent2'], C['bg3'])
            ys = [ymap[q] for q in qs if q in ymap]
            if not ys:
                continue
            if len(ys) > 1:
                self._canvas.create_line((x1 + x2) / 2, min(ys), (x1 + x2) / 2, max(ys), fill=outline, width=2)
            for y in ys:
                self._canvas.create_rectangle(x1, y - 11, x2, y + 11, fill=fill, outline=outline, width=1.5)
                if x2 - x1 > 34:
                    text = op if len(op) <= 12 else op[:11] + '…'
                    self._canvas.create_text((x1 + x2) / 2, y, text=text, fill=C['text'], font=FM.small_mono)
        self._canvas.create_text(label_w, height - 24, anchor='w', text=f'{t0 / 1000.0:,.3f} µs', fill=C['hint'], font=FM.small)
        self._canvas.create_text(width - 24, height - 24, anchor='e', text=f'{t1 / 1000.0:,.3f} µs', fill=C['hint'], font=FM.small)
        self._canvas.configure(scrollregion=(0, 0, width, height))
        self._canvas.xview_moveto(0.0)
        self._canvas.yview_moveto(0.0)

    def _redraw(self, reset_scroll=False):
        self._resize_after = None
        if self._source_image is None:
            return
        try:
            from PIL import Image, ImageTk
            source = self._source_image
            iw, ih = source.size
            self._canvas.update_idletasks()
            cw = max(120, self._canvas.winfo_width())
            if self._view_mode == '100':
                scale = 1.0
            else:
                scale = cw / max(1, iw)
                scale = max(0.08, min(4.0, scale))
            dw = max(1, int(round(iw * scale)))
            dh = max(1, int(round(ih * scale)))
            display = source if (dw, dh) == (iw, ih) else source.resize((dw, dh), Image.Resampling.LANCZOS)
            self._photo = ImageTk.PhotoImage(display)
            self._canvas.delete('all')
            self._canvas.create_image(0, 0, image=self._photo, anchor='nw')
            self._canvas.configure(scrollregion=(0, 0, dw, dh))
            if reset_scroll:
                self._canvas.xview_moveto(0.0)
                self._canvas.yview_moveto(0.0)
        except Exception as exc:
            self._notice.config(text=f'Could not resize schedule preview: {exc}')

class SchedulePanel(_Frame):
    NOTEBOOK_DEFAULTS = {'single_qubit_time_ns': str(NOTEBOOK_REFERENCE_DEFAULTS['single_qubit_time_us']), 'two_qubit_time_ns': str(NOTEBOOK_REFERENCE_DEFAULTS['two_qubit_time_us']).rstrip('0').rstrip('.'), 'starting_process_time_ns': str(NOTEBOOK_REFERENCE_DEFAULTS['starting_process_time_us']), 'ending_process_time_ns': str(NOTEBOOK_REFERENCE_DEFAULTS['ending_process_time_us'])}

    def __init__(self, parent):
        super().__init__(parent)
        self._busy = False
        self._scope_ids = []
        self._view_ids = []
        self._batch_results = []
        self._build()

    def _build(self):
        _panel_header(self, '◈  Schedule', 'Run the notebook-aligned Qoala/NetSquid scheduler and inspect the request timeline.', C['warning'])
        _body = _ResponsiveBody(self, flex_min=300)
        _body.pack(fill='both', expand=True)
        host = _body.inner
        self._responsive_body = _body
        cfg = _card(host, padx=16, pady=10)
        cfg.pack(fill='x', padx=28, pady=(16, 10))
        self._schedule_cfg = cfg
        self._timings = {}
        labels = [('Single-qubit gate', 'single_qubit_time_ns'), ('Two-qubit gate', 'two_qubit_time_ns'), ('EPR + EJPP start', 'starting_process_time_ns'), ('EJPP ending process', 'ending_process_time_ns')]
        self._schedule_cfg_fields = []
        for label, key in labels:
            var = tk.StringVar(value=self.NOTEBOOK_DEFAULTS[key])
            self._timings[key] = var
            lbl = tk.Label(cfg, text=label + ':', font=FM.small, fg=C['muted'], bg=C['bg2'])
            ent = tk.Entry(cfg, textvariable=var, width=13, font=FM.mono, bg=C['bg3'], fg=C['text'], insertbackground=C['warning'], relief='flat')
            unit = tk.Label(cfg, text='µs', font=FM.small, fg=C['hint'], bg=C['bg2'])
            self._schedule_cfg_fields.append((lbl, ent, unit))
        self._strategy_label = tk.Label(cfg, text='Strategy:', font=FM.small, fg=C['muted'], bg=C['bg2'])
        self._strategy = tk.StringVar(value=NOTEBOOK_REFERENCE_DEFAULTS['scheduling_strategy'])
        self._strategy_menu = tk.OptionMenu(cfg, self._strategy, 'QOALA', 'FCFS', 'EPR_PRIORITY', 'RANDOM')
        self._strategy_menu.config(font=FM.small, bg=C['bg3'], fg=C['text'], relief='flat', width=12)
        self._strategy_menu['menu'].config(bg=C['bg3'], fg=C['text'])
        self._scope_label = tk.Label(cfg, text='Circuit scope:', font=FM.small, fg=C['muted'], bg=C['bg2'])
        self._scope = tk.StringVar(value='Active circuit')
        self._scope_combo = ttk.Combobox(cfg, textvariable=self._scope, state='readonly', width=30)
        self._scope_combo.bind('<<ComboboxSelected>>', lambda _e: self._on_scope_changed())
        self._schedule_cfg.bind('<Configure>', self._layout_schedule_config, add='+')
        action = _frame(host)
        action.pack(fill='x', padx=28, pady=(0, 10))
        self._schedule_action = action
        self._run_btn = _button(action, '▶  Generate Qoala schedule', accent=C['warning'], command=self._generate, padx=17, pady=7)
        self._status = _label(action, 'Compile first', fg=C['muted'], anchor='w', justify='left')
        self._schedule_action_flow = _FlowLayout(action, [{'widget': self._run_btn, 'mr': 14}, {'widget': self._status, 'stretch': True, 'wrap': True, 'minw': _scaled(160)}], gap_y=6)
        self._progress = ttk.Progressbar(host, mode='determinate')
        self._progress.pack(fill='x', padx=28, pady=(0, 8))
        self._nb = ttk.Notebook(host)
        self._nb.pack(fill='both', expand=True, padx=28, pady=(0, 18))
        self._gantt_tab = _frame(self._nb)
        gantt_bar = _frame(self._gantt_tab)
        gantt_bar.pack(fill='x', padx=8, pady=(8, 3))
        self._gantt_bar = gantt_bar
        self._gantt_bar_left = _frame(gantt_bar)
        self._gantt_bar_right = _frame(gantt_bar)
        tk.Label(self._gantt_bar_left, text='Visualization:', font=FM.small, fg=C['muted'], bg=C['bg2']).pack(side='left')
        self._gantt_kind = tk.StringVar(value='Timed Gantt')
        gantt_menu = tk.OptionMenu(self._gantt_bar_left, self._gantt_kind, 'Timed Gantt', 'Layer Gantt', command=lambda _v: self._on_gantt_kind_changed())
        gantt_menu.config(font=FM.small, bg=C['bg3'], fg=C['text'], relief='flat', width=13)
        gantt_menu['menu'].config(bg=C['bg3'], fg=C['text'])
        gantt_menu.pack(side='left', padx=(6, 10))
        _ghost_button(self._gantt_bar_left, 'Open interactive', accent=C['warning'], command=self._open_selected_gantt, padx=11, pady=5).pack(side='left')
        _ghost_button(self._gantt_bar_left, 'Save HTML…', accent=C['accent'], command=self._save_selected_gantt, padx=11, pady=5).pack(side='left', padx=(8, 0))
        tk.Label(self._gantt_bar_right, text='Circuit:', font=FM.small, fg=C['muted'], bg=C['bg2']).pack(side='left')
        self._view_circuit = ttk.Combobox(self._gantt_bar_right, state='readonly', width=28)
        self._view_circuit.pack(side='left', fill='x', expand=True, padx=(6, 0))
        self._view_circuit.bind('<<ComboboxSelected>>', lambda _e: self._on_view_circuit_changed())
        self._gantt_bar.bind('<Configure>', self._layout_gantt_bar, add='+')
        self._gantt_cw = tk.StringVar(value='md')
        self._gantt_px = tk.IntVar(value=8)
        self._gantt_rh = tk.StringVar(value='normal')
        self._gantt_labels = tk.StringVar(value='on')
        self._gantt_gates = tk.StringVar(value='all')
        self._gantt_controls = _frame(self._gantt_tab, bg=C['bg3'])
        self._gantt_controls.pack(fill='x', padx=8, pady=(0, 4))
        self._gantt_refresh_after = None
        self._gantt_rendering = False
        self._gantt_render_pending = False
        self._rebuild_gantt_controls()
        self._gantt_preview = _ScheduleHtmlPreview(self._gantt_tab)
        self._gantt_preview.pack(fill='both', expand=True, padx=8, pady=(0, 8))
        self._nb.add(self._gantt_tab, text='Schedule visualization')
        f = _frame(self._nb)
        self._overview = TableView(f)
        self._overview.pack(fill='both', expand=True, padx=6, pady=6)
        self._nb.add(f, text='Overview')
        f = _frame(self._nb)
        self._schedule_table = TableView(f)
        self._schedule_table.pack(fill='both', expand=True, padx=6, pady=6)
        self._nb.add(f, text='Schedule table')
        f = _frame(self._nb)
        self._request_table = TableView(f)
        self._request_table.pack(fill='both', expand=True, padx=6, pady=6)
        self._nb.add(f, text='Request table')
        f = _frame(self._nb)
        self._artifacts = ArtifactBrowser(f, ('04_schedule',))
        self._artifacts.pack(fill='both', expand=True, padx=6, pady=6)
        self._nb.add(f, text='Exports')
        f = _frame(self._nb)
        self._log = scrolledtext.ScrolledText(f, font=FM.mono, bg=C['bg3'], fg=C['text'], relief='flat', padx=10, pady=8, state='disabled')
        self._log.pack(fill='both', expand=True, padx=6, pady=6)
        self._nb.add(f, text='Log')

    def _layout_schedule_config(self, _event=None):
        if not hasattr(self, '_schedule_cfg'):
            return
        try:
            width = max(320, int(self._schedule_cfg.winfo_width()))
        except Exception:
            width = 1100
        fields = list(getattr(self, '_schedule_cfg_fields', []))
        field_need = [int(lbl.winfo_reqwidth()) + 6 + min(int(ent.winfo_reqwidth()), _scaled(150)) + 4 + int(unit.winfo_reqwidth()) + 24 for lbl, ent, unit in fields]
        inner_w = width - 2 * _internal_border(self._schedule_cfg, 'x')
        cols = _fit_columns(inner_w, field_need, choices=(2,))
        for col in range(8):
            try:
                self._schedule_cfg.grid_columnconfigure(col, weight=0)
            except Exception:
                pass
        for i, (lbl, ent, unit) in enumerate(fields):
            for w in (lbl, ent, unit):
                w.grid_forget()
            row = i // cols
            base_col = i % cols * 4
            lbl.grid(row=row, column=base_col, sticky='w', padx=(0, 6), pady=5)
            ent.grid(row=row, column=base_col + 1, sticky='ew', pady=5)
            unit.grid(row=row, column=base_col + 2, sticky='w', padx=(4, 24), pady=5)
            try:
                self._schedule_cfg.grid_columnconfigure(base_col + 1, weight=1)
            except Exception:
                pass
        next_row = (len(fields) + cols - 1) // cols
        self._strategy_label.grid_forget()
        self._strategy_menu.grid_forget()
        self._scope_label.grid_forget()
        self._scope_combo.grid_forget()
        strategy_need = int(self._strategy_label.winfo_reqwidth()) + int(self._strategy_menu.winfo_reqwidth()) + 24
        scope_need = int(self._scope_label.winfo_reqwidth()) + 6 + min(int(self._scope_combo.winfo_reqwidth()), _scaled(260))
        if inner_w >= (max(field_need) if cols > 1 else strategy_need) + scope_need:
            self._strategy_label.grid(row=next_row, column=0, sticky='w', pady=5)
            self._strategy_menu.grid(row=next_row, column=1, sticky='w', pady=5)
            self._scope_label.grid(row=next_row, column=4 if cols > 1 else 3, sticky='w', padx=(0, 6), pady=5)
            self._scope_combo.grid(row=next_row, column=5 if cols > 1 else 4, columnspan=2, sticky='ew', pady=5)
            try:
                self._schedule_cfg.grid_columnconfigure(5 if cols > 1 else 4, weight=1)
            except Exception:
                pass
        else:
            self._strategy_label.grid(row=next_row, column=0, sticky='w', pady=5)
            self._strategy_menu.grid(row=next_row, column=1, columnspan=2, sticky='w', pady=5)
            self._scope_label.grid(row=next_row + 1, column=0, sticky='w', padx=(0, 6), pady=5)
            self._scope_combo.grid(row=next_row + 1, column=1, columnspan=3, sticky='ew', pady=5)
            try:
                self._schedule_cfg.grid_columnconfigure(1, weight=1)
            except Exception:
                pass

    def _layout_schedule_action(self, _event=None):
        flow = getattr(self, '_schedule_action_flow', None)
        if flow is not None:
            flow.schedule()

    def _layout_gantt_bar(self, _event=None):
        if not hasattr(self, '_gantt_bar'):
            return
        if getattr(self, '_gantt_bar_flow', None) is None:
            _flow_from_pack(self._gantt_bar_left, report_width=True)
            _flow_from_pack(self._gantt_bar_right, report_width=True, overrides={self._view_circuit: {'stretch': True, 'minw': _scaled(170)}})
            self._gantt_bar_flow = _FlowLayout(self._gantt_bar, [{'widget': self._gantt_bar_left, 'shrink': True, 'minw': 10 ** 6, 'mr': 12}, {'widget': self._gantt_bar_right, 'stretch': True, 'minw': _scaled(240)}], gap_y=5)
        else:
            self._gantt_bar_flow.schedule()

    def refresh_layout(self):
        self._layout_schedule_config()
        self._layout_schedule_action()
        self._layout_gantt_bar()

    def protocol_epr_attempt_time_us(self):
        single = float(self._timings['single_qubit_time_ns'].get())
        two = float(self._timings['two_qubit_time_ns'].get())
        start = float(self._timings['starting_process_time_ns'].get())
        ending = float(self._timings['ending_process_time_ns'].get())
        fine = ending - single - two
        mid_measure = 11.0 + fine
        epr_attempt = start - mid_measure - two
        if epr_attempt <= 0:
            raise ValueError('Schedule timings imply a non-positive EPR attempt duration. Check Single-qubit, Two-qubit, EPR + EJPP start and EJPP ending process.')
        return float(epr_attempt)

    def on_show(self):
        self.refresh_circuit_context()

    def refresh_circuit_context(self):
        root = self.winfo_toplevel()
        records = root.circuit_records() if hasattr(root, 'circuit_records') else []
        compiled = []
        for rec in records:
            ctl = root.get_pipeline_for_circuit(rec.get('id'), create=False) if hasattr(root, 'get_pipeline_for_circuit') else None
            if ctl is not None and ctl.state.bridge_file is not None:
                compiled.append(rec)
        batch = getattr(root._panels.get('Circuit'), 'is_batch_mode', lambda: False)()
        labels, ids = ([], [])
        if batch and len(compiled) > 1:
            labels.append(f'All compiled circuits ({len(compiled)})')
            ids.append(None)
        for rec in compiled:
            labels.append(f"{rec.get('name')}  •  {(rec.get('qubits') if rec.get('qubits') is not None else '?')}q  •  {rec.get('source', '')}")
            ids.append(rec.get('id'))
        self._scope_ids = ids
        self._scope_combo['values'] = labels
        if labels and (self._scope_combo.current() < 0 or self._scope_combo.current() >= len(labels)):
            self._scope_combo.current(0)
        scheduled = []
        for rec in compiled:
            ctl = root.get_pipeline_for_circuit(rec.get('id'), create=False)
            if ctl and ctl.state.qoala_result is not None:
                scheduled.append(rec)
        self._view_ids = [r.get('id') for r in scheduled]
        self._view_circuit['values'] = [f"{r.get('name')}  •  {(r.get('qubits') if r.get('qubits') is not None else '?')}q" for r in scheduled]
        if scheduled:
            active = getattr(root, '_active_circuit_id', None)
            idx = self._view_ids.index(active) if active in self._view_ids else 0
            self._view_circuit.current(idx)
        self._display_scope_data()

    def _scope_id(self):
        i = self._scope_combo.current()
        return self._scope_ids[i] if 0 <= i < len(self._scope_ids) else None

    def _targets(self):
        root = self.winfo_toplevel()
        records = root.circuit_records()
        sid = self._scope_id()
        compiled = [r for r in records if root.get_pipeline_for_circuit(r.get('id'), create=False) is not None and root.get_pipeline_for_circuit(r.get('id'), create=False).state.bridge_file is not None]
        if sid is None and self._scope_ids and (self._scope_ids[0] is None):
            return compiled
        return [r for r in compiled if r.get('id') == sid] if sid else compiled[:1]

    def _on_scope_changed(self):
        sid = self._scope_id()
        if sid:
            self.winfo_toplevel().activate_circuit(sid, create=False)
        self._display_scope_data()

    def _on_view_circuit_changed(self):
        i = self._view_circuit.current()
        if 0 <= i < len(self._view_ids):
            self.winfo_toplevel().activate_circuit(self._view_ids[i], create=False)
            self._display_active_schedule()
            self._refresh_gantt_preview()
            self._artifacts.refresh()

    def _display_active_schedule(self):
        root = self.winfo_toplevel()
        result = root.pipeline.state.qoala_result
        if result is None:
            return
        self._overview.set_data([{'strategy': result.get('strategy'), 'total_execution_time_ns': result.get('total_execution_time_ns'), 'n_original_events': result.get('n_original_events'), 'used_qpus': _safe_text(result.get('used_qpus', [])), 'requests': len(root.pipeline.state.request_table) if root.pipeline.state.request_table is not None else 0}])
        self._schedule_table.set_data(result.get('schedule', []))
        self._request_table.set_data(root.pipeline.state.request_table)

    def _display_scope_data(self):
        sid = self._scope_id()
        root = self.winfo_toplevel()
        if sid is None and self._batch_results:
            self._overview.set_data(self._batch_results)
            schedule_rows = []
            request_frames = []
            try:
                import pandas as pd
            except Exception:
                pd = None
            for rec in root.circuit_records():
                ctl = root.get_pipeline_for_circuit(rec.get('id'), create=False)
                if not ctl or ctl.state.qoala_result is None:
                    continue
                for row in ctl.state.qoala_result.get('schedule', []):
                    item = dict(row)
                    item = {'circuit': rec.get('name'), **item}
                    schedule_rows.append(item)
                table = ctl.state.request_table
                if pd is not None and table is not None:
                    try:
                        frame = table.copy()
                        frame.insert(0, 'circuit', rec.get('name'))
                        request_frames.append(frame)
                    except Exception:
                        pass
            self._schedule_table.set_data(schedule_rows)
            if request_frames and pd is not None:
                self._request_table.set_data(pd.concat(request_frames, ignore_index=True))
            else:
                self._request_table.clear()
            return
        if sid:
            ctl = root.get_pipeline_for_circuit(sid, create=False)
            if ctl and ctl.state.qoala_result is not None:
                root.activate_circuit(sid, create=False)
                self._display_active_schedule()

    def _rebuild_gantt_controls(self):
        for widget in self._gantt_controls.winfo_children():
            widget.destroy()
        row1 = _frame(self._gantt_controls, bg=C['bg3'])
        row1.pack(fill='x')
        row2 = _frame(self._gantt_controls, bg=C['bg3'])
        row2.pack(fill='x')
        tk.Label(row1, text='View controls:', font=FM.small, fg=C['muted'], bg=C['bg3']).pack(side='left', padx=(8, 10), pady=5)

        def add_menu(parent, label, variable, values, width=11):
            tk.Label(parent, text=label, font=FM.small, fg=C['muted'], bg=C['bg3']).pack(side='left', padx=(6, 4))
            menu = tk.OptionMenu(parent, variable, *values, command=lambda _value: self._queue_gantt_rerender())
            menu.config(font=FM.small, bg=C['bg2'], fg=C['text'], relief='flat', width=width, highlightbackground=C['border'])
            menu['menu'].config(bg=C['bg2'], fg=C['text'])
            menu.pack(side='left', padx=(0, 6), pady=4)
            return menu
        if self._gantt_kind.get() == 'Layer Gantt':
            add_menu(row1, 'Cell width', self._gantt_cw, ('xs', 'sm', 'md', 'lg', 'xl'), 7)
        else:
            tk.Label(row1, text='px / time unit', font=FM.small, fg=C['muted'], bg=C['bg3']).pack(side='left', padx=(6, 4))
            px_box = tk.Spinbox(row1, from_=1, to=40, increment=1, textvariable=self._gantt_px, width=5, font=FM.mono, bg=C['bg2'], fg=C['text'], relief='flat', command=self._queue_gantt_rerender)
            px_box.pack(side='left', padx=(0, 6), pady=4)
            px_box.bind('<Return>', lambda _e: self._queue_gantt_rerender())
            px_box.bind('<FocusOut>', lambda _e: self._queue_gantt_rerender())
        add_menu(row1, 'Row height', self._gantt_rh, ('tight', 'normal', 'spacious'), 10)
        add_menu(row2, 'Labels', self._gantt_labels, ('on', 'off'), 6)
        add_menu(row2, 'Show gates', self._gantt_gates, ('all', 'local only', 'remote only'), 11)
        for row in (row1, row2):
            _flow_from_pack(row, gap_y=0)

    def _current_gantt_view_options(self):
        rh_map = {'tight': 26, 'normal': 36, 'spacious': 50}
        gate_map = {'all': 'all', 'local only': 'local', 'remote only': 'remote'}
        opts = {'rh': rh_map.get(self._gantt_rh.get(), 36), 'lb': 1 if self._gantt_labels.get() == 'on' else 0, 'gf': gate_map.get(self._gantt_gates.get(), 'all')}
        if self._gantt_kind.get() == 'Layer Gantt':
            cw_map = {'xs': 22, 'sm': 32, 'md': 46, 'lg': 62, 'xl': 84}
            opts['cw'] = cw_map.get(self._gantt_cw.get(), 46)
        else:
            try:
                px = int(self._gantt_px.get())
            except Exception:
                px = 8
            opts['px'] = max(1, min(40, px))
        return opts

    def _on_gantt_kind_changed(self):
        self._rebuild_gantt_controls()
        self._refresh_gantt_preview()
        self._queue_gantt_rerender(delay=80)

    def _queue_gantt_rerender(self, *_args, delay=320):
        root = self.winfo_toplevel()
        if root.pipeline.state.run_dir is None or root.pipeline.state.qoala_result is None:
            return
        if self._gantt_refresh_after is not None:
            try:
                self.after_cancel(self._gantt_refresh_after)
            except Exception:
                pass
        self._gantt_refresh_after = self.after(delay, self._start_gantt_rerender)

    def _start_gantt_rerender(self):
        self._gantt_refresh_after = None
        if self._gantt_rendering:
            self._gantt_render_pending = True
            return
        root = self.winfo_toplevel()
        run_dir = root.pipeline.state.run_dir
        if not run_dir:
            return
        key, html_name, preview_name = self._selected_gantt_files()
        schedule_dir = run_dir / '04_schedule'
        html_path = schedule_dir / html_name
        preview_path = schedule_dir / preview_name
        if not html_path.exists():
            return
        options = self._current_gantt_view_options()
        label = 'timed Gantt' if key == 'timed' else 'layer Gantt'
        schedule_rows = list((root.pipeline.state.qoala_result or {}).get('schedule', []))
        self._gantt_rendering = True
        self._gantt_preview.set_notice(f'Updating {label} preview with the selected view controls…')
        result_box = {}

        def worker():
            try:
                from src.schedule_visuals import snapshot_schedule_html
                snap, error = snapshot_schedule_html(html_path, preview_path, ui_options=options, hide_controls=True)
            except Exception as exc:
                snap, error = (None, f'{type(exc).__name__}: {exc}')
            result_box['snap'] = snap
            result_box['error'] = error
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        self.after(80, lambda: self._poll_gantt_rerender(thread, result_box, key, label, schedule_rows))

    def _poll_gantt_rerender(self, thread, result_box, key, label, schedule_rows):
        if thread.is_alive():
            self.after(80, lambda: self._poll_gantt_rerender(thread, result_box, key, label, schedule_rows))
            return
        self._finish_gantt_rerender(key, label, result_box.get('snap'), result_box.get('error'), schedule_rows)

    def _finish_gantt_rerender(self, key, label, snap, error, schedule_rows):
        self._gantt_rendering = False
        current_key, _html, _preview = self._selected_gantt_files()
        if current_key == key:
            self._gantt_preview.show(snap if snap else None, label=label, error=error, schedule_rows=schedule_rows)
        if self._gantt_render_pending:
            self._gantt_render_pending = False
            self._queue_gantt_rerender(delay=60)

    def _log_write(self, msg):
        self._log.config(state='normal')
        self._log.insert('end', str(msg) + '\n')
        self._log.see('end')
        self._log.config(state='disabled')

    def _generate(self):
        if self._busy:
            return
        root = self.winfo_toplevel()
        targets = self._targets()
        if not targets:
            messagebox.showwarning('Schedule', 'Compile/distribute at least one circuit first.')
            return
        try:
            vals_us = {k: float(v.get()) for k, v in self._timings.items()}
            if any((v <= 0 for v in vals_us.values())):
                raise ValueError
        except ValueError:
            messagebox.showerror('Schedule', 'All timing values must be positive numbers in microseconds (µs).')
            return
        vals = {k: v * 1000.0 for k, v in vals_us.items()}
        self._busy = True
        self._run_btn.config(state='disabled')
        self._status.config(text=f'Scheduling 0/{len(targets)} circuit(s)…', fg=C['warning'])
        self._progress['maximum'] = max(1, len(targets))
        self._progress['value'] = 0
        self._log.config(state='normal')
        self._log.delete('1.0', 'end')
        self._log.config(state='disabled')

        def worker():
            completed = []
            failed = []
            for idx, rec in enumerate(targets, 1):
                ctl = root.get_pipeline_for_circuit(rec['id'], create=False)
                if ctl is None:
                    continue
                try:
                    self.after(0, lambda i=idx, n=rec.get('name'): self._status.config(text=f'Scheduling {i}/{len(targets)} • {n}', fg=C['warning']))
                    result = ctl.schedule(**vals, strategy=self._strategy.get(), log=lambda m, n=rec.get('name'): self.after(0, lambda msg=m, name=n: self._log_write(f'[{name}] {msg}')))
                    completed.append((rec, result, ctl))
                    self.after(0, lambda i=idx: self._progress.config(value=i))
                except Exception as exc:
                    failed.append((rec, exc))
                    self.after(0, lambda i=idx: self._progress.config(value=i))
                    self.after(0, lambda e=exc, n=rec.get('name'): self._log_write(f'[{n}] [ERROR] {type(e).__name__}: {e}'))
            self.after(0, lambda: self._done_batch(completed, failed))
        threading.Thread(target=worker, daemon=True).start()

    def _done_batch(self, completed, failed):
        self._busy = False
        self._run_btn.config(state='normal')
        rows = []
        for rec, result, ctl in completed:
            rows.append({'circuit': rec.get('name'), 'source': rec.get('source'), 'series': rec.get('series'), 'n_qubits': (ctl.state.compile_metadata or {}).get('n_qubits', rec.get('qubits')), 'strategy': result.get('strategy'), 'total_execution_time_us': float(result.get('total_execution_time_ns', 0.0)) / 1000.0, 'n_original_events': result.get('n_original_events'), 'used_qpus': _safe_text(result.get('used_qpus', [])), 'requests': len(ctl.state.request_table) if ctl.state.request_table is not None else 0, 'status': 'ok', 'error': ''})
        for rec, exc in failed:
            rows.append({'circuit': rec.get('name'), 'source': rec.get('source'), 'series': rec.get('series'), 'n_qubits': rec.get('qubits'), 'status': 'failed', 'error': f'{type(exc).__name__}: {exc}'})
        self._batch_results = rows
        if len(rows) > 1:
            self.winfo_toplevel().save_batch_table('02_schedule', rows, 'schedule_summary.csv')
        if completed:
            rec, result, ctl = completed[0]
            self.winfo_toplevel().activate_circuit(rec['id'], create=False)
            self._status.config(text=f'✓ {len(completed)}/{len(completed) + len(failed)} schedule(s) ready', fg=C['success'] if not failed else C['warning'])
            self._gantt_kind.set('Timed Gantt')
            self._rebuild_gantt_controls()
            self.refresh_circuit_context()
            if rec['id'] in self._view_ids:
                self._view_circuit.current(self._view_ids.index(rec['id']))
            self._display_scope_data()
            self._refresh_gantt_preview(result)
            self._artifacts.refresh()
            try:
                self._nb.select(self._gantt_tab)
            except Exception:
                pass
            for _r, _res, c in completed:
                c.write_manifest()
        else:
            self._status.config(text='✕ Scheduling failed', fg=C['danger'])
            messagebox.showerror('QNEST scheduling', 'All selected circuits failed. See the Schedule log for details.')

    def _failed(self, exc):
        self._busy = False
        self._run_btn.config(state='normal')
        self._status.config(text='✕ Failed', fg=C['danger'])
        self._log_write(f'[ERROR] {type(exc).__name__}: {exc}')
        messagebox.showerror('QNEST scheduling', str(exc))

    def _selected_gantt_files(self):
        timed = self._gantt_kind.get() != 'Layer Gantt'
        if timed:
            return ('timed', 'qoala_timed.html', 'qoala_timed.preview.png')
        return ('layer', 'qoala_schedule.html', 'qoala_layer.preview.png')

    def _refresh_gantt_preview(self, result=None):
        root = self.winfo_toplevel()
        run_dir = root.pipeline.state.run_dir
        if not run_dir:
            self._gantt_preview.clear()
            return
        key, html_name, preview_name = self._selected_gantt_files()
        schedule_dir = run_dir / '04_schedule'
        html_path = schedule_dir / html_name
        preview_path = schedule_dir / preview_name
        data = result if isinstance(result, dict) else root.pipeline.state.qoala_result or {}
        preview_meta = (data.get('gantt_previews') or {}).get(key, {}) if isinstance(data, dict) else {}
        meta_preview = preview_meta.get('preview')
        if meta_preview:
            candidate = Path(meta_preview)
            if candidate.exists():
                preview_path = candidate
        label = 'timed Gantt' if key == 'timed' else 'layer Gantt'
        error = preview_meta.get('error')
        if not html_path.exists():
            self._gantt_preview.clear('Generate a schedule to create the Gantt visualization.')
            return
        self._gantt_preview.show(preview_path if preview_path.exists() else None, label=label, error=error, schedule_rows=data.get('schedule', []) if isinstance(data, dict) else [])

    def _open_selected_gantt(self):
        _key, filename, _preview = self._selected_gantt_files()
        self._open_gantt(filename)

    def _save_selected_gantt(self):
        _key, filename, _preview = self._selected_gantt_files()
        run_dir = self.winfo_toplevel().pipeline.state.run_dir
        if not run_dir:
            messagebox.showwarning('Gantt', 'Generate a schedule first.')
            return
        src = run_dir / '04_schedule' / filename
        if not src.exists():
            messagebox.showwarning('Gantt', 'Generate a schedule first.')
            return
        dest = filedialog.asksaveasfilename(defaultextension='.html', initialfile=src.name, filetypes=[('HTML files', '*.html'), ('All files', '*.*')])
        if dest:
            try:
                shutil.copy2(src, dest)
                messagebox.showinfo('Saved', f'Schedule HTML saved to:\n{dest}')
            except Exception as exc:
                messagebox.showerror('Save error', str(exc))

    def _open_gantt(self, filename):
        run_dir = self.winfo_toplevel().pipeline.state.run_dir
        if run_dir:
            path = run_dir / '04_schedule' / filename
            if path.exists():
                _open_local_path(path)
                return
        messagebox.showwarning('Gantt', 'Generate a schedule first.')

class RunPanel(_Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self._running = False
        self._scope_ids = []
        self._result_ids = []
        self._batch_results = None
        self._build()

    def _build(self):
        _panel_header(self, '◈  Run', 'Compare AFA-QSP and HAMFA-QSP on the same Qoala request schedule.', C['danger'])
        _body = _ResponsiveBody(self, flex_min=300)
        _body.pack(fill='both', expand=True)
        host = _body.inner
        self._responsive_body = _body
        cfg = _card(host, padx=14, pady=10)
        cfg.pack(fill='x', padx=28, pady=(14, 8))
        self._run_cfg = cfg
        self._run_cfg_title = tk.Label(cfg, text='Protocol / Monte Carlo configuration', font=FM.subh, fg=C['danger'], bg=C['bg2'])
        self._run_cfg_title.grid(row=0, column=0, columnspan=8, sticky='w', pady=(0, 7))
        self._vars = {'F_T': tk.StringVar(value=str(NOTEBOOK_REFERENCE_DEFAULTS['F_T'])), 'alpha': tk.StringVar(value=str(NOTEBOOK_REFERENCE_DEFAULTS['alpha'])), 'seed': tk.StringVar(value=str(NOTEBOOK_REFERENCE_DEFAULTS['protocol_seed']))}
        self._run_field_pairs = []
        for label, key in [('Fidelity threshold F_T', 'F_T'), ('Cutoff fraction α', 'alpha'), ('Base random seed', 'seed')]:
            lbl = tk.Label(cfg, text=label + ':', font=FM.small, fg=C['muted'], bg=C['bg2'])
            ent = tk.Entry(cfg, textvariable=self._vars[key], width=16, font=FM.small_mono, bg=C['bg3'], fg=C['text'], insertbackground=C['danger'], relief='flat')
            self._run_field_pairs.append((lbl, ent))
        self._hedge_label = tk.Label(cfg, text='HAMFA hedge:', font=FM.small, fg=C['muted'], bg=C['bg2'])
        self._hedge = tk.StringVar(value='race')
        self._hedge_menu = tk.OptionMenu(cfg, self._hedge, 'race', 'sequential', 'off')
        self._hedge_menu.config(font=FM.small, bg=C['bg3'], fg=C['text'], relief='flat', width=11)
        self._hedge_menu['menu'].config(bg=C['bg3'], fg=C['text'])
        self._run_field_pairs.append((self._hedge_label, self._hedge_menu))
        self._mc_label = tk.Label(cfg, text='Monte Carlo runs / point:', font=FM.small, fg=C['muted'], bg=C['bg2'])
        self._mc_runs = tk.IntVar(value=NOTEBOOK_REFERENCE_DEFAULTS['monte_carlo_runs'])
        self._mc_spin = tk.Spinbox(cfg, from_=1, to=10000, textvariable=self._mc_runs, width=8, font=FM.small_mono, bg=C['bg3'], fg=C['text'], relief='flat')
        self._run_field_pairs.append((self._mc_label, self._mc_spin))
        self._scope_label = tk.Label(cfg, text='Circuit scope:', font=FM.small, fg=C['muted'], bg=C['bg2'])
        self._scope = tk.StringVar(value='Active circuit')
        self._scope_combo = ttk.Combobox(cfg, textvariable=self._scope, state='readonly', width=28)
        self._scope_combo.bind('<<ComboboxSelected>>', lambda _e: self._on_scope_changed())
        self._run_field_pairs.append((self._scope_label, self._scope_combo))
        self._deadline = tk.BooleanVar(value=NOTEBOOK_REFERENCE_DEFAULTS['deadline_equal_is_blocked'])
        self._deadline_check = tk.Checkbutton(cfg, text='Deadline equality counts as blocked', variable=self._deadline, font=FM.small, bg=C['bg2'], fg=C['text'], selectcolor=C['bg3'], activebackground=C['bg4'], activeforeground=C['text'], disabledforeground=C['muted'])
        self._physical_note = tk.StringVar(value='Physical inputs are inherited automatically from Network and Schedule.')
        self._physical_note_label = tk.Label(cfg, textvariable=self._physical_note, font=FM.small, fg=C['muted'], bg=C['bg2'], anchor='w', justify='left')
        self._run_cfg.bind('<Configure>', self._layout_run_config, add='+')
        action = _frame(host)
        action.pack(fill='x', padx=28, pady=(0, 8))
        self._run_action = action
        self._run_btn = _button(action, '▶  Run AFA + HAMFA', accent=C['danger'], command=self._run, padx=18, pady=7)
        self._run_export_btn = _ghost_button(action, 'Export whole run…', accent=C['danger'], command=self._export_run, padx=11, pady=7)
        self._run_open_btn = _ghost_button(action, 'Open run folder', accent=C['danger'], command=self._open_run, padx=11, pady=7)
        self._status = _label(action, 'Schedule first', fg=C['muted'], anchor='w', justify='left')
        self._run_action_flow = _FlowLayout(action, [{'widget': self._run_btn, 'mr': 8}, {'widget': self._run_export_btn, 'mr': 8}, {'widget': self._run_open_btn}, {'widget': self._status, 'brk': True, 'stretch': True, 'wrap': True, 'minw': _scaled(160)}], gap_y=6)
        self._prog = ttk.Progressbar(host, mode='determinate')
        self._prog.pack(fill='x', padx=28, pady=(0, 8))
        result_bar = _card(host, padx=10, pady=7)
        result_bar.pack(fill='x', padx=28, pady=(0, 8))
        result_controls = _frame(result_bar, bg=C['bg2'])
        result_controls.pack(fill='x')
        self._run_result_controls = result_controls
        self._result_circuit_label = tk.Label(result_controls, text='Display results for:', font=FM.small, fg=C['muted'], bg=C['bg2'])
        self._result_circuit = ttk.Combobox(result_controls, state='readonly', width=34)
        self._result_circuit.bind('<<ComboboxSelected>>', lambda _e: self._on_result_circuit_changed())
        self._mc_view_label = tk.Label(result_controls, text='Monte Carlo run:', font=FM.small, fg=C['muted'], bg=C['bg2'])
        self._mc_view = ttk.Combobox(result_controls, state='readonly', width=12)
        self._mc_view.bind('<<ComboboxSelected>>', lambda _e: self._refresh_active_outputs())
        self._result_units_label = tk.Label(result_controls, text='Time units:', font=FM.small, fg=C['muted'], bg=C['bg2'])
        self._result_units = tk.StringVar(value='µs')
        self._result_units_combo = ttk.Combobox(result_controls, textvariable=self._result_units, state='readonly', width=7, values=('ns', 'µs'))
        self._result_units_combo.bind('<<ComboboxSelected>>', lambda _e: self._on_result_units_changed())
        self._run_result_flow = _FlowLayout(result_controls, [{'widget': self._result_circuit_label, 'glue': True, 'mr': 7}, {'widget': self._result_circuit, 'stretch': True, 'minw': _scaled(190), 'mr': 18}, {'widget': self._mc_view_label, 'glue': True, 'mr': 7}, {'widget': self._mc_view, 'mr': 18}, {'widget': self._result_units_label, 'glue': True, 'mr': 7}, {'widget': self._result_units_combo}], gap_y=6)
        self._result_hint = tk.StringVar(value='Clean per-request results • display: µs • saved result tables remain ns • one circuit / Monte Carlo run at a time')
        tk.Label(result_bar, textvariable=self._result_hint, font=FM.small, fg=C['hint'], bg=C['bg2'], anchor='w').pack(fill='x', pady=(5, 0))
        self._nb = ttk.Notebook(host)
        self._nb.pack(fill='both', expand=True, padx=28, pady=(0, 16))
        result_aliases = {'Request k': 'Request', 'QPU C (i)': 'Control QPU', 'QPU T (j)': 'Target QPU', 'QPU C Link (m)': 'Control link', 'QPU T Link (n)': 'Target link', 'Δt_w(k)^(C_m,T_n) [ns]': 'Wait window [ns]', 't_D(k)^(C_m,T_n) [ns]': 'Deadline [ns]', 'Δt_P(k)^(C_m,T_n) [ns]': 'Punishment [ns]', 'Number of trials': 'Trials', 'Time duration until success [ns]': 'Time to success [ns]', 'Time before deadline [ns]': 'Deadline margin [ns]', 'HAMFA Case': 'Case', 'Path Used': 'Path', 'Completion time [ns]': 'Completion [ns]'}
        self._afa_tab = _frame(self._nb)
        afa_head = _frame(self._afa_tab)
        afa_head.pack(fill='x', padx=10, pady=(10, 4))
        tk.Label(afa_head, text='AFA-QSP Monte Carlo results', font=FM.subh, fg=C['accent'], bg=C['bg2']).pack(side='left')
        self._afa_meta = tk.StringVar(value='Per-request results')
        tk.Label(afa_head, textvariable=self._afa_meta, font=FM.small, fg=C['hint'], bg=C['bg2']).pack(side='right')
        self._afa = TableView(self._afa_tab, convert_times=False, center=True, heading_aliases=result_aliases, compact_numbers=True)
        self._afa.pack(fill='both', expand=True, padx=10, pady=(2, 10))
        self._nb.add(self._afa_tab, text='AFA-QSP results')
        self._hamfa_tab = _frame(self._nb)
        hamfa_head = _frame(self._hamfa_tab)
        hamfa_head.pack(fill='x', padx=10, pady=(10, 4))
        tk.Label(hamfa_head, text='HAMFA-QSP Monte Carlo results', font=FM.subh, fg=C['danger'], bg=C['bg2']).pack(side='left')
        self._hamfa_meta = tk.StringVar(value='Per-request results')
        tk.Label(hamfa_head, textvariable=self._hamfa_meta, font=FM.small, fg=C['hint'], bg=C['bg2']).pack(side='right')
        self._hamfa = TableView(self._hamfa_tab, convert_times=False, center=True, heading_aliases=result_aliases, compact_numbers=True)
        self._hamfa.pack(fill='both', expand=True, padx=10, pady=(2, 10))
        self._nb.add(self._hamfa_tab, text='HAMFA-QSP results')
        self._comparison_tab = _frame(self._nb)
        self._comparison = TableView(self._comparison_tab)
        self._comparison.pack(fill='both', expand=True, padx=6, pady=6)
        self._nb.add(self._comparison_tab, text='Protocol summary')
        self._nb.hide(self._comparison_tab)
        self._batch_table_tab = _frame(self._nb)
        self._batch_table = TableView(self._batch_table_tab, center=True)
        self._batch_table.pack(fill='both', expand=True, padx=6, pady=6)
        self._nb.add(self._batch_table_tab, text='Batch results')
        self._nb.hide(self._batch_table_tab)
        self._trail_tab = _frame(self._nb)
        self._trail = CircuitTrailView(self._trail_tab)
        self._trail.pack(fill='both', expand=True, padx=6, pady=6)
        self._nb.add(self._trail_tab, text='Circuit trail')
        self._nb.hide(self._trail_tab)
        self._plots_tab = _frame(self._nb)
        self._plots = PlotGallery(self._plots_tab)
        self._plots.pack(fill='both', expand=True, padx=6, pady=6)
        self._nb.add(self._plots_tab, text='Plots')
        self._nb.hide(self._plots_tab)
        self._batch_plots_tab = _frame(self._nb)
        self._batch_plots = PlotGallery(self._batch_plots_tab)
        self._batch_plots.pack(fill='both', expand=True, padx=6, pady=6)
        self._nb.add(self._batch_plots_tab, text='Batch scaling plots')
        self._nb.hide(self._batch_plots_tab)
        self._artifacts_tab = _frame(self._nb)
        self._artifacts = ArtifactBrowser(self._artifacts_tab)
        self._artifacts.pack(fill='both', expand=True, padx=6, pady=6)
        self._nb.add(self._artifacts_tab, text='All saved files')
        self._log_tab = _frame(self._nb)
        self._log = scrolledtext.ScrolledText(self._log_tab, font=FM.mono, bg=C['bg3'], fg=C['text'], relief='flat', padx=10, pady=8, state='disabled')
        self._log.pack(fill='both', expand=True, padx=6, pady=6)
        self._nb.add(self._log_tab, text='Log')
        self.after_idle(self.refresh_run_mode)

    def _switch_run_enabled(self):
        try:
            network = self.winfo_toplevel()._panels.get('Network')
            return bool(network is not None and network._is_switched())
        except Exception:
            return False

    def _set_widget_enabled(self, widget, enabled):
        try:
            if isinstance(widget, ttk.Combobox):
                widget.configure(state='readonly' if enabled else 'disabled')
            else:
                widget.configure(state='normal' if enabled else 'disabled')
        except Exception:
            pass

    def refresh_run_mode(self):
        enabled = self._switch_run_enabled()
        self._monte_carlo_enabled = enabled
        for _label, widget in getattr(self, '_run_field_pairs', []):
            self._set_widget_enabled(widget, enabled)
        self._set_widget_enabled(getattr(self, '_deadline_check', None), enabled)
        self._set_widget_enabled(getattr(self, '_run_btn', None), enabled and (not self._running))
        self._set_widget_enabled(getattr(self, '_result_circuit', None), enabled)
        self._set_widget_enabled(getattr(self, '_mc_view', None), enabled)
        self._set_widget_enabled(getattr(self, '_result_units_combo', None), enabled)
        if enabled:
            self._run_cfg_title.config(text='Protocol / Monte Carlo configuration', fg=C['danger'])
            self._physical_note.set('Physical inputs are inherited automatically from Network and Schedule.')
            self._run_export_btn.config(text='Export whole run…')
            try:
                self._artifacts.stage_prefixes = ()
            except Exception:
                pass
            if not self._targets():
                self._status.config(text='Schedule first', fg=C['muted'])
            elif not self._running:
                self._status.config(text='Ready for AFA-QSP + HAMFA-QSP Monte Carlo', fg=C['muted'])
        else:
            self._run_cfg_title.config(text='Monte Carlo unavailable — shared switch not selected', fg=C['muted'])
            self._physical_note.set('Switch-free network: AFA-QSP/HAMFA-QSP Monte Carlo is disabled. Export collects the completed Circuit, Network, Compile and Schedule artifacts only.')
            self._run_export_btn.config(text='Export previous steps…')
            try:
                self._artifacts.stage_prefixes = ('01_circuit', '02_network', '03_compile', '04_schedule', 'logs')
            except Exception:
                pass
            self._status.config(text='Switch-free mode • export Circuit → Schedule artifacts', fg=C['muted'])
            self._prog.config(value=0)
        monte_carlo_tabs = {'AFA-QSP results', 'HAMFA-QSP results'}
        try:
            for tab_id in self._nb.tabs():
                text = self._nb.tab(tab_id, 'text')
                if text in monte_carlo_tabs:
                    self._nb.tab(tab_id, state='normal' if enabled else 'disabled')
            if not enabled:
                for tab_id in self._nb.tabs():
                    if self._nb.tab(tab_id, 'text') == 'All saved files':
                        self._nb.select(tab_id)
                        break
                self._artifacts.refresh()
        except Exception:
            pass
        self._sync_result_tabs()

    def _layout_run_config(self, _event=None):
        if not hasattr(self, '_run_cfg'):
            return
        try:
            width = max(320, int(self._run_cfg.winfo_width()))
        except Exception:
            width = 1280
        pairs = list(getattr(self, '_run_field_pairs', []))
        if not pairs:
            return
        need = [int(lbl.winfo_reqwidth()) + 5 + min(int(widget.winfo_reqwidth()), _scaled(170)) + 22 for lbl, widget in pairs]
        cols = _fit_columns(width - 2 * _internal_border(self._run_cfg, 'x'), need, choices=(4, 3, 2))
        for col in range(10):
            try:
                self._run_cfg.grid_columnconfigure(col, weight=0)
            except Exception:
                pass
        for idx, (lbl, widget) in enumerate(pairs):
            lbl.grid_forget()
            widget.grid_forget()
            row = 1 + idx // cols
            col = idx % cols * 2
            lbl.grid(row=row, column=col, sticky='w', padx=(0, 5), pady=4)
            widget.grid(row=row, column=col + 1, sticky='ew', padx=(0, 22 if idx % cols != cols - 1 else 0), pady=4)
            try:
                self._run_cfg.grid_columnconfigure(col + 1, weight=1)
            except Exception:
                pass
        next_row = 1 + (len(pairs) + cols - 1) // cols
        self._deadline_check.grid_forget()
        self._physical_note_label.grid_forget()
        self._deadline_check.grid(row=next_row, column=0, columnspan=max(2, cols * 2), sticky='w', pady=(2, 0))
        self._physical_note_label.grid(row=next_row + 1, column=0, columnspan=max(2, cols * 2), sticky='ew', pady=(7, 0))

    def _layout_run_action(self, _event=None):
        flow = getattr(self, '_run_action_flow', None)
        if flow is not None:
            flow.schedule()

    def _layout_run_result_controls(self, _event=None):
        flow = getattr(self, '_run_result_flow', None)
        if flow is not None:
            flow.schedule()

    def _on_result_units_changed(self):
        unit = self._result_units.get() if hasattr(self, '_result_units') else 'µs'
        if unit not in {'ns', 'µs'}:
            unit = 'ns'
            self._result_units.set(unit)
        self._result_hint.set(f'Clean per-request results • display: {unit} • saved result tables remain ns • one circuit / Monte Carlo run at a time')
        self._refresh_active_outputs()

    def _display_exact_table(self, table):
        if table is None:
            return None
        if getattr(self, '_result_units', None) is not None and self._result_units.get() == 'µs':
            return _display_times_in_us(table)
        try:
            return table.copy()
        except Exception:
            return table

    def _sync_result_tabs(self):
        root = self.winfo_toplevel()
        circuit = root._panels.get('Circuit') if hasattr(root, '_panels') else None
        batch = bool(circuit is not None and getattr(circuit, 'is_batch_mode', lambda: False)())
        for tab, title in ((self._plots_tab, 'Plots'), (self._batch_plots_tab, 'Batch scaling plots')):
            try:
                if batch:
                    self._nb.add(tab, text=title)
                else:
                    self._nb.hide(tab)
            except Exception:
                pass

    def refresh_layout(self):
        self._layout_run_config()
        self._layout_run_action()
        self._layout_run_result_controls()
        self._sync_result_tabs()

    def on_show(self):
        self.refresh_circuit_context()

    def refresh_circuit_context(self):
        root = self.winfo_toplevel()
        records = root.circuit_records() if hasattr(root, 'circuit_records') else []
        scheduled = []
        for rec in records:
            ctl = root.get_pipeline_for_circuit(rec.get('id'), create=False) if hasattr(root, 'get_pipeline_for_circuit') else None
            if ctl and ctl.state.qoala_result is not None:
                scheduled.append(rec)
        batch = getattr(root._panels.get('Circuit'), 'is_batch_mode', lambda: False)()
        labels, ids = ([], [])
        if batch and len(scheduled) > 1:
            labels.append(f'All scheduled circuits ({len(scheduled)})')
            ids.append(None)
        for rec in scheduled:
            labels.append(f"{rec.get('name')}  •  {(rec.get('qubits') if rec.get('qubits') is not None else '?')}q  •  {rec.get('source', '')}")
            ids.append(rec.get('id'))
        self._scope_ids = ids
        self._scope_combo['values'] = labels
        if labels and (self._scope_combo.current() < 0 or self._scope_combo.current() >= len(labels)):
            self._scope_combo.current(0)
        self._refresh_result_selector()
        if self._batch_results is not None:
            self._batch_table.set_data(self._batch_display(self._batch_results))
        self._sync_result_tabs()
        self.refresh_run_mode()

    def _scope_id(self):
        i = self._scope_combo.current()
        return self._scope_ids[i] if 0 <= i < len(self._scope_ids) else None

    def _targets(self):
        root = self.winfo_toplevel()
        records = root.circuit_records()
        sid = self._scope_id()
        out = []
        for rec in records:
            ctl = root.get_pipeline_for_circuit(rec.get('id'), create=False)
            if ctl and ctl.state.qoala_result is not None:
                out.append(rec)
        if sid is None and self._scope_ids and (self._scope_ids[0] is None):
            return out
        return [r for r in out if r.get('id') == sid] if sid else out[:1]

    def _on_scope_changed(self):
        sid = self._scope_id()
        if sid:
            ctl = self.winfo_toplevel().get_pipeline_for_circuit(sid, create=False)
            if ctl and ctl.state.afa_summary is not None:
                self._select_result_circuit(sid)

    def _result_id(self):
        i = self._result_circuit.current()
        return self._result_ids[i] if 0 <= i < len(self._result_ids) else None

    def _select_result_circuit(self, cid):
        if cid in self._result_ids:
            self._result_circuit.current(self._result_ids.index(cid))
            self._on_result_circuit_changed()

    def _refresh_result_selector(self, preferred_id=None):
        root = self.winfo_toplevel()
        old_id = preferred_id if preferred_id is not None else self._result_id()
        records = []
        for rec in root.circuit_records() if hasattr(root, 'circuit_records') else []:
            ctl = root.get_pipeline_for_circuit(rec.get('id'), create=False)
            if ctl and ctl.state.afa_summary is not None and (ctl.state.hamfa_summary is not None):
                records.append(rec)
        self._result_ids = [r.get('id') for r in records]
        self._result_circuit['values'] = [f"{r.get('name')}  •  {(r.get('qubits') if r.get('qubits') is not None else '?')}q" for r in records]
        if not records:
            self._result_circuit.set('')
            self._mc_view['values'] = []
            self._mc_view.set('')
            return
        if old_id in self._result_ids:
            idx = self._result_ids.index(old_id)
        else:
            active = getattr(root, '_active_circuit_id', None)
            idx = self._result_ids.index(active) if active in self._result_ids else 0
        self._result_circuit.current(idx)
        self._refresh_mc_selector()
        self._refresh_active_outputs()

    def _refresh_mc_selector(self):
        cid = self._result_id()
        root = self.winfo_toplevel()
        ctl = root.get_pipeline_for_circuit(cid, create=False) if cid else None
        n = 0
        if ctl:
            n = max(len(getattr(ctl.state, 'afa_run_summaries', []) or []), len(getattr(ctl.state, 'hamfa_run_summaries', []) or []))
            if n == 0 and ctl.state.afa_summary is not None:
                n = int(ctl.state.afa_summary.get('simulation_runs', 1) or 1)
        values = [f'Run {i}' for i in range(1, max(1, n) + 1)] if ctl else []
        self._mc_view['values'] = values
        if values:
            current = self._mc_view.current()
            self._mc_view.current(current if 0 <= current < len(values) else 0)
        else:
            self._mc_view.set('')

    def _on_result_circuit_changed(self):
        cid = self._result_id()
        if cid:
            self.winfo_toplevel().activate_circuit(cid, create=False)
        self._refresh_mc_selector()
        self._refresh_active_outputs()

    def _mc_index(self):
        i = self._mc_view.current()
        return i if i >= 0 else 0

    def _log_write(self, msg):
        self._log.config(state='normal')
        self._log.insert('end', str(msg) + '\n')
        self._log.see('end')
        self._log.config(state='disabled')

    def _parse(self):
        if not self._switch_run_enabled():
            raise ValueError('AFA-QSP/HAMFA-QSP Monte Carlo requires Network → All-to-all → Shared switch.')
        root = self.winfo_toplevel()
        F_T = float(self._vars['F_T'].get())
        alpha = float(self._vars['alpha'].get())
        seed = int(float(self._vars['seed'].get()))
        runs = int(self._mc_runs.get())
        if not 0.0 < F_T <= 1.0:
            raise ValueError('F_T must satisfy 0 < F_T ≤ 1.')
        if not 0.0 < alpha < 1.0:
            raise ValueError('α must satisfy 0 < α < 1.')
        if runs < 1:
            raise ValueError('Monte Carlo runs per point must be at least 1.')
        network = root._panels.get('Network')
        schedule = root._panels.get('Schedule')
        if network is None or not hasattr(network, 'protocol_physical_parameters'):
            raise ValueError('Network physical parameters are not available.')
        if schedule is None or not hasattr(schedule, 'protocol_epr_attempt_time_us'):
            raise ValueError('Schedule timing parameters are not available.')
        phys = network.protocol_physical_parameters()
        epr_trial_us = float(schedule.protocol_epr_attempt_time_us())
        time_per_trial_ns = epr_trial_us * 1000.0
        t_cut_ns = -float(phys['delta_t_c_ns']) * math.log(alpha)
        self._physical_note.set('Physical inputs are inherited automatically from Network and Schedule.')
        return dict(p_succ=float(phys['p_succ']), p_succ_ap=float(phys['p_succ_ap']), time_per_trial_ns=time_per_trial_ns, t_cut_ns=t_cut_ns, delta_t_c_ns=float(phys['delta_t_c_ns']), F_I=float(phys['F_I']), F_T=F_T, alpha=alpha, seed=seed, background_start_ns=0.0, deadline_equal_is_blocked=bool(self._deadline.get()), hedge_mode=self._hedge.get(), monte_carlo_runs=runs, afa_fidelity=float(phys['afa_fidelity']))

    def _run(self):
        if self._running:
            return
        if not self._switch_run_enabled():
            self.refresh_run_mode()
            return
        root = self.winfo_toplevel()
        targets = self._targets()
        if not targets:
            messagebox.showwarning('Run', 'Generate the Qoala schedule for at least one circuit first.')
            return
        try:
            base_params = self._parse()
        except Exception as exc:
            messagebox.showerror('Run parameters', f'Check the numerical protocol parameters.\n\n{exc}')
            return
        mc_runs = int(base_params.get('monte_carlo_runs', 1))
        self._running = True
        self._run_btn.config(state='disabled')
        self._status.config(text=f'Simulating {len(targets)} circuit(s) × {mc_runs} Monte Carlo run(s)…', fg=C['warning'])
        self._prog['maximum'] = max(1, len(targets) * mc_runs)
        self._prog['value'] = 0
        self._log.config(state='normal')
        self._log.delete('1.0', 'end')
        self._log.config(state='disabled')

        def worker():
            completed, failed = ([], [])
            for idx, rec in enumerate(targets, 1):
                ctl = root.get_pipeline_for_circuit(rec['id'], create=False)
                if ctl is None:
                    continue
                params = dict(base_params)
                if len(targets) > 1:
                    q = (ctl.state.compile_metadata or {}).get('n_qubits', rec.get('qubits') or 0)
                    params['seed'] = int(base_params['seed']) + int(q or 0) * mc_runs
                try:
                    self.after(0, lambda i=idx, n=rec.get('name'): self._status.config(text=f'Simulating {i}/{len(targets)} • {n} • MC 0/{mc_runs}', fg=C['warning']))
                    base_done = (idx - 1) * mc_runs

                    def _mc_progress(done, total, name=rec.get('name'), i=idx, base=base_done):
                        self.after(0, lambda d=done, tt=total, n=name, ci=i, b=base: (self._prog.config(value=b + d), self._status.config(text=f'Simulating {ci}/{len(targets)} • {n} • MC {d}/{tt}', fg=C['warning'])))
                    result = ctl.run_protocols(**params, progress=_mc_progress, log=lambda m, n=rec.get('name'): self.after(0, lambda msg=m, name=n: self._log_write(f'[{name}] {msg}')))
                    completed.append((rec, result, ctl, params))
                    self.after(0, lambda i=idx: self._prog.config(value=i * mc_runs))
                except Exception as exc:
                    failed.append((rec, exc))
                    self.after(0, lambda i=idx: self._prog.config(value=i * mc_runs))
                    self.after(0, lambda e=exc, n=rec.get('name'): self._log_write(f'[{n}] [ERROR] {type(e).__name__}: {e}'))
            self.after(0, lambda: self._done_batch(completed, failed))
        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def _batch_row(rec, result, ctl, params):
        meta = ctl.state.compile_metadata or {}
        qoala = ctl.state.qoala_result or {}
        afa = result['afa_summary']
        ham = result['hamfa_summary']
        row = {'circuit': rec.get('name'), 'source': rec.get('source'), 'series': rec.get('series') or rec.get('benchmark') or rec.get('source'), 'n_qubits': int(meta.get('n_qubits', rec.get('qubits') or 0)), 'n_gates_original': meta.get('n_gates_original'), 'depth_original': meta.get('depth_original'), 'n_gates_distributed': meta.get('n_gates_distributed'), 'depth_distributed_pytket': meta.get('depth_distributed_pytket'), 'distributed_depth': meta.get('distributed_depth'), 'epr_pairs': meta.get('ebits_builtin'), 'epr_pairs_builtin': meta.get('ebits_builtin'), 'status': 'ok', 'error': '', 'qoala_total_time_ns': qoala.get('total_execution_time_ns'), 'total_requests': afa.get('total_requests'), 'simulation_seed': params.get('seed'), 'simulation_runs': params.get('monte_carlo_runs', 1), 'afa_punishment_time_ns': afa.get('total_punishment_time_ns'), 'hamfa_punishment_time_ns': ham.get('total_punishment_time_ns'), 'afa_blocked_requests': afa.get('total_blocked_requests'), 'hamfa_blocked_requests': ham.get('total_blocked_requests'), 'afa_mean_fidelity': afa.get('mean_delivered_fidelity'), 'hamfa_mean_fidelity': ham.get('mean_delivered_fidelity'), 'hamfa_memory_assisted_successful': ham.get('memory_assisted_successful', 0), 'hamfa_memory_assisted_not_successful': ham.get('memory_assisted_not_successful', 0), 'hamfa_all_photonic_used': ham.get('all_photonic_used', 0), 'hamfa_passed_t_cut': ham.get('passed_t_cut', 0)}
        for out_key, summary, metric in [('afa_punishment_time_ns_std', afa, 'total_punishment_time_ns'), ('hamfa_punishment_time_ns_std', ham, 'total_punishment_time_ns'), ('afa_blocked_requests_std', afa, 'total_blocked_requests'), ('hamfa_blocked_requests_std', ham, 'total_blocked_requests'), ('afa_mean_fidelity_std', afa, 'mean_delivered_fidelity'), ('hamfa_mean_fidelity_std', ham, 'mean_delivered_fidelity'), ('hamfa_memory_assisted_successful_std', ham, 'memory_assisted_successful'), ('hamfa_all_photonic_used_std', ham, 'all_photonic_used')]:
            row[out_key] = summary.get(metric + '_std', 0.0)
        return row

    @staticmethod
    def _batch_display(df):
        try:
            out = _display_times_in_us(df.copy())
            rename = {'afa_punishment_time_us': 'AFA punishment mean [µs]', 'afa_punishment_time_us_std': 'AFA punishment SD [µs]', 'hamfa_punishment_time_us': 'HAMFA punishment mean [µs]', 'hamfa_punishment_time_us_std': 'HAMFA punishment SD [µs]', 'afa_blocked_requests': 'AFA blocked mean', 'afa_blocked_requests_std': 'AFA blocked SD', 'hamfa_blocked_requests': 'HAMFA blocked mean', 'hamfa_blocked_requests_std': 'HAMFA blocked SD', 'afa_mean_fidelity': 'AFA mean fidelity', 'afa_mean_fidelity_std': 'AFA fidelity SD', 'hamfa_mean_fidelity': 'HAMFA mean fidelity', 'hamfa_mean_fidelity_std': 'HAMFA fidelity SD'}
            out = out.rename(columns=rename)
            preferred = [c for c in ['circuit', 'n_qubits', 'epr_pairs', 'total_requests', 'simulation_runs', 'AFA punishment mean [µs]', 'AFA punishment SD [µs]', 'HAMFA punishment mean [µs]', 'HAMFA punishment SD [µs]', 'AFA blocked mean', 'AFA blocked SD', 'HAMFA blocked mean', 'HAMFA blocked SD', 'AFA mean fidelity', 'AFA fidelity SD', 'HAMFA mean fidelity', 'HAMFA fidelity SD', 'hamfa_memory_assisted_successful', 'hamfa_memory_assisted_successful_std', 'hamfa_all_photonic_used', 'hamfa_all_photonic_used_std', 'status', 'error'] if c in out.columns]
            return out[preferred] if preferred else out
        except Exception:
            return df

    def _make_batch_plots(self, df):
        root = self.winfo_toplevel()
        batch_dir = root.ensure_batch_dir()
        plot_dir = batch_dir / 'plots'
        paths = []
        try:
            from src.plotting import plot_all_results
            valid = df.loc[df['status'] == 'ok'].copy() if 'status' in df.columns else df.copy()
            valid = valid.sort_values(['n_qubits', 'circuit']).reset_index(drop=True)
            if len(valid) >= 2 and valid['n_qubits'].nunique() >= 2:
                plot_all_results(valid, output_dir=plot_dir, formats=('pdf', 'svg', 'png'))
            if 'series' in valid.columns:
                for series, group in valid.groupby('series', dropna=False):
                    if len(group) >= 2 and group['n_qubits'].nunique() >= 2:
                        safe = re.sub('[^A-Za-z0-9._-]+', '_', str(series)).strip('_') or 'series'
                        plot_all_results(group.sort_values('n_qubits'), output_dir=plot_dir / safe, formats=('pdf', 'svg', 'png'))
            paths = sorted(plot_dir.glob('*.png'))
        except Exception as exc:
            self._log_write(f'[WARN] Batch scaling plots: {type(exc).__name__}: {exc}')
        return paths

    def _done_batch(self, completed, failed):
        self._running = False
        self.refresh_run_mode()
        rows = [self._batch_row(*x) for x in completed]
        for rec, exc in failed:
            rows.append({'circuit': rec.get('name'), 'source': rec.get('source'), 'series': rec.get('series'), 'n_qubits': rec.get('qubits'), 'status': 'failed', 'error': f'{type(exc).__name__}: {exc}'})
        try:
            import pandas as pd
            df = pd.DataFrame(rows).sort_values(['n_qubits', 'circuit'], na_position='last').reset_index(drop=True)
        except Exception:
            df = rows
        self._batch_results = df
        if len(rows) > 1:
            root = self.winfo_toplevel()
            root.save_batch_table('03_run', _display_times_in_us(df), 'batch_results.csv')
            batch_paths = self._make_batch_plots(df)
            self._batch_plots.set_paths(batch_paths, 'Run at least two different qubit sizes to create batch scaling plots.')
        self._batch_table.set_data(self._batch_display(df))
        self._sync_result_tabs()
        if completed:
            first_id = completed[0][0]['id']
            self._refresh_result_selector(preferred_id=first_id)
            result = completed[0][1]
            valid = all((bool(v) for v in result.get('validation', {}).values())) if result.get('validation') else True
            self._status.config(text=f'✓ {len(completed)}/{len(completed) + len(failed)} result set(s) ready', fg=C['success'] if valid and (not failed) else C['warning'])
            try:
                self._nb.select(self._afa_tab)
            except Exception:
                pass
            for _r, _res, ctl, _p in completed:
                ctl.write_manifest()
        else:
            self._status.config(text='✕ Simulation failed', fg=C['danger'])
            messagebox.showerror('QNEST protocol simulation', 'All selected circuits failed. See the Run log for details.')

    def _refresh_active_outputs(self):
        cid = self._result_id()
        root = self.winfo_toplevel()
        ctl = root.get_pipeline_for_circuit(cid, create=False) if cid else root.pipeline
        if ctl is None or ctl.state.afa_summary is None or ctl.state.hamfa_summary is None:
            return
        if cid:
            root.activate_circuit(cid, create=False)
        idx = self._mc_index()
        afa_runs = getattr(ctl.state, 'afa_run_summaries', []) or []
        ham_runs = getattr(ctl.state, 'hamfa_run_summaries', []) or []
        afa_summary = afa_runs[idx] if idx < len(afa_runs) else ctl.state.afa_summary
        ham_summary = ham_runs[idx] if idx < len(ham_runs) else ctl.state.hamfa_summary
        try:
            self._comparison.set_data(PipelineController._comparison_table(afa_summary, ham_summary))
        except Exception:
            pass

        def exact_table_for_run(tables, fallback, columns):
            try:
                if tables and 0 <= idx < len(tables):
                    return tables[idx].reindex(columns=columns).copy().reset_index(drop=True)
            except Exception:
                pass
            try:
                table = fallback
                if table is not None and 'Monte Carlo run' in table.columns:
                    table = table.loc[table['Monte Carlo run'] == idx + 1].copy()
                if table is not None:
                    return table.reindex(columns=columns).copy().reset_index(drop=True)
            except Exception:
                pass
            return fallback
        afa_exact = exact_table_for_run(getattr(ctl.state, 'afa_exact_run_tables', []) or [], ctl.state.afa_table, NOTEBOOK_AFA_TABLE_COLUMNS)
        hamfa_exact = exact_table_for_run(getattr(ctl.state, 'hamfa_exact_run_tables', []) or [], ctl.state.hamfa_table, NOTEBOOK_HAMFA_TABLE_COLUMNS)
        afa_display = self._display_exact_table(afa_exact)
        hamfa_display = self._display_exact_table(hamfa_exact)
        self._afa.set_data(afa_display)
        self._hamfa.set_data(hamfa_display)
        try:
            unit = self._result_units.get()
            circuit_name = self._result_circuit.get().split('  •  ', 1)[0].strip() or 'selected circuit'
            run_no = idx + 1
            arows = len(afa_display) if afa_display is not None else 0
            hrows = len(hamfa_display) if hamfa_display is not None else 0
            self._afa_meta.set(f'{circuit_name}  •  Run {run_no}  •  {arows} request(s)  •  {unit}')
            self._hamfa_meta.set(f'{circuit_name}  •  Run {run_no}  •  {hrows} request(s)  •  {unit}')
        except Exception:
            pass
        self._trail.refresh()
        self._plots.refresh()
        self._artifacts.refresh()

    def _failed(self, exc):
        self._running = False
        self.refresh_run_mode()
        self._status.config(text='✕ Failed', fg=C['danger'])
        self._log_write(f'[ERROR] {type(exc).__name__}: {exc}')
        messagebox.showerror('QNEST protocol simulation', str(exc))
        self._artifacts.refresh()

    def _export_previous_steps(self):
        root = self.winfo_toplevel()
        circuit = root._panels['Circuit']
        default_name = 'qnest_previous_steps.zip'
        if circuit.is_batch_mode() and root._batch_dir is not None:
            default_name = f'{root._batch_dir.name}_through_schedule.zip'
        elif root.pipeline.state.run_dir is not None:
            default_name = f'{root.pipeline.state.run_dir.name}_through_schedule.zip'
        dest = filedialog.asksaveasfilename(defaultextension='.zip', filetypes=[('ZIP archive', '*.zip')], initialfile=default_name)
        if not dest:
            return
        destination = Path(dest).expanduser()
        if destination.suffix.lower() != '.zip':
            destination = destination.with_suffix('.zip')
        try:
            with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as zf:
                batch_dir = root._batch_dir
                if circuit.is_batch_mode() and batch_dir is not None and batch_dir.exists():
                    for sub in ('01_compile', '02_schedule'):
                        base = batch_dir / sub
                        if base.exists():
                            for path in base.rglob('*'):
                                if path.is_file():
                                    zf.write(path, Path('batch') / path.relative_to(batch_dir))
                    manifest = batch_dir / 'batch_manifest.json'
                    if manifest.exists():
                        zf.write(manifest, Path('batch') / manifest.name)
                records = root.circuit_records() if hasattr(root, 'circuit_records') else []
                exported = 0
                for rec in records:
                    ctl = root.get_pipeline_for_circuit(rec.get('id'), create=False)
                    run_dir = ctl.state.run_dir if ctl else None
                    if run_dir is None or not run_dir.exists():
                        continue
                    prefix = Path('circuits') / (rec.get('name') or rec.get('id') or 'circuit') if circuit.is_batch_mode() else Path()
                    for path in run_dir.rglob('*'):
                        if not path.is_file():
                            continue
                        rel = path.relative_to(run_dir)
                        if rel.parts and rel.parts[0] == '05_run':
                            continue
                        if rel.name == 'manifest.json':
                            continue
                        zf.write(path, prefix / rel)
                        exported += 1
                if not records and root.pipeline.state.run_dir is not None:
                    run_dir = root.pipeline.state.run_dir
                    for path in run_dir.rglob('*'):
                        if not path.is_file():
                            continue
                        rel = path.relative_to(run_dir)
                        if rel.parts and rel.parts[0] == '05_run':
                            continue
                        zf.write(path, rel)
                        exported += 1
                if exported == 0:
                    raise RuntimeError('There are no completed Circuit/Network/Compile/Schedule artifacts to export yet.')
                export_meta = {'export_type': 'through_schedule', 'monte_carlo_included': False, 'included_stages': ['01_circuit', '02_network', '03_compile', '04_schedule', 'logs'], 'excluded_stage': '05_run'}
                zf.writestr('previous_steps_manifest.json', json.dumps(export_meta, indent=2))
            messagebox.showinfo('Exported', f'QNEST previous-step artifacts saved to:\n{destination}')
        except Exception as exc:
            try:
                if destination.exists() and destination.stat().st_size == 0:
                    destination.unlink()
            except Exception:
                pass
            messagebox.showerror('Export error', str(exc))

    def _export_run(self):
        if not self._switch_run_enabled():
            self._export_previous_steps()
            return
        root = self.winfo_toplevel()
        circuit = root._panels['Circuit']
        if circuit.is_batch_mode() and root._batch_dir is not None:
            dest = filedialog.asksaveasfilename(defaultextension='.zip', filetypes=[('ZIP archive', '*.zip')], initialfile=f'{root._batch_dir.name}.zip')
            if dest:
                try:
                    out = root.export_batch_zip(dest)
                    messagebox.showinfo('Exported', f'Complete QNEST batch saved to:\n{out}')
                except Exception as exc:
                    messagebox.showerror('Export error', str(exc))
            return
        run_dir = root.pipeline.state.run_dir
        if run_dir is None:
            messagebox.showwarning('Export', 'There is no active run yet.')
            return
        dest = filedialog.asksaveasfilename(defaultextension='.zip', filetypes=[('ZIP archive', '*.zip')], initialfile=f'{run_dir.name}.zip')
        if dest:
            try:
                root.pipeline.write_manifest()
                out = root.pipeline.export_session_zip(dest)
                messagebox.showinfo('Exported', f'Complete QNEST run saved to:\n{out}')
            except Exception as exc:
                messagebox.showerror('Export error', str(exc))

    def _open_run(self):
        root = self.winfo_toplevel()
        cid = self._result_id()
        if cid:
            ctl = root.get_pipeline_for_circuit(cid, create=False)
            if ctl and ctl.state.run_dir:
                _open_local_path(ctl.state.run_dir)
                return
        if self._scope_id() is None and root._batch_dir is not None:
            _open_local_path(root._batch_dir)
            return
        run_dir = root.pipeline.state.run_dir
        if run_dir:
            _open_local_path(run_dir)

def _center_window(win, parent, width, height):
    win.update_idletasks()
    px = parent.winfo_rootx() + max(0, (parent.winfo_width() - width) // 2)
    py = parent.winfo_rooty() + max(0, (parent.winfo_height() - height) // 2)
    win.geometry(f'{width}x{height}+{px}+{py}')

class SettingsDialog(tk.Toplevel):
    SCALE_LABELS = {'90%': 0.9, '100%': 1.0, '110%': 1.1, '125%': 1.25}
    THEME_META = {'Executive Slate': ('Balanced', 'Navy, white and restrained blue for a technical research workspace.'), 'Blue Steel': ('Cool', 'Low-saturation blue-grey surfaces designed for long analysis sessions.'), 'Neutral Graphite': ('Minimal', 'Graphite neutrals with a controlled blue accent and minimal visual noise.')}
    START_PAGES = ('Circuit', 'Network', 'Compile', 'Schedule', 'Run')

    def __init__(self, master):
        super().__init__(master)
        self.title('QNEST Settings')
        self.configure(bg=C['bg'])
        self.transient(master)
        self.grab_set()
        self.resizable(True, True)
        dialog_scale = max(0.9, min(1.25, float(master.ui_preferences.get('scale', 1.0))))
        self.minsize(round(860 * dialog_scale), round(570 * dialog_scale))
        prefs = master.ui_preferences
        self._theme = tk.StringVar(value=prefs.get('theme', 'Executive Slate'))
        current_scale = min(self.SCALE_LABELS, key=lambda k: abs(self.SCALE_LABELS[k] - prefs.get('scale', 1.0)))
        self._scale = tk.StringVar(value=current_scale)
        self._show_splash = tk.BooleanVar(value=bool(prefs.get('show_splash', True)))
        self._animate = tk.BooleanVar(value=bool(prefs.get('animate_splash', True)))
        self._start_page = tk.StringVar(value=prefs.get('start_page', 'Circuit'))
        self._ai_provider = tk.StringVar(value=prefs.get('ai_provider', 'Ollama (local)'))
        self._ai_endpoint = tk.StringVar(value=prefs.get('ai_endpoint', 'http://127.0.0.1:11434'))
        self._ai_model = tk.StringVar(value=prefs.get('ai_model', 'qwen3:8b'))
        self._ai_temperature = tk.DoubleVar(value=float(prefs.get('ai_temperature', 0.2)))
        self._ai_confirm = tk.BooleanVar(value=bool(prefs.get('ai_require_confirmation', True)))
        self._ai_dock_open = tk.BooleanVar(value=bool(prefs.get('ai_dock_open', True)))
        self._active_page = 'Appearance'
        self._nav_buttons = {}
        self._pages = {}
        self._theme_cards = {}
        self._scale_buttons = {}
        self._preview_widgets = {}
        self._dirty = False
        self._build()
        self._refresh_controls()
        self._show_page('Appearance')
        sw, sh = (self.winfo_screenwidth(), self.winfo_screenheight())
        ds = max(0.9, min(1.25, float(master.ui_preferences.get('scale', 1.0))))
        width = min(int(sw * 0.92), max(round(860 * ds), round(980 * ds)))
        height = min(int(sh * 0.9), max(round(590 * ds), round(690 * ds)))
        _center_window(self, master, width, height)
        self.protocol('WM_DELETE_WINDOW', self._cancel)

    def _build(self):
        header = tk.Frame(self, bg=C['bg2'], padx=26, pady=17)
        header.pack(fill='x', side='top')
        brand = tk.Frame(header, bg=C['bg2'])
        brand.pack(side='left', fill='x', expand=True)
        tk.Label(brand, text='Settings', font=FM.title, fg=C['text'], bg=C['bg2']).pack(anchor='w')
        tk.Label(brand, text='Application preferences for this device', font=FM.small, fg=C['muted'], bg=C['bg2']).pack(anchor='w', pady=(3, 0))
        tk.Label(header, text='LOCAL  •  NO EXPERIMENT VALUES', font=(FM.small.cget('family'), max(8, FM.small.cget('size') - 1), 'bold'), fg=C['accent'], bg=C['menu_sel'], padx=11, pady=6).pack(side='right', anchor='n')
        tk.Frame(self, bg=C['sep'], height=1).pack(fill='x', side='top')
        tk.Frame(self, bg=C['sep'], height=1).pack(fill='x', side='bottom')
        footer = tk.Frame(self, bg=C['bg2'], padx=24, pady=13)
        footer.pack(fill='x', side='bottom')
        self._footer_status = tk.Label(footer, text='Preferences are stored locally on this computer.', font=FM.small, fg=C['hint'], bg=C['bg2'])
        self._footer_status.pack(side='left')
        self._apply_btn = _button(footer, 'Apply', command=self._apply, padx=22, pady=7)
        self._apply_btn.pack(side='right')
        _ghost_button(footer, 'Cancel', command=self._cancel, padx=18, pady=7).pack(side='right', padx=(0, 8))
        _ghost_button(footer, 'Restore defaults', command=self._reset, padx=14, pady=7).pack(side='right', padx=(0, 8))
        main = tk.Frame(self, bg=C['bg'])
        main.pack(fill='both', expand=True)
        try:
            nav_need = max(FM.small.measure('Theme and scale'), FM.small.measure('Launch behaviour'), FM.small.measure('Local Qwen and planning'), FM.small_mono.measure(f'QNEST  v{APP_VERSION}')) + max(58, round(64 * FM.ratio))
        except Exception:
            nav_need = 225
        nav = tk.Frame(main, bg=C['sidebar_bg'], width=max(205, nav_need))
        nav.pack(side='left', fill='y')
        nav.pack_propagate(False)
        tk.Label(nav, text='PREFERENCES', font=(FM.small.cget('family'), max(8, FM.small.cget('size') - 1), 'bold'), fg=C['sidebar_muted'], bg=C['sidebar_bg'], anchor='w', padx=20, pady=18).pack(fill='x')
        for name, icon, desc in (('Appearance', '◈', 'Theme and scale'), ('Startup', '▶', 'Launch behaviour'), ('AI Assistant', '✦', 'Local Qwen and planning')):
            self._make_nav_item(nav, name, icon, desc)
        tk.Frame(nav, bg=C['sidebar_bg']).pack(fill='both', expand=True)
        tk.Label(nav, text=f'QNEST  v{APP_VERSION}', font=FM.small_mono, fg=C['sidebar_muted'], bg=C['sidebar_bg'], anchor='w', padx=20, pady=17).pack(fill='x', side='bottom')
        page_host = tk.Frame(main, bg=C['bg'])
        page_host.pack(side='left', fill='both', expand=True)
        for name, builder in (('Appearance', self._build_appearance), ('Startup', self._build_startup), ('AI Assistant', self._build_ai_assistant)):
            page = tk.Frame(page_host, bg=C['bg'])
            page.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._pages[name] = page
            builder(page)

    def _make_nav_item(self, parent, name, icon, desc):
        row = tk.Frame(parent, bg=C['sidebar_bg'], cursor='hand2')
        row.pack(fill='x', padx=8, pady=2)
        accent = tk.Frame(row, bg=C['sidebar_bg'], width=3)
        accent.pack(side='left', fill='y')
        inner = tk.Frame(row, bg=C['sidebar_bg'], cursor='hand2', padx=11, pady=10)
        inner.pack(side='left', fill='x', expand=True)
        title = tk.Label(inner, text=f'{icon}  {name}', anchor='w', font=FM.small, fg=C['sidebar_text'], bg=C['sidebar_bg'], cursor='hand2')
        title.pack(fill='x')
        sub = tk.Label(inner, text=desc, anchor='w', font=(FM.small.cget('family'), max(8, FM.small.cget('size') - 2)), fg=C['sidebar_muted'], bg=C['sidebar_bg'], cursor='hand2')
        sub.pack(fill='x', pady=(2, 0))
        for w in (row, inner, title, sub, accent):
            w.bind('<Button-1>', lambda e, n=name: self._show_page(n))
        self._nav_buttons[name] = row
        row._accent = accent
        row._inner = inner
        row._title = title
        row._sub = sub

    def _show_page(self, name):
        if name not in self._pages:
            return
        self._active_page = name
        self._pages[name].lift()
        for n, row in self._nav_buttons.items():
            active = n == name
            bg = C['sidebar_sel'] if active else C['sidebar_bg']
            row.config(bg=bg)
            row._inner.config(bg=bg)
            row._title.config(bg=bg, fg='#FFFFFF' if active else C['sidebar_text'])
            row._sub.config(bg=bg)
            row._accent.config(bg=C['accent'] if active else C['sidebar_bg'])

    def _page_heading(self, parent, title, subtitle):
        head = tk.Frame(parent, bg=C['bg'], padx=28, pady=16)
        head.pack(fill='x')
        tk.Label(head, text=title, font=FM.title, fg=C['text'], bg=C['bg']).pack(anchor='w')
        tk.Label(head, text=subtitle, font=FM.small, fg=C['muted'], bg=C['bg']).pack(anchor='w', pady=(4, 0))

    def _build_appearance(self, page):
        self._page_heading(page, 'Appearance', 'Control the visual system without changing experiment configuration.')
        content = tk.Frame(page, bg=C['bg'], padx=28, pady=0)
        content.pack(fill='both', expand=True, pady=(0, 22))
        theme = self._section_card(content, 'Visual theme', 'Choose a calibrated palette for the full QNEST workspace.')
        theme_grid = tk.Frame(theme, bg=C['bg2'])
        theme_grid.pack(fill='x', padx=14, pady=(0, 14))
        for col in range(3):
            theme_grid.grid_columnconfigure(col, weight=1, uniform='themes')
        for col, name in enumerate(THEMES):
            self._make_theme_card(theme_grid, name, col)
        scale = self._section_card(content, 'Interface scale', 'Set typography and control sizing for your display.')
        scale_body = tk.Frame(scale, bg=C['bg2'], padx=18, pady=0)
        scale_body.pack(fill='x', pady=(0, 16))
        seg = tk.Frame(scale_body, bg=C['bg3'], padx=3, pady=3)
        seg.pack(side='left', fill='x', expand=True)
        for label in self.SCALE_LABELS:
            btn = _segmented_button(seg, label, command=lambda v=label: self._set_scale(v), padx=10, pady=7)
            btn.pack(side='left', fill='x', expand=True, padx=1)
            self._scale_buttons[label] = btn
        tk.Label(scale_body, text='Recommended  ·  100%', font=FM.small, fg=C['muted'], bg=C['bg2'], padx=18).pack(side='right')

    def _build_startup(self, page):
        self._page_heading(page, 'Startup', 'Choose how QNEST opens. These preferences are local to this device.')
        content = tk.Frame(page, bg=C['bg'], padx=28, pady=0)
        content.pack(fill='both', expand=True, pady=(0, 22))
        launch = self._section_card(content, 'Launch destination', 'Select the workspace shown when QNEST starts.')
        row = tk.Frame(launch, bg=C['bg2'], padx=18, pady=0)
        row.pack(fill='x', pady=(0, 16))
        tk.Label(row, text='Start in', font=FM.small, fg=C['text'], bg=C['bg2'], width=18, anchor='w').pack(side='left')
        om = tk.OptionMenu(row, self._start_page, *self.START_PAGES, command=lambda *_: self._mark_dirty())
        om.config(font=FM.small, bg=C['bg3'], fg=C['text'], activebackground=C['bg4'], activeforeground=C['text'], relief='flat', highlightthickness=1, highlightbackground=C['border'], width=18)
        om['menu'].config(font=FM.small, bg=C['bg2'], fg=C['text'])
        om.pack(side='left')
        splash = self._section_card(content, 'Splash screen', 'Control the QNEST logo shown during application startup.')
        self._show_toggle = self._toggle_row(splash, 'Show splash screen', 'Display the QNEST launch screen before the workspace opens.', self._show_splash, self._toggle_show_splash)
        self._animate_toggle = self._toggle_row(splash, 'Animate logo', 'Play the animated logo when the splash screen is enabled.', self._animate, self._toggle_animate)

    def _build_ai_assistant(self, page):
        self._page_heading(page, 'AI Assistant', 'Local-first model connection and full validated control of the QNEST workspace.')
        content = tk.Frame(page, bg=C['bg'], padx=28, pady=0)
        content.pack(fill='both', expand=True, pady=(0, 18))
        content.grid_columnconfigure(0, weight=1, uniform='ai')
        content.grid_columnconfigure(1, weight=1, uniform='ai')
        connection = tk.Frame(content, bg=C['bg2'], highlightbackground=C['border'], highlightthickness=1)
        connection.grid(row=0, column=0, sticky='nsew', padx=(0, 7), pady=(0, 12))
        ch = tk.Frame(connection, bg=C['bg2'], padx=16, pady=11)
        ch.pack(fill='x')
        tk.Label(ch, text='Model connection', font=FM.subh, fg=C['text'], bg=C['bg2']).pack(anchor='w')
        tk.Label(ch, text='Private local inference is recommended.', font=FM.small, fg=C['muted'], bg=C['bg2']).pack(anchor='w', pady=(2, 0))
        grid = tk.Frame(connection, bg=C['bg2'], padx=16, pady=0)
        grid.pack(fill='x')
        grid.grid_columnconfigure(1, weight=1)
        tk.Label(grid, text='Provider', font=FM.small, fg=C['muted'], bg=C['bg2']).grid(row=0, column=0, sticky='w', padx=(0, 8), pady=4)
        provider = ttk.Combobox(grid, textvariable=self._ai_provider, state='readonly', values=('Ollama (local)', 'OpenAI-compatible'), width=24)
        provider.grid(row=0, column=1, sticky='ew', pady=4)
        provider.bind('<<ComboboxSelected>>', lambda _e: self._ai_provider_changed())
        tk.Label(grid, text='Model', font=FM.small, fg=C['muted'], bg=C['bg2']).grid(row=1, column=0, sticky='w', padx=(0, 8), pady=4)
        model = ttk.Combobox(grid, textvariable=self._ai_model, state='normal', values=('qwen3:4b', 'qwen3:8b', 'qwen3:14b', 'qwen3:30b'), width=24)
        model.grid(row=1, column=1, sticky='ew', pady=4)
        model.bind('<<ComboboxSelected>>', lambda _e: self._mark_dirty())
        model.bind('<KeyRelease>', lambda _e: self._mark_dirty())
        tk.Label(grid, text='Endpoint', font=FM.small, fg=C['muted'], bg=C['bg2']).grid(row=2, column=0, sticky='w', padx=(0, 8), pady=4)
        endpoint = tk.Entry(grid, textvariable=self._ai_endpoint, font=FM.small_mono, bg=C['bg3'], fg=C['text'], insertbackground=C['accent'], relief='flat')
        endpoint.grid(row=2, column=1, sticky='ew', pady=4)
        endpoint.bind('<KeyRelease>', lambda _e: self._mark_dirty())
        tk.Label(connection, text='Recommended local default  ·  qwen3:8b', font=FM.small, fg=C['hint'], bg=C['bg2'], anchor='w').pack(fill='x', padx=16, pady=(6, 5))
        ca = tk.Frame(connection, bg=C['bg2'], padx=16, pady=9)
        ca.pack(fill='x')
        self._ai_test_status = tk.Label(ca, text='Not tested', font=FM.small, fg=C['hint'], bg=C['bg2'])
        self._ai_test_status.pack(side='left')
        self._ai_test_btn = _ghost_button(ca, 'Test connection', accent=C['accent'], command=self._test_ai_connection, padx=11, pady=5)
        self._ai_test_btn.pack(side='right')
        behavior = tk.Frame(content, bg=C['bg2'], highlightbackground=C['border'], highlightthickness=1)
        behavior.grid(row=0, column=1, sticky='nsew', padx=(7, 0), pady=(0, 12))
        bh = tk.Frame(behavior, bg=C['bg2'], padx=16, pady=11)
        bh.pack(fill='x')
        tk.Label(bh, text='Assistant behaviour', font=FM.subh, fg=C['text'], bg=C['bg2']).pack(anchor='w')
        tk.Label(bh, text='Choose whether QNEST asks for approval before the assistant executes validated actions.', font=FM.small, fg=C['muted'], bg=C['bg2'], wraplength=330, justify='left').pack(anchor='w', pady=(2, 0))

        def ai_toggle_row(title, subtitle, var, command):
            row = tk.Frame(behavior, bg=C['bg2'], padx=16, pady=8)
            row.pack(fill='x')
            text = tk.Frame(row, bg=C['bg2'])
            text.pack(side='left', fill='x', expand=True)
            tk.Label(text, text=title, font=FM.small, fg=C['text'], bg=C['bg2'], anchor='w').pack(fill='x')
            tk.Label(text, text=subtitle, font=(FM.small.cget('family'), max(8, FM.small.cget('size') - 1)), fg=C['muted'], bg=C['bg2'], anchor='w', justify='left', wraplength=max(190, round(215 * FM.ratio))).pack(fill='x', pady=(2, 0))
            btn = _segmented_button(row, 'On' if var.get() else 'Off', command=command, padx=12, pady=5)
            btn.pack(side='right', padx=(10, 0), anchor='n')
            return btn
        self._ai_confirm_toggle = ai_toggle_row('Require approval', 'Show the ordered plan before execution. Turn this off for autonomous end-to-end runs.', self._ai_confirm, self._toggle_ai_confirm)
        _sep(behavior).pack(fill='x', padx=16)
        self._ai_dock_toggle = ai_toggle_row('Open at startup', 'Keep the right-side assistant tool window visible.', self._ai_dock_open, self._toggle_ai_dock)
        tk.Label(behavior, text='VALIDATED PLAN  •  APPROVAL  •  EXECUTION', font=(FM.small.cget('family'), max(8, FM.small.cget('size') - 1), 'bold'), fg=C['accent'], bg=C['menu_sel'], padx=10, pady=7).pack(fill='x', padx=16, pady=(4, 12))
        privacy = tk.Frame(content, bg=C['menu_sel'], highlightbackground=C['border'], highlightthickness=1, padx=14, pady=9)
        privacy.grid(row=1, column=0, columnspan=2, sticky='ew')
        tk.Label(privacy, text='LOCAL-FIRST PRIVACY', font=(FM.small.cget('family'), max(8, FM.small.cget('size') - 1), 'bold'), fg=C['accent'], bg=C['menu_sel']).pack(side='left')
        tk.Label(privacy, text='  Ollama keeps prompts on this computer. The assistant can control all exposed QNEST options and run the full workflow, while arbitrary Python/shell execution remains unavailable.', font=FM.small, fg=C['text'], bg=C['menu_sel'], anchor='w', justify='left', wraplength=680).pack(side='left', fill='x', expand=True)

    def _ai_provider_changed(self):
        provider = self._ai_provider.get()
        if provider == 'Ollama (local)' and (not self._ai_endpoint.get().strip()):
            self._ai_endpoint.set('http://127.0.0.1:11434')
        self._mark_dirty()

    def _toggle_ai_confirm(self):
        self._ai_confirm.set(not self._ai_confirm.get())
        self._mark_dirty()
        self._refresh_ai_controls()

    def _toggle_ai_dock(self):
        self._ai_dock_open.set(not self._ai_dock_open.get())
        self._mark_dirty()
        self._refresh_ai_controls()

    def _refresh_ai_controls(self):
        if hasattr(self, '_ai_confirm_toggle'):
            self._style_toggle(self._ai_confirm_toggle, self._ai_confirm.get(), enabled=True)
        if hasattr(self, '_ai_dock_toggle'):
            self._style_toggle(self._ai_dock_toggle, self._ai_dock_open.get(), enabled=True)

    def _test_ai_connection(self):
        if getattr(self, '_ai_testing', False):
            return
        self._ai_testing = True
        self._ai_test_btn.config(state='disabled')
        self._ai_test_status.config(text='Testing local model…', fg=C['warning'])
        client = QNESTAssistantClient(provider=self._ai_provider.get(), endpoint=self._ai_endpoint.get().strip(), model=self._ai_model.get().strip() or 'qwen3:8b', temperature=float(self._ai_temperature.get()))
        self._ai_test_result = None

        def worker():
            try:
                self._ai_test_result = (True, client.test_connection())
            except Exception as exc:
                self._ai_test_result = (False, str(exc))
        threading.Thread(target=worker, daemon=True).start()
        self.after(80, self._poll_ai_test)

    def _poll_ai_test(self):
        if self._ai_test_result is None:
            try:
                self.after(80, self._poll_ai_test)
            except Exception:
                pass
            return
        ok, text = self._ai_test_result
        self._ai_test_result = None
        self._finish_ai_test(ok, text)

    def _finish_ai_test(self, ok, text):
        self._ai_testing = False
        self._ai_test_btn.config(state='normal')
        self._ai_test_status.config(text=('✓ ' if ok else '✕ ') + text, fg=C['success'] if ok else C['danger'])

    def _section_card(self, parent, title, subtitle):
        card = tk.Frame(parent, bg=C['bg2'], highlightbackground=C['border'], highlightthickness=1)
        card.pack(fill='x', pady=(0, 14))
        head = tk.Frame(card, bg=C['bg2'], padx=18, pady=12)
        head.pack(fill='x')
        tk.Label(head, text=title, font=FM.subh, fg=C['text'], bg=C['bg2']).pack(anchor='w')
        tk.Label(head, text=subtitle, font=FM.small, fg=C['muted'], bg=C['bg2']).pack(anchor='w', pady=(2, 0))
        return card

    def _toggle_row(self, parent, title, subtitle, var, command):
        row = tk.Frame(parent, bg=C['bg2'], padx=18, pady=10)
        row.pack(fill='x')
        text = tk.Frame(row, bg=C['bg2'])
        text.pack(side='left', fill='x', expand=True)
        tk.Label(text, text=title, font=FM.small, fg=C['text'], bg=C['bg2']).pack(anchor='w')
        tk.Label(text, text=subtitle, font=(FM.small.cget('family'), max(8, FM.small.cget('size') - 1)), fg=C['muted'], bg=C['bg2']).pack(anchor='w', pady=(2, 0))
        btn = _segmented_button(row, 'Off', command=command, padx=16, pady=6)
        btn.pack(side='right', padx=(18, 0))
        return btn

    def _make_theme_card(self, parent, name, column):
        palette = THEMES[name]
        tile = tk.Frame(parent, bg=C['bg2'], highlightthickness=1, cursor='hand2', padx=12, pady=10)
        tile.grid(row=0, column=column, sticky='nsew', padx=4)
        top = tk.Frame(tile, bg=C['bg2'], cursor='hand2')
        top.pack(fill='x')
        indicator = tk.Label(top, text='○', width=2, font=FM.body, bg=C['bg2'], fg=C['hint'], cursor='hand2')
        indicator.pack(side='left')
        name_lbl = tk.Label(top, text=name, font=FM.small, fg=C['text'], bg=C['bg2'], cursor='hand2')
        name_lbl.pack(side='left', padx=(3, 0))
        tag, desc = self.THEME_META[name]
        sw = tk.Frame(tile, bg=C['bg2'], cursor='hand2')
        sw.pack(fill='x', pady=(8, 6))
        swatches = []
        for key in ('sidebar_bg', 'accent', 'accent2', 'bg3'):
            block = tk.Frame(sw, bg=palette[key], height=12, cursor='hand2')
            block.pack(side='left', fill='x', expand=True, padx=1)
            swatches.append(block)
        short_desc = {'Executive Slate': 'Crisp research default', 'Blue Steel': 'Cool, low-saturation', 'Neutral Graphite': 'Minimal neutral system'}[name]
        desc_lbl = tk.Label(tile, text=short_desc, font=(FM.small.cget('family'), max(8, FM.small.cget('size') - 2)), fg=C['muted'], bg=C['bg2'], cursor='hand2', anchor='w')
        desc_lbl.pack(fill='x')
        widgets = [tile, top, indicator, name_lbl, sw, desc_lbl, *swatches]
        for w in widgets:
            w.bind('<Button-1>', lambda e, n=name: self._set_theme(n))
        self._theme_cards[name] = {'tile': tile, 'indicator': indicator, 'name': name_lbl}

    def _set_theme(self, name):
        self._theme.set(name)
        self._mark_dirty()
        self._refresh_controls()

    def _set_scale(self, label):
        self._scale.set(label)
        self._mark_dirty()
        self._refresh_controls()

    def _toggle_show_splash(self):
        self._show_splash.set(not self._show_splash.get())
        if not self._show_splash.get():
            self._animate.set(False)
        self._mark_dirty()
        self._refresh_controls()

    def _toggle_animate(self):
        if not self._show_splash.get():
            return
        self._animate.set(not self._animate.get())
        self._mark_dirty()
        self._refresh_controls()

    def _mark_dirty(self):
        self._dirty = True
        if hasattr(self, '_footer_status'):
            self._footer_status.config(text='Unsaved changes', fg=C['warning'])

    def _refresh_controls(self):
        selected = self._theme.get()
        for name, refs in self._theme_cards.items():
            active = name == selected
            refs['tile'].config(highlightbackground=C['accent'] if active else C['border'], highlightcolor=C['accent'] if active else C['border'], highlightthickness=2 if active else 1)
            refs['indicator'].config(text='●' if active else '○', fg=C['accent'] if active else C['hint'])
            refs['name'].config(fg=C['accent'] if active else C['text'])
        for label, btn in self._scale_buttons.items():
            active = label == self._scale.get()
            btn.config(bg=C['accent'] if active else C['bg2'], fg='#FFFFFF' if active else C['muted'], activebackground=_mix_hex(C['accent'], '#000000', 0.1) if active else C['menu_sel'], activeforeground='#FFFFFF' if active else C['accent'], disabledforeground=C['muted'])
        if hasattr(self, '_show_toggle'):
            self._style_toggle(self._show_toggle, self._show_splash.get(), enabled=True)
        if hasattr(self, '_animate_toggle'):
            self._style_toggle(self._animate_toggle, self._animate.get(), enabled=self._show_splash.get())
        self._refresh_ai_controls()
        self._refresh_preview()

    def _style_toggle(self, btn, on, enabled):
        if not enabled:
            btn.config(text='Off', state='disabled', bg=C['bg3'], fg=C['hint'], disabledforeground=C['muted'])
            return
        btn.config(text='On' if on else 'Off', state='normal', bg=C['accent'] if on else C['bg3'], fg='#FFFFFF' if on else C['muted'], activebackground=_mix_hex(C['accent'], '#000000', 0.1) if on else C['menu_sel'], activeforeground='#FFFFFF' if on else C['accent'], disabledforeground=C['muted'])

    def _refresh_preview(self):
        if not self._preview_widgets:
            return
        palette = THEMES.get(self._theme.get(), THEMES['Executive Slate'])
        self._preview_caption.config(text=f'Preview  •  {self._theme.get()}  •  {self._scale.get()}')
        w = self._preview_widgets
        w['shell'].config(bg=palette['bg2'], highlightbackground=palette['border'])
        w['top'].config(bg=palette['toolbar_bg'])
        w['brand'].config(bg=palette['toolbar_bg'], fg=palette['text'])
        w['dot'].config(bg=palette['toolbar_bg'], fg=palette['accent'])
        w['main'].config(bg=palette['bg'])
        w['side'].config(bg=palette['sidebar_bg'])
        for i in range(5):
            w[f'side_{i}'].config(bg=palette['sidebar_sel'] if i == 2 else palette['sidebar_bg'], fg='#FFFFFF' if i == 2 else palette['sidebar_text'])
        w['canvas'].config(bg=palette['bg'])
        w['title'].config(bg=palette['bg'], fg=palette['accent'])
        w['subtitle'].config(bg=palette['bg'], fg=palette['muted'])
        w['card'].config(bg=palette['bg2'], highlightbackground=palette['border'])
        w['line'].config(bg=palette['accent'])
        w['line2'].config(bg=palette['bg4'])
        w['button'].config(bg=palette['accent'], fg='#FFFFFF')

    def _reset(self):
        self._theme.set('Executive Slate')
        self._scale.set('100%')
        self._show_splash.set(True)
        self._animate.set(True)
        self._start_page.set('Circuit')
        self._ai_provider.set('Ollama (local)')
        self._ai_endpoint.set('http://127.0.0.1:11434')
        self._ai_model.set('qwen3:8b')
        self._ai_temperature.set(0.2)
        self._ai_confirm.set(True)
        self._ai_dock_open.set(True)
        self._mark_dirty()
        self._refresh_controls()

    def _cancel(self):
        self.destroy()

    def _apply(self):
        self.master.apply_ui_preferences({'theme': self._theme.get(), 'scale': self.SCALE_LABELS[self._scale.get()], 'show_splash': bool(self._show_splash.get()), 'animate_splash': bool(self._animate.get()), 'start_page': self._start_page.get(), 'ai_provider': self._ai_provider.get(), 'ai_endpoint': self._ai_endpoint.get().strip(), 'ai_model': self._ai_model.get().strip() or 'qwen3:8b', 'ai_temperature': float(self._ai_temperature.get()), 'ai_require_confirmation': bool(self._ai_confirm.get()), 'ai_dock_open': bool(self._ai_dock_open.get())})
        self._dirty = False
        self.destroy()

class AboutDialog(tk.Toplevel):
    _DEEP = '#080D1A'
    _DEEP_2 = '#121B31'
    _INK = '#0C1220'
    _INK_SOFT = '#39445A'
    _MUTED = '#6E7C93'
    _TINT = '#F6F8FC'
    _RULE = '#DCE3ED'
    _STEEL = '#7E97BE'
    _VIOLET = '#6C2BD9'
    _VIOLET_2 = '#9B6BFF'

    def __init__(self, master):
        super().__init__(master)
        self.title('About QNEST')
        self.configure(bg='#FFFFFF')
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()
        self._photos = []
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        self.bind('<Escape>', lambda _e: self.destroy())
        self._build()
        scale = max(0.9, min(1.25, float(getattr(FM, 'ratio', 1.0))))
        width = min(int(self.winfo_screenwidth() * 0.94), round(850 * scale))
        height = min(int(self.winfo_screenheight() * 0.9), round(650 * scale))
        self.minsize(min(width, round(760 * scale)), min(height, round(590 * scale)))
        _center_window(self, master, width, height)

    def _asset_photo(self, image_name, *, max_w, max_h):
        try:
            from PIL import Image, ImageTk
            src = Image.open(PROJECT_ROOT / 'assets' / image_name).convert('RGBA')
            ratio = min(max_w / max(1, src.width), max_h / max(1, src.height), 1.0)
            size = (max(1, round(src.width * ratio)), max(1, round(src.height * ratio)))
            if size != src.size:
                src = src.resize(size, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(src)
            self._photos.append(photo)
            return photo
        except Exception:
            return None

    def _avatar(self, parent, image_name, initials):
        side = max(68, round(82 * max(0.9, min(1.2, FM.ratio))))
        try:
            from PIL import Image, ImageDraw, ImageOps, ImageTk
            src = Image.open(PROJECT_ROOT / 'assets' / image_name).convert('RGBA')
            crop = ImageOps.fit(src, (side, side), method=Image.Resampling.LANCZOS, centering=(0.5, 0.46))
            mask = Image.new('L', (side, side), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, side - 1, side - 1), fill=255)
            out = Image.new('RGBA', (side, side), (0, 0, 0, 0))
            out.paste(crop, (0, 0), mask)
            photo = ImageTk.PhotoImage(out)
            self._photos.append(photo)
            return tk.Label(parent, image=photo, bg='#FFFFFF', bd=0, highlightthickness=0)
        except Exception:
            return tk.Label(parent, text=initials, width=5, height=2, font=(FM.head.cget('family'), max(16, FM.head.cget('size') + 3), 'bold'), fg=self._VIOLET, bg='#F0E9FF')

    def _profile_card(self, parent, *, image_name, initials, name, affiliation):
        card = tk.Frame(parent, bg='#FFFFFF', highlightbackground=self._RULE, highlightthickness=1, padx=15, pady=13)
        avatar = self._avatar(card, image_name, initials)
        avatar.pack(side='left', padx=(0, 14))
        copy = tk.Frame(card, bg='#FFFFFF')
        copy.pack(side='left', fill='both', expand=True)
        tk.Label(copy, text=name, font=FM.subh, fg=self._INK, bg='#FFFFFF', anchor='w').pack(fill='x', anchor='w')
        tk.Label(copy, text='Senior Developer', font=FM.small, fg=self._VIOLET, bg='#FFFFFF', anchor='w').pack(fill='x', anchor='w', pady=(2, 0))
        tk.Label(copy, text=affiliation, font=FM.small, fg=self._MUTED, bg='#FFFFFF', anchor='w', justify='left', wraplength=max(180, round(225 * FM.ratio))).pack(fill='x', anchor='w', pady=(6, 0))
        return card

    def _section_title(self, parent, text):
        row = tk.Frame(parent, bg='#FFFFFF')
        row.pack(fill='x', pady=(0, 8))
        tk.Frame(row, width=4, height=max(14, round(16 * FM.ratio)), bg=self._VIOLET).pack(side='left', padx=(0, 9))
        tk.Label(row, text=text, font=FM.subh, fg=self._INK, bg='#FFFFFF').pack(side='left')
        return row

    def _support_logos(self, parent):
        row = tk.Frame(parent, bg='#FFFFFF')
        row.pack(fill='x', pady=(1, 7))
        for idx, (fname, fallback) in enumerate((('about-logo-wacqt.png', 'WACQT'), ('about-logo-bristol.png', 'University of Bristol'), ('about-logo-smart-internet-lab.png', 'Smart Internet Lab'), ('about-logo-iqn-hub.png', 'Integrated Quantum Networks Hub'))):
            cell = tk.Frame(row, bg='#FFFFFF')
            cell.pack(side='left', fill='both', expand=True, padx=(0 if idx == 0 else 8, 0))
            photo = self._asset_photo(fname, max_w=max(110, round(155 * min(1.15, FM.ratio))), max_h=max(30, round(42 * min(1.15, FM.ratio))))
            if photo is not None:
                tk.Label(cell, image=photo, bg='#FFFFFF', bd=0).pack(anchor='center', pady=3)
            else:
                tk.Label(cell, text=fallback, font=FM.small, fg=self._INK_SOFT, bg='#FFFFFF', justify='center').pack(anchor='center', pady=8)

    def _build(self):
        hero = tk.Frame(self, bg=self._DEEP, padx=30, pady=20)
        hero.pack(fill='x')
        top = tk.Frame(hero, bg=self._DEEP)
        top.pack(fill='x')
        tk.Label(top, text='QNEST', font=(FM.title.cget('family'), FM.title.cget('size') + 5, 'bold'), fg='#FFFFFF', bg=self._DEEP).pack(side='left', anchor='w')
        badge = tk.Frame(top, bg=self._DEEP_2, highlightbackground='#253352', highlightthickness=1, padx=10, pady=5)
        badge.pack(side='right', anchor='e')
        tk.Label(badge, text='●', font=FM.small, fg=self._VIOLET_2, bg=self._DEEP_2).pack(side='left')
        tk.Label(badge, text='  OPEN SOURCE', font=FM.small, fg='#D6E0F5', bg=self._DEEP_2).pack(side='left')
        tk.Label(hero, text=APP_SUBTITLE, font=FM.body, fg='#D6E0F5', bg=self._DEEP).pack(anchor='w', pady=(4, 0))
        tk.Label(hero, text=f'Version {APP_VERSION}', font=FM.small, fg=self._STEEL, bg=self._DEEP).pack(anchor='w', pady=(6, 0))
        body = tk.Frame(self, bg='#FFFFFF', padx=30, pady=18)
        body.pack(fill='both', expand=True)
        self._section_title(body, 'Overview')
        intro = 'QNEST is an open-source GUI-driven framework for end-to-end simulation of optical quantum data centers and quantum-network experiments, unifying circuit specification, network design, distributed compilation, scheduling and discrete-event execution.'
        tk.Label(body, text=intro, wraplength=max(650, round(775 * FM.ratio)), justify='left', font=FM.body, fg=self._INK_SOFT, bg='#FFFFFF', anchor='w').pack(fill='x', anchor='w', pady=(0, 13))
        tk.Frame(body, bg=self._RULE, height=1).pack(fill='x', pady=(0, 13))
        title_row = self._section_title(body, 'Team')
        tk.Label(title_row, text='Built between Gothenburg and Bristol', font=FM.small, fg=self._MUTED, bg='#FFFFFF').pack(side='right')
        team = tk.Frame(body, bg='#FFFFFF')
        team.pack(fill='x')
        team.grid_columnconfigure(0, weight=1, uniform='team')
        team.grid_columnconfigure(1, weight=1, uniform='team')
        self._profile_card(team, image_name='about-seyed-navid-elyasi.png', initials='SNE', name='Seyed Navid Elyasi', affiliation='Chalmers University of Technology').grid(row=0, column=0, sticky='nsew', padx=(0, 6))
        self._profile_card(team, image_name='about-sima-bahrani.png', initials='SB', name='Sima Bahrani', affiliation='University of Bristol').grid(row=0, column=1, sticky='nsew', padx=(6, 0))
        authors = tk.Frame(body, bg='#FFFFFF')
        authors.pack(fill='x', pady=(9, 12))
        tk.Label(authors, text='Co-authors', font=FM.small, fg=self._INK, bg='#FFFFFF').pack(side='left')
        tk.Label(authors, text='  Rui Wang · Dimitra Simeonidou · Paolo Monti · Rui Lin', font=FM.small, fg=self._MUTED, bg='#FFFFFF').pack(side='left')
        tk.Frame(body, bg=self._RULE, height=1).pack(fill='x', pady=(0, 12))
        self._section_title(body, 'Supported by')
        self._support_logos(body)
        tk.Label(body, text='Supported by the Swedish Research Council (VR) and the UK EPSRC Integrated Quantum Networks Hub (EP/Z533208/1).', font=FM.small, fg=self._MUTED, bg='#FFFFFF', anchor='w', justify='left', wraplength=max(650, round(775 * FM.ratio))).pack(fill='x', anchor='w')
        footer = tk.Frame(body, bg='#FFFFFF')
        footer.pack(fill='x', side='bottom', pady=(13, 0))
        tk.Frame(footer, bg=self._RULE, height=1).pack(fill='x', pady=(0, 11))
        line = tk.Frame(footer, bg='#FFFFFF')
        line.pack(fill='x')
        tk.Label(line, text='Open source · Chalmers × University of Bristol', font=FM.small, fg=self._MUTED, bg='#FFFFFF').pack(side='left')
        _button(line, 'Close', accent=self._VIOLET, command=self.destroy, padx=20, pady=7).pack(side='right')

class BugReportDialog(tk.Toplevel):

    def __init__(self, master):
        super().__init__(master)
        self.title('Report a Bug')
        self.configure(bg=C['bg'])
        self.transient(master)
        self.grab_set()
        self._build()
        _center_window(self, master, min(int(self.winfo_screenwidth() * 0.9), round(760 * FM.ratio)), min(int(self.winfo_screenheight() * 0.88), round(650 * FM.ratio)))

    def _build(self):
        head = tk.Frame(self, bg=C['bg2'], padx=24, pady=18)
        head.pack(fill='x')
        tk.Label(head, text='Report a Bug', font=FM.title, fg=C['text'], bg=C['bg2'], anchor='w').pack(fill='x')
        tk.Label(head, text=f'QNEST prepares the report for {BUG_REPORT_EMAIL}.', font=FM.body, fg=C['muted'], bg=C['bg2'], anchor='w', justify='left').pack(fill='x', pady=(3, 0))
        body = tk.Frame(self, bg=C['bg'], padx=24, pady=18)
        body.pack(fill='both', expand=True)
        tk.Label(body, text='What happened?', font=FM.subh, fg=C['text'], bg=C['bg'], anchor='w').pack(fill='x')
        self._description = scrolledtext.ScrolledText(body, height=8, font=FM.body, bg=C['bg2'], fg=C['text'], insertbackground=C['accent'], relief='flat', highlightbackground=C['border'], highlightthickness=1, padx=10, pady=10)
        self._description.pack(fill='both', expand=True, pady=(6, 14))
        tk.Label(body, text='Steps to reproduce', font=FM.subh, fg=C['text'], bg=C['bg'], anchor='w').pack(fill='x')
        self._steps = scrolledtext.ScrolledText(body, height=6, font=FM.body, bg=C['bg2'], fg=C['text'], insertbackground=C['accent'], relief='flat', highlightbackground=C['border'], highlightthickness=1, padx=10, pady=10)
        self._steps.pack(fill='both', expand=True, pady=(6, 12))
        self._include_logs = tk.BooleanVar(value=True)
        tk.Checkbutton(body, text='Include logs from the current QNEST run', variable=self._include_logs, font=FM.small, fg=C['muted'], bg=C['bg'], activebackground=C['bg4'], activeforeground=C['text'], disabledforeground=C['muted'], selectcolor=C['bg3']).pack(anchor='w')
        tk.Label(body, text='Your default mail application will open with the recipient, subject and report text filled in. If you save diagnostics, attach the ZIP before sending.', font=FM.small, fg=C['hint'], bg=C['bg'], anchor='w', justify='left', wraplength=max(420, round(690 * FM.ratio))).pack(fill='x', pady=(3, 0))
        footer = tk.Frame(self, bg=C['bg2'], padx=24, pady=14)
        footer.pack(fill='x')
        _ghost_button(footer, 'Cancel', command=self.destroy, padx=16, pady=7).pack(side='right')
        _ghost_button(footer, 'Save diagnostics…', command=self._save_bundle, padx=16, pady=7).pack(side='right', padx=(0, 8))
        _button(footer, 'Email bug report…', command=self._email_report, padx=18, pady=7).pack(side='right', padx=(0, 8))

    def _report_lines(self):
        root = self.master
        run_dir = getattr(root.pipeline.state, 'run_dir', None)
        return [f'QNEST version: {APP_VERSION}', f"Created: {datetime.now().isoformat(timespec='seconds')}", f'Platform: {platform.platform()}', f'Python: {sys.version}', f"Theme: {root.ui_preferences.get('theme')}", f"UI scale: {root.ui_preferences.get('scale')}", f"Current run: {run_dir or 'None'}", '', 'WHAT HAPPENED', self._description.get('1.0', 'end').strip(), '', 'STEPS TO REPRODUCE', self._steps.get('1.0', 'end').strip(), '']

    def _write_bundle(self, dest):
        root = self.master
        run_dir = getattr(root.pipeline.state, 'run_dir', None)
        with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('bug_report.txt', '\n'.join(self._report_lines()))
            zf.writestr('ui_settings.json', json.dumps(root.ui_preferences, indent=2))
            if self._include_logs.get() and run_dir:
                logs = Path(run_dir) / 'logs'
                if logs.exists():
                    for path in logs.rglob('*'):
                        if path.is_file():
                            zf.write(path, Path('logs') / path.relative_to(logs))

    def _choose_bundle_path(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return filedialog.asksaveasfilename(parent=self, defaultextension='.zip', initialfile=f'qnest_bug_{timestamp}.zip', filetypes=[('ZIP archive', '*.zip')])

    def _save_bundle(self):
        dest = self._choose_bundle_path()
        if not dest:
            return None
        try:
            self._write_bundle(dest)
            messagebox.showinfo('Bug report', f'Diagnostic bundle saved to:\n{dest}', parent=self)
            return dest
        except Exception as exc:
            messagebox.showerror('Bug report', str(exc), parent=self)
            return None

    def _email_report(self):
        description = self._description.get('1.0', 'end').strip()
        steps = self._steps.get('1.0', 'end').strip()
        if not description:
            messagebox.showwarning('Bug report', 'Please describe what happened before preparing the email.', parent=self)
            return
        bundle = None
        if self._include_logs.get():
            bundle = self._choose_bundle_path()
            if bundle:
                try:
                    self._write_bundle(bundle)
                except Exception as exc:
                    messagebox.showerror('Bug report', str(exc), parent=self)
                    return
        subject = f'QNEST v{APP_VERSION} bug report'
        body = '\n'.join(self._report_lines())
        if bundle:
            body += f'\nDIAGNOSTIC BUNDLE\n{bundle}\nPlease attach this ZIP to the message before sending.\n'
        uri = f'mailto:{BUG_REPORT_EMAIL}?subject={quote(subject)}&body={quote(body)}'
        try:
            opened = webbrowser.open(uri)
            if not opened:
                raise RuntimeError('No default mail application accepted the request.')
            messagebox.showinfo('Bug report', f'An email draft addressed to {BUG_REPORT_EMAIL} has been opened.' + (f'\n\nAttach the diagnostic ZIP before sending:\n{bundle}' if bundle else ''), parent=self)
            self.destroy()
        except Exception as exc:
            messagebox.showerror('Bug report', f'Could not open the default mail application.\n\nRecipient: {BUG_REPORT_EMAIL}\n\n{exc}', parent=self)

class AssistantDock(tk.Frame):

    def __init__(self, parent, root):
        super().__init__(parent, bg=C['bg2'], highlightbackground=C['border'], highlightthickness=1)
        self.root = root
        self._history = []
        self._pending_actions = []
        self._busy = False
        self._plan_card = None
        self._async_queue = queue.Queue()
        self._build()
        self._welcome()
        self.after(120, self._drain_async_queue)
        self.after(450, self._probe_connection)

    def _build(self):
        header = tk.Frame(self, bg=C['bg2'], padx=14, pady=11)
        header.pack(fill='x')
        title_box = tk.Frame(header, bg=C['bg2'])
        title_box.pack(side='left', fill='x', expand=True)
        row = tk.Frame(title_box, bg=C['bg2'])
        row.pack(fill='x')
        tk.Label(row, text='✦', font=FM.head, fg=C['accent'], bg=C['bg2']).pack(side='left')
        tk.Label(row, text='QNEST Assistant', font=FM.head, fg=C['text'], bg=C['bg2']).pack(side='left', padx=(7, 0))
        self._status_dot = tk.Label(row, text='●', font=FM.small, fg=C['hint'], bg=C['bg2'])
        self._status_dot.pack(side='left', padx=(9, 3))
        self._status_short = tk.Label(row, text='Local', font=FM.small, fg=C['muted'], bg=C['bg2'])
        self._status_short.pack(side='left')
        tk.Label(title_box, text='Plan  ·  configure  ·  explain', font=FM.small, fg=C['muted'], bg=C['bg2']).pack(anchor='w', pady=(3, 0))
        close = _ProfessionalButton(header, text='×', command=lambda: self.root.toggle_assistant(False), variant='secondary', accent=C['accent'], bg=C['bg2'], fg=C['muted'], activebackground=C['bg4'], activeforeground=C['text'], font=(FM.head.cget('family'), FM.head.cget('size') + 3), padx=8, pady=2, highlightthickness=0)
        close.pack(side='right', anchor='n')
        self._close_button = close
        self._model_bar = tk.Frame(self, bg=C['bg3'], padx=12, pady=7)
        self._model_bar.pack(fill='x')
        self._model_label = tk.Label(self._model_bar, text='', font=FM.small_mono, fg=C['muted'], bg=C['bg3'])
        self._model_label.pack(side='left', fill='x', expand=True)
        settings = tk.Label(self._model_bar, text='⚙  Configure', font=FM.small, fg=C['accent'], bg=C['bg3'], cursor='hand2', padx=4)
        settings.pack(side='right')
        settings.bind('<Button-1>', lambda _e: self.root._show_settings('AI Assistant'))
        self.refresh_model_badge()
        self._context_var = tk.StringVar(value='Context · workspace')
        context = tk.Frame(self, bg=C['bg2'], padx=12, pady=7)
        context.pack(fill='x')
        tk.Label(context, textvariable=self._context_var, font=FM.small, fg=C['hint'], bg=C['bg2'], anchor='w').pack(side='left', fill='x', expand=True)
        clear = tk.Label(context, text='New chat', font=FM.small, fg=C['accent'], bg=C['bg2'], cursor='hand2')
        clear.pack(side='right')
        clear.bind('<Button-1>', lambda _e: self.clear_chat())
        _sep(self).pack(fill='x')
        msg_host = tk.Frame(self, bg=C['bg'])
        self._activity_message_host = msg_host
        msg_host.pack(fill='both', expand=True)
        self._canvas = tk.Canvas(msg_host, bg=C['bg'], highlightthickness=0, bd=0)
        vs = ttk.Scrollbar(msg_host, orient='vertical', command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vs.set)
        vs.pack(side='right', fill='y')
        self._canvas.pack(side='left', fill='both', expand=True)
        self._messages = tk.Frame(self._canvas, bg=C['bg'])
        self._msg_window = self._canvas.create_window((0, 0), window=self._messages, anchor='nw')
        self._messages.bind('<Configure>', lambda _e: self._canvas.configure(scrollregion=self._canvas.bbox('all')))
        self._canvas.bind('<Configure>', self._resize_messages)
        self._canvas.bind_all('<MouseWheel>', self._wheel, add='+')
        self._activity_host = self
        self._activity_frame = tk.Frame(self, bg=C['bg2'], highlightbackground=C['border'], highlightcolor=C['accent'], highlightthickness=1, bd=0)
        activity_top = tk.Frame(self._activity_frame, bg=C['bg2'], padx=13, pady=10)
        activity_top.pack(fill='x')
        self._activity_dots = tk.Canvas(activity_top, width=42, height=14, bg=C['bg2'], highlightthickness=0, bd=0)
        self._activity_dots.pack(side='left', padx=(0, 7))
        self._activity_dot_ids = [self._activity_dots.create_oval(2 + i * 12, 4, 8 + i * 12, 10, fill=C['hint'], outline='') for i in range(3)]
        title_box = tk.Frame(activity_top, bg=C['bg2'])
        title_box.pack(side='left', fill='x', expand=True)
        self._activity_title = tk.Label(title_box, text='QNEST is working', font=FM.head, fg=C['text'], bg=C['bg2'], anchor='w')
        self._activity_title.pack(fill='x')
        self._activity_detail = tk.Label(title_box, text='', font=FM.small, fg=C['muted'], bg=C['bg2'], anchor='w', justify='left', wraplength=310)
        self._activity_detail.pack(fill='x', pady=(2, 0))
        self._activity_elapsed = tk.Label(activity_top, text='0.0 s', font=FM.small_mono, fg=C['hint'], bg=C['bg2'], anchor='e', width=9, padx=3)
        self._activity_elapsed.pack(side='right', padx=(8, 0), anchor='n')
        self._activity_steps_frame = tk.Frame(self._activity_frame, bg=C['bg2'], padx=13, pady=8)
        self._activity_steps_frame.pack(fill='x')
        self._activity_step_labels = []
        self._activity_steps = []
        self._activity_active_index = 0
        self._activity_started = 0.0
        self._activity_anim_phase = 0
        self._activity_anim_job = None
        self._activity_clock_job = None
        self._activity_visible = False
        activity_bottom = tk.Frame(self._activity_frame, bg=C['bg3'], padx=13, pady=7)
        activity_bottom.pack(fill='x')
        tk.Label(activity_bottom, text='Local inference can take a few seconds on the first turn.', font=FM.small, fg=C['hint'], bg=C['bg3'], anchor='w').pack(fill='x')
        _sep(self).pack(fill='x')
        composer = tk.Frame(self, bg=C['bg2'], padx=12, pady=11)
        composer.pack(fill='x')
        compose_card = tk.Frame(composer, bg=C['bg2'], highlightbackground=C['border'], highlightcolor=C['accent'], highlightthickness=1)
        compose_card.pack(fill='x')
        prompt_head = tk.Frame(compose_card, bg=C['bg2'], padx=10, pady=7)
        prompt_head.pack(fill='x')
        tk.Label(prompt_head, text='ASK QNEST', font=(FM.small.cget('family'), max(8, FM.small.cget('size') - 1), 'bold'), fg=C['muted'], bg=C['bg2']).pack(side='left')
        self._scope_badge = tk.Label(prompt_head, text='CURRENT WORKSPACE', font=(FM.small.cget('family'), max(8, FM.small.cget('size') - 2), 'bold'), fg=C['accent'], bg=C['menu_sel'], padx=7, pady=2)
        self._scope_badge.pack(side='right')
        _flow_from_pack(prompt_head, gap_y=4)
        self._prompt = tk.Text(compose_card, height=4, wrap='word', font=FM.body, bg=C['bg2'], fg=C['text'], insertbackground=C['accent'], relief='flat', bd=0, padx=10, pady=7, undo=True)
        self._prompt.pack(fill='x')
        self._prompt.bind('<Command-Return>', self._send_shortcut)
        self._prompt.bind('<Control-Return>', self._send_shortcut)
        compose_foot = tk.Frame(compose_card, bg=C['bg2'], padx=8, pady=7)
        compose_foot.pack(fill='x')
        tk.Label(compose_foot, text='⌘↵ to send', font=FM.small, fg=C['hint'], bg=C['bg2']).pack(side='left')
        self._send_btn = _button(compose_foot, 'Send  ↑', accent=C['accent'], command=self.send, padx=13, pady=5)
        self._send_btn.pack(side='right')
        self._thinking = tk.Label(composer, text='', font=FM.small, fg=C['muted'], bg=C['bg2'], anchor='w')
        self._thinking.pack(fill='x', pady=(6, 0))

    def _show_activity(self, *, title='QNEST is working', detail='', steps=None, active=0):
        steps = list(steps or [])
        self._activity_title.config(text=title)
        self._activity_detail.config(text=detail)
        self._activity_steps = steps
        self._activity_active_index = max(0, min(int(active), max(0, len(steps) - 1)))
        for child in self._activity_steps_frame.winfo_children():
            child.destroy()
        self._activity_step_labels = []
        for i, text in enumerate(steps):
            row = tk.Frame(self._activity_steps_frame, bg=C['bg2'])
            row.pack(fill='x', pady=2)
            mark = tk.Label(row, text='○', width=2, font=FM.small_mono, fg=C['hint'], bg=C['bg2'], anchor='w')
            mark.pack(side='left', anchor='n')
            label = tk.Label(row, text=text, font=FM.small, fg=C['muted'], bg=C['bg2'], justify='left', anchor='w', wraplength=300)
            label.pack(side='left', fill='x', expand=True, padx=(5, 0))
            self._activity_step_labels.append((mark, label))
        self.after_idle(lambda: _fluid_wrap_tree(self._activity_frame))
        self._paint_activity_steps()
        self._activity_started = time.monotonic()
        self._activity_anim_phase = 0
        self._activity_elapsed.config(text='0.0 s')
        self._activity_visible = True
        try:
            self._activity_frame.pack_forget()
        except Exception:
            pass
        try:
            self._activity_frame.pack(fill='x', padx=12, pady=(8, 6), before=self._activity_message_host)
        except Exception:
            self._activity_frame.pack(fill='x', padx=12, pady=(8, 6))
        self._animate_activity()
        self._tick_activity_clock()

    def _paint_activity_steps(self):
        for i, (mark, label) in enumerate(self._activity_step_labels):
            if i < self._activity_active_index:
                mark.config(text='✓', fg=C['success'])
                label.config(fg=C['muted'])
            elif i == self._activity_active_index:
                mark.config(text='●', fg=C['accent'])
                label.config(fg=C['text'])
            else:
                mark.config(text='○', fg=C['hint'])
                label.config(fg=C['hint'])

    def _update_activity(self, *, active=None, detail=None, title=None):
        if not self._activity_visible:
            return
        if title is not None:
            self._activity_title.config(text=title)
        if detail is not None:
            self._activity_detail.config(text=detail)
        if active is not None and self._activity_steps:
            self._activity_active_index = max(0, min(int(active), len(self._activity_steps) - 1))
            self._paint_activity_steps()

    def _animate_activity(self):
        if not self._activity_visible:
            return
        self._activity_anim_phase = (self._activity_anim_phase + 1) % 3
        for i, dot in enumerate(self._activity_dot_ids):
            self._activity_dots.itemconfigure(dot, fill=C['accent'] if i == self._activity_anim_phase else C['bg4'])
        self._activity_anim_job = self.after(300, self._animate_activity)

    def _tick_activity_clock(self):
        if not self._activity_visible:
            return
        elapsed = max(0.0, time.monotonic() - self._activity_started)
        self._activity_elapsed.config(text=f'{elapsed:0.1f} s')
        if elapsed >= 15 and self._activity_active_index == 2:
            self._activity_detail.config(text='Still generating locally — QNEST remains responsive.')
        elif elapsed >= 6 and self._activity_active_index == 2:
            self._activity_detail.config(text='Local model is still generating the structured response…')
        self._activity_clock_job = self.after(250, self._tick_activity_clock)

    def _hide_activity(self):
        self._activity_visible = False
        for job in (self._activity_anim_job, self._activity_clock_job):
            if job is not None:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass
        self._activity_anim_job = None
        self._activity_clock_job = None
        try:
            self._activity_frame.pack_forget()
        except Exception:
            pass

    def _model_progress(self, stage, detail=''):
        mapping = {'context': 0, 'connect': 1, 'inference': 2, 'validate': 3, 'ready': 3}
        active = mapping.get(str(stage), self._activity_active_index)
        self._update_activity(active=active, detail=detail or None)

    def _resize_messages(self, event):
        try:
            self._canvas.itemconfigure(self._msg_window, width=max(1, event.width))
            self._rewrap_cards(max(250, event.width - 54))
        except Exception:
            pass

    def _rewrap_cards(self, width=None):
        _fluid_wrap_tree(self._messages)

    def _wheel(self, event):
        try:
            x, y = self.winfo_pointerxy()
            target = self.winfo_containing(x, y)
            if target is None or not self._is_descendant(target):
                return
            self._canvas.yview_scroll(-1 * int(event.delta / 120), 'units')
        except Exception:
            pass

    def _is_descendant(self, widget):
        while widget is not None:
            if widget is self:
                return True
            try:
                widget = widget.master
            except Exception:
                return False
        return False

    def _probe_connection(self):
        client = self.root.get_assistant_client()

        def worker():
            try:
                msg = client.test_connection()
                self._async_queue.put(('probe', True, msg))
            except Exception as exc:
                self._async_queue.put(('probe', False, str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def _drain_async_queue(self):
        try:
            while True:
                item = self._async_queue.get_nowait()
                kind = item[0]
                if kind == 'probe':
                    self._connection_state(item[1], item[2])
                elif kind == 'progress':
                    self._model_progress(item[1], item[2] if len(item) > 2 else '')
                elif kind == 'reply':
                    self._receive(item[1])
                elif kind == 'error':
                    self._receive_error(item[1])
        except queue.Empty:
            pass
        try:
            if self.winfo_exists():
                self.after(100, self._drain_async_queue)
        except Exception:
            pass

    def _connection_state(self, ok, detail):
        try:
            if ok:
                self._status_dot.config(fg=C['success'])
                self._status_short.config(text='Ready' if 'not pulled' not in detail else 'Model missing')
            else:
                self._status_dot.config(fg=C['danger'])
                self._status_short.config(text='Offline')
        except Exception:
            pass

    def refresh_model_badge(self):
        prefs = self.root.ui_preferences
        provider = prefs.get('ai_provider', 'Ollama (local)')
        model = prefs.get('ai_model', 'qwen3:8b')
        self._model_label.config(text=f"{model}  ·  {('localhost' if provider.startswith('Ollama') else 'compatible endpoint')}")
        self._status_short.config(text='Local' if provider.startswith('Ollama') else 'Endpoint')

    def refresh_context_badge(self):
        try:
            n = len(self.root.circuit_records())
            page = self.root._active or 'Circuit'
            suffix = f" • {n} circuit{('s' if n != 1 else '')}" if n else ''
            self._context_var.set(f'Context  ·  {page}{suffix}')
        except Exception:
            pass

    def _welcome(self):
        self._add_card('assistant', 'Describe the experiment you want to build, change, run, or understand. I use the live QNEST workspace on every turn, can control all exposed validated settings, and adapt the workflow to current prerequisites. The scientific backend remains deterministic and you approve changes before they are applied.', subtle=True)
        self._add_suggestions()

    def _add_suggestions(self):
        row = tk.Frame(self._messages, bg=C['bg'])
        row.pack(fill='x', padx=12, pady=(0, 10))
        for text in ('Create the default 5–20q GHZ experiment', 'Explain this run', 'Configure a 7-QPU memory switch'):
            chip = _ghost_button(row, text, accent=C['accent'], command=lambda t=text: self._use_suggestion(t), padx=8, pady=4)
            chip.pack(fill='x', pady=2)
        self.after_idle(lambda r=row: _fluid_wrap_tree(r) if r.winfo_exists() else None)

    def _use_suggestion(self, text):
        self._prompt.delete('1.0', 'end')
        if text.startswith('Create'):
            text = 'Create a GHZ batch from 5 to 20 qubits in steps of 2 using MQT Bench, configure an all-to-all network with 7 QPUs and 4 qubits per QPU using a shared Memory-assisted switch, then compile, generate the Qoala schedules, and run AFA-QSP/HAMFA-QSP Monte Carlo using the reference Run parameters.'
        elif text.startswith('Explain'):
            text = 'Explain the current QNEST experiment state and what I should inspect next.'
        else:
            text = 'Configure an all-to-all network with 7 QPUs, 4 qubits per QPU, using a shared Memory-assisted switch.'
        self._prompt.insert('1.0', text)
        self._prompt.focus_set()

    def _add_card(self, role, text, *, subtle=False, actions=None):
        outer = tk.Frame(self._messages, bg=C['bg'])
        outer.pack(fill='x', padx=12, pady=(8, 4))
        user = role == 'user'
        accent = C['accent'] if user else C['comm']
        card_bg = C['menu_sel'] if user else C['bg2']
        card = tk.Frame(outer, bg=card_bg, highlightbackground=C['border'], highlightthickness=1)
        card.pack(fill='x', anchor='e' if user else 'w', padx=(30, 0) if user else (0, 18))
        head = tk.Frame(card, bg=card_bg, padx=11, pady=7)
        head.pack(fill='x')
        tk.Label(head, text='YOU' if user else 'QNEST ASSISTANT', font=(FM.small.cget('family'), max(8, FM.small.cget('size') - 1), 'bold'), fg=accent, bg=card_bg).pack(side='left')
        if not user:
            tk.Label(head, text='●', font=FM.small, fg=C['success'] if not subtle else C['hint'], bg=card_bg).pack(side='right')
        body = tk.Label(card, text=text, justify='left', anchor='w', font=FM.body, fg=C['muted'] if subtle else C['text'], bg=card_bg, padx=11, pady=7, wraplength=330)
        body._assistant_wrap = True
        body.pack(fill='x')
        if actions:
            self._build_plan_inside(card, actions, card_bg)
        self.after_idle(lambda o=outer: _fluid_wrap_tree(o) if o.winfo_exists() else None)
        self.after_idle(self._scroll_bottom)
        return card

    def _build_plan_inside(self, card, actions, bg):
        display_actions = self.root.assistant_plan_preview_actions(actions)
        _sep(card).pack(fill='x', padx=10, pady=(4, 0))
        box = tk.Frame(card, bg=bg, padx=11, pady=9)
        box.pack(fill='x')
        tk.Label(box, text=f"PLAN  ·  {len(display_actions)} ACTION{('S' if len(display_actions) != 1 else '')}", font=(FM.small.cget('family'), max(8, FM.small.cget('size') - 1), 'bold'), fg=C['muted'], bg=bg).pack(anchor='w')
        for i, action in enumerate(display_actions, 1):
            title = self.root.describe_assistant_action(action)
            r = tk.Frame(box, bg=bg)
            r.pack(fill='x', pady=(6, 0))
            tk.Label(r, text=str(i), width=2, font=FM.small_mono, fg=C['accent'], bg=C['menu_sel'], padx=2, pady=2).pack(side='left', anchor='n')
            lab = tk.Label(r, text=title, font=FM.small, fg=C['text'], bg=bg, justify='left', anchor='w', wraplength=285)
            lab._assistant_wrap = True
            lab.pack(side='left', fill='x', expand=True, padx=(7, 0))
        controls = tk.Frame(box, bg=bg)
        controls.pack(fill='x', pady=(11, 0))
        _ghost_button(controls, 'Dismiss', accent=C['muted'], command=self.dismiss_plan, padx=10, pady=5).pack(side='right')
        _button(controls, 'Apply plan', accent=C['accent'], command=self.apply_plan, padx=12, pady=5).pack(side='right', padx=(0, 7))

    def _scroll_bottom(self):
        try:
            self._messages.update_idletasks()
            self._canvas.configure(scrollregion=self._canvas.bbox('all'))
            self._canvas.yview_moveto(1.0)
        except Exception:
            pass

    def clear_chat(self):
        if self._busy:
            return
        self._hide_activity()
        for child in self._messages.winfo_children():
            child.destroy()
        self._history.clear()
        self._pending_actions.clear()
        self._welcome()

    def _send_shortcut(self, _event=None):
        self.send()
        return 'break'

    def send(self):
        if self._busy:
            return
        text = self._prompt.get('1.0', 'end').strip()
        if not text:
            return
        self._prompt.delete('1.0', 'end')
        self._add_card('user', text)
        self._history.append({'role': 'user', 'content': text})
        self._pending_actions = []
        self._busy = True
        self._send_btn.config(state='disabled')
        try:
            self._send_btn.config(text='Working…')
        except Exception:
            pass
        self._thinking.config(text='')
        self._status_dot.config(fg=C['warning'])
        self._show_activity(title='QNEST is thinking', detail='Grounding in QNEST knowledge and the current workspace…', steps=['Ground in QNEST knowledge + workspace', 'Check model connection', 'Generate response / action plan', 'Validate against QNEST actions'], active=0)
        context = self.root.assistant_context(text)
        client = self.root.get_assistant_client()
        history = list(self._history[:-1])

        def progress(stage, detail=''):
            self._async_queue.put(('progress', stage, detail))

        def worker():
            try:
                reply = client.ask(text, context, history, progress=progress)
                self._async_queue.put(('reply', reply))
            except Exception as exc:
                self._async_queue.put(('error', exc))
        threading.Thread(target=worker, daemon=True).start()

    def _receive(self, reply):
        self._busy = False
        self._send_btn.config(state='normal', text='Send  ↑')
        self._thinking.config(text='')
        self._update_activity(active=3, detail='Response validated and ready.')
        self._hide_activity()
        self._status_dot.config(fg=C['success'])
        self._pending_actions = list(reply.actions or [])
        self._add_card('assistant', reply.message, actions=self._pending_actions)
        self._history.append({'role': 'assistant', 'content': reply.message})
        if self._pending_actions and (not self.root.ui_preferences.get('ai_require_confirmation', True)):
            self.apply_plan()

    def _receive_error(self, exc):
        self._busy = False
        self._send_btn.config(state='normal', text='Send  ↑')
        self._thinking.config(text='')
        self._hide_activity()
        self._status_dot.config(fg=C['danger'])
        detail = str(exc)
        prefs = self.root.ui_preferences
        if prefs.get('ai_provider', '').startswith('Ollama'):
            message = f"I couldn't reach the local Qwen service. QNEST itself is still fully usable.\n\nEndpoint: {prefs.get('ai_endpoint')}\nModel: {prefs.get('ai_model')}\n\nStart Ollama and make sure the selected model is pulled, then try again. You can test the connection from Settings → AI Assistant.\n\nTechnical detail: {detail}"
        else:
            message = f'The configured model endpoint could not answer.\n\n{detail}'
        self._add_card('assistant', message, subtle=False)

    def dismiss_plan(self):
        self._pending_actions = []
        self._add_card('assistant', 'Plan dismissed. No QNEST settings were changed.', subtle=True)

    def apply_plan(self):
        if not self._pending_actions:
            return
        queue = list(self._pending_actions)
        self._pending_actions = []
        self._thinking.config(text=f'Applying validated plan  ·  {len(queue)} action(s)…')
        self._execute_queue(queue, completed=[])

    def _execute_queue(self, queue, completed):
        if not queue:
            self._thinking.config(text='')
            text = 'Applied the plan successfully.'
            if completed:
                text += '  ' + ' → '.join(completed)
            self._add_card('assistant', text, subtle=True)
            self.refresh_context_badge()
            return
        action = queue.pop(0)
        try:
            if str(action.get('name', '')) == 'complete_workflow':
                expanded = self.root.assistant_complete_workflow_actions(action.get('args') or {})
                queue[:0] = expanded
                self._thinking.config(text='Preparing end-to-end execution…')
                self.after(25, lambda: self._execute_queue(queue, completed))
                return
            result = self.root.execute_assistant_action(action)
            completed.append(str(result.get('label') or action.get('name')))
            async_key = result.get('async')
            if async_key:
                self._thinking.config(text=f'Running  ·  {completed[-1]}…')
                self._poll_async(async_key, queue, completed)
            else:
                self.after(25, lambda: self._execute_queue(queue, completed))
        except Exception as exc:
            self._thinking.config(text='')
            self._add_card('assistant', f'I stopped before applying the remaining actions because QNEST rejected one step:\n\n{type(exc).__name__}: {exc}')

    def _poll_async(self, key, queue, completed):
        if self.root.assistant_operation_busy(key):
            self.after(250, lambda: self._poll_async(key, queue, completed))
            return
        self.after(75, lambda: self._execute_queue(queue, completed))

class MainWindow(tk.Tk):
    MENU_ITEMS = [('Circuit', '◈', CircuitPanel, 'accent'), ('Network', '⬡', NetworkPanel, 'accent2'), ('Compile', '⚙', CompilePanel, 'success'), ('Schedule', '▦', SchedulePanel, 'warning'), ('Run', '▶', RunPanel, 'danger')]

    def __init__(self):
        super().__init__()
        self.withdraw()
        self.ui_preferences = _load_ui_preferences()
        _activate_theme(self.ui_preferences['theme'])
        FM.set_user_scale(self.ui_preferences['scale'])
        _install_interaction_defaults(self)
        self.title(f'{APP_NAME} — {APP_SUBTITLE}')
        self.configure(bg=C['bg'])
        sw, sh = (self.winfo_screenwidth(), self.winfo_screenheight())
        w, h = (int(sw * 0.84), int(sh * 0.84))
        self.geometry(f'{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}')
        self.minsize(980, 650)
        self._panels = {}
        self._menu_btns = {}
        self._menu_accents = {}
        self._active = ''
        self.pipeline = PipelineController(PROJECT_ROOT)
        self._circuit_pipelines = {}
        self._active_circuit_id = None
        self._batch_dir = None
        self._batch_tables = {}
        FM._init()
        FM.scale(w, h)
        self._configure_ttk_styles()
        self._apply_window_scale_constraints()
        self._build_layout()
        start_page = self.ui_preferences.get('start_page', 'Circuit')
        if start_page not in {item[0] for item in self.MENU_ITEMS}:
            start_page = 'Circuit'
        self._select(start_page)
        self._polish_interactive_tree(self)
        self._last_size = (w, h)
        self.bind('<Configure>', self._on_resize)
        self.bind('<Map>', lambda _e: self._schedule_scale_stabilization(), add='+')
        self.after_idle(self._schedule_scale_stabilization)
        self.after_idle(self._schedule_responsive_refresh)
        if self.ui_preferences.get('show_splash', True):
            SplashScreen(self, animate=self.ui_preferences.get('animate_splash', True))
        else:
            self.deiconify()
        self.protocol('WM_DELETE_WINDOW', self._on_close)

    def _configure_ttk_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except Exception:
            pass
        ratio = max(0.85, min(1.3, FM.ratio))
        line_body = max(16, int(FM.body.metrics('linespace')))
        line_small = max(14, int(FM.small.metrics('linespace')))
        row_h = max(28, line_body + round(10 * ratio))
        tab_x = max(14, round(18 * ratio))
        tab_y = max(6, round(8 * ratio))
        combo_y = max(3, round(5 * ratio))
        style.configure('Treeview', background=C['bg2'], fieldbackground=C['bg2'], foreground=C['text'], bordercolor=C['border'], lightcolor=C['border'], darkcolor=C['border'], rowheight=row_h, font=FM.body)
        style.map('Treeview', background=[('selected', C['menu_sel'])], foreground=[('selected', C['text'])])
        style.configure('Treeview.Heading', background=C['bg3'], foreground=C['text'], relief='flat', bordercolor=C['border'], font=(FM.small.cget('family'), FM.small.cget('size'), 'bold'), padding=(max(8, round(10 * ratio)), max(5, round(7 * ratio))))
        style.map('Treeview.Heading', background=[('active', C['bg4'])])
        style.configure('TNotebook', background=C['bg2'], borderwidth=0)
        style.configure('TNotebook.Tab', background=C['bg3'], foreground=C['muted'], padding=(tab_x, tab_y), borderwidth=0, font=FM.small)
        style.map('TNotebook.Tab', background=[('selected', C['bg2']), ('active', C['bg4'])], foreground=[('selected', C['text']), ('active', C['text'])])
        style.configure('TProgressbar', troughcolor=C['bg3'], background=C['accent'], bordercolor=C['bg3'], lightcolor=C['accent'], darkcolor=C['accent'], thickness=max(8, round(10 * ratio)))
        style.configure('TCombobox', fieldbackground=C['bg3'], background=C['bg3'], foreground=C['text'], arrowcolor=C['muted'], bordercolor=C['border'], font=FM.body, padding=(max(5, round(7 * ratio)), combo_y), arrowsize=max(12, round(14 * ratio)))
        style.map('TCombobox', fieldbackground=[('readonly', C['bg3']), ('disabled', C['bg4'])], foreground=[('readonly', C['text']), ('disabled', C['muted'])], selectbackground=[('readonly', C['menu_sel'])], selectforeground=[('readonly', C['text'])])
        style.configure('Vertical.TScrollbar', arrowsize=max(12, round(14 * ratio)))
        style.configure('Horizontal.TScrollbar', arrowsize=max(12, round(14 * ratio)))

    def _apply_window_scale_constraints(self):
        factor = max(0.9, min(1.25, float(self.ui_preferences.get('scale', 1.0))))
        sw, sh = (self.winfo_screenwidth(), self.winfo_screenheight())
        min_w = min(int(sw * 0.92), max(980, round(980 * factor)))
        min_h = min(int(sh * 0.9), max(650, round(650 * factor)))
        try:
            self.minsize(min_w, min_h)
        except Exception:
            pass

    def _polish_interactive_tree(self, widget):
        ratio = max(0.85, min(1.3, FM.ratio))
        try:
            if isinstance(widget, tk.Entry):
                widget.configure(relief='flat', highlightthickness=1, highlightbackground=C['border'], highlightcolor=C['accent'], bg=C['bg3'], fg=C['text'], insertbackground=C['accent'], font=FM.mono)
            elif isinstance(widget, tk.Spinbox):
                widget.configure(relief='flat', highlightthickness=1, highlightbackground=C['border'], highlightcolor=C['accent'], bg=C['bg3'], fg=C['text'], insertbackground=C['accent'], buttonbackground=C['bg2'], font=FM.mono)
            elif isinstance(widget, tk.Menubutton):
                widget.configure(relief='flat', highlightthickness=1, highlightbackground=C['border'], highlightcolor=C['accent'], bg=C['bg3'], fg=C['text'], font=FM.small, activebackground=C['menu_sel'], activeforeground=C['text'], padx=max(7, round(9 * ratio)), pady=max(3, round(5 * ratio)))
        except Exception:
            pass
        for child in widget.winfo_children():
            self._polish_interactive_tree(child)

    @staticmethod
    def _pack_pad_total(widget, option='pady'):
        try:
            value = widget.pack_info().get(option, 0)
            parts = widget.tk.splitlist(value) if isinstance(value, str) else value
            if isinstance(parts, (tuple, list)):
                nums = [int(float(x)) for x in parts]
                return sum(nums) if len(nums) > 1 else 2 * nums[0]
            return 2 * int(float(parts))
        except Exception:
            try:
                return 2 * int(float(value))
            except Exception:
                return 0

    def _fit_compact_nonpropagating_bars(self, widget=None):
        widget = widget or self
        for frame in widget.winfo_children():
            try:
                if isinstance(frame, tk.Frame) and frame.winfo_manager() in {'pack', 'place', 'grid'}:
                    configured_h = int(float(frame.cget('height') or 0))
                    if 0 < configured_h <= 80 and (not bool(frame.pack_propagate())):
                        needed = configured_h
                        horizontal_children = 0
                        for child in frame.winfo_children():
                            if child.winfo_manager() != 'pack':
                                continue
                            info = child.pack_info()
                            if str(info.get('side', 'top')) in {'left', 'right'}:
                                horizontal_children += 1
                                needed = max(needed, int(child.winfo_reqheight()) + self._pack_pad_total(child, 'pady') + 2)
                        if horizontal_children and needed > configured_h:
                            frame.configure(height=needed)
            except Exception:
                pass
            self._fit_compact_nonpropagating_bars(frame)

    def _force_font_geometry_refresh(self, widget=None):
        widget = widget or self
        for child in widget.winfo_children():
            try:
                keys = child.keys()
                if 'font' in keys:
                    current = child.cget('font')
                    if current:
                        child.configure(font=current)
            except Exception:
                pass
            self._force_font_geometry_refresh(child)

    def _stabilize_scaled_layout(self):
        self._scale_stabilize_job = None
        try:
            if not self.winfo_exists() or not self.winfo_ismapped():
                return
            w, h = (self.winfo_width(), self.winfo_height())
            if w < 100 or h < 100:
                return
            FM.scale(w, h)
            self._configure_ttk_styles()
            self._polish_interactive_tree(self)
            self._force_font_geometry_refresh(self)
            self.update_idletasks()
            self._fit_compact_nonpropagating_bars(self)
            self._update_sidebar_width(w)
            self.update_idletasks()
        except Exception:
            pass

    def _schedule_scale_stabilization(self, delay=45):
        try:
            job = getattr(self, '_scale_stabilize_job', None)
            if job:
                self.after_cancel(job)
        except Exception:
            pass
        try:
            self._scale_stabilize_job = self.after(delay, self._stabilize_scaled_layout)
        except Exception:
            self._scale_stabilize_job = None

    def _toolbar_button(self, parent, text, command):
        lbl = tk.Label(parent, text=text, font=FM.small, fg=C['muted'], bg=C['toolbar_bg'], padx=12, pady=8, cursor='hand2')
        lbl.pack(side='right', padx=(0, 2), pady=8)
        lbl.bind('<Button-1>', lambda _e: command())
        lbl.bind('<Enter>', lambda _e: lbl.config(bg=C['toolbar_hover'], fg=C['text']))
        lbl.bind('<Leave>', lambda _e: lbl.config(bg=C['toolbar_bg'], fg=C['muted']))
        return lbl

    def _on_close(self):
        seen = set()
        try:
            controllers = [self.pipeline, *self._circuit_pipelines.values()]
            for ctl in controllers:
                bridge = getattr(ctl, '_pytket_bridge', None)
                if bridge is not None and id(bridge) not in seen:
                    seen.add(id(bridge))
                    try:
                        bridge.shutdown()
                    except Exception:
                        pass
        except Exception:
            pass
        self.destroy()

    def _build_layout(self):
        topbar = tk.Frame(self, bg=C['toolbar_bg'], height=58, highlightbackground=C['border'], highlightthickness=1)
        topbar.pack(fill='x', side='top')
        topbar.pack_propagate(False)
        self._topbar = topbar
        brand = tk.Frame(topbar, bg=C['toolbar_bg'])
        brand.pack(side='left', fill='y', padx=(18, 0))
        tk.Label(brand, text='QNEST', font=FM.head, fg=C['text'], bg=C['toolbar_bg']).pack(side='left', fill='y')
        self._brand_bar = tk.Frame(brand, bg=C['accent'], width=3)
        self._brand_bar.pack(side='left', fill='y', pady=15, padx=12)
        self._brand_subtitle = tk.Label(brand, text=APP_SUBTITLE, font=FM.small, fg=C['muted'], bg=C['toolbar_bg'])
        self._brand_subtitle.pack(side='left', fill='y')
        topbar.bind('<Configure>', lambda _e: self.after_idle(self._fit_topbar), add='+')
        self._toolbar_button(topbar, 'About', self._show_about)
        self._toolbar_button(topbar, 'Report a Bug', self._show_bug_report)
        self._toolbar_button(topbar, 'Documentation', self._open_documentation)
        self._toolbar_button(topbar, 'Settings', self._show_settings)
        self._assistant_toolbar_btn = self._toolbar_button(topbar, '✦  AI Assistant', self.toggle_assistant)
        self._assistant_toolbar_btn.bind('<Enter>', lambda _e: self._paint_assistant_toolbar_button(True))
        self._assistant_toolbar_btn.bind('<Leave>', lambda _e: self._paint_assistant_toolbar_button(False))
        body = tk.Frame(self, bg=C['bg'])
        body.pack(fill='both', expand=True)
        sidebar = tk.Frame(body, bg=C['sidebar_bg'])
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)
        self._sidebar = sidebar
        self.update_idletasks()
        self._update_sidebar_width(self.winfo_width())
        tk.Label(sidebar, text='WORKSPACE', font=FM.small, fg=C['sidebar_muted'], bg=C['sidebar_bg'], padx=20, pady=18).pack(anchor='w')
        for name, icon, _, accent_key in self.MENU_ITEMS:
            self._menu_accents[name] = accent_key
            btn = tk.Label(sidebar, text=f'{icon}   {name}', font=FM.menu, fg=C['sidebar_text'], bg=C['sidebar_bg'], anchor='w', padx=20, pady=15, cursor='hand2')
            btn.pack(fill='x', padx=8, pady=2)
            btn.bind('<Button-1>', lambda e, n=name: self._select(n))
            btn.bind('<Enter>', lambda e, b=btn, n=name: self._hover(b, n, True))
            btn.bind('<Leave>', lambda e, b=btn, n=name: self._hover(b, n, False))
            self._menu_btns[name] = btn
        foot = tk.Frame(sidebar, bg=C['sidebar_bg'])
        foot.pack(side='bottom', fill='x', padx=18, pady=16)
        tk.Label(foot, text='RESEARCH TOOLKIT', font=FM.small, fg=C['sidebar_muted'], bg=C['sidebar_bg']).pack(anchor='w')
        tk.Label(foot, text=f'v{APP_VERSION}', font=FM.small_mono, fg=C['sidebar_text'], bg=C['sidebar_bg']).pack(anchor='w', pady=(3, 0))
        self._workspace_panes = tk.PanedWindow(body, orient='horizontal', bg=C['sep'], bd=0, sashwidth=5, sashrelief='flat', showhandle=False)
        self._workspace_panes.pack(side='left', fill='both', expand=True)
        self._content = tk.Frame(self._workspace_panes, bg=C['bg'])
        self._workspace_panes.add(self._content, minsize=620, stretch='always')
        for name, _, PanelClass, _ in self.MENU_ITEMS:
            panel = PanelClass(self._content)
            panel.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._panels[name] = panel
        self._assistant_dock = AssistantDock(self._workspace_panes, self)
        self._assistant_visible = False
        self._assistant_last_width = None
        if self.ui_preferences.get('ai_dock_open', True):
            self.toggle_assistant(True)
        else:
            self._paint_assistant_toolbar_button(False)

    def _fit_topbar(self):
        bar = getattr(self, '_topbar', None)
        sub = getattr(self, '_brand_subtitle', None)
        if bar is None or sub is None:
            return
        try:
            width = int(bar.winfo_width())
            if width <= 1:
                return
            need = 0
            for child in bar.pack_slaves():
                l, r = _pad_pair(child.pack_info().get('padx', 0))
                need += int(child.winfo_reqwidth()) + l + r
            if sub.winfo_manager():
                show = need + 16 <= width
            else:
                show = need + int(sub.winfo_reqwidth()) + int(self._brand_bar.winfo_reqwidth()) + 24 + 16 <= width
            if show and (not sub.winfo_manager()):
                self._brand_bar.pack(side='left', fill='y', pady=15, padx=12)
                sub.pack(side='left', fill='y')
            elif not show and sub.winfo_manager():
                sub.pack_forget()
                self._brand_bar.pack_forget()
        except Exception:
            pass

    def _schedule_responsive_refresh(self, delay=120):
        try:
            job = getattr(self, '_responsive_refresh_job', None)
            if job:
                self.after_cancel(job)
        except Exception:
            pass
        try:
            self._responsive_refresh_job = self.after(delay, self._run_responsive_refresh)
        except Exception:
            self._responsive_refresh_job = None

    def _run_responsive_refresh(self):
        self._responsive_refresh_job = None
        self._refresh_responsive_layouts()

    def _update_sidebar_width(self, window_width):
        if not hasattr(self, '_sidebar'):
            return
        try:
            longest = max((FM.menu.measure(name) for name, *_ in self.MENU_ITEMS))
            icon_allowance = max((FM.menu.measure(icon) for _, icon, *_ in self.MENU_ITEMS))
            footer_need = max(FM.small.measure('RESEARCH TOOLKIT'), FM.small_mono.measure(f'v{APP_VERSION}')) + 42
            required = max(longest + icon_allowance + 92, footer_need)
        except Exception:
            required = 190
        proportional = min(270, max(190, int(window_width) // 7))
        self._sidebar.config(width=max(190, required, proportional))

    def _on_resize(self, event):
        if event.widget is not self:
            return
        w, h = (event.width, event.height)
        if (w, h) == getattr(self, '_last_size', None):
            return
        self._last_size = (w, h)
        old_ratio = FM.ratio
        FM.scale(w, h)
        if abs(FM.ratio - old_ratio) > 1e-06:
            self._configure_ttk_styles()
            self._polish_interactive_tree(self)
            self._schedule_scale_stabilization()
        self._update_sidebar_width(w)
        self._schedule_responsive_refresh()

    def _select(self, name):
        if self._active:
            prev = self._menu_btns[self._active]
            prev.config(fg=C['sidebar_text'], bg=C['sidebar_bg'])
        self._active = name
        accent = C[self._menu_accents[name]]
        btn = self._menu_btns[name]
        btn.config(fg='#FFFFFF', bg=C['sidebar_sel'], highlightbackground=accent, highlightthickness=1)
        panel = self._panels[name]
        panel.lift()
        self.after_idle(lambda p=panel: _fluid_wrap_tree(p))
        hook = getattr(panel, 'on_show', None)
        if callable(hook):
            try:
                hook()
            except Exception:
                pass
        if hasattr(self, '_assistant_dock'):
            try:
                self._assistant_dock.refresh_context_badge()
            except Exception:
                pass

    def circuit_records(self):
        panel = self._panels.get('Circuit')
        return panel.get_circuit_records() if panel is not None else []

    def get_pipeline_for_circuit(self, circuit_id, create=True):
        ctl = self._circuit_pipelines.get(circuit_id)
        if ctl is None and create:
            if not self._circuit_pipelines and self.pipeline.state.run_dir is None:
                ctl = self.pipeline
            else:
                ctl = PipelineController(PROJECT_ROOT)
            self._circuit_pipelines[circuit_id] = ctl
        return ctl

    def activate_circuit(self, circuit_id, create=False):
        ctl = self.get_pipeline_for_circuit(circuit_id, create=create)
        self._active_circuit_id = circuit_id
        if ctl is not None:
            self.pipeline = ctl
        return ctl

    def on_circuit_set_changed(self):
        valid = {r.get('id') for r in self.circuit_records()}
        for cid in list(self._circuit_pipelines):
            if cid not in valid:
                self._circuit_pipelines.pop(cid, None)
        for name in ('Compile', 'Schedule', 'Run'):
            panel = self._panels.get(name)
            hook = getattr(panel, 'refresh_circuit_context', None) if panel else None
            if callable(hook):
                try:
                    hook()
                except Exception:
                    pass
        if hasattr(self, '_assistant_dock'):
            try:
                self._assistant_dock.refresh_context_badge()
            except Exception:
                pass

    def ensure_batch_dir(self):
        if self._batch_dir is None:
            stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            self._batch_dir = PROJECT_ROOT / 'batch_runs' / f'{stamp}_batch'
            for sub in ('01_compile', '02_schedule', '03_run', 'plots'):
                (self._batch_dir / sub).mkdir(parents=True, exist_ok=True)
        return self._batch_dir

    def save_batch_table(self, stage, rows, filename):
        try:
            import pandas as pd
            df = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
            out = self.ensure_batch_dir() / stage / filename
            out.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(out, index=False)
            try:
                df.to_html(out.with_suffix('.html'), index=False, border=0)
            except Exception:
                pass
            self._batch_tables[filename] = df
            try:
                self.write_batch_manifest()
            except Exception:
                pass
            return (df, out)
        except Exception:
            return (rows, None)

    def write_batch_manifest(self):
        if self._batch_dir is None:
            return None
        records = []
        for rec in self.circuit_records():
            ctl = self._circuit_pipelines.get(rec.get('id'))
            records.append({'id': rec.get('id'), 'name': rec.get('name'), 'source': rec.get('source'), 'series': rec.get('series'), 'qubits': rec.get('qubits'), 'run_dir': str(ctl.state.run_dir) if ctl and ctl.state.run_dir else None, 'compiled': bool(ctl and ctl.state.compile_metadata), 'scheduled': bool(ctl and ctl.state.qoala_result is not None), 'simulated': bool(ctl and ctl.state.afa_summary is not None and (ctl.state.hamfa_summary is not None))})
        path = self._batch_dir / 'batch_manifest.json'
        path.write_text(json.dumps({'generated': datetime.now().isoformat(timespec='seconds'), 'mode': 'Batch / sweep', 'circuits': records, 'batch_tables': sorted(self._batch_tables.keys())}, indent=2, default=str), encoding='utf-8')
        return path

    def export_batch_zip(self, destination):
        batch_dir = self._batch_dir
        if batch_dir is None or not batch_dir.exists():
            raise RuntimeError('There is no batch experiment to export yet.')
        destination = Path(destination).expanduser()
        if destination.suffix.lower() != '.zip':
            destination = destination.with_suffix('.zip')
        self.write_batch_manifest()
        with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as zf:
            for path in batch_dir.rglob('*'):
                if path.is_file():
                    zf.write(path, Path('batch') / path.relative_to(batch_dir))
            for rec in self.circuit_records():
                ctl = self._circuit_pipelines.get(rec.get('id'))
                run_dir = ctl.state.run_dir if ctl else None
                if run_dir and run_dir.exists():
                    for path in run_dir.rglob('*'):
                        if path.is_file():
                            zf.write(path, Path('circuits') / rec.get('name', rec['id']) / path.relative_to(run_dir))
        return destination

    def _hover(self, btn, name, entering):
        if name == self._active:
            return
        btn.config(bg=C['sidebar_sel'] if entering else C['sidebar_bg'], fg='#FFFFFF' if entering else C['sidebar_text'])

    def _assistant_is_attached(self):
        if not hasattr(self, '_assistant_dock') or not hasattr(self, '_workspace_panes'):
            return False
        try:
            dock_path = str(self._assistant_dock)
            return dock_path in {str(pane) for pane in self._workspace_panes.panes()}
        except Exception:
            return False

    def _paint_assistant_toolbar_button(self, hovered=False):
        if not hasattr(self, '_assistant_toolbar_btn'):
            return
        visible = self._assistant_is_attached()
        try:
            if visible:
                bg = C['menu_sel'] if not hovered else C['bg4']
                fg = C['accent']
            else:
                bg = C['toolbar_hover'] if hovered else C['toolbar_bg']
                fg = C['text'] if hovered else C['muted']
            self._assistant_toolbar_btn.config(bg=bg, fg=fg)
        except Exception:
            pass

    def toggle_assistant(self, show=None):
        if not hasattr(self, '_assistant_dock'):
            return False
        attached = self._assistant_is_attached()
        target = not attached if show is None else bool(show)
        if target and (not attached):
            default_width = max(420, min(470, int(self.winfo_width() * 0.28)))
            width = int(self._assistant_last_width or default_width)
            width = max(380, min(width, max(380, int(self.winfo_width() * 0.48))))
            try:
                panes_w = int(self._workspace_panes.winfo_width())
                if panes_w > 1:
                    width = max(320, min(width, panes_w - _scaled(560)))
                    self._workspace_panes.paneconfigure(self._content, minsize=max(480, min(620, panes_w - width)))
            except Exception:
                pass
            self._workspace_panes.add(self._assistant_dock, minsize=min(380, width), width=width, stretch='never')
            try:
                self._assistant_dock.refresh_model_badge()
                self._assistant_dock.refresh_context_badge()
            except Exception:
                pass
        elif not target and attached:
            try:
                width = int(self._assistant_dock.winfo_width())
                if width >= 300:
                    self._assistant_last_width = width
            except Exception:
                pass
            self._workspace_panes.forget(self._assistant_dock)
        self._assistant_visible = self._assistant_is_attached()
        self._paint_assistant_toolbar_button(False)
        self.after_idle(self._refresh_responsive_layouts)
        return self._assistant_visible

    def _refresh_responsive_layouts(self):
        for panel in getattr(self, '_panels', {}).values():
            hook = getattr(panel, 'refresh_layout', None)
            if callable(hook):
                try:
                    hook()
                except Exception:
                    pass
        if hasattr(self, '_assistant_dock'):
            try:
                self._assistant_dock.update_idletasks()
            except Exception:
                pass
        try:
            _fluid_wrap_tree(self)
        except Exception:
            pass

    def get_assistant_client(self):
        prefs = self.ui_preferences
        return QNESTAssistantClient(provider=prefs.get('ai_provider', 'Ollama (local)'), endpoint=prefs.get('ai_endpoint', 'http://127.0.0.1:11434'), model=prefs.get('ai_model', 'qwen3:8b'), temperature=prefs.get('ai_temperature', 0.2))

    def assistant_control_catalog(self):
        controls = {}

        def add(control_id, label, current, kind='string', *, options=None, minimum=None, maximum=None, unit=None, active=True, note=None):
            item = {'label': label, 'type': kind, 'current': current, 'active': bool(active)}
            if options is not None:
                item['options'] = list(options)
            if minimum is not None:
                item['min'] = minimum
            if maximum is not None:
                item['max'] = maximum
            if unit:
                item['unit'] = unit
            if note:
                item['note'] = note
            controls[control_id] = item
        prefs = self.ui_preferences
        scale_num = float(prefs.get('scale', 1.0))
        scale_label = min(SettingsDialog.SCALE_LABELS, key=lambda k: abs(SettingsDialog.SCALE_LABELS[k] - scale_num))
        add('settings.theme', 'Appearance theme / template', prefs.get('theme'), 'enum', options=THEMES.keys())
        add('settings.scale', 'Interface scale', scale_label, 'enum', options=SettingsDialog.SCALE_LABELS.keys())
        add('settings.show_splash', 'Show splash screen', bool(prefs.get('show_splash', True)), 'boolean')
        add('settings.animate_splash', 'Animate splash logo', bool(prefs.get('animate_splash', True)), 'boolean')
        add('settings.start_page', 'Startup workspace', prefs.get('start_page', 'Circuit'), 'enum', options=SettingsDialog.START_PAGES)
        add('settings.ai_provider', 'AI provider', prefs.get('ai_provider', 'Ollama (local)'), 'enum', options=('Ollama (local)', 'OpenAI-compatible'))
        add('settings.ai_endpoint', 'AI endpoint', prefs.get('ai_endpoint', 'http://127.0.0.1:11434'), 'string')
        add('settings.ai_model', 'AI model', prefs.get('ai_model', 'qwen3:8b'), 'string', note='Common local choices: qwen3:4b, qwen3:8b, qwen3:14b, qwen3:30b')
        add('settings.ai_temperature', 'AI temperature', float(prefs.get('ai_temperature', 0.2)), 'number', minimum=0.0, maximum=1.0)
        add('settings.ai_require_confirmation', 'Require approval before applying an AI plan', bool(prefs.get('ai_require_confirmation', True)), 'boolean')
        add('settings.ai_dock_open', 'Open AI Assistant at startup', bool(prefs.get('ai_dock_open', True)), 'boolean')
        add('assistant.visible', 'AI Assistant dock visibility now', bool(self._assistant_is_attached()), 'boolean')
        circuit = self._panels.get('Circuit')
        if circuit:
            add('circuit.workflow_mode', 'Circuit workflow', circuit._workflow_mode.get(), 'enum', options=('Single circuit', 'Batch / sweep'))
            add('circuit.tab', 'Circuit sub-tab', circuit._active_tab.get(), 'enum', options=('Import', 'MQT Bench', 'QASM Editor'))
            selected_benchmarks = [name for name, var in {**circuit._scal_vars, **circuit._ns_vars}.items() if var.get()]
            add('circuit.mqt.benchmarks', 'Selected MQT Bench benchmarks', selected_benchmarks, 'multi_enum', options=list(circuit.SCALABLE) + list(circuit.NON_SCALABLE))
            add('circuit.mqt.qubits', 'Single-circuit MQT qubits', int(circuit._q_count.get()), 'integer', minimum=1)
            add('circuit.mqt.min_qubits', 'Batch MQT minimum qubits', int(circuit._q_min.get()), 'integer', minimum=1)
            add('circuit.mqt.max_qubits', 'Batch MQT maximum qubits', int(circuit._q_max.get()), 'integer', minimum=1)
            add('circuit.mqt.step', 'Batch MQT qubit step', int(circuit._q_step.get()), 'integer', minimum=1)
            records = circuit.get_circuit_records()
            active = circuit.get_active_record()
            add('circuit.active', 'Active circuit', active.get('id') if active else None, 'enum', options=[r.get('id') for r in records], note='Circuit IDs map to names in CURRENT QNEST CONTEXT.circuits')
        network = self._panels.get('Network')
        if network:
            add('network.tab', 'Network view', getattr(network, '_active_assistant_tab', 'Table'), 'enum', options=('Table', 'Designer'))
            add('network.servers', 'Number of QPUs / servers', int(network._n_srv.get()), 'integer', minimum=2, maximum=32)
            add('network.qubits_per_qpu', 'Qubits per QPU', int(network._qppq.get()), 'integer', minimum=1, maximum=10000)
            add('network.topology', 'Network topology', network._topo.get(), 'enum', options=('All-to-all', 'Linear chain', 'Star', 'Ring', 'Custom'))
            add('network.interconnect', 'All-to-all interconnect', network._interconnect.get(), 'enum', options=('Direct QPU links', 'Shared switch'), active=network._topo.get() == 'All-to-all')
            add('network.switch_mode', 'Shared-switch mode', network._switch_mode.get(), 'enum', options=('All-photonic', 'Memory-assisted'), active=network._is_switched())
            active_keys = {spec[1] for spec in network._active_specs()}
            seen = set()
            for spec in network.OPTICAL_SPECS + network.ALL_PHOTONIC_SWITCH_SPECS + network.MEMORY_SPECS:
                group, key, label, _default, unit, kind, choices = spec
                if key in seen:
                    continue
                seen.add(key)
                control_kind = 'enum' if choices else 'integer' if unit in {'integer', 'count', 'ports', 'cycles'} else 'number'
                kwargs = {'options': choices} if choices else {}
                if unit == '0–1':
                    kwargs.update({'minimum': 0.0, 'maximum': 1.0})
                add(f'network.physical.{key}', f'{group}: {label}', network._physical_vars[key].get(), control_kind, unit=unit or None, active=key in active_keys, **kwargs)
            for _row, rd in network._link_rows:
                a, b = rd.get('pair', (None, None))
                if a is None:
                    continue
                add(f'network.link.S{a}-S{b}.distance_km', f'Physical link S{a} ↔ S{b} distance', rd['dist_var'].get(), 'number', minimum=0.0, unit='km')
        compile_panel = self._panels.get('Compile')
        if compile_panel:
            add('compile.scope', 'Compile circuit scope', compile_panel._scope.get(), 'enum', options=list(compile_panel._scope_combo.cget('values') or []))
            add('compile.method', 'Distribution method', compile_panel._method.get(), 'enum', options=compile_panel.DISTRIBUTION_METHODS)
            add('compile.seed', 'Compile/distribution seed', compile_panel._seed.get(), 'integer')
            add('compile.run_name', 'Compile run name', compile_panel._circuit_name.get(), 'string')
        schedule = self._panels.get('Schedule')
        if schedule:
            add('schedule.single_qubit_us', 'Single-qubit gate time', schedule._timings['single_qubit_time_ns'].get(), 'number', minimum=0.0, unit='µs')
            add('schedule.two_qubit_us', 'Two-qubit gate time', schedule._timings['two_qubit_time_ns'].get(), 'number', minimum=0.0, unit='µs')
            add('schedule.epr_ejpp_start_us', 'EPR + EJPP start time', schedule._timings['starting_process_time_ns'].get(), 'number', minimum=0.0, unit='µs')
            add('schedule.ejpp_ending_us', 'EJPP ending process time', schedule._timings['ending_process_time_ns'].get(), 'number', minimum=0.0, unit='µs')
            add('schedule.strategy', 'Qoala scheduling strategy', schedule._strategy.get(), 'enum', options=('QOALA', 'FCFS', 'EPR_PRIORITY', 'RANDOM'))
            add('schedule.scope', 'Schedule circuit scope', schedule._scope.get(), 'enum', options=list(schedule._scope_combo.cget('values') or []))
            add('schedule.view.kind', 'Schedule visualization kind', schedule._gantt_kind.get(), 'enum', options=('Timed Gantt', 'Layer Gantt'))
            add('schedule.view.cell_width', 'Layer Gantt cell width', schedule._gantt_cw.get(), 'enum', options=('xs', 'sm', 'md', 'lg', 'xl'))
            add('schedule.view.px_per_time', 'Timed Gantt pixels per time unit', int(schedule._gantt_px.get()), 'integer', minimum=1, maximum=80)
            add('schedule.view.row_height', 'Gantt row height', schedule._gantt_rh.get(), 'enum', options=('tight', 'normal', 'spacious'))
            add('schedule.view.labels', 'Gantt labels', schedule._gantt_labels.get(), 'enum', options=('on', 'off'))
            add('schedule.view.gates', 'Gantt gate filter', schedule._gantt_gates.get(), 'enum', options=('all', 'local only', 'remote only'))
        run = self._panels.get('Run')
        if run:
            run_active = bool(network is not None and network._is_switched())
            run_note = None if run_active else 'Available only when Network uses All-to-all → Shared switch.'
            add('run.fidelity_threshold', 'AFA/HAMFA fidelity threshold F_T', run._vars['F_T'].get(), 'number', minimum=0.0, maximum=1.0, active=run_active, note=run_note)
            add('run.alpha', 'HAMFA cutoff fraction α', run._vars['alpha'].get(), 'number', minimum=0.0, maximum=1.0, active=run_active, note=run_note)
            add('run.seed', 'Run base random seed', run._vars['seed'].get(), 'integer', active=run_active, note=run_note)
            add('run.hedge', 'HAMFA hedge mode', run._hedge.get(), 'enum', options=('race', 'sequential', 'off'), active=run_active, note=run_note)
            add('run.monte_carlo_runs', 'Monte Carlo runs per point', int(run._mc_runs.get()), 'integer', minimum=1, maximum=10000, active=run_active, note=run_note)
            add('run.scope', 'Run circuit scope', run._scope.get(), 'enum', options=list(run._scope_combo.cget('values') or []), active=run_active, note=run_note)
            add('run.result_units', 'Run result-table display units', run._result_units.get() if hasattr(run, '_result_units') else 'µs', 'enum', options=('ns', 'µs'))
            add('run.deadline_equality_blocked', 'Deadline equality counts as blocked', bool(run._deadline.get()), 'boolean')
        return controls

    @staticmethod
    def _assistant_bool(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        text = str(value).strip().lower()
        if text in {'1', 'true', 'yes', 'on', 'enabled', 'enable'}:
            return True
        if text in {'0', 'false', 'no', 'off', 'disabled', 'disable'}:
            return False
        raise ValueError(f'Expected a boolean value, got: {value}')

    def _assistant_apply_preference(self, key, value):
        prefs = {}
        if key == 'theme':
            if value not in THEMES:
                raise ValueError(f'Unknown theme: {value}')
            prefs[key] = value
        elif key == 'scale':
            label = str(value).strip()
            if label in SettingsDialog.SCALE_LABELS:
                prefs[key] = SettingsDialog.SCALE_LABELS[label]
            else:
                number = float(str(value).replace('%', ''))
                if number > 10:
                    number /= 100.0
                allowed = tuple(SettingsDialog.SCALE_LABELS.values())
                if not any((abs(number - x) < 1e-09 for x in allowed)):
                    raise ValueError('Scale must be 90%, 100%, 110%, or 125%.')
                prefs[key] = number
        elif key in {'show_splash', 'animate_splash', 'ai_require_confirmation', 'ai_dock_open'}:
            prefs[key] = self._assistant_bool(value)
            if key == 'show_splash' and (not prefs[key]):
                prefs['animate_splash'] = False
        elif key == 'start_page':
            if value not in SettingsDialog.START_PAGES:
                raise ValueError(f'Unknown startup page: {value}')
            prefs[key] = value
        elif key == 'ai_provider':
            if value not in {'Ollama (local)', 'OpenAI-compatible'}:
                raise ValueError(f'Unsupported AI provider: {value}')
            prefs[key] = value
        elif key == 'ai_endpoint':
            text = str(value).strip()
            if not text.startswith(('http://', 'https://')):
                raise ValueError('AI endpoint must start with http:// or https://')
            prefs[key] = text
        elif key == 'ai_model':
            text = str(value).strip()
            if not text:
                raise ValueError('AI model cannot be empty.')
            prefs[key] = text
        elif key == 'ai_temperature':
            number = float(value)
            if not 0.0 <= number <= 1.0:
                raise ValueError('AI temperature must be in [0, 1].')
            prefs[key] = number
        else:
            raise ValueError(f'Unsupported preference: {key}')
        self.apply_ui_preferences(prefs)

    def _assistant_set_control(self, control_id, value):
        cid = str(control_id or '').strip()
        catalog = self.assistant_control_catalog()
        if cid not in catalog:
            raise ValueError(f'Unknown QNEST control: {cid}')
        if cid.startswith('settings.'):
            self._assistant_apply_preference(cid.split('.', 1)[1], value)
            return {'label': f"Set {catalog[cid]['label']}"}
        if cid == 'assistant.visible':
            self.toggle_assistant(self._assistant_bool(value))
            return {'label': 'Show AI Assistant' if self._assistant_bool(value) else 'Hide AI Assistant'}
        circuit = self._panels['Circuit']
        if cid == 'circuit.workflow_mode':
            return self.execute_assistant_action({'name': 'set_circuit_workflow', 'args': {'mode': str(value)}})
        if cid == 'circuit.tab':
            return self.execute_assistant_action({'name': 'select_circuit_tab', 'args': {'tab': str(value)}})
        if cid == 'circuit.mqt.benchmarks':
            vals = value if isinstance(value, list) else [value]
            return self.execute_assistant_action({'name': 'configure_mqt', 'args': {'benchmarks': vals}})
        if cid in {'circuit.mqt.qubits', 'circuit.mqt.min_qubits', 'circuit.mqt.max_qubits', 'circuit.mqt.step'}:
            key = {'circuit.mqt.qubits': 'qubits', 'circuit.mqt.min_qubits': 'min_qubits', 'circuit.mqt.max_qubits': 'max_qubits', 'circuit.mqt.step': 'step'}[cid]
            return self.execute_assistant_action({'name': 'configure_mqt', 'args': {key: int(value)}})
        if cid == 'circuit.active':
            wanted = str(value)
            records = circuit.get_circuit_records()
            rec = next((r for r in records if str(r.get('id')) == wanted or str(r.get('name')) == wanted), None)
            if not rec:
                raise ValueError(f'Circuit is unavailable: {value}')
            circuit.activate_record(rec['id'])
            return {'label': f"Activate circuit {rec.get('name')}"}
        network = self._panels['Network']
        if cid == 'network.tab':
            val = str(value)
            if val not in {'Table', 'Designer'}:
                raise ValueError('Network tab must be Table or Designer.')
            network._active_assistant_tab = val
            network._switch(val)
            self._select('Network')
            return {'label': f'Network → {val}'}
        if cid in {'network.servers', 'network.qubits_per_qpu', 'network.topology', 'network.interconnect', 'network.switch_mode'}:
            arg = cid.split('.', 1)[1]
            return self.execute_assistant_action({'name': 'configure_network', 'args': {arg: value}})
        if cid.startswith('network.physical.'):
            key = cid.split('.', 2)[2]
            if key not in network._physical_vars:
                raise ValueError(f'Unknown physical parameter: {key}')
            spec = next((sp for sp in network.OPTICAL_SPECS + network.ALL_PHOTONIC_SWITCH_SPECS + network.MEMORY_SPECS if sp[1] == key), None)
            if spec:
                _group, _key, _label, _default, unit, _kind, choices = spec
                if choices and str(value) not in choices:
                    raise ValueError(f"{key} must be one of: {', '.join(map(str, choices))}")
                if not choices:
                    number = float(value)
                    if unit == '0–1' and (not 0.0 <= number <= 1.0):
                        raise ValueError(f'{key} must be in [0, 1].')
                    if unit in {'integer', 'count', 'ports', 'cycles'} and int(number) != number:
                        raise ValueError(f'{key} must be an integer.')
                    if unit in {'count', 'ports', 'cycles'} and number < 1:
                        raise ValueError(f'{key} must be at least 1.')
            network._physical_vars[key].set(str(value))
            network._schedule_recalc()
            return {'label': f'Set network physical parameter {key}'}
        m = re.fullmatch('network\\.link\\.S(\\d+)-S(\\d+)\\.distance_km', cid)
        if m:
            pair = (int(m.group(1)), int(m.group(2)))
            distance = float(value)
            if distance < 0:
                raise ValueError('Link distance cannot be negative.')
            for _row, rd in network._link_rows:
                if tuple(rd.get('pair', ())) in {pair, pair[::-1]}:
                    rd['dist_var'].set(str(distance))
                    network._schedule_recalc()
                    return {'label': f'Set S{pair[0]} ↔ S{pair[1]} distance'}
            raise ValueError(f'Physical link S{pair[0]} ↔ S{pair[1]} is not present in the current topology.')
        compile_panel = self._panels['Compile']
        if cid == 'compile.method':
            return self.execute_assistant_action({'name': 'configure_compile', 'args': {'method': str(value)}})
        if cid == 'compile.seed':
            return self.execute_assistant_action({'name': 'configure_compile', 'args': {'seed': int(value)}})
        if cid == 'compile.scope':
            if not self._assistant_set_scope(compile_panel, value):
                raise ValueError(f'Compile scope is unavailable: {value}')
            return {'label': 'Set Compile scope'}
        if cid == 'compile.run_name':
            compile_panel._circuit_name.set(str(value))
            return {'label': 'Set Compile run name'}
        schedule = self._panels['Schedule']
        timing_map = {'schedule.single_qubit_us': 'single_qubit_time_ns', 'schedule.two_qubit_us': 'two_qubit_time_ns', 'schedule.epr_ejpp_start_us': 'starting_process_time_ns', 'schedule.ejpp_ending_us': 'ending_process_time_ns'}
        if cid in timing_map:
            number = float(value)
            if number < 0:
                raise ValueError('Schedule timing cannot be negative.')
            schedule._timings[timing_map[cid]].set(str(number))
            return {'label': f"Set {catalog[cid]['label']}"}
        if cid == 'schedule.strategy':
            val = str(value)
            if val not in {'QOALA', 'FCFS', 'EPR_PRIORITY', 'RANDOM'}:
                raise ValueError(f'Unknown schedule strategy: {val}')
            schedule._strategy.set(val)
            return {'label': f'Set schedule strategy to {val}'}
        if cid == 'schedule.scope':
            if not self._assistant_set_scope(schedule, value):
                raise ValueError(f'Schedule scope is unavailable: {value}')
            return {'label': 'Set Schedule scope'}
        if cid.startswith('schedule.view.'):
            mapping = {'schedule.view.kind': (schedule._gantt_kind, {'Timed Gantt', 'Layer Gantt'}), 'schedule.view.cell_width': (schedule._gantt_cw, {'xs', 'sm', 'md', 'lg', 'xl'}), 'schedule.view.row_height': (schedule._gantt_rh, {'tight', 'normal', 'spacious'}), 'schedule.view.labels': (schedule._gantt_labels, {'on', 'off'}), 'schedule.view.gates': (schedule._gantt_gates, {'all', 'local only', 'remote only'})}
            if cid == 'schedule.view.px_per_time':
                number = int(value)
                if not 1 <= number <= 80:
                    raise ValueError('Timed Gantt px/time must be 1–80.')
                schedule._gantt_px.set(number)
            else:
                var, opts = mapping[cid]
                val = str(value)
                if val not in opts:
                    raise ValueError(f"{cid} must be one of: {', '.join(sorted(opts))}")
                var.set(val)
            if cid == 'schedule.view.kind':
                schedule._on_gantt_kind_changed()
            else:
                schedule._queue_gantt_rerender(delay=80)
            return {'label': f"Set {catalog[cid]['label']}"}
        run = self._panels['Run']
        if cid in {'run.fidelity_threshold', 'run.alpha', 'run.seed', 'run.hedge', 'run.monte_carlo_runs', 'run.deadline_equality_blocked'}:
            keymap = {'run.fidelity_threshold': 'fidelity_threshold', 'run.alpha': 'alpha', 'run.seed': 'seed', 'run.hedge': 'hedge', 'run.monte_carlo_runs': 'monte_carlo_runs', 'run.deadline_equality_blocked': 'deadline_equality_blocked'}
            return self.execute_assistant_action({'name': 'configure_run', 'args': {keymap[cid]: value}})
        if cid == 'run.scope':
            if not self._assistant_set_scope(run, value):
                raise ValueError(f'Run scope is unavailable: {value}')
            return {'label': 'Set Run scope'}
        if cid == 'run.result_units':
            val = str(value).strip()
            if val.lower() in {'us', 'µs', 'μs', 'microseconds', 'microsecond'}:
                val = 'µs'
            elif val.lower() in {'ns', 'nanoseconds', 'nanosecond'}:
                val = 'ns'
            if val not in {'ns', 'µs'}:
                raise ValueError('Run result units must be ns or µs.')
            run._result_units.set(val)
            run._on_result_units_changed()
            return {'label': f'Set Run result-table display units to {val}'}
        raise ValueError(f'Control is exposed but has no setter: {cid}')

    def assistant_complete_workflow_actions(self, args=None):
        args = args or {}
        circuit = self._panels['Circuit']
        records = circuit.get_circuit_records()
        selected_mqt = any((v.get() for v in list(circuit._scal_vars.values()) + list(circuit._ns_vars.values())))
        actions = []
        if not records:
            if not selected_mqt:
                raise ValueError('No circuit is available. Select/import a circuit or configure an MQT benchmark first.')
            actions.append({'name': 'generate_mqt', 'args': {}})
        batch = circuit.is_batch_mode()
        scope = 'All circuits' if batch else 'Active circuit'
        actions.extend([{'name': 'configure_compile', 'args': {'scope': scope}}, {'name': 'compile', 'args': {}}, {'name': 'configure_schedule', 'args': {'scope': scope}}, {'name': 'schedule', 'args': {}}])
        network = self._panels.get('Network')
        if network is not None and network._is_switched():
            actions.extend([{'name': 'configure_run', 'args': {'scope': scope}}, {'name': 'run_protocols', 'args': {}}])
        return actions

    @staticmethod
    def _assistant_json_safe(value, *, max_depth=7, max_items=180):
        if max_depth < 0:
            return '…'
        if value is None or isinstance(value, (str, int, float, bool)):
            if isinstance(value, float) and (not math.isfinite(value)):
                return str(value)
            return value
        if isinstance(value, Path):
            return str(value)
        if hasattr(value, 'item'):
            try:
                return MainWindow._assistant_json_safe(value.item(), max_depth=max_depth - 1, max_items=max_items)
            except Exception:
                pass
        if hasattr(value, 'tolist') and (not isinstance(value, (dict, list, tuple, set))):
            try:
                return MainWindow._assistant_json_safe(value.tolist(), max_depth=max_depth - 1, max_items=max_items)
            except Exception:
                pass
        if isinstance(value, dict):
            out = {}
            items = list(value.items())
            for key, item in items[:max_items]:
                out[str(key)] = MainWindow._assistant_json_safe(item, max_depth=max_depth - 1, max_items=max_items)
            if len(items) > max_items:
                out['_truncated_items'] = len(items) - max_items
            return out
        if isinstance(value, (list, tuple, set)):
            seq = list(value)
            out = [MainWindow._assistant_json_safe(v, max_depth=max_depth - 1, max_items=max_items) for v in seq[:max_items]]
            if len(seq) > max_items:
                out.append({'_truncated_items': len(seq) - max_items})
            return out
        return str(value)

    @classmethod
    def _assistant_table_digest(cls, table, *, max_rows=8, max_numeric=20, max_categorical=12):
        if table is None:
            return None
        try:
            import pandas as pd
            if isinstance(table, list):
                table = pd.DataFrame(table)
            elif not hasattr(table, 'columns'):
                return cls._assistant_json_safe(table)
            df = table.copy()
            columns = [str(c) for c in df.columns]
            digest = {'rows': int(len(df)), 'columns': columns}
            if df.empty:
                return digest
            preferred_tokens = ('request', 'qpu', 'wait', 'deadline', 'punish', 'completion', 'duration', 'time', 'trial', 'blocked', 'fidelity', 'memory', 'photonic', 'rescued', 'age', 'cut', 'success', 'event')
            numeric_cols = []
            for col in df.columns:
                try:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        numeric_cols.append(col)
                except Exception:
                    pass
            numeric_cols = sorted(numeric_cols, key=lambda c: (0 if any((t in str(c).lower() for t in preferred_tokens)) else 1, columns.index(str(c))))[:max_numeric]
            stats = {}
            for col in numeric_cols:
                try:
                    ser = pd.to_numeric(df[col], errors='coerce').dropna()
                    if ser.empty:
                        continue
                    stats[str(col)] = {'count': int(ser.count()), 'mean': cls._assistant_json_safe(float(ser.mean())), 'std': cls._assistant_json_safe(float(ser.std(ddof=0))), 'min': cls._assistant_json_safe(float(ser.min())), 'median': cls._assistant_json_safe(float(ser.median())), 'max': cls._assistant_json_safe(float(ser.max()))}
                except Exception:
                    continue
            if stats:
                digest['numeric_statistics'] = stats
            counts = {}
            for col in df.columns:
                if len(counts) >= max_categorical:
                    break
                try:
                    ser = df[col].dropna()
                    nunique = int(ser.astype(str).nunique()) if len(ser) else 0
                    name = str(col).lower()
                    important = any((t in name for t in ('blocked', 'memory', 'photonic', 'rescued', 'success', 'mode', 'case', 'qpu')))
                    if 0 < nunique <= 12 and (important or not pd.api.types.is_numeric_dtype(df[col])):
                        vc = ser.astype(str).value_counts().head(12)
                        counts[str(col)] = {str(k): int(v) for k, v in vc.items()}
                except Exception:
                    continue
            if counts:
                digest['categorical_counts'] = counts
            sample = df.head(max_rows)
            digest['sample_rows'] = cls._assistant_json_safe(sample.to_dict(orient='records'), max_items=max_rows)
            signal_cols = [c for c in df.columns if any((t in str(c).lower() for t in ('blocked', 'rescued', 'failed', 'rejection', 'punishment')))]
            notable_parts = []
            for col in signal_cols:
                try:
                    ser = df[col]
                    text = ser.astype(str).str.strip().str.lower()
                    mask = text.isin({'yes', 'true', 'blocked', 'failed'})
                    if pd.api.types.is_numeric_dtype(ser):
                        mask = mask | (pd.to_numeric(ser, errors='coerce').fillna(0) > 0)
                    part = df.loc[mask].head(max_rows)
                    if not part.empty:
                        notable_parts.append(part)
                except Exception:
                    continue
            if notable_parts:
                notable = pd.concat(notable_parts, ignore_index=True).drop_duplicates().head(max_rows)
                digest['notable_rows'] = cls._assistant_json_safe(notable.to_dict(orient='records'), max_items=max_rows)
            return digest
        except Exception:
            try:
                return {'rows': int(len(table)), 'data': cls._assistant_json_safe(table)}
            except Exception:
                return {'data': cls._assistant_json_safe(table)}

    @staticmethod
    def _assistant_result_detail_requested(user_text):
        text = str(user_text or '').lower()
        if not text:
            return False
        terms = ('result', 'results', 'interpret', 'analyse', 'analyze', 'analysis', 'explain', 'technical', 'why', 'blocked', 'fidelity', 'latency', 'punishment', 'request table', 'schedule', 'compile', 'distribution', 'afa', 'hamfa', 'monte carlo', 'performance', 'compare', 'comparison', 'inspect', 'diagnose', 'what happened', 'what does')
        return any((term in text for term in terms))

    @classmethod
    def _assistant_exact_table_payload(cls, table):
        if table is None:
            return None
        try:
            import pandas as pd
            df = table.copy() if isinstance(table, pd.DataFrame) else pd.DataFrame(table)
            records = df.to_dict(orient='records')
            return {'row_count': int(len(df)), 'columns': [str(c) for c in df.columns], 'rows': cls._assistant_json_safe(records, max_items=max(200, len(records) + 10))}
        except Exception:
            return {'data': cls._assistant_json_safe(table, max_items=500)}

    def _assistant_scientific_results(self, *, include_tables=False):
        circuit_panel = self._panels.get('Circuit')
        network_panel = self._panels.get('Network')
        compile_panel = self._panels.get('Compile')
        schedule_panel = self._panels.get('Schedule')
        run_panel = self._panels.get('Run')
        out = {'detail_level': 'clean Monte Carlo result tables + technical layer data' if include_tables else 'layer summaries', 'unit_conventions': {'backend_time': 'nanoseconds (ns) unless a field explicitly names another unit', 'gui_time': 'Run result tables can display ns or µs; saved per-request result tables remain raw nanoseconds [ns]', 'conversion': '1 µs = 1000 ns', 'fidelity': 'dimensionless probability-like value on [0, 1]'}, 'layers': {}, 'circuits': []}
        records = self.circuit_records()
        out['layers']['circuit'] = {'workflow_mode': circuit_panel._workflow_mode.get() if circuit_panel else None, 'active_circuit_id': getattr(self, '_active_circuit_id', None), 'circuit_count': len(records), 'records': self._assistant_json_safe(records, max_items=80)}
        network_data = None
        if network_panel:
            try:
                network_data = network_panel.get_network_data()
            except Exception as exc:
                network_data = {'error': f'{type(exc).__name__}: {exc}'}
        out['layers']['network'] = self._assistant_json_safe(network_data, max_items=220)
        active_id = getattr(self, '_active_circuit_id', None)
        if active_id is None and len(records) == 1:
            active_id = records[0].get('id')
        selected_mc_index = 0
        selected_result_id = None
        if run_panel is not None:
            try:
                selected_mc_index = int(run_panel._mc_index())
                selected_result_id = run_panel._result_id()
            except Exception:
                pass
        selected_units = 'ns'
        if run_panel is not None and hasattr(run_panel, '_result_units'):
            try:
                selected_units = run_panel._result_units.get()
            except Exception:
                pass
        out['layers']['run_result_table_view'] = {'selected_circuit_id': selected_result_id, 'selected_monte_carlo_run': selected_mc_index + 1, 'display_units': selected_units, 'storage_units': 'raw notebook [ns]', 'table_contract': 'clean researcher-facing per-request results only; simulator diagnostics are intentionally hidden; UI may convert time columns to µs on request; no GUI-added metadata columns', 'afa_columns_raw_ns': list(NOTEBOOK_AFA_TABLE_COLUMNS), 'hamfa_columns_raw_ns': list(NOTEBOOK_HAMFA_TABLE_COLUMNS)}
        for rec in records:
            cid = rec.get('id')
            detail_this_circuit = bool(include_tables or (cid is not None and cid == active_id))
            ctl = self.get_pipeline_for_circuit(cid, create=False)
            item = {'circuit': self._assistant_json_safe(rec), 'status': {'compiled': False, 'scheduled': False, 'simulated': False}}
            if ctl is None:
                out['circuits'].append(item)
                continue
            state = ctl.state
            if state.compile_metadata:
                item['status']['compiled'] = True
                compile_meta = dict(state.compile_metadata)
                compile_meta.pop('renderer_snapshots', None)
                compile_meta.pop('bridge_file', None)
                compile_meta.pop('circuit_artifacts', None)
                item['compile'] = self._assistant_json_safe(compile_meta, max_items=220)
            if isinstance(state.qoala_result, dict):
                item['status']['scheduled'] = True
                qresult = dict(state.qoala_result)
                schedule_rows = qresult.pop('schedule', []) or []
                qresult.pop('gantt_previews', None)
                item['schedule'] = {'summary': self._assistant_json_safe(qresult, max_items=120), 'event_count': len(schedule_rows), 'request_count': int(len(state.request_table)) if state.request_table is not None else 0}
                if detail_this_circuit:
                    item['schedule']['events'] = self._assistant_table_digest(schedule_rows, max_rows=8)
                    item['schedule']['request_table'] = self._assistant_table_digest(state.request_table, max_rows=10)
            if state.afa_summary is not None or state.hamfa_summary is not None:
                item['status']['simulated'] = bool(state.afa_summary is not None and state.hamfa_summary is not None)
                public_summary_keys = ('simulation_runs', 'total_requests', 'total_blocked_requests', 'total_punishment_time_ns', 'memory_assisted_successful', 'all_photonic_used')

                def _public_summary(summary):
                    summary = summary or {}
                    return {k: summary.get(k) for k in public_summary_keys if k in summary}
                run_result = {'afa_qsp_summary': self._assistant_json_safe(_public_summary(state.afa_summary), max_items=30), 'hamfa_qsp_summary': self._assistant_json_safe(_public_summary(state.hamfa_summary), max_items=30), 'afa_monte_carlo_replicates': len(getattr(state, 'afa_run_summaries', []) or []), 'hamfa_monte_carlo_replicates': len(getattr(state, 'hamfa_run_summaries', []) or [])}
                try:
                    comparison = PipelineController._comparison_table(state.afa_summary or {}, state.hamfa_summary or {})
                    run_result['afa_vs_hamfa'] = self._assistant_json_safe(comparison.to_dict(orient='records'), max_items=120)
                except Exception:
                    pass
                afa_exact_runs = getattr(state, 'afa_exact_run_tables', []) or []
                hamfa_exact_runs = getattr(state, 'hamfa_exact_run_tables', []) or []
                run_result['result_table_runs_available'] = max(len(afa_exact_runs), len(hamfa_exact_runs))
                if detail_this_circuit:
                    exact_idx = selected_mc_index
                    if afa_exact_runs:
                        exact_idx = min(exact_idx, len(afa_exact_runs) - 1)
                    elif hamfa_exact_runs:
                        exact_idx = min(exact_idx, len(hamfa_exact_runs) - 1)
                    exact_pair = {'monte_carlo_run': exact_idx + 1, 'display_units': selected_units, 'storage_units': 'raw notebook [ns]'}

                    def _assistant_display_table(table):
                        if table is None:
                            return None
                        if selected_units == 'µs':
                            return _display_times_in_us(table)
                        return table
                    if afa_exact_runs and exact_idx < len(afa_exact_runs):
                        exact_pair['afa_qsp_results'] = self._assistant_exact_table_payload(_assistant_display_table(afa_exact_runs[exact_idx]))
                    if hamfa_exact_runs and exact_idx < len(hamfa_exact_runs):
                        exact_pair['hamfa_qsp_results'] = self._assistant_exact_table_payload(_assistant_display_table(hamfa_exact_runs[exact_idx]))
                    if 'afa_qsp_results' not in exact_pair and state.afa_table is not None:
                        try:
                            t = state.afa_table
                            if 'Monte Carlo run' in t.columns:
                                t = t.loc[t['Monte Carlo run'] == exact_idx + 1]
                            exact_pair['afa_qsp_results'] = self._assistant_exact_table_payload(_assistant_display_table(t.reindex(columns=NOTEBOOK_AFA_TABLE_COLUMNS).reset_index(drop=True)))
                        except Exception:
                            pass
                    if 'hamfa_qsp_results' not in exact_pair and state.hamfa_table is not None:
                        try:
                            t = state.hamfa_table
                            if 'Monte Carlo run' in t.columns:
                                t = t.loc[t['Monte Carlo run'] == exact_idx + 1]
                            exact_pair['hamfa_qsp_results'] = self._assistant_exact_table_payload(_assistant_display_table(t.reindex(columns=NOTEBOOK_HAMFA_TABLE_COLUMNS).reset_index(drop=True)))
                        except Exception:
                            pass
                    run_result['result_tables'] = exact_pair
                item['run'] = run_result
            out['circuits'].append(item)
        batch = {}
        try:
            if compile_panel and getattr(compile_panel, '_batch_results', None):
                batch['compile'] = self._assistant_json_safe(compile_panel._batch_results, max_items=100)
        except Exception:
            pass
        try:
            if schedule_panel and getattr(schedule_panel, '_batch_results', None):
                batch['schedule'] = self._assistant_json_safe(schedule_panel._batch_results, max_items=100)
        except Exception:
            pass
        try:
            if run_panel and getattr(run_panel, '_batch_results', None) is not None:
                br = run_panel._batch_results
                if len(br):
                    batch['run'] = self._assistant_table_digest(br, max_rows=12, max_numeric=28)
        except Exception:
            pass
        if batch:
            out['batch_results'] = batch
        try:
            if run_panel and getattr(run_panel, '_batch_plots', None) is not None:
                out['batch_plots'] = [str(Path(p).name) for p in getattr(run_panel._batch_plots, '_paths', [])]
        except Exception:
            pass
        return out

    def assistant_context(self, user_text=None):
        circuits = []
        for rec in self.circuit_records():
            circuits.append({'id': rec.get('id'), 'name': rec.get('name'), 'source': rec.get('source'), 'series': rec.get('series'), 'qubits': rec.get('qubits'), 'gates': rec.get('gates'), 'depth': rec.get('depth')})
        circuit = self._panels.get('Circuit')
        network = self._panels.get('Network')
        compile_panel = self._panels.get('Compile')
        schedule = self._panels.get('Schedule')
        run = self._panels.get('Run')
        ctx = {'application': {'name': 'QNEST — Quantum Network End-to-End Simulation Toolkit', 'version': APP_VERSION, 'knowledge_source': 'docs/QNEST_Knowledge_Base.md'}, 'active_workspace': self._active, 'circuit_workflow': circuit._workflow_mode.get() if circuit else None, 'circuit_tab': circuit._active_tab.get() if circuit else None, 'circuits': circuits, 'available_mqt_scalable_benchmarks': list(getattr(circuit, 'SCALABLE', [])), 'available_mqt_fixed_benchmarks': list(getattr(circuit, 'NON_SCALABLE', [])), 'controls': self.assistant_control_catalog(), 'notebook_reference_defaults': self._assistant_json_safe(NOTEBOOK_REFERENCE_DEFAULTS), 'assistant_default_experiment': self._assistant_json_safe(ASSISTANT_DEFAULT_EXPERIMENT), 'assistant_runtime_policy': {'state_source': 'live workspace context on every turn', 'control_scope': 'all exposed validated QNEST controls/actions', 'default_all_to_all_interconnect': 'Shared switch', 'default_shared_switch_mode': 'Memory-assisted', 'run_rule': 'AFA-QSP/HAMFA-QSP Monte Carlo is available only for All-to-all → Shared switch; explicit switch-free networks end after Schedule and export prior-stage artifacts.', 'explicit_user_choices_override_defaults': True}, 'network': {}, 'compile': {}, 'schedule': {}, 'run': {}}
        if network:
            try:
                ctx['network'] = {'servers': int(network._n_srv.get()), 'qubits_per_qpu': int(network._qppq.get()), 'topology': network._topo.get(), 'interconnect': network._interconnect.get(), 'switch_mode': network._switch_mode.get() if network._is_switched() else None}
            except Exception:
                pass
        if compile_panel:
            ctx['compile'] = {'distribution_method': compile_panel._method.get(), 'seed': compile_panel._seed.get(), 'busy': bool(compile_panel._busy), 'compiled_circuits': sum((bool(c.state.compile_metadata) for c in self._circuit_pipelines.values())), 'available_methods': list(compile_panel.DISTRIBUTION_METHODS)}
        if schedule:
            ctx['schedule'] = {'strategy': schedule._strategy.get(), 'timings_us': {k: v.get() for k, v in schedule._timings.items()}, 'busy': bool(schedule._busy), 'scheduled_circuits': sum((bool(c.state.qoala_result is not None) for c in self._circuit_pipelines.values()))}
        if run:
            ctx['run'] = {'available': bool(network is not None and network._is_switched()), 'availability_rule': 'Monte Carlo requires All-to-all → Shared switch; switch-free workflows stop after Schedule and export prior-stage artifacts.', 'fidelity_threshold': run._vars['F_T'].get(), 'alpha': run._vars['alpha'].get(), 'base_seed': run._vars['seed'].get(), 'hedge': run._hedge.get(), 'monte_carlo_runs': int(run._mc_runs.get()), 'result_display_units': run._result_units.get() if hasattr(run, '_result_units') else 'µs', 'busy': bool(run._running), 'completed_result_sets': sum((bool(c.state.afa_summary is not None and c.state.hamfa_summary is not None) for c in self._circuit_pipelines.values()))}
            try:
                phys = network.protocol_physical_parameters() if network is not None and network._is_switched() else None
                trial_us = schedule.protocol_epr_attempt_time_us() if schedule is not None else None
                if phys and trial_us:
                    p_ref = float(phys['p_succ'])
                    trial_ns = float(trial_us) * 1000.0
                    ctx['run']['theory_sanity'] = {'trial_model': 'N ~ Geometric(p_succ); T_success = N * time_per_trial_ns', 'p_succ': p_ref, 'time_per_trial_ns': trial_ns, 'expected_trials_per_success': 1.0 / p_ref if p_ref > 0 else None, 'expected_success_time_ns': trial_ns / p_ref if p_ref > 0 else None, 'display_note': 'Raw nanosecond values can be numerically large; µs display changes units only, not the simulation.'}
            except Exception:
                pass
        ctx['scientific_results'] = self._assistant_scientific_results(include_tables=self._assistant_result_detail_requested(user_text))
        try:
            state = self.pipeline.state
            results = {}
            if state.compile_metadata:
                keys = ('distribution_method', 'n_qubits', 'n_gates_original', 'depth_original', 'n_qpus', 'n_gates_distributed', 'distributed_depth', 'ebits_builtin')
                results['compile_summary'] = {k: state.compile_metadata.get(k) for k in keys if k in state.compile_metadata}
            if isinstance(state.qoala_result, dict):
                qkeys = ('strategy', 'total_execution_time_ns', 'n_original_events', 'used_qpus', 'requests')
                results['schedule_summary'] = {k: state.qoala_result.get(k) for k in qkeys if k in state.qoala_result}
            if state.afa_summary:
                results['afa_qsp_summary'] = dict(state.afa_summary)
            if state.hamfa_summary:
                results['hamfa_qsp_summary'] = dict(state.hamfa_summary)
            if results:
                ctx['current_results'] = results
        except Exception:
            pass
        return ctx

    def assistant_plan_preview_actions(self, actions):
        preview = []
        try:
            mc_runs = int(self._panels['Run']._mc_runs.get())
        except Exception:
            mc_runs = None
        network = self._panels.get('Network')
        try:
            topology = network._topo.get() if network else None
            interconnect = network._interconnect.get() if network else None
            switch_mode = network._switch_mode.get() if network and network._is_switched() else None
        except Exception:
            topology = interconnect = switch_mode = None
        for planned in actions or []:
            pname = str(planned.get('name', ''))
            pargs = planned.get('args') or {}
            if pname == 'configure_run' and pargs.get('monte_carlo_runs') is not None:
                try:
                    mc_runs = int(pargs.get('monte_carlo_runs'))
                except Exception:
                    pass
            elif pname == 'set_control':
                cid = str(pargs.get('control_id', ''))
                if cid == 'run.monte_carlo_runs':
                    try:
                        mc_runs = int(pargs.get('value'))
                    except Exception:
                        pass
                elif cid == 'network.topology':
                    topology = pargs.get('value')
                elif cid == 'network.interconnect':
                    interconnect = pargs.get('value')
                elif cid == 'network.switch_mode':
                    switch_mode = pargs.get('value')
            elif pname == 'configure_network':
                topology = pargs.get('topology', topology)
                interconnect = pargs.get('interconnect', interconnect)
                switch_mode = pargs.get('switch_mode', switch_mode)
        future_run = str(topology) == 'All-to-all' and str(interconnect) == 'Shared switch' and (str(switch_mode) in {'All-photonic', 'Memory-assisted'})
        for action in actions or []:
            if str(action.get('name', '')) != 'complete_workflow':
                preview.append(action)
                continue
            preview.extend([{'name': 'workflow_compile', 'args': {}}, {'name': 'workflow_schedule', 'args': {}}])
            if future_run:
                preview.append({'name': 'workflow_run', 'args': {'monte_carlo_runs': mc_runs}})
        return preview

    def describe_assistant_action(self, action):
        name = str(action.get('name', ''))
        args = action.get('args') or {}
        labels = {'navigate': lambda: f"Open {args.get('page', 'workspace')}", 'set_circuit_workflow': lambda: f"Set circuit workflow to {args.get('mode')}", 'select_circuit_tab': lambda: f"Open Circuit → {args.get('tab')}", 'configure_mqt': lambda: 'Configure MQT Bench' + (f" ({', '.join(map(str, args.get('benchmarks', [])))})" if args.get('benchmarks') else ''), 'generate_mqt': lambda: 'Generate configured MQT circuit set', 'configure_network': lambda: f"Configure network ({args.get('servers', 'current')} QPUs, {args.get('topology', 'current topology')}" + (f", {args.get('interconnect')}" if args.get('interconnect') else '') + (f" / {args.get('switch_mode')}" if args.get('switch_mode') else '') + ')', 'sync_network_designer': lambda: 'Synchronize topology to Network Designer', 'configure_compile': lambda: f"Configure distribution ({args.get('method', 'current method')})", 'compile': lambda: 'Prepare + distribute circuit(s)', 'configure_schedule': lambda: 'Configure Qoala scheduler', 'schedule': lambda: 'Generate Qoala schedule(s)', 'configure_run': lambda: 'Configure AFA-QSP / HAMFA-QSP Monte Carlo', 'run_protocols': lambda: 'Run AFA-QSP + HAMFA-QSP', 'set_control': lambda: f"Set {args.get('control_id', 'QNEST control')} → {args.get('value')}", 'import_circuit_files': lambda: f"Import {len(args.get('paths') or [])} circuit file(s)", 'set_qasm': lambda: f"Set QASM circuit ({args.get('name', 'circuit')})", 'open_settings': lambda: f"Open Settings → {args.get('page', 'Appearance')}", 'complete_workflow': lambda: 'Run configured experiment end-to-end', 'workflow_compile': lambda: 'Compile / distribute the configured circuit set', 'workflow_schedule': lambda: 'Generate Qoala schedule(s) for the compiled circuit set', 'workflow_run': lambda: 'Run AFA-QSP + HAMFA-QSP Monte Carlo' + (f"  ·  {args.get('monte_carlo_runs')} run(s) / point" if args.get('monte_carlo_runs') else '')}
        fn = labels.get(name)
        return fn() if fn else name

    @staticmethod
    def _assistant_set_combo(combo, query):
        values = list(combo.cget('values') or [])
        q = str(query or '').strip().lower()
        if not q:
            return False
        for i, value in enumerate(values):
            text = str(value).lower()
            if text == q or q in text or (q == 'all circuits' and text.startswith('all ')):
                combo.current(i)
                combo.event_generate('<<ComboboxSelected>>')
                return True
        return False

    def _assistant_set_scope(self, panel, query):
        try:
            panel.refresh_circuit_context()
        except Exception:
            pass
        combo = panel._scope_combo
        values = list(combo.cget('values') or [])
        ids = list(getattr(panel, '_scope_ids', []) or [])
        q = str(query or '').strip().lower()
        if not q or not values:
            return False

        def choose(index):
            if index < 0 or index >= len(values):
                return False
            combo.current(index)
            combo.event_generate('<<ComboboxSelected>>')
            return True
        if q in {'all circuits', 'all', 'all eligible circuits', 'all compiled circuits', 'all scheduled circuits'}:
            if ids and ids[0] is None:
                return choose(0)
            if len(values) == 1:
                return choose(0)
            return self._assistant_set_combo(combo, 'All circuits')
        if q in {'active circuit', 'active', 'current circuit', 'selected circuit'}:
            active_id = getattr(self, '_active_circuit_id', None)
            if active_id in ids:
                return choose(ids.index(active_id))
            if len(values) == 1:
                return choose(0)
            return False
        return self._assistant_set_combo(combo, query)

    def execute_assistant_action(self, action):
        name = str(action.get('name', ''))
        args = action.get('args') if isinstance(action.get('args'), dict) else {}
        if name == 'set_control':
            return self._assistant_set_control(args.get('control_id'), args.get('value'))
        if name == 'import_circuit_files':
            panel = self._panels['Circuit']
            paths = args.get('paths') or []
            if isinstance(paths, str):
                paths = [paths]
            if not paths:
                raise ValueError('No circuit paths were supplied.')
            if len(paths) > 1 and (not panel.is_batch_mode()):
                panel._workflow_mode.set('Batch / sweep')
                panel._on_mode_changed()
            first = None
            for i, raw_path in enumerate(paths):
                path = Path(str(raw_path)).expanduser()
                if not path.is_file():
                    raise ValueError(f'Circuit file does not exist: {path}')
                content = path.read_text(encoding='utf-8')
                rec = panel._add_circuit(name=path.stem, qasm_text=content, source='Imported', path=path, series=path.stem, replace_single=not panel.is_batch_mode() and i == 0)
                first = first or rec
            if first:
                panel.activate_record(first['id'])
            panel._switch_tab('Import')
            self.on_circuit_set_changed()
            self._select('Circuit')
            return {'label': f'Imported {len(paths)} circuit file(s)'}
        if name == 'set_qasm':
            panel = self._panels['Circuit']
            qasm = str(args.get('qasm') or '').strip()
            if not qasm:
                raise ValueError('QASM text cannot be empty.')
            cname = str(args.get('name') or 'assistant_circuit').strip() or 'assistant_circuit'
            mode = str(args.get('mode') or 'replace active').strip().lower()
            if mode == 'new' or panel.get_active_record() is None:
                if mode == 'new' and (not panel.is_batch_mode()):
                    panel._workflow_mode.set('Batch / sweep')
                    panel._on_mode_changed()
                rec = panel._add_circuit(name=cname, qasm_text=qasm + '\n', source='AI Assistant', series=cname, replace_single=not panel.is_batch_mode())
                panel.activate_record(rec['id'])
            else:
                rec = panel.get_active_record()
                rec['name'] = panel._unique_name(cname) if cname != rec.get('name') else rec.get('name')
                rec['qasm_text'] = qasm + '\n'
                stats = panel._basic_qasm_stats(rec['qasm_text'])
                for key in ('qubits', 'gates', 'depth', 'cx'):
                    if stats.get(key) is not None:
                        rec[key] = stats[key]
                panel.activate_record(rec['id'])
            panel._switch_tab('QASM Editor')
            self.on_circuit_set_changed()
            self._select('Circuit')
            return {'label': 'QASM circuit updated'}
        if name == 'open_settings':
            page = str(args.get('page') or 'Appearance')
            if page not in {'Appearance', 'Startup', 'AI Assistant'}:
                raise ValueError(f'Unknown Settings page: {page}')
            self._show_settings(page)
            return {'label': f'Open Settings → {page}'}
        if name == 'complete_workflow':
            raise RuntimeError('complete_workflow must be expanded by the assistant queue.')
        if name == 'navigate':
            page = str(args.get('page', ''))
            if page not in self._panels:
                raise ValueError(f'Unknown workspace: {page}')
            self._select(page)
            return {'label': f'Open {page}'}
        if name == 'set_circuit_workflow':
            panel = self._panels['Circuit']
            mode = str(args.get('mode', ''))
            if mode not in {'Single circuit', 'Batch / sweep'}:
                raise ValueError('Circuit mode must be Single circuit or Batch / sweep.')
            panel._workflow_mode.set(mode)
            panel._on_mode_changed()
            self._select('Circuit')
            return {'label': mode}
        if name == 'select_circuit_tab':
            tab = str(args.get('tab', ''))
            if tab not in {'Import', 'MQT Bench', 'QASM Editor'}:
                raise ValueError(f'Unknown Circuit tab: {tab}')
            panel = self._panels['Circuit']
            panel._switch_tab(tab)
            self._select('Circuit')
            return {'label': f'Circuit → {tab}'}
        if name == 'configure_mqt':
            panel = self._panels['Circuit']
            panel._switch_tab('MQT Bench')
            self._select('Circuit')
            requested = args.get('benchmarks') or []
            if isinstance(requested, str):
                requested = [requested]
            if requested:
                for v in list(panel._scal_vars.values()) + list(panel._ns_vars.values()):
                    v.set(False)
                available = {**panel._scal_vars, **panel._ns_vars}
                matched = []
                for wanted in requested:
                    w = str(wanted).lower().strip()
                    for label, var in available.items():
                        if label.lower() == w or w in label.lower() or label.lower() in w:
                            var.set(True)
                            matched.append(label)
                            break
                if not matched:
                    raise ValueError('None of the requested MQT benchmark names matched this QNEST installation.')
            if any((k in args for k in ('min_qubits', 'max_qubits', 'step'))):
                panel._workflow_mode.set('Batch / sweep')
                panel._on_mode_changed()
                if 'min_qubits' in args:
                    panel._q_min.set(max(1, int(args['min_qubits'])))
                if 'max_qubits' in args:
                    panel._q_max.set(max(1, int(args['max_qubits'])))
                if 'step' in args:
                    panel._q_step.set(max(1, int(args['step'])))
            elif 'qubits' in args:
                panel._workflow_mode.set('Single circuit')
                panel._on_mode_changed()
                panel._q_count.set(max(1, int(args['qubits'])))
            panel._mark_mqt_validation_stale()
            panel._refresh_mqt_generation_plan()
            return {'label': 'MQT Bench configured'}
        if name == 'generate_mqt':
            panel = self._panels['Circuit']
            if str(panel._mqt_generate_btn.cget('state')) == 'disabled':
                raise RuntimeError('MQT generation is already running.')
            panel._switch_tab('MQT Bench')
            self._select('Circuit')
            panel._generate_mqt()
            return {'label': 'Generate MQT', 'async': 'mqt'}
        if name == 'configure_network':
            panel = self._panels['Network']
            if 'servers' in args:
                panel._n_srv.set(max(2, int(args['servers'])))
            if 'qubits_per_qpu' in args:
                panel._qppq.set(max(1, int(args['qubits_per_qpu'])))
            if 'topology' in args:
                topo = str(args['topology'])
                aliases = {'fully connected': 'All-to-all', 'complete': 'All-to-all', 'line': 'Linear chain', 'linear': 'Linear chain'}
                topo = aliases.get(topo.lower(), topo)
                if topo not in {'All-to-all', 'Ring', 'Linear chain', 'Star', 'Custom'}:
                    raise ValueError(f'Unsupported topology: {topo}')
                panel._topo.set(topo)
            if 'interconnect' in args:
                raw = str(args['interconnect']).strip()
                norm = ' '.join(raw.lower().replace('_', ' ').replace('-', ' ').split())
                if 'direct' in norm:
                    value = 'Direct QPU links'
                elif 'switch' in norm:
                    value = 'Shared switch'
                else:
                    value = raw
                if value not in {'Direct QPU links', 'Shared switch'}:
                    raise ValueError('Interconnect must be Direct QPU links or Shared switch.')
                panel._interconnect.set(value)
            if 'switch_mode' in args:
                raw = str(args['switch_mode']).strip()
                norm = ' '.join(raw.lower().replace('_', ' ').replace('-', ' ').split())
                if 'memory' in norm:
                    value = 'Memory-assisted'
                elif 'photonic' in norm:
                    value = 'All-photonic'
                else:
                    value = raw
                if value not in {'All-photonic', 'Memory-assisted'}:
                    raise ValueError('Switch mode must be All-photonic or Memory-assisted.')
                if panel._topo.get() == 'All-to-all':
                    panel._interconnect.set('Shared switch')
                panel._switch_mode.set(value)
            panel._topology_changed()
            panel._schedule_recalc()
            self._select('Network')
            return {'label': 'Network configured'}
        if name == 'sync_network_designer':
            panel = self._panels['Network']
            panel._sync_to_designer()
            self._select('Network')
            return {'label': 'Network Designer synchronized'}
        if name == 'configure_compile':
            panel = self._panels['Compile']
            if 'method' in args:
                method = str(args['method'])
                if method not in panel.DISTRIBUTION_METHODS:
                    raise ValueError(f'Unsupported distribution method: {method}')
                panel._method.set(method)
            if 'seed' in args:
                panel._seed.set(str(int(args['seed'])))
            if 'scope' in args:
                if not self._assistant_set_scope(panel, args['scope']):
                    raise ValueError(f"Compile scope is unavailable: {args['scope']}")
            self._select('Compile')
            return {'label': 'Compile configured'}
        if name == 'compile':
            panel = self._panels['Compile']
            if panel._busy:
                raise RuntimeError('Compile is already running.')
            self._select('Compile')
            panel._compile()
            return {'label': 'Compile / distribute', 'async': 'compile'}
        if name == 'configure_schedule':
            panel = self._panels['Schedule']
            if 'strategy' in args:
                strategy = str(args['strategy'])
                if strategy not in {'QOALA', 'FCFS', 'EPR_PRIORITY', 'RANDOM'}:
                    raise ValueError(f'Unsupported schedule strategy: {strategy}')
                panel._strategy.set(strategy)
            mapping = {'single_qubit_us': 'single_qubit_time_ns', 'two_qubit_us': 'two_qubit_time_ns', 'epr_ejpp_start_us': 'starting_process_time_ns', 'ejpp_ending_us': 'ending_process_time_ns'}
            for arg_key, var_key in mapping.items():
                if arg_key in args:
                    value = float(args[arg_key])
                    if value < 0:
                        raise ValueError(f'{arg_key} cannot be negative.')
                    panel._timings[var_key].set(str(value))
            if 'scope' in args:
                if not self._assistant_set_scope(panel, args['scope']):
                    raise ValueError(f"Schedule scope is unavailable: {args['scope']}")
            self._select('Schedule')
            return {'label': 'Schedule configured'}
        if name == 'schedule':
            panel = self._panels['Schedule']
            if panel._busy:
                raise RuntimeError('Schedule is already running.')
            self._select('Schedule')
            panel._generate()
            return {'label': 'Qoala schedule', 'async': 'schedule'}
        if name == 'configure_run':
            panel = self._panels['Run']
            network = self._panels.get('Network')
            if network is None or not network._is_switched():
                panel.refresh_run_mode()
                return {'label': 'Monte Carlo skipped — shared switch not selected'}
            if 'fidelity_threshold' in args:
                v = float(args['fidelity_threshold'])
                if not 0 <= v <= 1:
                    raise ValueError('Fidelity threshold must be in [0,1].')
                panel._vars['F_T'].set(str(v))
            if 'alpha' in args:
                v = float(args['alpha'])
                if not 0 <= v <= 1:
                    raise ValueError('alpha must be in [0,1].')
                panel._vars['alpha'].set(str(v))
            if 'seed' in args:
                panel._vars['seed'].set(str(int(args['seed'])))
            if 'hedge' in args:
                value = str(args['hedge'])
                if value not in {'race', 'sequential', 'off'}:
                    raise ValueError(f'Unsupported HAMFA hedge: {value}')
                panel._hedge.set(value)
            if 'monte_carlo_runs' in args:
                panel._mc_runs.set(max(1, int(args['monte_carlo_runs'])))
            if 'deadline_equality_blocked' in args:
                panel._deadline.set(bool(args['deadline_equality_blocked']))
            if 'scope' in args:
                if not self._assistant_set_scope(panel, args['scope']):
                    raise ValueError(f"Run scope is unavailable: {args['scope']}")
            self._select('Run')
            return {'label': 'Run configured'}
        if name == 'run_protocols':
            panel = self._panels['Run']
            network = self._panels.get('Network')
            if network is None or not network._is_switched():
                panel.refresh_run_mode()
                self._select('Run')
                return {'label': 'Monte Carlo skipped — shared switch not selected'}
            if panel._running:
                raise RuntimeError('Run is already in progress.')
            self._select('Run')
            panel._run()
            return {'label': 'AFA + HAMFA', 'async': 'run'}
        raise ValueError(f'Unsupported assistant action: {name}')

    def assistant_operation_busy(self, key):
        try:
            if key == 'mqt':
                return str(self._panels['Circuit']._mqt_generate_btn.cget('state')) == 'disabled'
            if key == 'compile':
                return bool(self._panels['Compile']._busy)
            if key == 'schedule':
                return bool(self._panels['Schedule']._busy)
            if key == 'run':
                return bool(self._panels['Run']._running)
        except Exception:
            return False
        return False

    def _show_settings(self, page=None):
        dlg = SettingsDialog(self)
        if page and page in getattr(dlg, '_pages', {}):
            dlg._show_page(page)

    def _show_about(self):
        AboutDialog(self)

    def _show_bug_report(self):
        BugReportDialog(self)

    def _open_documentation(self):
        candidates = [PROJECT_ROOT / 'docs' / 'QNEST_User_Guide.html', PROJECT_ROOT / 'README.md']
        for path in candidates:
            if path.exists():
                _open_local_path(path)
                return
        messagebox.showwarning('Documentation', 'QNEST documentation was not found in this installation.')

    def apply_ui_preferences(self, prefs):
        old = dict(C)
        self.ui_preferences.update(prefs)
        _save_ui_preferences(self.ui_preferences)
        _activate_theme(self.ui_preferences['theme'])
        FM.set_user_scale(self.ui_preferences['scale'])
        _install_interaction_defaults(self)
        self._apply_window_scale_constraints()
        self.configure(bg=C['bg'])
        self._recolor_tree(self, old, dict(C))
        self._configure_ttk_styles()
        self._polish_interactive_tree(self)
        self._schedule_scale_stabilization()
        if self._active:
            active = self._active
            self._active = ''
            self._select(active)
        if hasattr(self, '_assistant_dock'):
            try:
                self._assistant_dock.refresh_model_badge()
                self._paint_assistant_toolbar_button(False)
            except Exception:
                pass

    def _recolor_tree(self, widget, old, new):
        old_to_key = {}
        for key, value in old.items():
            old_to_key.setdefault(str(value).lower(), key)
        options = ('background', 'foreground', 'activebackground', 'activeforeground', 'insertbackground', 'highlightbackground', 'highlightcolor', 'selectcolor')
        for opt in options:
            try:
                value = str(widget.cget(opt)).lower()
                key = old_to_key.get(value)
                if key and key in new:
                    widget.configure(**{opt: new[key]})
            except Exception:
                pass
        if isinstance(widget, tk.Canvas):
            for item in widget.find_all():
                for opt in ('fill', 'outline'):
                    try:
                        value = str(widget.itemcget(item, opt)).lower()
                        key = old_to_key.get(value)
                        if key and key in new:
                            widget.itemconfigure(item, **{opt: new[key]})
                    except Exception:
                        pass
        for child in widget.winfo_children():
            self._recolor_tree(child, old, new)

def _ensure_qnest_runtime():
    if getattr(sys, 'frozen', False):
        return
    if os.environ.get('QNEST_ALLOW_OTHER_PYTHON') == '1':
        return
    exe = Path(sys.executable).expanduser().resolve()
    exe_text = str(exe).replace('\\', '/')
    if os.environ.get('CONDA_DEFAULT_ENV') == 'qoala' or '/envs/qoala/' in exe_text:
        return
    candidates = []
    override = os.environ.get('QNEST_PYTHON', '').strip()
    if override:
        candidates.append(Path(override).expanduser())
    home = Path.home()
    candidates.extend([home / 'miniforge3' / 'envs' / 'qoala' / 'bin' / 'python', home / 'mambaforge' / 'envs' / 'qoala' / 'bin' / 'python', home / 'miniconda3' / 'envs' / 'qoala' / 'bin' / 'python', home / 'anaconda3' / 'envs' / 'qoala' / 'bin' / 'python'])
    for candidate in candidates:
        try:
            candidate = candidate.resolve()
            if candidate.is_file() and os.access(candidate, os.X_OK) and (candidate != exe):
                env = os.environ.copy()
                env['QNEST_RUNTIME_BOOTSTRAPPED'] = '1'
                print(f'QNEST: relaunching with scientific runtime: {candidate}', flush=True)
                os.execve(str(candidate), [str(candidate), str(Path(__file__).resolve()), *sys.argv[1:]], env)
        except Exception:
            continue
if __name__ == '__main__':
    _ensure_qnest_runtime()
    app = MainWindow()
    app.mainloop()