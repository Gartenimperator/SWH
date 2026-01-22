# API Routes and HTML Interface for Tentacle Arm Controller
# Handles HTTP endpoints and serves the web UI

import json
from motors import move_stepper, move_multiple_steppers
from webserver import get_wifi_status
from config import DEFAULT_SPEED_US, DEFAULT_STEPS, INTERLACE_STEP_SIZE, MIN_SPEED_US, MAX_SPEED_US


def route_request(request):
    """Route HTTP request to appropriate handler.

    Args:
        request: Dict with method, path, headers, body

    Returns:
        Tuple of (status_code, content_type, body)
    """
    path = request['path'].split('?')[0]  # Remove query string
    method = request['method']

    # Route table
    if path == '/' and method == 'GET':
        return handle_index()
    elif path == '/api/move' and method == 'POST':
        return handle_move(request)
    elif path == '/api/jog' and method == 'POST':
        return handle_jog(request)
    elif path == '/api/status' and method == 'GET':
        return handle_status()
    else:
        return (404, 'text/plain', 'Not Found')


def handle_index():
    """Serve the HTML interface."""
    return (200, 'text/html', HTML_INTERFACE)


def handle_move(request):
    """Handle multi-motor coordinated movement.

    Request body JSON:
    {
        "motors": [{"id": "x", "direction": 1, "steps": 200}, ...],
        "speed": 1000,
        "interlace": 10
    }
    """
    try:
        data = json.loads(request['body'])
        motors = data.get('motors', [])
        speed = int(data.get('speed', DEFAULT_SPEED_US))
        interlace = int(data.get('interlace', INTERLACE_STEP_SIZE))

        if not motors:
            return (400, 'application/json', json.dumps({'error': 'No motors specified'}))

        # Validate and convert motor args
        motor_args = []
        for m in motors:
            motor_args.append({
                'id': m['id'],
                'direction': int(m['direction']),
                'steps': int(m['steps'])
            })

        success = move_multiple_steppers(motor_args, speed, interlace)

        return (200, 'application/json', json.dumps({
            'success': success,
            'motors': len(motor_args),
            'speed': speed,
            'interlace': interlace
        }))

    except Exception as e:
        return (400, 'application/json', json.dumps({'error': str(e)}))


def handle_jog(request):
    """Handle single motor jog (left/right buttons).

    Request body JSON:
    {
        "motor": "x",
        "direction": 1,
        "steps": 50,
        "speed": 1000
    }
    """
    try:
        data = json.loads(request['body'])
        motor_id = data.get('motor', 'x')
        direction = int(data.get('direction', 1))
        steps = int(data.get('steps', DEFAULT_STEPS))
        speed = int(data.get('speed', DEFAULT_SPEED_US))

        success = move_stepper(motor_id, direction, speed, steps)

        return (200, 'application/json', json.dumps({
            'success': success,
            'motor': motor_id,
            'direction': direction,
            'steps': steps
        }))

    except Exception as e:
        return (400, 'application/json', json.dumps({'error': str(e)}))


def handle_status():
    """Return system status."""
    status = get_wifi_status()
    return (200, 'application/json', json.dumps(status))


# Embedded HTML Interface
HTML_INTERFACE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tentacle Arm Controller</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }
        h1 {
            text-align: center;
            margin-bottom: 20px;
            color: #00d4ff;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        .motor-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .motor-card {
            background: #16213e;
            border-radius: 10px;
            padding: 15px;
            border: 2px solid #0f3460;
        }
        .motor-card.enabled {
            border-color: #00d4ff;
        }
        .motor-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
        }
        .motor-header input[type="checkbox"] {
            width: 20px;
            height: 20px;
            accent-color: #00d4ff;
        }
        .motor-header h3 {
            font-size: 1.2em;
            color: #00d4ff;
        }
        .motor-options {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .direction-group {
            display: flex;
            gap: 15px;
        }
        .direction-group label {
            display: flex;
            align-items: center;
            gap: 5px;
            cursor: pointer;
        }
        .direction-group input[type="radio"] {
            accent-color: #00d4ff;
        }
        .steps-input {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .steps-input label {
            min-width: 50px;
        }
        .steps-input input {
            flex: 1;
            padding: 8px;
            border: 1px solid #0f3460;
            border-radius: 5px;
            background: #1a1a2e;
            color: #eee;
            font-size: 1em;
        }
        .jog-buttons {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }
        .jog-btn {
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            transition: transform 0.1s;
        }
        .jog-btn:active {
            transform: scale(0.95);
        }
        .jog-left {
            background: #e94560;
            color: white;
        }
        .jog-right {
            background: #0f3460;
            color: white;
        }
        .settings-panel {
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .setting-row {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 15px;
        }
        .setting-row:last-child {
            margin-bottom: 0;
        }
        .setting-row label {
            min-width: 120px;
        }
        .setting-row input[type="range"] {
            flex: 1;
            accent-color: #00d4ff;
        }
        .setting-row input[type="number"] {
            width: 100px;
            padding: 8px;
            border: 1px solid #0f3460;
            border-radius: 5px;
            background: #1a1a2e;
            color: #eee;
        }
        .speed-labels {
            display: flex;
            justify-content: space-between;
            font-size: 0.8em;
            color: #888;
            margin-top: 5px;
        }
        .run-btn {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #00d4ff, #0f3460);
            border: none;
            border-radius: 10px;
            color: white;
            font-size: 1.2em;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.1s, box-shadow 0.1s;
        }
        .run-btn:hover {
            box-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
        }
        .run-btn:active {
            transform: scale(0.98);
        }
        .run-btn:disabled {
            background: #444;
            cursor: not-allowed;
        }
        .status {
            text-align: center;
            margin-top: 15px;
            padding: 10px;
            border-radius: 5px;
            background: #0f3460;
            font-size: 0.9em;
        }
        .status.success { background: #1b4332; }
        .status.error { background: #5c1a1a; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Tentacle Arm Controller</h1>

        <div class="motor-cards">
            <div class="motor-card" id="motor-x">
                <div class="motor-header">
                    <input type="checkbox" id="enable-x">
                    <h3>Motor X</h3>
                </div>
                <div class="motor-options">
                    <div class="direction-group">
                        <label><input type="radio" name="dir-x" value="1" checked> CW</label>
                        <label><input type="radio" name="dir-x" value="0"> CCW</label>
                    </div>
                    <div class="steps-input">
                        <label>Steps:</label>
                        <input type="number" id="steps-x" value="200" min="1" max="10000">
                    </div>
                    <div class="jog-buttons">
                        <button class="jog-btn jog-left" onclick="jog('x', 0)">Left</button>
                        <button class="jog-btn jog-right" onclick="jog('x', 1)">Right</button>
                    </div>
                </div>
            </div>

            <div class="motor-card" id="motor-y">
                <div class="motor-header">
                    <input type="checkbox" id="enable-y">
                    <h3>Motor Y</h3>
                </div>
                <div class="motor-options">
                    <div class="direction-group">
                        <label><input type="radio" name="dir-y" value="1" checked> CW</label>
                        <label><input type="radio" name="dir-y" value="0"> CCW</label>
                    </div>
                    <div class="steps-input">
                        <label>Steps:</label>
                        <input type="number" id="steps-y" value="200" min="1" max="10000">
                    </div>
                    <div class="jog-buttons">
                        <button class="jog-btn jog-left" onclick="jog('y', 0)">Left</button>
                        <button class="jog-btn jog-right" onclick="jog('y', 1)">Right</button>
                    </div>
                </div>
            </div>

            <div class="motor-card" id="motor-z">
                <div class="motor-header">
                    <input type="checkbox" id="enable-z">
                    <h3>Motor Z</h3>
                </div>
                <div class="motor-options">
                    <div class="direction-group">
                        <label><input type="radio" name="dir-z" value="1" checked> CW</label>
                        <label><input type="radio" name="dir-z" value="0"> CCW</label>
                    </div>
                    <div class="steps-input">
                        <label>Steps:</label>
                        <input type="number" id="steps-z" value="200" min="1" max="10000">
                    </div>
                    <div class="jog-buttons">
                        <button class="jog-btn jog-left" onclick="jog('z', 0)">Left</button>
                        <button class="jog-btn jog-right" onclick="jog('z', 1)">Right</button>
                    </div>
                </div>
            </div>
        </div>

        <div class="settings-panel">
            <div class="setting-row">
                <label>Speed (us):</label>
                <input type="range" id="speed-slider" min="100" max="5000" value="1000">
                <input type="number" id="speed-value" value="1000" min="100" max="5000">
            </div>
            <div class="speed-labels">
                <span>Fast (100us)</span>
                <span>Slow (5000us)</span>
            </div>
            <div class="setting-row" style="margin-top: 15px;">
                <label>Interlace Steps:</label>
                <input type="number" id="interlace" value="10" min="1" max="100">
            </div>
        </div>

        <button class="run-btn" onclick="runMotors()">Run Selected Motors</button>

        <div class="status" id="status">Ready</div>
    </div>

    <script>
        // Sync slider and number input
        const speedSlider = document.getElementById('speed-slider');
        const speedValue = document.getElementById('speed-value');
        speedSlider.oninput = () => speedValue.value = speedSlider.value;
        speedValue.oninput = () => speedSlider.value = speedValue.value;

        // Update card styling when enabled
        ['x', 'y', 'z'].forEach(m => {
            const cb = document.getElementById('enable-' + m);
            const card = document.getElementById('motor-' + m);
            cb.onchange = () => card.classList.toggle('enabled', cb.checked);
        });

        function setStatus(msg, type) {
            const el = document.getElementById('status');
            el.textContent = msg;
            el.className = 'status ' + (type || '');
        }

        async function jog(motor, direction) {
            setStatus('Jogging ' + motor.toUpperCase() + '...');
            try {
                const res = await fetch('/api/jog', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        motor: motor,
                        direction: direction,
                        steps: 50,
                        speed: parseInt(speedValue.value)
                    })
                });
                const data = await res.json();
                if (data.success) {
                    setStatus('Jog complete', 'success');
                } else {
                    setStatus('Jog failed: ' + (data.error || 'Unknown error'), 'error');
                }
            } catch (e) {
                setStatus('Error: ' + e.message, 'error');
            }
        }

        async function runMotors() {
            const motors = [];
            ['x', 'y', 'z'].forEach(m => {
                if (document.getElementById('enable-' + m).checked) {
                    const dir = document.querySelector('input[name="dir-' + m + '"]:checked').value;
                    const steps = document.getElementById('steps-' + m).value;
                    motors.push({
                        id: m,
                        direction: parseInt(dir),
                        steps: parseInt(steps)
                    });
                }
            });

            if (motors.length === 0) {
                setStatus('No motors selected', 'error');
                return;
            }

            setStatus('Running ' + motors.length + ' motor(s)...');
            try {
                const res = await fetch('/api/move', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        motors: motors,
                        speed: parseInt(speedValue.value),
                        interlace: parseInt(document.getElementById('interlace').value)
                    })
                });
                const data = await res.json();
                if (data.success) {
                    setStatus('Movement complete', 'success');
                } else {
                    setStatus('Failed: ' + (data.error || 'Unknown error'), 'error');
                }
            } catch (e) {
                setStatus('Error: ' + e.message, 'error');
            }
        }
    </script>
</body>
</html>
"""
