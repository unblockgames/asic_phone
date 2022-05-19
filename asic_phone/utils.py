from datetime import datetime, timedelta, time
from sys import stderr

BUSINESSHOURS = {  # Business hours in UTC -6
    "open": [7, 0, 0],  # [hour, minute, second]
    "close": [17, 0, 0],  # [hour, minute, second]
    "timezone": -6,  # [integer hour offset]
    # mon == 1, tue == 2 ... sun == 7
    "daysOfWeek": [1, 2, 3, 4, 5]
}


def log(message):
    print(message) >> stderr


def isBusinessHours():
    now = datetime.now()  # Current time in UTC
    # adjust to current timezone
    now = now + timedelta(hours=BUSINESSHOURS["timezone"])
    day = now.isoweekday()  # get number of day of week.
    if day not in BUSINESSHOURS["daysOfWeek"]:
        return False
    openTime = time(
        BUSINESSHOURS["open"][0], BUSINESSHOURS["open"][1], BUSINESSHOURS["open"][2])
    closeTime = time(
        BUSINESSHOURS["close"][0], BUSINESSHOURS["close"][1], BUSINESSHOURS["close"][2])
    if now.time() < openTime:
        return False
    if now.time() >= closeTime:
        return False
    return True
