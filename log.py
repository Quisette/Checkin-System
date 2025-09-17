import datetime
def CheckinLog(msg):
    path = 'D://repos/Checkin-System/log.txt'
    with open(path, 'a') as f:
        str = f"[{datetime.datetime.now().date()}] {msg} \n"
        print(str)
        f.write(str)