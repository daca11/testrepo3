import os
import signal
import subprocess


class Obd_Connector:

    def __init__(self):
        self.process = None

    def runProcess(self):
        # self.process = subprocess.Popen(
        #     "motion -m -c " + os.path.join(MOTION_ROOT_DIR, "configuration", "motion.conf"),
        #     shell=True, preexec_fn=os.setsid)
        self.process = subprocess.Popen(
            "rfcomm connect hci0 00:1D:A5:15:9E:D3", #TODO: run as sudo python script because of this!
            shell=True)


    def killProcess(self):
        os.killpg(os.getpgid(self.process.pid), signal.SIGINT)
        # os.system("killall -g -KILL motion")
        # observer.stop() #is it required?
        # observer.join()