import glob
import os
import subprocess
import sys
import time
import urllib2
from multiprocessing import Process

import requests
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

# TODO: read from config file
from rest.objects import CameraEvent, Trip

MOTION_ROOT_DIR = "/home/pi/motionfiles"
CAMERAS = 2
PATTERN = "*.avi"
SECONDS_POST_CAPTURE = 60


#'http://192.168.42.13:8080/autologger/rest/',
WS_URIS = ['http://dalexa.no-ip.biz:8080/autologger/rest/', 'http://192.168.1.136:8080/autologger/rest/']
CURRENT_WS_URI_ID = 0
WS_URI = WS_URIS[CURRENT_WS_URI_ID]  # switch global/local ip
CHECK_INTERVAL = 1
RETRY_INTERVAL = 5


class WatcherHandler(PatternMatchingEventHandler):
    # def __init__(self):
    #     super(WatcherHandler, self).__init__()
        # self.counter = 0

    def on_created(self, event):
        # if self.counter % 10 == 0:  # REMOVE WHEN WATCHER EXTERNALIZED!
        # for each cam (observer), remove the oldest if there is more than two files
        rootEventPath, eventFile = os.path.split(event.src_path)
        print "<<< created " + eventFile
        fileList = sorted(glob.glob1(rootEventPath, PATTERN))
        while len(fileList) > SECONDS_POST_CAPTURE:
            fileToRemove = rootEventPath + "/" + fileList.pop(0)  # TODO: join paths with os.join?
            os.remove(fileToRemove)
            print ">>> removed " + fileToRemove

        # self.counter += 1


class CamRecorder:
    def __init__(self):
        self.process = None
        self.firstRun = True
        self.observer = None
        # TODO param storage dirs

    """
        Moves all *.avi files of each camera into a directory
        named like the first video in the directory of that camera
    """

    def archiveFiles(self, tripId, dateTimeEvent=None, event=False):
        for num_cam in xrange(1, CAMERAS + 1):
            cam_dir = MOTION_ROOT_DIR + "/cam" + str(num_cam)
            new_dir = ""
            filelist = []
            #archive!
            for file in sorted(glob.glob1(cam_dir, PATTERN)):
                # file = only filename+ext
                if new_dir == "":
                    filename, extension = os.path.splitext(file)
                    new_dir = cam_dir + "/" + filename
                    os.mkdir(new_dir)  # TODO: check if exists...

                filelist.append(new_dir + "/" + file)
                print cam_dir + "/" + file + " >>> " + new_dir + "/" + file
                os.rename(cam_dir + "/" + file, new_dir + "/" + file)

            #join files
            if len(filelist) != 0:
                proc = subprocess.Popen('ffmpeg -i "concat:' + '|'.join(filelist) + '" -c copy ' + new_dir + '/' +
                                        'outputCam' + str(num_cam) + '.avi',
                                 shell=True)
                proc.wait()
                print "VIDEO JOINED!!!"

                # SEND TO WS (if event)
                if event:
                    p = Process(target=self.sendVideo, args=(tripId, dateTimeEvent, num_cam ))
                    p.start()


    def sendVideo(self, tripId, dateTime, cameraId):

        sent = False

        while tripId.value is 0:
            print "No trip id to send video..."
            time.sleep(RETRY_INTERVAL)

        print "Trip ID!: " + str(tripId.value)
        trip = Trip(tripId.value)
        cameraEvent = CameraEvent(trip, dateTime, cameraId)

        while not sent:
            try:
                headers = {'content-type': 'application/json'}
                r = requests.post(WS_URI+"video", data=cameraEvent.toJSON(), headers=headers)
                if r.status_code == 200:
                    sent = True
                    print "!!!! VIDEO SENT !!!!"
                else:
                    print "Failed sending VIDEO to WS, status: " + str(r.status_code)
            except:
                ex_type, ex_value, ex_trace = sys.exc_info()
                print "Failed sending VIDEO to WS, exception: " + str(ex_value)

            time.sleep(RETRY_INTERVAL)


    def runProcess(self):
        # self.process = subprocess.Popen(
        #     "motion -m -c " + os.path.join(MOTION_ROOT_DIR, "configuration", "motion.conf"),
        #     shell=True, preexec_fn=os.setsid)
        subprocess.Popen(["motion", "-m", "-c", os.path.join(MOTION_ROOT_DIR, "configuration", "motion.conf")]
            ,
            shell=False)


    def killProcess(self):
        # os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
        os.system("killall -g -KILL motion") #TODO: CHECK IF IT IS ALIVE
        # observer.stop() #is it required?
        # observer.join()
        self.firstRun = True

    def pause(self):
        # disable emulate motion + reset event? (optional: kill -1 'pid-of-motion')
        urllib2.urlopen("http://localhost:8080/0/config/set?emulate_motion=off").read()

    def resume(self):
        urllib2.urlopen("http://localhost:8080/0/config/set?emulate_motion=on").read()

    def start(self):
        # schedule a watcher for each camera
        self.observer = Observer()
        for num_cam in xrange(1, CAMERAS + 1):
            self.observer.schedule(WatcherHandler(), path=MOTION_ROOT_DIR + "/cam" + str(num_cam))

        self.observer.start()

        if self.firstRun:
            self.runProcess()
            self.firstRun = False
        else:
            self.resume()

        print "**RECORDING**"

    def fire(self):
        print "-----NEW EVENT!-----"  # TODO: param seconds of countdown...
        self.observer.stop()
        self.observer.join()
        time.sleep(SECONDS_POST_CAPTURE)
        print "**>NOT RECORDING<**"
        self.pause()




