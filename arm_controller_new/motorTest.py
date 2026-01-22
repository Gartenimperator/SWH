from machine import Pin
import time

# Pin definitions
dir_pin_1 = Pin(3, Pin.OUT)
step_pin_1 = Pin(2, Pin.OUT)

dir_pin_2 = Pin(5, Pin.OUT)
step_pin_2 = Pin(4, Pin.OUT)

dir_pin_3 = Pin(7, Pin.OUT)
step_pin_3 = Pin(6, Pin.OUT)
steps_per_revolution = 10
def spin_motor():
    c = 0
    t = True
    while t:
        print("turning")
        c = c + 1
        # Set motor direction clockwise
        dir_pin_1.value(1)
        dir_pin_2.value(0)
        dir_pin_3.value(0)
        t = False
        # Spin motor slowly
        for x in range(steps_per_revolution):
            step_pin_1.value(1)
            if x < 100:
                step_pin_2.value(1)
                step_pin_3.value(1)
            time.sleep_us(2000)
            step_pin_1.value(0)
            if x < 100:
                step_pin_3.value(0)
                step_pin_2.value(0)
            time.sleep_us(2000)

# Run the motor control
spin_motor()