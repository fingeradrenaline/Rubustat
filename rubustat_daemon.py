#! /usr/bin/python
 
import sys
import subprocess
import os
import time
import RPi.GPIO as GPIO
import datetime
import ConfigParser

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

sqliteEnabled = config.getboolean('sqlite','enabled')
if sqliteEnabled == True:
    import sqlite3

#mail config
mailEnabled = config.getboolean('mail', 'enabled')


if mailEnabled == True:
    import smtplib

    config.read("mailconf.txt")
    SMTP_SERVER = config.get('mailconf','SMTP_SERVER')
    SMTP_PORT = int(config.get('mailconf','SMTP_PORT'))
    username = config.get('mailconf','username')
    password = config.get('mailconf','password')
    sender = config.get('mailconf','sender')
    recipient = config.get('mailconf','recipient')
    subject = config.get('mailconf','subject')
    #body = config.get('mailconf','body')
    errorThreshold = float(config.get('mail','errorThreshold'))

#schedule config
scheduleEnabled = config.getboolean('schedule', 'enabled')


if scheduleEnabled == True:

    config.read("scheduleconf.txt")
    on_temp = config.get('scheduleconf','on_temp')
    off_temp = config.get('scheduleconf','off_temp')
    now = datetime.datetime.now()
    
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
        def sendErrorMail(self, body):
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

    if scheduleEnabled == True:
	def schedule_change(self, scheduled):
	    #Reads contents of status file
	    f = open("status", "r")
	    targetTemp = f.readline().strip()
	    mode = f.readline()
	    f.close()
	    #if the current time is within the scheduled on-period
	    if scheduled == True:
		f = open("status", "w")
		f.write(on_temp + "\n" + mode)
		f.close()
	    #if the current time is within the scheduled off-period
	    if scheduled == False:
		f = open("status", "w")
		f.write(off_temp + "\n" + mode)
		f.close()
	    

	def check_schedule(self):
	    now = datetime.datetime.now()
	    day_of_week = datetime.date.today().weekday() # 0 is Monday, 6 is Sunday
	    
	    #wow this is ugly
	    #If there is a problem, defaults to off_temp
	    #Ignore all the comments, they're for bug squashing
	    if day_of_week == 0:
		if now < monday_off:
		    #body = "Off: " +  str(monday_off) + "<br>On: " + str(monday_on) + "<br>Now: " + str(now) + "<br>Day: " + str(day_of_week) + "<br>Before Off <br>Temp:" + on_temp
		    scheduled = True
		    #self.sendErrorMail(body)
		elif now > monday_off and now < monday_on:
		    #body = "Off: " +  str(monday_off) + "<br>On: " + str(monday_on) + "<br>Now: " + str(now) + "<br>Day: " + str(day_of_week) + "<br>Before On <br>Temp:" + off_temp
		    scheduled = False
		    #self.sendErrorMail(body)
		elif now > monday_on:
		    #body = "Off: " +  str(monday_off) + "<br>On: " + str(monday_on) + "<br>Now: " + str(now) + "<br>Day: " + str(day_of_week) + "<br>After On <br>Temp:" + on_temp
		    scheduled = True
		    #self.sendErrorMail(body)
	    
	    elif day_of_week == 1:
		if now < tuesday_off:
		    #body = "Off: " +  str(tuesday_off) + "<br>On: " + str(tuesday_on) + "<br>Now: " + str(now) + "<br>Day: " + str(day_of_week) + "<br>Before Off <br>Temp:" + on_temp
		    scheduled = True
		    #self.sendErrorMail(body)
		elif now > tuesday_off and now < tuesday_on:
		    #body = "Off: " +  str(tuesday_off) + "<br>On: " + str(tuesday_on) + "<br>Now: " + str(now) + "<br>Day: " + str(day_of_week) + "<br>Before On <br>Temp:" + off_temp
		    scheduled = False
		    #self.sendErrorMail(body)
		elif now > tuesday_on:
		    #body = "Off: " +  str(tuesday_off) + "<br>On: " + str(tuesday_on) + "<br>Now: " + str(now) + "<br>Day: " + str(day_of_week) + "<br>After On <br>Temp:" + on_temp
		    scheduled = True
		    #self.sendErrorMail(body)
		
	    elif day_of_week == 2:
		if now < wednesday_off:
		    #body = "Off: " +  str(wednesday_off) + "<br>On: " + str(wednesday_on) + "<br>Now: " + str(now) + "<br>Day: " + str(day_of_week) + "<br>Before Off <br>Temp:" + on_temp
		    scheduled = True
		    #self.sendErrorMail(body)
		elif now > wednesday_off and now < wednesday_on:
		    #body = "Off: " +  str(wednesday_off) + "<br>On: " + str(wednesday_on) + "<br>Now: " + str(now) + "<br>Day: " + str(day_of_week) + "<br>Before On <br>Temp:" + off_temp
		    scheduled = False
		    #self.sendErrorMail(body)
		elif now > wednesday_on:
		    #body = "Off: " +  str(wednesday_off) + "<br>On: " + str(wednesday_on) + "<br>Now: " + str(now) + "<br>Day: " + str(day_of_week) + "<br>After On <br>Temp:" + on_temp
		    scheduled = True
		    #self.sendErrorMail(body)
		    
	    elif day_of_week == 3:
		if now < thursday_off:
		    #body = "Off: " +  str(thursday_off) + "<br>On: " + str(thursday_on) + "<br>Now: " + str(now) + "<br>Day: " + str(day_of_week) + "<br>Before Off <br>Temp:" + on_temp
		    scheduled = True
		    #self.sendErrorMail(body)
		elif now > thursday_off and now < thursday_on:
		    #body = "Off: " +  str(thursday_off) + "<br>On: " + str(thursday_on) + "<br>Now: " + str(now) + "<br>Day: " + str(day_of_week) + "<br>Before On <br>Temp:" + off_temp
		    scheduled = False
		    #self.sendErrorMail(body)
		elif now > thursday_on:
		    #body = "Off: " +  str(thursday_off) + "<br>On: " + str(thursday_on) + "<br>Now: " + str(now) + "<br>Day: " + str(day_of_week) + "<br>After On <br>Temp:" + on_temp
		    scheduled = True
		    #self.sendErrorMail(body)
		    
	    elif day_of_week == 4:
		if now < friday_off:
		    #body = "Off: " +  str(friday_off) + "<br>On: " + str(friday_on) + "<br>Now: " + str(now) + "<br>Day: " + str(day_of_week) + "<br>Before Off <br>Temp:" + on_temp
		    scheduled = True
		    #self.sendErrorMail(body)
		elif now > friday_off and now < friday_on:
		    #body = "Off: " +  str(friday_off) + "<br>On: " + str(friday_on) + "<br>Now: " + str(now) + "<br>Day: " + str(day_of_week) + "<br>Before On <br>Temp:" + off_temp
		    scheduled = False
		    #self.sendErrorMail(body)
		elif now > friday_on:
		    #body = "Off: " +  str(friday_off) + "<br>On: " + str(friday_on) + "<br>Now: " + str(now) + "<br>Day: " + str(day_of_week) + "<br>After On <br>Temp:" + on_temp
		    scheduled = True
		    #self.sendErrorMail(body)
		    
	    elif day_of_week == 5:
		if now < saturday_off:
		    #body = "Off: " +  str(saturday_off) + "<br>On: " + str(saturday_on) + "<br>Now: " + str(now) + "<br>Day: " + str(day_of_week) + "<br>Before Off <br>Temp:" + on_temp
		    scheduled = True
		    #self.sendErrorMail(body)
		elif now > saturday_off and now < saturday_on:
		    #body = "Off: " +  str(saturday_off) + "<br>On: " + str(saturday_on) + "<br>Now: " + str(now) + "<br>Day: " + str(day_of_week) + "<br>Before On <br>Temp:" + off_temp
		    scheduled = False
		    #self.sendErrorMail(body)
		elif now > saturday_on:
		    #body = "Off: " +  str(saturday_off) + "<br>On: " + str(saturday_on) + "<br>Now: " + str(now) + "<br>Day: " + str(day_of_week) + "<br>After On <br>Temp:" + on_temp
		    scheduled = True
		    #self.sendErrorMail(body)
		    
	    elif day_of_week == 6:
		if now < sunday_off:
		    #body = "Off: " +  str(sunday_off) + "<br>On: " + str(sunday_on) + "<br>Now: " + str(now) + "<br>Day: " + str(day_of_week) + "<br>Before Off <br>Temp:" + on_temp
		    scheduled = True
		    #self.sendErrorMail(body)
		elif now > sunday_off and now < sunday_on:
		    #body = "Off: " +  str(sunday_off) + "<br>On: " + str(sunday_on) + "<br>Now: " + str(now) + "<br>Day: " + str(day_of_week) + "<br>Before On <br>Temp:" + off_temp
		    scheduled = False
		    #self.sendErrorMail(body)
		elif now > sunday_on:
		    #body = "Off: " +  str(sunday_off) + "<br>On: " + str(sunday_on) + "<br>Now: " + str(now) + "<br>Day: " + str(day_of_week) + "<br>After On <br>Temp:" + on_temp
		    scheduled = True
		    #self.sendErrorMail(body)
		

	    self.schedule_change(scheduled)

    def run(self):
        lastLog = datetime.datetime.now()
        lastMail = datetime.datetime.now()
        self.configureGPIO()
	emails = 0
	length = 0
        while True:

            #change cwd to wherever rubustat_daemon is
            abspath = os.path.abspath(__file__)
            dname = os.path.dirname(abspath)
            os.chdir(dname)

            indoorTemp = float(getIndoorTemp())
            hvacState = int(self.getHVACState())

            file = open("status", "r")
            targetTemp = float(file.readline())
            mode = file.readline()
            file.close()

            now = datetime.datetime.now()
            logElapsed = now - lastLog
            mailElapsed = now - lastMail
	    self.check_schedule()
	
            ### check if we need to send error mail
            #cooling 
            #it's 78, we want it to be 72, and the error threshold is 5 = this triggers
            if mailEnabled == True and (mailElapsed > datetime.timedelta(minutes=20)) and (indoorTemp - float(targetTemp) ) > errorThreshold and emails <= 5:
		length += 20
		emails += 1
		body = "The A/C has been at least 10 degrees off from it's setpoint for " + str(length) + " minutes. There may be a problem." + " This is notification " + str(emails) + " of 6. <br><br>The setpoint is " + str(targetTemp) + " and the current temperature is " + str(indoorTemp) + "."
		if emails == 6:
		    body = "The A/C has been at least 10 degrees off from it's setpoint for " + str(length) + " minutes. There may be a problem." + " This is notification " + str(emails) + " of 6. No more mail will be sent. Check http://THERMOSTAT-ADDRESS for updates. <br><br>The setpoint is " + str(targetTemp) + " and the current temperature is " + str(indoorTemp) + "."
		self.sendErrorMail(body)
    
                lastMail = datetime.datetime.now()
                if DEBUG == 1:
                    log = open("logs/debug_" + datetime.datetime.now().strftime('%Y%m%d') + ".log", "a")
                    log.write("MAIL: Sent mail to " + recipient + " at " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + "\n")
                    log.close()

            #heat 
            #it's 72, we want it to be 78, and the error threshold is 5 = this triggers
            if mailEnabled == True and (mailElapsed > datetime.timedelta(minutes=20)) and (float(targetTemp) - indoorTemp ) > errorThreshold and emails <=5:
		length += 20
		emails += 1
		body = "The A/C has been at least 10 degrees off from it's setpoint for " + str(length) + " minutes. There may be a problem." + " This is notification " + str(emails) + " of 6. <br><br>The setpoint is " + str(targetTemp) + " and the current temperature is " + str(indoorTemp) + "."
		if emails == 6:
		    body = "The A/C has been at least 10 degrees off from it's setpoint for " + str(length) + " minutes. There may be a problem." + " This is notification " + str(emails) + " of 6. No more mail will be sent. Check http://THERMOSTAT-ADDRESS for updates. <br><br>The setpoint is " + str(targetTemp) + " and the current temperature is " + str(indoorTemp) + "."
		
		self.sendErrorMail(body)
                lastMail = datetime.datetime.now()
                if DEBUG == 1:
                    log = open("logs/debug_" + datetime.datetime.now().strftime('%Y%m%d') + ".log", "a")
                    log.write("MAIL: Sent mail to " + recipient + " at " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + "\n")
                    log.close()


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
                            log.write("STATE: Switching to heat at " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + "\n")
                            log.close()
                        hvacState = self.heat()

                elif hvacState == 1: #heating
                    if indoorTemp > targetTemp + active_hysteresis:
                        if DEBUG == 1:
                            log = open("logs/debug_" + datetime.datetime.now().strftime('%Y%m%d') + ".log", "a")
                            log.write("STATE: Switching to fan_to_idle at " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + "\n")
                            log.close()
			emails = 0
			length = 0
                        self.fan_to_idle()
                        time.sleep(30)
                        if DEBUG == 1:
                            log = open("logs/debug_" + datetime.datetime.now().strftime('%Y%m%d') + ".log", "a")
                            log.write("STATE: Switching to idle at " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + "\n")
                            log.close()
                        hvacState = idle()

                elif hvacState == -1: # it's cold out, why is the AC running?
                        if DEBUG == 1:
                            log = open("logs/debug_" + datetime.datetime.now().strftime('%Y%m%d') + ".log", "a")
                            log.write("STATE: Switching to idle at " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + "\n")
                            log.close()
                        hvacState = self.idle()

            # ac mode
            elif mode == "cool":
                if hvacState == 0: #idle
                    if indoorTemp > targetTemp + inactive_hysteresis:
                        if DEBUG == 1:
                            log = open("logs/debug_" + datetime.datetime.now().strftime('%Y%m%d') + ".log", "a")
                            log.write("STATE: Switching to cool at " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + "\n")
                            log.close()
                        hvacState = self.cool()

                elif hvacState == -1: #cooling
                    if indoorTemp < targetTemp - active_hysteresis:
                        if DEBUG == 1:
                            log = open("logs/debug_" + datetime.datetime.now().strftime('%Y%m%d') + ".log", "a")
                            log.write("STATE: Switching to fan_to_idle at " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + "\n")
                            log.close()
			emails = 0
			length = 0
                        self.fan_to_idle()
                        time.sleep(30)
                        if DEBUG == 1:
                            log = open("logs/debug_" + datetime.datetime.now().strftime('%Y%m%d') + ".log", "a")
                            log.write("STATE: Switching to idle at " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + "\n")
                            log.close()
                        hvacState = self.idle()

                elif hvacState == 1: # it's hot out, why is the heater on?
                        if DEBUG == 1:
                            log = open("logs/debug_" + datetime.datetime.now().strftime('%Y%m%d') + ".log", "a")
                            log.write("STATE: Switching to fan_to_idle at " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + "\n")
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
                log.write("Report at " + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + ":\n")
                log.write("hvacState = " + str(hvacState)+ "\n")
                log.write("indoorTemp = " + str(indoorTemp)+ "\n")
                log.write("targetTemp = " + str(targetTemp)+ "\n")
                log.write("heatStatus = " + str(heatStatus) + "\n")
                log.write("coolStatus = " + str(coolStatus)+ "\n")
                log.write("fanStatus = " + str(fanStatus)+ "\n")
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
