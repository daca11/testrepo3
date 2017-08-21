import glob
import os
import subprocess
import time
import urllib2

from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

# TODO: read from config file
MOTION_ROOT_DIR = "/home/pi/motionfiles"
CAMERAS = 2
PATTERN = "*.avi"
VIDEO_LENGHT_SECONDS = 60


class WatcherHandler(PatternMatchingEventHandler): #TODO: SE ACUMULA! replace with check each 10 secs
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
        while len(fileList) > VIDEO_LENGHT_SECONDS:
            fileToRemove = rootEventPath + "/" + fileList.pop(0)  # TODO: join paths with os.join?
            print ">>> removing " + fileToRemove
            os.remove(fileToRemove)

    def on_created(self, event):
        self.process(event)


class CamRecorder:
    def __init__(self):
        self.process = None
        self.firstRun = True
        self.observer = Observer()
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
        # self.process = subprocess.Popen(
        #     "motion -m -c " + os.path.join(MOTION_ROOT_DIR, "configuration", "motion.conf"),
        #     shell=True, preexec_fn=os.setsid)
        subprocess.Popen(
            "motion -m -c " + os.path.join(MOTION_ROOT_DIR, "configuration", "motion.conf"),
            shell=True)


    def killProcess(self):
        # os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
        os.system("killall -g -KILL motion")
        # observer.stop() #is it required?
        # observer.join()
        self.firstRun = True

    def pause(self):
        # disable emulate motion + reset event? (optional: kill -1 'pid-of-motion')
        urllib2.urlopen("http://localhost:8080/0/config/set?emulate_motion=off").read()

    def resume(self):
        urllib2.urlopen("http://localhost:8080/0/config/set?emulate_motion=on").read()

    def start(self):
        self.archiveFiles()

        # observer = Observer()
        # schedule a watcher for each camera
        for num_cam in xrange(1, CAMERAS + 1):
            self.observer.schedule(WatcherHandler(), path=MOTION_ROOT_DIR + "/cam" + str(num_cam))
        self.observer.start() #TODO: already started???
        print "Starting to record..."

        if self.firstRun:
            self.runProcess()
            self.firstRun = False
        else:
            self.resume()
######################################################

            # while not newEvent:
            #     key = sys.stdin.read(1)
            #     if key[0] == "q":
            #         newEvent = True
            #         print "New event! starting 1min countdown and stopping observers" # TODO: param seconds of countdown...
            #         observer.stop()
            #         observer.join()
            #         time.sleep(5)
            #         print "Pausing motion..."
            #         # killing causes video device busy and skip seconds of recording
            #         # self.killProcess()
            #         self.pause()

    def fire(self):
        print "New event! starting 1min countdown and stopping observers"  # TODO: param seconds of countdown...
        self.observer.stop()
        self.observer.join()
        time.sleep(VIDEO_LENGHT_SECONDS)
        print "Pausing motion..."
        # killing causes video device busy and skip seconds of recording
        # self.killProcess()
        self.pause()




