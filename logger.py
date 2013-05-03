import logging

import conf

# create logger
logger = logging.getLogger("MCU")
logger.setLevel(conf.LOG_LEVEL)

formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
formatter_error = logging.Formatter('****** ERROR ****** %(asctime)s | %(module)s/%(filename)s | %(funcName)s():%(lineno)d | %(message)s')

file_handler = logging.FileHandler(conf.LOG_FILEPATH)
file_error_handler = logging.FileHandler(conf.LOG_ERROR_FILEPATH)

file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

file_error_handler.setLevel(logging.ERROR)
file_error_handler.setFormatter(formatter_error)
logger.addHandler(file_error_handler)

if conf.LOG_EMAIL:
    # email in case of errors
    mail_handler = logging.SMTPHandler(conf.LOG_MAIL_HOSTNAME, conf.LOG_MAIL_FROM, conf.LOG_MAIL_TO, "[MCU] Error")
    mail_handler.setLevel(logging.ERROR)
    mail_handler.setFormatter(formatter_error)
    logger.addHandler(mail_handler)

        # send email only every hour to avoid email-bombing
def sendEmail(email_body):

    if not os.path.exists('temp'):
        os.mkdir('temp')

    last_sent = None
    send_email = False
    filepath = os.path.join('temp', 'last_email_sent.txt')
    now = datetime.now()

    try:
        # save locally in a file last time email was sent
        if os.path.exists(filepath):
            # read the configuration
            fp = open(filepath)
            date_read = fp.readline()
            print date_read
            last_sent = datetime.strptime(date_read, '%Y-%m-%d %H:%M:%S')
            fp.close()

        if not last_sent or (now - last_sent) > timedelta(minutes=conf.LOG_EMAIL_FREQUENCY):
            # time expired, send email
            send_email = True

    except Exception as err:
        email_body += "\n\nOTHER ERRORS:\nImpossible to check last sent error email.\n%s\n\n" % err
        send_email = True

    if send_email:
        m = ErrorMail(email_body)
        m.send()

        fp = open(filepath, 'w')
        fp.write(now.strftime('%Y-%m-%d %H:%M:%S'))
        fp.close()
