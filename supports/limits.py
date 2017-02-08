"""A module to define exposure limits.

A support module which is used to define exposure limits for gases.
Once defined, the Class is shared across all objects which
access it, i.e. limits are the same across all output plugins
which apply them. All limits are classed as 'breached' if the
current concentration of gas goes *above* the defined level.

Where EU limits are defined as averages over time, e.g. average CO level
over eight hours, we are only comparing instantaneous values from the
AirPi to them, so this is not entirely accurate (close enough though!).

"""
import support

class Limits(support.Support):
    """A module to define exposure limits.

    A support module which is used to define exposure limits for gases.
    Once defined, the Class is shared across all objects which
    access it, i.e. limits are the same across all output plugins
    which apply them. All limits are classed as 'breached' if the
    current concentration of gas goes *above* the defined level.

    Where EU limits are defined as averages over time, e.g. average CO level
    over eight hours, we are only comparing instantaneous values from the
    AirPi to them, so this is not entirely accurate (close enough though!).

    """

    optionalSpecificParams = ["limit_Nitrogen_Dioxide",
                              "limit_Carbon_Monoxide",
                              "limit_Air_Quality",
                              "limit_Relative_Humidity",
                              "limit_Pressure",
                              "limit_DHT22-Temperature",
                              "limit_BMP085-Temperature"]

    def __init__(self, config):
        """Initialise.

        Initialise the Limits class, using the parameters passed in
        'params'. Note that the 'requiredParams' and 'optionalParams'

        Args:
            self: self.
            params: Parameters to be used as the limits. Can be empty. If not, must be
                    a list of phenomena names with corresponding strings containing
                    comma-separated value and unit, e.g.:
                    params["nitrogen_dioxide"] = ["10,Ohms"]
                    params["carbon_monoxide"] = ["20",ppm"]

        """
        super(Limits, self).__init__(config)
        #TODO: What about the fact that the limits are already in self.params? Do we want to use them? Do we even care?
        self.limits = {}
        if config.has_section("Limits") and config.has_option("Limits", "enabled") and config.getboolean("Limits", "enabled"):
            for phenomena, limit in config.items("Limits"):
                if phenomena.startswith("limit_"):
                    [value, units] = limit.split(',', 1)
                    name = phenomena[6:].lower()
                    self.limits[name] = {}
                    self.limits[name]["value"] = value
                    self.limits[name]["units"] = units

    def isbreach(self, samplename, samplevalue, sampleunit):
        """Check whether a data point breaches a limit.

        Checks whether the value of a specific data point breaches the
        defined limit.
        NOTE: We are comparing instantaneous AirPi values with, in some
        cases, EU limits per hourly average, calendar year (NO2) or
        eight-hour average (CO).

        Args:
            self: self.
            datapoint: The datapoint to be tested. Passed by the output
                       plugin which is checking for the breach.

        """
        samplename = samplename.lower()
        if samplename in self.limits:
            if samplevalue > float(self.limits[samplename]["value"]):
                sensorunit = self.limits[samplename]["units"]
                if sampleunit == sensorunit:
                    return True
                else:
                    print('ERROR: Limit units do not match measurement units for ' + samplename)
                    print('       ' + sampleunit + ' is not the same as ' + sensorunit)
        return False
