import threading
import time
import traceback

import requests

from camera.motion import CamRecorder
from obd.obd_recorder import OBD_Recorder
from position.gpsPoller import GpsPoller
from rest.objects import GpsObject, ObdObject, RestMessage


def camRecorderThread(camRecorder):
    camRecorder.start()


def obdThread(obdRecorder):
    """ Gets the current obd sensors status """

    global obdSlot

    obdRecorder.connect()
    attempts = 1

    while True:
        if not obdRecorder.is_connected():
            if attempts % 10 == 0:
                print "OBD Not connected. Retrying in 10 secs..."
                time.sleep(10)
            else:
                print "OBD Not connected. Retrying in 1 sec..."
                time.sleep(1)
            attempts += 1
            obdRecorder.connect()
        else:
            obdSlot = obdRecorder.record_data()  # TODO: make record_data returns an obd object


def gpsThread(gpsPoller):
    """ Gets the current position """

    global gpsSlot

    while True:
        gpsSlot = gpsPoller.writeNext()


def restThread():
    """ Wraps sensor data in a message and sends it to ws via post """

    message = RestMessage(gpsSlot, obdSlot)
    jsonmessage = message.toJSON()
    headers = { 'content-type' : 'application/json'}
    r = requests.post('http://192.168.1.108:8080/autologger/rest/', data=message.toJSON(), headers=headers)
    print "Post status: " + str(r.status_code)

# TODO: catch exception in threads and rethrow in main thread (bucket queue?)

if __name__ == '__main__':
    try:
        threads = []

        gpsSlot = GpsObject()
        obdSlot = ObdObject()

        cam = CamRecorder()
        th = threading.Thread(target=camRecorderThread, args=(cam,))  # TODO: configure as a daemon...
        threads.append(th)

        gpsp = GpsPoller()
        th = threading.Thread(target=gpsThread, args=(gpsp,))
        threads.append(th)

        obd = OBD_Recorder()
        th = threading.Thread(target=obdThread, args=(obd,))
        threads.append(th)

        # Ejecutamos todos los procesos
        for t in threads:
            t.start()

        while True:
            # print "Gps: " + gpsSlot
            # print "OBD: " + obdSlot

            # send as rest message in a separate new thread
            th = threading.Thread(target=restThread,)
            th.start()
            time.sleep(1)

            # TODO: --> handle errors (queue unsent msgs?)

        # Esperamos a que se completen todos los procesos
        # for t in threads:
        #     t.join()
    except:
        traceback.print_exc()
    finally:
        print "HALTING DOWN!"
        cam.killProcess()  # Kill motion to stop recording
        gpsp.closeFile()  # Flush gps logfile
        obd.closeFile()  # Flush obd logfile
        print "HALTED!"
