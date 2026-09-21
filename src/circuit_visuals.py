from html.parser import HTMLParser
from pathlib import Path
import html as _html
import os
import shutil
import subprocess
_RESPONSIVE_CSS = '\n<style id="qnest-responsive-pytket">\nhtml, body {\n  margin: 0 !important;\n  padding: 0 !important;\n  width: 100% !important;\n  height: 100% !important;\n  min-width: 0 !important;\n  min-height: 0 !important;\n  overflow: hidden !important;\n  background: #ffffff;\n}\n.pytket-circuit-display-container {\n  position: fixed !important;\n  inset: 0 !important;\n  width: 100vw !important;\n  height: 100vh !important;\n  min-width: 0 !important;\n  min-height: 0 !important;\n  max-width: none !important;\n  max-height: none !important;\n  box-sizing: border-box !important;\n  resize: none !important;\n  overflow: hidden !important;\n}\ncircuit-display-container {\n  display: block !important;\n  width: 100% !important;\n  height: 100% !important;\n  min-width: 0 !important;\n  min-height: 0 !important;\n  max-width: none !important;\n  max-height: none !important;\n}\n</style>\n'
_RESPONSIVE_JS = '\n<script id="qnest-responsive-pytket-script">\n(function () {\n  function fitOuterShell() {\n    const host = document.querySelector(\'.pytket-circuit-display-container\');\n    if (!host) return;\n    host.style.width = \'100vw\';\n    host.style.height = \'100vh\';\n    host.style.maxWidth = \'none\';\n    host.style.maxHeight = \'none\';\n    host.style.resize = \'none\';\n    const component = host.querySelector(\'circuit-display-container\');\n    if (component) {\n      component.style.display = \'block\';\n      component.style.width = \'100%\';\n      component.style.height = \'100%\';\n      component.style.maxWidth = \'none\';\n      component.style.maxHeight = \'none\';\n    }\n  }\n  window.addEventListener(\'load\', fitOuterShell);\n  window.addEventListener(\'resize\', fitOuterShell);\n  const observer = new MutationObserver(fitOuterShell);\n  observer.observe(document.documentElement, {childList: true, subtree: true});\n  setTimeout(fitOuterShell, 0);\n  setTimeout(fitOuterShell, 250);\n  setTimeout(fitOuterShell, 1000);\n})();\n</script>\n'

class _IFrameSrcdocExtractor(HTMLParser):

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.srcdoc = None

    def handle_starttag(self, tag, attrs):
        if self.srcdoc is not None or tag.lower() != 'iframe':
            return
        data = dict(attrs)
        value = data.get('srcdoc')
        if value:
            self.srcdoc = value

def _inject_before(text, marker, addition):
    idx = text.lower().rfind(marker.lower())
    if idx >= 0:
        return text[:idx] + addition + '\n' + text[idx:]
    return text + '\n' + addition

def make_responsive_pytket_html_text(renderer_html):
    text = str(renderer_html or '')
    parser = _IFrameSrcdocExtractor()
    try:
        parser.feed(text)
    except Exception:
        parser.srcdoc = None
    if parser.srcdoc:
        inner = _html.unescape(parser.srcdoc)
    else:
        inner = text
    if '<html' not in inner.lower():
        inner = '<!DOCTYPE html><html><head></head><body>' + inner + '</body></html>'
    if 'qnest-responsive-pytket' not in inner:
        inner = _inject_before(inner, '</head>', _RESPONSIVE_CSS)
        inner = _inject_before(inner, '</body>', _RESPONSIVE_JS)
    return inner

def make_responsive_pytket_html_file(html_path, output_path=None):
    source = Path(html_path).expanduser().resolve()
    dest = Path(output_path).expanduser().resolve() if output_path else source
    text = source.read_text(encoding='utf-8', errors='replace')
    responsive = make_responsive_pytket_html_text(text)
    dest.write_text(responsive, encoding='utf-8')
    return dest

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

def _validate_and_trim_snapshot(path):
    try:
        from PIL import Image, ImageChops, ImageStat
        with Image.open(path) as src:
            im = src.convert('RGB')
            w, h = im.size
            if w < 160 or h < 80:
                return (False, f'renderer snapshot is too small ({w}×{h} px)')
            corners = [im.getpixel((0, 0)), im.getpixel((w - 1, 0)), im.getpixel((0, h - 1)), im.getpixel((w - 1, h - 1))]
            bg = tuple((round(sum((c[i] for c in corners)) / 4) for i in range(3)))
            background = Image.new('RGB', im.size, bg)
            diff = ImageChops.difference(im, background).convert('L')
            mask = diff.point(lambda v: 255 if v >= 14 else 0)
            bbox = mask.getbbox()
            if bbox is None:
                return (False, 'renderer snapshot contains no visible circuit content')
            stat = ImageStat.Stat(mask)
            changed_fraction = stat.mean[0] / 255.0
            if changed_fraction < 0.00045:
                return (False, 'renderer snapshot is effectively blank')
            left, top, right, bottom = bbox
            content_w = right - left
            content_h = bottom - top
            if content_w < 80 or content_h < 35:
                return (False, f'renderer content collapsed to {content_w}×{content_h} px')
            pad_x, pad_y = (24, 20)
            crop = (max(0, left - pad_x), max(0, top - pad_y), min(w, right + pad_x), min(h, bottom + pad_y))
            cropped = im.crop(crop)
            cropped.save(path)
        return (True, None)
    except Exception as exc:
        return (False, f'could not validate renderer snapshot: {type(exc).__name__}: {exc}')

def validate_pytket_snapshot(path):
    return _validate_and_trim_snapshot(Path(path).expanduser().resolve())

def _snapshot_with_playwright(html_path, png_path, *, width, height):
    from playwright.sync_api import sync_playwright
    html_uri = html_path.resolve().as_uri()
    with sync_playwright() as pw:
        browser = None
        errors = []
        launch_extra = {'args': ['--allow-file-access-from-files']}
        if hasattr(os, 'geteuid') and os.geteuid() == 0:
            launch_extra['args'].append('--no-sandbox')
        try:
            browser = pw.chromium.launch(headless=True, **launch_extra)
        except Exception as exc:
            errors.append(str(exc))
            for executable in _candidate_browsers():
                try:
                    browser = pw.chromium.launch(headless=True, executable_path=executable, **launch_extra)
                    break
                except Exception as inner:
                    errors.append(str(inner))
        if browser is None:
            raise RuntimeError('Could not launch Chromium for the pytket renderer. ' + ' | '.join(errors[-2:]))
        try:
            page = browser.new_page(viewport={'width': width, 'height': height})
            page.goto(html_uri, wait_until='load', timeout=30000)
            host_page = page
            if page.locator('iframe').count():
                iframe = page.locator('iframe').first
                iframe.wait_for(state='visible', timeout=20000)
                frame = iframe.content_frame
                if frame is not None:
                    host_page = frame
            container = host_page.locator('.pytket-circuit-display-container').first
            container.wait_for(state='visible', timeout=25000)
            painted = False
            last_detail = ''
            for _ in range(60):
                try:
                    detail = container.evaluate("el => ({\n                            w: Math.max(el.scrollWidth || 0, el.clientWidth || 0),\n                            h: Math.max(el.scrollHeight || 0, el.clientHeight || 0),\n                            html: (el.innerHTML || '').length,\n                            svg: el.querySelectorAll('svg').length,\n                            canvas: el.querySelectorAll('canvas').length,\n                            children: el.querySelectorAll('*').length\n                        })")
                    last_detail = str(detail)
                    if detail.get('w', 0) >= 120 and detail.get('h', 0) >= 60 and (detail.get('html', 0) >= 200) and (detail.get('svg', 0) > 0 or detail.get('canvas', 0) > 0 or detail.get('children', 0) > 12):
                        painted = True
                        break
                except Exception:
                    pass
                page.wait_for_timeout(200)
            if not painted:
                raise RuntimeError(f"pytket renderer loaded but did not paint circuit content; last DOM state: {last_detail or 'unavailable'}")
            expansion = container.evaluate("root => {\n                  function allNodes(node) {\n                    const out = [];\n                    function walk(n) {\n                      if (!n || !n.querySelectorAll) return;\n                      for (const el of n.querySelectorAll('*')) {\n                        out.push(el);\n                        if (el.shadowRoot) walk(el.shadowRoot);\n                      }\n                    }\n                    walk(node);\n                    return out;\n                  }\n                  const nodes = [root, ...allNodes(root)];\n                  const scrollables = nodes.filter(el => {\n                    try {\n                      return (el.scrollWidth > el.clientWidth + 2 ||\n                              el.scrollHeight > el.clientHeight + 2) &&\n                             el.clientWidth > 40 && el.clientHeight > 25;\n                    } catch (_) { return false; }\n                  });\n                  // Expand deepest scrollables first so ancestor scroll sizes\n                  // are recomputed from their complete child content.\n                  scrollables.reverse().forEach(el => {\n                    const sw = Math.max(el.scrollWidth, el.clientWidth);\n                    const sh = Math.max(el.scrollHeight, el.clientHeight);\n                    el.style.setProperty('overflow', 'visible', 'important');\n                    el.style.setProperty('overflow-x', 'visible', 'important');\n                    el.style.setProperty('overflow-y', 'visible', 'important');\n                    el.style.setProperty('max-width', 'none', 'important');\n                    el.style.setProperty('max-height', 'none', 'important');\n                    if (sw > el.clientWidth + 2)\n                      el.style.setProperty('width', sw + 'px', 'important');\n                    if (sh > el.clientHeight + 2)\n                      el.style.setProperty('height', sh + 'px', 'important');\n                  });\n                  root.style.setProperty('position', 'relative', 'important');\n                  root.style.setProperty('inset', 'auto', 'important');\n                  root.style.setProperty('overflow', 'visible', 'important');\n                  root.style.setProperty('max-width', 'none', 'important');\n                  root.style.setProperty('max-height', 'none', 'important');\n                  const finalW = Math.max(root.scrollWidth, root.clientWidth, 240);\n                  const finalH = Math.max(root.scrollHeight, root.clientHeight, 120);\n                  root.style.setProperty('width', finalW + 'px', 'important');\n                  root.style.setProperty('height', finalH + 'px', 'important');\n                  document.documentElement.style.overflow = 'visible';\n                  document.body.style.overflow = 'visible';\n                  return {w: finalW, h: finalH, expanded: scrollables.length};\n                }")
            page.wait_for_timeout(300)
            target_w = int(min(max(expansion.get('w', width), width), 12000))
            target_h = int(min(max(expansion.get('h', height), height), 12000))
            try:
                page.set_viewport_size({'width': min(target_w, 4000), 'height': min(target_h, 3000)})
            except Exception:
                pass
            png_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                container.screenshot(path=str(png_path))
            except Exception:
                page.screenshot(path=str(png_path), full_page=True)
        finally:
            browser.close()

def _snapshot_with_chromium_cli(html_path, png_path, *, width, height):
    browsers = _candidate_browsers()
    if not browsers:
        raise RuntimeError('No Chromium/Chrome/Edge executable was found.')
    png_path.parent.mkdir(parents=True, exist_ok=True)
    last_error = ''
    for browser in browsers:
        cmd = [browser, '--headless=new', '--disable-gpu', '--allow-file-access-from-files', '--virtual-time-budget=9000', f'--window-size={width},{height}', f'--screenshot={png_path}']
        if hasattr(os, 'geteuid') and os.geteuid() == 0:
            cmd.append('--no-sandbox')
        cmd.append(html_path.resolve().as_uri())
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            if proc.returncode == 0 and png_path.exists() and (png_path.stat().st_size > 0):
                ok, reason = _validate_and_trim_snapshot(png_path)
                if ok:
                    return
                last_error = reason or 'Chromium produced an invalid renderer image'
            else:
                last_error = (proc.stderr or proc.stdout or f'exit code {proc.returncode}').strip()
        except Exception as exc:
            last_error = str(exc)
    raise RuntimeError(last_error or 'Chromium could not render the circuit HTML.')

def snapshot_pytket_html(html_path, png_path=None, *, width=1800, height=900):
    html = Path(html_path).expanduser().resolve()
    if not html.exists():
        return (None, f'Renderer HTML does not exist: {html}')
    try:
        make_responsive_pytket_html_file(html)
    except Exception as exc:
        return (None, f'Could not prepare responsive pytket HTML: {type(exc).__name__}: {exc}')
    png = Path(png_path).expanduser().resolve() if png_path else html.with_suffix('.renderer.png')
    errors = []
    try:
        _snapshot_with_playwright(html, png, width=width, height=height)
        ok, reason = _validate_and_trim_snapshot(png)
        if ok:
            return (png, None)
        errors.append(f'Playwright validation: {reason}')
    except Exception as exc:
        errors.append(f'Playwright: {exc}')
    try:
        _snapshot_with_chromium_cli(html, png, width=width, height=height)
        ok, reason = _validate_and_trim_snapshot(png)
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

def snapshot_many(items):
    results = {}
    for html, png in items:
        html_p = Path(html)
        out, error = snapshot_pytket_html(html_p, png)
        results[str(html_p)] = {'snapshot': str(out) if out is not None else None, 'error': error}
    return results