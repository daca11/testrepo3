import threading

from camera.motion import CamRecorder
from obd.obd_recorder import OBD_Recorder


def camRecorderThread():
    cam = CamRecorder()
    cam.start()


def obdThread():
    logitems = ["rpm", "speed", "throttle_pos", "load", "fuel_status"]
    o = OBD_Recorder('/home/pi/obdfiles/', logitems)

    o.connect()

    while not o.is_connected():
        print "Not connected. Retrying..."
        o.connect()

    o.record_data()

if __name__ == '__main__':
    threads = []

    th = threading.Thread(target=camRecorderThread, args=())
    threads.append(th)
    th = threading.Thread(target=camRecorderThread(), args=())

    # Ejecutamos todos los procesos
    for t in threads:
        t.start()

    # Esperamos a que se completen todos los procesos
    for t in threads:
        t.join()
