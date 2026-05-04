# app.py
import json
import os
import shutil
import threading
import time

from flask import Flask, jsonify, render_template, request, send_from_directory

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

# Shared status reported via /status. Mutate only while holding status_lock.
status = {
    'running': False,
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
}
status_lock = threading.Lock()
scene_thread = None  # guarded by status_lock


def _idle_status():
    return {
        'running': False,
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
    }


def _estimate_duration(steps):
    return int(sum(s.get('duration', 2) + s.get('transition_duration', 0) for s in steps))


def run_scene_thread(scene_data):
    steps = scene_data.get('steps', [])
    total_steps = len(steps)
    start_time = time.time()
    total_duration = _estimate_duration(steps)
    narrative_intro = scene_data.get('narrative_intro')

    with status_lock:
        status.update({
            'running': True,
            'scene': scene_data.get('name', 'Unnamed'),
            'total_steps': total_steps,
            'duration': total_duration,
            'narrative_intro': narrative_intro,
        })

    last = scene_data.get('last', steps[0].get('color', [0, 0, 0]) if steps else [0, 0, 0])
    try:
        for idx, step in enumerate(steps):
            if effects.is_cancelled():
                break
            with status_lock:
                status.update({
                    'step': idx + 1,
                    'current_effect': step.get('effect', 'solid'),
                    'current_transition': step.get('transition', 'fade'),
                    'elapsed': int(time.time() - start_time),
                    'narrative': step.get('narrative'),
                    'step_params': {
                        k: v for k, v in step.items()
                        if k not in ('effect', 'transition', 'transition_duration', 'narrative', 'step')
                    },
                })

            transition_name = step.get('transition', 'fade')
            if transition_name != 'instant':
                from_color = last
                to_color = step.get('color', step.get('color_start', last))
                trans_fn = effects.TRANSITIONS.get(transition_name, effects.transition_fade)
                trans_fn(
                    strip,
                    from_color,
                    to_color,
                    step.get('transition_duration', 2),
                    **effects._transition_kwargs(step),
                )
                if effects.is_cancelled():
                    break

            effect_name = step.get('effect', 'solid')
            effect_fn = effects.EFFECTS.get(effect_name, effects.effect_solid)
            effect_fn(strip, **effects._effect_kwargs(step))

            last = step.get('color', step.get('color_end', last))
    finally:
        with status_lock:
            status.update(_idle_status())


def _start_scene(scene_data):
    """Launch a scene in a background thread. Returns (ok, error_message)."""
    global scene_thread
    with status_lock:
        if scene_thread is not None and scene_thread.is_alive():
            return False, 'Scene already running'
        effects.reset_cancel()
        scene_thread = threading.Thread(target=run_scene_thread, args=(scene_data,), daemon=True)
        scene_thread.start()
    return True, None


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
    scenes = []
    for fname in scene_files:
        try:
            with open(os.path.join(SCENES_DIR, fname)) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        scenes.append({
            'filename': fname,
            'name': data.get('name', fname),
            'description': data.get('description', ''),
        })
    return jsonify(scenes)


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


@app.route('/stop', methods=['POST'])
def stop_scene():
    global scene_thread
    with status_lock:
        thread = scene_thread
    if thread is None or not thread.is_alive():
        apply_color(strip, [0, 0, 0])
        return jsonify({'status': 'idle'})
    effects.cancel()
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
    apply_color(strip, [0, 0, 0])
    os._exit(0)


@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
