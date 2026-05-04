# app.py
import json
import os
import shutil
import threading
import time

from flask import Flask, Response, jsonify, render_template, request, send_from_directory

import effects
from controller import apply_color, apply_fade, get_pixels, init_strip

app = Flask(__name__)
strip = init_strip()

BASE_DIR = os.path.dirname(__file__)
SCENES_DIR = os.path.join(BASE_DIR, 'scenes')
PLAYLISTS_DIR = os.path.join(BASE_DIR, 'playlists')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
os.makedirs(PLAYLISTS_DIR, exist_ok=True)

# Make turrell_colors.json available under /static for the UI dropdown.
os.makedirs(STATIC_DIR, exist_ok=True)
_turrell_src = os.path.join(BASE_DIR, 'turrell_colors.json')
_turrell_dst = os.path.join(STATIC_DIR, 'turrell_colors.json')
if os.path.exists(_turrell_src) and not os.path.exists(_turrell_dst):
    shutil.copy(_turrell_src, _turrell_dst)


def _idle_status():
    return {
        'running': False,
        'paused': False,
        'current_effect': None,
        'current_transition': None,
        'step': 0,
        'total_steps': 0,
        'elapsed': 0,
        'duration': 0,
        'scene': None,
        'narrative_intro': None,
        'narrative': None,
        'step_params': None,
        'speed': 1.0,
        'brightness': 31,
        'playlist': None,
        'playlist_step': 0,
        'playlist_total': 0,
    }


# Shared status reported via /status. Mutate only while holding status_lock.
status = _idle_status()
status_lock = threading.Lock()
scene_thread = None  # guarded by status_lock


def _set_status(**fields):
    """Update status under lock."""
    with status_lock:
        status.update(fields)


def run_items_thread(items, playlist_name, speed):
    """Run a list of {'scene': scene_data, 'repeat': N|None} items in sequence."""
    _set_status(
        running=True,
        paused=False,
        playlist=playlist_name,
        playlist_total=len(items),
        speed=speed,
    )
    try:
        for pidx, item in enumerate(items, start=1):
            if effects.is_cancelled():
                break
            scene_data = item['scene']
            steps = scene_data.get('steps', [])
            start_time = time.time()
            _set_status(
                playlist_step=pidx,
                scene=scene_data.get('name', 'Unnamed'),
                total_steps=len(steps),
                duration=effects.estimate_duration(steps, speed=speed),
                narrative_intro=scene_data.get('narrative_intro'),
            )

            def on_step(idx, step, _start=start_time):
                _set_status(
                    step=idx,
                    current_effect=step.get('effect', 'solid'),
                    current_transition=step.get('transition', 'fade'),
                    elapsed=int(time.time() - _start),
                    narrative=step.get('narrative'),
                    step_params=effects.effect_kwargs(step),
                )

            effects.apply_scene(
                strip, scene_data,
                on_step=on_step,
                speed=speed,
                repeat=item.get('repeat'),
            )
    finally:
        with status_lock:
            preserved_brightness = status.get('brightness', 31)
            preserved_speed = status.get('speed', 1.0)
            status.update(_idle_status())
            status['brightness'] = preserved_brightness
            status['speed'] = preserved_speed


def _start_run(items, playlist_name=None):
    """Launch a sequence of scenes in a background thread."""
    global scene_thread
    with status_lock:
        if scene_thread is not None and scene_thread.is_alive():
            return False, 'Scene already running'
        effects.reset_cancel()
        effects.resume()
        speed = float(status.get('speed') or 1.0)
        scene_thread = threading.Thread(
            target=run_items_thread,
            args=(items, playlist_name, speed),
            daemon=True,
        )
        scene_thread.start()
    return True, None


def _start_scene(scene_data):
    return _start_run([{'scene': scene_data}], None)


def _set_brightness(value):
    if hasattr(strip, 'set_global_brightness'):
        strip.set_global_brightness(value)
    elif hasattr(strip, 'set_brightness'):
        strip.set_brightness(value)
    elif hasattr(strip, 'global_brightness'):
        strip.global_brightness = value


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/set_color', methods=['POST'])
def set_color():
    data = request.json or {}
    color = data.get('color', [255, 255, 255])
    apply_color(strip, color)
    return jsonify(status='ok')


@app.route('/fade', methods=['POST'])
def fade():
    data = request.json or {}
    apply_fade(strip, data['start'], data['end'], float(data['duration']))
    return jsonify(status='fading')


@app.route('/apply_scene', methods=['POST'])
def scene():
    data = request.json or {}
    ok, err = _start_scene(data)
    if not ok:
        return jsonify({'error': err}), 409
    return jsonify(status='scene started')


@app.route('/scenes', methods=['GET'])
def list_scenes():
    scene_files = sorted(f for f in os.listdir(SCENES_DIR) if f.endswith('.json'))
    out = []
    for fname in scene_files:
        try:
            with open(os.path.join(SCENES_DIR, fname)) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            out.append({'filename': fname, 'name': fname, 'description': '', 'warnings': [f'parse error: {e}']})
            continue
        out.append({
            'filename': fname,
            'name': data.get('name', fname),
            'description': data.get('description', ''),
            'warnings': effects.validate_scene(data),
        })
    return jsonify(out)


@app.route('/apply_scene_file', methods=['POST'])
def apply_scene_file():
    data = request.json or {}
    filename = data.get('filename')
    if not filename or not filename.endswith('.json') or os.sep in filename or '/' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    path = os.path.join(SCENES_DIR, filename)
    if not os.path.isfile(path):
        return jsonify({'error': 'Scene not found'}), 404
    with open(path) as f:
        scene_data = json.load(f)
    ok, err = _start_scene(scene_data)
    if not ok:
        return jsonify({'error': err}), 409
    return jsonify({'status': 'scene started'})


def _safe_filename(name):
    return bool(name) and name.endswith('.json') and os.sep not in name and '/' not in name and not name.startswith('.')


@app.route('/playlists', methods=['GET'])
def list_playlists():
    if not os.path.isdir(PLAYLISTS_DIR):
        return jsonify([])
    files = sorted(f for f in os.listdir(PLAYLISTS_DIR) if f.endswith('.json'))
    out = []
    for fname in files:
        try:
            with open(os.path.join(PLAYLISTS_DIR, fname)) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            out.append({'filename': fname, 'name': fname, 'description': '', 'item_count': 0, 'warnings': [f'parse error: {e}']})
            continue
        items = data.get('items', []) or []
        warnings = []
        for i, it in enumerate(items, start=1):
            sc = it.get('scene') if isinstance(it, dict) else None
            if not sc:
                warnings.append(f'item {i}: missing "scene"')
            elif not os.path.isfile(os.path.join(SCENES_DIR, sc)):
                warnings.append(f'item {i}: scene {sc!r} not found')
        out.append({
            'filename': fname,
            'name': data.get('name', fname),
            'description': data.get('description', ''),
            'item_count': len(items),
            'warnings': warnings,
        })
    return jsonify(out)


@app.route('/apply_playlist', methods=['POST'])
def apply_playlist():
    data = request.json or {}
    filename = data.get('filename')
    if not _safe_filename(filename):
        return jsonify({'error': 'Invalid filename'}), 400
    path = os.path.join(PLAYLISTS_DIR, filename)
    if not os.path.isfile(path):
        return jsonify({'error': 'Playlist not found'}), 404
    with open(path) as f:
        playlist = json.load(f)
    items = []
    for item in (playlist.get('items') or []):
        if not isinstance(item, dict):
            continue
        scene_filename = item.get('scene')
        if not _safe_filename(scene_filename):
            return jsonify({'error': f'Invalid scene filename: {scene_filename!r}'}), 400
        spath = os.path.join(SCENES_DIR, scene_filename)
        if not os.path.isfile(spath):
            return jsonify({'error': f'Scene {scene_filename!r} not found'}), 404
        with open(spath) as sf:
            scene_data = json.load(sf)
        items.append({'scene': scene_data, 'repeat': item.get('repeat')})
    if not items:
        return jsonify({'error': 'Playlist has no playable items'}), 400
    ok, err = _start_run(items, playlist.get('name', filename))
    if not ok:
        return jsonify({'error': err}), 409
    return jsonify({'status': 'playlist started'})


@app.route('/status', methods=['GET'])
def get_status():
    with status_lock:
        return jsonify(dict(status))


@app.route('/pixels', methods=['GET'])
def pixels_now():
    return jsonify(get_pixels())


@app.route('/pixels_stream')
def pixels_stream():
    """Server-Sent Events stream of the LED buffer for the browser preview."""
    def gen():
        last = None
        while True:
            snap = get_pixels()
            if snap != last:
                yield f"data: {json.dumps(snap)}\n\n"
                last = snap
            time.sleep(0.05)  # 20 Hz cap
    return Response(gen(), mimetype='text/event-stream')


@app.route('/status_stream')
def status_stream():
    """Server-Sent Events stream of status changes. ~5 Hz, push on change."""
    def gen():
        last = None
        # Send a hello immediately so EventSource fires `open`.
        while True:
            with status_lock:
                snap = dict(status)
            if snap != last:
                yield f"data: {json.dumps(snap)}\n\n"
                last = snap
            time.sleep(0.2)
    return Response(gen(), mimetype='text/event-stream')


@app.route('/save_scene', methods=['POST'])
def save_scene():
    """Save a scene JSON to scenes/. Validates structure; refuses overwrite
    unless `overwrite: true` is set."""
    data = request.json or {}
    filename = data.get('filename', '')
    scene_data = data.get('data')
    overwrite = bool(data.get('overwrite'))
    if not _safe_filename(filename):
        return jsonify({'error': 'Invalid filename (must end in .json, no path separators)'}), 400
    if not isinstance(scene_data, dict):
        return jsonify({'error': '"data" must be an object'}), 400
    warnings = effects.validate_scene(scene_data)
    if warnings:
        return jsonify({'error': 'Scene validation failed', 'warnings': warnings}), 400
    path = os.path.join(SCENES_DIR, filename)
    if os.path.exists(path) and not overwrite:
        return jsonify({'error': 'File exists', 'exists': True}), 409
    with open(path, 'w') as f:
        json.dump(scene_data, f, indent=2)
    return jsonify({'status': 'saved', 'filename': filename})


@app.route('/run_effect', methods=['POST'])
def run_effect():
    data = request.json or {}
    effect = data.get('effect')
    params = data.get('params', {}) or {}
    if not effect:
        return jsonify({'error': 'No effect provided'}), 400
    fn = effects.EFFECTS.get(effect)
    if not fn:
        return jsonify({'error': 'Unknown effect'}), 400
    threading.Thread(target=fn, args=(strip,), kwargs=params, daemon=True).start()
    return jsonify({'status': f'{effect} started'})


@app.route('/pause', methods=['POST'])
def pause_scene():
    effects.pause()
    _set_status(paused=True)
    return jsonify({'status': 'paused'})


@app.route('/resume', methods=['POST'])
def resume_scene():
    effects.resume()
    _set_status(paused=False)
    return jsonify({'status': 'running'})


@app.route('/brightness', methods=['POST'])
def set_brightness():
    data = request.json or {}
    try:
        value = int(data.get('value'))
    except (TypeError, ValueError):
        return jsonify({'error': 'value must be an integer 0-31'}), 400
    if not 0 <= value <= 31:
        return jsonify({'error': 'value must be 0-31'}), 400
    _set_brightness(value)
    _set_status(brightness=value)
    return jsonify({'status': 'ok', 'brightness': value})


@app.route('/speed', methods=['POST'])
def set_speed():
    """Set the speed multiplier for the next scene start (1.0 = normal)."""
    data = request.json or {}
    try:
        value = float(data.get('value'))
    except (TypeError, ValueError):
        return jsonify({'error': 'value must be a number'}), 400
    if value <= 0:
        return jsonify({'error': 'value must be > 0'}), 400
    _set_status(speed=value)
    return jsonify({'status': 'ok', 'speed': value})


@app.route('/stop', methods=['POST'])
def stop_scene():
    global scene_thread
    with status_lock:
        thread = scene_thread
    if thread is None or not thread.is_alive():
        apply_color(strip, [0, 0, 0])
        return jsonify({'status': 'idle'})
    effects.cancel()
    effects.resume()  # don't deadlock a paused worker
    thread.join(timeout=5)
    apply_color(strip, [0, 0, 0])
    effects.reset_cancel()
    return jsonify({'status': 'stopped'})


@app.route('/off', methods=['POST'])
def turn_off():
    apply_color(strip, [0, 0, 0])
    return jsonify({'status': 'off'})


@app.route('/exit', methods=['POST'])
def exit_server():
    effects.cancel()
    effects.resume()
    apply_color(strip, [0, 0, 0])
    os._exit(0)


@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
