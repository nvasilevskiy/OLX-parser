# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
from hashlib import sha224
import re
import csv
import smtplib
import sys
import urllib.request
import json
import configparser
import time
import datetime

# Write data to file function

def write_data_to_csv(mode, data):
    write_mode = "w"
    if mode == "a":
        write_mode = "a"
    with open('olx.db', write_mode, encoding='utf-8', newline='') as fp:
        csvfile = csv.writer(fp, delimiter=',', dialect='excel')
        for key in data.items():
            try:
                csvfile.writerows([key])
            except IOError as e:
                print("Write to DB file error!"), e
                sys.exit(1)

def get_phone_number(url):
    url = url[:(url.find('.ua')+3)] + '/ajax/misc/contact/phone/' + url[(url.find('ID')+2):(url.find('.html'))] + '/'
    try:
        response = urllib.request.urlopen(url)
    except Exception as e:
        number = "N/A"
        return number
    html = response.read()
    json_numbers = (((((BeautifulSoup(html)).get_text()).replace(" ", "")).replace("-", "")).replace("(", "")).replace(")", "")
    numbers = []
    number = ''
    for index, obj in enumerate(json_numbers):
        if obj.isdigit():
            if json_numbers[index+1].isdigit() == True:
                number += json_numbers[index]
            else:
                number += json_numbers[index]
                numbers.append(number)
                number = ''
    for each in numbers:
        number += each + ' '
    return number

def send_mail(fromaddr, toaddr, password, msg):
    try:
        print('Sending the mail with new data...')
        try:
            print('Try send via', mail_server)
            print('From', fromaddr, 'to:', toaddr)

            server = smtplib.SMTP(mail_server)
        except:
            print('Network error! Please run with mail_debug_level=1')
            print('Please enable low security access for your mail!')
            sys.exit(1)
        server.set_debuglevel(mail_debug_level)
        server.ehlo()
        server.starttls()
        server.login(fromaddr, password)
        server.sendmail(fromaddr, toaddr, msg.encode('utf-8'))
        server.quit()
        print(' ')
        print('Done!')
    except smtplib.SMTPException as e:
        print('Send mail error! Please run with mail_debug_level=1'), e
        print('Please enable low security access for your mail!')
        sys.exit(1)


while True:
    #Load parameters from file
    try:
        config = configparser.RawConfigParser()
        config.read('settings.ini')
        fromaddr = (config['DEFAULT']['sender'])
        toaddr = (config['DEFAULT']['receiver'])
        password = (config['DEFAULT']['password'])
        mail_server = (config['DEFAULT']['mail_server'])
        mail_debug_level = int((config['DEFAULT']['mail_debug_level']))
        should_send_mail = int((config['DEFAULT']['send_mail']))
        start_interval = int((config['DEFAULT']['start_interval']))
        url = (config['DEFAULT']['url'])
    except Exception as e:
        print("Could not parse setting.ini with parameters, please check it."), e
        sys.exit(1)

    ####################
    out = {}
    compare_out = {}
    i = 0
    price_flag = False
    to_write = {}
    first_run = True
    subject = "Report from OXL parser on " + (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    msg = ("Subject: %s\n From: %s\r\nTo: %s\r\n\r\n" % (subject, fromaddr, toaddr))
    ####################

    try:
        with open('olx.db') as file:
            print('Checking DB file...')
            first_run = False
            pass
    except IOError as e:
        print('This is first run or DB file is missing...', e)
        first_run = True

    try:
        response = urllib.request.urlopen(url)
        pass
    except Exception as e:
        print('Can not get target URL!', e)
        sys.exit(1)

    print('Get data from target URL: ', url)
    html = response.read()
    olx = BeautifulSoup(html)

    print('Parsing...')
    Message_and_Link = olx.findAll('a', {'class': 'detailsLink'})
    Price = olx.findAll('p', {'class': 'price'})
    Price_data = []

    #Looking for Price
    for price in Price:
        PriceText = price.getText()
        if PriceText.strip() != '':
            Price_data.append(price.getText().strip())

    print('Compiling data...')

    #Compiling all...
    for each in Message_and_Link:
        PostText = each.getText()
        if PostText.strip() != "":
            Text = (re.sub("^\s+|\n|\r|\s+$", '', (each.getText())).replace('"','')).replace("'",'')
            index = (sha224((Price_data[i]+Text).encode('utf-8')).hexdigest())
            Price = (Price_data[i])
            Link = (each['href'])
            out[index] = {"Price": Price, "Text": Text, "Link": Link, "Phone": get_phone_number(Link)}
            i += 1
    print(' ')
    print('Done!')

    if first_run:
        write_data_to_csv("w", out)

    else:
        with open('olx.db', 'r', encoding='utf-8', newline='') as fp:
            reader = csv.reader(fp)
            counter = 1
            for row in reader:
                string = (row[1].replace("'", '"'))
                string_json = (json.dumps(string, ensure_ascii=False, separators=(":", ",")))
                try:
                    string_json_out = json.loads(json.loads(string_json))
                except Exception as e:
                    print('We have problem with DB file! Line: ' + str(counter) + '. Error message:', e)
                    print('Please delete this line from olx.db and start again.')
                    sys.exit(1)
                compare_out[row[0]] = string_json_out
                counter += 1

    #Compare using new data with old data

        for key in out.keys():
                if key not in compare_out.keys():
                    print('We have new record with id', key)
                    TextMessage = (out[key]["Text"]).encode(sys.stdin.encoding, errors='ignore')
                    print('Message is:', TextMessage.decode(sys.stdin.encoding, errors='ignore'))
                    print('Phone(s):', out[key]["Phone"])
                    print('Price is:', out[key]["Price"])
                    print('Link:', out[key]["Link"] + '\n')
                    to_write[key] = {"Price": out[key]["Price"],
                                     "Link": out[key]["Link"],
                                     "Text": out[key]["Text"],
                                     "Phone": out[key]["Phone"]
                                     }
                if key in compare_out.keys():
                    if (out[key]['Price'] != compare_out[key]['Price']):
                        print('New price(s) was found!')
                        price_flag = True
                        TextMessage = (out[key]["Text"]).encode(sys.stdin.encoding)
                        print('Message is:', TextMessage.decode(sys.stdin.encoding))
                        msg += 'We have new price update!\n'
                        msg += 'Text: '+ (out[key]["Text"] + "\n" + 'Old price: ' + compare_out[key]["Price"] + " >> New price: "
                                          + out[key]["Price"] + "\n"
                                          + "Phone(s): " + out[key]["Phone"] + "\n"
                                          + "Link: " + out[key]["Link"] + "\n\n")
                        print('Old price: ' + compare_out[key]["Price"] + " >> New price: " + out[key]["Price"])
                        print('Phone(s):', out[key]["Phone"])
                        print('Link:', out[key]["Link"])
                        print(' ')
                        print('Change price to new in DB...')
                        try:
                            price_change = open("olx.db", encoding='utf-8').read()
                            if key in price_change:
                                price_change = price_change.replace(compare_out[key]["Price"], out[key]["Price"])
                            price_change_write = open("olx.db", 'w', encoding='utf-8')
                            price_change_write.write(price_change)
                            price_change_write.close()
                        except IOError as e:
                            print('Unable to write data in to DB file! ', e)
                            sys.exit(1)
                        print(' ')

    if (should_send_mail == 1):
        if price_flag:
            if len(to_write) == 0:
                send_mail(fromaddr, toaddr, password, msg)

    if len(to_write) == 0:
        print('...')
        if (first_run):
            print('DB creation complete!')
            #sys.exit(0)
        print('Updating data complete! \nWaiting for next run.')
        #sys.exit(0)
    else:
        print('Write new record(s) to DB file...')
        write_data_to_csv("a", to_write)
        print('...')
        print('Done!')

        msg += 'New ads was added!\n\n'
        for key in to_write.keys():
            msg += (to_write[key]["Text"]) + " Price: " + (to_write[key]["Price"]) + " Phone(s): " + (to_write[key]["Phone"]) + "\nLink: " + (
                to_write[key]["Link"]) + "\n\n"
        print(' ')
        if should_send_mail == 1:
            send_mail(fromaddr, toaddr, password, msg)



    print('Next start in ' + str(start_interval) + ' minute(s)')
    for i in range(start_interval+1):
        time.sleep(60)
        sys.stdout.write("\r%d%%" % (i*(100/start_interval)))
        sys.stdout.flush()

    print('')
    #sys.exit(0)

