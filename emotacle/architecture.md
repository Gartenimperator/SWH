# Tentacle Arm Controller — Architecture

```mermaid
classDiagram
    class EventBus {
        -list _queue
        -Event _event
        +emit(event, data)
        +listen() tuple
    }

    class ArmController {
        -EventBus _bus
        -LEDController _led
        -CoordinateController _coord
        -float _nx
        -float _ny
        -int _retension_counter
        -dict _tension_buttons
        +bool debug
        +run()
        +calibrate()
        -_move_loop()
        -_execute_deltas(deltas)
        -_retension()
        -_on_joystick(data)
        -_on_home()
        -_on_motor_select(data)
        -_on_motor_pull(data)
        -_on_motor_release(data)
        -_is_under_tension(motor) bool
    }

    class CoordinateController {
        +float azimuth
        +float elevation
        -dict _motor_positions
        +rotate(delta_degrees) dict
        +tilt(delta_elevation) dict
        +home() dict
        +set_center()
        +get_position() dict
        -_move_to(azimuth, elevation) dict
        -_calculate_ideal_positions(azimuth, elevation) dict
        -_compute_slack_factor(elevation) float
    }

    class LEDController {
        -PWM _r
        -PWM _g
        -PWM _b
        -int _mode_idx
        +current_mode
        +run()
        +set_mode(name)
        +next_mode()
        +stop()
    }

    class Joystick {
        -EventBus _bus
        -ADC adc_x
        -ADC adc_y
        -Pin sw
        +float nx
        +float ny
        +bool pressed
        +run()
        -_read_adc(adc) int
        -_normalize(raw) float
    }

    class Gamepad {
        -EventBus _bus
        -I2C i2c
        -str selected_motor
        +run()
        +get_single_pressed() str
    }

    class StepperMotor {
        +str name
        -Pin dir
        -StateMachine sm
        +set_direction(direction)
        +step_async(steps, delay_us)
        +pulse(delay_us)
    }

    class config {
        <<module>>
        MOTOR_ANGLES : x=0° y=120° z=240°
        
        CLOCKWISE : 0
COUNTERCLOCKWISE : 1

STEPS_PER_REV      : 200   
DEFAULT_SPEED_US   : 2000   
INTERLACE_STEP_SIZE : 10 
        ... and more
    }

    ArmController --> EventBus : listens
    ArmController --> LEDController : controls
    ArmController --> CoordinateController : owns
    ArmController ..> StepperMotor : uses via motors module

    Joystick --> EventBus : emits
    Gamepad --> EventBus : emits
```

## Event Flow

```mermaid
sequenceDiagram
    participant J as Joystick
    participant G as Gamepad
    participant B as EventBus
    participant A as ArmController
    participant C as CoordinateController
    participant M as motors module

    J->>B: emit(joystick, {nx, ny})
    G->>B: emit(home / debug_toggle)
    G->>B: emit(motor_select / motor_pull / motor_release)

    B->>A: listen() → event, data
    A->>C: tilt(delta) or rotate(delta)
    C-->>A: motor step deltas dict
    A->>M: move_multiple_steppers(deltas)
```

## Module Overview

| File | Purpose |
|---|---|
| `main.py` | Entry point — wires all components together and starts asyncio tasks |
| `arm_controller.py` | Top-level control logic, joystick/gamepad event handling, retension |
| `coordinate_controller.py` | Spherical coordinate math, motor position tracking |
| `motors.py` | PIO-based stepper motor driver (`StepperMotor`) and module-level move functions |
| `led_controller.py` | Async RGB LED with switchable animation modes |
| `joystick_controller.py` | Reads analog joystick, emits `joystick` events |
| `touchpad_controller.py` | Reads I2C gamepad buttons, emits control events |
| `event_bus.py` | Async queue connecting input controllers to `ArmController` |
| `config.py` | All pin assignments, tuning constants, and motor geometry |
