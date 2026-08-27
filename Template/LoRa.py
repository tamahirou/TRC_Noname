from machine import Pin,SPI
from machine import UART
import time
import struct
import ConfigTreat


AUX_PIN = 13
M0_PIN = 14
M1_PIN = 15

def LoRaMode0(aux):
    while aux.value() == 0:
        time.sleep(0.001)
    PIN_M0 = Pin(M0_PIN,Pin.OUT)
    PIN_M1 = Pin(M1_PIN,Pin.OUT)
    PIN_M0.value(0)
    PIN_M1.value(0)
    return

def LoRaMode1(aux):
    while aux.value() == 0:
        time.sleep(0.001)
    PIN_M0 = Pin(M0_PIN,Pin.OUT)
    PIN_M1 = Pin(M1_PIN,Pin.OUT)
    PIN_M0.value(1)
    PIN_M1.value(0)
    return

def LoRaMode2(aux):
    while aux.value() == 0:
        time.sleep(0.001)    
    PIN_M0 = Pin(M0_PIN,Pin.OUT)
    PIN_M1 = Pin(M1_PIN,Pin.OUT)
    PIN_M0.value(0)
    PIN_M1.value(1)
    return

def LoRaMode3(aux):
    while aux.value() == 0:
        time.sleep(0.001)
    PIN_M0 = Pin(M0_PIN,Pin.OUT)
    PIN_M1 = Pin(M1_PIN,Pin.OUT)
    PIN_M0.value(1)
    PIN_M1.value(1)
    return



def auxpin():
    return Pin(AUX_PIN,Pin.IN)


def LoRaBegin():
    LoRaMode3(auxpin())
    
    uart = UART(0,9600)
    uart.init(9600,bits=8,parity=None,stop=1)

    return uart


def LoRaReInit(uart,aux):
    LoRaMode3(aux)
    while aux.value() == 0:
        time.sleep(1)
    for data in ConfigTreat.valuedata:
        uart.write(bytes( data))
        time.sleep(0.002)
        
    while aux.value() == 0:
        time.sleep(1)
    time.sleep(0.02)
    buf0 = bytes()    
    flag = 0
    while True:
        if uart.any() >0:
            buf0 = uart.read(uart.any())
            print(buf0)
            flag = 1
        else:
            if flag != 0:
                break
    print("LoRa Initialized")    

    LoRaMode0(aux)

    return

