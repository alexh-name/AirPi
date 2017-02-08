""" Read data from the DHT22 sensor.

A high-level Class to read data from the DHT22 sensor. An instance of
the Class can read *either* temperature *or* pressure; see __init__()
for more detail. Requires the low-level dhtreader.so (shared object) to
read the raw data from the sensor.

"""
import sensor
import dhtreader
import time
import threading

# https://github.com/adafruit/Adafruit-Raspberry-Pi-Python-Code/blob/master/Adafruit_DHT_Driver_Python/dhtreader.c

class DHT22(sensor.Sensor):
    """ Read data from the DHT22 sensor.

    A high-level Class to read data from the DHT22 sensor. An instance of
    the Class can read *either* temperature *or* pressure; see __init__()
    for more detail. Requires the low-level dhtreader.so (shared object) to
    read the raw data from the sensor.

    """
    requiredData = ["measurement", "pinnumber"]
    optionalData = ["unit", "description"]

    def __init__(self, data):
        """Initialise.

        Initialise the DHT22 sensor class using parameters passed in 'data'.
        Instances of this class can be set to monitor either temperature
        ('temp') or pressure ('h'). This is determined by the contents of
        'data' passed to this __init__ function. If you want to read both
        properties, you'll need two instances of the class.
        When set to read temperature, self.valname is 'Temperature-DHT' to
        differentiate it from other temperature sensors on the AirPi (such as
        the BMP). By default temperatures are read in Celsius; data["unit"]
        can be set to "F" to return readings in Fahrenheit instead if required.
        Humidity is returned as percentage relative humidity.

        Args:
            self: self.
            data: A dict containing the parameters to be used during setup.

        Return:

        """
        dhtreader.init()
        dhtreader.lastDataTime = 0
        dhtreader.lastData = (None, None)
        self.readingtype = "sample"
        self.pinnum = int(data["pinnumber"])
        if "temp" in data["measurement"].lower():
            self.sensorname = "DHT22-temp"
            self.valname = "Temperature-DHT"
            self.valunit = "Celsius"
            self.valsymbol = "C"
            if "unit" in data:
                if data["unit"] == "F":
                    self.valunit = "Fahrenheit"
                    self.valsymbol = "F"
        elif "h" in data["measurement"].lower():
            self.sensorname = "DHT22-hum"
            self.valname = "Relative_Humidity"
            self.valsymbol = "%"
            self.valunit = "Pct Relative Humidity"
        if "description" in data:
            self.description = data["description"]
        else:
            self.description = "A combined temperature and humidity sensor."
        return

    def getval(self):
        """Get the current sensor value.

        Get the current sensor value, for either temperature or humidity
        (whichever is appropriate to this instance of the class). Don't
        read more often than every two seconds (manufacturer says this
        is the average sensing time).

        Args:
            self: self.

        Returns:
            float The current value for the sensor.

        """
        if (time.time() - dhtreader.lastDataTime) > 2: # ok to do another reading
            # launch & wait for thread
            thread = DHTReadThread(self)
            thread.start()
            thread.join(2)
            if thread.isAlive():
                raise Exception('Timeout reading ' + self.sensorname)
            dhtreader.lastDataTime = time.time()

        temp, humid = dhtreader.lastData
        if self.valname == "Temperature-DHT":
            temp = temp
            if self.valunit == "Fahrenheit":
                try:
                    temp = temp * 1.8 + 32
                except TypeError:
                    # This will be thrown if the sensor fails to read,
                    # and so 'temp' has type 'None'. That usually
                    # happens at the start of the run, and is dealt with
                    # either by the fact that it's a dummy run and we're
                    # ignoring readings anyway, or by sample() in the
                    # main airpi.py script (~ line 908).
                    pass
            return temp
        elif self.valname == "Relative_Humidity":
            return humid

# http://softwareramblings.com/2008/06/running-functions-as-threads-in-python.html
# https://docs.python.org/2/library/threading.html
class DHTReadThread(threading.Thread):
    def __init__(self, parent):
        self.parent = parent
        threading.Thread.__init__(self)

    def run(self):
        try:
            temp, humid = dhtreader.read(22, self.parent.pinnum)
        except Exception:
            temp, humid = dhtreader.lastData
        dhtreader.lastData = (temp, humid)
