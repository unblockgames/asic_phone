from utils import log
import json
import os
import sys
import requests
import random
import time
import pymysql
from flask import Flask, make_response, request
from twilio.rest import Client
from twilio.twiml.voice_response import Gather, VoiceResponse, Say, Dial, Play
from twilio.twiml.messaging_response import Body, Message, Redirect, MessagingResponse

app = Flask(__name__)


# Your Account SID from twilio.com/console
account_sid = "ACd6341f5eb34207b6329a50257b36eef0"
# Your Auth Token from twilio.com/console
auth_token = "f26b9492de9465d70a3aabee240d3d6c"

client = Client(account_sid, auth_token)

with open(os.getcwd() + "/main.conf", "r") as file:
    CONFIG = json.load(file)


def openDB():
    con = pymysql.connect(host=CONFIG['DATABASE']['HOST'], user=CONFIG['DATABASE']['USERNAME'], password=CONFIG['DATABASE']
                          ['PASSWORD'], database=CONFIG['DATABASE']['DATABASE'])
    return con


@app.route("/")
def helloworld():
    return "Hello World"


@app.route("/entry")
def entry():
    twilio_response = VoiceResponse()
    gather = Gather(timeout=CONFIG['CALLDURATIONS']
                    ['xshort'], action="/menu_option_selected")
    gather.play(
        "https://asicminingpanelspublic.s3.us-east-2.amazonaws.com/asic_phone/__Main+Menu.wav")
    twilio_response.append(gather)
    # Assemble the Response
    r = make_response(str(twilio_response), 200)
    r.mimetype = 'text/xml'
    r.headers["Content-Type"] = "text/xml; charset=utf-8"
    return r


@app.route("/menu_option_selected", methods=["POST"])
def menu_option_selected():
    twilio_response = VoiceResponse()
    try:
        option = request.form['Digits'][0]
        if option == '1':
            dial = Dial()
            dial.conference(request.form['CallSid'],
                            status_callback=CONFIG['BASELINK'] + "/handleconference", status_callback_event="start end join leave hold modify speaker announcement")
            twilio_response.append(dial)
    except Exception as e:
        twilio_response.append(Say("An error has occurred."))
        log(str(e))
    # Assemble the Response
    r = make_response(str(twilio_response), 200)
    r.mimetype = 'text/xml'
    r.headers["Content-Type"] = "text/xml; charset=utf-8"
    return r


@app.route("/handleconference", methods=["POST"])
def handle_conference():
    con = openDB()
    cur = con.cursor()
    if 'ConferenceSid' in request.form:
        print(request.form['ConferenceSid'])
    print(request.form['StatusCallbackEvent'])
    if request.form['StatusCallbackEvent'] == 'participant-join':
        if request.form['FriendlyName'] == request.form['CallSid']:
            # if this caller made the conference...
            sqlStatement = "INSERT INTO Conferences (id) VALUES (%(id)s)"
            sqlArgs = dict(id=request.form['ConferenceSid'])
            cur.execute(sqlStatement, sqlArgs)
            con.commit()
            participant = client.conferences(request.form['ConferenceSid']) \
                .participants \
                .create(
                    label='Sales Rep',
                    from_="+18175009328",
                    to=CONFIG['NUMBERS']['Owner']['Jason']
            )
            time.sleep(30)
            sqlStatement = "SELECT pickedUp FROM Conferences WHERE id=%(id)s"
            sqlArgs = dict(id=request.form['ConferenceSid'])
            cur.execute(sqlStatement, sqlArgs)
            conferenceResponse = cur.fetchone()
            pickedUp = conferenceResponse[0]
            if not pickedUp:
                print("Need to redirect call")
            else:
                print("Call got picked up.")
        else:
            sqlStatement = "UPDATE Conferences SET pickedUp=1 WHERE id=%(conferenceSid)s"
            sqlArgs = dict(conferenceSid=request.form['FriendlyName'])
            cur.execute(sqlStatement, sqlArgs)
            con.commit()
    return ""


if __name__ == "__main__":
    app.run()
