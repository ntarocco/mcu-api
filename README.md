MCU API
===
## Description

MCU API project implements the API for videoconference Codian MCU devices from [CISCO Tandberg](http://www.ivci.com/videoconferencing-tandberg-video-conferencing-network-infrastructure.html) in Python.
A smaller set of API is implemented for devices with software version 2.8, but you can find the full documentation for version
2.8 and 2.9 under the docs folder.


MCU API is a watchdog to monitor participants connected to conferences. It allows to retrieve the status of participants and monitor the video transmission's status. When a participant is disconnected, it will be automatically re-connected. If the video transmission is frozen, the participant is disconnected and re-connected.
In case of any error, an email is sent to the senders set in the script configuration. To avoid e-mail spam, a logging filter is implemented to send emails every hour.


## Installation

There are no external libraries to be installed. After cloning the repo, create your conf.py (from the conf.py.sample)
and set your parameters.
The project folder has to be writable because the script will create two folders, temp and logs.
If you want to set-up the watchdog, create a cron job to be run every 1/5 mins.


## Extend

To extend the API, you can implement them in the api.py classes, inside Common class or creating a new class for a specific software version.
Create then another module to call the new API implemented.
