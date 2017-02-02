#! /bin/bash

# =============================================================================
# File:     install.sh
# Requires: Raspbian on Raspberry Pi.
# Purpose:  An easy way to install the AirPi software.
# Comments: - Just automates the steps outlined in README.md.
#           - Installs python3 packages, because hopefully the code will be
#             updated soon!
#           - Installs to home directory of the default 'pi' user.
#           - Assumes that the Raspberry Pi is a Revision 2.0 board, i.e. the
#             I2C bus is on Port 1 (*not* Port 0 as it was on Rev. 1 boards).
#           - Includes an apt-get 'upgrade' to latest firmware.
# Author:   Haydn Williams <pi@hwmail.co.uk>
# Date:     January 2015
# =============================================================================

# Begin
echo "====================================="
echo "[AirPi] BEGINNING AIRPI INSTALLATION."
echo "====================================="
echo ""
if whiptail --title "AirPi installation" --yes-button " Heck yes! " --no-button " Erm, no thanks " --yesno "This script installs the AirPi software from github.com/haydnw/AirPi onto your Raspberry Pi.

Please read the notes below before deciding whether you want to continue with the installation.

- Installs to home directory of the default 'pi' user.
- Assumes that the Raspberry Pi is a Revision 2.0 board.
  (If not, you'll have to change the I2C port number from 1 to 0 in /boot/config.txt)
- Includes an apt-get 'upgrade' to latest software/firmware.

Start installing the AirPi software?" 18 100 ;then

	# Ensure everything is up-to-date
	echo "====================================="
	echo "[AirPi] UPDATING EXISTING PACKAGES..."
	echo "====================================="
	sudo apt-get -y update
	sudo apt-get -y upgrade
	echo "============================================"
	echo "[AirPi] FINISHED UPDATING EXISTING PACKAGES."
	echo "============================================"
	echo ""

	# Install required packages using apt-get
        # Note that git is in the list because it's not included in Jessie Lite
	echo "==========================================="
	echo "[AirPi] INSTALLING NEW REQUIRED PACKAGES..."
	echo "==========================================="
	sudo apt-get -y install python-dev python-setuptools python-requests python3-dev python3-requests libxml2-dev libxslt1-dev python-lxml i2c-tools git python-numpy
	echo ""
        sudo apt-get -y install python-smbus

	# Install Twitter support (not available via apt-get)
	easy_install Twitter
	echo "=================================================="
	echo "[AirPi] FINISHED INSTALLING NEW REQUIRED PACKAGES."
	echo "=================================================="
	echo ""

	# Enable I2C support
	echo "==============================="
	echo "[AirPi] ENABLING I2C SUPPORT..."
	echo "==============================="
	sudo echo "i2c-dev" >> /etc/modules
	sudo echo "# Enable I2C (http://www.raspberrypi.org/forums/viewtopic.php?f=28&t=97314)" >> /boot/config.txt
	sudo echo "dtparam=i2c1=on" >> /boot/config.txt # Use i2c0 if you have a Rev. 1 RPi board
	sudo echo ""                >> /boot/config.txt
	if [ -e "/etc/modprobe.d/raspi-blacklist.conf" ]
	then
        # Pre-2015 Raspbian, so raspi-blacklist still exists
        sudo sed -i 's/#i2c-bcm2708/i2c-bcm2708/g' /etc/modprobe.d/raspi-blacklist.conf
	fi
	echo "======================================"
	echo "[AirPi] FINISHED ENABLING I2C SUPPORT."
	echo "======================================"
	echo ""

	# Install AirPi software from GitHub
	echo "===================================="
	echo "[AirPi] INSTALLING AIRPI SOFTWARE..."
	echo "===================================="
	git clone https://github.com/haydnw/airpi /home/pi/AirPi
	sudo chown -R pi:pi /home/pi/AirPi
	sudo echo "export PATH=$PATH:~/AirPi" >> /home/pi/.profile
	echo "==========================================="
	echo "[AirPi] FINISHED INSTALLING AIRPI SOFTWARE."
	echo "==========================================="
	echo ""

        # Install GPS support
        if whiptail --title "AirPi installation" --yes-button " GPS please " --no-button " No thanks " --yesno "Would you like to install GPS support?" 18 100 ; then
            sudo apt-get install gpsd gpsd-clients python-gps
            sudo sed -i 's/DEVICES=""/DEVICES="/dev/ttyAMA0"/g' /etc/default/gpsd
            whiptail --title "AirPi installation" --msgbox "GPS support has been installed.

Note that after a reboot you will need to run the following command to start the GPS service on your Raspberry Pi:
sudo gpsd /dev/ttyAMA0 -F /var/run/gpsd.sock

You can then run this command to check that the GPS is working:
cgps -s" 18 100
        fi

	# Let the user know the score
	echo "======================="
	echo "[AirPi] SETUP COMPLETE."
	echo "======================="
	if whiptail --title "AirPi installation" --yes-button " Reboot now! " --no-button " Nah, later " --yesno "AirPi installation is complete.

You will need to reboot your Raspberry Pi before using the AirPi.

Have fun!  :)" 18 100 ; then
       	    sudo reboot
        else
            echo "[AirPi] Installation complete. Will not reboot."
        fi
    else
        echo "[AirPi] Installation aborted. You can stop panicking now."
    fi
