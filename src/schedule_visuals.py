from pathlib import Path
import json
import os
import shutil
import subprocess
import threading
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote

@contextmanager
def _serve_html_locally(html_path):
    directory = html_path.parent.resolve()

    class QuietHandler(SimpleHTTPRequestHandler):

        def log_message(self, _format, *_args):
            pass
    handler = partial(QuietHandler, directory=str(directory))
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        yield f'http://{host}:{port}/{quote(html_path.name)}'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

def _candidate_browsers():
    candidates = []
    env_browser = os.environ.get('QNEST_CHROMIUM') or os.environ.get('CHROME_PATH')
    if env_browser:
        candidates.append(env_browser)
    for name in ('chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable', 'microsoft-edge', 'msedge'):
        path = shutil.which(name)
        if path:
            candidates.append(path)
    candidates.extend(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/Applications/Chromium.app/Contents/MacOS/Chromium', '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'])
    out = []
    seen = set()
    for candidate in candidates:
        p = str(Path(candidate).expanduser())
        if p not in seen and Path(p).exists():
            seen.add(p)
            out.append(p)
    return out

def _validate_snapshot(path):
    try:
        from PIL import Image, ImageChops, ImageStat
        with Image.open(path) as src:
            im = src.convert('RGB')
            w, h = im.size
            if w < 320 or h < 180:
                return (False, f'schedule preview is too small ({w}×{h} px)')
            corners = [im.getpixel((0, 0)), im.getpixel((w - 1, 0)), im.getpixel((0, h - 1)), im.getpixel((w - 1, h - 1))]
            bg = tuple((round(sum((c[i] for c in corners)) / 4) for i in range(3)))
            background = Image.new('RGB', im.size, bg)
            diff = ImageChops.difference(im, background).convert('L')
            mask = diff.point(lambda v: 255 if v >= 12 else 0)
            bbox = mask.getbbox()
            if bbox is None:
                return (False, 'schedule preview contains no visible content')
            stat = ImageStat.Stat(mask)
            changed_fraction = stat.mean[0] / 255.0
            if changed_fraction < 0.00035:
                return (False, 'schedule preview is effectively blank')
            left, top, right, bottom = bbox
            if right - left < 180 or bottom - top < 80:
                return (False, 'schedule visualization collapsed while rendering')
            pad_x, pad_y = (24, 20)
            crop = (max(0, left - pad_x), max(0, top - pad_y), min(w, right + pad_x), min(h, bottom + pad_y))
            im.crop(crop).save(path)
        return (True, None)
    except Exception as exc:
        return (False, f'could not validate schedule preview: {type(exc).__name__}: {exc}')

def _snapshot_with_playwright(html_path, png_path, *, width, height, ui_options=None, hide_controls=True):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = None
        errors = []
        args = ['--allow-file-access-from-files']
        if hasattr(os, 'geteuid') and os.geteuid() == 0:
            args.append('--no-sandbox')
        try:
            browser = pw.chromium.launch(headless=True, args=args)
        except Exception as exc:
            errors.append(str(exc))
            for executable in _candidate_browsers():
                try:
                    browser = pw.chromium.launch(headless=True, executable_path=executable, args=args)
                    break
                except Exception as inner:
                    errors.append(str(inner))
        if browser is None:
            raise RuntimeError('Could not launch Chromium. ' + ' | '.join(errors[-2:]))
        try:
            page = browser.new_page(viewport={'width': width, 'height': height})
            page.set_default_timeout(10000)
            with _serve_html_locally(html_path) as uri:
                page.goto(uri, wait_until='load', timeout=15000)
                svg = page.locator('svg#g').first
            svg.wait_for(state='visible', timeout=20000)
            opts = dict(ui_options or {})
            if opts:
                page.evaluate("opts => {\n                      const setVal = (id, val, eventName='change') => {\n                        const el = document.getElementById(id);\n                        if (!el || val === undefined || val === null) return;\n                        el.value = String(val);\n                        el.dispatchEvent(new Event(eventName, {bubbles:true}));\n                      };\n                      setVal('cw', opts.cw, 'change');\n                      setVal('rh', opts.rh, 'change');\n                      setVal('lb', opts.lb, 'change');\n                      setVal('gf', opts.gf, 'change');\n                      setVal('px', opts.px, 'input');\n                    }", opts)
                page.wait_for_timeout(180)
            if hide_controls:
                page.evaluate("() => {\n                      const ctrl = document.querySelector('.ctrl');\n                      if (ctrl) ctrl.style.display = 'none';\n                    }")
                page.wait_for_timeout(60)
            painted = False
            last_state = None
            for _ in range(50):
                try:
                    last_state = svg.evaluate("el => ({\n                          children: el.querySelectorAll('*').length,\n                          w: Math.max(el.scrollWidth || 0, el.clientWidth || 0,\n                                      Number(el.getAttribute('width')) || 0),\n                          h: Math.max(el.scrollHeight || 0, el.clientHeight || 0,\n                                      Number(el.getAttribute('height')) || 0)\n                        })")
                    if last_state.get('children', 0) > 8 and last_state.get('w', 0) > 150 and (last_state.get('h', 0) > 80):
                        painted = True
                        break
                except Exception:
                    pass
                page.wait_for_timeout(120)
            if not painted:
                raise RuntimeError(f'Gantt HTML loaded but did not paint; state={last_state}')
            dims = page.evaluate("() => {\n                  const sc = document.getElementById('sc');\n                  const svg = document.getElementById('g');\n                  if (sc) {\n                    const sw = Math.max(sc.scrollWidth, sc.clientWidth, 400);\n                    const sh = Math.max(sc.scrollHeight, sc.clientHeight, 160);\n                    sc.style.overflow = 'visible';\n                    sc.style.width = sw + 'px';\n                    sc.style.maxWidth = 'none';\n                    sc.style.height = sh + 'px';\n                  }\n                  document.documentElement.style.overflow = 'visible';\n                  document.body.style.overflow = 'visible';\n                  const r = document.body.getBoundingClientRect();\n                  return {\n                    w: Math.ceil(Math.max(document.body.scrollWidth, document.documentElement.scrollWidth, r.width, 600)),\n                    h: Math.ceil(Math.max(document.body.scrollHeight, document.documentElement.scrollHeight, r.height, 300)),\n                    svgW: svg ? Math.ceil(svg.getBoundingClientRect().width) : 0,\n                    svgH: svg ? Math.ceil(svg.getBoundingClientRect().height) : 0\n                  };\n                }")
            page.wait_for_timeout(150)
            target_w = max(width, min(int(dims.get('w', width)), 14000))
            target_h = max(height, min(int(dims.get('h', height)), 10000))
            try:
                page.set_viewport_size({'width': min(target_w, 5000), 'height': min(target_h, 3500)})
            except Exception:
                pass
            png_path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(png_path), full_page=True, timeout=12000)
        finally:
            browser.close()

def _snapshot_with_chromium_cli(html_path, png_path, *, width, height, ui_options=None, hide_controls=True):
    browsers = _candidate_browsers()
    if not browsers:
        raise RuntimeError('No Chromium/Chrome/Edge executable was found.')
    render_html = html_path
    temp_html = None
    if ui_options or hide_controls:
        try:
            opts_json = json.dumps(dict(ui_options or {}))
            injected = f"\n<script>\nwindow.addEventListener('load', function() {{\n  setTimeout(function() {{\n    const opts = {opts_json};\n    const setVal = (id, val, ev) => {{\n      const el = document.getElementById(id);\n      if (!el || val === undefined || val === null) return;\n      el.value = String(val);\n      el.dispatchEvent(new Event(ev || 'change', {{bubbles:true}}));\n    }};\n    setVal('cw', opts.cw, 'change');\n    setVal('rh', opts.rh, 'change');\n    setVal('lb', opts.lb, 'change');\n    setVal('gf', opts.gf, 'change');\n    setVal('px', opts.px, 'input');\n    if ({str(bool(hide_controls)).lower()}) {{\n      const ctrl = document.querySelector('.ctrl');\n      if (ctrl) ctrl.style.display = 'none';\n    }}\n  }}, 150);\n}});\n</script>\n"
            source = html_path.read_text(encoding='utf-8')
            source = source.replace('</body>', injected + '\n</body>')
            temp_html = html_path.with_name('.qnest_' + html_path.name)
            temp_html.write_text(source, encoding='utf-8')
            render_html = temp_html
        except Exception:
            render_html = html_path
    last_error = ''
    try:
        for browser in browsers:
            cmd = [browser, '--headless=new', '--disable-gpu', '--allow-file-access-from-files', '--virtual-time-budget=4000', f'--window-size={width},{height}', f'--screenshot={png_path}']
            if hasattr(os, 'geteuid') and os.geteuid() == 0:
                cmd.append('--no-sandbox')
            cmd.append(render_html.resolve().as_uri())
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=18)
                if proc.returncode == 0 and png_path.exists() and (png_path.stat().st_size > 0):
                    ok, reason = _validate_snapshot(png_path)
                    if ok:
                        return
                    last_error = reason or 'Chromium produced an invalid image'
                else:
                    last_error = (proc.stderr or proc.stdout or f'exit code {proc.returncode}').strip()
            except Exception as exc:
                last_error = str(exc)
        raise RuntimeError(last_error or 'Chromium could not render the schedule HTML.')
    finally:
        if temp_html is not None:
            try:
                temp_html.unlink(missing_ok=True)
            except Exception:
                pass

def snapshot_schedule_html(html_path, png_path=None, *, width=1800, height=950, ui_options=None, hide_controls=True):
    html = Path(html_path).expanduser().resolve()
    if not html.exists() or not html.is_file():
        return (None, f'Schedule HTML does not exist: {html}')
    if html.suffix.lower() not in {'.html', '.htm'}:
        return (None, 'Only local HTML schedule artifacts can be previewed.')
    png = Path(png_path).expanduser().resolve() if png_path else html.with_suffix('.preview.png')
    errors = []
    try:
        _snapshot_with_playwright(html, png, width=width, height=height, ui_options=ui_options, hide_controls=hide_controls)
        ok, reason = _validate_snapshot(png)
        if ok:
            return (png, None)
        errors.append(f'Playwright validation: {reason}')
    except Exception as exc:
        errors.append(f'Playwright: {exc}')
    try:
        _snapshot_with_chromium_cli(html, png, width=width, height=height, ui_options=ui_options, hide_controls=hide_controls)
        ok, reason = _validate_snapshot(png)
        if ok:
            return (png, None)
        errors.append(f'Chromium validation: {reason}')
    except Exception as exc:
        errors.append(f'Chromium CLI: {exc}')
    try:
        if png.exists():
            png.unlink()
    except Exception:
        pass
    return (None, '; '.join(errors[-3:]))