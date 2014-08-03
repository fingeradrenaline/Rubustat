import subprocess
import glob
import time
import os

def getIndoorTemp():
    total = 0
    subprocess.Popen('modprobe w1-gpio', shell=True)
    subprocess.Popen('modprobe w1-therm', shell=True)
    count = subprocess.Popen('cat /sys/bus/w1/devices/w1_bus_master1/w1_master_slave_count', shell=True, stdout=subprocess.PIPE)
    number_of_sensors = int(count.stdout.read())
    base_dir = '/sys/bus/w1/devices/'
    
    for i in range (0,number_of_sensors):
        device_folder = glob.glob(base_dir + '28*')[i]
        device_file = device_folder + '/w1_slave'
        f = open(device_file, 'r')
        lines = f.readlines()
        f.close    
        while lines[0].strip()[-3:] != 'YES':
            time.sleep(0.2)
            f2 = open(device_file, 'r')
            lines = f.readlines()
            f2.close()
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_string = lines[1][equals_pos+2:]
            temp_c = float(temp_string) / 1000.0
            temp_f_i = temp_c * 9.0 / 5.0 + 32.0
        total += temp_f_i
    if number_of_sensors > 1:
        average = total / number_of_sensors
        return average
    else:
        return temp_f_i
    
    return read_temp()