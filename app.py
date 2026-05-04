# app.py
import json
import os
import shutil
import threading
import time

from flask import Flask, Response, jsonify, render_template, request, send_from_directory

import effects
from controller import apply_color, apply_fade, init_strip

app = Flask(__name__)
strip = init_strip()

BASE_DIR = os.path.dirname(__file__)
SCENES_DIR = os.path.join(BASE_DIR, 'scenes')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

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
    }


# Shared status reported via /status. Mutate only while holding status_lock.
status = _idle_status()
status_lock = threading.Lock()
scene_thread = None  # guarded by status_lock


def _set_status(**fields):
    """Update status under lock."""
    with status_lock:
        status.update(fields)


def run_scene_thread(scene_data, speed):
    steps = scene_data.get('steps', [])
    start_time = time.time()
    _set_status(
        running=True,
        paused=False,
        scene=scene_data.get('name', 'Unnamed'),
        total_steps=len(steps),
        duration=effects.estimate_duration(steps, speed=speed),
        narrative_intro=scene_data.get('narrative_intro'),
        speed=speed,
    )

    def on_step(idx, step):
        _set_status(
            step=idx,
            current_effect=step.get('effect', 'solid'),
            current_transition=step.get('transition', 'fade'),
            elapsed=int(time.time() - start_time),
            narrative=step.get('narrative'),
            step_params=effects.effect_kwargs(step),
        )

    try:
        effects.apply_scene(strip, scene_data, on_step=on_step, speed=speed)
    finally:
        with status_lock:
            preserved_brightness = status.get('brightness', 31)
            status.update(_idle_status())
            status['brightness'] = preserved_brightness


def _start_scene(scene_data):
    """Launch a scene in a background thread. Returns (ok, error_message)."""
    global scene_thread
    with status_lock:
        if scene_thread is not None and scene_thread.is_alive():
            return False, 'Scene already running'
        effects.reset_cancel()
        effects.resume()
        speed = float(status.get('speed') or 1.0)
        scene_thread = threading.Thread(
            target=run_scene_thread,
            args=(scene_data, speed),
            daemon=True,
        )
        scene_thread.start()
    return True, None


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


@app.route('/status', methods=['GET'])
def get_status():
    with status_lock:
        return jsonify(dict(status))


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
