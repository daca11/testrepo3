import glob
import os
import subprocess
import time
import urllib2
from multiprocessing import Process

from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

# TODO: read from config file
MOTION_ROOT_DIR = "/home/pi/motionfiles"
CAMERAS = 2
PATTERN = "*.avi"
SECONDS_POST_CAPTURE = 60


class WatcherHandler(PatternMatchingEventHandler): #TODO: SE ACUMULA! replace with check each 10 secs
    def __init__(self):
        super(WatcherHandler, self).__init__()
        self.counter = 0

    def on_created(self, event):
        if self.counter % 10 == 0:  # REMOVE WHEN WATCHER EXTERNALIZED!
            # for each cam (observer), remove the oldest if there is more than two files
            rootEventPath, eventFile = os.path.split(event.src_path)
            print "<<< created " + eventFile
            fileList = sorted(glob.glob1(rootEventPath, PATTERN))
            while len(fileList) > SECONDS_POST_CAPTURE:
                fileToRemove = rootEventPath + "/" + fileList.pop(0)  # TODO: join paths with os.join?
                os.remove(fileToRemove)
                print ">>> removed " + fileToRemove

        self.counter += 1


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
                proc = subprocess.Popen(["ffmpeg", "-i", "\"concat:" + "|".join(filelist) + "\"", "-c", "copy",
                                         new_dir +  "/output.avi"], # FIXME: FILENAME TOO LONG, join little chunks?
                                 shell=False)
                proc.wait()
                print "VIDEO JOINED!!!"
                #TODO: SEND TO WS


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
        #  OPEN IT IN ANOTHER PROCESS AND WAIT TO FINISH
        p = Process(target=self.archiveFiles)
        p.start()
        p.join()
        # self.archiveFiles()

        if self.firstRun:
            # schedule a watcher for each camera
            for num_cam in xrange(1, CAMERAS + 1):
                self.observer.schedule(WatcherHandler(), path=MOTION_ROOT_DIR + "/cam" + str(num_cam))

            self.observer.start()  # TODO: already started???

            self.runProcess()
            self.firstRun = False
        else:
            self.resume()

        print "**RECORDING**"

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
        print ">>>NEW EVENT!<<<"  # TODO: param seconds of countdown...
        self.observer.stop()
        # self.observer.join()
        time.sleep(SECONDS_POST_CAPTURE)
        print "**>NOT RECORDING<**"
        self.pause()




