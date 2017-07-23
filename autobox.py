import sys
import threading
import time
import traceback

import requests

import obd
from camera.motion import CamRecorder
from logger.filelogger import FileLogger
from obd.connector import Obd_Connector
from position.gpsPoller import GpsPoller
from rest.objects import LogMessage, Trip, ObdObject

#'http://192.168.42.13:8080/autologger/rest/',
WS_URIS = ['http://dalexa.no-ip.biz:8080/autologger/rest/', 'http://192.168.1.108:8080/autologger/rest/']
CURRENT_WS_URI_ID = 0
WS_URI = WS_URIS[CURRENT_WS_URI_ID]  # switch global/local ip
CHECK_INTERVAL = 1
RETRY_INTERVAL = 5

def camRecorderThread(camRecorder):
    camRecorder.start()


def obdThread(obdConnection):
    """ Gets the current obd sensors status """

    global obdSlot
    #TODO: when load = 0 then re-run program?
    obdConnection.runProcess()
    obdRecorder = obd.Async("/dev/rfcomm0")
    was_connected = False

    while True:
        if not obdRecorder.is_connected():
            was_connected = False
            print "OBD Not connected. Retrying in 5 secs..."
            time.sleep(5)
            obdConnection.runProcess()
            obdRecorder = obd.Async("/dev/rfcomm0")
        else:
            if not was_connected:
                print "OBD Successfully connected!"
                obdRecorder.watch(obd.commands.RPM)
                obdRecorder.watch(obd.commands.SPEED)
                obdRecorder.watch(obd.commands.THROTTLE_POS)
                obdRecorder.watch(obd.commands.ENGINE_LOAD)
                obdRecorder.watch(obd.commands.LONG_FUEL_TRIM_1)
                obdRecorder.start()
                was_connected = True


            rpm = obdRecorder.query(obd.commands.RPM).value
            speed = obdRecorder.query(obd.commands.SPEED).value
            throttlepos = obdRecorder.query(obd.commands.THROTTLE_POS).value
            engineload = obdRecorder.query(obd.commands.ENGINE_LOAD).value
            fuellevel = obdRecorder.query(obd.commands.LONG_FUEL_TRIM_1).value


            obdSlot = ObdObject(
                rpm.magnitude if rpm is not None else None,
                speed.magnitude if speed is not None else None,
                throttlepos.magnitude if throttlepos is not None else None,
                engineload.magnitude if engineload is not None else None,
                fuellevel.magnitude if fuellevel is not None else None
            )



def gpsThread(gpsPoller):
    """ Gets the current position """

    global gpsSlot

    while True:
        gpsSlot = gpsPoller.writeNext()


def postMessages():
    """ Sends pending rest messages in the queue to the rest WS """

    global logMessages
    global CURRENT_WS_URI_ID
    global WS_URI
    global WS_URIS

    attempts = 0
    tripId = None

    # request a trip id

    while tripId is None:
        print "Requesting trip id..."

        try:
            r = requests.get(WS_URI)
            if r.status_code == 200:

                tripId = r.text
                attempts = 0

                while True:
                    try:
                        if len(logMessages) != 0:
                            logMsg = logMessages[0]
                            logMsg.trip = Trip(tripId)
                            headers = {'content-type': 'application/json'}
                            r = requests.post(WS_URI, data=logMsg.toJSON(), headers=headers)
                            if r.status_code == 200:
                                logMessages.pop(0)
                                attempts = 0
                            else:
                                attempts = failAttempt(attempts, "Failed sending log to WS", r.status_code)
                    except:
                        attempts = failAttempt(attempts, "Failed sending log to WS", None, sys.exc_info())
            else:
                attempts = failAttempt(attempts, "Failed requesting tripId to WS", r.status_code)
        except:
            CURRENT_WS_URI_ID = 0 if CURRENT_WS_URI_ID == 1 else 1
            WS_URI = WS_URIS[CURRENT_WS_URI_ID]
            attempts = failAttempt(attempts, "Failed requesting tripId to WS", None, sys.exc_info())


def failAttempt(attempts, message, status, exception=None):
    # failed request, retry in 5 secs

    attempts += 1
    errorMsg = "Failed attempt " + str(attempts)
    errorMsg += ", message: " + message
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

        gpsSlot = None
        obdSlot = None

        # Camera thread
        cam = CamRecorder()
        th = threading.Thread(target=camRecorderThread, args=(cam,))  # TODO: configure as a daemon...
        threads.append(th)

        # GPS thread
        gpsp = GpsPoller()
        th = threading.Thread(target=gpsThread, args=(gpsp,))
        threads.append(th)

        # OBD thread
        obdConn = Obd_Connector()
        th = threading.Thread(target=obdThread, args=(obdConn,))
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
                print "OBDLOG: " + message.toJSON()
                logMessages.append(message)
                time.sleep(CHECK_INTERVAL)

    except:
        traceback.print_exc()
    finally:
        print "HALTING DOWN!"
        cam.killProcess()  # Kill motion to stop recording
        gpsp.closeFile()  # Flush gps logfile
        # obdConn.closeFile()  # Flush obd logfile
        obdConn.killProcess()  # Disconnect from obd bt
        print "HALTED!"
