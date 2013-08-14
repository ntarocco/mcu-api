from logger import logger
import httplib
import xmlrpclib

from mcu_watchdog import conf


class MCUConnector(object):
    """
        MCUConnector handles requests to Codian MCU API
    """

    def __init__(self):
        """
            Init the class creating the auth dict for each request
        """
        # create a dict with username and password to be added to the each request
        self._auth_data = {
            'authenticationUser': conf.MCU_API_USERNAME,
            'authenticationPassword': conf.MCU_API_PSW
        }

    def request(self, method_name, params):
        """
            Send a request to Codian MCU API, adding username and password
        """
        try:
            logger.debug("API Request - Method: %s - Params: %s" % (method_name, params))
            # add authentication params to the request
            params = dict(params.items() + self._auth_data.items())
            # convert dict to xml for the request
            xmlrequest = xmlrpclib.dumps(tuple([params]), method_name)
            logger.debug("%s" % xmlrequest)

            conn = httplib.HTTPSConnection(conf.MCU_API_HOSTNAME)
            # add the correct headers
            headers = {"Content-type": "text/xml", "charset": "utf-8", "Content-Length": "%d" % len(xmlrequest)}
            # send the request to the API url
            conn.request("POST", conf.MCU_API_URL, headers=headers)
            conn.send(xmlrequest)
            # get the response
            response = conn.getresponse()
            response = response.read()
            logger.debug("Response: %s" % response)
            # close connection
            conn.close()

            # convert xml response to dict
            return xmlrpclib.loads(response)
        except xmlrpclib.Fault as err:
            logger.exception("XMLRPC request FAILED using Codian MSE API: %s" % err)
        except Exception as err:
            logger.exception("XMLRPC exception using Codian MSE API: %s" % err)


class API_Common(object):
    """
        Common API between different versions of Codian MCU. When conference_name is set, it will be used
        for the API calls if it is not overridden by a method param.
    """
    _conference_name = None

    def __init__(self, conference_name=None):
        self._conn = MCUConnector()
        self._conference_name = conference_name


class API_2_8(API_Common):
    """
        Common API between different versions of Codian MCU
    """

    def __init__(self, conference_name):
        super(API_2_8, self).__init__(conference_name)

    def get_conference_status(self, conference_name=None):
        """
            Get the status of a conference and return a dict with all the details.
        """
        if not conference_name:
            conference_name = self._conference_name

        params = {
            'conferenceName': conference_name
        }
        response = self._conn.request('conference.status', params)

        if response:
            response = response[0][0]
            return response

    def lock_conference(self, conference_name=None):
        """
            Try to lock a conference.
        """
        if not conference_name:
            conference_name = self._conference_name

        params = {
            'conferenceName': conference_name,
            'locked': True
        }
        response = self._conn.request('conference.modify', params)

        if response:
            response = response[0][0]
            if response['status'] != "operation successful":
                logger.error("Error trying to lock the conference: %s" % conference_name)

    def is_participant_connected(self, participant_name, conference_name=None):
        """
            Return True or False if the paricipant is connected to the conference.
        """
        if not conference_name:
            conference_name = self._conference_name

        params = {
            'conferenceName': conference_name,
            'participantName': participant_name
        }
        response = self._conn.request('participant.status', params)

        if response:
            response = response[0][0]
            # returning True if the participant is connected
            return response['callState'] == "connected"

    def get_participant_status(self, participant_name, conference_name=None):
        """
            Return all the details of a participant.
        """
        if not conference_name:
            conference_name = self._conference_name

        params = {
            'conferenceName': conference_name,
            'participantName': participant_name
        }
        response = self._conn.request('participant.status', params)

        if response:
            response = response[0][0]
            return response

    def participant_connect(self, participant_name, conference_name=None):
        """
            Connect a participant (already added) to the confernece.
        """
        if not conference_name:
            conference_name = self._conference_name

        params = {
            'conferenceName': conference_name,
            'participantName': participant_name
        }
        response = self._conn.request('participant.connect', params)

        if response:
            response = response[0][0]
            if response['status'] != "operation successful":
                logger.error("Error trying to connect the partipant %s to the conference " % (participant_name, conference_name))

    def participant_disconnect(self, participant_name, conference_name=None):
        """
            Disconnect a participant from a conference.
        """
        if not conference_name:
            conference_name = self._conference_name

        params = {
            'conferenceName': conference_name,
            'participantName': participant_name
        }
        response = self._conn.request('participant.disconnect', params)

        if response:
            response = response[0][0]
            if response['status'] != "operation successful":
                logger.error("Error trying to disconnect the partipant %s to the conference " % (participant_name, conference_name))

    def restore_layout(self, participant_name, layout_index, conference_name=None):
        """
            Restore the layout according to the index set in the configuration file.
        """
        if not conference_name:
            conference_name = self._conference_name

        params = {
            'conferenceName': conference_name,
            'panes': [{
                'index': layout_index,
                'type': 'participant',
                'participantName': participant_name
            }]
        }
        response = self._conn.request('conference.paneplacement.modify', params)

        if not response:
            logger.error("Error trying to set the layout for the conference " % conference_name)

    def participant_add(self, participant_name, participant_address, participant_display_name, conference_name=None):
        """
            Add a new participant to the conference.
        """
        if not conference_name:
            conference_name = self._conference_name

        params = {
            'conferenceName': conference_name,
            'participantName': participant_name,
            'address': participant_address,
            'displayNameOverrideStatus': True,
            'displayNameOverrideValue': participant_display_name
        }
        response = self._conn.request('participant.add', params)
        return response

    def participant_modify(self, participant_name, participant_address, participant_display_name, conference_name=None):
        """
            Modify a participant already connected to the conference.
        """
        if not conference_name:
            conference_name = self._conference_name

        params = {
            'conferenceName': conference_name,
            'participantName': participant_name,
            'address': participant_address,
            'displayNameOverrideStatus': True,
            'displayNameOverrideValue': participant_display_name
        }
        response = self._conn.request('participant.modify', params)
        return response

    def participant_remove(self, participant_name, conference_name=None):
        """
            Remove a participant from the conference.
        """
        if not conference_name:
            conference_name = self._conference_name

        params = {
            'conferenceName': conference_name,
            'participantName': participant_name
        }
        response = self._conn.request('participant.remove', params)
        return response


class API():
    """
        Factory class to return the proper class to use
    """
    @staticmethod
    def get_instance(conference_name):
        if conf.MCU_API_VERSION == '2.8':
            return API_2_8(conference_name)
