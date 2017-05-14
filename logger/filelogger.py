import time


class FileLogger:
    def __init__(self, path):
        localtime = time.localtime(time.time())
        self.file = path + "car-"+str(localtime[0])+"-"+str(localtime[1])+"-"+str(localtime[2])+"-"+str(localtime[3])+"-"+str(localtime[4])+"-"+str(localtime[5])+".txt"
        self.log_file = open(self.file, "w", 0)