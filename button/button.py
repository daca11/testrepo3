import RPi.GPIO as GPIO


GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN)

while True:
    input_value = GPIO.input(17)

    if not input_value:
        print("Who pressed my button!")
        while input_value == False:
            input_value = GPIO.input(17)