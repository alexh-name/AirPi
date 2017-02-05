\# ==========================================================================  
\# File:     useage.md  
\# Purpose:  Instructions for using AirPi software.  
\# Author:   Haydn Williams <pi@hwmail.co.uk>  
\# Date:     December 2014  
\# ==========================================================================  

# AirPi Software Usage Instructions

## Index
1. [About](#about)
1. [Overview](#overview)
1. [Starting and Stopping Sampling](#sampling)
1. [Software Updates](#updates)
1. [Settings](#settings)
1. [Pre-defined Sensors](#sensors)
1. [Pre-defined Outputs](#outputs)
1. [Pre-defined Notifications](#notifications)
1. [Troubleshooting](#troubleshooting)
1. [Defining Custom Sensors](#customSensors)
1. [Defining Custom Outputs](#customOutput)


## <a id="about"></a>About
This fork of the AirPi software is held on GitHub at
http://github.com/haydnw/AirPi

This document assumes that the software has been installed in the default
location, which is `/home/pi/AirPi` and that you have added that directory to
your `$PATH` variable; this can be done by adding the following line to
~/.profile:
```shell
PATH="/home/pi/AirPi:$PATH"
```

## <a id="overview"></a>Overview
The AirPi software consists of four main parts:
* "sensor" plugins define the sensors used to collect readings of individual
  phenomena by the AirPi.
* "output" plugins define how the information obtained from sensors should be
  displayed on screen, saved to file, or posted to a web service.
* "notification" plugins define how alerts should be sent if the AirPi experiences
  an error.
* The `airpictl.sh` shell script controls the starting and stopping of the AirPi,
  and fits the sensor, output and notification information together into a single
  system.

## <a id="sampling"></a>Starting and Stopping Sampling
The software is controlled using the script named `airpictl.sh`. It has three
sampling modes, to deal with various situations. The sampling mode should be
chosen based on whether you need to do anything else while logged in to the
Raspberry Pi, and whether you are logged in directly or via SSH. The three
sampling modes are:
+ **normal** - Runs in the foreground; you cannot do anything else while the
sampling is under way.
+ **bg** - Runs in the background while you are logged in. You can do other
things and the sampling will continue as long as you are logged in. If you log
out, the sampling will stop.
+ **unatt** - Runs unattended in the background even if you log out. You can do
other things while logged in, and you even can log out and then back in again
later. The sampling will only stop if you specifically request it to.

To start sampling, run the script and append the sampling mode after it:
```shell
airpictl.sh normal
airpictl.sh bg
airpictl.sh unatt
```

To stop sampling, either press `Ctrl+C` when running in 'normal' mode, or use
the `airpictl.sh` script to stop background or unattended runs. Note that this
must be done as a superuser:
```shell
cd ~/AirPi
sudo ./airpictl.sh stop
```

To check whether the AirPi is sampling, run:
```shell
airpictl.sh status
```

## <a id="updates"></a>Software Updates
To check the software version, run:
```shell
airpictl.sh version
```

To update to the latest version, run:
```shell
git pull origin
```
**Note:** This will over-write all of your existing settings and any other
customisation (*e.g.* new modules you have written). Be sure to back them up
first if you want to keep them.

## <a id="settings"></a>Settings
Settings are defined in the `settings.cfg` file, which can be found in the `cfg`
directory. Values do not need any quote marks around them. Strings may include
spaces. There is equivalence between `yes`,`on`, and `true` and between `no`,`off`, and `false`;
these are not case-sensitive. Comments take an entire line, and begin with a
hash (`#`).

There are a number of sections within the `settings.cfg`:

**\[Sampling\]**  
*Controls frequency and duration of sampling.*  
This section controls the frequency and duration of the sampling, and features
relating to the collection of average data rather than point data.
+ `sampleFreq` specifies how often readings should be taken (in seconds). It is
recommended that you do not specify a duration of less than five seconds, as
unpredictable behaviour may result. This *may* be due to a Raspberry Pi bug
involving clock-stretching on the I2C bus:
  + https://dl.dropboxusercontent.com/u/3669512/2835_I2C%20interface.pdf
  + http://www.advamation.com/knowhow/raspberrypi/rpi-i2c-bug.html
  + http://elinux.org/BCM2835_datasheet_errata#p35_I2C_clock_stretching
+ `stopafter` allows you to stop sampling after the specified number of samples
have been taken. Remember that you have used `sampleFreq` to determine the time
between samples, so this effectively allows you to stop sampling after a
certain time period too. Set this to `0` (zero) to continue indefinitely.
+ `averageFreq` specifies how often, in seconds, an average reading should be
calculated from point readings. For example, if `sampleFreq` is set to `10` and
*averageFreq* is set to `30`, the system will average three point readings to
produce a single averaged reading every 30 seconds. Set this to `0` (zero) to
disable averaging.
+ `dummyduration` specifies how long, in seconds, the system should obtain
sensor readings *without recording them* ('dummy' runs). This allows you
initialise the system prior to recording data. Set this to `0` (zero) to disable
initialising 'dummy' runs.
+ `printUnaveraged` is not used at present.


**\[LEDs\]**  
*Controls LED behaviour.*  
This section controls the behaviour of the red and green LEDs on the AirPi (*N.B.*
not the Raspberry Pi LEDs).
+ `redPin` specifies the wiring pin used for the red LED.
+ `greenPin` specifies the wiring pin used for the green LED.
+ `successLED` specifies the behaviour of the green LED.
  + `all` will flash the LED each time a successful sample is taken (no
errors).
  + `first` will flash the LED when the first successful sample is taken, but
then there will be no further flashes.
+ `failLED` specifies the behaviour of the red LED.
  + `all` will flash the LED each time a failed sample is taken (one or more
  errors).
  + `first` will flash the LED when the first failed sample is taken,
  but then there will be no further flashes.
  + `constant` will light the LED when the first failed sample is taken (one or
  more errors) and it will remain lit until the sampling is stopped.

**\[Misc\]**  
*Various miscellaneous settings.*  
This section controls a number of other settings.
+ `printErrors` specifies whether or not error messages should be printed to
screen.
If enabled, you may find that error messages are printed in amongst screen
output from your enabled output plugins.
+ `bootstart` specifies whether the AirPi should start automatically sampling
as soon as it boots up. See the `boot` directory for more information.
+ `operator` specifies the name of the operator who is running the AirPi
sampling.
This information is included in output if metadata is requested.
+ `help` determines whether extra text should be printed during sampling to
provide further helpful information about the run.

**\[Debug\]**  
*Debug messages and associated options.*  
This section controls options relating to debugging output and is only likely
to be useful if you experience any problems with the software, or do your own
development of it.
+ `debug` specifies whether 'debug mode' should be active; if so, many
diagnostic messages will be printed to screen during a run.
+ `waittostart` specifies whether sampling will be delayed until the 'start' of
a minute, *i.e.* zero seconds. It can be useful to turn this off to save time
when debugging.


## <a id="sensors"></a>Pre-defined Sensors
Sensors are defined in the `sensors.cfg` file, which can be found in the `cfg`
directory. A number of sensors are already defined in the file
[on GitHub](http://github.com/haydnw/airpi/tree/development2/cfg/sensors.cfg).
They are described below, and salient features noted. For information about
defining custom sensors, see the [Defining Custom Sensors](#customSensors)
section of this file.

Values in the file do not need any quote marks around them. Strings may include
spaces (except for `sensorname` and `measurement`). There is equivalence
between `yes`,`on`, and `true` and between `no`,`off`, and `false`;
these are not case-sensitive. Comments take an entire line, and begin with a
hash (`#`).

Most changes to this file will be to enable or disable individual sensors. It
is unlikely that many changes will need to be made once initial sensor details
have been entered (or if using existing sensor definitions).

Note that although each definition is referred to as a 'sensor', they actually
could more accurately be referred to as 'measurements'. For example, in the
standard setup there are two definitions relating to the DHT22 sensor, because
that particular physical sensor reads out both temperature and humidity.

**\[BMP085-temp\]** ([datasheet](http://github.com/haydnw/airpi/tree/development2/docs/datasheets/BMP085.pdf))  
*Temperature measurement from the BMP085 sensor.*  
Readings are in degrees Fahrenheit or Celcius. Usually reads 2.0 to 2.2 degrees
Celcius higher than the DHT22 sensor.

**\[BMP085-pres\]** ([datasheet](http://github.com/haydnw/airpi/tree/development2/docs/datasheets/BMP085.pdf))  
*Pressure measurement from the BMP085 sensor.*  
Readings are in [hectoPascals](http://en.wikipedia.org/wiki/Pascal_(unit)),
which are [equivalent to millibars](http://en.wikipedia.org/wiki/Pascal_(unit)#Hectopascal_and_millibar_units).

**\[MCP3008\]** ([datasheet](http://github.com/haydnw/airpi/tree/development2/docs/datasheets/MCP3008.pdf))  
*Analogue-to-digital convertor.*  
Not a real sensor - this is the Analogue-to-digital converter (ADC) and doesn't
give any readings.

**\[DHT22-hum\]** ([datasheet](http://github.com/haydnw/airpi/tree/development2/docs/datasheets/DHT22.pdf))  
*Humidity measurement from the DHT22 sensor.*  
Readings are as % humidity. Manufacturer recommends not reading from this
sensor more than once every two seconds.

**\[DHT22-temp\]** ([datasheet](http://github.com/haydnw/airpi/tree/development2/docs/datasheets/DHT22.pdf))  
*Temperature measurement from the DHT22 sensor.*  
Readings are in degrees Fahrenheit or Celcius. Manufacturer recommends not
reading from this sensor more than once every two seconds.

**\[LDR\]** ([datasheet](http://github.com/haydnw/airpi/tree/development2/docs/datasheets/LDR.pdf))  
*Generic light dependent resistor.*  
There is no specific model for the LDR. It is present on version 1.2 and 1.4
AirPi boards. Resistance goes down as light level increases, and *vice versa*.

**\[TGS2600\]** ([datasheet](http://github.com/haydnw/airpi/tree/development2/docs/datasheets/TGS2600.pdf))  
*Volatile Organic Compound (VOC) sensor.*  
Measures methane, carbon monoxide, iso-butane, ethanol and Hydrogen. This
sensor is not included on AirPi boards by default, but there is a space for it
to be added.

**\[MiCS-2710\]** ([datasheet](http://github.com/haydnw/airpi/tree/development2/docs/datasheets/MiCS-2710.pdf))  
*Nitrogen Dioxide sensor.*  

**\[MiCS-5525\]** ([datasheet](http://github.com/haydnw/airpi/tree/development2/docs/datasheets/MiCS-5525.pdf))  
*Carbon monoxide sensor.*  

**\[Microphone\]**
*Noise level sensor.*  
Included on the v1.2 and v1.4 AirPi boards.

**\[UVI-01\]** ([datasheet](http://github.com/haydnw/airpi/tree/development2/docs/datasheets/UVI-01-E.pdf))  
*Ultraviolet light sensor.*  
Included on the v1.0 AirPi board, but replaced by the LDR on subsequent
revisions.

**\[Raingauge\]**


**\[GPS\]** ([datasheet](http://github.com/haydnw/airpi/tree/development2/docs/datasheets/GPS.pdf))  
GPS location sensor.  


## <a id="outputs"></a>Pre-defined Outputs
Output plugins are defined in the `outputs.cfg` file, which can be found in the
`cfg` directory. A number of output plugins are already defined in the file
[on GitHub](http://github.com/haydnw/airpi/tree/development2/cfg/outputs.cfg).
They are described below, and salient features noted. For information about
defining custom outputs, see the [Defining Custom Outputs](#customOutput)
section.

Values in the file do not need any quote marks around them. Strings may
include spaces. There is equivalence between `yes`,`on`, and `true` and between
`no`,`off`, and `false`; these are not case-sensitive. Comments take an entire line, and
begin with a hash (`#`).

Most changes to this file will be to enable or disable individual output
plugins, or change the location or format of their output.

###Common Options
The following options are common to a number of output plugins:
+ `filename` specifies the name of the Python script file for the output
  plugin. No file extension or path details are required.
+ `enabled` specifies whether or not the output plugin is enabled.
+ `calibration` specifies whether or not user-defined calibration functions
  should be applied to raw data.
+ `metadata` specifies whether or not metadata should be output by the
  plugin (if it is capable of doing so).
+ `outputDir` specifies the directory where the output plugin should save any
  output file(s).
+ `outputFile` specifies the filename where the output plugin should save any
  output. Use `<hostname>` to automatically include
  the hostname of the Raspberry Pi in the filename. Use `<date>` (no
  apostrophes) to automatically include the start date of the sampling in the
  filename.
+ `target` specifies where the output plugin sends data to. Should be `screen`,
  `internet`, `file`, or `support`.

**\[Print\]**  
*Print details to screen.*  
Print data to [stdout](http://en.wikipedia.org/wiki/Standard_streams#Standard_output_.28stdout.29),
which is usually the screen.
+ `format` specifies the format in which the data should be output to screen.
  + `friendly` prints easily readable titles and values.
  + `csv` prints information in Comma-Separated Value (CSV) format.

**\[CSVOutput\]**  
*Write information to .csv file.*  
Write data to a Comma-Separated Value (CSV) file. Most of the Common Options
described earlier in this document are used with this plugin; there are no
options unique to this plugin.

**\[JSONOutput\]**  
*Write information to .json file.*  
Write data to a JavaScript Object Notation (JSON) file. Most of the Common
Options described earlier in this document are used with this pluin; there are
no options unique to this plugin.

**\[HTTP\]**  
*Display information on a local website.*  
Display information on an HTTP server created on the Raspberry Pi. This will
usually output information at `http://127.0.0.1:8080`, but running the software
with `help = on` in `cfg/settings.cfg` will display the network
address.
+ `wwwPath` is the folder where web server files can be found. The default is
  `www`, which works fine for most applications. If you are using the HTTP
  plugin with the AirPi "bootstart" feature then you must declare `wwwPath` as
  a full explicit path (*e.g.* `/home/myname/AirPi/www`). If you do not, AirPi
  will assume that the full explicit path is `/home/pi/AirPi/www`.
+ `port` is the port number on which the website should be served. The default
  is 8080.
+ `history` specifies whether or not historical data should be stored / loaded.
+ `historySize` specifies how many historical readings should be stored / loaded.
+ `historyInterval`
+ `historyCalibrated` specifies whether or not data in the history should be
  calibrated according to functions defined in the `\[Calibration\]` plugin.
+ `title` specifies the title to be used on the HTML pages.
+ `about` specifies the text to be used in the information section of the
  pages.

**\[Xively\]**  
*Output information to a [Xively](http://www.xively.com) feed.*  
Output information to a feed on the Xively website. Individual Xively streams
within the target feed must have exactly the same names as the AirPi sensors.
Running the software with `help = on` in `cfg/settings.cfg` will
print the sensor names to facilitate their duplication in Xicely.
+ `APIKey` specifies the Xively API key to be used. This is defined by Xively
  and can be found in your account details on the Xively website.
+ `FeedID` specifies the ID of the specific Xively feed to which data should be
  published.  This is defined by Xively and can be found in your account
  details on the Xively website.

**\[dweet\]**  
*Output information to a [Dweet](http://dweet.io) feed.*  
Output information to a feed on the Dweet website.
+ `thing` is the name under which the feed will be posted on the Dweet website.

**\[Thingspeak\]**
*Output information to a [Thingspeak](https://thingspeak.com) feed.*
Output information to a feed on the Thingspeak website.
+ `apikey` is the API key used to define the target feed on Thingspeak.

**\[Ubidots\]**
*Output information to an [Ubidots](http://ubidots.com) feed.*
Output information to a feed on the Ubidots website.
+ `token` is the Ubidots account token.
+ `ID-<sensor>` is the Ubidots feed ID for each individual metric.
+ `showcost` determines whether to show the cost of each upload.

**\[RRDOutput\]**  
*Save information to an [RRD](http://oss.oetiker.ch/rrdtool/) database.*  
Save information on a rotating basis to a Round-Robin Database (RRD) file. RRD
is reasonably complex, and further details about the plugin can be found in the
Python module itself (outputs/rrdoutput.py). This plugin provides only basic
RRD support; for better support try https://www.cccmz.de/projekt-airpi/

**\[plot\]**  
*Plot information to a graph on screen.*  
Plot information to an ASCII line, bar or scatter graph on [stdout](http://en.wikipedia.org/wiki/Standard_streams#Standard_output_.28stdout.29),
which is usually the screen. You can plot only one parameter at a time. Running
the software with `help = on` in `cfg/settings.cfg` will print
the sensor names to facilitate entry of the correct name in this section. If
this plugin is enabled at the same time as the `[print]` plugin, this plugin will
be automatically disabled (you can only display one thing at a time on screen!).
+ `metric` is the name of the sensor whose data should be plotted.

**\[sqldatabase\]**
*Output information to a MySQL database.*
Output all information except GPS to a MySQL database. The database must include
the following field names/types:
```
Station       VARCHAR(20)
Sample_Time   DATETIME
Sensor        VARCHAR(25)
Value         DOUBLE
Unit          VARCHAR(25)
```
See [this link for a script](http://airpi.freeforums.net/post/1127/thread)
to create an appropriate database.
+ `station` is the name of the AirPi station/location.
+ `host` is the hostname of the machine where the MySQL database sits.
+ `db` is the name of the database on the MySQL host.
+ `user` is the username for connecting to the database.
+ `passwd` is the password for connecting to the database.
If your data is top secret / mission critical then please note that the password
for the database is just held in plain text and is therefore visible to anyone
who can access your AirPi files. There is no encryption on the password or data
if sent to a MySQL host on a different machine.

**\[Dashboard\]**
*Show limit breach information on screen.*
User green and red on screen to represent whether limits defined using the \'limits\'
support plugin have been breached or not. All limits are defined using the \'limits\'
support plugin; this output plugin therefore has no options. This output plugin
will not work if the \'limits\' support plugin is not enabled, or doesn\'t have any
limits set.

## Pre-defined Supports

**\[Calibration\]**
*Change raw data by applying custom functions.*

# DO NOT ASSUME ANY PRE-DEFINED FUNCTIONS BELOW ARE CORRECT!                 #
# EVERY SENSOR IS DIFFERENT SO YOU CAN'T JUST COPY SOMEONE ELSE'S FUNCTIONS! #
# THE ONLY WAY TO ACCURATELY CONVERT ANY RESISTANCE TO AN ABSOLUTE VALUE SUCH AS PPM IS TO CALIBRATE YOUR OWN SENSOR AGAINST A KNOWN 'GOOD' SENSOR/METER IN SEVERAL KNOWN CONCENTRATIONS OF THE TARGET GAS, THEN USE THE KNOWN 'GOOD' READINGS TO DETERMINE THE CORRECTION FUNCTION FOR YOUR AIRPI. 

This plugin applies a function to raw data obtained from sensors, with the aim
of allowing the correction of erroneous data via offsets, or conversion from one unit to
another. For calibration to work you must define a function for the
relevant sensor plugin and then enable calibration within the options for the
output plugin where calibration should be applied.
To define a calibration function, use the following syntax:
```
func_<sensor_name> = <function>,<units>
```
Where:
+ `<sensor_name>` is the name of the sensor metric to which the calibration should be
  applied. Note that the *name* is different from the *sensor*. You can obtain the name by
  switching debug ON in `cfg/settings.cfg` and looking at the details as the sensor
  is initialised at the start of the run.
+ `<function>` is the correction function which should be applied to the raw
  data. Use the letter `x` to represent the raw data (*e.g.* the function `2*x`
  would double the raw value).
+ `<units>` is the name of the units in which the corrected data is measured.

Example: reduce temperature from BMP085 sensor by 3 degrees Celcius:
```
func_Temperature-BMP = x-3,Corrected Deg C
```

**\[Limits\]**
This plugin allows you to set an upper limit for sensor readings. If a reading
is higher than the defined limit, and warning will be shown. Note that the
style of the warning is determined entirely by the output plugins being used at the time;
this plugin does not handle actually making the warnings, it merely reports whether or
not the limits have been breached.
+ `limit_Nitrogen_Dioxide` is the upper limit for NO2.
+ `limit_Carbon_Monoxide` is the upper limit for CO.
+ `limit_Air_Quality` is the upper limit for Air Quality.
+ `limit_Relative_Humidity` is the upper limit for Relative Humidity.
+ `limit_Pressure` is the upper limit for barometric Pressure.
+ `limit_DHT22-Temperature` is the upper limit for temperature on the DHT22 sensor.
+ `limit_BMP085-Temperature` is the upper limit for temperature on the BMP085 sensor.

## <a id="notifications"></a>Pre-defined Notifications
Notification plugins are defined in the `notifications.cfg` file, which can be found in the
`cfg` directory. A number of notification plugins are already defined in the file
[on GitHub](http://github.com/haydnw/airpi/tree/development2/cfg/notifications.cfg).
They are described below, and salient features noted. For information about
defining custom notifications, see the [Defining Custom Notifications](#customNotifications)
section.

Values in the file do not need any quote marks around them. Strings may
include spaces. There is equivalence between `yes`,`on`, and `true` and between
`no`,`off`, and `false`; these are not case-sensitive. Comments take an entire line, and
begin with a hash.

Most changes to this file will be to enable or disable individual notification
plugins, or change parameters.

**Common Options**
The following options are common to a number of notification plugins:
+ `msgalertsensor` specifies the text of the notification message which will be
  sent when a sensor fails.
+ `msgalertoutput` specifies the text of the notification message which will be
  sent when an output plugin fails.
+ `msgdata` specifies the text of the notification message which will be sent
  when a data change notifications is triggered.
+ `filename` specifies the name of the Python script file for the notification
  plugin. No file extension or path details are required.
+ `enabled` specifies whether or not the notification plugin is enabled.
+ `target` specifies where the notification plugin sends data to. Should be
  `screen`, `internet`, `file`, or `support`.

**\[Tweet\]**  
*Send notifications by Tweeting.*  
Send notifications by Tweeting to a specific Twitter account.
+ `consumerkey` specifies the API key provided by Twitter.
+ `consumersecret` specifies the secret provided by Twitter.

**\[Email\]**  
*Send notifications by email.*  
Send notifications by sending emails to a specific email address.
+ `toaddress` specifies the email address to which notifications are sent.
+ `fromaddress` specifies the email address from which notifications are sent.
+ `fromname` specifies the name from whom emails are sent.
+ `smtpserver` specifies the SMTP server through which emails are sent.
+ `smtpport` specifies the port number on the SMTP server through which emails are sent.
+ `smtptls` specifies whether [TLS](http://en.wikipedia.org/wiki/Transport_Layer_Security#Other_uses) 
  is enabled on the connection.
+ `smtpuser` specifies the username used to authenticate against the SMTP server.
+ `smtppass` specifies the password used to authenticate against the SMTP server.

**\[SMS\]**  
*Send notifications by SMS (text message).*  
Send notifications by sending SMS text messages to a specific telephone number.
This is provided using the [TextLocal](http://textlocal.com) service; an account
is required and charges may apply.
+ `user` specifies the username for the TextLocal account.
+ `hash` specifies the hash for the TextLocal account.
+ `to` specifies the telephone number to which notifications should be sent.


## <a id="troubleshooting"></a>Troubleshooting
+ Ensure that `airpictl.sh` has been added to your `$PATH` environment variable.
+ Ensure that scripts are executable.

## <a id="customSensors"><a>Defining Custom Sensors
Custom sensors can be defined in the `cfg/sensors.cfg` file. Such an
entry only tells the AirPi that a sensor exists; you must still write
the supporting Python code to tell the AirPi how to read data from the sensor.
A Python template/example can be found in the `docs` folder.

Values in the `sensors.cfg` file do not need any quote marks around them.
Strings may include spaces. There is equivalence between `yes`,`on`, and `true` and between
`no`,`off`, and `false`; these are not case-sensitive. Comments take an entire line, and
begin with a hash (`#`).

Remember that although each definition is referred to as a 'sensor', they actually
could more accurately be referred to as 'measurements'. For example, in the
standard setup there are two definitions relating to the DHT22 sensor, because
that particular physical sensor reads out both temperature and humidity.

There are a number of sections within `sensors.cfg` - each one defines a single 
measurement. The following fields are **mandatory** for every sensor
(measurement) definition:
+ `filename` specifies the name of the Python script file for the sensor. No
file extension or path details are required. All analogue sensors use the same
module; this should be set to `analogue` for all analogue sensors.
+ `enabled` specifies whether or not the sensor is enabled.
+ `sensorname` specifies the short name for the sensor. This must be unique to
this sensor. Do not include any spaces in this (use underscores if required).
Note that some sensor names are determined automatically in the relevant Python module file
(namely measurements from the DHT22 and BMP085 sensors).
+ `description` is a longer (one-sentance) description of the sensor.

The following fields may be required for some sensor definitions, but not all:
+ `measurement` specifies the phenomenon which the sensor measures. Do not
include any spaces in this (use underscores if required).
+ `adcpin` specifies the ADC pin to which an analogue sensor is connected.
+ `pulldownResistance` specifies the value of the pull-down resistor used with
  the sensor.
+ `pullupResistance` specifies the value of the pull-up resistor used with the
  sensor.
+ `pinnumber` specifies the GPIO pin which a sensor is connected to.
+ `sensorvoltage` specifies the voltage at which the sensor is running.
+ `i2cbus` specifies the port number for the i2c bus (`0` for first version
  Raspberry Pi, `1` for subsequent revisions).
+ `mslp` specifies whether Mean Sea Level Pressure should be returned instead
  of absolute local pressure (requires `altitude` to be set too).
+ `altitude` specifies the current altitude in meters, for use with `mslp` in relation to
  atmospheric pressure readings.


## <a id="customOutput"></a>Defining Custom Output Plugins
Custom output plugins can be defined in the `cfg/outputs.cfg` file. Such an
entry only tells the AirPi that an output module exists; you must still write
the supporting Python code to actually output the data in the required format
and to the required location. A Python template/example can be found in
the `docs` folder.

Values in the `outputs.cfg` file do not need any quote marks around them.
Strings may include spaces. There is equivalence between `yes`,`on`, and `true` and between
`no`,`off`, and `false`; these are not case-sensitive. Comments take an entire line, and
begin with a hash (`#`).

There are a number of sections within `outputs.cfg` - each one defines a single
output plugin. The following fields are **mandatory** for every output plugin
definition:
+ `filename` specifies the name of the Python script file for the output
  plugin. No file extension or path details are required.
+ `enabled` specifies whether or not the output plugin is enabled.
+ `calibration` specifies whether or not user-defined calibration functions
  should be applied to raw data.
+ `description` is a longer (one-sentence) description of the sensor.

There are a number of other parameters which can be defined for each output
plugin. These can be customised for each individual plugin and are therefore
beyond the scope of this document.

## <a id="customNotifications"></a>Defining Custom Notification Plugins
Custom notification plugins can be defined in the `cfg/notifications.cfg` file. Such an
entry only tells the AirPi that an notification module exists; you must still write
the supporting Python code to actually send the notification. A Python template/example
can be found in the `docs` folder.

Values in the `notifications.cfg` file do not need any quote marks around them.
Strings may include spaces. There is equivalence between `yes`,`on`, and `true` and between
`no`,`off`, and `false`; these are not case-sensitive. Comments take an entire line, and
begin with a hash (`#`).

There are a number of sections within `notifications.cfg` - each one defines a single
notification plugin. The following fields are **mandatory** for every notification plugin
definition:
+ `filename` specifies the name of the Python script file for the output
  plugin. No file extension or path details are required.
+ `enabled` specifies whether or not the notification plugin is enabled.
+ `target` specifies where the notification plugin sends data to. Should be
  `screen`, `internet`, `file`, or `support`. If the target is `internet` it specifies
  that the notification plugin requires internet connectivity to function correctly. If
  it does, and there is no connectivity, the plugin will be disabled.

There are a number of other parameters which can be defined for each notification
plugin. These can be customised for each individual plugin and are therefore
beyond the scope of this document.
