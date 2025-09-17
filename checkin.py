import json
import log
from checkin_tool import Checkin
from datetime import datetime, timedelta

def parse_taiwan_year_range(project_time):
    """Parse Taiwan year format (e.g., '1140922 ~ 1150327') to date range"""
    if not project_time or "~" not in project_time:
        return None, None

    taiwan_start, taiwan_end = project_time.split("~")
    taiwan_start = taiwan_start.strip()
    taiwan_end = taiwan_end.strip()

    # Convert Taiwan year to AD (add 1911)
    if len(taiwan_start) >= 7 and len(taiwan_end) >= 7:  # Format: 1140922
        # Parse start date
        tw_year = int(taiwan_start[:3]) + 1911
        tw_month = int(taiwan_start[3:5])
        tw_day = int(taiwan_start[5:7])
        start_date = datetime(tw_year, tw_month, tw_day).date()

        # Parse end date
        tw_year = int(taiwan_end[:3]) + 1911
        tw_month = int(taiwan_end[3:5])
        tw_day = int(taiwan_end[5:7])
        end_date = datetime(tw_year, tw_month, tw_day).date()

        return start_date, end_date

    return None, None

CURRENT_DATETIME = datetime.now()
SIGN_THRESHOLD = timedelta(minutes=10)


log.CheckinLog("Daily checking started")

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# Check if current date is within any project's date ranges
current_date_in_range = False

for data in config:
    project = config[data]

    # Skip projects without date range configuration
    if "date_ranges" not in project:
        continue

    # Check each date range
    for date_range in project["date_ranges"]:
        # Generate timestamps for today if within this date range
        start_date = datetime.strptime(date_range["start_date"], '%Y-%m-%d').date()
        end_date = datetime.strptime(date_range["end_date"], '%Y-%m-%d').date()

        # Also check Taiwan year format in projectTime if available
        if "projectTime" in project:
            taiwan_start_date, taiwan_end_date = parse_taiwan_year_range(project["projectTime"])
            if taiwan_start_date and taiwan_end_date:
                # Use Taiwan dates if they're more restrictive
                start_date = max(start_date, taiwan_start_date)
                end_date = min(end_date, taiwan_end_date)

        if start_date <= CURRENT_DATETIME.date() <= end_date:
            current_date_in_range = True
            # Generate timestamps from project-level hours
            log.CheckinLog("Currently in project time range. Checking time...")
            start_time = datetime.strptime(f"{CURRENT_DATETIME.date()} {project['start_hour']}", '%Y-%m-%d %H:%M:%S')
            end_time = datetime.strptime(f"{CURRENT_DATETIME.date()} {project['end_hour']}", '%Y-%m-%d %H:%M:%S')

            timestamps = [start_time, end_time]

            for timestamp in timestamps:
                # Check if this timestamp was already processed today
                timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                if timestamp_str not in project["checked_in_date"]:
                    
                    if abs(CURRENT_DATETIME - timestamp) < SIGN_THRESHOLD:
                    # if True:
                        #checkin/out
                        log.CheckinLog("starting checking in ....")
                        if Checkin(project["projectName"],project["projectTime"],project["checkinHour"],project["message"]):
                            # Add processed timestamp to prevent duplicate processing
                            config[data]["checked_in_date"].append(timestamp_str)
                            log.CheckinLog("Checkin/out Success. ")
                        else:
                            log.CheckinLog("Checkin/out Failed. " )
                    else:
                        log.CheckinLog("Not in designated project checkin/out time.")


# Check if current date is not in any project range
if not current_date_in_range:
    log.CheckinLog("Not in project range. You're free today!")

# update config
with open("config.json", "w", encoding="utf-8") as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

log.CheckinLog( f"Daily checking ended")