activate_this = '/var/www/twilio_app/.venv/bin/activate_this.py'

with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

import sys
sys.path.insert(0, '/var/www/twilio_app')

from twilio_app.app import app as application