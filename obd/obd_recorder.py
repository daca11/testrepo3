#!/usr/bin/env python

import time
from datetime import datetime

import obd_io
import obd_sensors
from obd_utils import scanSerial
from rest.objects import ObdObject


class OBD_Recorder():
    def __init__(self):
        self.port = None
        localtime = time.localtime(time.time())
        filename = '/home/pi/obdfiles/'+"car-"+str(localtime[0])+"-"+str(localtime[1])+"-"+str(localtime[2])+"-"+str(localtime[3])+"-"+str(localtime[4])+"-"+str(localtime[5])+".txt"
        self.log_file = open(filename, "w", 0) # TODO: flush on newline?
        self.log_file.write("Time,RPM,MPH,Throttle,Load,Fuel Status\n")

        # for item in ["rpm", "speed", "throttle_pos", "load", "fuel_status"]:
        #     self.add_log_item(item)

        self.gear_ratios = [34/13, 39/21, 36/23, 27/20, 26/21, 25/22]
        #log_formatter = logging.Formatter('%(asctime)s.%(msecs).03d,%(message)s', "%H:%M:%S")

    def connect(self):
        portnames = scanSerial()
        #portnames = ['COM10']
        print portnames
        for port in portnames:
            self.port = obd_io.OBDPort(port, None, 2, 2)
            if(self.port.State == 0):
                self.port.close()
                self.port = None
            else:
                break

        if(self.port):
            print "Connected to "+self.port.port.name
            
    def is_connected(self):
        return self.port
        
    # def add_log_item(self, item):
    #     for index, e in enumerate(obd_sensors.SENSORS):
    #         if(item == e.shortname):
    #             self.sensorlist.append(index)
    #             print "Logging item: "+e.name
    #             break
            
            
    def record_data(self):
        if(self.port is None):
            return ObdObject()
        
        print "Logging started"
        
        #while 1:
        log_string = str(datetime.now())
        # results = {}

        sensorIndexEnum = obd_sensors.SensorIndexEnum()

        obdObject = ObdObject()
        obdObject.rpm = self.port.get_sensor_value(obd_sensors.SENSORS[sensorIndexEnum.rpm])
        obdObject.speed = self.port.get_sensor_value(obd_sensors.SENSORS[sensorIndexEnum.speed])
        obdObject.throttle = self.port.get_sensor_value(obd_sensors.SENSORS[sensorIndexEnum.throttle])
        obdObject.load = self.port.get_sensor_value(obd_sensors.SENSORS[sensorIndexEnum.load])
        obdObject.fuel = self.port.get_sensor_value(obd_sensors.SENSORS[sensorIndexEnum.fuel])

        # for index in self.sensorIndexList:
        #     (name, value, unit) = self.port.sensor(index)
        #     log_string = log_string + ","+str(value)
            # results[obd_sensors.SENSORS[index].shortname] = value;

        # gear = self.calculate_gear(results["rpm"], results["speed"])
        # log_string = log_string #+ "," + str(gear)

        #write to log
        self.log_file.write(obdObject.rpm + "," +
                            obdObject.speed + "," +
                            obdObject.throttle + "," +
                            obdObject.load + "," +
                            obdObject.fuel + "\n")

        return obdObject

            
    def calculate_gear(self, rpm, speed):
        if speed == "" or speed == 0:
            return 0
        if rpm == "" or rpm == 0:
            return 0

        rps = rpm/60
        mps = (speed*1.609*1000)/3600
        
        primary_gear = 85/46 #street triple
        final_drive  = 47/16
        
        tyre_circumference = 1.978 #meters

        current_gear_ratio = (rps*tyre_circumference)/(mps*primary_gear*final_drive)
        
        #print current_gear_ratio
        gear = min((abs(current_gear_ratio - i), i) for i in self.gear_ratios)[1] 
        return gear

    def closeFile(self):
        self.log_file.close()

# username = getpass.getuser()
# logitems = ["rpm", "speed", "throttle_pos", "load", "fuel_status"]
# o = OBD_Recorder('/home/'+username+'/pyobd-pi/log/', logitems)
# o.connect()
#
# while not o.is_connected():
#     print "Not connected. Retrying..."
#     o.connect()
#
# o.record_data()
