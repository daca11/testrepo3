import threading
import time

from camera.motion import CamRecorder
from obd.obd_recorder import OBD_Recorder


def camRecorderThread(camRecorder):
    camRecorder.start()


def obdThread():
    logitems = ["rpm", "speed", "throttle_pos", "load", "fuel_status"]
    o = OBD_Recorder('/home/pi/obdfiles/', logitems)
    o.connect()
    attempts = 1

    while not o.is_connected():
        if attempts % 10 == 0:
            print "Not connected. Retrying in 10 secs..."
            time.sleep(10)
        else:
            print "Not connected. Retrying in 1 sec..."
            time.sleep(1)
        attempts += 1
        o.connect()

    o.record_data()

if __name__ == '__main__':
    try:
        threads = []

        cam = CamRecorder()
        th = threading.Thread(target=camRecorderThread, args=(cam,))
        threads.append(th)

        th = threading.Thread(target=obdThread, args=())
        threads.append(th)

        # Ejecutamos todos los procesos
        for t in threads:
            t.start()

        # Esperamos a que se completen todos los procesos
        for t in threads:
            t.join()

    finally:
        print "HALTING DOWN!"
        cam.killProcess()
        print "HALTED!"