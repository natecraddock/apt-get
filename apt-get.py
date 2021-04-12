#!/usr/bin/env python3

import json
import logging
import os
import sys
import time
from enum import Enum
from typing import List

import requests
from bs4 import BeautifulSoup

# Super Mario Sunshine
import sms


##### Utils #####
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class Update(Enum):
    NONE = 1
    VACANCY = 2
    NEW = 3

class ApartmentListing:
    @staticmethod
    def from_json(data: dict):
        return ApartmentListing(data["name_full"], data["name"], data["number"],
                data["vacancies_str"], data["vacancies"], data["rents"], data["url"])

    def __init__(self, name_full: str, name: str, number: int,
                 vacancies_str: str, vacancies: int, rents: List[int], url: str):
        self.name_full = name_full
        self.name = name
        self.number = number
        self.vacancies_str = vacancies_str
        self.vacancies = vacancies
        self.rents = rents
        self.url = url

    def __str__(self):
        return f"{self.name} #{self.number} vacancies: {self.vacancies} {self.rents}"

    def __eq__(self, o: object) -> bool:
        return self.name_full == o.name_full

# Setup logging
logging.basicConfig(filename="/home/pi/dev/apt-get/log.txt", format="%(asctime)s %(levelname)s: %(message)s",
                    datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)

logging.info("Started")

URL = "http://www.aspenridgemanagement.com/mens-housing/"

response = requests.get(URL)
if not response.ok:
    eprint(f"Could not connect to {URL}")
    sys.exit(1)

soup = BeautifulSoup(response.text, "html.parser")

apartments = []
for apartment in soup.select(".complexdetails"):
    name = apartment.h5.a.text
    vacancies = apartment.h5.next_sibling.strip()
    rent = apartment.h5.next_sibling.next_sibling.next_sibling.strip()

    name_full = name.strip()
    if "#" in name:
        name, number = name.split("#")
        name = name.strip()
        number = number.strip()
    else:
        name = name_full.strip()
        number = "No Number"
    
    vacancies_str = vacancies
    vacancies = int(vacancies.split(" ")[0].strip())
    rents = [int(r.strip(", ")) for r in rent.split("$")[1:]]

    apartments.append(ApartmentListing(name_full, name, number, vacancies_str, vacancies, rents, URL))

logging.info(f"Found {len(apartments)} listings")

database_list = []
with open("/home/pi/dev/apt-get/database.json", "r") as database:
    listings = json.loads(database.read())
    for listing in listings:
        database_list.append(ApartmentListing.from_json(listing))
        
def update_database(apartment: ApartmentListing, database: List[ApartmentListing]) -> Update:
    found = False
    for listing in database:
        if listing == apartment:
            found = True
            # Case 1: Number of vacancies has changed
            if listing.vacancies != apartment.vacancies:
                listing.vacancies = apartment.vacancies
                return Update.VACANCY
    
    # Case 2: New Listing
    if not found:
        database.append(apartment)
        return Update.NEW
    
    # Case 3: No change
    return Update.NONE

new_listings: List[ApartmentListing] = []
changed_vacancies: List[ApartmentListing] = []

# Compare data for changes in vacancies and new listings
for apartment in apartments:
    update_type = update_database(apartment, database_list)
    if update_type is Update.VACANCY:
        changed_vacancies.append(apartment)

    elif update_type is Update.NEW:
        new_listings.append(apartment)

# Send Texts
if new_listings or changed_vacancies:
    body_str = "¯\_(ツ)_/¯\n\n"

    body_str += "New Listings:\n"
    if new_listings:
        for item in new_listings:
            logging.info(f"New Listing: {item}")
            body_str += f"* {item.name_full} vacancies: {item.vacancies} rents: {item.rents}\n"
    else:
        body_str += "None\n\n"

    body_str += "Changed Listings:\n"
    if changed_vacancies:
        for item in changed_vacancies:
            logging.info(f"Changed Vacancy: {item}")
            body_str += f"* {item.name_full} vacancies: {item.vacancies} rents: {item.rents}\n"
    else:
        body_str += "None\n"

    #Split the message if over 800 chars long, split the texts
    if len(body_str) > 1200:
        start_index = 0
        ending_index = 600
        while (ending_index < len(body_str)):

            str_segment = ""

            if (ending_index > len(body_str)):
                str_segment = body_str[start_index:]
            else:
                str_segment = body_str[start_index:ending_index]

            recipients = json.loads(os.environ["NUMBERS"])
            sms.send_message(recipients, str_segment)

            start_index = ending_index
            ending_index += 600
    else:
        recipients = json.loads(os.environ["NUMBERS"])
        sms.send_message(recipients, body_str)


with open("/home/pi/dev/apt-get/database.json", "w") as database:
    json.dump(database_list, database, default=lambda o: o.__dict__, indent=2)

logging.info("################ FINISHED ################")
