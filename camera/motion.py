import glob
import os
import signal
import subprocess
import sys
import time
import urllib2

from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

# TODO: read from config file
MOTION_ROOT_DIR = "/home/pi/motionfiles"
CAMERAS = 2
PATTERN = "*.avi"


class WatcherHandler(PatternMatchingEventHandler):
    patterns = [PATTERN]

    def process(self, event):
        """
        event.event_type
            'modified' | 'created' | 'moved' | 'deleted'
        event.is_directory
            True | False
        event.src_path
            path/to/observed/file
        """
        # the file will be processed there
        print event.src_path, event.event_type  # print now only for debug

        # for each cam (observer), remove the oldest if there is more than two files
        rootEventPath, eventFile = os.path.split(event.src_path)

        fileList = sorted(glob.glob1(rootEventPath, PATTERN))
        if (len(fileList) > 2):
            fileToRemove = rootEventPath + "/" + fileList.pop(0)  # TODO: join paths with os.join?
            print "removing " + fileToRemove
            os.remove(fileToRemove)

    def on_created(self, event):
        self.process(event)


class CamRecorder:
    def __init__(self):
        self.process = None
        # TODO param storage dirs

    """
        Moves all *.avi files of each camera into a directory
        named like the first video in the directory of that camera
    """

    def archiveFiles(self):
        for num_cam in xrange(1, CAMERAS + 1):
            cam_dir = MOTION_ROOT_DIR + "/cam" + str(num_cam)
            new_dir = ""
            for file in sorted(glob.glob1(cam_dir, PATTERN)):
                # file = only filename+ext
                if new_dir == "":
                    filename, extension = os.path.splitext(file)
                    new_dir = cam_dir + "/" + filename
                    os.mkdir(new_dir)  # TODO: check if exists...
                print "rename " + cam_dir + "/" + file
                print "to " + new_dir + "/" + file
                os.rename(cam_dir + "/" + file, new_dir + "/" + file)

    def runProcess(self):
        self.process = subprocess.Popen(
            "motion -m -c " + os.path.join(MOTION_ROOT_DIR, "configuration", "motion.conf"),
            shell=True, preexec_fn=os.setsid)


    def killProcess(self):
        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)

    def pause(self):
        # disable emulate motion + reset event? (optional: kill -1 'pid-of-motion')
        urllib2.urlopen("http://localhost:8080/foo/bar").read()

    def resume(self):
        urllib2.urlopen("http://localhost:8080/foo/bar").read()

    def start(self):
        firstRun = True

        try:
            while True:
                self.archiveFiles()

                newEvent = False

                observer = Observer()
                # schedule a watcher for each camera
                for num_cam in xrange(1, CAMERAS + 1):
                    observer.schedule(WatcherHandler(), path=MOTION_ROOT_DIR + "/cam" + str(num_cam))
                observer.start()
                print "Starting to record..."

                if firstRun:
                    self.runProcess()
                else:
                    self.resume()

                while not newEvent:
                    key = sys.stdin.read(1)
                    if key == "q":
                        newEvent = True
                        print "New event! starting 1min countdown and stopping observers" # TODO: param seconds of countdown...
                        observer.stop()
                        observer.join()
                        time.sleep(5)
                        print "Pausing motion..."
                        # killing causes video device busy and skip seconds of recording
                        # self.killProcess()
                        self.pause()

        finally:
            print "HALTING DOWN!"
            self.killProcess()
            observer.stop()
            observer.join()
            print "HALTED!"
