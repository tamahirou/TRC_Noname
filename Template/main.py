from machine import Pin
from time import sleep 
from machine import UART
import struct
import time

import LoRa
import send
import receive
import ConfigTreat



def main():
    uart = LoRa.LoRaBegin()

    ConfigTreat.ConfigApply(uart)
    time.sleep(0.5)
      #onfigTreat.ConfigAllDisp(uart)
    
    #\LoRa.LoRaReInit(uart,aux)
 

    while True:

        send.send(uart)

        receive.recv(uart)

        time.sleep(1)
        

        
        


if __name__ == "__main__":
    main()