import threading
import time
import traceback

from camera.motion import CamRecorder
from obd.obd_recorder import OBD_Recorder
from position.gpsPoller import GpsPoller


def camRecorderThread(camRecorder):
    camRecorder.start()


def obdThread(obdRecorder):
    obdRecorder.connect()
    attempts = 1

    while not obdRecorder.is_connected():
        if attempts % 10 == 0:
            print "Not connected. Retrying in 10 secs..."
            time.sleep(10)
        else:
            print "Not connected. Retrying in 1 sec..."
            time.sleep(1)
        attempts += 1
        obdRecorder.connect()

    obdRecorder.record_data()


def gpsThread(gpsPoller):
    while True:
        gpsPoller.writeNext()

# TODO: catch exception in threads and rethrow in main thread (bucket queue?)

if __name__ == '__main__':
    try:
        threads = []

        cam = CamRecorder()
        th = threading.Thread(target=camRecorderThread, args=(cam,)) # TODO: configure as a daemon...
        threads.append(th)

        gpsp = GpsPoller()
        th = threading.Thread(target=gpsThread, args=(gpsp,))
        threads.append(th)

        logitems = ["rpm", "speed", "throttle_pos", "load", "fuel_status"]
        obd = OBD_Recorder('/home/pi/obdfiles/', logitems)
        th = threading.Thread(target=obdThread, args=(obd,))  # TODO: join obd+gps>send json into the same thread?
        threads.append(th)

        # Ejecutamos todos los procesos
        for t in threads:
            t.start()

        # Esperamos a que se completen todos los procesos
        for t in threads:
            t.join()
    except:
        traceback.print_exc()
    finally:
        print "HALTING DOWN!"
        cam.killProcess()  # Kill motion to stop recording
        gpsp.closeFile()  # Flush gps logfile
        obd.closeFile()  # Flush obd logfile
        print "HALTED!"
