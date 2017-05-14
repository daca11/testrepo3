import json


class GpsObject:
    def __init__(self, lat=None, lng=None):
        self.lat = lat
        self.lng = lng


class ObdObject:
    def __init__(self, rpm=None, speed=None, throttle=None, load=None, fuel=None):
        self.rpm = rpm
        self.speed = speed
        self.throttle = throttle
        self.load = load
        self.fuel = fuel


class Trip:
    def __init__(self, tripId):
        self.tripId = tripId


class LogMessage:
    def __init__(self, time, gps=None, obd=None):
        self.trip = None
        self.time = time
        self.gps = gps
        self.obd = obd
        # TODO: event? How to send an event has been happened? Event number? None if no event?

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=False, indent=None)