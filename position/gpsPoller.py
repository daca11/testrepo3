from gps import gps, WATCH_ENABLE


class GpsPoller:
    def __init__(self):
        self.poller = gps(mode=WATCH_ENABLE)
        self.logfile = open("/home/pi/gpsfiles/locations.txt", "a")  # TODO: append time+gpstime from fix.xxxx
        self.attempts = 0

    def writeNext(self):
        self.poller.next()
        if self.poller.fix.latitude == 0.0 and self.poller.fix.longitude == 0.0:
            if self.attempts % 10 == 0:
                print "Waiting gps..."

            self.attempts += 1
        else:
            print "Position: (" + str(self.poller.fix.latitude) + ", " + str(self.poller.fix.longitude) + ")"
            self.logfile.write("%s,%s\n" % (self.poller.fix.latitude, self.poller.fix.longitude))
            self.attempts = 0

    def closeFile(self):
        self.logfile.close()