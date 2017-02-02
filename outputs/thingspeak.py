import output
import requests

class ThingSpeak(output.Output):
    """A module to output data to ThingSpeak.

    """

    requiredSpecificParams = ["apikey"]

    def __init__(self, config):
        super(ThingSpeak, self).__init__(config)
        self.apikey = self.params["apikey"]

    def output_data(self, datapoints, dummy):
        """Output data.

        Output data in the format stipulated by the plugin. Calibration
        is carried out first if required.
        Note this method does not yet output GPS (Location) data.
        Because this particular plugin (plot) does not show time, the
        third argument (normally called 'sampletime') is called 'dummy'
        to facilitate compliance with pylint.

        Args:
            self: self.
            datapoints: A dict containing the data to be output.
            dummy: datetime representing the time the sample was taken.

        """
        if self.params["calibration"]:
            datapoints = self.cal.calibrate(datapoints)
        arr = {}
        counter = 1
        for point in datapoints:
            if point["name"] != "Location":
                if point["value"] != None: #this means it has no data to upload.
                    arr["field" + str(counter)] = round(point["value"], 2)
                counter += 1
        url = "https://api.thingspeak.com/update?key=" + self.apikey
        try:
            z = requests.post(url, params=arr)
            if z.text == "0":
                print("Error: ThingSpeak error - " + z.text)
                print("Error: ThingSpeak URL  - " + z.url)
                return False
        except Exception:
            return False
        return True
