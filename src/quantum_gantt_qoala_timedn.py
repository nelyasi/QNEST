import json
import re
import webbrowser
from pathlib import Path

def _server_from_qubit_name(qid):
    m = re.match('(server_\\d+)', qid)
    return m.group(1) if m else 'unknown'

def _qubit_label(qid):
    return qid.replace('server_', 's').replace('_link_register', '_lnk')

def _qoala_schedule_rows(qoala_output):
    if isinstance(qoala_output, dict) and 'schedule' in qoala_output:
        rows = list(qoala_output['schedule'])
        total = float(qoala_output.get('total_execution_time_ns', max((r.get('end_ns', 0) for r in rows), default=0)))
    elif isinstance(qoala_output, list):
        rows = list(qoala_output)
        total = float(max((r.get('end_ns', 0) for r in rows), default=0))
    else:
        raise TypeError('Expected the Qoala output dict or result["schedule"] list.')
    return (rows, total)
_COMM_TYPES = {'EJPP_START', 'EPR_GENERATION', 'EPR_END'}

def _unique_preserve(items):
    out = []
    seen = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out

def _protocol_role_rank(row, gate_type):
    role = str(row.get('role', '')).lower()
    if role == 'distributed':
        return 0
    if gate_type in {'EJPP_START', 'EPR_GENERATION'} and role == 'create':
        return 0
    if gate_type == 'EPR_END' and role == 'source':
        return 0
    return 1

def _collapse_visual_protocol_rows(rows):
    groups = {}
    normal = []
    for original in rows:
        row = dict(original)
        row['qubits'] = list(original.get('qubits', []))
        gate_type = row.get('type', '')
        event = row.get('event')
        if gate_type in _COMM_TYPES and event is not None:
            groups.setdefault((event, gate_type), []).append(row)
        else:
            normal.append(row)
    merged = list(normal)
    for (event, gate_type), group in groups.items():
        if len(group) == 1:
            merged.append(group[0])
            continue
        group = sorted(group, key=lambda r: (_protocol_role_rank(r, gate_type), float(r.get('start_ns', 0)), r.get('qpu') if r.get('qpu') is not None else -1))
        representative = dict(group[0])
        start_ns = min((float(r['start_ns']) for r in group))
        end_ns = max((float(r['end_ns']) for r in group))
        qids = _unique_preserve((qid for r in group for qid in r.get('qubits', [])))
        qpus = sorted({r.get('qpu') for r in group if r.get('qpu') is not None})
        source_qpu = representative.get('qpu')
        peer_candidates = [q for q in qpus if q != source_qpu]
        representative.update({'qubits': qids, 'start_ns': start_ns, 'end_ns': end_ns, 'duration_ns': end_ns - start_ns, 'role': 'distributed'})
        if peer_candidates:
            representative['peer'] = peer_candidates[0]
        if gate_type == 'EJPP_START':
            representative['operation'] = 'EPR + EJPP_Start'
            representative['task_class'] = 'DistributedEJPPStart'
        elif gate_type == 'EPR_END':
            representative['operation'] = 'ending_process'
            representative['task_class'] = 'DistributedEndingProcess'
        merged.append(representative)
    merged.sort(key=lambda r: (float(r.get('start_ns', 0)), float(r.get('end_ns', 0)), r.get('event') if r.get('event') is not None else -1, r.get('qpu') if r.get('qpu') is not None else -1))
    return merged

def _ejpp_start_wire_info(qids):
    processing = [q for q in qids if '_link_register' not in q]
    links = [q for q in qids if '_link_register' in q]
    if len(processing) != 1 or len(links) < 2:
        return None
    proc = processing[0]
    source_server = _server_from_qubit_name(proc)
    source_links = [q for q in links if _server_from_qubit_name(q) == source_server]
    remote_links = [q for q in links if _server_from_qubit_name(q) != source_server]
    if len(source_links) != 1 or len(remote_links) != 1:
        return None
    return (proc, source_links[0], remote_links[0])

def _expand_ending_process_wires(rows):
    active_by_remote = {}
    output = []
    type_priority = {'EJPP_START': 0, 'EPR_GENERATION': 0, 'EPR_END': 2}
    ordered = sorted((dict(r) for r in rows), key=lambda r: (float(r.get('start_ns', 0)), type_priority.get(r.get('type', ''), 1), r.get('event') if r.get('event') is not None else -1))
    for row in ordered:
        row['qubits'] = list(row.get('qubits', []))
        gate_type = row.get('type', '')
        if gate_type == 'EJPP_START':
            info = _ejpp_start_wire_info(row['qubits'])
            if info is not None:
                _, _, remote_link = info
                active_by_remote[remote_link] = row
        elif gate_type == 'EPR_END':
            matching_remote = next((qid for qid in row['qubits'] if qid in active_by_remote), None)
            if matching_remote is None:
                end_processing = {q for q in row['qubits'] if '_link_register' not in q}
                candidates = []
                for remote, start_row in active_by_remote.items():
                    info = _ejpp_start_wire_info(start_row.get('qubits', []))
                    if info is not None and info[0] in end_processing:
                        candidates.append(remote)
                if len(candidates) == 1:
                    matching_remote = candidates[0]
            if matching_remote is not None:
                start_row = active_by_remote.pop(matching_remote)
                start_qids = list(start_row.get('qubits', []))
                if _ejpp_start_wire_info(start_qids) is not None:
                    row['qubits'] = start_qids
                    row['display_protocol_qubits'] = start_qids
        output.append(row)
    output.sort(key=lambda r: (float(r.get('start_ns', 0)), float(r.get('end_ns', 0)), r.get('event') if r.get('event') is not None else -1, r.get('qpu') if r.get('qpu') is not None else -1))
    return output

def _normalise_visual_rows(rows):
    rows = _collapse_visual_protocol_rows(rows)
    rows = _expand_ending_process_wires(rows)
    return rows

def extract_qoala_timed_schedule(qoala_output):
    raw_rows, total_time = _qoala_schedule_rows(qoala_output)
    rows = _normalise_visual_rows(raw_rows)
    qubit_order = []
    qubit_meta = {}
    seen = set()
    for row in rows:
        for qid in row.get('qubits', []):
            if qid not in seen:
                seen.add(qid)
                qubit_order.append(qid)
                qubit_meta[qid] = {'label': _qubit_label(qid), 'reg': qid.split('[')[0], 'server': _server_from_qubit_name(qid), 'virtual': '_link_register' in qid}
    gates = []
    dedup = set()
    for row in rows:
        qids = list(row.get('qubits', []))
        gate_type = row.get('type', '')
        is_comm = gate_type in _COMM_TYPES
        key = (row.get('event'), gate_type, row.get('start_ns'), row.get('end_ns'), tuple(qids), row.get('operation'))
        if is_comm and key in dedup:
            continue
        dedup.add(key)
        if gate_type == 'EJPP_START':
            label = 'EPR + EJPP_Start'
            display_name = 'EJPP+'
        elif gate_type == 'EPR_GENERATION':
            label = 'EPR generation'
            display_name = 'EPR'
        elif gate_type == 'EPR_END':
            label = 'ending_process'
            display_name = 'END'
        else:
            label = row.get('operation', gate_type or 'operation')
            display_name = label
        gates.append({'name': label, 'display_name': display_name, 'qubits': qids, 'is_comm': is_comm, 'is_micro': False, 'is_classical': False, 'micro': None, 'duration': float(row.get('duration_ns', row['end_ns'] - row['start_ns'])), 't_start': float(row['start_ns']), 't_end': float(row['end_ns']), 'event': row.get('event'), 'qpu': row.get('qpu'), 'peer': row.get('peer'), 'role': row.get('role', ''), 'task_class': row.get('task_class', ''), 'qoala_type': gate_type})
    gates.sort(key=lambda g: (g['t_start'], g['t_end'], g.get('event') or -1))
    return {'total_time': total_time, 'total_time_micro': None, 'qubits': qubit_order, 'qubit_meta': qubit_meta, 'gates': gates, 'gates_micro': None, 'qubits_micro': None, 'qubit_meta_micro': None}
_PALETTE = [{'hex': '#185FA5', 'light': '#dceaf7', 'dark': '#0C447C'}, {'hex': '#0F6E56', 'light': '#d0f0e6', 'dark': '#085041'}, {'hex': '#854F0B', 'light': '#fae8c8', 'dark': '#633806'}, {'hex': '#A32D2D', 'light': '#fad8d8', 'dark': '#791F1F'}, {'hex': '#534AB7', 'light': '#e8e6fa', 'dark': '#3C3489'}, {'hex': '#2D7A9A', 'light': '#d4eef7', 'dark': '#1a5570'}]
_MICRO_COLORS = {'Bell': {'hex': '#7B2D8B', 'light': '#F3E5F5', 'dark': '#5A1F68'}, 'CX_loc': {'hex': '#1565C0', 'light': '#DDEEFF', 'dark': '#0D47A1'}, 'Measure': {'hex': '#4E342E', 'light': '#EFEBE9', 'dark': '#3E2723'}, 'classical_comm': {'hex': '#888888', 'light': '#F5F5F5', 'dark': '#555555'}, 'X_ff': {'hex': '#E65100', 'light': '#FFF3E0', 'dark': '#BF360C'}, 'Z_ff': {'hex': '#2E7D32', 'light': '#E8F5E9', 'dark': '#1B5E20'}}

def _server_colors(qubit_meta):
    servers = sorted({m['server'] for m in qubit_meta.values()})
    return {s: _PALETTE[i % len(_PALETTE)] for i, s in enumerate(servers)}

def _build_html(schedule, time_unit, title, show_micro):
    sc = _server_colors(schedule['qubit_meta'])
    sc_json = json.dumps(sc)
    micro_colors_json = json.dumps(_MICRO_COLORS)
    time_unit_json = json.dumps(time_unit)
    if show_micro and schedule['gates_micro'] is not None:
        gates = schedule['gates_micro']
        total_t = schedule['total_time_micro']
        qubits = schedule['qubits_micro']
        qubit_meta = schedule['qubit_meta_micro']
        is_micro = True
    else:
        gates = schedule['gates']
        total_t = schedule['total_time']
        qubits = schedule['qubits']
        qubit_meta = schedule['qubit_meta']
        is_micro = False
    scale = {'ns': 1.0, 'us': 1000.0, 'µs': 1000.0, 'ms': 1000000.0}.get(time_unit, 1.0)
    display_gates = []
    for gate in gates:
        g = dict(gate)
        for key in ('duration', 't_start', 't_end'):
            if g.get(key) is not None:
                g[key] = float(g[key]) / scale
        display_gates.append(g)
    display_total_t = float(total_t) / scale if total_t is not None else total_t
    data_json = json.dumps({'total_time': display_total_t, 'gates': display_gates, 'qubits': qubits, 'qubit_meta': qubit_meta})
    qubit_rows_json = json.dumps([{'id': qid, 'label': qubit_meta[qid]['label'], 'server': qubit_meta[qid]['server'], 'virtual': qubit_meta[qid].get('virtual', False)} for qid in qubits])
    return f"""<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n<title>{title}</title>\n<style>\n:root{{\n  --bg:#fff;--bg2:#f4f4f2;--text:#111;--muted:#666;\n  --border:rgba(0,0,0,.10);--sep:rgba(0,0,0,.13);\n  --tt:#fff;--tt-bd:rgba(0,0,0,.18);\n  --sans:'DM Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;\n  --mono:'DM Mono','SFMono-Regular',Consolas,'Liberation Mono','Courier New',monospace;\n  --fs-base:clamp(14px,1.5vw,17px);\n  --fs-sm:clamp(12px,1.2vw,15px);\n  --fs-xs:clamp(11px,1.0vw,13px);\n  --fs-h1:clamp(15px,1.8vw,22px);\n}}\n@media(prefers-color-scheme:dark){{\n  :root{{\n    --bg:#181818;--bg2:#242424;--text:#e0e0e0;--muted:#888;\n    --border:rgba(255,255,255,.10);--sep:rgba(255,255,255,.14);\n    --tt:#242424;--tt-bd:rgba(255,255,255,.2);\n  }}\n}}\n*{{box-sizing:border-box;margin:0;padding:0}}\nbody{{\n  background:var(--bg);color:var(--text);\n  font-family:var(--sans);font-size:var(--fs-base);\n  padding:clamp(14px,2vw,28px);\n  -webkit-font-smoothing:antialiased;\n}}\nh1{{\n  font-family:var(--sans);font-size:var(--fs-h1);font-weight:700;\n  letter-spacing:.02em;text-transform:uppercase;margin-bottom:16px;\n}}\n.ctrl{{display:flex;gap:clamp(10px,1.5vw,20px);flex-wrap:wrap;align-items:center;margin-bottom:14px}}\n.ctrl label{{\n  font-size:var(--fs-xs);font-weight:600;color:var(--muted);\n  margin-right:4px;font-family:var(--sans);\n  text-transform:uppercase;letter-spacing:.06em;\n}}\nselect{{\n  font-size:var(--fs-sm);font-family:var(--sans);font-weight:500;\n  padding:5px 10px;border-radius:6px;min-height:34px;\n  border:1px solid var(--border);background:var(--bg2);\n  color:var(--text);cursor:pointer;\n}}\ninput[type=range]{{\n  padding:0;width:clamp(70px,8vw,110px);vertical-align:middle;cursor:pointer;\n}}\n.pxval{{\n  font-size:var(--fs-xs);font-family:var(--mono);font-weight:500;\n  color:var(--muted);min-width:28px;\n}}\n.leg{{\n  display:flex;flex-wrap:wrap;gap:clamp(8px,1.2vw,14px);margin-bottom:14px;\n  font-size:var(--fs-xs);color:var(--muted);align-items:center;\n  font-family:var(--sans);\n}}\n.li{{display:flex;align-items:center;gap:6px;font-weight:500}}\n.sw{{width:clamp(11px,1.2vw,14px);height:clamp(11px,1.2vw,14px);border-radius:3px;flex-shrink:0}}\n.ldiv{{width:1px;height:16px;background:var(--border);margin:0 6px}}\n#sc{{overflow-x:auto}}\nsvg{{display:block}}\n.tt{{\n  position:fixed;background:var(--tt);border:1px solid var(--tt-bd);\n  border-radius:8px;padding:10px 14px;font-size:var(--fs-sm);\n  font-family:var(--sans);pointer-events:none;z-index:999;\n  color:var(--text);line-height:1.8;display:none;\n  box-shadow:0 4px 16px rgba(0,0,0,.15);max-width:300px;word-break:break-all;\n}}\n.tt strong{{font-weight:700}}\n.tt em{{font-style:italic;color:var(--muted);font-size:.9em}}\n</style>\n</head>\n<body>\n<h1>&#x25A6; circuit schedule (timed)</h1>\n<div class="ctrl">\n  <span style="display:flex;align-items:center;gap:6px">\n    <label>px / time unit</label>\n    <input type="range" id="px" min="1" max="40" value="8">\n    <span class="pxval" id="pxval">8</span>\n  </span>\n  <span><label>row height</label>\n  <select id="rh">\n    <option value="26">tight</option>\n    <option value="36" selected>normal</option>\n    <option value="50">spacious</option>\n  </select></span>\n  <span><label>labels</label>\n  <select id="lb">\n    <option value="1" selected>on</option>\n    <option value="0">off</option>\n  </select></span>\n  <span><label>show gates</label>\n  <select id="gf">\n    <option value="all" selected>all</option>\n    <option value="local">local only</option>\n    <option value="remote">remote only</option>\n  </select></span>\n</div>\n<div class="leg" id="leg"></div>\n<div id="sc"><svg id="g"></svg></div>\n<div class="tt" id="tt"></div>\n\n<script>\nvar SCH        = {data_json};\nvar ROWS       = {qubit_rows_json};\nvar SC         = {sc_json};\nvar MC         = {micro_colors_json};\nvar TUNIT      = {time_unit_json};\nvar IS_MICRO   = {json.dumps(is_micro)};\nvar NS         = 'http://www.w3.org/2000/svg';\nvar LW         = 160;\nvar PT         = 42;\nvar PB         = 26;\nvar RG         = 4;\nvar TICK_H     = 7;\n\nvar SANS = "'DM Sans',system-ui,sans-serif";\nvar MONO = "'DM Mono','Courier New',monospace";\n\nvar PX       = 8;\nvar RH       = 36;\nvar SL       = true;\nvar GF       = 'all';\n\nvar dk = function(){{ return matchMedia('(prefers-color-scheme:dark)').matches; }};\nfunction ry(ri){{ return PT + ri*(RH+RG); }}\nfunction mk(tag, attrs){{\n  var e = document.createElementNS(NS, tag);\n  var keys = Object.keys(attrs);\n  for(var i=0;i<keys.length;i++) e.setAttribute(keys[i], attrs[keys[i]]);\n  return e;\n}}\nfunction tx(x, y, s, attrs){{\n  var e = mk('text', Object.assign({{x:x, y:y}}, attrs));\n  e.textContent = s;\n  return e;\n}}\n\nfunction gateFontSize(labelLen){{\n  var base = Math.min(RH * 0.38, 15);\n  if(labelLen > 5) base *= 0.78;\n  return Math.max(9, base) + 'px';\n}}\nfunction rowFontSize(){{\n  return Math.max(11, Math.min(RH * 0.38, 15)) + 'px';\n}}\nfunction tickFontSize(){{\n  return Math.max(10, Math.min(PX * 1.4, 13)) + 'px';\n}}\n\nvar ttEl = document.getElementById('tt');\nfunction showTT(e, gate){{\n  var html = '<strong>' + gate.name + '</strong>';\n  if(gate.micro) html += ' <em>[' + gate.micro + ']</em>';\n  html += '<br>qubits: '   + gate.qubits.join(', ');\n  html += '<br>start: '    + gate.t_start.toFixed(1) + ' ' + TUNIT;\n  html += '<br>end: '      + gate.t_end.toFixed(1)   + ' ' + TUNIT;\n  html += '<br>duration: ' + gate.duration.toFixed(1) + ' ' + TUNIT;\n  html += '<br>type: '     + (gate.qoala_type || (gate.is_comm ? 'communication' : 'local'));\n  if(gate.event !== null && gate.event !== undefined) html += '<br>event: ' + gate.event;\n  if(gate.qpu !== null && gate.qpu !== undefined) html += '<br>QPU: ' + gate.qpu;\n  if(gate.peer !== null && gate.peer !== undefined) html += '<br>peer: QPU ' + gate.peer;\n  if(gate.role) html += '<br>role: ' + gate.role;\n  ttEl.innerHTML = html;\n  ttEl.style.display = 'block';\n  moveTT(e);\n}}\nfunction moveTT(e){{ ttEl.style.left=(e.clientX+16)+'px'; ttEl.style.top=(e.clientY-8)+'px'; }}\nfunction hideTT(){{ ttEl.style.display='none'; }}\n\nfunction tickSpacing(){{\n  var candidates=[1,2,5,10,20,50,100,200,500,1000,2000,5000];\n  for(var i=0;i<candidates.length;i++) if(candidates[i]*PX>=60) return candidates[i];\n  return candidates[candidates.length-1];\n}}\n\nfunction classicalWire(x1, yMid, xDrop, yTarget, col){{\n  var g2=2.5;\n  svg.appendChild(mk('line',{{x1:x1,y1:yMid-g2,x2:xDrop,y2:yMid-g2,stroke:col,'stroke-width':'1.4'}}));\n  svg.appendChild(mk('line',{{x1:x1,y1:yMid+g2,x2:xDrop,y2:yMid+g2,stroke:col,'stroke-width':'1.4'}}));\n  svg.appendChild(mk('line',{{x1:x1,y1:yMid-g2,x2:x1,y2:yMid+g2,stroke:col,'stroke-width':'1.4'}}));\n  if(Math.abs(yTarget-yMid)>4){{\n    svg.appendChild(mk('line',{{x1:xDrop-g2,y1:yMid,x2:xDrop-g2,y2:yTarget-7,stroke:col,'stroke-width':'1.4'}}));\n    svg.appendChild(mk('line',{{x1:xDrop+g2,y1:yMid,x2:xDrop+g2,y2:yTarget-7,stroke:col,'stroke-width':'1.4'}}));\n    svg.appendChild(mk('polygon',{{points:(xDrop-5)+','+(yTarget-7)+' '+(xDrop+5)+','+(yTarget-7)+' '+xDrop+','+yTarget,fill:col}}));\n  }}\n}}\n\nfunction drawMeasureBox(gx,gy,gw,gh,fi,st,gate){{\n  var r=mk('rect',{{x:gx,y:gy,width:gw,height:gh,rx:4,fill:fi,stroke:st,'stroke-width':'1.8'}});\n  r.style.cursor='pointer';\n  (function(g){{r.addEventListener('mouseenter',function(e){{showTT(e,g);}});r.addEventListener('mousemove',moveTT);r.addEventListener('mouseleave',hideTT);}})(gate);\n  svg.appendChild(r);\n  if(gw>18){{\n    var cx3=gx+gw/2,cy3=gy+gh*0.62,r3=Math.min(gw*0.33,gh*0.30);\n    svg.appendChild(mk('path',{{d:'M '+(cx3-r3)+' '+cy3+' A '+r3+' '+r3+' 0 0 1 '+(cx3+r3)+' '+cy3,fill:'none',stroke:st,'stroke-width':'1.4'}}));\n    svg.appendChild(mk('line',{{x1:cx3,y1:cy3,x2:(cx3+r3*0.7),y2:(cy3-r3*0.85),stroke:st,'stroke-width':'1.4'}}));\n  }}\n}}\n\nfunction drawClassCommBox(gx,gy,gw,gh,fi,st,gate){{\n  svg.appendChild(mk('rect',{{x:gx,y:gy,width:gw,height:gh,rx:4,fill:fi,stroke:st,'stroke-width':'1.2','stroke-dasharray':'3,2'}}));\n  var step=7;\n  for(var hx=gx;hx<gx+gw+gh;hx+=step){{\n    var x1h=Math.max(hx-gh,gx),y1h=hx>gx+gh?gy+gh-(hx-(gx+gh)):gy;\n    var x2h=Math.min(hx,gx+gw),y2h=hx<gx+gh?gy:gy+(hx-gx-gh);\n    if(x2h>x1h)svg.appendChild(mk('line',{{x1:x1h,y1:y1h,x2:x2h,y2:y2h,stroke:st,opacity:'0.3','stroke-width':'1'}}));\n  }}\n  if(SL&&gw>28) svg.appendChild(tx(gx+gw/2,gy+gh/2+5,'comm',{{\n    'text-anchor':'middle','font-size':Math.max(9,Math.min(RH*0.28,12))+'px',\n    fill:st,'font-family':MONO,'font-weight':'500'\n  }}));\n  var r2=mk('rect',{{x:gx,y:gy,width:gw,height:gh,rx:4,fill:'none',stroke:st,'stroke-width':'1.2','stroke-dasharray':'3,2'}});\n  r2.style.cursor='pointer';\n  (function(g){{r2.addEventListener('mouseenter',function(e){{showTT(e,g);}});r2.addEventListener('mousemove',moveTT);r2.addEventListener('mouseleave',hideTT);}})(gate);\n  svg.appendChild(r2);\n}}\n\nfunction drawFeedForwardBox(gx,gy,gw,gh,fi,st,tc2,lbl,gate,feedFromQubit){{\n  var rec=measRecord[feedFromQubit];\n  if(rec){{ classicalWire(rec.xEnd, rec.yCentre, gx+gw/2, gy, st); }}\n  var r=mk('rect',{{x:gx,y:gy,width:gw,height:gh,rx:4,fill:fi,stroke:st,'stroke-width':'1.8'}});\n  r.style.cursor='pointer';\n  (function(g){{r.addEventListener('mouseenter',function(e){{showTT(e,g);}});r.addEventListener('mousemove',moveTT);r.addEventListener('mouseleave',hideTT);}})(gate);\n  svg.appendChild(r);\n  if(SL&&gw>12) svg.appendChild(tx(gx+gw/2,gy+gh/2+5,lbl,{{\n    'text-anchor':'middle','font-size':gateFontSize(1),\n    fill:tc2,'font-weight':'700','font-family':MONO\n  }}));\n}}\n\nvar svg;\nvar measRecord;\n\nfunction render(){{\n  svg = document.getElementById('g');\n  svg.innerHTML='';\n  measRecord = {{}};\n  var d       = dk();\n  var gates   = SCH.gates;\n  var totalT  = SCH.total_time;\n  var nR      = ROWS.length;\n  var plotW   = Math.ceil(totalT*PX);\n  var W       = LW+plotW+24;\n  var H       = ry(nR)+PB;\n  svg.setAttribute('width',W); svg.setAttribute('height',H);\n  svg.setAttribute('viewBox','0 0 '+W+' '+H);\n\n  var tf  = d?'#d8d8d8':'#111';\n  var mf  = d?'#888':'#777';\n  var gc  = d?'rgba(255,255,255,.035)':'rgba(0,0,0,.02)';\n  var trc = d?'rgba(255,255,255,.07)':'rgba(0,0,0,.07)';\n  var spc = d?'rgba(255,255,255,.14)':'rgba(0,0,0,.12)';\n  var axc = d?'rgba(255,255,255,.20)':'rgba(0,0,0,.16)';\n\n  var tfs = tickFontSize();\n  var rfs = rowFontSize();\n\n  // time axis\n  svg.appendChild(mk('line',{{x1:LW,y1:PT-2,x2:LW+plotW,y2:PT-2,stroke:axc,'stroke-width':'1'}}));\n  var ts=tickSpacing(), t=0;\n  while(t<=totalT+ts){{\n    var tx2=LW+t*PX;\n    svg.appendChild(mk('line',{{x1:tx2,y1:PT-2,x2:tx2,y2:PT-2-TICK_H,stroke:axc,'stroke-width':'1'}}));\n    svg.appendChild(tx(tx2,PT-2-TICK_H-4,''+t,{{\n      'text-anchor':'middle','font-size':tfs,fill:mf,'font-family':MONO,'font-weight':'500'\n    }}));\n    svg.appendChild(mk('line',{{x1:tx2,y1:PT,x2:tx2,y2:ry(nR),stroke:gc,'stroke-width':'1'}}));\n    t+=ts;\n  }}\n  svg.appendChild(tx(LW+plotW+5,PT-2-TICK_H-4,TUNIT,{{\n    'text-anchor':'start','font-size':tfs,fill:mf,'font-family':MONO,'font-weight':'500'\n  }}));\n\n  // qubit rows\n  var prevServer=null, groupStart=0, groupServer=ROWS.length>0?ROWS[0].server:null;\n  function flushBar(endRi){{\n    if(groupServer==null) return;\n    var col=SC[groupServer],hex=col?col.hex:'#888';\n    var y0=ry(groupStart)+1,y1=ry(endRi)-RG-1;\n    // Left accent bar (zone 1): x 1–5\n    if(y1>y0) svg.appendChild(mk('rect',{{x:1,y:y0,width:4,height:y1-y0,rx:2,fill:hex,opacity:'0.75'}}));\n    // Rotated server label (zone 2): centred at x=13, safely within 6–20px\n    var mid=(y0+y1)/2,sn=groupServer.replace('server_','S');\n    svg.appendChild(tx(13,mid,sn,{{\n      'text-anchor':'middle','font-size':Math.max(8,Math.min(RH*0.28,11))+'px',\n      fill:hex,'font-family':SANS,'font-weight':'700',opacity:'0.85',\n      transform:'rotate(-90,13,'+mid+')'\n    }}));\n  }}\n\n  for(var ri=0;ri<ROWS.length;ri++){{\n    var row=ROWS[ri],y=ry(ri);\n    var isVirtual = row.virtual === true;\n    if(prevServer!==null&&prevServer!==row.server){{\n      svg.appendChild(mk('line',{{x1:0,y1:y-RG/2,x2:W,y2:y-RG/2,stroke:spc,'stroke-width':'1'}}));\n      flushBar(ri); groupStart=ri; groupServer=row.server;\n    }}\n    prevServer=row.server;\n    if(ri%2===0){{\n      var col2=SC[row.server],rf=col2?(d?col2.dark+'18':col2.light+'44'):'transparent';\n      svg.appendChild(mk('rect',{{x:LW,y:y,width:plotW,height:RH,fill:rf}}));\n    }}\n    var dc=SC[row.server];\n    // Dot (zone 3): fixed at x=24, clear of the rotated label\n    var dotSz = Math.max(8, Math.min(RH*0.32, 12));\n    var dotX = 24;\n    if(isVirtual){{\n      svg.appendChild(mk('rect',{{\n        x:dotX,y:y+RH/2-dotSz*0.4,width:dotSz*0.8,height:dotSz*0.8,rx:1,\n        fill:'none',stroke:dc?dc.hex:'#888','stroke-width':'1.5',\n        transform:'rotate(45,'+(dotX+dotSz*0.4)+','+(y+RH/2)+')'\n      }}));\n    }} else {{\n      svg.appendChild(mk('rect',{{\n        x:dotX,y:y+RH/2-dotSz*0.5,width:dotSz,height:dotSz,rx:2,\n        fill:dc?dc.hex:'#888',opacity:'0.85'\n      }}));\n    }}\n    // Qubit name (zone 4): right-aligned to LW-8, starts well after dot\n    svg.appendChild(tx(LW-8,y+RH/2+5,row.label,{{\n      'text-anchor':'end','font-size':rfs,\n      fill: isVirtual?(d?'#aaa':'#888'):tf,\n      'font-family':MONO,'font-weight':'500',\n      'font-style': isVirtual?'italic':'normal'\n    }}));\n    svg.appendChild(mk('line',{{\n      x1:LW,y1:y+RH/2,x2:LW+plotW,y2:y+RH/2,\n      stroke:trc,'stroke-width':'1',\n      'stroke-dasharray': isVirtual?'4,4':'2,3'\n    }}));\n  }}\n  flushBar(ROWS.length);\n\n  var q2r={{}};\n  for(var ri2=0;ri2<ROWS.length;ri2++) q2r[ROWS[ri2].id]=ri2;\n\n  for(var gi=0;gi<gates.length;gi++){{\n    var gate=gates[gi];\n    if(GF==='local'  && gate.is_comm)  continue;\n    if(GF==='remote' && !gate.is_comm) continue;\n\n    var riList=[];\n    for(var qi=0;qi<gate.qubits.length;qi++){{\n      var rr=q2r[gate.qubits[qi]];\n      if(rr!==undefined) riList.push(rr);\n    }}\n    if(riList.length===0) continue;\n\n    var minRi=riList[0],maxRi=riList[0];\n    for(var k=1;k<riList.length;k++){{\n      if(riList[k]<minRi) minRi=riList[k];\n      if(riList[k]>maxRi) maxRi=riList[k];\n    }}\n\n    var gx  = LW + gate.t_start*PX;\n    var gw  = Math.max(gate.duration*PX, 6);\n    var bri = riList[0];\n    var by  = ry(bri);\n    var gh  = RH-6;\n    var gy  = by+Math.floor((RH-gh)/2);\n\n    var fi,st,tc2;\n    if(gate.micro && MC[gate.micro]){{\n      var mcol=MC[gate.micro];\n      fi=d?mcol.dark+'cc':mcol.light; st=mcol.hex; tc2=d?'#eee':mcol.dark;\n    }} else if(gate.is_comm){{\n      fi=d?'#3C3489':'#EEEDFE'; st=d?'#AFA9EC':'#534AB7'; tc2=d?'#CECBF6':'#3C3489';\n    }} else {{\n      var fRi=q2r[gate.qubits[0]],fsrv=fRi!==undefined?ROWS[fRi].server:null,fsc=fsrv?SC[fsrv]:null;\n      fi=fsc?(d?fsc.dark+'cc':fsc.light):(d?'#2a2a2a':'#eee');\n      st=fsc?fsc.hex:'#888'; tc2=d?'#ddd':(fsc?fsc.dark:'#333');\n    }}\n\n    var micro=gate.micro||'none';\n\n    if(micro==='Measure'){{\n      drawMeasureBox(gx,gy,gw,gh,fi,st,gate);\n      measRecord[gate.qubits[0]]={{xEnd:gx+gw, yCentre:by+RH/2}};\n\n    }} else if(micro==='classical_comm'){{\n      drawClassCommBox(gx,gy,gw,gh,fi,st,gate);\n\n    }} else if(micro==='X_ff' || micro==='Z_ff'){{\n      drawFeedForwardBox(gx,gy,gw,gh,fi,st,tc2,micro==='X_ff'?'X':'Z',gate,gate.feed_from||null);\n\n    }} else if(micro==='Bell'){{\n      if(riList.length>1){{\n        var connX=gx+gw/2,topY2=ry(minRi)+RH/2,botY2=ry(maxRi)+RH/2;\n        var seg=(botY2-topY2)/6,wPath='M '+connX+' '+topY2;\n        for(var wi=0;wi<6;wi++){{\n          var wx=connX+(wi%2===0?5:-5);\n          wPath+=' Q '+wx+' '+(topY2+(wi+0.5)*seg)+' '+connX+' '+(topY2+(wi+1)*seg);\n        }}\n        svg.appendChild(mk('path',{{d:wPath,fill:'none',stroke:st,'stroke-width':'1.8'}}));\n      }}\n      for(var bi2=0;bi2<riList.length;bi2++){{\n        var bri2=riList[bi2],by2=ry(bri2),gy2=by2+Math.floor((RH-gh)/2);\n        var rb=mk('rect',{{x:gx,y:gy2,width:gw,height:gh,rx:4,fill:fi,stroke:st,'stroke-width':'1.8'}});\n        rb.style.cursor='pointer';\n        (function(g){{rb.addEventListener('mouseenter',function(e){{showTT(e,g);}});rb.addEventListener('mousemove',moveTT);rb.addEventListener('mouseleave',hideTT);}})(gate);\n        svg.appendChild(rb);\n        if(SL&&gw>14) svg.appendChild(tx(gx+gw/2,gy2+gh/2+5,bi2===0?'Bell':'~',{{\n          'text-anchor':'middle','font-size':gateFontSize(bi2===0?4:1),\n          fill:tc2,'font-weight':'600','font-family':MONO\n        }}));\n      }}\n\n    }} else {{\n      if(riList.length>1){{\n        var cxs=gx+gw/2;\n        svg.appendChild(mk('line',{{x1:cxs,y1:ry(minRi)+RH/2,x2:cxs,y2:ry(maxRi)+RH/2,\n          stroke:st,'stroke-width':gate.is_comm?'1.8':'1.4','stroke-dasharray':gate.is_comm?'4,2':'none'}}));\n      }}\n      for(var bi3=0;bi3<riList.length;bi3++){{\n        var bri3=riList[bi3],by3=ry(bri3),gy3=by3+Math.floor((RH-gh)/2);\n        var rs=mk('rect',{{x:gx,y:gy3,width:gw,height:gh,rx:4,fill:fi,stroke:st,'stroke-width':'1.8'}});\n        rs.style.cursor='pointer';\n        (function(g){{rs.addEventListener('mouseenter',function(e){{showTT(e,g);}});rs.addEventListener('mousemove',moveTT);rs.addEventListener('mouseleave',hideTT);}})(gate);\n        svg.appendChild(rs);\n        if(SL&&gw>14){{\n          var lbl3=bi3===0?(gate.display_name||gate.name):(gate.is_comm?'~':'.');\n          if(lbl3.length>6) lbl3=lbl3.slice(0,6);\n          svg.appendChild(tx(gx+gw/2,gy3+gh/2+5,lbl3,{{\n            'text-anchor':'middle','font-size':gateFontSize(lbl3.length),\n            fill:tc2,'font-weight':'600','font-family':MONO\n          }}));\n        }}\n      }}\n    }}\n  }}\n  buildLeg(gates);\n}}\n\nfunction buildLeg(gates){{\n  var leg=document.getElementById('leg');\n  leg.innerHTML='';\n  var d=dk();\n\n  var servers=Object.keys(SC).sort();\n  for(var i=0;i<servers.length;i++){{\n    var srv=servers[i],col=SC[srv];\n    var div=document.createElement('div'); div.className='li';\n    var sw=document.createElement('span'); sw.className='sw'; sw.style.background=col.hex;\n    div.appendChild(sw);\n    div.appendChild(document.createTextNode(srv.replace('server_','server ')));\n    leg.appendChild(div);\n  }}\n\n  var dv=document.createElement('div'); dv.className='ldiv'; leg.appendChild(dv);\n\n  if(IS_MICRO){{\n    var mkeys=['Bell','CX_loc','Measure','classical_comm','X_ff','Z_ff'];\n    var mlabels={{'Bell':'Bell (ebit gen)','CX_loc':'CX root→link','Measure':'Measure link','classical_comm':'Classical comm','X_ff':'X (feed-fwd)','Z_ff':'Z (feed-fwd)'}};\n    for(var j=0;j<mkeys.length;j++){{\n      var mk2=mkeys[j],mc=MC[mk2];\n      if(!mc) continue;\n      var div2=document.createElement('div'); div2.className='li';\n      var sw2=document.createElement('span'); sw2.className='sw';\n      sw2.style.cssText='background:'+(d?mc.dark:mc.light)+';outline:1.5px solid '+mc.hex;\n      div2.appendChild(sw2);\n      div2.appendChild(document.createTextNode(mlabels[mk2]));\n      leg.appendChild(div2);\n    }}\n  }} else {{\n    var sw3=document.createElement('span'); sw3.className='sw';\n    sw3.style.cssText='background:'+(d?'#3C3489':'#EEEDFE')+';outline:1.5px solid '+(d?'#AFA9EC':'#534AB7');\n    var div3=document.createElement('div'); div3.className='li';\n    div3.appendChild(sw3);\n    div3.appendChild(document.createTextNode('EJPP / communication'));\n    leg.appendChild(div3);\n  }}\n\n  var note=document.createElement('span');\n  note.style.cssText='font-size:var(--fs-xs,12px);color:var(--muted);margin-left:10px;border-left:1px solid var(--border);padding-left:10px';\n  note.textContent='bar width = duration · hover gates for details' + (IS_MICRO?' · italic rows = virtual link qubits':'');\n  leg.appendChild(note);\n}}\n\ndocument.getElementById('gf').addEventListener('change',function(e){{GF=e.target.value;render();}});\ndocument.getElementById('px').addEventListener('input',function(e){{PX=+e.target.value;document.getElementById('pxval').textContent=PX;render();}});\ndocument.getElementById('rh').addEventListener('change',function(e){{RH=+e.target.value;render();}});\ndocument.getElementById('lb').addEventListener('change',function(e){{SL=e.target.value==='1';render();}});\nmatchMedia('(prefers-color-scheme:dark)').addEventListener('change',render);\nrender();\n</script>\n</body>\n</html>"""

def draw_qoala_gantt_timed(qoala_output, output='qoala_gantt_timed.html', show=True, title='Qoala execution schedule (timed)', time_unit='ns'):
    schedule = extract_qoala_timed_schedule(qoala_output)
    html = _build_html(schedule, time_unit, title, False)
    out_path = Path(output).expanduser().resolve()
    out_path.write_text(html, encoding='utf-8')
    if show:
        try:
            from IPython.display import IFrame, display
            display(IFrame(src=str(out_path), width='100%', height='660px'))
        except ImportError:
            webbrowser.open(out_path.as_uri())
    return out_path