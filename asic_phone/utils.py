from sys import stderr


def log(message):
    print(message) >> stderr
