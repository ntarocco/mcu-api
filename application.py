#
# MCU watchdog
# This sript checks if the conferences set in the conf file have all the participants connected
# and with video ok (not frozen).
# This script should be run every few minutes by a cron job.
# It uses the 'temp' local folder to save temporary plate.
#

import json
import os
import time

from mcu_watchdog import conf
from mcu_watchdog.logger import logger
from mcu_watchdog.api import API


def get_av_packets(conference_name, participant_name):
    """
        Read the local temporary file (if present) to return the av packets
        received for the participant at the previous execution.
        If the file does not exists, return 0.
    """
    file_path = os.path.join('temp', 'tracked_av_packets.temp')
    if os.path.exists(file_path):
        fp = open(file_path)
        d = json.load(fp)
        fp.close()

        if conference_name in d and participant_name in d[conference_name]:
            return long(d[conference_name][participant_name]['audio']), long(d[conference_name][participant_name]['video'])

    return 0, 0


def set_av_packets(conference_name, participant_name, audio_packets, video_packets):
    """
        Save the current audio and video packets for a participant.
    """
    # open the file
    file_path = os.path.join('temp', 'tracked_av_packets.temp')
    if os.path.exists(file_path):
        fp = open(file_path)
        d = json.load(fp)
        fp.close()
    else:
        d = dict()

    if conference_name in d:
        if participant_name in d[conference_name]:
            d[conference_name][participant_name]['audio'] = audio_packets
            d[conference_name][participant_name]['video'] = video_packets
        else:
            d[conference_name][participant_name] = {
                'audio': audio_packets,
                'video': video_packets
            }
    else:
        p = dict()
        p[participant_name] = {
            'audio': audio_packets,
            'video': video_packets
        }
        d[conference_name] = p

    logger.debug("Writing new av packets dict: %s" % d)

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


def _disconnect_participant(participant):
    """
        Disconnect a participant to the current conference.
    """
    logger.info("Disconnecting participant %s..." % participant['name'])
    api.participant_disconnect(participant['name'])
    # sleep to give time to MCU to connect the participant
    time.sleep(5)

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
                    if not details:
                        logger.error("Failed getting status details for the participant '%s' in the conference '%s'. Please check its status on MCU webinterface." % (participant['name'], conference['name']))
                    elif details['callState'] == "dormant":
                        # participant is inactive, disconnect it
                        _disconnect_participant(participant)
                    else:
                        if details['callState'] == "connected" and ("audioRxReceived" not in details or "videoRxReceived" not in details):
                            # something wrong with the participant
                            _disconnect_participant(participant)
                        else:
                            if details['callState'] != "connected":
                                # participant is not connected, connected it
                                _connect_participant(participant)
                            else:
                                # connect but get A/V packets from previous execution to see if participant is frozen
                                previous_audio_packets, previous_video_packets = get_av_packets(conference['name'], participant['name'])
                                logger.debug("Conference: %s - Participant: %s - Previous packets A/V: %s | %s - Current packets A/V: %s | %s" % (conference['name'], participant['name'], previous_audio_packets, previous_video_packets, details['audioRxReceived'], details['videoRxReceived']))
                                # check if audio and video are frozen comparing the number of current received packets with the previous execution
                                if long(details['audioRxReceived']) <= previous_audio_packets and long(details['videoRxReceived']) <= previous_video_packets:
                                    # it looks like everything is frozen here
                                    #logger.error("It looks like the participant '%s' in the conference '%s' is frozen. It will be now disconnected and re-connected" % (participant['name'], conference['name']))
                                    # disconnect the participant
                                    api.participant_disconnect(participant['name'])
                                    time.sleep(5)
                                    # re-connect
                                    _connect_participant(participant)

                            # re-get the status of the participant
                            details = api.get_participant_status(participant['name'])

                            # save current video packets
                            if "audioRxReceived" in details and "videoRxReceived" in details:
                                set_av_packets(conference['name'], participant['name'], details['audioRxReceived'], details['videoRxReceived'])

            else:
                logger.error("The conference %s is not connected" % conference['name'])
    except Exception as err:
        logger.exception("Exception occurred: %s" % err)
