#!/usr/bin/env python

"""Start sampling with an AirPi board.

This is the main script file for sampling air quality and / or weather
data with an AirPi board on a Raspberry Pi. It takes configuration
settings from a number of config files, and outputs data from the
specified sensors in one or more requested formats. Errors notifications
can be raised via several methods.

See: http://airpi.es
     http://github.com/haydnw/airpi

"""

import sys
sys.dont_write_bytecode = True

# We don't import individual sensors classes etc.
# here because they are imported dynamically below.
import socket
import RPi.GPIO as GPIO
import ConfigParser
import datetime
import time
import inspect
import os
import signal
import urllib2
import logging
import subprocess
from logging import handlers
from math import isnan
from sensors import sensor
from outputs import output
from supports import support
from notifications import notification

class MissingField(Exception):
    """Exception to raise when an imported plugin is missing a required
    field.

    """
    pass

def format_msg(msg, msgtype):
    """Format messages for consistency.

    Format messages in a consistent format for display to the user, or
    for recording in the LOGGER.

    Args:
        msg: The message to be formatted.
        msgtype: The type of message represented by msg.

    Returns:
        The formatted string.

    """
    msgtypes = ['error', 'warning', 'info']
    if msgtype in msgtypes:
        return(msgtype.upper() + ":").ljust(8, ' ') + " " + msg
    elif msgtype is 'sys':
        return("[AirPi] " + msg)
    else:
        return(msgtype.title() + ":").ljust(8, ' ') + " " + msg

def logthis(kind, msg):
    """ Add spaces to align debug output.

    Add spaces to LOGGER messages, so that debug output is nicely
    aligned and therefore more readable.

    Args:
        kind: The kind of message to be processed.
        msg: The message to be processed.

    """
    if kind == "debug" or kind == "error":
        LOGGER.debug(" " + msg)
    else:
        LOGGER.info("  " + msg)

def get_subclasses(mod, cls):
    """Load subclasses for a module.

    Load the named subclasses for a specified module. Keys are named
    'dummy' because they are not used, and calling them this means that
    Pylint doesn't throw a message about them not being used.

    Args:
        mod: Module from which subclass should be loaded.
        cls: Subclass to load

    Returns:
        The subclass.

    """
    for dummy, obj in inspect.getmembers(mod):
        if hasattr(obj, "__bases__") and cls in obj.__bases__:
            return obj

def check_conn():
    """Check internet connectivity.

    Check for internet connectivity by trying to connect to a website.

    Returns:
        boolean True if successfully connects to the site within five
                seconds.
        boolean False if fails to connect to the site within five
                seconds.

    """
    try:
        urllib2.urlopen("http://www.google.com", timeout=5)
        return True
    except urllib2.URLError:
        pass
    return False

def led_setup(redpin, greenpin):
    """Set up AirPi LEDs.

    Carry out initial setup of AirPi LEDs, including setting them to
    'off'.

    Args:
        redpin:   GPIO pin number for red pin.
        greenpin: GPIO pin number for green pin.

    """
    if redpin:
        GPIO.setup(redpin, GPIO.OUT, initial=GPIO.LOW)
    if redpin:
        GPIO.setup(greenpin, GPIO.OUT, initial=GPIO.LOW)

def led_on(pin):
    """Turn LED on.

    Turn on an AirPi LED at a given GPIO pin number.

    Args:
        pin: Pin number of the LED to turn on.

    """
    GPIO.output(pin, GPIO.HIGH)

def led_off(pin):
    """Turn LED off.

    Turn off an AirPi LED at a given GPIO pin number.

    Args:
        pin: Pin number of the LED to turn off.

    """
    GPIO.output(pin, GPIO.LOW)

def get_serial():
    """Get Raspberry Pi serial no.

    Get the serial number of the Raspberry Pi.
    See: http://raspberrypi.nxez.com/2014/01/19/
            getting-your-raspberry-pi-serial-number-using-python.html

    Returns:
        string The serial number, or an error string.

    """
    cpuserial = "0000000000000000"
    try:
        thefile = open('/proc/cpuinfo', 'r')
        for line in thefile:
            if line[0:6] == 'Serial':
                cpuserial = line[10:26]
        thefile.close()
    except Exception:
        cpuserial = "ERROR000000000"
    return cpuserial

def get_hostname():
    """Get current hostname.

    Get the current hostname of the Raspberry Pi.

    Returns:
        string The hostname.

    """
    if socket.gethostname().find('.') >= 0:
        return socket.gethostname()
    else:
        return socket.gethostbyaddr(socket.gethostname())[0]

def set_cfg_paths():
    """Set paths to cfg files.

    Set the paths to config files. Assumes that they are in a
    sub-directory called 'cfg', within the same directory as the current
    script (airpi.py).

    Returns:
        dict The paths to the various config files.

    """
    cfgpaths = {}
    basedir = os.path.abspath('.')
    if basedir == "/":
        basedir = "/home/pi/AirPi"
    cfgdir = os.path.join(basedir, 'cfg')
    cfgpaths['settings'] = os.path.join(cfgdir, 'settings.cfg')
    cfgpaths['sensors'] = os.path.join(cfgdir, 'sensors.cfg')
    cfgpaths['outputs'] = os.path.join(cfgdir, 'outputs.cfg')
    cfgpaths['notifications'] = os.path.join(cfgdir, 'notifications.cfg')
    cfgpaths['supports'] = os.path.join(cfgdir, 'supports.cfg')
    logdir = os.path.join(basedir, 'log')
    cfgpaths['log'] = os.path.join(logdir, 'airpi.log')
    return cfgpaths

def set_up_logger():
    """Set up a logger.

    Set up a logger to be used for this main script.

    """
    thislogger = logging.getLogger(__name__)
    thislogger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(CFGPATHS['log'],
                maxBytes=40960, backupCount=5)
    thislogger.addHandler(handler)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    return thislogger

def check_cfg_file(filetocheck):
    """Check cfg file exists.

    Check whether a specified cfg file exists. Print and log a warning
    if not. Log the file name if it does exist.

    Args:
        filetocheck: The file to check the existence of.

    Returns:
        boolean True if the file exists.

    """
    if not os.path.isfile(filetocheck):
        msg = "Unable to access config file: " + filetocheck
        print(msg)
        logthis("error", msg)
        exit(1)
    else:
        msg = "Config file: " + filetocheck
        logthis("info", msg)
        return True

def any_plugins_enabled(plugins, plugintype):
    """Warn user if no plugins in a list are enabled.

    Print and log a message if the list of enabled plugins is empty,
    i.e. there are no plugins enabled.

    Args:
        plugins: Array of plugins to check.
        type:    The type of plugin being checked.
    Returns:
        boolean True if there are any plugins enabled.

    """
    if not plugins:
        msg = "There are no " + plugintype + " plugins enabled!"
        msg += " Please enable at least one and try again."
        print(msg)
        logthis("error", msg)
        sys.exit(1)
    else:
        return True

def set_up_supports():
    """Set up AirPi support plugins.
    Set up AirPi support plugins by reading supports.cfg to determine
    which should be enabled.
    Returns:
        list A list containing the enabled 'support' objects.
    """

    print("==========================================================")
    msg = format_msg("SUPPORTS", 'loading')
    print(msg)

    check_cfg_file(CFGPATHS['supports'])

    SUPPORTCONFIG = ConfigParser.SafeConfigParser()
    SUPPORTCONFIG.read(CFGPATHS['supports'])

    SUPPORTNAMES = SUPPORTCONFIG.sections()

    supportplugins = {}

    for plugin in SUPPORTNAMES:
        try:
            try:
                filename = SUPPORTCONFIG.get(plugin, "filename")
            except Exception:
                msg = "No filename config option found for support plugin "
                msg += str(plugin)
                msg = format_msg(msg, 'error')
                print(msg)
                raise
            try:
                enabled = SUPPORTCONFIG.getboolean(plugin, "enabled")
            except Exception:
                enabled = True

            #if enabled, load the plugin
            if enabled:
                try:
                    # 'a' means nothing below, but argument must be non-null
                    
                    mod = __import__('supports.' + filename, fromlist=['a'])
                    msg = "Successfully imported support module: " + filename
                    msg = format_msg(msg, 'success')
                    logthis("info", msg)
                except Exception:
                    msg = "Could not import support module " + filename
                    msg = format_msg(msg, 'error')
                    print(msg)
                    raise

                try:
                    msg = "Trying to get subclass for " + filename
                    msg = format_msg(msg, 'info')
                    logthis('info', msg)
                    supportclass = get_subclasses(mod, support.Support)
                    msg = "Successfully got subclasses for " + filename
                    msg = format_msg(msg, 'success')
                    logthis("info", msg)
                    if supportclass == None:
                        raise AttributeError
                except Exception:
                    msg = "Could not find a subclass of support.Support in"
                    msg += " module " + filename
                    msg = format_msg(msg, 'error')
                    print(msg)
                    raise

                try:
                    logthis("info", "Starting to set instclass for " + filename)
                    instclass = supportclass(SUPPORTCONFIG)
                    logthis("info", "Support plugin params are: " + str(instclass.params))
                    msg = "Successfully set instclass for " + filename
                    msg = format_msg(msg, 'success')
                    logthis("info", msg)

                    supportplugins[instclass.name.lower()] = instclass
                    msg = "Loaded support plugin " + str(plugin)
                    msg = format_msg(msg, 'success')
                    print(msg)
                    LOGGER.info("*******************")

                except Exception as excep:
                    msg = "Failed to import support plugin " + plugin
                    msg = format_msg(msg, 'error')
                    print(msg)
                    logthis("info", msg)

            else:
                # Plugin is not enabled
                supportplugins[filename] = False

        except Exception as excep: #add specific exception for missing module
            msg = "Did not import support plugin " + str(plugin) + ": " + str(excep)
            msg = format_msg(msg, 'error')
            print(msg)
            raise excep
        
    return supportplugins

def set_up_sensors():
    """Set up AirPi sensors.

    Set up AirPi sensors by reading sensors.cfg to determine which
    should be enabled, then checking that all required fields are
    present in sensors.cfg.

    Returns:
        list A list containing the enabled 'sensor' objects.

    """

    print("==========================================================")
    msg = format_msg("SENSORS", 'loading')
    print(msg)

    check_cfg_file(CFGPATHS['sensors'])

    SENSORCONFIG = ConfigParser.SafeConfigParser()
    SENSORCONFIG.read(CFGPATHS['sensors'])

    SENSORNAMES = SENSORCONFIG.sections()

    sensorplugins = []

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM) #Use BCM GPIO numbers.

    for i in SENSORNAMES:
        try:
            # See if the plugin is enabled
            try:
                enabled = SENSORCONFIG.getboolean(i, "enabled")
                logthis("info", str(i) + " requested: " + str(enabled))
            except Exception as excep:
                enabled = True

            # If enabled, load the plugin
            if enabled:

                try:
                    filename = SENSORCONFIG.get(i, "filename")
                    logthis("info", "Filename is: " + filename)
                except Exception:
                    msg = "No filename config option found for sensor plugin "
                    msg += str(i)
                    msg = format_msg(msg, 'error')
                    print(msg)
                    logthis("error", msg)
                    raise

                try:
                    # 'a' means nothing below, but argument must be non-null
                    logthis("info", "Trying to import sensors." + filename)
                    mod = __import__('sensors.' + filename, fromlist=['a'])
                    logthis("info", "Successfully imported sensors." + filename)
                except Exception as excep:
                    msg = "Could not import sensor module " + filename
                    msg = format_msg(msg, 'error')
                    print(msg)
                    logthis("error", msg)
                    raise

                try:
                    sensorclass = get_subclasses(mod, sensor.Sensor)
                    if sensorclass == None:
                        raise AttributeError
                except Exception:
                    msg = "Could not find a subclass of sensor.Sensor in"
                    msg += " module " + filename
                    msg = format_msg(msg, 'error')
                    print(msg)
                    logthis("error", msg)
                    raise

                try:
                    reqd = sensorclass.requiredData
                except Exception:
                    reqd = []
                    msg = "Unable to determine required parameters for the sensor."
                    msg = format_msg(msg, 'error')
                    print(msg)
                try:
                    opt = sensorclass.optionalData
                except Exception:
                    msg = "Unable to determine optional parameters for the sensor."
                    msg = format_msg(msg, 'error')
                    print(msg)
                    opt = []
                # Sensors don't have any common params, so this is empty
                common = []
                
                #TODO: Get rid of this when it's all activated in Output
                plugindata = define_plugin_params(SENSORCONFIG,
                                i, reqd, opt, common)

                try:
                    instclass = sensorclass(plugindata)
                except Exception:
                    if "serial_gps" not in filename:
                        msg = "Unable to set instclass for sensor using plugindata."
                    else:
                        msg = " GPS instance not created - socket not set up?"
                    msg = format_msg(msg, 'error')
                    LOGGER.error(msg)
                    raise

                # Check for a getval() method
                if callable(getattr(instclass, "getval", None)):
                    sensorplugins.append(instclass)
                    # Store sensorplugins array length for GPS plugin
                    if "serial_gps" in filename:
                        global gpsplugininstance
                        gpsplugininstance = instclass
                    msg = "Loaded sensor plugin " + str(i)
                    msg = format_msg(msg, 'success')
                    print(msg)
                else:
                    msg = "Loaded sensor support plugin " + str(i)
                    msg = format_msg(msg, 'success')
                    print(msg)
        except Exception as excep:
            # TODO: add specific exception for missing module
            msg = "Did not import sensor plugin " + str(i) + ": " + str(excep)
            msg = format_msg(msg, 'error')
            print(msg)
            continue

        LOGGER.info("*******************")


    if any_plugins_enabled(sensorplugins, 'sensor'):
        return sensorplugins

def set_up_outputs():
    """Set up AirPi output plugins.

    Set up AirPi output plugins by reading outputs.cfg to determine
    which should be enabled, then checking that all required fields are
    present in outputs.cfg.

    Returns:
        list A list containing the enabled 'output' objects.

    """

    print("==========================================================")
    msg = format_msg("OUTPUTS", 'loading')
    print(msg)

    check_cfg_file(CFGPATHS['outputs'])

    OUTPUTCONFIG = ConfigParser.SafeConfigParser()
    OUTPUTCONFIG.read(CFGPATHS['outputs'])

    OUTPUTNAMES = OUTPUTCONFIG.sections()
    if "Notes" in OUTPUTNAMES:
        OUTPUTNAMES.remove("Notes")

    outputplugins = []

    for plugin in OUTPUTNAMES:
        try:
            try:
                filename = OUTPUTCONFIG.get(plugin, "filename")
            except Exception:
                msg = "No filename config option found for output plugin "
                msg += str(plugin)
                msg = format_msg(msg, 'error')
                print(msg)
                raise
            try:
                enabled = OUTPUTCONFIG.getboolean(plugin, "enabled")
            except Exception:
                enabled = True

            #if enabled, load the plugin
            if enabled:
                try:
                    # 'a' means nothing below, but argument must be non-null
                    
                    mod = __import__('outputs.' + filename, fromlist=['a'])
                    msg = "Successfully imported output module: " + filename
                    msg = format_msg(msg, 'success')
                    logthis("info", msg)
                except Exception:
                    msg = "Could not import output module " + filename
                    msg = format_msg(msg, 'error')
                    print(msg)
                    raise

                try:
                    msg = "Trying to get subclass for " + filename
                    msg = format_msg(msg, 'info')
                    logthis('info', msg)
                    outputclass = get_subclasses(mod, output.Output)
                    msg = "Successfully got subclasses for " + filename
                    msg = format_msg(msg, 'success')
                    logthis("info", msg)
                    if outputclass == None:
                        raise AttributeError
                except Exception:
                    msg = "Could not find a subclass of output.Output in"
                    msg += " module " + filename
                    msg = format_msg(msg, 'error')
                    print(msg)
                    raise

                try:
                    logthis("info", "Starting to set instclass for " + filename)
                    instclass = outputclass(OUTPUTCONFIG)
                    logthis("info", "Output plugin params are: " + str(instclass.params))
                    msg = "Successfully set instclass for " + filename
                    msg = format_msg(msg, 'success')
                    logthis("info", msg)

                    outputplugins.append(instclass)
                    msg = "Loaded output plugin " + instclass.name
                    msg = format_msg(msg, 'success')
                    print(msg)
                    LOGGER.info("*******************")

                except Exception as excep:
                    msg = "Failed to import plugin " + plugin + ": " + str(excep)
                    msg = format_msg(msg, 'error')
                    print(msg)
                    logthis("info", msg)

        except Exception as excep: #add specific exception for missing module
            msg = "Did not import output plugin " + str(plugin) + ": " + str(excep)
            msg = format_msg(msg, 'error')
            print(msg)
            raise excep

    if any_plugins_enabled(outputplugins, 'output'):
        # TODO: Fix this to look at plugin.params["target"]
        #return fix_duplicate_outputs(outputplugins)
        return outputplugins

def fix_duplicate_outputs(plugins):
    """Ensure only one output plugin for stdout is enabled.

    Check whether the list of enabled output plugins includes more than
    one which prints to stdout. If it does, disable all except Print to
    avoid mayhem on screen!

    Args:
        plugins: A list containing the enabled output plugin
                 objects.

    Returns:
        list A new list of enabled output plugin objects, containing
             only one plugin which outputs to screen.

    """
    enabled = []
    for index, plugin in enumerate(plugins):
        name = plugin.getname()
        if plugin.target == "screen":
            thisPlugin = {}
            thisPlugin["name"] = name
            thisPlugin["index"] = index
            enabled.append(thisPlugin)

    removed = 0 # pop() changes indices; this helps us keep track
    if len(enabled) >= 2: 
        for plugin in enabled:
            if plugin["name"] != "Print":
                plugins.pop(plugin["index"] - removed)
                removed += 1
        msg = "Only one plugin can output to screen at at time."
        msg += os.linesep
        msg += "         Print is enabled; others have been disabled."
        msg = format_msg(msg, 'warning')
        print(msg)
    return plugins


def define_plugin_params(config, name, reqd, opt, common):
    """Define setup parameters for an plugin.

    Take a list of parameters supplied by the user ('config'), and
    compare to the separate lists of 'required', 'optional' and 'common'
    parameters for the plugin. Check that 'required' ones are present
    (raise a MissingField exception if not). Merge all three dicts into
    one 'params' dict that holds all setup parameters for this plugin,
    then tag metadata and async info on to the end.
    Parameters supplied by the user usually come from the relevant cfg
    file, while the lists of 'required', 'optional' and 'common'
    parameters are normally defined in the plugin Class.

    Args:
        config: The configparser containing the parameters defined by
                the user.
        name: The name of the plugin defined in the config file.
        reqd: List of parameters required by the plugin.
        opt: List of parameters considered optional for the plugin.
        common: List of parameters which are common across all plugins.

    Returns:
        dict A dict containing the various parameters.

    """
    LOGGER.debug(" Defining plugin params for " + name)
    LOGGER.debug(" - reqd:   " + str(reqd))
    LOGGER.debug(" - opt:    " + str(opt))
    LOGGER.debug(" - common: " + str(common))
    params = {}
    # Defaults:
    params["metadata"] = False
    #TODO: Can we delete this below?
    #params["limits"] = False
    params['async'] = False
    # Read params which have been defined
    if reqd:
        for reqdfield in reqd:
            if config.has_option(name, reqdfield):
                params[reqdfield] = config.get(name, reqdfield)
            else:
                msg = "Missing required field '" + reqdfield
                msg += "' for plugin " + name + "."
                print(msg)
                logthis("error", msg)
                msg += "This should be found in file: " + CFGPATHS['outputs']
                msg = format_msg(msg, 'error')
                print(msg)
                logthis("error", msg)
                raise MissingField
    if opt:
        for optfield in opt:
            if config.has_option(name, optfield):
                params[optfield] = config.get(name, optfield)
    if common:
        for commonfield in common:
            if config.has_option("Common", commonfield):
                params[commonfield] = config.get("Common", commonfield)

    LOGGER.debug(" Final combined params to be used to create " + name + " instance are:")
    LOGGER.debug(" " + str(params))
    return params

def set_up_notifications():
    """Set up AirPi notification plugins.

    Set up AirPi notification plugins by reading notifications.cfg to
    determine which should be enabled. For each plugin, check that all
    required fields are present; if so, create an instance of the plugin
    class and append it to the list of Notification plugins. Return the
    list.

    Returns:
        list A list containing the enabled 'notification' objects.

    """

    print("==========================================================")
    msg = format_msg("NOTIFICATIONS", 'loading')
    print(msg)

    check_cfg_file(CFGPATHS['notifications'])

    NOTIFICATIONCONFIG = ConfigParser.SafeConfigParser()
    NOTIFICATIONCONFIG.read(CFGPATHS['notifications'])

    NOTIFICATIONNAMES = NOTIFICATIONCONFIG.sections()
    NOTIFICATIONNAMES.remove("Common")

    notificationPlugins = []

    for i in NOTIFICATIONNAMES:
        try:
            try:
                filename = NOTIFICATIONCONFIG.get(i, "filename")
            except Exception:
                msg = "No filename config option found for notification plugin "
                msg += str(i)
                msg = format_msg(msg, 'error')
                print(msg)
                logthis("error", msg)
                raise
            try:
                enabled = NOTIFICATIONCONFIG.getboolean(i, "enabled")
            except Exception:
                enabled = True

            #if enabled, load the plugin
            if enabled:
                try:
                    # 'a' means nothing below, but argument must be non-null
                    mod = __import__('notifications.' + filename,
                            fromlist=['a'])
                except Exception:
                    msg = "Could not import notification module " + filename
                    msg = format_msg(msg, 'error')
                    print(msg)
                    logthis("error", msg)
                    raise

                try:
                    notificationclass = get_subclasses(mod,
                            notification.Notification)
                    if notificationclass == None:
                        raise AttributeError
                except Exception:
                    msg = "Could not find a subclass of"
                    msg += " notification.Notification in module " + filename
                    msg = format_msg(msg, 'error')
                    print(msg)
                    logthis("error", msg)
                    raise
                try:
                    reqd = notificationclass.requiredParams
                except Exception:
                    reqd = []
                try:
                    opt = notificationclass.optionalParams
                except Exception:
                    opt = []
                try:
                    common = notificationclass.commonParams
                except Exception:
                    common = []

                #TODO: Get rid of this when it's all activated in Output
                plugindata = define_plugin_params(NOTIFICATIONCONFIG, i,
                                reqd, opt, common)

                if NOTIFICATIONCONFIG.get(i, "target") == "internet" and not check_conn():
                    msg = "Skipping notification plugin " + i
                    msg += " because no internet connectivity."
                    msg = format_msg(msg, 'error')
                    print(msg)
                    logthis("info", msg)
                else:
                    instclass = notificationclass(plugindata)
                    instclass.async = plugindata['async']

                # check for a sendnotification function
                if callable(getattr(instclass, "sendnotification", None)):
                    notificationPlugins.append(instclass)
                    msg = "Loaded notification plugin " + str(i)
                    msg = format_msg(msg, 'success')
                    print(msg)
                    logthis("info", msg)
                else:
                    msg = "No callable sendnotification() function"
                    msg += " for notification plugin " + str(i)
                    msg = format_msg(msg, 'error')
                    print(msg)
                    logthis("info", msg)

        except Exception as excep:
            msg = "Did not import notification plugin " + str(i) + ": "
            msg += str(excep)
            msg = format_msg(msg, 'error')
            print(msg)
            logthis("error", msg)
            raise excep

    # Don't run any_plugins_enabled() here, because it's OK to NOT have any
    # notifications enabled (unlike sensors and outputs).
    if not notificationPlugins:
        msg = "No Notifications enabled."
        msg = format_msg(msg, 'info')
        print(msg)
    return notificationPlugins

def set_settings():
    """Set up settings.

    Set up settings by reading from settings.cfg.

    Returns:
        list A list containing the various settings.

    """

    print("==========================================================")
    print(format_msg("SETTINGS", 'loading'))

    check_cfg_file(CFGPATHS['settings'])
    mainconfig = ConfigParser.SafeConfigParser()
    mainconfig.read(CFGPATHS['settings'])

    if mainconfig.has_option("Debug", "debug"):
        if mainconfig.getboolean("Debug", "debug"):
            logging.basicConfig(level=logging.DEBUG)

    settingslist = {}

    settingslist['SAMPLEFREQ'] = mainconfig.getfloat("Sampling", "sampleFreq")
    if mainconfig.has_option("Sampling", "averageFreq"):
        if mainconfig.getint("Sampling", "averageFreq") != 0:
            settingslist['AVERAGEFREQ'] = mainconfig.getint("Sampling",
                "averageFreq")
            averagefreq = settingslist['AVERAGEFREQ']
            if averagefreq > 0:
                averagecount = averagefreq / settingslist['SAMPLEFREQ']
                if averagecount < 2:
                    msg = "averageFreq must be a least twice sampleFreq."
                    msg = format_msg(msg, 'error')
                    print(msg)
                    logthis("error", msg)
                    sys.exit(1)
                else:
                    settingslist['AVERAGECOUNT'] = averagecount
                    settingslist['PRINTUNAVERAGED'] = mainconfig.getboolean("Sampling", "printUnaveraged")
    settingslist['STOPAFTER'] = 0 # Default
    if mainconfig.has_option("Sampling", "stopafter"):
        if mainconfig.getint("Sampling", "stopafter") != 0:
            settingslist['STOPAFTER'] = mainconfig.getint("Sampling",
                "stopafter")
    settingslist['DUMMYDURATION'] = 0 # Default
    if mainconfig.has_option("Sampling", "dummyduration"):
        settingslist['DUMMYDURATION'] = mainconfig.getint("Sampling",
            "dummyduration")
    # LEDs
    settingslist['REDPIN'] = mainconfig.getint("LEDs", "redPin")
    settingslist['GREENPIN'] = mainconfig.getint("LEDs", "greenPin")
    settingslist['SUCCESSLED'] = mainconfig.get("LEDs", "successLED")
    settingslist['FAILLED'] = mainconfig.get("LEDs", "failLED")
    settingslist['LIMITLED'] = mainconfig.get("LEDs", "limitLED")
    # Misc
    settingslist['OPERATOR'] = mainconfig.get("Misc", "operator")
    settingslist['HELP'] = mainconfig.getboolean("Misc", "help")
    settingslist['PRINTERRORS'] = mainconfig.getboolean("Misc", "printErrors")
    # Debug
    settingslist['WAITTOSTART'] = mainconfig.getboolean("Debug", "waittostart")

    msg = "Loaded settings."
    msg = format_msg(msg, 'success')
    print(msg)
    logthis("info", msg)

    return settingslist

def set_metadata():
    """Set metadata.

    Set up metadata for this run. Outputting of the metadata is handled
    by each of the output plugins individually, so that you can - for
    example - output metadata via Print and CSVOutput in the same run.

    Returns:
        dict All metadata elements.

    """
    meta = {
        "STARTTIME":time.strftime("%H:%M on %A %d %B %Y"),
        "OPERATOR":SETTINGS['OPERATOR'],
        "PIID":get_serial(),
        "PINAME":get_hostname(),
        "SAMPLEFREQ": str(int(SETTINGS['SAMPLEFREQ'])) + " seconds"
        }
    if 'AVERAGEFREQ' in SETTINGS:
        meta['AVERAGEFREQ'] = str(SETTINGS['AVERAGEFREQ']) + " seconds"
    if SETTINGS['DUMMYDURATION'] != 0:
        meta["DUMMYDURATION"] = str(int(SETTINGS['DUMMYDURATION'])) + " seconds"
    if SETTINGS['STOPAFTER'] != 0:
        meta["STOPAFTER"] = str(int(SETTINGS['STOPAFTER'])) + " samples"
    return meta

def output_metadata(plugins, meta):
    """Output metadata via enabled plugins.

    Output metadata for the run via each of the enabled 'output'
    plugins. Note that some output plugins will not output metadata as
    it is not appropriate.

    Args:
        plugins: List of enabled 'output' plugins.
        meta: Metadata for the run.

    """
    if meta is None:
        meta = set_metadata()
    for plugin in plugins:
    #for name, data in inspect.getmembers(plugins):
    #    if hasattr(name, "output_metadata"):
        plugin.output_metadata(meta)

def delay_start():
    """Delay sampling for a set time.

    Delay sampling for a predetermined amount of time, notifying the
    user in 10-second chunks. This is primarily used to wait until the
    'start' of a full minute (i.e. zero seconds on the clock) before
    starting a run.

    Args:
        delay: How long the run should be delayed for (seconds).

    """
    # First calculate the required delay length
    now = datetime.datetime.now()
    seconds = float(now.second + (now.microsecond / 1000000))
    delay = (60 - seconds)
    # Now account for any dummy runs (including if DUMMYRUN = 0)
    dummyduration = SETTINGS['DUMMYDURATION']
    if delay > dummyduration:
        delay = delay - dummyduration
    else:
        delay = delay + (60 - dummyduration)
    # OK, commence the delay
    print("==========================================================")
    msg = "Sampling will start in " + str(int(delay)) + " seconds."
    msg = format_msg(msg, 'info')
    print(msg)
    remainder = delay % 10
    remaining = delay - remainder
    time.sleep(remainder)
    while remaining >= 1:
        msg = "Sampling will start in " + str(int(remaining)) + " seconds."
        msg = format_msg(msg, 'info')
        print(msg)
        time.sleep(10)
        remaining -= 10

def dummy_runs(dummyduration):
    """Do dummy runs to kick off sensors.

    Read from the enabled sensors a few times to kick them in to life.
    The data, or results of trying to read the sensors, are not stored
    anywhere. This just helps ensure that there are no zero-readings
    when we get on to the 'actual' readings.

    Args:
        dummyduration: How long the dummy runs should last (seconds).

    """
    msg = "Doing initialising runs for " + str(dummyduration) + " seconds."
    msg = format_msg(msg, 'info')
    print(msg)
    startdummy = time.time()
    diff = 0
    while diff < dummyduration:
        # Note there is no sleep() here, so they will read as quickly as
        # possible for 15 seconds.
        for i in PLUGINSSENSORS:
            if i == gpsplugininstance:
                read_gps(i)
            else:
                read_sensor(i, None)
        diff = time.time() - startdummy
    return True

def read_sensor(sensorplugin, limit):
    """Read from a non-GPS sensor.

    Read info from a sensor. Note this is not just the value, but also the
    sensor name, units, symbol, etc. N.B. GPS data is read using `read_gps()`.

    Args:
        sensorplugin: The sensor plugin which should be read.

    Returns:
        dict The sensor data.

    """
    reading = {}
    reading["value"] = sensorplugin.getval()
    reading["unit"] = sensorplugin.valunit
    reading["symbol"] = sensorplugin.valsymbol
    reading["name"] = sensorplugin.valname
    reading["sensor"] = sensorplugin.sensorname
    reading["description"] = sensorplugin.description
    reading["readingtype"] = sensorplugin.readingtype
    if limit is not None and limit is not False:
        reading["breach"] = limit.isbreach(reading["name"], reading["value"], reading["unit"])
    else:
        reading["breach"] = False
    return reading

def read_gps(sensorplugin):
    """Read from a GPS sensor.

    Read info from a GPS sensor. Note this is not just one value, but
    multiple values for latitude, longitude, etc. N.B. Non-GPS data is
    read using `read_sensor()`.

    Args:
        sensorplugin: The sensor plugin which should be read.

    Returns:
        dict All of the sensor data elements.

    """
    reading = {}
    val = sensorplugin.getval()
    LOGGER.debug(" GPS output %s" % (val,))
    reading["latitude"] = val[0]
    reading["longitude"] = val[1]
    if not isnan(val[2]):
        reading["altitude"] = val[2]
    reading["disposition"] = val[3]
    reading["exposure"] = val[4]
    reading["name"] = sensorplugin.valname
    reading["sensor"] = sensorplugin.sensorname
    return reading

def sample():
    """Sample from sensors and record the output.

    Commence and then continue sampling from the enabled sensors and
    writing to enabled 'output' plugins. Will continue until forceably
    stopped with Ctrl+C, or it reaches the number of samples requested
    using 'stopafter' in the settings.cfg file.

    """
    msg = "Starting sampling..."
    msg = format_msg(msg, "info")
    print(msg)
    print("==========================================================")
    global samples
    greenhaslit = False
    redhaslit = False
    lastupdated = 0
    alreadysentsensornotifications = False
    alreadysentoutputnotifications = False
    if 'AVERAGEFREQ' in SETTINGS:
        countcurrent = 0
        counttarget = SETTINGS['AVERAGECOUNT']
        dataset = {}
    while True:
        try:
            curtime = time.time()
            timesincelast = curtime - lastupdated
            sampletime = None
            if timesincelast > (SETTINGS['SAMPLEFREQ'] - 0.01):
                if (timesincelast > (SETTINGS['SAMPLEFREQ'] + 0.02)) and (samples is not 0):
                    print(format_msg("Can't keep up - requested sample frequency is too fast!", "warning"))
                lastupdated = curtime
                data = []
                # Read the sensors
                failedsensors = []
                sampletime = datetime.datetime.now()
                breaches = []
                for sensor in PLUGINSSENSORS:
                    datadict = {}
                    if sensor == gpsplugininstance:
                        datadict = read_gps(sensor)
                    else:
                        datadict = read_sensor(sensor, PLUGINSSUPPORTS["limits"])
                        # TODO: Ensure this is robust
                        if (datadict["value"] is None or
                                isnan(float(datadict["value"])) or
                                datadict["value"] == 0):
                            failedsensors.append(sensor.sensorname)
                    # Average the data if required
                    if (('AVERAGEFREQ' in SETTINGS) and
                            (sensor != gpsplugininstance)):
                        identifier = datadict['sensor'] + "-"
                        identifier += datadict['name']
                        if identifier not in dataset:
                            dataset[identifier] = {}
                            temp = datadict.copy()
                            temp.pop("value", None)
                            for thekey, thevalue in temp.iteritems():
                                if thekey not in dataset[identifier]:
                                    dataset[identifier][thekey] = thevalue
                            dataset[identifier]['values'] = []
                        dataset[identifier]['values'].append(datadict["value"])
                    # Always record raw values for every sensor
                    data.append(datadict)
                    #print datadict["breach"]
                    #print "Trap -1"
                    if datadict["breach"] is True:
                        breaches.append(sensor.sensorname)
                # Record the outcome of reading sensors
                if 'AVERAGEFREQ' in SETTINGS:
                    countcurrent += 1
                if failedsensors:
                    if not alreadysentsensornotifications:
                        for j in PLUGINSNOTIFICATIONS:
                            j.sendnotification("alertsensor")
                        alreadysentsensornotifications = True
                    msg = "Failed to obtain data from these sensors: " + ", ".join(failedsensors)
                    msg = format_msg(msg, 'error')
                    logthis("error", msg)
                    if SETTINGS['PRINTERRORS']:
                        print(msg)
                else:
                    msg = "Data successfully obtained from all sensors."
                    msg = format_msg(msg, 'success')
                    logthis("info", msg)

                # Output data
                try:
                    # Averaging
                    if 'AVERAGEFREQ' in SETTINGS:
                        if countcurrent == counttarget:
                            data = average_dataset(identifier, dataset)
                            dataset = {}
                    if (('AVERAGEFREQ' in SETTINGS and
                        countcurrent == counttarget) or
                            ('AVERAGEFREQ' not in SETTINGS)):
                        if 'AVERAGEFREQ' in SETTINGS:
                            countcurrent = 0
                        # Output the data
                        outputsworking = True
                        for i in PLUGINSOUTPUTS:
                            LOGGER.debug(" Dataset to output to " + str(i) + ":")
                            LOGGER.debug(" " + str(data))
                            if i.output_data(data, sampletime) == False:
                                outputsworking = False
                        # Record the outcome of outputting data
                        if outputsworking:
                            msg = "Data output in all requested formats."
                            msg = format_msg(msg, 'success')
                            logthis("info", msg)
                            if (SETTINGS['GREENPIN'] and
                                    (SETTINGS['SUCCESSLED'] == "all" or
                                    (SETTINGS['SUCCESSLED'] == "first" and
                                        not greenhaslit))):
                                led_on(SETTINGS['GREENPIN'])
                                greenhaslit = True
                            if (breaches != [] and SETTINGS['LIMITLED'] == "yes"):
                                led_on(SETTINGS['REDPIN'])
                                redhaslit = True
                            else:
                                led_off(SETTINGS['REDPIN'])
                        else:
                            if not alreadysentoutputnotifications:
                                for j in PLUGINSNOTIFICATIONS:
                                    j.sendnotification("alertoutput")
                                alreadysentoutputnotifications = True
                            msg = "Failed to output in all requested formats."
                            msg = format_msg(msg, 'error')
                            logthis("error", msg)
                            if SETTINGS['PRINTERRORS']:
                                print(msg)
                            if (SETTINGS['REDPIN'] and
                                    (SETTINGS['FAILLED'] in ["all", "constant"] or
                                    (SETTINGS['FAILLED'] == "first" and
                                        not redhaslit))):
                                led_on(SETTINGS['REDPIN'])
                                redhaslit = True

                except KeyboardInterrupt:
                    raise
                except Exception as excep:
                    msg = "Exception during output: %s" % excep
                    msg = format_msg(msg, 'error')
                    logthis("error", msg)
                else:
                    # Delay before turning off LED
                    time.sleep(1)
                    if SETTINGS['GREENPIN']:
                        led_off(SETTINGS['GREENPIN'])
                    if (SETTINGS['REDPIN'] and
                            SETTINGS['FAILLED'] != "constant" and
                                (breaches == [] or SETTINGS['LIMITLED'] != "yes")):
                        led_off(SETTINGS['REDPIN'])
                samples += 1
                if samples == SETTINGS['STOPAFTER']:
                    msg = "Reached requested number of samples - stopping run."
                    msg = format_msg(msg, 'sys')
                    print(msg)
                    logthis("info", msg)
                    stop_sampling(None, None)
            try:
                time.sleep(SETTINGS['SAMPLEFREQ'] - (time.time() - curtime))
            except KeyboardInterrupt:
                raise
            except Exception:
                pass # fall back on old method...
        except KeyboardInterrupt:
            stop_sampling(None, None)

def average_dataset(identifier, dataset):
    """Average a dataset.

    Take a dataset consisting of 'n' separate readings, and calculate
    the mean across those readings. The dataset will be a dict of dicts;
    each element in the first dict is a single time point in the set to
    be averaged. Each of these single time points is a dict which
    contains one reading for each of the enabled sensors.

    Args:
        identifier: The unique identifier for the sensor and property
            being averaged.
        dataset: The list of 'n' separate time points to be averaged.

    Returns:
        list The averaged data.

    """
    totals = {}
    numberofsamples = {}
    # For each identifier, sum the indidivual values in the
    # dataset[identifier]['values'] list.
    # Count the number of samples as we go along, in case one sensor has
    # missed any readings.
    for identifier, properties in dataset.iteritems():
        totals[identifier] = 0
        numberofsamples[identifier] = 0
        for value in properties['values']:
            if value != "-" and value is not None and not isnan(value):
                totals[identifier] += value
                numberofsamples[identifier] += 1
    # For each identifier, divide the sum by the number of samples
    for identifier, total in totals.iteritems():
        dataset[identifier]['value'] = total / numberofsamples[identifier]
        dataset[identifier]['readingtype'] = "average"
    # Re-format to that expected by output_data() methods of the output
    # plugins
    formatted = []
    for identifier in dataset:
        dataset[identifier]['identifier'] = identifier
        formatted.append(dataset[identifier])
    return formatted

def stop_sampling(dummy, _):
    """Stop a run.

    Stop a run by shutting down the GPS controller, turning off LEDs and
    then printing a summary of the run statistics. Note that this can be
    run either programatically because we have completed the requested
    number of samples, or manually because the user pressed Ctrl+C
    (KeyboardInterrupt). If it is a KeyboardInterrupt, then the
    two parameters are passed to this method automatically (see
    https://docs.python.org/3/library/signal.html#signal.signal). They
    are not actually used by our code; they're named 'dummy' and '_' so
    that pylint ignores the fact that we don't ever use them (see Q4.5
    on http://docs.pylint.org/faq.html)

    """
    print("")
    msg = "Sampling stopping..."
    msg = format_msg(msg, 'sys')
    print(msg)
    logthis("info", msg)
    try:
        if gpsplugininstance:
            gpsplugininstance.stopcontroller()
    except NameError:
        # If GPS socket isn't set, gpsplugininstance won't exist. It
        # raises it's own error and quits before here, but quit again
        # just in case.
        sys.exit(1)
    led_off(SETTINGS['GREENPIN'])
    led_off(SETTINGS['REDPIN'])
    timedelta = datetime.datetime.utcnow() - STARTTIME
    hours, remainder = divmod(timedelta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    msg = "This run lasted " + str(hours) + "h " + str(minutes) + "m "
    msg += str(seconds)  + "s, and consisted of " + str(samples) + " samples."
    msg = format_msg(msg, 'sys')
    print(msg)
    logthis("info", msg)
    msg = "Sampling stopped."
    msg = format_msg(msg, 'sys')
    print(msg)
    logthis("info", msg)
    sys.exit(1)

if __name__ == '__main__':
    # Set up and execute an AirPi sampling run.

    CFGPATHS = set_cfg_paths()

    LOGGER = set_up_logger()
    # For debugging / logging, preferably set "debug" to "yes" in
    # the cfg/settings.cfg file. Alternatively, uncomment below:
    #logging.basicConfig(level=logging.DEBUG)


    #Set variables
    gpsplugininstance = None
    SETTINGS = set_settings()
    notificationsMade = {}
    samples = 0
    STARTTIME = datetime.datetime.utcnow()

    # Add Git commit ref to debug output
    p1 = subprocess.Popen(["git", "log"], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["head", "-1"], stdin=p1.stdout, stdout=subprocess.PIPE)
    p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
    commit,err = p2.communicate()
    logthis('debug', "Git " + commit)
    for theprocess in [p1, p2]:
        if theprocess.stdin:
            theprocess.stdin.close()
        if theprocess.stdout:
            theprocess.stdout.close()
        if theprocess.stderr:
            theprocess.stderr.close()
        try:
            theprocess.kill()
        except OSError:
            # can't kill a dead proc
            pass

    #Set up plugins
    PLUGINSSUPPORTS = set_up_supports()
    PLUGINSSENSORS = set_up_sensors()
    PLUGINSOUTPUTS = set_up_outputs()
    PLUGINSNOTIFICATIONS = set_up_notifications()

    # Set up metadata
    METADATA = set_metadata()
    if any_plugins_enabled(PLUGINSOUTPUTS, 'output'):
        output_metadata(PLUGINSOUTPUTS, METADATA)

    led_setup(SETTINGS['REDPIN'], SETTINGS['GREENPIN'])

    # Register the Ctrl+C signal handler
    signal.signal(signal.SIGINT, stop_sampling)

    print("==========================================================")
    print(format_msg("Setup complete.", 'success'))

    # Do Help
    if SETTINGS["HELP"]:
        print("==========================================================")
        print(format_msg("HELP", 'loading'))
        print(format_msg("Your sensors are named as follows:", "help"))
        for sensor in PLUGINSSENSORS:
            print("         " + sensor.get_sensor_name())
        for output in PLUGINSOUTPUTS:
            if callable(getattr(output, "get_help", None)):
                print(format_msg(output.get_help(), "help"))

    # Wait until the start of the next minute
    if SETTINGS["WAITTOSTART"]:
        delay_start()

    if SETTINGS['DUMMYDURATION'] != 0:
        dummy_runs(SETTINGS['DUMMYDURATION'])

    # Sample!
    sample()
