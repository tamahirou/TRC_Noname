import time
import struct
import LoRa
import setting


#global value
valuedata = []

#-----------------------------------------------------------
# 現在のパラメータ設定状態を一覧出力

 
def ConfigAllDisp(uart):
    aux = LoRa.auxpin()
    
    LoRa.LoRaMode3(aux)
    time.sleep(0.2)
    
    command = [0xC1, 0x00, 0x08]
    response = bytes()

    print("# Command Request")
    print(bytes(command))
    
    while uart.any() != 0 :
        response = uart.read(uart.any())

    while aux.value() == 0:
        time.sleep(0.001)
    for value in command:
        data = struct.pack("B", value)
        uart.write(bytes(data))
        time.sleep(0.002)

    time.sleep(1)
    while aux.value() == 0:
        time.sleep(0.001)
    while uart.any() != 0 :
        response = uart.read(uart.any())




    print("# Command Response")
    print(response)

    print("\n現在の設定一覧")


#    _, _, _, ADDH, ADDL, REG0, REG1, REG2, REG3, CRYPT_H, CRYPT_L = response

    ADDH = response[3]
    ADDL = response[4]
    REG0 = response[5]
    REG1 = response[6]
    REG2 = response[7]
    REG3 = response[8]
    CRYPT_H = response[9]
    CRYPT_L = response[10]
    ADDH = ADDH<< 8
    ADDL = ADDL
    address = ADDH + ADDL
    print("Address             : {0}".format(address))

    UART = REG0 & 0b1110_0000
    UART = UART >> 5
    uart_setting = {
        0b000: "1200bps",
        0b001: "2400bps",
        0b010: "4800bps",
        0b011: "9600bps",
        0b100: "19200bps",
        0b101: "38400bps",
        0b110: "57600bps",
        0b111: "115200bps",
    }
    print("UART                : {0}".format(uart_setting[UART]))

    AIR_DATA_RATE = REG0 & 0b0001_1111
    BW = REG0 & 0b0000_0011
    air_data_rate_setting = {
        0b00000: "15,625bps, SF: 5, BW:125kHz",
        0b00100: " 9,375bps, SF: 6, BW:125kHz",
        0b01000: " 5,469bps, SF: 7, BW:125kHz",
        0b01100: " 3,125bps, SF: 8, BW:125kHz",
        0b10000: " 1,758bps, SF: 9, BW:125kHz",
        0b00001: "31,250bps, SF: 5, BW:250kHz",
        0b00101: "18,750bps, SF: 6, BW:250kHz",
        0b01001: "10,938bps, SF: 7, BW:250kHz",
        0b01101: " 6,250bps, SF: 8, BW:250kHz",
        0b10001: " 3,516bps, SF: 9, BW:250kHz",
        0b10101: " 1,953bps, SF:10, BW:250kHz",
        0b00010: "62,500bps, SF: 5, BW:500kHz",
        0b00110: "37,500bps, SF: 6, BW:500kHz",
        0b01010: "21,875bps, SF: 7, BW:500kHz",
        0b01110: "12,500bps, SF: 8, BW:500kHz",
        0b10010: " 7,031bps, SF: 9, BW:500kHz",
        0b10110: " 3,906bps, SF:10, BW:500kHz",
        0b11010: " 2,148bps, SF:11, BW:500kHz",
    }
    print("Air Data Rate       : {0}".format(air_data_rate_setting[AIR_DATA_RATE].strip()))


    SUB_PACKET_LEN = REG1 & 0b1100_0000
    SUB_PACKET_LEN = SUB_PACKET_LEN >> 6
    sub_packet_setting = {
        0b00: "200bytes",
        0b01: "128bytes",
        0b10: "64bytes",
        0b11: "32bytes",
    }
    print("Sub Packet Size     : {0}".format(sub_packet_setting[SUB_PACKET_LEN]))

    RSSI_AMBIENT = REG1 & 0b0010_0000
    RSSI_AMBIENT = RSSI_AMBIENT >> 5
    rssi_ambient_setting = {
        0b0: "Disable",
        0b1: "Enable",
    }
    print("RSSI Ambient noise  : {0}".format(rssi_ambient_setting[RSSI_AMBIENT]))

    # TRANSMIT_PAUSE = REG1 & 0b0001_0000
    # TRANSMIT_PAUSE = TRANSMIT_PAUSE >> 4
    # transmit_pause_setting = {
    #     0b0: 'Enable',
    #     0b1: 'Disable',
    # }
    # print(
    #     f'Transmission pause  : {transmit_pause_setting[TRANSMIT_PAUSE]}'
    # )

    TRANSMIT_POWER = REG1 & 0b0000_0011
    transmit_power_setting = {
        0b00: "Unavailable",
        0b01: "13dBm",
        0b10: "7dBm",
        0b11: "0dBm",
    }
    print("Transmitting Power  : {transmit_power_setting[TRANSMIT_POWER]}")

    CH = REG2

    if BW == 0b00:
        frequency = 920.6 + CH * 0.2
    elif BW == 0b01:
        frequency = 920.7 + CH * 0.2
    elif BW == 0b10:
        frequency = 920.8 + CH * 0.2

    print("CH                  : {0}".format(CH))
    print("Actual frequency    : {0:.1f}MHz".format(frequency))


    RSSI_BYTE = REG3 & 0b1000_0000
    RSSI_BYTE = RSSI_BYTE >> 7
    rssi_byte_setting = {
        0b0: "Disable",
        0b1: "Enable",
    }
    print("RSSI Byte           : {0}".format(rssi_byte_setting[RSSI_BYTE]))

    TRANSMIT_METHOD = REG3 & 0b0100_0000
    TRANSMIT_METHOD = TRANSMIT_METHOD >> 6
    transmit_method_setting = {
        0b0: "Transparent transmission mode",
        0b1: "Fixed transmission mode",
    }
    print("Transmission Method : {0}".format(transmit_method_setting[TRANSMIT_METHOD]))

    # LBT = REG3 & 0b0001_0000
    # LBT = LBT >> 4
    # lbt_setting = {
    #     0b0: 'Enable',
    #     0b1: 'Disable',
    # }
    # print(f'LBT         : {lbt_setting[LBT]}')

    WOR_CYCLE = REG3 & 0b00000111
    wor_cycle_setting = {
        0b000: "500ms",
        0b001: "1000ms",
        0b010: "1500ms",
        0b011: "2000ms",
        0b100: "2500ms",
        0b101: "3000ms",
        0b110: "3500ms",
        0b111: "4000ms",
    }
    print("WOR Cycle           : {0}\n".format(wor_cycle_setting[WOR_CYCLE]))

    LoRa.LoRaMode0(aux)
    return


#-----------------------------------------------------------
# setting.py コンフィグ設定ファイルからコンフィグパラメータを設定する

def ConfigApply(uart):
    aux = LoRa.auxpin()
 
    command = [0xC0, 0x00, 0x08]


#設定値の読み取り
    own_address = int(setting.own_address)
    baud_rate = int(setting.baud_rate)
    bw = int(setting.bw)
    sf = int(setting.sf)
    subpacket_size = int(setting.subpacket_size)
    rssi_ambient_noise_flag = int(setting.rssi_ambient_noise_flag)
    transmitting_power = int(setting.transmitting_power) 
    own_channel = int(setting.own_channel)
    rssi_byte_flag = int(setting.rssi_byte_flag)
    transmission_method_type = int(setting.transmission_method_type)
    wor_cycle = int(setting.wor_cycle)
    encryption_key = int(setting.encryption_key)


    # Address 00H, 01H
    # own_addressr@@----.@p
#    own_address = int(own_address)
    ADDH = own_address >> 8
    ADDL = own_address & 0b1111_1111
    command.append(ADDH)
    command.append(ADDL)

    # Address 02H
    REG0 = 0

    # baud_rate
#    baud_rate = int(baud_rate)

    baud_rate_bit = {
        1200: 0b000,
        2400: 0b001,
        4800: 0b010,
        9600: 0b011,
        19200: 0b100,
        38400: 0b101,
        57600: 0b110,
        115200: 0b111,
    }

    if baud_rate in baud_rate_bit:
        baud_rate = baud_rate_bit[baud_rate]
    else:
        baud_rate = baud_rate_bit[9600]

    baud_rate = baud_rate << 5
    REG0 = REG0 | baud_rate

    # air_data_rate
#    bw = int(bw)
#    sf = int(sf)
    air_data_rate = (bw, sf)

    air_data_rate_bit = {
        (125, 5): 0b00000,
        (125, 6): 0b00100,
        (125, 7): 0b01000,
        (125, 8): 0b01100,
        (125, 9): 0b10000,
        (250, 5): 0b00001,
        (250, 6): 0b00101,
        (250, 7): 0b01001,
        (250, 8): 0b01101,
        (250, 9): 0b10001,
        (250, 10): 0b10101,
        (500, 5): 0b00010,
        (500, 6): 0b00110,
        (500, 7): 0b01010,
        (500, 8): 0b01110,
        (500, 9): 0b10010,
        (500, 10): 0b10110,
        (500, 11): 0b11010,
    }

    if air_data_rate in air_data_rate_bit:
        air_data_rate = air_data_rate_bit[air_data_rate]
    else:
        air_data_rate = air_data_rate_bit[(125, 7)]

    REG0 = REG0 | air_data_rate
    command.append(REG0)

    # Address 03H
    REG1 = 0

    # subpacket_size
#    subpacket_size = int(subpacket_size)

    subpacket_size_bit = {200: 0b00, 128: 0b01, 64: 0b10, 32: 0b11}

    if subpacket_size in subpacket_size_bit:
        subpacket_size = subpacket_size_bit[subpacket_size]
    else:
        subpacket_size = subpacket_size_bit[200]

    subpacket_size = subpacket_size << 6
    REG1 = REG1 | subpacket_size

    # rssi_ambient_noise_flag
#    rssi_ambient_noise_flag = int(rssi_ambient_noise_flag)

    if rssi_ambient_noise_flag == 0:
        rssi_ambient_noise_flag = 0b0
    elif rssi_ambient_noise_flag == 1:
        rssi_ambient_noise_flag = 0b1
    else:
        rssi_ambient_noise_flag = 0b0

    rssi_ambient_noise_flag = rssi_ambient_noise_flag << 5
    REG1 = REG1 | rssi_ambient_noise_flag

    # # transmission_pause_flag
    # transmission_pause_flag = int(transmission_pause_flag)

    # if transmission_pause_flag == 0:
    #     transmission_pause_flag = 0b1
    # elif transmission_pause_flag == 1:
    #     transmission_pause_flag = 0b0
    # else:
    #     transmission_pause_flag = 0b0

    # transmission_pause_flag = transmission_pause_flag << 4
    # REG1 = REG1 | transmission_pause_flag

    # transmitting_power
#    transmitting_power = int(transmitting_power)

    transmitting_power_bit = {13: 0b01, 7: 0b10, 0: 0b11}

    if transmitting_power in transmitting_power_bit:
        transmitting_power = transmitting_power_bit[transmitting_power]
    else:
        transmitting_power = transmitting_power_bit[13]

    REG1 = REG1 | transmitting_power
    command.append(REG1)

    # Address 04H
    # own_channel
    REG2 = 0

#    own_channel = int(own_channel)

    if bw == 125:
        if 0 < own_channel < 37:
            pass
        else:
            own_channel = 0
    elif bw == 250:
        if 0 < own_channel < 36:
            pass
        else:
            own_channel = 0
    elif bw == 500:
        if 0 < own_channel < 30:
            pass
        else:
            own_channel = 0
    else:
        own_channel = 0

    REG2 = REG2 | own_channel
    command.append(REG2)

    # Address 05H
    REG3 = 0

    # rssi_byte_flag
#    rssi_byte_flag = int(rssi_byte_flag)

    if rssi_byte_flag == 0:
        rssi_byte_flag = 0b0
    elif rssi_byte_flag == 1:
        rssi_byte_flag = 0b1
    else:
        rssi_byte_flag = 0b1

    rssi_byte_flag = rssi_byte_flag << 7
    REG3 = REG3 | rssi_byte_flag

    # transmission_method_type
#    transmission_method_type = int(transmission_method_type)

    if transmission_method_type == 1:
        transmission_method_type = 0b0        #transparet
    elif transmission_method_type == 2:
        transmission_method_type = 0b1        #fixed
    else:
        transmission_method_type = 0b1

    transmission_method_type = transmission_method_type << 6
    REG3 = REG3 | transmission_method_type

    # # lbt_flag
    # lbt_flag = int(lbt_flag)

    # if lbt_flag == 0:
    #     lbt_flag = 0b1
    # elif lbt_flag == 1:
    #     lbt_flag = 0b0
    # else:
    #     lbt_flag = 0b0

    # lbt_flag = lbt_flag << 4
    # REG3 = REG3 | lbt_flag

    # wor_cycle
#    wor_cycle = int(wor_cycle)

    wor_cycle_bit = {
        500: 0b000,
        1000: 0b001,
        1500: 0b010,
        2000: 0b011,
        2500: 0b100,
        3000: 0b101,
        3500: 0b110,
        4000: 0b111,
    }

    if wor_cycle in wor_cycle_bit:
        wor_cycle = wor_cycle_bit[wor_cycle]
    else:
        wor_cycle = wor_cycle_bit[2000]

    REG3 = REG3 | wor_cycle
    command.append(REG3)

    # Address 06H, 07H
    # encryption_key
    encryption_key = int(encryption_key)
    CRYPT_H = encryption_key >> 8
    CRYPT_L = encryption_key & 0b1111_1111
    command.append(CRYPT_H)
    command.append(CRYPT_L)

    print("# Command Request")
#    command_hex = list(map(lambda n: "0x" + format(n, "02x"), command))
#    print(command_hex)
    print("{0}".format(bytes(command)))

    LoRa.LoRaMode3(aux)

    time.sleep(0.2)
    while uart.any() != 0 :
        response = uart.read(uart.any())

    while aux.value() == 0:
        time.sleep(0.001)
    for value in command:
        data = struct.pack("B", value)
        uart.write(bytes(data))
        valuedata.append(data)
#        print(data)
        time.sleep(0.002)

    time.sleep(1)
    response = bytes()

    flg = 0

    while aux.value() == 0:
        time.sleep(0.001)
    while uart.any() != 0 :
        response = uart.read(uart.any())



    print("# Command Response")
    print(response)

    
    LoRa.LoRaMode0(aux)
    return
