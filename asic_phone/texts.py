import os
import json
from twilio.rest import Client


# Find your Account SID and Auth Token at twilio.com/console
# and set the environment variables. See http://twil.io/secure

# with open(os.getcwd() + "/main.conf", "r") as file:
#    CONFIG = json.load(file)
with open("/var/www/twilio_app/twilio_app/main.conf", "r") as file:
    CONFIG = json.load(file)

account_sid = CONFIG['TWILIO_AUTH']['account_sid']
auth_token = CONFIG['TWILIO_AUTH']['auth_token']
client = Client(account_sid, auth_token)

service = client.messaging \
                .services \
                .create(friendly_name='My First Messaging Service')


def text(number, message):
    message = client.messages\
        .create(
            body=message,
            messaging_service_sid=service.sid,
            to=number
        )
    return
