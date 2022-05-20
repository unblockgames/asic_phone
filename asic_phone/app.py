from sys import stderr
from utils import log, isBusinessHours
import json
import os
import requests
import time
import pymysql
import urllib.parse as up
from flask import Flask, make_response, request
from twilio.rest import Client
from twilio.twiml.voice_response import Gather, VoiceResponse, Say, Dial, Play, Hangup
from twilio.twiml.messaging_response import Redirect

app = Flask(__name__)


# Your Account SID from twilio.com/console
account_sid = "ACd6341f5eb34207b6329a50257b36eef0"
# Your Auth Token from twilio.com/console
auth_token = "f26b9492de9465d70a3aabee240d3d6c"

client = Client(account_sid, auth_token)

# with open(os.getcwd() + "/main.conf", "r") as file:
#    CONFIG = json.load(file)
with open("/var/www/twilio_app/twilio_app/main.conf", "r") as file:
    CONFIG = json.load(file)


def openDB():
    con = pymysql.connect(host=CONFIG['DATABASE']['HOST'], user=CONFIG['DATABASE']['USERNAME'], password=CONFIG['DATABASE']
                          ['PASSWORD'], database=CONFIG['DATABASE']['DATABASE'])
    return con


def addToConference(caller, conferenceSid, whoToCall, timeout):
    con = openDB()
    cur = con.cursor()
    for person in whoToCall:
        call = client.calls.create(
            to=person['number'], from_="+18175009328", timeout=timeout, url=CONFIG['BASELINK'] + "/joinConference")
        sqlStatement = "INSERT INTO Calls VALUES (%(CallSid)s, %(ConferenceSid)s, 0)"
        sqlArgs = dict(CallSid=call.sid,
                       ConferenceSid=conferenceSid)
        cur.execute(sqlStatement, sqlArgs)
        con.commit()
    return


def conferenceStarted():
    con = openDB()
    cur = con.cursor()
    sqlStatement = "SELECT * FROM Calls WHERE ConferenceSid=%(ConferenceSid)s AND isClaimed=1"
    sqlArgs = dict(
        ConferenceSid=request.form['ConferenceSid'])
    cur.execute(sqlStatement, sqlArgs)
    if cur.fetchone() is None:
        return False
    return True


@app.route("/entry")
def entry():
    twilio_response = VoiceResponse()
    gather = Gather(timeout=CONFIG['CALLDURATIONS']
                    ['xxshort'], action="/menu_option_selected")
    gather.play(
        "https://asicminingpanelspublic.s3.us-east-2.amazonaws.com/asic_phone/__Main+Menu.wav")
    twilio_response.append(gather)
    twilio_response.redirect(
        url=CONFIG['BASELINK'] + "/menu_option_selected?transferDigits=7")
    # Assemble the Response
    r = make_response(str(twilio_response), 200)
    r.mimetype = 'text/xml'
    r.headers["Content-Type"] = "text/xml; charset=utf-8"
    return r


@app.route("/menu_option_selected", methods=["POST"])
def menu_option_selected():
    twilio_response = VoiceResponse()
    try:
        transferred = False
        if "Digits" in request.form:
            option = request.form['Digits'][0]
        elif "transferDigits" in request.args:
            option = str(request.args['transferDigits'])
            transferred = True
        if option == '6':
            gather = Gather(timeout=CONFIG['CALLDURATIONS']
                            ['xxshort'], action="/directory_dial")
            gather.append(Play(
                "https://asicminingpanelspublic.s3.us-east-2.amazonaws.com/asic_phone/_Complete+Directory.mp3"))
            twilio_response.append(gather)
        else:
            dial = Dial(hangup_on_star=True)
            dial.conference(request.form['CallSid'],
                            status_callback=CONFIG['BASELINK'] +
                            "/handleconference?option={0}&transferred={1}".format(
                option, transferred),
                status_callback_event="join leave",
                start_conference_on_enter=False,
                record="record-from-start")
            twilio_response.append(dial)
    except Exception as e:
        twilio_response.append(Say("An error has occurred."))
        log(str(e))
    # Assemble the Response
    r = make_response(str(twilio_response), 200)
    r.mimetype = 'text/xml'
    r.headers["Content-Type"] = "text/xml; charset=utf-8"
    return r


@app.route("/directory_dial", methods=["POST"])
def directory_dial():
    con = openDB()
    cur = con.cursor()
    twilio_response = VoiceResponse()
    if 'transferDigits' in request.args:
        option = request.args['transferDigits']
    else:
        option = request.form['Digits']
    if option == '101':  # Sales
        twilio_response.append(
            Redirect(url="/menu_option_selected?transferDigits=1"))
    elif option == '102':  # Shipping
        twilio_response.append(
            Redirect(url="/menu_option_selected?transferDigits=2"))
    elif option == '103':  # Customer Service
        twilio_response.append(
            Redirect(url="/menu_option_selected?transferDigits=3"))
    elif option == '104':  # Purchasing
        twilio_response.append(
            Redirect(url="/menu_option_selected?transferDigits=4"))
    elif option == '105':  # Accounting
        dial = Dial(hangup_on_star=True)
        dial.conference(request.form['CallSid'],
                        status_callback=CONFIG['BASELINK'] +
                        "/handleconference?option={0}&transferred={1}".format(
            option, 0),
            status_callback_event="join leave",
            start_conference_on_enter=False,
            record="record-from-start")
        twilio_response.append(dial)
    elif option == '106':  # Warehouse
        dial = Dial(hangup_on_star=True)
        dial.conference(request.form['CallSid'],
                        status_callback=CONFIG['BASELINK'] +
                        "/handleconference?option={0}&transferred={1}".format(
            option, 0),
            status_callback_event="join leave",
            start_conference_on_enter=False,
            record="record-from-start")
        twilio_response.append(dial)
    else:
        sqlStatement = "SELECT * FROM Extensions WHERE ext=%(option)s"
        sqlArgs = dict(option=option)
        cur.execute(sqlStatement, sqlArgs)
        extension_response = cur.fetchone()
        if extension_response is None:
            twilio_response.append(
                Say("The extension you dialed was invalid."))
            twilio_response.append(
                Redirect(url="/menu_option_selected?transferDigits=6"))
        else:
            dial = Dial(hangup_on_star=True)
            dial.conference(request.form['CallSid'],
                            status_callback=CONFIG['BASELINK'] +
                            "/handleconference?option={0}&transferred={1}".format(
                option, 0),
                status_callback_event="join leave",
                start_conference_on_enter=False,
                record="record-from-start")
            twilio_response.append(dial)
    # Assemble the Response
    r = make_response(str(twilio_response), 200)
    r.mimetype = 'text/xml'
    r.headers["Content-Type"] = "text/xml; charset=utf-8"
    return r


@app.route("/voicemail")
def voicemail():
    target = ""
    if "target" in request.args:
        target = request.args['target']
    if "ext" in request.args:
        ext = request.args['ext']
        con = openDB()
        cur = con.cursor()
        sqlStatement = "SELECT voicemail FROM Extensions WHERE ext=%(ext)s"
        sqlArgs = dict(ext=ext)
        cur.execute(sqlStatement, sqlArgs)
        url = cur.fetchone()[0]
    else:
        url = "https://asicminingpanelspublic.s3.us-east-2.amazonaws.com/asic_phone/_Main+Voicemail.wav"
    twilio_response = VoiceResponse()
    twilio_response.play(url)
    twilio_response.record(action="/twilio_record?target={0}".format(target))
    # Assemble the Response
    r = make_response(str(twilio_response), 200)
    r.mimetype = 'text/xml'
    r.headers["Content-Type"] = "text/xml; charset=utf-8"
    return r


@app.route("/twilio_record", methods=["POST"])
def twilio_record():
    twilio_response = VoiceResponse()
    recording_url = request.form["RecordingUrl"]
    caller = request.form["Caller"]
    if 'target' in request.args and request.args['target'] != "":
        data = {"content": "A voicemail was received for " +
                up.unquote(request.args['target']) + '.\n' + caller + '\n' + recording_url}
    else:
        data = {"content": "A voicemail was received.\n" +
                caller + '\n' + recording_url}
    requests.post("https://discord.com/api/webhooks/930470038266339449/iRe6TVWB6uno4_LJMEMmC2h3BvrsoccGOCTyBeGtewnrW69Y-nCnIAIT5vgDAmKKDSOi",
                  data=data)
    twilio_response.hangup()
    # Assemble the Response
    r = make_response(str(twilio_response), 200)
    r.mimetype = 'text/xml'
    r.headers["Content-Type"] = "text/xml; charset=utf-8"
    return r


@app.route("/handleconference", methods=["POST"])
def handle_conference():
    if "option" in request.args:
        option = str(request.args['option'])
    if "transferred" in request.args:
        transferred = request.args['transferred']
    con = openDB()
    cur = con.cursor()
    if 'ConferenceSid' in request.form:
        print("Conference Sid = " + request.form['ConferenceSid'])
    if 'CallSid' in request.form:
        print("Call SID = " + request.form['CallSid'])
    if 'StatusCallbackEvent' in request.form:
        print(request.form['StatusCallbackEvent'])
        if request.form['StatusCallbackEvent'] == 'participant-join':
            if request.form['FriendlyName'] == request.form['CallSid']:
                # if this caller made the conference...
                sqlStatement = "INSERT INTO Conferences (id) VALUES (%(id)s)"
                sqlArgs = dict(id=request.form['ConferenceSid'])
                cur.execute(sqlStatement, sqlArgs)
                con.commit()
                caller = client.calls(request.form['CallSid']).fetch()
                # Call the team
                # Determine who to call...
                if option:
                    if option == '1':
                        # call them...
                        addToConference(
                            caller, request.form['ConferenceSid'], CONFIG['NUMBERS']['Sales'], CONFIG['CALLDURATIONS']['long']*2)
                        time.sleep(CONFIG['CALLDURATIONS']['long'] + 3)
                        # if the conference hasnt started yet, call next person in line
                        if not conferenceStarted():
                            addToConference(
                                caller, request.form['ConferenceSid'], CONFIG['NUMBERS']['Owner'], CONFIG['CALLDURATIONS']['short'])
                            time.sleep(CONFIG['CALLDURATIONS']['short'] + 3)
                        # if the conference hasnt started yet, send to voicemail
                        if not conferenceStarted():
                            #  send to voicemail...
                            client.calls.get(request.form['CallSid']).update(
                                url=CONFIG['BASELINK'] + "/voicemail?target=Sales", method="GET")
                    elif option == '2':
                        # call them...
                        addToConference(
                            caller, request.form['ConferenceSid'], CONFIG['NUMBERS']['Mgr'], CONFIG['CALLDURATIONS']['long']*2)
                        addToConference(
                            caller, request.form['ConferenceSid'], CONFIG['NUMBERS']['Warehouse'], CONFIG['CALLDURATIONS']['long']*2)
                        time.sleep(CONFIG['CALLDURATIONS']['long'] + 3)
                        # if the conference hasnt started yet, call next person in line
                        if not conferenceStarted():
                            addToConference(
                                caller, request.form['ConferenceSid'], CONFIG['NUMBERS']['Owner'], CONFIG['CALLDURATIONS']['short'])
                            addToConference(
                                caller, request.form['ConferenceSid'], CONFIG['NUMBERS']['Sales'], CONFIG['CALLDURATIONS']['short'])
                            time.sleep(CONFIG['CALLDURATIONS']['short'] + 3)
                        # if the conference hasnt started yet, send to voicemail
                        if not conferenceStarted():
                            #  send to voicemail...
                            client.calls.get(request.form['CallSid']).update(
                                url=CONFIG['BASELINK'] + "/voicemail?target=ShippingReceiving", method="GET")
                    elif option == '3':
                        # call them...
                        if isBusinessHours():
                            addToConference(
                                caller, request.form['ConferenceSid'], CONFIG['NUMBERS']['Sales'], CONFIG['CALLDURATIONS']['long'])
                        else:
                            addToConference(
                                caller, request.form['ConferenceSid'], CONFIG['NUMBERS']['Owner'], CONFIG['CALLDURATIONS']['long'])
                        time.sleep(CONFIG['CALLDURATIONS']['long'] + 3)
                        # if the conference hasnt started yet, send to voicemail
                        if not conferenceStarted():
                            #  send to voicemail...
                            client.calls.get(request.form['CallSid']).update(
                                url=CONFIG['BASELINK'] + "/voicemail?target=CustomerService", method="GET")
                    elif option == '4':
                        # call them...
                        if isBusinessHours():
                            addToConference(
                                caller, request.form['ConferenceSid'], CONFIG['NUMBERS']['Mgr'], CONFIG['CALLDURATIONS']['long'])
                        else:
                            addToConference(
                                caller, request.form['ConferenceSid'], CONFIG['NUMBERS']['Owner'], CONFIG['CALLDURATIONS']['long'])
                        time.sleep(CONFIG['CALLDURATIONS']['long'] + 3)
                        # if the conference hasnt started yet, send to voicemail
                        if not conferenceStarted():
                            #  send to voicemail...
                            client.calls.get(request.form['CallSid']).update(
                                url=CONFIG['BASELINK'] + "/voicemail?target=Vendor", method="GET")
                    elif option == '5':
                        # call them...
                        if isBusinessHours():
                            addToConference(
                                caller, request.form['ConferenceSid'], CONFIG['NUMBERS']['Accnt'], CONFIG['CALLDURATIONS']['long'])
                        else:
                            addToConference(
                                caller, request.form['ConferenceSid'], CONFIG['NUMBERS']['Owner'], CONFIG['CALLDURATIONS']['long'])
                        time.sleep(CONFIG['CALLDURATIONS']['long'] + 3)
                        # if the conference hasnt started yet, send to voicemail
                        if not conferenceStarted():
                            #  send to voicemail...
                            client.calls.get(request.form['CallSid']).update(
                                url=CONFIG['BASELINK'] + "/voicemail?target=Accounting", method="GET")
                    elif option == '106':
                        addToConference(
                            caller, request.form['ConferenceSid'], CONFIG['NUMBERS']['Warehouse'], CONFIG['CALLDURATIONS']['long'])
                        time.sleep(CONFIG['CALLDURATIONS']['long'] + 3)
                        # if the conference hasnt started yet, send to voicemail
                        if not conferenceStarted():
                            #  send to voicemail...
                            client.calls.get(request.form['CallSid']).update(
                                url=CONFIG['BASELINK'] + "/voicemail?target=Warehouse", method="GET")
                    else:
                        sqlStatement = "SELECT * FROM Extensions WHERE ext=%(option)s"
                        sqlArgs = dict(option=option)
                        cur.execute(sqlStatement, sqlArgs)
                        extension_response = cur.fetchone()
                        if extension_response is None:
                            # call them...
                            if isBusinessHours():
                                addToConference(
                                    caller, request.form['ConferenceSid'], CONFIG['NUMBERS']['Sales'], CONFIG['CALLDURATIONS']['long'])
                                addToConference(
                                    caller, request.form['ConferenceSid'], CONFIG['NUMBERS']['Owner'], CONFIG['CALLDURATIONS']['long'])
                            else:
                                addToConference(
                                    caller, request.form['ConferenceSid'], CONFIG['NUMBERS']['Owner'], CONFIG['CALLDURATIONS']['long'])
                            time.sleep(CONFIG['CALLDURATIONS']['long'] + 3)
                            # if the conference hasnt started yet, send to voicemail
                            if not conferenceStarted():
                                #  send to voicemail...
                                client.calls.get(request.form['CallSid']).update(
                                    url=CONFIG['BASELINK'] + "/voicemail", method="GET")
                        else:

                            addToConference(
                                caller, request.form['ConferenceSid'], [{"number": extension_response[2]}], CONFIG['CALLDURATIONS']['long'])
                            time.sleep(CONFIG['CALLDURATIONS']['long'] + 3)
                            # if the conference hasnt started yet, send to voicemail
                            if not conferenceStarted():
                                #  send to voicemail...
                                client.calls.get(request.form['CallSid']).update(
                                    url=CONFIG['BASELINK'] + "/voicemail?ext={0}&target={1}".format(option, extension_response[1]), method="GET")
        elif request.form['StatusCallbackEvent'] == 'participant-leave':
            if request.form['FriendlyName'] == request.form['CallSid']:
                try:
                    conference = client.conferences(
                        request.form['ConferenceSid']).fetch().update(status="completed")
                except:
                    stderr.write(
                        "There was an error that occurred when fetching the conference...")
                    stderr.write(conference.sid)
    print("---------------")
    return ""


@app.route("/joinConference", methods=["POST"])
def joinConference():
    twilio_response = VoiceResponse()
    con = openDB()
    cur = con.cursor()
    sqlStatement = "SELECT * FROM Calls WHERE CallSid=%(CallSid)s"
    sqlArgs = dict(CallSid=request.form['CallSid'])
    cur.execute(sqlStatement, sqlArgs)
    call_response = cur.fetchone()
    if call_response is None:
        twilio_response.append(Say("An error occurred."))
        twilio_response.append(Hangup())
    elif not call_response[2]:  # if the call is not yet claimed
        # claim the call
        sqlStatement = "UPDATE Calls SET isClaimed=1 WHERE CallSid=%(CallSid)s"
        cur.execute(sqlStatement, sqlArgs)
        con.commit()
        # connect to the conference
        dial = Dial(hangup_on_star=True)
        conference = client.conferences.get(call_response[1]).fetch()
        dial.conference(conference.friendly_name)
        twilio_response.append(dial)
        twilio_response.append(
            Redirect(url=CONFIG['BASELINK'] + "/call_control"))
    else:  # if the call is already claimed
        twilio_response.append(Say("Someone already answered the call."))
        twilio_response.append(Hangup())
    # Assemble the Response
    r = make_response(str(twilio_response), 200)
    r.mimetype = 'text/xml'
    r.headers["Content-Type"] = "text/xml; charset=utf-8"
    return r


@app.route("/call_control", methods=["POST"])
def call_control():
    con = openDB()
    cur = con.cursor()
    sqlStatement = "SELECT ConferenceSid FROM Calls WHERE CallSid=%(CallSid)s"
    sqlArgs = dict(CallSid=request.form['CallSid'])
    cur.execute(sqlStatement, sqlArgs)
    conference = client.conferences.get(cur.fetchone()[0]).fetch()
    caller = conference.participants.get(conference.friendly_name).fetch()
    caller.update(hold=True)
    twilio_response = VoiceResponse()
    gather = Gather(timeout=CONFIG['CALLDURATIONS']
                    ['xxshort'], action="/call_control_option_selected")
    gather.append(
        Say("To transfer the caller to Sales, press 1. To transfer the caller to a manager, press 2. To transfer the caller to an extension press 3. To transfer the caller to a specific 10 digit phone number, press 4. To send the caller to voicemail press 5."))
    twilio_response.append(gather)
    # Assemble the Response
    r = make_response(str(twilio_response), 200)
    r.mimetype = 'text/xml'
    r.headers["Content-Type"] = "text/xml; charset=utf-8"
    return r


@app.route("/call_control_option_selected", methods=["POST"])
def call_control_option_selected():
    con = openDB()
    cur = con.cursor()
    sqlStatement = "SELECT ConferenceSid FROM Calls WHERE CallSid=%(CallSid)s"
    sqlArgs = dict(CallSid=request.form['CallSid'])
    cur.execute(sqlStatement, sqlArgs)
    conference = client.conferences.get(cur.fetchone()[0]).fetch()
    caller = conference.participants.get(conference.friendly_name).fetch()
    twilio_response = VoiceResponse()
    digits = request.form['Digits']
    if digits == '1':
        client.calls(caller.call_sid).update(
            url=CONFIG['BASELINK'] + "/menu_option_selected?transferred=1&transferDigits=1", method="POST")
        twilio_response.append(
            Say("The caller was transferred. Goodbye."))
    elif digits == '2':
        client.calls(caller.call_sid).update(
            url=CONFIG['BASELINK'] + "/menu_option_selected?transferred=1&transferDigits=2", method="POST")
        twilio_response.append(
            Say("The caller was transferred. Goodbye."))
    elif digits == '3':
        gather = Gather(timeout=CONFIG['CALLDURATIONS']['xxshort'],
                        action="/transfer_to_extension?callerSid={0}".format(caller.call_sid))
        gather.append(Say(
            "Enter the 3 digit extension of the person you want to transfer the caller to. For a list of extensions, dial 1."))
        twilio_response.append(gather)
    elif digits == '4':
        gather = Gather(timeout=CONFIG['CALLDURATIONS']
                        ['xxshort'], action="/transfer_direct?callerSid={0}".format(caller.call_sid))
        gather.append(
            Say("Enter the 10 digit number you want the caller to be transferred to."))
        twilio_response.append(gather)
    elif digits == '5':
        call = client.calls.get(caller.call_sid).fetch()
        call.update(url=CONFIG['BASELINK'] + "/voicemail", method="GET")
        twilio_response.append(
            Say("The caller was sent to voicemail. Goodbye."))
    else:
        twilio_response.append(Say("The option you selected does not exist."))
        twilio_response.append(
            Redirect(url=CONFIG['BASELINK'] + "/call_control"))
    # Assemble the Response
    r = make_response(str(twilio_response), 200)
    r.mimetype = 'text/xml'
    r.headers["Content-Type"] = "text/xml; charset=utf-8"
    return r


@app.route("/transfer_to_extension", methods=['POST'])
def transfer_to_extension():
    twilio_response = VoiceResponse()
    if request.form['Digits'] == '1':
        gather = Gather(timeout=CONFIG['CALLDURATIONS']['xxshort'],
                        action="/transfer_to_extension?callerSid={0}".format(request.args['callerSid']))
        gather.append(Play(
            "https://asicminingpanelspublic.s3.us-east-2.amazonaws.com/asic_phone/_Complete+Directory.mp3"))
        twilio_response.append(gather)
    else:
        client.calls(request.args['callerSid']).update(
            url=CONFIG['BASELINK'] + "/directory_dial?transferred=1&transferDigits={0}".format(request.form['Digits']), method="POST")
        twilio_response.append(
            Say("The caller was transferred. Goodbye."))
    # Assemble the Response
    r = make_response(str(twilio_response), 200)
    r.mimetype = 'text/xml'
    r.headers["Content-Type"] = "text/xml; charset=utf-8"
    return r


@app.route("/transfer_direct", methods=["POST"])
def transfer_direct():
    twilio_response = VoiceResponse()
    digits = request.form['Digits']
    if len(digits) == 10:
        group1 = digits[0:3]
        group2 = digits[3:6]
        group3 = digits[6:]
    elif len(digits) == 11:
        group1 = digits[1:4]
        group2 = digits[4:7]
        group3 = digits[7:]
    else:
        twilio_response.say("You entered an invalid number of digits.")
        twilio_response.append(
            Redirect(url=CONFIG['BASELINK'] + "/call_control"))
    client.calls(request.args['callerSid']).update(
        twiml='<Response><Dial>{0}-{1}-{2}</Dial></Response>'.format(group1, group2, group3))
    twilio_response.append(
        Say("The caller was transferred. Goodbye."))
    # Assemble the Response
    r = make_response(str(twilio_response), 200)
    r.mimetype = 'text/xml'
    r.headers["Content-Type"] = "text/xml; charset=utf-8"
    return r


if __name__ == "__main__":
    app.run()
