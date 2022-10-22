#!/usr/bin/python3

import RPi.GPIO as GPIO
import time

PIN_TRIGGER = 7
PIN_ECHO = 11


def get_distance():
    s = 0.00001
    for i in range(10):
        GPIO.output(PIN_TRIGGER, GPIO.HIGH)
        time.sleep(s)
        GPIO.output(PIN_TRIGGER, GPIO.LOW)

        start_time = time.time()
        while True:
            pulse_start_time = time.time()
            if GPIO.input(PIN_ECHO) == 0:
                if (pulse_start_time - start_time) > 0.02:
                    return -1
            else:
                break

        start_time = time.time()
        while True:
            pulse_end_time = time.time()
            if GPIO.input(PIN_ECHO) == 1:
                if (pulse_end_time - start_time) > 0.02:
                    return -1
            else:
                break

        pulse_duration = pulse_end_time - pulse_start_time + s * 1.2
        # 20 C
        return round(pulse_duration * 17178, 3)


try:
    GPIO.setmode(GPIO.BOARD)

    GPIO.setup(PIN_TRIGGER, GPIO.OUT)
    GPIO.setup(PIN_ECHO, GPIO.IN)

    GPIO.output(PIN_TRIGGER, GPIO.LOW)

    print("Waiting for sensor to settle")

    time.sleep(2)

    while True:
        distances = []

        distance = get_distance()
        if distance > 0:
            distance -= 1.68
            distances.append(distance)

        if len(distances) >= 1:
            avg = sum(distances) / len(distances)
            delta = avg / 20
            no_outlier = []
            for l in distances:
                if abs(l - avg) < delta:
                    no_outlier.append(l)

            if len(no_outlier) >= 1:
                print("Distance: ", round(sum(no_outlier) / len(no_outlier), 1))

finally:
    GPIO.cleanup()
