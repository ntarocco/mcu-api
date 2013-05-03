#
# MCU watchdog
# This sript checks if the conferences set in the conf file have all the participants connected
# and with video ok (not frozen). In case of problem, it disconnect an re-connect the client.
# This script should be run every few minutes by a cron job.
# It uses the 'temp' local folder to save temporary plate.
#

import json
from logger import logger
import os
import sys
import time

import conf
from api import API

def get_video_packets(conference_name, participant_name):
    """
        Read the local temporary file (if present) to return the video packets
        received for the participant at the previous execution.
        If the file does not exists, return 0.
    """
    file_path = os.path.join('temp', 'tracked_video_packets.temp')
    if os.path.exists(file_path):
        fp = open(file_path)
        d = json.load(fp)
        fp.close()

        if conference_name in d and participant_name in d[conference_name]:
            return long(d[conference_name][participant_name])

    return 0

def set_video_packets(conference_name, participant_name, video_packets):
    """
        Save the current video packets for a participant.
    """
    # open the file
    file_path = os.path.join('temp', 'tracked_video_packets.temp')
    if os.path.exists(file_path):
        fp = open(file_path)
        d = json.load(fp)
        fp.close()
    else:
        d = dict()

    if conference_name in d:
        d[conference_name][participant_name] = video_packets
    else:
        d[conference_name] = {
            participant_name: video_packets
        }
    logger.debug("Writing new video packets dict: %s" % d)

    fp = open(file_path, 'w')
    json.dump(d, fp, sort_keys=True, indent=4, separators=(',', ': '))
    fp.close()

def _connect_participant(participant):
    """
        Connect a participant to the current conference.
    """
    logger.info("Participant %s not connected. Connecting..." % participant['name'])
    api.participant_connect(participant['name'])
    # sleep to give time to MCU to connect the participant
    time.sleep(5)
    # restore the layout of this participant in the conference
    logger.info("Restoring layout of participant %s with index %s" % (participant['name'], participant['layout_index']))
    api.restore_layout(participant['name'], participant['layout_index'])

####################################################################################

if __name__ == '__main__':

    # check if logs and temp folder exit
    if not os.path.exists('logs'):
        os.mkdir('logs')
    if not os.path.exists('temp'):
        os.mkdir('temp')

    try:
        # check if the conferences in conf are running correctly
        for conference in conf.WATCHDOG_CONFERENCES:
            # get the API instance
            api = API.get_instance(conference['name'])
            # check if the conference is active
            status = api.get_conference_status()

            if status['conferenceActive']:

                # lock the conference
                if not status['locked'] and conference['locked']:
                    api.lock_conference(conference['name'])

                # for each participants, check if it is connected
                for participant in conference['participants']:
                    details = api.get_participant_status(participant['name'])
                    if details['callState'] != "connected":
                        # participant is not connected, connected it
                        _connect_participant(participant)
                        # re-get the status of the participant
                        details = api.get_participant_status(participant['name'])
                    else:
                        # connect but get video packets from previous execution to see if video is frozen
                        previous_packets = get_video_packets(conference['name'], participant['name'])
                        # check if video is frozen comparing the number of current received packets with the previous execution
                        if long(details['videoRxReceived']) <= previous_packets:
                            # it looks like everything is frozen here
                            logger.error("It looks like the participant '%s' in the conference '%s' is frozen. It will be now disconnected and re-connected" % (participant['name'], conference['name']))
                            # disconnect the participant
                            api.participant_disconnect(participant['name'])
                            time.sleep(5)
                            # re-connect
                            _connect_participant(participant)
                            # re-get the status of the participant
                            details = api.get_participant_status(participant['name'])

                    # save current video packets
                    set_video_packets(conference['name'], participant['name'], details['videoRxReceived'])

            else:
                logger.error("The conference %s is not connected" % conference['name'])
    except Exception as err:
        logger.error("Exception occurred: %s" % err)