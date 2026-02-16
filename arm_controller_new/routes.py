# API Routes and HTML Interface for Tentacle Arm Controller
# Handles HTTP endpoints and serves the web UI

import json
from motors import move_stepper, move_multiple_steppers
from webserver import get_wifi_status
from config import (DEFAULT_SPEED_US, DEFAULT_STEPS, INTERLACE_STEP_SIZE,
                    MIN_SPEED_US, MAX_SPEED_US, ROTATION_STEP_DEGREES, ELEVATION_STEP_UNITS)
from coordinate_controller import get_controller


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
    elif path == '/api/rotate' and method == 'POST':
        return handle_rotate(request)
    elif path == '/api/tilt' and method == 'POST':
        return handle_tilt(request)
    elif path == '/api/position' and method == 'GET':
        return handle_position()
    elif path == '/api/home' and method == 'POST':
        return handle_home(request)
    elif path == '/api/set-center' and method == 'POST':
        return handle_set_center(request)
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


def handle_rotate(request):
    """Handle rotation in coordinate mode.

    Request body JSON:
    {
        "delta": 15,    // degrees to rotate (positive = left, negative = right)
        "speed": 1000   // optional motor speed
    }
    """
    try:
        data = json.loads(request['body'])
        delta = float(data.get('delta', ROTATION_STEP_DEGREES))
        speed = int(data.get('speed', DEFAULT_SPEED_US))

        controller = get_controller()
        deltas = controller.rotate(delta)

        # Execute motor movements
        _execute_motor_deltas(deltas, speed)

        position = controller.get_position()
        return (200, 'application/json', json.dumps({
            'success': True,
            'azimuth': position['azimuth'],
            'elevation': position['elevation'],
            'slack_factor': position['slack_factor'],
            'deltas': deltas
        }))

    except Exception as e:
        return (400, 'application/json', json.dumps({'error': str(e)}))


def handle_tilt(request):
    """Handle tilt (elevation change) in coordinate mode.

    Request body JSON:
    {
        "delta": 10,    // elevation change (positive = more tilt, negative = less)
        "speed": 1000   // optional motor speed
    }
    """
    try:
        data = json.loads(request['body'])
        delta = float(data.get('delta', ELEVATION_STEP_UNITS))
        speed = int(data.get('speed', DEFAULT_SPEED_US))

        controller = get_controller()
        deltas = controller.tilt(delta)

        # Execute motor movements
        _execute_motor_deltas(deltas, speed)

        position = controller.get_position()
        return (200, 'application/json', json.dumps({
            'success': True,
            'azimuth': position['azimuth'],
            'elevation': position['elevation'],
            'slack_factor': position['slack_factor'],
            'deltas': deltas
        }))

    except Exception as e:
        return (400, 'application/json', json.dumps({'error': str(e)}))


def handle_position():
    """Return current coordinate position."""
    controller = get_controller()
    position = controller.get_position()
    return (200, 'application/json', json.dumps(position))


def handle_home(request):
    """Return tentacle to center position.

    Request body JSON:
    {
        "speed": 1000   // optional motor speed
    }
    """
    try:
        data = json.loads(request['body']) if request['body'] else {}
        speed = int(data.get('speed', DEFAULT_SPEED_US))

        controller = get_controller()
        deltas = controller.home()

        # Execute motor movements
        _execute_motor_deltas(deltas, speed)

        position = controller.get_position()
        return (200, 'application/json', json.dumps({
            'success': True,
            'azimuth': position['azimuth'],
            'elevation': position['elevation'],
            'slack_factor': position['slack_factor'],
            'deltas': deltas
        }))

    except Exception as e:
        return (400, 'application/json', json.dumps({'error': str(e)}))


def handle_set_center(request):
    """Set current physical position as the new center/origin.

    Called after manual calibration to mark the current position as (0, 0).
    """
    try:
        controller = get_controller()
        controller.set_center()

        return (200, 'application/json', json.dumps({
            'success': True,
            'message': 'Center position set',
            'azimuth': 0,
            'elevation': 0
        }))

    except Exception as e:
        return (400, 'application/json', json.dumps({'error': str(e)}))


def _execute_motor_deltas(deltas, speed):
    """Execute motor movements based on position deltas.

    Args:
        deltas: Dict of motor step deltas {'x': int, 'y': int, 'z': int}
        speed: Motor speed in microseconds
    """
    motor_args = []
    for motor_id, delta in deltas.items():
        if delta != 0:
            motor_args.append({
                'id': motor_id,
                'direction': 1 if delta > 0 else 0,
                'steps': abs(delta)
            })

    if motor_args:
        move_multiple_steppers(motor_args, speed)


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

        /* Tab Navigation */
        .tab-nav {
            display: flex;
            gap: 5px;
            margin-bottom: 20px;
        }
        .tab-btn {
            flex: 1;
            padding: 12px 20px;
            background: #16213e;
            border: 2px solid #0f3460;
            border-radius: 10px 10px 0 0;
            color: #888;
            font-size: 1em;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.2s;
        }
        .tab-btn.active {
            background: #0f3460;
            border-color: #00d4ff;
            color: #00d4ff;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }

        /* Motor Cards (Calibration Mode) */
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

        /* Settings Panel */
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
        .setting-row select {
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

        /* Buttons */
        .run-btn, .action-btn {
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
        .run-btn:hover, .action-btn:hover {
            box-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
        }
        .run-btn:active, .action-btn:active {
            transform: scale(0.98);
        }
        .run-btn:disabled, .action-btn:disabled {
            background: #444;
            cursor: not-allowed;
        }
        .set-center-btn {
            background: linear-gradient(135deg, #f39c12, #e74c3c);
            margin-top: 20px;
        }

        /* Coordinate Mode Controls */
        .coord-controls {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
            margin-bottom: 20px;
        }
        .coord-row {
            display: flex;
            gap: 10px;
            justify-content: center;
        }
        .coord-btn {
            width: 80px;
            height: 80px;
            border: none;
            border-radius: 15px;
            font-size: 1.5em;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.1s, box-shadow 0.1s;
        }
        .coord-btn:active {
            transform: scale(0.95);
        }
        .coord-btn:hover {
            box-shadow: 0 0 15px rgba(0, 212, 255, 0.4);
        }
        .coord-up {
            background: linear-gradient(135deg, #00d4ff, #0f3460);
            color: white;
        }
        .coord-down {
            background: linear-gradient(135deg, #e94560, #0f3460);
            color: white;
        }
        .coord-left, .coord-right {
            background: linear-gradient(135deg, #16213e, #0f3460);
            color: #00d4ff;
            border: 2px solid #00d4ff;
        }
        .coord-spacer {
            width: 80px;
            height: 80px;
        }

        /* Position Display */
        .position-display {
            background: #16213e;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
            text-align: center;
        }
        .position-display h3 {
            color: #00d4ff;
            margin-bottom: 10px;
        }
        .position-values {
            display: flex;
            justify-content: center;
            gap: 30px;
        }
        .position-item {
            text-align: center;
        }
        .position-item .label {
            font-size: 0.9em;
            color: #888;
        }
        .position-item .value {
            font-size: 1.5em;
            font-weight: bold;
            color: #00d4ff;
        }

        /* Home Button */
        .home-btn {
            background: linear-gradient(135deg, #27ae60, #16a085);
            margin-top: 10px;
        }

        /* Status */
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

        /* Controller Tab */
        .ws-indicator {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 15px;
            font-size: 0.9em;
        }
        .ws-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #e94560;
            transition: background 0.3s;
        }
        .ws-dot.connected {
            background: #27ae60;
        }
        .controller-section {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 20px;
        }
        .slider-area {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 30px;
        }
        .slider-track {
            position: relative;
            background: #16213e;
            border: 2px solid #0f3460;
            border-radius: 10px;
            touch-action: none;
            user-select: none;
        }
        .slider-track.vertical {
            width: 60px;
            height: 250px;
        }
        .slider-track.horizontal {
            width: 280px;
            height: 60px;
        }
        .slider-thumb {
            position: absolute;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: linear-gradient(135deg, #00d4ff, #0f3460);
            border: 2px solid #00d4ff;
            cursor: grab;
            touch-action: none;
            transition: none;
        }
        .slider-thumb.snap {
            transition: top 0.2s ease-out, left 0.2s ease-out;
        }
        .slider-thumb:active {
            cursor: grabbing;
        }
        .slider-group {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 6px;
        }
        .slider-label {
            font-size: 0.8em;
            color: #888;
            text-align: center;
        }
        .slider-end-labels {
            display: flex;
            justify-content: space-between;
            font-size: 0.75em;
            color: #666;
        }
        .slider-end-labels.vertical {
            flex-direction: column;
            height: 250px;
        }
        .slider-end-labels.horizontal {
            width: 280px;
        }
        .slider-with-labels {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .ctrl-home-btn {
            padding: 15px 40px;
            background: linear-gradient(135deg, #27ae60, #16a085);
            border: none;
            border-radius: 10px;
            color: white;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.1s, box-shadow 0.1s;
        }
        .ctrl-home-btn:hover {
            box-shadow: 0 0 20px rgba(39, 174, 96, 0.5);
        }
        .ctrl-home-btn:active {
            transform: scale(0.95);
        }
        .ctrl-home-btn:disabled {
            background: #444;
            cursor: not-allowed;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Tentacle Arm Controller</h1>

        <!-- Tab Navigation -->
        <div class="tab-nav">
            <button class="tab-btn active" onclick="switchTab('calibration')">Calibration</button>
            <button class="tab-btn" onclick="switchTab('coordinate')">Coordinate Mode</button>
            <button class="tab-btn" onclick="switchTab('controller')">Controller</button>
        </div>

        <!-- Calibration Tab -->
        <div id="tab-calibration" class="tab-content active">
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

            <button class="action-btn set-center-btn" onclick="setCenter()">Set as Center</button>
        </div>

        <!-- Coordinate Mode Tab -->
        <div id="tab-coordinate" class="tab-content">
            <div class="position-display">
                <h3>Current Position</h3>
                <div class="position-values">
                    <div class="position-item">
                        <div class="label">Azimuth</div>
                        <div class="value" id="azimuth-value">0</div>
                    </div>
                    <div class="position-item">
                        <div class="label">Elevation</div>
                        <div class="value" id="elevation-value">0</div>
                    </div>
                </div>
            </div>

            <div class="coord-controls">
                <div class="coord-row">
                    <div class="coord-spacer"></div>
                    <button class="coord-btn coord-up" onclick="tilt(1)">UP</button>
                    <div class="coord-spacer"></div>
                </div>
                <div class="coord-row">
                    <button class="coord-btn coord-left" onclick="rotate(1)">LEFT</button>
                    <div class="coord-spacer"></div>
                    <button class="coord-btn coord-right" onclick="rotate(-1)">RIGHT</button>
                </div>
                <div class="coord-row">
                    <div class="coord-spacer"></div>
                    <button class="coord-btn coord-down" onclick="tilt(-1)">DOWN</button>
                    <div class="coord-spacer"></div>
                </div>
            </div>

            <button class="action-btn home-btn" onclick="goHome()">HOME</button>

            <div class="settings-panel" style="margin-top: 20px;">
                <div class="setting-row">
                    <label>Rotation Step:</label>
                    <input type="number" id="rotation-step" value="15" min="1" max="360">
                </div>
                <div class="setting-row">
                    <label>Elevation Step:</label>
                    <input type="number" id="elevation-step" value="10" min="1" max="30">
                </div>
                <div class="setting-row">
                    <label>Slack Factor:</label>
                    <span id="coord-slack-display" style="font-size:1.2em; color:#00d4ff; font-weight:bold;">0.60</span>
                    <span style="color:#888; font-size:0.85em;">(auto: decreases with elevation)</span>
                </div>
                <div class="setting-row">
                    <label>Speed (us):</label>
                    <input type="range" id="coord-speed-slider" min="100" max="5000" value="1000">
                    <input type="number" id="coord-speed-value" value="1000" min="100" max="5000">
                </div>
                <div class="speed-labels">
                    <span>Fast (100us)</span>
                    <span>Slow (5000us)</span>
                </div>
            </div>
        </div>

        <!-- Controller Tab -->
        <div id="tab-controller" class="tab-content">
            <div class="ws-indicator">
                <div class="ws-dot" id="ws-dot"></div>
                <span id="ws-status-text">Disconnected</span>
            </div>

            <div class="position-display">
                <h3>Position</h3>
                <div class="position-values">
                    <div class="position-item">
                        <div class="label">Azimuth</div>
                        <div class="value" id="ctrl-azimuth">--</div>
                    </div>
                    <div class="position-item">
                        <div class="label">Elevation</div>
                        <div class="value" id="ctrl-elevation">--</div>
                    </div>
                </div>
            </div>

            <div class="controller-section">
                <!-- Tilt (vertical) slider -->
                <div class="slider-group">
                    <div class="slider-label">Tilt</div>
                    <div class="slider-with-labels">
                        <div class="slider-end-labels vertical">
                            <span>UP</span>
                            <span>DOWN</span>
                        </div>
                        <div class="slider-track vertical" id="tilt-track">
                            <div class="slider-thumb" id="tilt-thumb"></div>
                        </div>
                    </div>
                </div>

                <!-- Rotation (horizontal) slider -->
                <div class="slider-group">
                    <div class="slider-label">Rotation</div>
                    <div class="slider-track horizontal" id="rotate-track">
                        <div class="slider-thumb" id="rotate-thumb"></div>
                    </div>
                    <div class="slider-end-labels horizontal">
                        <span>LEFT</span>
                        <span>RIGHT</span>
                    </div>
                </div>

                <button class="ctrl-home-btn" id="ctrl-home-btn" onclick="ctrlHome()">HOME</button>

                <div class="settings-panel" style="width:100%;">
                    <div class="setting-row">
                        <label>Slack Factor:</label>
                        <span id="ctrl-slack-display" style="font-size:1.2em; color:#00d4ff; font-weight:bold;">0.60</span>
                        <span style="color:#888; font-size:0.85em;">(auto)</span>
                    </div>
                    <div class="setting-row">
                        <label>Speed (us):</label>
                        <input type="range" id="ctrl-speed-slider" min="100" max="5000" value="1000">
                        <input type="number" id="ctrl-speed-value" value="1000" min="100" max="5000">
                    </div>
                    <div class="speed-labels">
                        <span>Fast (100us)</span>
                        <span>Slow (5000us)</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="status" id="status">Ready</div>
    </div>

    <script>
        // Tab switching
        let activeTab = 'calibration';
        function switchTab(tabName) {
            // Disconnect WS when leaving controller tab
            if (activeTab === 'controller' && tabName !== 'controller') {
                disconnectWS();
            }

            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

            document.querySelector('.tab-btn[onclick*="' + tabName + '"]').classList.add('active');
            document.getElementById('tab-' + tabName).classList.add('active');
            activeTab = tabName;

            if (tabName === 'coordinate') {
                updatePositionDisplay();
            }
            if (tabName === 'controller') {
                connectWS();
            }
        }

        // Sync slider and number inputs
        const speedSlider = document.getElementById('speed-slider');
        const speedValue = document.getElementById('speed-value');
        speedSlider.oninput = () => speedValue.value = speedSlider.value;
        speedValue.oninput = () => speedSlider.value = speedValue.value;

        const coordSpeedSlider = document.getElementById('coord-speed-slider');
        const coordSpeedValue = document.getElementById('coord-speed-value');
        coordSpeedSlider.oninput = () => coordSpeedValue.value = coordSpeedSlider.value;
        coordSpeedValue.oninput = () => coordSpeedSlider.value = coordSpeedValue.value;

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

        function updatePositionDisplay() {
            fetch('/api/position')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('azimuth-value').textContent = Math.round(data.azimuth) + '\u00B0';
                    document.getElementById('elevation-value').textContent = Math.round(data.elevation);
                })
                .catch(e => console.error('Failed to fetch position:', e));
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

        async function setCenter() {
            setStatus('Setting center position...');
            try {
                const res = await fetch('/api/set-center', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: '{}'
                });
                const data = await res.json();
                if (data.success) {
                    setStatus('Center position set!', 'success');
                    updatePositionDisplay();
                } else {
                    setStatus('Failed: ' + (data.error || 'Unknown error'), 'error');
                }
            } catch (e) {
                setStatus('Error: ' + e.message, 'error');
            }
        }

        async function rotate(direction) {
            const step = parseInt(document.getElementById('rotation-step').value);
            const delta = step * direction;
            setStatus('Rotating ' + (direction > 0 ? 'left' : 'right') + '...');
            try {
                const res = await fetch('/api/rotate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        delta: delta,
                        speed: parseInt(coordSpeedValue.value)
                    })
                });
                const data = await res.json();
                if (data.success) {
                    document.getElementById('azimuth-value').textContent = Math.round(data.azimuth) + '\u00B0';
                    document.getElementById('elevation-value').textContent = Math.round(data.elevation);
                    if (data.slack_factor !== undefined) document.getElementById('coord-slack-display').textContent = data.slack_factor.toFixed(2);
                    setStatus('Rotation complete', 'success');
                } else {
                    setStatus('Failed: ' + (data.error || 'Unknown error'), 'error');
                }
            } catch (e) {
                setStatus('Error: ' + e.message, 'error');
            }
        }

        async function tilt(direction) {
            const step = parseInt(document.getElementById('elevation-step').value);
            const delta = step * direction;
            setStatus('Tilting ' + (direction > 0 ? 'up' : 'down') + '...');
            try {
                const res = await fetch('/api/tilt', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        delta: delta,
                        speed: parseInt(coordSpeedValue.value)
                    })
                });
                const data = await res.json();
                if (data.success) {
                    document.getElementById('azimuth-value').textContent = Math.round(data.azimuth) + '\u00B0';
                    document.getElementById('elevation-value').textContent = Math.round(data.elevation);
                    if (data.slack_factor !== undefined) document.getElementById('coord-slack-display').textContent = data.slack_factor.toFixed(2);
                    setStatus('Tilt complete', 'success');
                } else {
                    setStatus('Failed: ' + (data.error || 'Unknown error'), 'error');
                }
            } catch (e) {
                setStatus('Error: ' + e.message, 'error');
            }
        }

        async function goHome() {
            setStatus('Returning to center...');
            try {
                const res = await fetch('/api/home', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        speed: parseInt(coordSpeedValue.value)
                    })
                });
                const data = await res.json();
                if (data.success) {
                    document.getElementById('azimuth-value').textContent = Math.round(data.azimuth) + '\u00B0';
                    document.getElementById('elevation-value').textContent = Math.round(data.elevation);
                    if (data.slack_factor !== undefined) document.getElementById('coord-slack-display').textContent = data.slack_factor.toFixed(2);
                    setStatus('Returned to center', 'success');
                } else {
                    setStatus('Failed: ' + (data.error || 'Unknown error'), 'error');
                }
            } catch (e) {
                setStatus('Error: ' + e.message, 'error');
            }
        }

        // Sync controller speed slider
        const ctrlSpeedSlider = document.getElementById('ctrl-speed-slider');
        const ctrlSpeedValue = document.getElementById('ctrl-speed-value');
        ctrlSpeedSlider.oninput = () => ctrlSpeedValue.value = ctrlSpeedSlider.value;
        ctrlSpeedValue.oninput = () => ctrlSpeedSlider.value = ctrlSpeedValue.value;

        // === WebSocket Controller ===
        let ws = null;
        let wsReconnectTimer = null;

        function connectWS() {
            if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
            const host = window.location.hostname + ':' + window.location.port;
            ws = new WebSocket('ws://' + host + '/ws');

            ws.onopen = function() {
                document.getElementById('ws-dot').classList.add('connected');
                document.getElementById('ws-status-text').textContent = 'Connected';
            };

            ws.onclose = function() {
                document.getElementById('ws-dot').classList.remove('connected');
                document.getElementById('ws-status-text').textContent = 'Disconnected';
                ws = null;
                // Auto-reconnect if still on controller tab
                if (activeTab === 'controller') {
                    wsReconnectTimer = setTimeout(connectWS, 2000);
                }
            };

            ws.onerror = function() {
                ws.close();
            };

            ws.onmessage = function(ev) {
                try {
                    const msg = JSON.parse(ev.data);
                    if (msg.type === 'state' || msg.type === 'position' || msg.type === 'stopped' || msg.type === 'homed') {
                        if (msg.azimuth !== undefined) {
                            document.getElementById('ctrl-azimuth').textContent = Math.round(msg.azimuth) + '\u00B0';
                        }
                        if (msg.elevation !== undefined) {
                            document.getElementById('ctrl-elevation').textContent = Math.round(msg.elevation);
                        }
                        if (msg.slack_factor !== undefined) {
                            document.getElementById('ctrl-slack-display').textContent = msg.slack_factor.toFixed(2);
                        }
                    }
                } catch(e) {}
            };
        }

        function disconnectWS() {
            if (wsReconnectTimer) { clearTimeout(wsReconnectTimer); wsReconnectTimer = null; }
            if (ws) {
                ws.close();
                ws = null;
            }
        }

        function wsSend(obj) {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify(obj));
            }
        }

        // Safety: disconnect on page unload
        window.addEventListener('beforeunload', function() {
            disconnectWS();
        });

        // === Slider Drag Logic ===
        function setupSlider(trackId, thumbId, axis, actionName) {
            const track = document.getElementById(trackId);
            const thumb = document.getElementById(thumbId);
            const isVertical = axis === 'vertical';
            let dragging = false;
            let currentDirection = null;
            const deadzone = 15; // pixels from center before triggering

            function centerThumb() {
                thumb.classList.add('snap');
                if (isVertical) {
                    thumb.style.top = (track.clientHeight / 2 - thumb.clientHeight / 2) + 'px';
                    thumb.style.left = (track.clientWidth / 2 - thumb.clientWidth / 2) + 'px';
                } else {
                    thumb.style.left = (track.clientWidth / 2 - thumb.clientWidth / 2) + 'px';
                    thumb.style.top = (track.clientHeight / 2 - thumb.clientHeight / 2) + 'px';
                }
                setTimeout(function() { thumb.classList.remove('snap'); }, 200);
            }

            // Initial position
            centerThumb();

            thumb.addEventListener('pointerdown', function(e) {
                e.preventDefault();
                dragging = true;
                thumb.setPointerCapture(e.pointerId);
                thumb.classList.remove('snap');
            });

            thumb.addEventListener('pointermove', function(e) {
                if (!dragging) return;
                e.preventDefault();

                const rect = track.getBoundingClientRect();
                const thumbSize = isVertical ? thumb.clientHeight : thumb.clientWidth;
                const trackSize = isVertical ? rect.height : rect.width;
                const center = trackSize / 2;

                if (isVertical) {
                    let y = e.clientY - rect.top - thumbSize / 2;
                    y = Math.max(0, Math.min(trackSize - thumbSize, y));
                    thumb.style.top = y + 'px';
                    thumb.style.left = (track.clientWidth / 2 - thumb.clientWidth / 2) + 'px';

                    const displacement = (center - thumbSize / 2) - y; // positive = up
                    handleDisplacement(displacement);
                } else {
                    let x = e.clientX - rect.left - thumbSize / 2;
                    x = Math.max(0, Math.min(trackSize - thumbSize, x));
                    thumb.style.left = x + 'px';
                    thumb.style.top = (track.clientHeight / 2 - thumb.clientHeight / 2) + 'px';

                    const displacement = x - (center - thumbSize / 2); // positive = right
                    handleDisplacement(displacement);
                }
            });

            function handleDisplacement(displacement) {
                let newDir = null;
                if (displacement > deadzone) {
                    newDir = 1;
                } else if (displacement < -deadzone) {
                    newDir = -1;
                }

                if (newDir !== currentDirection) {
                    // Direction changed
                    if (currentDirection !== null) {
                        wsSend({cmd: 'stop'});
                    }
                    if (newDir !== null) {
                        wsSend({
                            cmd: 'start',
                            action: actionName,
                            direction: newDir,
                            speed: parseInt(ctrlSpeedValue.value)
                        });
                    }
                    currentDirection = newDir;
                }
            }

            function release(e) {
                if (!dragging) return;
                dragging = false;

                if (currentDirection !== null) {
                    wsSend({cmd: 'stop'});
                    currentDirection = null;
                }
                centerThumb();
            }

            thumb.addEventListener('pointerup', release);
            thumb.addEventListener('pointercancel', release);
        }

        // Initialize sliders after DOM is ready
        setupSlider('tilt-track', 'tilt-thumb', 'vertical', 'tilt');
        setupSlider('rotate-track', 'rotate-thumb', 'horizontal', 'rotate');

        // Home button for controller tab
        function ctrlHome() {
            wsSend({cmd: 'home', speed: parseInt(ctrlSpeedValue.value)});
        }

        // Initial position load
        updatePositionDisplay();
    </script>
</body>
</html>
"""
