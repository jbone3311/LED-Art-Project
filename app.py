# app.py
from flask import Flask, render_template, request, jsonify
from effects import apply_scene
from controller.led_driver import init_strip, apply_color, apply_fade
import json

app = Flask(__name__)
strip = init_strip()

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
