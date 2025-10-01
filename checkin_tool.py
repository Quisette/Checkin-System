import os
import requests
from datetime import datetime
from bs4 import BeautifulSoup as BS
import parsers
import log
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()

'''
1. GET https://portal.ncu.edu.tw/endpoint?openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0&openid.mode=checkid_setup&openid.return_to=https%3A%2F%2Fcis.ncu.edu.tw%2FHumanSys%2Flogin&openid.realm=https%3A%2F%2Fcis.ncu.edu.tw&openid.ns.ax=http%3A%2F%2Fopenid.net%2Fsrv%2Fax%2F1.0&openid.ax.mode=fetch_request&openid.ax.type.user_roles=http%3A%2F%2Faxschema.org%2Fuser%2Froles&openid.ax.type.contact_email=http%3A%2F%2Faxschema.org%2Fcontact%2Femail&openid.ax.type.contact_name=http%3A%2F%2Faxschema.org%2Fcontact%2Fname&openid.ax.type.contact_ename=http%3A%2F%2Faxschema.org%2Fcontact%2Fename&openid.ax.type.student_id=http%3A%2F%2Faxschema.org%2Fstudent%2Fid&openid.ax.type.alunmi_leaveSem=http%3A%2F%2Faxschema.org%2Falunmi%2FleaveSem&openid.ax.required=user_roles&openid.ax.if_available=contact_email%2Ccontact_name%2Ccontact_ename%2Cstudent_id%2Calunmi_leaveSem&openid.identity=https%3A%2F%2Fportal.ncu.edu.tw%2Fuser%2F&openid.claimed_id=https%3A%2F%2Fportal.ncu.edu.tw%2Fuser%2F

2. POST https://portal.ncu.edu.tw/login

3. POST https://portal.ncu.edu.tw/leaving

4. GET https://cis.ncu.edu.tw/HumanSys/home

5. GET https://cis.ncu.edu.tw/HumanSys/student/stdSignIn

6. GET https://cis.ncu.edu.tw/HumanSys/student/stdSignIn/create?ParttimeUsuallyId=210885

7. POST https://cis.ncu.edu.tw/HumanSys/student/stdSignIn_detail
json "isOK"

'''
# ENDPOINT_URL = "https://portal.ncu.edu.tw/endpoint?openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0&openid.mode=checkid_setup&openid.return_to=https%3A%2F%2Fcis.ncu.edu.tw%2FHumanSys%2Flogin&openid.realm=https%3A%2F%2Fcis.ncu.edu.tw&openid.ns.ax=http%3A%2F%2Fopenid.net%2Fsrv%2Fax%2F1.0&openid.ax.mode=fetch_request&openid.ax.type.user_roles=http%3A%2F%2Faxschema.org%2Fuser%2Froles&openid.ax.type.contact_email=http%3A%2F%2Faxschema.org%2Fcontact%2Femail&openid.ax.type.contact_name=http%3A%2F%2Faxschema.org%2Fcontact%2Fname&openid.ax.type.contact_ename=http%3A%2F%2Faxschema.org%2Fcontact%2Fename&openid.ax.type.student_id=http%3A%2F%2Faxschema.org%2Fstudent%2Fid&openid.ax.type.alunmi_leaveSem=http%3A%2F%2Faxschema.org%2Falunmi%2FleaveSem&openid.ax.required=user_roles&openid.ax.if_available=contact_email%2Ccontact_name%2Ccontact_ename%2Cstudent_id%2Calunmi_leaveSem&openid.identity=https%3A%2F%2Fportal.ncu.edu.tw%2Fuser%2F&openid.claimed_id=https%3A%2F%2Fportal.ncu.edu.tw%2Fuser%2F"
ENDPOINT_URL = "https://cis.ncu.edu.tw/HumanSys/home"
NCU_HOST = "https://portal.ncu.edu.tw/login"
LEAVE_URL = "https://portal.ncu.edu.tw/leaving"
HOST = "https://cis.ncu.edu.tw/HumanSys/home"
NCU_CHECKIN_HOST = "https://cis.ncu.edu.tw/HumanSys/student/stdSignIn"
NCU_CHECKIN_CREATE = "https://cis.ncu.edu.tw/HumanSys/student/stdSignIn/create"
NCU_POST_CHECKIN_CREATE = "https://cis.ncu.edu.tw/HumanSys/student/stdSignIn_detail"
NCU_CIS_LOCALE = "tw"

CURRENT_TIME = datetime.now()

# Set Account/Password In Environment Variables -> NCU_PORTAL = account:password
userinfo = os.environ['NCU_PORTAL'].split(":")
ACCOUNT = userinfo[0]
PASSWORD = userinfo[1]

def HttpMethod(url, method, session, cookies=None, data=None):
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.6',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-User': '?1',
        'Sec-GPC': '1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Brave";v="140"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }

    # Add Referer and Origin based on the target URL
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    if 'cis.ncu.edu.tw' in url:
        headers['Referer'] = 'https://portal.ncu.edu.tw/'
        headers['Origin'] = 'https://portal.ncu.edu.tw'
        headers['Sec-Fetch-Site'] = 'cross-site'
    elif 'portal.ncu.edu.tw' in url:
        headers['Sec-Fetch-Site'] = 'same-origin'
        if method == 'POST':
            headers['Origin'] = base_url
            headers['Referer'] = url

    if method == 'GET':
        res = session.get(url, headers=headers, cookies=cookies, params=data, verify=False)
    elif method == 'POST':
        res = session.post(url, headers=headers, cookies=cookies, data=data, verify=False)
    return res, session

def GetPortalLoginPayload(session):
    xsrf = session.cookies.get_dict()['XSRF-TOKEN']
    payload = {
        'username': ACCOUNT,
        'password': PASSWORD,
        '_csrf': xsrf,
        'language': 'CHINESE',
    }
    # sess = session.cookies.get_dict()['SESSION']
    # portal = session.cookies.get_dict()['portal']
    return payload

def GetPortalLeavingPayload(session):
    xsrf = session.cookies.get_dict()['XSRF-TOKEN']
    payload = {
        'chineseName': "人事系統",
        'englishName': "Human+Resource+System",
        '_csrf': xsrf
    }
    return payload

def Checkin(projectName, projectTime, requireCheckinHour, signoutMsg):
    try:
        session = requests.session()
        res, session = HttpMethod(ENDPOINT_URL, 'GET', session)
        cookies = res.cookies
        log.CheckinLog(f"GET {ENDPOINT_URL} Success")
    except Exception as err:
        txt = f"{CURRENT_TIME} >> GET {ENDPOINT_URL} error message: {err} "
        log.CheckinLog(txt)
        log.CheckinLog(f"GET {ENDPOINT_URL} Failed")
        log.CheckinLog(f"Error: {err}")

    try:
        login_payload = GetPortalLoginPayload(session)
        res, session = HttpMethod(NCU_HOST, 'POST', session, cookies=cookies, data=login_payload)
        cookies = session.cookies
        log.CheckinLog(f"POST {NCU_HOST} Success")
        log.CheckinLog(f"Login response status: {res.status_code}")

        # Check login response
        if res.status_code == 200:
            content = res.content.decode('utf-8')
            page = BS(content, features='lxml')
            title = page.find('title')
            if title:
                log.CheckinLog(f"Login response page title: {title.get_text()}")

    except Exception as err:
        txt = f"{CURRENT_TIME} >> POST {NCU_HOST} error message: {err} "
        log.CheckinLog(txt)
        log.CheckinLog(f"POST {NCU_HOST} Failed")
        log.CheckinLog(f"Error: {err}")
        
    try:
        res, session = HttpMethod(LEAVE_URL, 'POST', session, cookies=cookies, data=GetPortalLeavingPayload(session))
        print(res.content.decode('utf-8'))
        log.CheckinLog(f"POST {LEAVE_URL} Success")

    except Exception as err:
        txt = f"{CURRENT_TIME} >> POST {LEAVE_URL} error message: {err} "
        log.CheckinLog(txt)
        log.CheckinLog(f"POST {LEAVE_URL} Failed")
        log.CheckinLog(f"Error: {err}")

    # Add callback redirect to complete authentication
    CALLBACK_URL = "https://cis.ncu.edu.tw/HumanSys/oauth/callback"
    try:
        res, session = HttpMethod(CALLBACK_URL, 'GET', session, cookies=cookies)
        log.CheckinLog(f"GET {CALLBACK_URL} Success")
        # Update cookies after callback
        callback_cookies = dict(res.cookies)
        cookies.update(callback_cookies)
    except Exception as err:
        txt = f"{CURRENT_TIME} >> GET {CALLBACK_URL} error message: {err} "
        log.CheckinLog(txt)
        log.CheckinLog(f"GET {CALLBACK_URL} Failed")
        log.CheckinLog(f"Error: {err}")

    laravel_session_token = ""


    try:
        res, session = HttpMethod(HOST, 'GET', session)
        cookies = dict(res.cookies)
        cookies['locale'] = NCU_CIS_LOCALE
        
        print("============LARAVEL_SESSION START================")
        print(session.cookies.get_dict())

        print(session.cookies.get_dict()['XSRF-TOKEN'])
        cookies['laravel_session'] = session.cookies.get_dict()['laravel_session']
        print(cookies['laravel_session'])
        laravel_session_token = cookies['laravel_session']
        print("============LARAVEL_SESSION END================")

        content = res.content.decode('utf-8')
        page = BS(content, features='lxml')
        username = parsers.ExtractUserName(page)
        log.CheckinLog(f"Login User: {username}")
        log.CheckinLog(f"GET {HOST} Success")
    except Exception as err:
        txt = f"{CURRENT_TIME} >> GET {HOST} error message: {err} "
        log.CheckinLog(txt)
        log.CheckinLog(f"GET {HOST} Failed")
        log.CheckinLog(f"Error: {err}")

    try:
        res, session = HttpMethod(NCU_CHECKIN_HOST, 'GET', session, cookies=cookies)
        cookies = dict(res.cookies)
        cookies['locale'] = NCU_CIS_LOCALE
        cookies['laravel_session'] = laravel_session_token
        content = res.content.decode('utf-8')
        page = BS(content, features='lxml')

        # Check if login was successful by checking page title
        title = page.find('title')
        if title:
            title_text = title.get_text()
            if 'NCU Portal' in title_text or '中央大學入口網站' in title_text:
                log.CheckinLog(f"Login failed - still on portal page: {title_text}")
                return False

        ParttimeUsuallyId = parsers.ExtractParttimeUsuallyId(page, projectName, projectTime)
        token = parsers.ExtractCheckinToken(page)
        log.CheckinLog(f"Checkin Token: {token}")
        log.CheckinLog(f"ParttimeUsuallyId : {ParttimeUsuallyId}")
        if type(ParttimeUsuallyId) != int:
            return False
        log.CheckinLog(f"GET {NCU_CHECKIN_HOST} Success")
    except Exception as err:
        txt = f"{CURRENT_TIME} >> GET {NCU_CHECKIN_HOST} error message: {err} "
        log.CheckinLog(txt)
        log.CheckinLog(f"GET {NCU_CHECKIN_HOST} Failed")
        log.CheckinLog(f"Error: {err}")

    # Initialize variables in case of exception
    signintime = []
    signouttime = []
    idNo = None
    payload = {}

    try:
        res, session = HttpMethod(NCU_CHECKIN_CREATE, 'GET', session, cookies=cookies, data={'ParttimeUsuallyId': ParttimeUsuallyId})
        cookies = dict(res.cookies)
        cookies['locale'] = NCU_CIS_LOCALE
        cookies['laravel_session'] = laravel_session_token

        content = res.content.decode('utf-8')
        page = BS(content, features='lxml')
        idNo = page.find('input', {'id': 'idNo'})
        idNo = idNo.get('value')
        signintime = page.find('div', {'id': 'SigninTime'}).contents
        signouttime = page.find('div', {'id': 'SignoutTime'}).contents
        
        log.CheckinLog(f"idNo: {idNo}")
        log.CheckinLog(f"signintime: {signintime}")
        log.CheckinLog(f"signouttime: {signouttime}")
        
        payload = {
            'functionName' : "doSign",
            'idNo' : idNo,
            'ParttimeUsuallyId' : ParttimeUsuallyId,
            'AttendWork' : "",
            '_token' : token
        }
        log.CheckinLog(f"GET {NCU_CHECKIN_CREATE} Success")
    except Exception as err:
        txt = f"{CURRENT_TIME} >> GET {NCU_CHECKIN_CREATE} error message: {err} "
        log.CheckinLog(txt)
        log.CheckinLog(f"GET {NCU_CHECKIN_CREATE} Failed")
        log.CheckinLog(f"Error: {err}")
        return False

    # Check if required data was successfully retrieved
    if idNo is None or payload == {}:
        log.CheckinLog("Failed to retrieve required check-in data")
        return False

    if signintime != []:
        txt = '簽退計畫： '+ projectName +'\n'+'簽退時間： ' + str(CURRENT_TIME) 
        signintime_hour = int(signintime[0].split(":")[0])
        if CURRENT_TIME.hour - signintime_hour >= requireCheckinHour:
            try:
                payload['AttendWork'] = signoutMsg
                res, session = HttpMethod(NCU_POST_CHECKIN_CREATE, 'POST', session, cookies=cookies, data=payload)
                content = res.content.decode('utf-8')
                log.CheckinLog(f"POST {NCU_POST_CHECKIN_CREATE} Success")
                log.CheckinLog(txt)
                return True
            except Exception as err:
                txt = f"POST {NCU_POST_CHECKIN_CREATE} error message: {err} "
                log.CheckinLog(txt)
                log.CheckinLog(f"POST {NCU_POST_CHECKIN_CREATE} Failed")
                log.CheckinLog(f"Error: {err}")
        else:
            txt = f"簽退時間未滿{requireCheckinHour}小時： " + str(CURRENT_TIME) 
            log.CheckinLog(txt)
            log.CheckinLog("Not Yet To Signout")
    else:
        log.CheckinLog("Signin!")
        txt = '簽到計畫： '+ projectName +'\n' + '簽到時間： ' + str(CURRENT_TIME) 
        try:
            res, session = HttpMethod(NCU_POST_CHECKIN_CREATE, 'POST', session, cookies=cookies, data=payload)
            content = res.content.decode('utf-8')
            log.CheckinLog(f"POST {NCU_POST_CHECKIN_CREATE} Success")
            log.CheckinLog(txt)
            return True
        except Exception as err:
            txt = f"{CURRENT_TIME} >> POST {NCU_POST_CHECKIN_CREATE} error message: {err} "
            log.CheckinLog(txt)
            log.CheckinLog(f"POST {NCU_POST_CHECKIN_CREATE} Failed")
            log.CheckinLog(f"Error: {err}")
    return False