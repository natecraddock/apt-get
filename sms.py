import logging
import os
from twilio.rest import Client

FROM = os.environ['TWILLIO_NUMBER']
account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']

client = Client(account_sid, auth_token)

def send_message(numbers: list, body: str):

    for number in numbers:
        client.messages.create(body=body, from_=FROM, to=number)
