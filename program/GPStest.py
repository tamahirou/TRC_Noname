from machine import UART, Pin
import time

# ===== ピン設定 =====
# UART1を使用（GP4=TX, GP5=RX）
GPS_TX_PIN = 12  # Pico GP4 → GPS RX
GPS_RX_PIN = 13  # Pico GP5 ← GPS TX
BAUDRATE = 115200
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        

# UART初期化
gps = UART(0, baudrate=BAUDRATE, tx=Pin(GPS_TX_PIN), rx=Pin(GPS_RX_PIN))

# ===== 関数定義 =====
def parse_gga(sentence):
    """
    GGAセンテンスをパースして緯度・経度を取得
    例: $GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47
    
    戻り値: 座標データの辞書、または None
    """
    parts = sentence.split(',')
    
    # GGAセンテンスかチェック
    if len(parts) < 10 or parts[0] not in ['$GPGGA', '$GNGGA', '$GLGGA', '$GAGGA']:
        return None
    
    # 時刻
    time_utc = parts[1] if parts[1] else None
    
    # 緯度の取得
    if parts[2] and parts[3]:
        try:
            lat_deg = float(parts[2][:2])
            lat_min = float(parts[2][2:])
            latitude = lat_deg + (lat_min / 60.0)
            if parts[3] == 'S':
                latitude = -latitude
        except:
            return None
    else:
        return None
    
    # 経度の取得
    if parts[4] and parts[5]:
        try:
            lon_deg = float(parts[4][:3])
            lon_min = float(parts[4][3:])
            longitude = lon_deg + (lon_min / 60.0)
            if parts[5] == 'W':
                longitude = -longitude
        except:
            return None
    else:
        return None
    
    # GPS品質（0=無効, 1=GPS, 2=DGPS）
    quality = int(parts[6]) if parts[6] else 0
    
    # 衛星数
    satellites = int(parts[7]) if parts[7] else 0
    
    # 高度
    try:
        altitude = float(parts[9]) if parts[9] else 0.0
    except:
        altitude = 0.0
    
    return {
        'time': time_utc,
        'latitude': latitude,
        'longitude': longitude,
        'quality': quality,
        'satellites': satellites,
        'altitude': altitude
    }

def create_google_maps_link(latitude, longitude):
    """Google Mapsリンクを生成"""
    return f"https://www.google.com/maps?q={latitude},{longitude}"

# ===== メインプログラム =====
print("=" * 50)
print("GPS座標取得プログラム開始")
print("=" * 50)
print(f"UART設定: TX=GP{GPS_TX_PIN}, RX=GP{GPS_RX_PIN}, Baud={BAUDRATE}")
print("GPSデータ受信中...")
print("※屋外または窓際で使用してください")
print("※初回起動時は数分かかる場合があります")
print("=" * 50)
print()

last_valid_data = None
line_count = 0

while True:
    if gps.any():
        data = gps.readline()
        try:
            sentence = data.decode('utf-8').strip()
            line_count += 1
            
            # 10行ごとに受信中メッセージを表示
            if line_count % 10 == 0:
                print(".", end="")
            
            # GGAセンテンスのみ処理
            if 'GGA' in sentence and sentence.startswith('$G'):
                gps_data = parse_gga(sentence)
                
                if gps_data and gps_data['quality'] > 0:
                    # 有効なデータの場合のみ表示
                    last_valid_data = gps_data
                    
                    print("\n")
                    print("=" * 50)
                    print("【GPS位置情報取得成功】")
                    print("=" * 50)
                    print(f"時刻(UTC): {gps_data['time']}")
                    print(f"緯度:      {gps_data['latitude']:.6f}°")
                    print(f"経度:      {gps_data['longitude']:.6f}°")
                    print(f"高度:      {gps_data['altitude']:.1f} m")
                    print(f"GPS品質:   {gps_data['quality']} (1=GPS, 2=DGPS)")
                    print(f"衛星数:    {gps_data['satellites']} 個")
                    print("-" * 50)
                    print(f"Google Maps:")
                    print(create_google_maps_link(gps_data['latitude'], gps_data['longitude']))
                    print("=" * 50)
                    print()
                    
                elif gps_data:
                    # データは取得できたが品質が0（GPS未確定）
                    if line_count % 20 == 0:
                        print(f"\n衛星探索中... (衛星数: {gps_data['satellites']})")
                        
        except Exception as e:
            # デコードエラーは無視
            pass
    
    time.sleep(0.1)