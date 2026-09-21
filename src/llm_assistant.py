import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
ACTION_CATALOG = [{'name': 'navigate', 'description': 'Open one QNEST workspace page.', 'args': {'page': 'Circuit | Network | Compile | Schedule | Run'}}, {'name': 'set_circuit_workflow', 'description': 'Choose single-circuit or batch/sweep workflow.', 'args': {'mode': 'Single circuit | Batch / sweep'}}, {'name': 'select_circuit_tab', 'description': 'Open a Circuit sub-tab.', 'args': {'tab': 'Import | MQT Bench | QASM Editor'}}, {'name': 'configure_mqt', 'description': 'Configure MQT Bench selection and scalable circuit size(s).', 'args': {'benchmarks': ['exact benchmark labels from QNEST when known'], 'qubits': 'integer for single mode', 'min_qubits': 'integer for batch mode', 'max_qubits': 'integer for batch mode', 'step': 'positive integer for batch mode'}}, {'name': 'generate_mqt', 'description': 'Generate the currently configured MQT Bench circuits.', 'args': {}}, {'name': 'configure_network', 'description': 'Configure QPU/network architecture. For an All-to-all network, when the researcher does not explicitly choose an interconnect, the QNEST Assistant default is Shared switch with Memory-assisted mode so the optional Monte Carlo Run stage remains available. Explicit Direct QPU links or All-photonic requests must be preserved.', 'args': {'servers': 'integer >= 2', 'qubits_per_qpu': 'positive integer', 'topology': 'All-to-all | Linear chain | Ring | Star | Custom', 'interconnect': 'Direct QPU links | Shared switch', 'switch_mode': 'All-photonic | Memory-assisted (default for an unspecified shared-switch mode)'}}, {'name': 'sync_network_designer', 'description': 'Synchronize the Table topology to the visual Designer.', 'args': {}}, {'name': 'configure_compile', 'description': 'Configure DQC distribution settings.', 'args': {'method': 'distribution method shown by QNEST', 'seed': 'integer', 'scope': 'Active circuit | All circuits'}}, {'name': 'compile', 'description': 'Run Prepare + Distribute for the chosen scope.', 'args': {}}, {'name': 'configure_schedule', 'description': 'Configure Qoala scheduling. All times are user-facing microseconds.', 'args': {'single_qubit_us': 'number', 'two_qubit_us': 'number', 'epr_ejpp_start_us': 'number', 'ejpp_ending_us': 'number', 'strategy': 'QOALA | FCFS | EPR_PRIORITY | RANDOM', 'scope': 'Active circuit | All circuits'}}, {'name': 'schedule', 'description': 'Generate Qoala schedule(s) for the chosen scope.', 'args': {}}, {'name': 'configure_run', 'description': 'Configure AFA-QSP / HAMFA-QSP Monte Carlo settings. This stage is available only when Network uses All-to-all → Shared switch.', 'args': {'fidelity_threshold': 'number in [0,1]', 'alpha': 'number in [0,1]', 'seed': 'integer', 'hedge': 'race or supported hedge mode', 'monte_carlo_runs': 'positive integer', 'deadline_equality_blocked': 'boolean', 'scope': 'Active circuit | All circuits'}}, {'name': 'run_protocols', 'description': 'Run AFA-QSP + HAMFA-QSP for the chosen scope. Only valid when Network uses All-to-all → Shared switch; switch-free workflows stop after Schedule.', 'args': {}}, {'name': 'set_control', 'description': 'Set any exposed QNEST control independently. Use an exact control_id and allowed value from CURRENT QNEST CONTEXT.controls. This includes Appearance/Startup/AI settings, Circuit, Network physical parameters and link distances, Compile, Schedule/Gantt, Run, and live assistant visibility.', 'args': {'control_id': 'exact id from CURRENT QNEST CONTEXT.controls', 'value': 'validated value'}}, {'name': 'import_circuit_files', 'description': 'Import one or more local QASM/Python circuit files by explicit path. The path must already exist on this computer.', 'args': {'paths': ['/path/to/circuit.qasm']}}, {'name': 'set_qasm', 'description': 'Create or replace a QASM circuit directly from user-provided/assistant-authored QASM. QNEST validates downstream stages normally.', 'args': {'name': 'circuit name', 'qasm': 'OPENQASM text', 'mode': 'replace active | new'}}, {'name': 'open_settings', 'description': 'Open the QNEST Settings Center on a requested page.', 'args': {'page': 'Appearance | Startup | AI Assistant'}}, {'name': 'complete_workflow', 'description': 'Continue the current configured experiment through all remaining valid stages: generate selected MQT circuits if needed, Compile/Distribute and Schedule; run AFA-QSP + HAMFA-QSP Monte Carlo only when Network uses All-to-all → Shared switch. Switch-free workflows stop after Schedule. Batch mode automatically uses all circuits.', 'args': {'rebuild': 'boolean, default true'}}]
_EXECUTION_OPT_OUT_PHRASES = ('plan only', 'planning only', 'do not run', "don't run", 'dont run', 'without running', 'do not execute', "don't execute", 'dont execute', 'just explain', 'explain only', 'only explain', 'just configure', 'configure only', 'only configure', 'do not compile', "don't compile", 'dont compile', 'do not schedule', "don't schedule", 'dont schedule')

def _extract_requested_mc_runs(user_text):
    text = (user_text or '').lower()
    patterns = ('(?:monte\\s*carlo|\\bmc\\b)[^0-9]{0,24}(\\d{1,5})\\s*(?:runs?|repetitions?|replicas?)?', '(\\d{1,5})\\s*(?:monte\\s*carlo|\\bmc\\b)\\s*(?:runs?|repetitions?|replicas?)?', '(\\d{1,5})\\s*(?:runs?|repetitions?|replicas?)\\s*(?:per\\s*point\\s*)?(?:for\\s*)?(?:monte\\s*carlo|\\bmc\\b)')
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            try:
                return max(1, min(10000, int(m.group(1))))
            except Exception:
                pass
    return None

def _execution_opted_out(user_text):
    text = ' '.join((user_text or '').lower().split())
    return any((phrase in text for phrase in _EXECUTION_OPT_OUT_PHRASES))

def _execution_intent(user_text, actions):
    text = ' '.join((user_text or '').lower().split())
    if _execution_opted_out(user_text):
        return False
    explicit = ('run the experiment', 'run experiment', 'execute the experiment', 'simulate', 'end-to-end', 'end to end', 'full workflow', 'through run', 'until run', 'to the end', 'monte carlo', 'compile and schedule', 'schedule and run', 'compile, schedule')
    if any((phrase in text for phrase in explicit)):
        return True
    stage_groups = set()
    for action in actions:
        name = str(action.get('name', ''))
        if name in {'set_circuit_workflow', 'select_circuit_tab', 'configure_mqt', 'generate_mqt', 'import_circuit_files', 'set_qasm'}:
            stage_groups.add('circuit')
        elif name in {'configure_network', 'sync_network_designer'}:
            stage_groups.add('network')
        elif name in {'configure_compile', 'compile'}:
            stage_groups.add('compile')
        elif name in {'configure_schedule', 'schedule'}:
            stage_groups.add('schedule')
        elif name in {'configure_run', 'run_protocols'}:
            stage_groups.add('run')
    if 'experiment' in text and stage_groups:
        return True
    return len(stage_groups) >= 2 and ('circuit' in stage_groups or 'network' in stage_groups)

def _network_user_preferences(user_text):
    text = ' '.join((user_text or '').lower().replace('_', ' ').split())
    return {'direct': any((p in text for p in ('direct qpu', 'direct link', 'direct links', 'without a switch', 'no switch', 'switch-free', 'switch free'))), 'shared': any((p in text for p in ('shared switch', 'use a switch', 'with a switch'))), 'memory': any((p in text for p in ('memory-assisted', 'memory assisted', 'memory switch'))), 'all_photonic': any((p in text for p in ('all-photonic', 'all photonic', 'photonic switch')))}

def _normalize_network_value(value, kind):
    if value is None:
        return value
    raw = str(value).strip()
    norm = ' '.join(raw.lower().replace('_', ' ').replace('-', ' ').split())
    if kind == 'topology':
        if norm in {'all to all', 'alltoall', 'fully connected', 'full mesh'}:
            return 'All-to-all'
        if norm in {'linear', 'line', 'linear chain', 'chain'}:
            return 'Linear chain'
        if norm == 'ring':
            return 'Ring'
        if norm == 'star':
            return 'Star'
        if norm == 'custom':
            return 'Custom'
    elif kind == 'interconnect':
        if 'direct' in norm:
            return 'Direct QPU links'
        if 'switch' in norm:
            return 'Shared switch'
    elif kind == 'switch_mode':
        if 'memory' in norm:
            return 'Memory-assisted'
        if 'photonic' in norm:
            return 'All-photonic'
    return raw

def _normalize_network_actions(user_text, context, actions):
    prefs = _network_user_preferences(user_text)
    current = context.get('network') or {}
    for action in actions:
        if str(action.get('name')) != 'configure_network':
            continue
        args = action.setdefault('args', {})
        if 'topology' in args:
            args['topology'] = _normalize_network_value(args.get('topology'), 'topology')
        if 'interconnect' in args:
            args['interconnect'] = _normalize_network_value(args.get('interconnect'), 'interconnect')
        if 'switch_mode' in args:
            args['switch_mode'] = _normalize_network_value(args.get('switch_mode'), 'switch_mode')
        effective_topology = str(args.get('topology') or current.get('topology') or 'All-to-all')
        if effective_topology != 'All-to-all':
            continue
        if prefs['direct']:
            args['interconnect'] = 'Direct QPU links'
            args.pop('switch_mode', None)
            continue
        if prefs['shared'] or prefs['memory'] or prefs['all_photonic'] or ('switch_mode' in args) or (not prefs['direct']):
            args['interconnect'] = 'Shared switch'
            if prefs['all_photonic']:
                args['switch_mode'] = 'All-photonic'
            elif prefs['memory']:
                args['switch_mode'] = 'Memory-assisted'
            else:
                args['switch_mode'] = 'Memory-assisted'
    return actions

def _planned_run_available(context, actions):
    network = dict(context.get('network') or {})
    topology = network.get('topology')
    interconnect = network.get('interconnect')
    switch_mode = network.get('switch_mode')
    for action in actions:
        name = str(action.get('name', ''))
        args = action.get('args') or {}
        if name == 'configure_network':
            topology = args.get('topology', topology)
            interconnect = args.get('interconnect', interconnect)
            switch_mode = args.get('switch_mode', switch_mode)
        elif name == 'set_control':
            cid = str(args.get('control_id', ''))
            if cid == 'network.topology':
                topology = args.get('value')
            elif cid == 'network.interconnect':
                interconnect = args.get('value')
            elif cid == 'network.switch_mode':
                switch_mode = args.get('value')
    return str(topology) == 'All-to-all' and str(interconnect) == 'Shared switch' and (str(switch_mode) in {'All-photonic', 'Memory-assisted'})

def _enforce_end_to_end_plan(user_text, context, actions):
    actions = [dict(a) for a in actions]
    actions = _normalize_network_actions(user_text, context, actions)
    if _execution_opted_out(user_text):
        blocked = {'complete_workflow', 'compile', 'schedule', 'run_protocols'}
        return ([a for a in actions if str(a.get('name')) not in blocked], False)
    if not _execution_intent(user_text, actions):
        return (actions, False)
    requested_mc = _extract_requested_mc_runs(user_text)
    has_complete = any((str(a.get('name')) == 'complete_workflow' for a in actions))
    if requested_mc is not None:
        configured = False
        for action in actions:
            if str(action.get('name')) == 'configure_run':
                args = action.setdefault('args', {})
                args['monte_carlo_runs'] = requested_mc
                configured = True
                break
        if not configured:
            insert_at = next((i for i, a in enumerate(actions) if str(a.get('name')) == 'complete_workflow'), len(actions))
            actions.insert(insert_at, {'name': 'configure_run', 'args': {'monte_carlo_runs': requested_mc}})
    if has_complete:
        return (actions, False)
    downstream_ops = {'compile', 'schedule', 'run_protocols'}
    normalized = [a for a in actions if str(a.get('name')) not in downstream_ops]
    normalized.append({'name': 'complete_workflow', 'args': {'rebuild': True}})
    return (normalized, True)
PLAN_SCHEMA = {'type': 'object', 'properties': {'message': {'type': 'string'}, 'actions': {'type': 'array', 'items': {'type': 'object', 'properties': {'name': {'type': 'string'}, 'args': {'type': 'object'}}, 'required': ['name', 'args']}}}, 'required': ['message', 'actions']}
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_KNOWLEDGE_PATH = _PROJECT_ROOT / 'docs' / 'QNEST_Knowledge_Base.md'

def _load_qnest_knowledge():
    try:
        text = _KNOWLEDGE_PATH.read_text(encoding='utf-8').strip()
    except Exception:
        text = ''
    if text:
        return text[:22000]
    return 'QNEST is the Quantum Network End-to-End Simulation Toolkit. Featured senior developers: Seyed Navid Elyasi (Chalmers University of Technology) and Sima Bahrani (University of Bristol). Co-authors: Rui Wang, Dimitra Simeonidou, Paolo Monti, Rui Lin. QNEST is an open-source Chalmers × University of Bristol collaboration.'

def _canonical_project_fact_reply(user_text):
    q = ' '.join((user_text or '').lower().split())
    if not q:
        return None
    action_words = ('configure', 'create', 'generate', 'compile', 'schedule', 'run ', 'execute', 'set ', 'change', 'apply', 'import', 'build a ')
    if any((w in q for w in action_words)):
        return None
    identity_phrases = ('who made', 'who has made', 'who built', 'who developed', 'who created', 'who are the developers', 'who are developers', 'who is the developer', 'who are the authors', 'who are authors', 'author of qnest', 'qnest team', 'development team', 'co-author', 'coauthor')
    if any((x in q for x in identity_phrases)):
        return "QNEST's featured Senior Developers are Seyed Navid Elyasi (Chalmers University of Technology) and Sima Bahrani (University of Bristol). The QNEST paper co-authors are Rui Wang, Dimitra Simeonidou, Paolo Monti, and Rui Lin. QNEST is presented as an open-source collaboration between Chalmers University of Technology and the University of Bristol."
    funding_phrases = ('funded', 'funding', 'funders', 'who funds', 'fund ', 'sponsor', 'supported by', 'who supports', 'research council', 'epsrc', 'iqn hub', 'integrated quantum networks hub')
    if any((x in q for x in funding_phrases)):
        return "QNEST's project acknowledgement states: Supported by the Swedish Research Council (VR) and the UK EPSRC Integrated Quantum Networks Hub (EP/Z533208/1). Project/support marks also include WACQT, the University of Bristol, Smart Internet Lab, and the Integrated Quantum Networks Hub."
    about_phrases = ('what is qnest', 'what does qnest stand for', 'describe qnest')
    if any((x in q for x in about_phrases)):
        return 'QNEST stands for Quantum Network End-to-End Simulation Toolkit. It is a GUI-driven research toolkit for end-to-end optical quantum-network and quantum-data-center experimentation, covering Circuit → Network → Compile/Distribute → Schedule → Run/Analyse.'
    return None

def _json_from_text(text):
    raw = (text or '').strip()
    if not raw:
        return {'message': 'The model returned an empty response.', 'actions': []}
    candidates = [raw]
    fenced = re.findall('```(?:json)?\\s*(\\{.*?\\})\\s*```', raw, flags=re.S | re.I)
    candidates = fenced + candidates
    start, end = (raw.find('{'), raw.rfind('}'))
    if 0 <= start < end:
        candidates.append(raw[start:end + 1])
    for item in candidates:
        try:
            obj = json.loads(item)
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    return {'message': raw, 'actions': []}

class AssistantReply:

    def __init__(self, message, actions=None, raw='', model=''):
        self.message = message
        self.actions = [] if actions is None else actions
        self.raw = raw
        self.model = model

    def __repr__(self):
        return f'AssistantReply(message={self.message!r}, actions={self.actions!r}, raw={self.raw!r}, model={self.model!r})'

    def __eq__(self, other):
        if other.__class__ is self.__class__:
            return (self.message, self.actions, self.raw, self.model) == (other.message, other.actions, other.raw, other.model)
        return NotImplemented

class LLMConnectionError(RuntimeError):
    pass

class QNESTAssistantClient:

    def __init__(self, *, provider='Ollama (local)', endpoint='http://127.0.0.1:11434', model='qwen3:8b', temperature=0.2, timeout=180.0):
        self.provider = provider
        self.endpoint = endpoint.rstrip('/')
        self.model = model.strip() or 'qwen3:8b'
        self.temperature = float(temperature)
        self.timeout = float(timeout)

    @staticmethod
    def _is_local_url(url):
        try:
            host = (urllib.parse.urlparse(url).hostname or '').lower()
        except Exception:
            return False
        return host in {'127.0.0.1', 'localhost', '::1'}

    @classmethod
    def _urlopen(cls, req, *, timeout):
        url = req.full_url if hasattr(req, 'full_url') else str(req)
        if cls._is_local_url(url):
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            return opener.open(req, timeout=timeout)
        return urllib.request.urlopen(req, timeout=timeout)

    @staticmethod
    def _find_ollama_executable():
        candidates = [shutil.which('ollama'), '/opt/homebrew/bin/ollama', '/usr/local/bin/ollama', str(Path.home() / '.local' / 'bin' / 'ollama')]
        for item in candidates:
            if item and os.path.isfile(item) and os.access(item, os.X_OK):
                return item
        return None

    def _ollama_tags(self, timeout=2.0):
        req = urllib.request.Request(self.endpoint + '/api/tags', method='GET')
        with self._urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8', errors='replace'))

    def ensure_ollama_running(self, *, wait_seconds=10.0):
        if not self.provider.startswith('Ollama'):
            return (True, 'Not an Ollama provider')
        if not self._is_local_url(self.endpoint):
            return (False, 'Automatic start is only available for localhost Ollama endpoints.')
        try:
            self._ollama_tags(timeout=1.5)
            return (True, 'Ollama is already running')
        except Exception:
            pass
        exe = self._find_ollama_executable()
        if not exe:
            return (False, 'Ollama is installed but its CLI could not be found on PATH or in /opt/homebrew/bin.')
        log_path = os.path.join(tempfile.gettempdir(), 'qnest_ollama.log')
        try:
            log = open(log_path, 'ab', buffering=0)
            subprocess.Popen([exe, 'serve'], stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True)
        except Exception as exc:
            return (False, f'Could not start Ollama: {exc}')
        deadline = time.time() + max(2.0, float(wait_seconds))
        last_exc = None
        while time.time() < deadline:
            try:
                self._ollama_tags(timeout=1.0)
                return (True, f'Started local Ollama ({exe})')
            except Exception as exc:
                last_exc = exc
                time.sleep(0.25)
        return (False, f'Ollama did not become ready at {self.endpoint}. Log: {log_path}. Last error: {last_exc}')

    def _request_json(self, url, payload, headers=None):
        body = json.dumps(payload).encode('utf-8')
        hdr = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        if headers:
            hdr.update(headers)
        req = urllib.request.Request(url, data=body, headers=hdr, method='POST')
        try:
            with self._urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode('utf-8', errors='replace'))
        except urllib.error.HTTPError as exc:
            detail = ''
            try:
                detail = exc.read().decode('utf-8', errors='replace')
            except Exception:
                pass
            raise LLMConnectionError(f'HTTP {exc.code}: {detail or exc.reason}') from exc
        except urllib.error.URLError as exc:
            raise LLMConnectionError(str(getattr(exc, 'reason', exc))) from exc
        except TimeoutError as exc:
            raise LLMConnectionError('The model server timed out.') from exc

    def test_connection(self):
        if self.provider.startswith('Ollama'):
            started = ''
            ok, detail = self.ensure_ollama_running(wait_seconds=10.0)
            if not ok:
                raise LLMConnectionError(detail)
            if detail.startswith('Started'):
                started = detail + ' • '
            try:
                data = self._ollama_tags(timeout=5.0)
                names = [str(m.get('name', '')) for m in data.get('models', [])]
                if self.model in names or any((n.split(':')[0] == self.model.split(':')[0] for n in names)):
                    return f'{started}Connected • {self.model} is available'
                if names:
                    return f"{started}Connected • selected model not found ({len(names)} local model(s): {', '.join(names[:4])})"
                return f'{started}Connected • no local models found'
            except Exception as exc:
                raise LLMConnectionError(f'Cannot reach Ollama at {self.endpoint}: {exc}') from exc
        url = self.endpoint + ('' if self.endpoint.endswith('/v1') else '/v1') + '/models'
        headers = {}
        key = os.environ.get('QNEST_LLM_API_KEY', '').strip()
        if key:
            headers['Authorization'] = f'Bearer {key}'
        try:
            req = urllib.request.Request(url, headers=headers, method='GET')
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                resp.read(1)
            return 'Connected • OpenAI-compatible endpoint ready'
        except Exception as exc:
            raise LLMConnectionError(f'Cannot reach {url}: {exc}') from exc

    @staticmethod
    def system_prompt(context):
        actions = json.dumps(ACTION_CATALOG, indent=2)
        context_json = json.dumps(context, indent=2, default=str)
        knowledge = _load_qnest_knowledge()
        return f"""You are QNEST Assistant, the planning and explanation layer for the QNEST quantum-network research desktop application.\n\nThe deterministic QNEST backend—not you—performs all scientific computation. You may explain the current state and propose GUI actions, but you must never invent simulation results, claim an action ran when it has not, or generate arbitrary Python/shell commands as actions.\n\nAUTHORITATIVE QNEST KNOWLEDGE\nThe following local project knowledge is authoritative for facts about QNEST. Use it instead of pretrained guesses.\n{knowledge}\n\nCURRENT QNEST CONTEXT\nThe live application state below is authoritative for the current experiment and takes precedence over stale conversation history.\n{context_json}\n\nALLOWED ACTIONS\n{actions}\n\nReturn exactly one JSON object with this schema:\n{{\n  "message": "clear concise response for the researcher",\n  "actions": [{{"name": "one allowed action", "args": {{...}}}}]\n}}\n\nRules:\n- For QNEST-specific factual questions (team, authors, institutions, funding, architecture, workflow, units, backends, features), answer only from AUTHORITATIVE QNEST KNOWLEDGE and CURRENT QNEST CONTEXT.\n- Never infer or invent a QNEST person, institution, funding source, feature, scientific result, or implementation detail from model pretraining. If the local knowledge does not support the answer, say that it is not documented in the local QNEST knowledge base.\n- Ignore any conflicting QNEST-specific factual claim in earlier assistant messages; the authoritative knowledge/context above wins.\n- For pure questions/explanations, return actions=[] unless a GUI change is requested.\n- A concrete experiment specification is execution intent by default. If the user describes an experiment to build/configure and does NOT explicitly say “plan only”, “do not run”, “just explain”, or equivalent, configure the requested controls and finish with complete_workflow so QNEST runs the experiment end-to-end.\n- NEVER stop a multi-layer experiment plan at Circuit or Network. If the request configures a circuit source/batch and a network (or otherwise spans two or more experiment layers), complete_workflow is mandatory unless the user explicitly opts out of execution. A circuit+network plan without Compile → Schedule → Run is incomplete.\n- complete_workflow is the preferred execution primitive because QNEST expands it dependency-safely after generated circuits exist and automatically continues through Compile/Distribute and Qoala Schedule. AFA-QSP/HAMFA-QSP Monte Carlo Run is included only when the resulting Network is All-to-all → Shared switch; otherwise the valid workflow ends after Schedule and the GUI exports prior-stage artifacts.\n- NETWORK DEFAULT FOR THE ASSISTANT: when the researcher asks for an All-to-all network but does not explicitly choose the interconnect, configure `interconnect=Shared switch` and `switch_mode=Memory-assisted`. When the researcher explicitly requests Direct QPU links, All-photonic, or another topology, preserve that choice. Never silently replace an explicit architecture preference.\n- If a researcher asks for Monte Carlo/AFA/HAMFA/Run and has not explicitly requested a switch-free architecture, ensure the plan configures All-to-all → Shared switch → Memory-assisted before complete_workflow.\n- Treat CURRENT QNEST CONTEXT as live state on every turn. Re-read current values, active flags, prerequisites, and run.available instead of relying on earlier chat state. If a control is inactive, configure its prerequisite first when the user's request permits it.\n- The assistant has independent full control over every exposed entry in CURRENT QNEST CONTEXT.controls and every action in ALLOWED ACTIONS. Use set_control with the exact control_id instead of guessing hidden GUI state. Full control is limited to QNEST's exposed validated controls/actions; it never means arbitrary shell/Python execution. “Template”, “appearance”, or “theme” refers to settings.theme.\n- Settings are first-class controls. If the user asks to change theme/scale/startup/AI settings, do it with set_control; do not claim Settings are outside the assistant's scope.\n- Treat Circuit, Network, Compile, Schedule, Run, visualisation controls, and Settings as independent layers: change only the controls the user requested and preserve all other current values.\n- For requests to configure or run QNEST, propose the minimum ordered action list needed. Use complete_workflow for full experiment execution rather than stopping after configuration.\n- Prefer preserving values the user did not mention. Use current/default values already present in CURRENT QNEST CONTEXT rather than inventing replacements.\n- Never guess a benchmark name if it is not in CURRENT QNEST CONTEXT; explain the ambiguity instead.\n- Never bypass QNEST validation. MQT compatibility, network constraints and downstream prerequisites are validated by QNEST.\n- CURRENT QNEST CONTEXT.scientific_results is the authoritative read-only scientific result surface. Use it whenever the researcher asks about results, interpretation, performance, blocked requests, fidelity, latency, Compile/Distribution, Schedule/Qoala, AFA-QSP, HAMFA-QSP, Monte Carlo behaviour, or comparisons across layers/circuits.\n- The Run layer has a CLEAN RESEARCHER-FACING RESULT TABLE CONTRACT. `scientific_results.layers.run_result_table_view` declares the selected display unit and visible result schema, and each detailed circuit result may contain `run.result_tables`. These AFA-QSP/HAMFA-QSP rows are the primary per-request Monte Carlo evidence shown to the researcher. They intentionally exclude simulator-internal HAMFA diagnostics such as memory ages/lifetimes, Δτ thresholds, expected AP timing, aborted-trial diagnostics, effective-pair age, and other implementation-only fields. Do not surface those hidden diagnostics as normal results.\n- If the researcher asks for the result table, a result row, or Monte Carlo output, reproduce/use ONLY the corresponding `afa_qsp_results` or `hamfa_qsp_results` data. Respect `display_units` in the live Run view. Do not add hidden/internal columns or synthesize extra factors. Unit conversion is allowed only when the UI/user has selected or requested it.\n- For result interpretation, explain the evidence layer-by-layer (Circuit → Network → Compile/Distribution → Schedule/Qoala → Run) and connect downstream behaviour only when the supplied values support that connection. Distinguish measured/current values from your interpretation.\n- When scientific_results contains table digests for non-Run layers, use their row counts, numeric_statistics, categorical_counts, sample_rows and notable_rows as evidence. Do not claim to have inspected rows that are not present in the context.\n- Run summaries/comparison data are secondary aggregate metadata. Use them only when the researcher asks for an aggregate/statistical comparison; never substitute them for the clean per-request result tables.\n- Backend result fields ending in _ns or labelled [ns] are nanoseconds. The Run exact-table tabs have a user-selectable ns/µs presentation mode while raw saved notebook tables remain ns. Use the current `display_units` from context when discussing the visible table, and state the unit clearly.\n- `notebook_reference_defaults` in CURRENT QNEST CONTEXT contains the canonical physical/timing/QSP reference parameters copied from the bundled GHZ/BV/QFT/W-State Monte Carlo notebooks. Preserve those for parameters the researcher did not override.\n- `assistant_default_experiment` is the QNEST Assistant starter experiment: GHZ batch, 5→20 qubits with step 2, 7 QPUs × 4 qubits/QPU, All-to-all → Shared switch → Memory-assisted. Use this when the researcher asks for the default/starter experiment or activates the default GHZ suggestion. It overrides only those listed experiment dimensions; unmentioned physical/timing/QSP parameters still come from `notebook_reference_defaults`.\n- `run.theory_sanity`, when present, states the live geometric-trial model and its expected scale. Do not “correct” large raw ns values merely because they look large; first check units. The Run table defaults to µs for readability while saved per-request result tables remain ns.\n- In Batch / sweep mode, preserve and use the batch scaling plots alongside the clean per-circuit/per-replicate tables; do not imply that adding exact tables removed the plots.\n- If a requested result layer has not completed, say exactly which layer/result is unavailable instead of inventing it.\n- If the request specifies Compile, Schedule or Run parameters, set those controls before complete_workflow.\n- If there is no circuit and no circuit source/benchmark was specified, ask for one rather than inventing it.\n- Full control means full control of QNEST's exposed application actions, not arbitrary Python, shell, filesystem deletion, or external-system access.\n- Keep message useful but compact. Do not include markdown code fences around the JSON.\n"""

    def ask(self, user_text, context, history=None, progress=None):

        def report(stage, detail=''):
            if progress is not None:
                try:
                    progress(stage, detail)
                except Exception:
                    pass
        report('context', 'Grounding the request in QNEST project knowledge and live workspace state')
        canonical = _canonical_project_fact_reply(user_text)
        if canonical is not None:
            report('ready', 'Answered from the local QNEST knowledge base')
            return AssistantReply(message=canonical, actions=[], raw=canonical, model='QNEST knowledge base')
        messages = [{'role': 'system', 'content': self.system_prompt(context)}]
        for item in (history or [])[-8:]:
            role = item.get('role')
            content = item.get('content', '')
            if role in {'user', 'assistant'} and content:
                messages.append({'role': role, 'content': content[:6000]})
        messages.append({'role': 'user', 'content': user_text})
        if self.provider.startswith('Ollama'):
            report('connect', f'Checking local {self.model}')
            ok, detail = self.ensure_ollama_running(wait_seconds=10.0)
            if not ok:
                raise LLMConnectionError(detail)
            report('inference', f'Waiting for {self.model} to generate a response')
            data = self._request_json(self.endpoint + '/api/chat', {'model': self.model, 'messages': messages, 'stream': False, 'format': PLAN_SCHEMA, 'think': False, 'options': {'temperature': self.temperature}})
            raw = str((data.get('message') or {}).get('content', ''))
        else:
            report('connect', 'Checking the configured model endpoint')
            base = self.endpoint + ('' if self.endpoint.endswith('/v1') else '/v1')
            headers = {}
            key = os.environ.get('QNEST_LLM_API_KEY', '').strip()
            if key:
                headers['Authorization'] = f'Bearer {key}'
            report('inference', f'Waiting for {self.model} to generate a response')
            data = self._request_json(base + '/chat/completions', {'model': self.model, 'messages': messages, 'temperature': self.temperature, 'response_format': {'type': 'json_object'}}, headers=headers)
            choices = data.get('choices') or []
            raw = str(((choices[0] if choices else {}).get('message') or {}).get('content', ''))
        report('validate', 'Validating the structured QNEST response')
        obj = _json_from_text(raw)
        message = str(obj.get('message') or 'I prepared a plan.')
        actions = obj.get('actions') if isinstance(obj.get('actions'), list) else []
        cleaned = []
        allowed = {a['name'] for a in ACTION_CATALOG}
        for action in actions:
            if not isinstance(action, dict):
                continue
            name = str(action.get('name', ''))
            if name not in allowed:
                continue
            args = action.get('args') if isinstance(action.get('args'), dict) else {}
            cleaned.append({'name': name, 'args': args})
        cleaned, augmented = _enforce_end_to_end_plan(user_text, context, cleaned)
        if augmented:
            message = message.rstrip()
            if message and message[-1] not in '.!?':
                message += '.'
            if _planned_run_available(context, cleaned):
                mc_runs = (context.get('run') or {}).get('monte_carlo_runs')
                mc_note = f' using the current {mc_runs} Monte Carlo run(s) per point' if mc_runs else ' using the current Monte Carlo configuration'
                message += ' The validated plan will then continue through Compile/Distribute, Qoala scheduling, and AFA-QSP/HAMFA-QSP Run' + mc_note + '.'
            else:
                message += ' The validated plan will continue through Compile/Distribute and Qoala scheduling. Monte Carlo Run is omitted because the resulting network is switch-free.'
        report('ready', 'Response ready')
        return AssistantReply(message=message, actions=cleaned, raw=raw, model=self.model)