import sys
import httplib
import xmlrpclib
import time

import conf
from mail_handler import ErrorMail

# create a xmlrpc request adding auth params and return the response
def request(methodName, params):
    xmlrequest = None
    response = None
    try:
        # add authentication params to the request
        params = dict(params.items() + conf.API_AUTH.items())
        xmlrequest = xmlrpclib.dumps(tuple([params]), methodName)

        conn = httplib.HTTPSConnection(conf.API_URL['hostname'])
        headers = { "Content-type": "text/xml", "charset": "utf-8", "Content-Length": "%d" % len(xmlrequest) }
        conn.request("POST", conf.API_URL['url'], headers=headers)
        conn.send(xmlrequest)
        response = conn.getresponse()
        response = response.read()
        #print response.status, response.reason
        conn.close()

        return xmlrpclib.loads(response)
    except xmlrpclib.Fault as err:
        email_body = """
        XMLRPC request FAILED using Codian MSE API.\n\n
        Error message: %s\n\n""" % (err)
    except Exception as err:
        email_body = """
        XMLRPC exception using Codian MSE API.\n\n
        Error message: %s\n\n""" % (err)

    # need to remove username and password from the request before sending out the email, so regenerate the xml request
    xmlrequest = xmlrpclib.dumps(tuple([params.items()]), methodName)

    email_body += """
    Request:\n%s\n\n
    Response:\n%s\n\n""" % (xmlrequest, response)

    m = ErrorMail(email_body)
    m.send()

    sys.exit(1)

# return if the conference is active or not
def getConferenceStatus():
    params = {
        'conferenceName': conf.CONFERENCE_NAME
    }
    response = request('conference.status', params)

    if response:
        response = response[0][0]
        return {
            'conferenceActive': response['conferenceActive'],
            'locked': response['locked'],
            }

# return if the participant is connected to the conference or not
def isParticipantConnected(participantName):
    params = {
        'conferenceName': conf.CONFERENCE_NAME,
        'participantName': participantName
    }
    response = request('participant.status', params)

    if response:
        response = response[0][0]
        return response['callState'] == "connected"

# try to connect a participant
def participantConnect(participantName, participantSettings):
    params = {
        'conferenceName': conf.CONFERENCE_NAME,
        'participantName': participantName
    }
    response = request('participant.connect', params)

    if response:
        response = response[0][0]
        if response['status'] != "operation successful":
            email_body = """
            Error trying to connect one participant: \n\n
            Participant: %s\n\n
            Params: %s\n\n""" % (participantName, params)

            m = ErrorMail(email_body)
            m.send()
        else:
            restoreLayout(participantName, participantSettings)

# try to disconnect a participant
def participantDisconnect(participantName, participantSettings):
    params = {
        'conferenceName': conf.CONFERENCE_NAME,
        'participantName': participantName
    }
    response = request('participant.disconnect', params)

    if response:
        response = response[0][0]
        if response['status'] != "operation successful":
            print "Error, disconnection failed"

# change back the pane placement layout
def restoreLayout(participantName, participantSettings):

    params = {
        'conferenceName': conf.CONFERENCE_NAME,
        'panes': [{
            'index': participantSettings['index'],
            'type': 'participant',
            'participantName': participantName
        }]
    }
    response = request('conference.paneplacement.modify', params)

    if not response:
        email_body = """
        Error trying to restore the layout of the pane placement: \n\n
        Participant: %s\n\n
        Params: %s\n\n""" % (participantName, params)

        m = ErrorMail(email_body)
        m.send()


if __name__ == '__main__':
    # script run from the console

    # check if the console is active
    status = getConferenceStatus()
    if status['conferenceActive'] and status['locked']:

        # for each participants, check if it is connected
        for name, settings in conf.PARTICIPANTS_TO_BE_CONNECTED.items():
            if not isParticipantConnected(name):
                participantConnect(name, settings)

    else:
        email_body = """
        The conference %s is not active or not locked: \n\n
        Active: %s\n\n
        Locked: %s\n\n""" % (conf.CONFERENCE_NAME, status['conferenceActive'], status['locked'])

        m = ErrorMail(email_body)
        m.send()

