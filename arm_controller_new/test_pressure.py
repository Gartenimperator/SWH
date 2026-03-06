# Button test — GP16, GP17, GP18 each wired to GND via a button

from machine import Pin
import utime

buttons = [
    Pin(16, Pin.IN, Pin.PULL_UP),
    Pin(17, Pin.IN, Pin.PULL_UP),
    Pin(18, Pin.IN, Pin.PULL_UP),
]

last_states = [1, 1, 1]


def main():
    print("Button test — GP16, GP17, GP18. Ctrl+C to stop.\n")

    while True:
        for i, btn in enumerate(buttons):
            state = btn.value()
            if state != last_states[i]:
                if state == 0:
                    print(f"Button GP{16 + i} PRESSED")
                last_states[i] = state
        utime.sleep_ms(20)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDone.")
