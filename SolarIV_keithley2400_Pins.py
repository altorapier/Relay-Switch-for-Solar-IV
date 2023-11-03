## This program performs Solar IV measurements using a keithley 2400 SMU,
## and with a custom arduino circuit for device selection and shutter toggling

#package imports
from IPython import get_ipython
get_ipython().magic('reset -sf')
import os
from promptlib import Files
import pyvisa
import numpy as np
import time as t
import datetime
import shutil
import pandas as pd
import serial
import struct

#Micro usb connection for arduino circuit, use serial.tools.list_ports.comports() to search for the port 
arduino = serial.Serial(port='COM9', baudrate=9600, timeout=1)
 
# Connect and setup Keithley through USB-GPIB
rm = pyvisa.ResourceManager()
smu = rm.open_resource('GPIB0::24::INSTR',write_termination = '\n',read_termination='\n')
smu.timeout = 500000

#function to send command s to arduino to select device via relay or to toggle  
def ardOssilaSw(pin_num,pinstate):
  validpins = [1,2,3,4,5,6,7,8]
  validstates = [0,1]
  if pin_num in validpins:
      if pinstate in validstates:
          arduino.write(struct.pack('>BB',int(pin_num-1),int(pinstate)))
          t.sleep(1)
          data = arduino.readline()
      else:
          print('Not a valid pin state, setting to 0 by default')
          arduino.write(struct.pack('>BB',int(pin_num-1),int(0)))
          t.sleep(1)
          data = arduino.readline()
  else:
      print('Not a valid pin, setting to pin 1 by default')
      if pinstate in validstates:
          arduino.write(struct.pack('>BB',int(0),int(pinstate)))
          t.sleep(1)
          data = arduino.readline()
      else:
          print('Not a valid pin state, setting to 0 by default')
          arduino.write(struct.pack('>BB',int(0),int(0)))
          t.sleep(1)
          data = arduino.readline()

#function to send command s to arduino to select device via relay or to toggle  
def ardLightSw(lightstate):
    validstates = [0,1]
    if lightstate in validstates:
        arduino.write(struct.pack('>BB',int(19),int(lightstate)))
        t.sleep(1)
        arduino.readline()
    else:
        print('Not a valid pin state, setting to 0 by default')
        arduino.write(struct.pack('>BB',int(19),int(0)))
        t.sleep(1)
        arduino.readline()


# Sweep parameters
Vmax = 1.2
Vmin = -0.2
Vdiff = 20e-3
dirr = -1 #1: Forward, -1:Reverse
Suns = 100.7e-3 # mW/cm^2
Area = 0.16**2 #cm^2
if dirr == 1:
    voltages = (np.arange(Vmin, Vmax+Vdiff/2,Vdiff ))
elif dirr == -1:
    voltages = np.flip(np.arange(Vmin, Vmax+Vdiff/2,Vdiff ))
delayTime = 0.1 # seconds

typeN = "MAPI"
batch = 1
sample = 12
Run = 1
pins = [1,2,3,4,5,6,7,8]

darkreadings = np.zeros([len(voltages),len(pins)])
lightreadings = np.zeros([len(voltages),len(pins)])
Wmpp = np.zeros(len(pins))
Voc = np.zeros(len(pins))
Isc = np.zeros(len(pins))
FF = np.zeros(len(pins)) 
PCE = np.zeros(len(pins))
avePCE = 0

files = Files()
#request location to save data
outputPath = files.dir()
now = datetime.datetime.now()
folderName = now.strftime("%Y-%m-%d-%H.%M")
outputFolder = "".join([outputPath, folderName])
specs = typeN+"_B"+str(batch)+"S"+str(sample)

# House keeping for saving files
if (os.path.exists(outputFolder) == False):
  os.makedirs(outputFolder)
else:
  shutil.rmtree(outputFolder)
  os.makedirs(outputFolder)

#IV Sweep settings
print(smu.query('*IDN?'))
smu.write("*RST")
smu.write(":SOUR:FUNC VOLT")
smu.write(":SENS:FUNC 'CURR:DC'")
smu.write(":SENS:CURR:PROT 0.01")
smu.write(":SENS:CURR:RANG 0.01")
if dirr == 1:
    smu.write(":SOUR:VOLT:START " + "{:.2e}".format(Vmin))
    smu.write(":SOUR:VOLT:STOP " + "{:.2e}".format(Vmax))
else:
    smu.write(":SOUR:VOLT:START " + "{:.2e}".format(Vmax))
    smu.write(":SOUR:VOLT:STOP " + "{:.2e}".format(Vmin))
smu.write(":SOUR:SWE:POIN " + "{:.2e}".format(voltages.size))
smu.write(":SOUR:VOLT:MODE SWE")
smu.write(":SOUR:SWE:RANG AUTO")
smu.write(":SOUR:SWE:SPAC LIN")
smu.write(":TRIG:COUN "+ "{:.2e}".format(voltages.size))
smu.write(":SOUR:DEL "+ "{:.2e}".format(delayTime))

#Setup for plotting and measureing
readings = np.zeros(voltages.size)
err_readings = np.zeros(voltages.size)

outputFilename = "".join([outputFolder, "\\Solar IV"+specs+"R"+str(Run)+".xlsx"])
#make sure light is off
ardLightSw(0) 

for pin in pins:  
    
    ardOssilaSw(pin,1)#select pin
    smu.write(":OUTP ON")#connect smu to pin 
    darkreading = np.reshape(smu.query_ascii_values('READ?',container=np.array),[len(voltages),5])#measure dark current
    ardLightSw(1)#turn on light
    lightreading = np.reshape(smu.query_ascii_values('READ?',container=np.array),[len(voltages),5])#measure light current
    ardLightSw(0)#turn light off
    ardOssilaSw(pin,0)#deselect pin
    smu.write("OUTP OFF")#disconnect smu from pin 
    
    #processing data
    iPin = pins.index(pin)
    readings = lightreadings[:,iPin]
    darkreadings[:,iPin] = darkreading[:,1]
    lightreadings[:,iPin] = lightreading[:,1]
    statreading = lightreadings[:,iPin]
    Wmpp[iPin] = np.max(-statreading*voltages) 
    if dirr == 1:
        Voc[iPin] = np.interp(0,statreading,voltages)
    elif dirr == -1:
        Voc[iPin] = np.interp(0,np.flip(statreading),np.flip(voltages))
    Isc[iPin] = np.interp(0,voltages,(statreading))    
    FF[iPin] = Wmpp[iPin]/(-Isc[iPin]*Voc[iPin])*100
    PCE[iPin] = 100*Wmpp[iPin]/(Suns*Area)
    print("Pin: ",pin)
    print("Fill Factor: ",FF[iPin])
    print("Open Circuit Voltage: ",Voc[iPin])
    print("Short Circuit Current: ",Isc[iPin])
    print("Power Conversion: ",PCE[iPin])


#Setup and save data
specsheader = []
specsheader.append('Vstart')
specsheader.append('Vend')
specsheader.append('Vdiff')
specsheader.append('Delay')
specInd = ['Vstart','Ved','Vdiff','Delay']
SpecsData = np.asarray([voltages[0],voltages[len(voltages)-1],Vdiff,delayTime])
Mspecs = pd.DataFrame(SpecsData,index=specsheader) 

statheader = []
statheader.append('Pins')
statheader.append('Voc')
statheader.append('Isc')
statheader.append('Wmpp')
statheader.append('FF')
statheader.append('PCE')
StatsData = [pins,Voc,Isc,Wmpp,FF,PCE]
Stats = pd.DataFrame(StatsData,index=statheader)  

Dheader = []
Dheader.append('Voltage')
for pin in pins: 
    Dheader.append('Pin '+str(pin))
DcData = np.append([voltages],darkreadings.T,axis=0)    
LcData = np.append([voltages],lightreadings.T,axis=0)   
Dcurrents= pd.DataFrame(DcData.T) 
Lcurrents= pd.DataFrame(LcData.T) 
  
# Write output to file
writer = pd.ExcelWriter(outputFilename)
Mspecs.to_excel(writer,sheet_name='Specs',header=False,index=True)
Dcurrents.to_excel(writer, sheet_name="Dark Current", index=False,header=Dheader)
Lcurrents.to_excel(writer, sheet_name="Light Current", index=False,header=Dheader)
Stats.to_excel(writer, sheet_name="Stats",header=False,index=True)
writer.save()

arduino.close()
smu.write('beeper.beep(1, 1500)')