import sys
import threading
import time
import traceback

import requests

from camera.motion import CamRecorder
from logger.filelogger import FileLogger
from obd.obd_recorder import OBD_Recorder
from position.gpsPoller import GpsPoller
from rest.objects import LogMessage, Trip

WS_URI = 'http://192.168.1.108:8080/autologger/rest/'  # TODO: switch local/global ip
CHECK_INTERVAL = 1
RETRY_INTERVAL = 5
RETRY_ATTEMPS = 5

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
            obdSlot = obdRecorder.record_data()


def gpsThread(gpsPoller):
    """ Gets the current position """

    global gpsSlot

    while True:
        gpsSlot = gpsPoller.writeNext()


def postMessages():
    """ Sends pending rest messages in the queue to the rest WS """

    global logMessages
    attempts = 0
    tripId = None

    # request a trip id

    while tripId is None and attempts < RETRY_ATTEMPS:
        print "Requesting trip id..."

        try:
            r = requests.get(WS_URI)
            if r.status_code == 200:

                tripId = r.text
                attempts = 0

                while attempts < RETRY_ATTEMPS:
                    try:
                        if len(logMessages) != 0:
                            logMsg = logMessages[0]
                            logMsg.trip = Trip(tripId)
                            headers = {'content-type': 'application/json'}
                            r = requests.post(WS_URI, data=logMsg.toJSON(), headers=headers)
                            if r.status_code == 200:
                                logMessages.pop()
                                attempts = 0
                            else:
                                attempts = failAttempt(attempts, r.status_code)
                    except:
                        attempts = failAttempt(attempts, None, sys.exc_info())

                print "Failed sending log to WS, logging locally only"

            else:
                attempts = failAttempt(attempts, r.status_code)
        except:
            attempts = failAttempt(attempts, None, sys.exc_info())

    print "Failed requesting tripId, logging locally only"


def failAttempt(attempts, status, exception=None):
    # failed get, retry in 5 secs
    # after 5 failed attempts, do not send data to ws

    attempts += 1
    errorMsg = "Failed attempt " + str(attempts)
    if status is not None:
        errorMsg += ", status: " + str(status)
    if exception is not None:
        ex_type, ex_value, ex_trace = exception
        errorMsg += ", exception: " + str(ex_value)
    print errorMsg
    time.sleep(RETRY_INTERVAL)
    return attempts


# TODO: catch exception in threads and rethrow in main thread (bucket queue?)

if __name__ == '__main__':
    try:
        logger = FileLogger('/home/pi/logs/')
        logMessages = []

        threads = []

        gpsSlot = None # GpsObject()
        obdSlot = None # ObdObject()

        # Camera thread
        cam = CamRecorder()
        th = threading.Thread(target=camRecorderThread, args=(cam,))  # TODO: configure as a daemon...
        threads.append(th)

        # GPS thread
        gpsp = GpsPoller()
        th = threading.Thread(target=gpsThread, args=(gpsp,))
        threads.append(th)

        # OBD thread
        obd = OBD_Recorder()
        th = threading.Thread(target=obdThread, args=(obd,))
        threads.append(th)

        # WS REST thread
        th = threading.Thread(target=postMessages,)
        threads.append(th)

        # Start all threads
        for t in threads:
            t.start()

        while True:
            # gather sensor info each second, write to log, send to ws
            # TODO: PRIORITY LOG FOR EVENT START/END (no check every x secs)
            if gpsSlot is not None or obdSlot is not None:
                message = LogMessage(time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()), gpsSlot, obdSlot)
                # TODO: Serialize (pickle?), save in internal BD?, save in csv?, resend on reconnection?
                # TODO: how to save tripId in local logs? (internal BD)
                logger.log_file.write(message.toJSON() + "\n")  # save in json for now
                logMessages.append(message)
                time.sleep(CHECK_INTERVAL)

    except:
        traceback.print_exc()
    finally:
        print "HALTING DOWN!"
        cam.killProcess()  # Kill motion to stop recording
        gpsp.closeFile()  # Flush gps logfile
        obd.closeFile()  # Flush obd logfile
        print "HALTED!"
