# app.py
from flask import Flask, render_template, request, jsonify
from effects import apply_scene
from controller.led_driver import init_strip, apply_color, apply_fade, cleanup
import json
import atexit
import signal

app = Flask(__name__)

# Initialize LED strip
try:
    strip = init_strip()
except Exception as e:
    print(f"Failed to initialize LED strip: {e}")
    strip = None

def cleanup_handler(signum=None, frame=None):
    """Clean up LED strip on exit."""
    print("Cleaning up...")
    try:
        cleanup()
    except Exception as e:
        print(f"Error during cleanup: {e}")

# Register cleanup handlers
atexit.register(cleanup_handler)
signal.signal(signal.SIGTERM, cleanup_handler)
signal.signal(signal.SIGINT, cleanup_handler)

@app.route('/')
def index():
    """Serve the main web interface."""
    return render_template('index.html')

@app.route('/set_color', methods=['POST'])
def set_color():
    """Set a solid color for all LEDs."""
    if not strip:
        return jsonify(status='error', message='LED strip not initialized'), 500
    
    try:
        data = request.json
        color = data.get('color', [255, 255, 255])
        # Validate color values
        if not all(isinstance(c, (int, float)) and 0 <= c <= 255 for c in color):
            return jsonify(status='error', message='Invalid color values'), 400
        
        apply_color(color)
        return jsonify(status='ok')
    except Exception as e:
        return jsonify(status='error', message=str(e)), 500

@app.route('/fade', methods=['POST'])
def fade():
    """Create a fade effect between two colors."""
    if not strip:
        return jsonify(status='error', message='LED strip not initialized'), 500
    
    try:
        data = request.json
        start = data.get('start', [0, 0, 0])
        end = data.get('end', [255, 255, 255])
        duration = float(data.get('duration', 1.0))
        
        # Validate inputs
        if not all(isinstance(c, (int, float)) and 0 <= c <= 255 
                  for c in start + end):
            return jsonify(status='error', message='Invalid color values'), 400
        if not 0 < duration <= 10:  # Limit duration to reasonable range
            return jsonify(status='error', message='Invalid duration'), 400
            
        apply_fade(start, end, duration)
        return jsonify(status='ok')
    except Exception as e:
        return jsonify(status='error', message=str(e)), 500

@app.route('/apply_scene', methods=['POST'])
def scene():
    """Apply a predefined scene."""
    if not strip:
        return jsonify(status='error', message='LED strip not initialized'), 500
    
    try:
        data = request.json
        apply_scene(data)
        return jsonify(status='ok')
    except Exception as e:
        return jsonify(status='error', message=str(e)), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
