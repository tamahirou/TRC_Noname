own_address = '0'
baud_rate = '9600'
bw = '125'
sf = '9'
subpacket_size = '32'
rssi_ambient_noise_flag = '0'
transmitting_power = '13'
own_channel = '0'
rssi_byte_flag = '1'                # RSSIバイト有効
transmission_method_type = '1'      # 1 is transparent, 2 is Fixed
wor_cycle = '3000'
encryption_key = '0'
payload_length = 32           # 送信ペーロード長
ascii_text = True             # 送信データに"ascii"を設定
fixed_mode = False            # 変更するときはsetting.pyのtransmission_method_typeも同時に
                              # False = transparet mode : method_type 1
                              # True  = fixed mode : method type 2
target_address = 0xffff       # BroadCast
target_channel = 0x00
Argrssi = True                #RSSIバイト有効

# ===== UART設定(TX=GP4, RX=GP5) =====
UART_ID = 1        # GP4/GP5はUART1のデフォルトピン
TX_PIN = 4
RX_PIN = 5
UART_BAUDRATE = 9600