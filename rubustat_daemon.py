#! /usr/bin/python
 
import sys
import subprocess
import os
import time
import RPi.GPIO as GPIO
import datetime
import ConfigParser
import feedparser
import imaplib

from daemon import Daemon
from getIndoorTemp import getIndoorTemp
#set working directory to where "rubustat_daemon.py" is
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

#read values from the config file
config = ConfigParser.ConfigParser()
config.read("config.txt")
DEBUG = int(config.get('main','DEBUG'))
active_hysteresis = float(config.get('main','active_hysteresis'))
inactive_hysteresis = float(config.get('main','inactive_hysteresis'))
HEATER_PIN = int(config.get('main','HEATER_PIN'))
AC_PIN = int(config.get('main','AC_PIN'))
FAN_PIN = int(config.get('main','FAN_PIN'))
on_temp = config.get('main','on_temp')
off_temp = config.get('main','off_temp')

sqliteEnabled = config.getboolean('sqlite','enabled')
if sqliteEnabled == True:
    import sqlite3


#mail config
mailEnabled = config.getboolean('mail', 'enabled')
#gps config
#gpsEnabled = config.getboolean('gps','enabled')

f = open("status", "r")
targetTemp = f.readline().strip()
mode = f.readline().strip()
scheduleEnabled = f.readline().strip()
gpsEnabled = f.readline().strip()
f.close()



if mailEnabled == True:
    import smtplib

    config.read("mailconf.txt")
    SMTP_SERVER = config.get('mailconf','SMTP_SERVER')
    SMTP_PORT = int(config.get('mailconf','SMTP_PORT'))
    username = config.get('mailconf','username')
    password = config.get('mailconf','password')
    sender = config.get('mailconf','sender')
    errorThreshold = float(config.get('mail','errorThreshold'))
    roommate_1_mail = config.get('mailconf','roommate_1_mail')
    roommate_2_mail = config.get('mailconf','roommate_2_mail')

#schedule config
#scheduleEnabled = config.getboolean('schedule', 'enabled')

config.read("scheduleconf.txt")
now = datetime.datetime.now()

#Read schedule config file and define on and off times per day

monday_off_hour = config.get('scheduleconf','monday_off_hour')
monday_off_minute = config.get('scheduleconf','monday_off_minute')
monday_on_hour = config.get('scheduleconf','monday_on_hour')
monday_on_minute = config.get('scheduleconf','monday_on_minute')
monday_off = now.replace(hour=int(monday_off_hour), minute=int(monday_off_minute), second=0, microsecond=0)
monday_on = now.replace(hour=int(monday_on_hour), minute=int(monday_on_minute), second=0, microsecond=0)

tuesday_off_hour = config.get('scheduleconf','tuesday_off_hour')
tuesday_off_minute = config.get('scheduleconf','tuesday_off_minute')
tuesday_on_hour = config.get('scheduleconf','tuesday_on_hour')
tuesday_on_minute = config.get('scheduleconf','tuesday_on_minute')
tuesday_off = now.replace(hour=int(tuesday_off_hour), minute=int(tuesday_off_minute), second=0, microsecond=0)
tuesday_on = now.replace(hour=int(tuesday_on_hour), minute=int(tuesday_on_minute), second=0, microsecond=0)

wednesday_off_hour = config.get('scheduleconf','wednesday_off_hour')
wednesday_off_minute = config.get('scheduleconf','wednesday_off_minute')
wednesday_on_hour = config.get('scheduleconf','wednesday_on_hour')
wednesday_on_minute = config.get('scheduleconf','wednesday_on_minute')
wednesday_off = now.replace(hour=int(wednesday_off_hour), minute=int(wednesday_off_minute), second=0, microsecond=0)
wednesday_on = now.replace(hour=int(wednesday_on_hour), minute=int(wednesday_on_minute), second=0, microsecond=0)

thursday_off_hour = config.get('scheduleconf','thursday_off_hour')
thursday_off_minute = config.get('scheduleconf','thursday_off_minute')
thursday_on_hour = config.get('scheduleconf','thursday_on_hour')
thursday_on_minute = config.get('scheduleconf','thursday_on_minute')
thursday_off = now.replace(hour=int(thursday_off_hour), minute=int(thursday_off_minute), second=0, microsecond=0)
thursday_on = now.replace(hour=int(thursday_on_hour), minute=int(thursday_on_minute), second=0, microsecond=0)

friday_off_hour = config.get('scheduleconf','friday_off_hour')
friday_off_minute = config.get('scheduleconf','friday_off_minute')
friday_on_hour = config.get('scheduleconf','friday_on_hour')
friday_on_minute = config.get('scheduleconf','friday_on_minute')
friday_off = now.replace(hour=int(friday_off_hour), minute=int(friday_off_minute), second=0, microsecond=0)
friday_on = now.replace(hour=int(friday_on_hour), minute=int(friday_on_minute), second=0, microsecond=0)

saturday_off_hour = config.get('scheduleconf','saturday_off_hour')
saturday_off_minute = config.get('scheduleconf','saturday_off_minute')
saturday_on_hour = config.get('scheduleconf','saturday_on_hour')
saturday_on_minute = config.get('scheduleconf','saturday_on_minute')
saturday_off = now.replace(hour=int(saturday_off_hour), minute=int(saturday_off_minute), second=0, microsecond=0)
saturday_on = now.replace(hour=int(saturday_on_hour), minute=int(saturday_on_minute), second=0, microsecond=0)

sunday_off_hour = config.get('scheduleconf','sunday_off_hour')
sunday_off_minute = config.get('scheduleconf','sunday_off_minute')
sunday_on_hour = config.get('scheduleconf','sunday_on_hour')
sunday_on_minute = config.get('scheduleconf','sunday_on_minute')
sunday_off = now.replace(hour=int(sunday_off_hour), minute=int(sunday_off_minute), second=0, microsecond=0)
sunday_on = now.replace(hour=int(sunday_on_hour), minute=int(sunday_on_minute), second=0, microsecond=0)


class rubustatDaemon(Daemon):
    
    def configureGPIO(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(HEATER_PIN, GPIO.OUT)
        GPIO.setup(AC_PIN, GPIO.OUT)
        GPIO.setup(FAN_PIN, GPIO.OUT)
        subprocess.Popen("echo " + str(HEATER_PIN) + " > /sys/class/gpio/export", shell=True)
        subprocess.Popen("echo " + str(AC_PIN) + " > /sys/class/gpio/export", shell=True)
        subprocess.Popen("echo " + str(FAN_PIN) + " > /sys/class/gpio/export", shell=True)

    def getHVACState(self):
        heatStatus = int(subprocess.Popen("cat /sys/class/gpio/gpio" + str(HEATER_PIN) + "/value", shell=True, stdout=subprocess.PIPE).stdout.read().strip())
        coolStatus = int(subprocess.Popen("cat /sys/class/gpio/gpio" + str(AC_PIN) + "/value", shell=True, stdout=subprocess.PIPE).stdout.read().strip())
        fanStatus = int(subprocess.Popen("cat /sys/class/gpio/gpio" + str(FAN_PIN) + "/value", shell=True, stdout=subprocess.PIPE).stdout.read().strip())

        if heatStatus == 1 and fanStatus == 1:
            #heating
            return 1
            
        elif coolStatus == 1 and fanStatus == 1:
            #cooling
            return -1

        elif heatStatus == 0 and coolStatus == 0 and fanStatus == 0:
            #idle
            return 0

        else:
            #broken
            return 2

    def cool(self):
        GPIO.output(HEATER_PIN, False)
        GPIO.output(AC_PIN, True)
        GPIO.output(FAN_PIN, True)
        return -1

    def heat(self):
        GPIO.output(HEATER_PIN, True)
        GPIO.output(AC_PIN, False)
        GPIO.output(FAN_PIN, True)
        return 1

    def fan_to_idle(self): 
        #to blow the rest of the heated / cooled air out of the system
        GPIO.output(HEATER_PIN, False)
        GPIO.output(AC_PIN, False)
        GPIO.output(FAN_PIN, True)

    def idle(self):
        GPIO.output(HEATER_PIN, False)
        GPIO.output(AC_PIN, False)
        GPIO.output(FAN_PIN, False)
        #delay to preserve compressor
        time.sleep(360)
        return 0

    if mailEnabled == True:
        def sendErrorMail(self, subject, body, recipient):
            headers = ["From: " + sender,
                       "Subject: " + subject,
                       "To: " + recipient,
                       "MIME-Version: 1.0",
                       "Content-Type: text/html"]
            headers = "\r\n".join(headers)
            session = smtplib.SMTP(SMTP_SERVER, SMTP_PORT) 
            session.ehlo()
            #you may need to comment this line out if you're a crazy person
            #and use non-tls SMTP servers
            session.starttls()
            session.ehlo
            session.login(username, password)
            session.sendmail(sender, recipient, headers + "\r\n\r\n" + body)
            session.quit()


    def schedule_change(self, scheduled):
	#Read contents of status file
	f = open("status", "r")
	targetTemp = f.readline().strip()
	mode = f.readline().strip()
	scheduleEnabled = f.readline().strip()
	gpsEnabled = f.readline().strip()
	f.close()
	#if the current time is within the scheduled on-period, update status file setTemp = on_temp
	if scheduled == True:
	    f = open("status", "w")
	    f.write(on_temp + "\n" + mode + "\n" + scheduleEnabled + "\n" + gpsEnabled)
	    f.close()

	#if the current time is within the scheduled off-period, update status file setTemp = off_temp
	if scheduled == False:
	    f = open("status", "w")
	    f.write(off_temp + "\n" + mode + "\n" + scheduleEnabled + "\n" + gpsEnabled)
	    f.close()	    

    def check_schedule(self):
	now = datetime.datetime.now()
	day_of_week = datetime.date.today().weekday() # 0 is Monday, 6 is Sunday
	if day_of_week == 0:
	    if now < monday_off:
		scheduled = True
	    elif now > monday_off and now < monday_on:
		scheduled = False
	    elif now > monday_on:
		scheduled = True
	elif day_of_week == 1:
	    if now < tuesday_off:
		scheduled = True
	    elif now > tuesday_off and now < tuesday_on:
		scheduled = False
	    elif now > tuesday_on:
		scheduled = True
	elif day_of_week == 2:
	    if now < wednesday_off:
		scheduled = True
	    elif now > wednesday_off and now < wednesday_on:
		scheduled = False
	    elif now > wednesday_on:
		scheduled = True  
	elif day_of_week == 3:
	    if now < thursday_off:
		scheduled = True
	    elif now > thursday_off and now < thursday_on:
		scheduled = False
	    elif now > thursday_on:
		scheduled = True
	elif day_of_week == 4:
	    if now < friday_off:
		scheduled = True
	    elif now > friday_off and now < friday_on:
		scheduled = False
	    elif now > friday_on:
		scheduled = True
	elif day_of_week == 5:
	    if now < saturday_off:
		scheduled = True
	    elif now > saturday_off and now < saturday_on:
		scheduled = False
	    elif now > saturday_on:
		scheduled = True
	elif day_of_week == 6:
	    if now < sunday_off:
		scheduled = True
	    elif now > sunday_off and now < sunday_on:
		scheduled = False
	    elif now > sunday_on:
		scheduled = True
	    

	self.schedule_change(scheduled)

    def gps_change(self, scheduled):
	#Reads contents of status file
	f = open("status", "r")
	targetTemp = f.readline().strip()
	mode = f.readline().strip()
	scheduleEnabled = f.readline().strip()
	gpsEnabled = f.readline()
	f.close()
    
	#if the current time is within the scheduled on-period
	if scheduled == True:
	    f = open("status", "w")
	    f.write(on_temp + "\n" + mode + "\n" + scheduleEnabled + "\n" + gpsEnabled)
	    f.close()
	    targetTemp = on_temp

	#if the current time is within the scheduled off-period
	if scheduled == False:
	    f = open("status", "w")
	    f.write(off_temp + "\n" + mode + "\n" + scheduleEnabled + "\n" + gpsEnabled)
	    f.close()
	    targetTemp = off_temp

	else: 
	    f = open("status", "w")
	    f.write(targetTemp + "\n" + mode + "\n" + scheduleEnabled + "\n" + gpsEnabled)
	    f.close()


    def run(self):
        lastLog = datetime.datetime.now()
        lastMail = datetime.datetime.now()
        self.configureGPIO()
	emails = 0
	length = 0
	roomate_2 = "gone"
	roomate_1 = "gone"

        while True:
            #change cwd to wherever rubustat_daemon is
            abspath = os.path.abspath(__file__)
            dname = os.path.dirname(abspath)
            os.chdir(dname)
            indoorTemp = float(getIndoorTemp())
            hvacState = int(self.getHVACState())

            file = open("status", "r")
            targetTemp = float(file.readline().strip())
            mode = file.readline().strip()
	    scheduleEnabled = file.readline().strip()
	    gpsEnabled = file.readline()
            file.close()
	    
            now = datetime.datetime.now()
            logElapsed = now - lastLog
            mailElapsed = now - lastMail

	    if scheduleEnabled == "True":
		self.check_schedule()
<<<<<<< HEAD
<<<<<<< HEAD
=======
=======
>>>>>>> FETCH_HEAD
		
	    if gpsEnabled == "True":
		response = feedparser.parse("https://" + username + ":" + password + "@mail.google.com/gmail/feed/atom")
		unread_count = int(response["feed"]["fullcount"])
		scheduled = ""
>>>>>>> FETCH_HEAD
		
	    if gpsEnabled == "True":
		try:
			response = feedparser.parse("https://" + username + ":" + password + "@mail.google.com/gmail/feed/atom")
			unread_count = int(response["feed"]["fullcount"])
			scheduled = ""
		except:
			unread_count = 0
			scheduled = ""
		#If there's messages, let's do something.
		if unread_count != 0:
		    for i in range(0,unread_count):
			if response['items'][i].title == "roomate_2 exited":
			    roomate_2 = "gone"
			elif response['items'][i].title == "roomate_2 entered":
			    roomate_2 = "here"
			elif response['items'][i].title == "roomate_1 exited":
			    roomate_1 = "gone"
			elif response['items'][i].title == "roomate_1 entered":
			    roomate_1 = "here"

			if response['items'][i].title == "roomate_1 entered" and roomate_2 == "gone":
			    subject = "Mikey Entered"
			    body =  "The A/C has been turned down to " + str(on_temp) + ". It is currently " + str(indoorTemp) + " in the house."
			    recipient = roommate_1_mail
			    self.sendErrorMail(subject, body, recipient)
<<<<<<< HEAD
			elif response['items'][i].title == "roomate_1 exited" and roomate_2 == "here":
			    subject = "Mikey Exited"
			    body = "The A/C will be turned up to " + str(off_temp) + " when Roomate_2 leaves. It is currently " + str(indoorTemp) + " in the house."
			    recipient = roommate_1_mail
=======
			elif response['items'][i].title == "roommate2 exited" and roommate1 == "here":
			    subject = "C U soon sucka"
			    body = "The A/C will be turned down to " + str(on_temp) + " when Roommate1 leaves. It is currently " + str(indoorTemp) + " in the house."
			    recipient = roommate_2_mail
>>>>>>> FETCH_HEAD
			    self.sendErrorMail(subject, body, recipient)
			elif response['items'][i].title == "roomate_1 exited" and roomate_2 == "gone":
			    subject = "Mikey Exited"
			    body = "The A/C has been turned up to " + str(off_temp) + ". It is currently " + str(indoorTemp) + " in the house."
			    recipient = roommate_1_mail
			    self.sendErrorMail(subject, body, recipient)
			elif response['items'][i].title == "roomate_2 entered" and roomate_1 == "gone":
			    subject = "Roomate_2 Entered"
			    body = "The A/C has been turned down to " + str(on_temp) + ". It is currently " + str(indoorTemp) + " in the house."
			    recipient = roommate_2_mail
			    self.sendErrorMail(subject, body, recipient)
			elif response['items'][i].title == "roomate_2 exited" and roomate_1 == "here":
			    subject = "Roomate_2 Exited"
			    body = "The A/C will be turned up to " + str(off_temp) + " when Mikey leaves. It is currently " + str(indoorTemp) + " in the house."
			    recipient = roommate_2_mail
			    self.sendErrorMail(subject, body, recipient)
			elif response['items'][i].title == "roomate_2 exited" and roomate_1 == "gone":
			    subject = "Roomate_2 Exited"
			    body = "The A/C has been turned up to " + str(off_temp) + ". It is currently " + str(indoorTemp) + " in the house."
			    recipient = roommate_2_mail
			    self.sendErrorMail(subject, body, recipient)

			#We've processed the message, now let's mark it as read so we don't act on it again
			if unread_count != 0:
			    obj = imaplib.IMAP4_SSL('imap.gmail.com', '993')
			    obj.login(username, password)
			    obj.select('Inbox')
			    typ ,data = obj.search(None,'UnSeen')
			    obj.store(data[0].replace(' ',','),'+FLAGS','\Seen')

		    if roomate_2 == "gone" and roomate_1 == "gone":
			    scheduled = False
		    elif roomate_2 == "here" and roomate_1 == "gone":
			    scheduled = True
		    elif roomate_2 == "gone" and roomate_1 == "here":
			    scheduled = True
		    elif roomate_2 == "here" and roomate_1 == "here":
			    scheduled = True

		    self.gps_change(scheduled)
		    

            ### check if we need to send error mail
            #cooling 
            #it's 78, we want it to be 72, and the error threshold is 5 = this triggers

	    if mode == "cool":
		if mailEnabled == True and (mailElapsed > datetime.timedelta(minutes=20)) and (indoorTemp - float(targetTemp) ) > errorThreshold and emails <= 5:
		    length += 20
		    emails += 1
		    body = "The A/C has been at least " + str(errorThreshold) + " degrees off from it's setpoint for " + str(length) + " minutes. There may be a problem." + " This is notification " + str(emails) + " of 6. <br><br>The setpoint is " + str(targetTemp) + " and the current temperature is " + str(indoorTemp) + "."
		    subject = "There is a problem with the A/C"
		    recipient = roommate_1_mail
		    self.sendErrorMail(subject, body, recipient)
		    recipient = roommate_2_mail
		    self.sendErrorMail(subject, body, recipient)
		    if emails == 6:
			body = "The A/C has been at least " + str(errorThreshold) + " degrees off from it's setpoint for " + str(length) + " minutes. There may be a problem." + " This is notification " + str(emails) + " of 6. No more mail will be sent. Check http://thermostat.aneis.ch for updates. <br><br>The setpoint is " + str(targetTemp) + " and the current temperature is " + str(indoorTemp) + "."
			subject = "This is the last you'll hear from me..."
			recipient = roommate_1_mail
			self.sendErrorMail(subject, body, recipient)
			#Just reset the recipient and send with same body and subject instead on concatinating emails
			recipient = roommate_2_mail
			self.sendErrorMail(subject, body, recipient)  
		    lastMail = datetime.datetime.now()

		    if DEBUG == 1:
			log = open("logs/debug_" + datetime.datetime.now().strftime('%Y%m%d') + ".log", "a")
			log.write("MAIL: Sent mail to " + recipient + " at " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\n")
			log.close()

		if mailEnabled == True and (indoorTemp - float(targetTemp) ) < errorThreshold:
		    emails = 0
		    length = 0

            #heat 
            #it's 72, we want it to be 78, and the error threshold is 5 = this triggers
            elif mode == "heat":
		if mailEnabled == True and (mailElapsed > datetime.timedelta(minutes=20)) and (float(targetTemp) - indoorTemp ) > errorThreshold and emails <=5:
		    length += 20
		    emails += 1
		    body = "The A/C has been at least " + str(errorThreshold) + " degrees off from it's setpoint for " + str(length) + " minutes. There may be a problem." + " This is notification " + str(emails) + " of 6. <br><br>The setpoint is " + str(targetTemp) + " and the current temperature is " + str(indoorTemp) + "."
		    subject = "There is a problem with the A/C"
		    recipient = roommate_1_mail
		    self.sendErrorMail(subject, body, recipient)
		    #Just reset the recipient and send with same body and subject instead on concatinating emails
		    recipient = roommate_2_mail
		    self.sendErrorMail(subject, body, recipient)
		    if emails == 6:
			body = "The A/C has been at least " + str(errorThreshold) + " degrees off from it's setpoint for " + str(length) + " minutes. There may be a problem." + " This is notification " + str(emails) + " of 6. No more mail will be sent. Check http://thermostat.aneis.ch for updates. <br><br>The setpoint is " + str(targetTemp) + " and the current temperature is " + str(indoorTemp) + "."
			recipient = roommate_1_mail
			self.sendErrorMail(subject, body, recipient)
			recipient = roommate_2_mail
			self.sendErrorMail(subject, body, recipient)  
		    lastMail = datetime.datetime.now()
		    
		    if DEBUG == 1:
			log = open("logs/debug_" + datetime.datetime.now().strftime('%Y%m%d') + ".log", "a")
			log.write("MAIL: Sent mail to " + recipient + " at " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\n")
			log.close()

		if mailEnabled == True and (float(targetTemp) - indoorTemp ) < errorThreshold:
		    emails = 0
		    length = 0


            #logging actual temp and indoor temp to sqlite database.
            #you can do fun things with this data, like make charts! 
            if logElapsed > datetime.timedelta(minutes=6) and sqliteEnabled:
                c.execute('INSERT INTO logging VALUES(?, ?, ?)', (now, indoorTemp, targetTemp))
                conn.commit()
                lastLog = datetime.datetime.now()


            # heater mode
            if mode == "heat":
                if hvacState == 0: #idle
                    if indoorTemp < targetTemp - inactive_hysteresis:
                        if DEBUG == 1:
                            log = open("logs/debug_" + datetime.datetime.now().strftime('%Y%m%d') + ".log", "a")
                            log.write("STATE: Switching to heat at " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\n")
                            log.close()
                        hvacState = self.heat()

                elif hvacState == 1: #heating
                    if indoorTemp > targetTemp + active_hysteresis:
                        if DEBUG == 1:
                            log = open("logs/debug_" + datetime.datetime.now().strftime('%Y%m%d') + ".log", "a")
                            log.write("STATE: Switching to fan_to_idle at " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\n")
                            log.close()
			emails = 0
			length = 0
                        self.fan_to_idle()
                        time.sleep(30)
                        if DEBUG == 1:
                            log = open("logs/debug_" + datetime.datetime.now().strftime('%Y%m%d') + ".log", "a")
                            log.write("STATE: Switching to idle at " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\n")
                            log.close()
                        hvacState = idle()

                elif hvacState == -1: # it's cold out, why is the AC running?
                        if DEBUG == 1:
                            log = open("logs/debug_" + datetime.datetime.now().strftime('%Y%m%d') + ".log", "a")
                            log.write("STATE: Switching to idle at " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\n")
                            log.close()
                        hvacState = self.idle()

            # ac mode
            elif mode == "cool":
                if hvacState == 0: #idle
                    if indoorTemp > targetTemp + inactive_hysteresis:
                        if DEBUG == 1:
                            log = open("logs/debug_" + datetime.datetime.now().strftime('%Y%m%d') + ".log", "a")
                            log.write("STATE: Switching to cool at " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\n")
                            log.close()
                        hvacState = self.cool()

                elif hvacState == -1: #cooling
                    if indoorTemp < targetTemp - active_hysteresis:
                        if DEBUG == 1:
                            log = open("logs/debug_" + datetime.datetime.now().strftime('%Y%m%d') + ".log", "a")
                            log.write("STATE: Switching to fan_to_idle at " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\n")
                            log.close()
			emails = 0
			length = 0
                        self.fan_to_idle()
                        time.sleep(30)
                        if DEBUG == 1:
                            log = open("logs/debug_" + datetime.datetime.now().strftime('%Y%m%d') + ".log", "a")
                            log.write("STATE: Switching to idle at " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\n")
                            log.close()
                        hvacState = self.idle()

                elif hvacState == 1: # it's hot out, why is the heater on?
                        if DEBUG == 1:
                            log = open("logs/debug_" + datetime.datetime.now().strftime('%Y%m%d') + ".log", "a")
                            log.write("STATE: Switching to fan_to_idle at " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\n")
                            log.close()
                        hvacState = self.idle()
            else:
                print "It broke."

            #loggin'stuff
            if DEBUG == 1:
                heatStatus = int(subprocess.Popen("cat /sys/class/gpio/gpio" + str(HEATER_PIN) + "/value", shell=True, stdout=subprocess.PIPE).stdout.read().strip())
                coolStatus = int(subprocess.Popen("cat /sys/class/gpio/gpio" + str(AC_PIN) + "/value", shell=True, stdout=subprocess.PIPE).stdout.read().strip())
                fanStatus = int(subprocess.Popen("cat /sys/class/gpio/gpio" + str(FAN_PIN) + "/value", shell=True, stdout=subprocess.PIPE).stdout.read().strip())
                log = open("logs/debug_" + datetime.datetime.now().strftime('%Y%m%d') + ".log", "a")
                log.write("Report at " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\n")
                log.write("hvacState = " + str(hvacState)+ "\n")
                log.write("indoorTemp = " + str(indoorTemp)+ "\n")
                log.write("targetTemp = " + str(targetTemp)+ "\n")
                log.write("heatStatus = " + str(heatStatus) + "\n")
                log.write("coolStatus = " + str(coolStatus)+ "\n")
                log.write("fanStatus = " + str(fanStatus)+ "\n")
		#Who is home?
		log.write("roommateStatus = roomate_1: " + str(roomate_1) + " roomate_2: " + str(roomate_2) +"\n")

                log.close()

            time.sleep(5)


if __name__ == "__main__":
        daemon = rubustatDaemon('rubustatDaemon.pid')
      
        #Setting up logs
        if not os.path.exists("logs"):
            subprocess.Popen("mkdir logs", shell=True)

        if sqliteEnabled == True:
            conn = sqlite3.connect("temperatureLogs.db")
            c = conn.cursor()
            c.execute('CREATE TABLE IF NOT EXISTS logging (datetime TIMESTAMP, actualTemp FLOAT, targetTemp INT)')    

        if len(sys.argv) == 2:
                if 'start' == sys.argv[1]:
                        daemon.start()
                elif 'stop' == sys.argv[1]:
                        #stop all HVAC activity when daemon stops
                        GPIO.setmode(GPIO.BCM)
                        GPIO.setup(HEATER_PIN, GPIO.OUT)
                        GPIO.setup(AC_PIN, GPIO.OUT)
                        GPIO.setup(FAN_PIN, GPIO.OUT)
                        GPIO.output(HEATER_PIN, False)
                        GPIO.output(AC_PIN, False)
                        GPIO.output(FAN_PIN, False)
                        daemon.stop()
                elif 'restart' == sys.argv[1]:
                        daemon.restart()
                else:
                        print "Unknown command"
                        sys.exit(2)
                sys.exit(0)
        else:
                print "usage: %s start|stop|restart" % sys.argv[0]
                sys.exit(2)
