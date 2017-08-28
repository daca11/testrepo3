import datetime
import multiprocessing
import sys
import threading
import time
import traceback
from multiprocessing import Process

import RPi.GPIO as GPIO
import requests

import obd
from camera.motion import CamRecorder
from logger.filelogger import FileLogger
from obd.connector import Obd_Connector
from position.gpsPoller import GpsPoller
from rest.objects import LogMessage, Trip, ObdObject

#'http://192.168.42.13:8080/autologger/rest/',
WS_URIS = ['http://dalexa.no-ip.biz:8080/autologger/rest/', 'http://192.168.1.136:8080/autologger/rest/']
CURRENT_WS_URI_ID = 1
WS_URI = WS_URIS[CURRENT_WS_URI_ID]  # switch global/local ip
CHECK_INTERVAL = 1
RETRY_INTERVAL = 5

def camRecorderThread(camRecorder, eventDetected, tripId):

    p = Process(target=camRecorder.archiveFiles, args=(tripId,))
    p.start()
    p.join()

    camRecorder.start()


    while True:
        eventDetected.wait()
        dateTimeEvent = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        camRecorder.fire()

        p = Process(target=camRecorder.archiveFiles, args=(tripId,dateTimeEvent,True,))
        p.start()
        p.join()

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
                obdRecorder.watch(obd.commands.FUEL_LEVEL)
                obdRecorder.start()
                was_connected = True


            rpm = obdRecorder.query(obd.commands.RPM).value
            speed = obdRecorder.query(obd.commands.SPEED).value
            throttlepos = obdRecorder.query(obd.commands.THROTTLE_POS).value
            engineload = obdRecorder.query(obd.commands.ENGINE_LOAD).value
            fuellevel = obdRecorder.query(obd.commands.FUEL_LEVEL).value


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
    global tripId

    # request a trip id

    while tripId.value is 0:
        print "Requesting trip id..."

        try:
            r = requests.get(WS_URI)
            if r.status_code == 200:

                tripId.value = int(r.text)
                attempts = 0

                while True:
                    try:
                        if len(logMessages) != 0:
                            logMsg = logMessages[0]
                            logMsg.trip = Trip(tripId.value)
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


def buttonThread():
    global buttonPressed

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(17, GPIO.IN)

    while True:
        if not GPIO.input(17):
            buttonPressed = True  # Will be false when event has been registered


# TODO: catch exception in threads and rethrow in main thread (bucket queue?)

if __name__ == '__main__':
    #bug in python2.7, strptime not thread safe
    throwaway = datetime.datetime.strptime('20110101', '%Y%m%d')

    try:
        logger = FileLogger('/home/pi/logs/')
        logMessages = []

        threads = []

        eventDetected = multiprocessing.Event()
        # fireCamera = False
        tripId = multiprocessing.Value('i', 0)

        # Global vars
        gpsSlot = None
        obdSlot = None
        buttonPressed = False

        # Camera thread
        cam = CamRecorder()
        camWorker = multiprocessing.Process(target=camRecorderThread, args=(cam, eventDetected, tripId))
        camWorker.start()
        # th = threading.Thread(target=camRecorderThread, args=(cam,))
        # threads.append(th)

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

        # Button Thread
        th = threading.Thread(target=buttonThread,)
        threads.append(th)

        # Start all threads
        for t in threads:
            t.start()


        while True:

            if buttonPressed or (obdSlot is not None and obdSlot.rpm > 3000):  # Threshold EVENT DETECTED!
                buttonPressed = False  # Reset button status
                eventDetected.set()  # Turned off when log enqueued
                # fireCamera = True     # Turned off when video completes

            # gather sensor info each second, write to log, send to ws
            if eventDetected.is_set() or gpsSlot is not None or obdSlot is not None:
                message = LogMessage(time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()), gpsSlot, obdSlot, eventDetected.is_set())
                eventDetected.clear() #maybe if is_set?
                # TODO: Serialize (pickle?), save in internal BD?, save in csv?, resend on reconnection?
                # TODO: how to save tripId in local logs? (internal BD)
                logger.log_file.write(message.toJSON() + "\n")  # save in json for now
                print "OBDLOG: " + message.toJSON()
                logMessages.append(message)

            time.sleep(CHECK_INTERVAL) #sleep out of if!


    except:
        traceback.print_exc()
    finally:
        print "HALTING DOWN!"
        cam.killProcess()  # Kill motion to stop recording
        camWorker.terminate()

        gpsp.closeFile()  # Flush gps logfile
        # obdConn.closeFile()  # Flush obd logfile
        obdConn.killProcess()  # Disconnect from obd bt
        print "HALTED!"
