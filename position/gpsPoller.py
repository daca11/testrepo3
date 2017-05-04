from gps import gps, WATCH_ENABLE

from rest.objects import GpsObject


class GpsPoller:
    def __init__(self):
        self.poller = gps(mode=WATCH_ENABLE)
        self.logfile = open("/home/pi/gpsfiles/locations.txt", "a", 0)  # TODO: append time+gpstime from fix.xxxx
        self.attempts = 0

    def writeNext(self):
        self.poller.next()
        if self.poller.fix.latitude == 0.0 and self.poller.fix.longitude == 0.0:
            if self.attempts % 10 == 0:
                print "Waiting gps..."

            self.attempts += 1
            return GpsObject()
        else:
            gpsObject = GpsObject(self.poller.fix.latitude, self.poller.fix.longitude)
            print "Position: (" + str(gpsObject.lat) + ", " + str(gpsObject.lng) + ")"
            self.logfile.write("%s,%s\n" % (gpsObject.lat, gpsObject.lng))
            self.attempts = 0
            return gpsObject



    def closeFile(self):
        self.logfile.close()