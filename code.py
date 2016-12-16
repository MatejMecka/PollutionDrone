#!/bin/env python3

import requests
import serial
import argparse
import os
import logging
import struct
import io
import time


def bytes2int(bytes):
    return struct.unpack("B", bytes)[0]

def init_usb(sysnode):
    return os.system("echo disabled > %s/power/wakeup"%sysnode)

def turn_on_usb(sysnode):
    return os.system("echo on > %s/power/level"%sysnode)

def turn_off_usb(sysnode):
    return os.system("echo on > %s/power/level"%sysnode)

def setup_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--device", help="device node",
        default="/dev/ttyUSB0")
    parser.add_argument("-u", "--url", 
        help="POST to this url. If empty, the script will only print out the values")
    parser.add_argument("-l", "--loglevel", help="Log level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO")
    parser.add_argument("-p", "--powersaving", help="Powersaving",
        action="store_true")
    parser.add_argument("-s", "--sysnode", help="System node for the usb - for powersaving",
        default="/sys/bus/usb/devices/usb1")
    return parser.parse_args()


if __name__ == "__main__":
    args = setup_args()
    logging.basicConfig(format='%(levelname)s:%(message)s', level=getattr(logging, args.loglevel.upper()))

    if args.powersaving and args.sysnode:
        logging.debug("Init Powersaving")
        logging.debug(init_usb(args.sysnode))
        logging.debug("Turning USB ON")
        logging.debug(turn_on_usb(args.sysnode))

    try:
        
        ser2 = serial.Serial('/dev/ttyS0',9600, timeout=1)
        sio = io.TextIOWrapper(io.BufferedRWPair(ser2, ser2, 1), encoding='ascii', newline='\r')

        gotGPS = True
        while gotGPS:
            print("recording")
            datastring = ser2.readline()
            if datastring.strip().split(',')[0] == '$GPGGA' :
                    gotGPS = False  
                    lat = datastring.strip().split(',')[2]
                    lon = datastring.strip().split(',')[4]
                    alt = datastring.strip().split(',')[9]
                    logging.info("lat: %s" % lat)
                    logging.info("lon: %s" % lon)
                    logging.info("alt: %s" % alt)




        with serial.Serial(args.device, baudrate=9600) as ser:
            logging.info("Serial device initialized")
            read_full = False
            pm25 = 0
            pm10 = 0
            data = []
            while not read_full:
                if ser.read() == b'\xaa':
                    logging.debug("FIRST HEADER GOOD")
                    # FIRST HEADER IS GOOD
                    if ser.read() == b'\xc0':
                        # SECOND HEADER IS GOOD
                        logging.debug("SECOND HEADER GOOD")
                        for i in range(8):
                            byte = ser.read()
                            data.append(bytes2int(byte))

                        if data[-1] == 171:
                            # END BYTE IS GOOD. DO CRC AND CALCULATE
                            logging.debug("END BYTE GOOD")
                            if data[6] == sum(data[0:6])%256:
                                logging.debug("CRC GOOD")
                            pm25 = (data[0]+data[1]*256)/10
                            pm10 = (data[4]+data[3]*256)/10
                            read_full = True
            if args.url:
                logging.info("Posting to %s" % args.url)
                #r = requests.post("FIREBASEURL", data={"location":{"altitude":"200","latitude":lat, "longitude":lon},"polution":{"pm10":pm10,"pm2":pm25}})
                r = requests.post("FIREBASEURL", json={"location":{"altitude":alt,"latitude":lat, "longitude":lon},"polution":{"pm10":pm10,"pm2":pm25}, "time": time.strftime("%H:%M:%S"), "date":time.strftime("%d/%m/%Y")})
                logging.debug(r)
                logging.debug(r.text) #TEXT/HTML
                logging.debug(r.status_code, r.reason) #HTTP

            logging.info("PM 10: %s" % pm10)
            logging.info("PM 2.5: %s" % pm25)
    except serial.SerialException as e:
        logging.critical(e)

    if args.powersaving and args.sysnode:
        logging.debug("Turning USB OFF")
        logging.debug(turn_off_usb())
