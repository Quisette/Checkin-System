import datetime
def CheckinLog(msg):
    path = 'D://Checkin-System/log.txt' # todo
    with open(path, 'a', encoding='utf-8') as f:
        str = f"[{datetime.datetime.now().date()}] {msg} \n"
        print(str)
        f.write(str)