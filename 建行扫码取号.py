# 脚本名称: [建行扫码取号]
# 功能描述: [抽奖获得外卖券]
# 使用说明:
#   - 同建行生活CC豆
#   - 注后续新类似活动只需找 https://event.ccbft.com/api/activity 请求体里面activityCode值填入下面activityCode
# 定时设置: [定时执行的时间，如每天特定时间]
# 更新日志:
#   - [日期]: 2.18
#   - [日期]: [更新内容]
# 注: 本脚本仅用于个人学习和交流，请勿用于非法用途。作者不承担由于滥用此脚本所引起的任何责任，请在下载后24小时内删除。
# 作者: 洋洋不瘦

import os
import random
import re
import time
import json
from urllib.parse import quote

import requests

GLOBAL_DEBUG = False
send_notify = []


def log_info(text, notify=False):
    if notify:
        print(text)
        send_notify.append(text)
    else:
        print(text)


class CCD:
    def __init__(self, ccb_cookie):
        ccb_cookie_parts = ccb_cookie.split("#")
        self.deviceid, self.meb_id, self.phone, self.ccb_token = ccb_cookie_parts
        self.session = requests.Session()
        self.activityCode = 'AP20240223F0301T0331'
        self.user_id = None
        self.token_headers = {
            'Host': 'event.ccbft.com',
            'accept': 'application/json, text/plain, */*',
            'origin': 'https://event.ccbft.com',
            'x-requested-with': 'com.ccb.longjiLife',
            'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'content-type': 'application/json'
        }

    def send_request(self, url, headers=None, cookies=None, data=None, params=None, method='GET', debug=None,
                     retries=5):

        debug = debug if debug is not None else GLOBAL_DEBUG

        self.session.headers.update(headers or {})
        if cookies:
            self.session.cookies.update(cookies)
        request_args = {'json': data} if isinstance(data, dict) else {'data': data}

        for attempt in range(retries):
            try:
                response = self.session.request(method, url, params = params, **request_args)
                response.raise_for_status()
                if debug:
                    print(f'\n【{url}】响应数据:\n{response.text}')
                return response
            except (requests.RequestException, ConnectionError, TimeoutError) as e:
                print(f"请求异常: {e}")
                if attempt >= retries - 1:
                    print("达到最大重试次数。")
                    return None
                time.sleep(1)

    def encrypt(self, text):
        res = requests.post('http://82.157.10.108:8086/get_jhenc', data = {'encdata': text})
        return res.text

    # 刷新session,param
    def get_param(self, type=1):
        try:
            url = 'https://yunbusiness.ccb.com/clp_service/txCtrl?txcode=autoLogin'

            headers = {
                'Host': 'yunbusiness.ccb.com',
                'user-agent': '%E5%BB%BA%E8%A1%8C%E7%94%9F%E6%B4%BB/2023031502 CFNetwork/1404.0.5 Darwin/22.3.0',
                'devicetype': 'iOS',
                'mbc-user-agent': f'MBCLOUDCCB/iPhone/iOS16.3.1/2.15/2.1.5/7E1BDB39-5CF8-4B88-BB12-AFF439B6A249/chinamworld/750*1334/2.1.5.002/1.0/{self.deviceid}/iPhone8Global/iOS/iOS16.3.1',
                'appversion': '2.1.5.002',
                'ua': 'IPHONE',
                'clientallver': '2.1.5.002',
                'deviceid': self.deviceid,
                'accept-language': 'zh-CN,zh-Hans;q=0.9',
                'c-app-id': '03_64e1367661ee4091acc04ce98f3660e6',
                'accept': 'application/json',
                'content-type': 'application/json',
            }

            data = {
                "Token": self.ccb_token}
            data = json.dumps(data)
            data = quote(self.encrypt(data))
            res = self.send_request(url, headers, data = data, method = "POST")

            setCookie = res.headers.get('Set-Cookie')
            if setCookie:
                session_cookie = re.search(r'SESSION=([^;]+)', setCookie)
                session_value = session_cookie.group(1)
                if type == 1:
                    return session_value
                elif type == 2:
                    param_url = 'https://yunbusiness.ccb.com/basic_service/txCtrl?txcode=A3341SB06'
                    param_payload = {
                        "regionCode": "110000",
                        "PLATFORM_ID": "WANGDIANQHHD20240426",  # 需要更换
                        "chnlType": "1",
                        "APPEND_PARAM": "",
                        "ENCRYPT_MSG": f"BGCOLOR=&userid={self.meb_id}&mobile={self.phone}&orderid=&PLATFLOWNO=1051000101693904952945620&cityid=610100&openid=&Usr_Name=&USERID={self.meb_id}&MOBILE={self.phone}&ORDERID=&CITYID=610100&OPENID=&userCityId=360400&lgt=116.25548583307314&ltt=29.36255293895674&USERCITYID=360400&LGT=116.25548583307314&LTT=29.36255293895674&GPS_TYPE=gcj02&MOBILE={self.phone}&CrdtType=1010&CrdtNo=231212"
                    }

                    headers['cookie'] = f'SESSION={session_value}'
                    param_res = self.send_request(param_url, headers = headers, data = param_payload,
                                                  method = "POST").json()
                    errCode = param_res.get('errCode')
                    if errCode != '0':
                        print(param_res)
                        return None
                    else:
                        jhsh_Param = param_res.get('data', {}).get('ENCRYPTED_MSG', '')
                        return jhsh_Param

            else:
                print(f'session刷新失败，{res.text}')
                return None
        except Exception as e:
            print(f"错误信息:{e}")

    # 获取token，uuid
    def get_ccb_uuid(self):
        ccbParam = self.get_param(type = 2)
        if ccbParam is None:
            return None
        try:
            url = f"https://event.ccbft.com/api/flow/nf/shortLink/redirect/ccb_gjb?CCB_Chnl=2030023&ccbParamSJ={ccbParam}&cityid=110000&CITYID=110000&userCityId=110000&USERCITYID=110000"

            payload = {
                "shortId": "polFsWD2jPnjhOx9ruVBcA",
                "archId": "ccb_gjb",
                "ccbParamSJ": ccbParam,
                "channelId": "ccbLife",
                "ifCcbLifeFirst": True
            }
            base_header = {
                'Host': 'event.ccbft.com',
                'accept': 'application/json, text/plain, */*',
                'origin': 'https://event.ccbft.com',
                'x-requested-with': 'com.ccb.longjiLife',
                'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'content-type': 'application/json'
            }

            return_data = self.send_request(url, headers = base_header, data = payload, method = 'POST').json()

            redirect_url = return_data['data'].get('redirectUrl')
            pattern = f"__dmsp_token=([^&]+)"
            match = re.search(pattern, redirect_url)
            token = match.group(1) if match else None
            ccb_uuid = return_data['data'].get('ccbLifeUUID')
            return token, ccb_uuid
        except Exception as e:
            print(e)

    # 活动secparam
    def get_secParam(self):
        try:
            user_msg = self.get_param(type = 2)
            detail_url = "https://event.ccbft.com/api/activity/nf/largeTurntableRaffleServer/queryActivityDetail"
            detail_payload = {
                "activityCode": self.activityCode,
                "verFlag": "act",
                "channel": "jhsh",
                "userMsg": user_msg,
            }

            response = self.send_request(detail_url, headers = self.token_headers, data = detail_payload,
                                         method = "POST")
            secParam = response.headers.get('secParam')
            return_data = response.json()
            self.token_headers['secParam'] = secParam
            if secParam:
                self.user_id = return_data.get('data', {}).get('userId', '')
                self.query()
            else:
                log_info(f"登录失败: {return_data}")

        except Exception as e:
            print(e)

    # 查询
    def query(self):
        try:
            num_url = 'https://event.ccbft.com/api/activity/nf/largeTurntableRaffleServer/queryLotteryCount'
            num_payload = {
                "activityCode": self.activityCode,
                "userId": self.user_id
            }

            num_res = self.send_request(num_url, headers = self.token_headers, data = num_payload,
                                        method = "POST").json()
            points = num_res.get('data').get('points')
            print(f'用户剩余抽奖次数: {points}')
            time.sleep(2)
            for _ in range(points):
                draw_url = 'https://event.ccbft.com/api/activity/nf/largeTurntableRaffleServer/activityParticipation'
                draw_payload = {
                    "activityCode": self.activityCode,
                    "verFlag": "act",
                    "userId": self.user_id
                }
                draw_res = self.send_request(draw_url, headers = self.token_headers, data = draw_payload,
                                             method = "POST").json()
                if draw_res.get('code') != 200:
                    print(draw_res.get('message'))
                coupon_name = draw_res.get('data', {}).get('couponName', '')

                print(f'抽奖结果: {coupon_name}')
                time.sleep(3)

        except Exception as e:
            print(e)


if __name__ == "__main__":
    env_name = 'ccdck'
    token = os.getenv(env_name)
    if not token:
        print(f'⛔️未获取到ck变量：请检查变量 {env_name}是否填写')
        exit(0)
    cookies = re.split(r'[@\n]', token)
    msg = f"建行生活共获取到{len(cookies)}个账号"
    print(msg)

    for i, cookie in enumerate(cookies, start = 1):
        print(f"\n======== ▷ 第 {i} 个账号 ◁ ========")
        CCD(cookie).get_secParam()
        print("\n随机等待5-10s进行下一个账号")
        time.sleep(random.randint(5, 10))
