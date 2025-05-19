# app.py
from flask import Flask, render_template, request, jsonify, send_from_directory
from effects import apply_scene
from controller.led_driver import init_strip, apply_color, apply_fade
import json
import os
import threading
import time

app = Flask(__name__)
strip = init_strip()

SCENES_DIR = 'scenes'

# Ensure static directory exists and turrell_colors.json is available
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)
TURRELL_COLORS_SRC = os.path.join(os.path.dirname(__file__), 'turrell_colors.json')
TURRELL_COLORS_DST = os.path.join(STATIC_DIR, 'turrell_colors.json')
if os.path.exists(TURRELL_COLORS_SRC) and not os.path.exists(TURRELL_COLORS_DST):
    import shutil
    shutil.copy(TURRELL_COLORS_SRC, TURRELL_COLORS_DST)

status = {
    'running': False,
    'current_effect': None,
    'current_transition': None,
    'step': 0,
    'total_steps': 0,
    'elapsed': 0,
    'duration': 0,
    'scene': None,
    'narrative': None
}

status_lock = threading.Lock()

# Helper to run scene in a thread
scene_thread = None

def run_scene_thread(scene_data):
    global status
    steps = scene_data.get('steps', [])
    total_steps = len(steps)
    start_time = time.time()
    with status_lock:
        status['running'] = True
        status['scene'] = scene_data.get('name', 'Unnamed')
        status['total_steps'] = total_steps
    last = scene_data.get('last', steps[0].get('color', [0,0,0]) if steps else [0,0,0])
    for idx, step in enumerate(steps):
        with status_lock:
            status['step'] = idx + 1
            status['current_effect'] = step.get('effect', 'solid')
            status['current_transition'] = step.get('transition', 'fade')
            status['elapsed'] = int(time.time() - start_time)
            status['duration'] = int(sum(s.get('duration', 2) + s.get('transition_duration', 0) for s in steps))
            status['narrative'] = step.get('narrative', None)
        # Run transition
        if status['current_transition'] != 'instant':
            from_color = last
            to_color = step.get('color', step.get('color_start', last))
            apply_scene.transition(strip, from_color, to_color, step.get('transition_duration', 2), **{k: v for k, v in step.items() if k not in ("effect", "duration")})
        # Run effect
        apply_scene.effects.get(status['current_effect'], apply_scene.effect_solid)(strip, **{k: v for k, v in step.items() if k not in ("effect", "transition", "transition_duration")})
        last = step.get('color', step.get('color_end', last))
    with status_lock:
        status['running'] = False
        status['current_effect'] = None
        status['current_transition'] = None
        status['step'] = 0
        status['scene'] = None
        status['narrative'] = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/set_color', methods=['POST'])
def set_color():
    data = request.json
    color = data.get('color', [255, 255, 255])
    apply_color(strip, color)
    return jsonify(status='ok')

@app.route('/fade', methods=['POST'])
def fade():
    data = request.json
    start = data['start']
    end = data['end']
    duration = float(data['duration'])
    apply_fade(strip, start, end, duration)
    return jsonify(status='fading')

@app.route('/apply_scene', methods=['POST'])
def scene():
    data = request.json
    apply_scene(strip, data)
    return jsonify(status='scene loaded')

@app.route('/scenes', methods=['GET'])
def list_scenes():
    scene_files = [f for f in os.listdir(SCENES_DIR) if f.endswith('.json')]
    scenes = []
    for fname in scene_files:
        with open(os.path.join(SCENES_DIR, fname)) as f:
            data = json.load(f)
            scenes.append({
                'filename': fname,
                'name': data.get('name', fname),
                'description': data.get('description', '')
            })
    return jsonify(scenes)

@app.route('/apply_scene_file', methods=['POST'])
def apply_scene_file():
    data = request.json
    filename = data.get('filename')
    if not filename:
        return jsonify({'error': 'No filename provided'}), 400
    with open(os.path.join(SCENES_DIR, filename)) as f:
        scene_data = json.load(f)
    apply_scene(strip, scene_data)
    return jsonify({'status': 'scene loaded'})

@app.route('/status', methods=['GET'])
def get_status():
    with status_lock:
        return jsonify(status)

@app.route('/run_effect', methods=['POST'])
def run_effect():
    data = request.json
    effect = data.get('effect')
    params = data.get('params', {})
    if not effect:
        return jsonify({'error': 'No effect provided'}), 400
    fn = getattr(apply_scene, f'effect_{effect}', None)
    if not fn:
        return jsonify({'error': 'Unknown effect'}), 400
    threading.Thread(target=fn, args=(strip,), kwargs=params).start()
    return jsonify({'status': f'{effect} started'})

@app.route('/off', methods=['POST'])
def turn_off():
    apply_color(strip, [0, 0, 0])
    return jsonify({'status': 'off'})

@app.route('/exit', methods=['POST'])
def exit_server():
    apply_color(strip, [0, 0, 0])  # Turn off LEDs before exiting
    os._exit(0)
    return jsonify({'status': 'exiting'})

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
