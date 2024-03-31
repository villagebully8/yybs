# 脚本名称: [建行生活签到]
# 功能描述: [获得外卖券]
# 使用说明:
#   - 同建行生活CC豆CK
# 定时设置: [0 0 7,16 * * *]
# 更新日志:
#   - [3.8]: 增加普通用户可断签一次
#   - [3.17]: 增加第七天用户可更换奖励
# 注: 本脚本仅用于个人学习和交流，请勿用于非法用途。作者不承担由于滥用此脚本所引起的任何责任，请在下载后24小时内删除。
# 作者: 洋洋不瘦

import os
import json
import random
import re
import time
from urllib.parse import quote
import requests

mid = '165'  # 有问题，请求头这里改成自己的

reward_type = '外卖'  # 奖励类型  外卖  或者  出行
Flag = 0  # 外卖类型，1为信用卡专属,0普通用户
Break = 0  # 0正常领取， 1签到三天断签一天，2继续签到并且第七天领取打车券 (普通用户可选)


class CCD:
    def __init__(self, ccb_cookie):
        ccb_cookie_parts = ccb_cookie.split("#")
        self.deviceid, self.meb_id, self.phone, self.ccb_token = ccb_cookie_parts
        self.session = requests.Session()
        self.info_headers = {
            'Host': 'yunbusiness.ccb.com',
            'zipversion': '1.0',
            'channel_num': '2',
            'mid': mid,
            'accept': 'application/json,text/javascript,*/*',
            'content-type': 'application/json;charset=UTF-8',
            'Connection': 'keep-alive'
        }

    # 定义加密函数
    def encrypt(self, text):
        res = requests.post('http://82.157.10.108:8086/get_jhenc', data = {'encdata': text})
        return res.text

    # 签到
    def ccbLife(self):
        session_value = self.auto_login(self.ccb_token)
        if session_value is None:
            return print('刷新session失败')
        info_url = "https://yunbusiness.ccb.com/clp_coupon/txCtrl?txcode=A3341A038"  # 签到信息

        d = self.get_act_id(self.meb_id, '签到')
        ACT_ID = d.get('AD_URL', '').split('=')[1]
        info_payload = {
            "MEB_ID": self.meb_id,
            "ACT_ID": ACT_ID,
            "REGION_CODE": "110000",
            "chnlType": "1",
            "regionCode": "110000"}

        info_data = requests.request("POST", info_url, headers = self.info_headers, json = info_payload).json()

        REWARD_NODES = info_data.get('data', {}).get('REWARD_NODES', '')

        IS_SIGN = info_data.get('data', {}).get('IS_SIGN', '')  # 是否签到
        SIGN_DAY = info_data.get('data', {}).get('SIGN_DAY', '')  # 签到天数
        REWORD_LIST = info_data.get('data', {}).get('REWORD_LIST', '')
        if IS_SIGN == 1:
            print(f'-今日已签到，当前签到次数: {SIGN_DAY}')
            self.reward_day(SIGN_DAY, REWORD_LIST, REWARD_NODES)
        else:
            if Break == 1 and SIGN_DAY >= 3:
                print('用户已连续签到3次，为你断签一次')
                return
            elif Break == 2 and SIGN_DAY >= 6:
                global reward_type
                print('用户已连续签到6次，奖励类型改为出行')
                reward_type = '出行'

            print('未签到，去签到')
            signin_url = 'https://yunbusiness.ccb.com/clp_coupon/txCtrl?txcode=A3341A115'  # 签到
            signin_payload = {
                "regionCode": "110000",
                "REGION_CODE": "110000",
                "chnlType": "1",
                "APPEND_PARAM": "",
                "ACT_ID": ACT_ID
            }  # deceiveid

            signin_headers = {
                'Host': 'yunbusiness.ccb.com',
                'zipversion': '1.0',
                'accept': 'application/json',
                'deviceid': 'deviceid',
                'mid': mid,
                'appversion': '2.1.3.001',
                'devicetype': 'Android',
                'channel_num': '2',
                'mbc-user-agent': f'MBCLOUDCCB/Android/Android 13/2.13/2.00/{self.deviceid}/chinamworld/1080*2316/',
                'Cookie': f'SESSION={session_value}',
                'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
                'content-type': 'application/json; charset=utf-8',
                'Connection': 'keep-alive'
            }
            signin_data = requests.request("POST", signin_url, headers = signin_headers, json = signin_payload).json()
            if signin_data.get('errCode', '') == '0':
                info_data = requests.request("POST", info_url, headers = self.info_headers, json = info_payload).json()

                REWARD_NODES = info_data.get('data', {}).get('REWARD_NODES', '')
                SIGN_DAY = info_data.get('data', {}).get('SIGN_DAY', '')  # 签到天数
                REWORD_LIST = info_data.get('data', {}).get('REWORD_LIST', '')
                print(f'-签到成功,已签到天数: {SIGN_DAY}')
                self.reward_day(SIGN_DAY, REWORD_LIST, REWARD_NODES)
            else:
                print(signin_data)

    # 查询奖励
    def reward_day(self, SIGN_DAY, REWORD_LIST, REWARD_NODES):
        if REWORD_LIST:
            for reward in REWORD_LIST:
                DISTRIBUTE_STATUS = reward['DISTRIBUTE_STATUS']
                if DISTRIBUTE_STATUS == 1:
                    COUP_TITLE = reward['COUP_TITLE']
                    COUP_SUB_TITLE = reward['COUP_SUB_TITLE']
                    print(f'-已领取奖励: {COUP_TITLE} {COUP_SUB_TITLE}')
                else:
                    print(f'-领取签到{SIGN_DAY}天奖励')
                    coupon_id, coupon_type, dccp = self.get_coupon_id(SIGN_DAY, REWARD_NODES)
                    print(f'奖品ID: {coupon_id}')
                    self.receive(SIGN_DAY, coupon_id, coupon_type, dccp)

    # 奖品id
    def get_coupon_id(self, sign_day, REWARD_NODES):
        coupon_id = None
        coupon_type = None
        dccp = None
        for value in REWARD_NODES[str(sign_day)]:
            couponScene = value['couponScene']

            couponId = value['couponId']
            couponType = value['couponType']
            dccpBscInfSn = value['dccpBscInfSn']

            if reward_type != couponScene:
                continue
            if reward_type == '出行':
                coupon_id = couponId
                coupon_type = couponType
                dccp = dccpBscInfSn
                break

            elif reward_type == '外卖' and (
                    Flag == 1 and '限信用卡' in value['subTitle'] or Flag != 1 and '限信用卡' not in value['subTitle']):
                coupon_id = couponId
                coupon_type = couponType
                dccp = dccpBscInfSn
                break
        return coupon_id, coupon_type, dccp

    # 签到奖励
    def receive(self, SIGN_DAY, coupon_id, coupon_type, dccp):
        d = self.get_act_id(self.meb_id, '签到')
        ACT_ID = d.get('AD_URL', '').split('=')[1]
        receive_url = 'https://yunbusiness.ccb.com/clp_coupon/txCtrl?txcode=A3341C082'
        receive_payload = {
            "actId": ACT_ID,
            "nodeDay": SIGN_DAY,
            "couponType": coupon_type,
            "nodeCouponId": coupon_id,
            "dccpBscInfSn": dccp,
            "mebId": self.meb_id,
            "chnlType": "1",
            "regionCode": "110000"
        }

        receive_data = requests.request("POST", receive_url, headers = self.info_headers, json = receive_payload).json()
        if receive_data['errCode'] != '0':
            print(receive_data)
        else:
            print(f'-{receive_data.get("data").get("couponName")}: 领取成功')

    # 获取ACT_ID
    def get_act_id(self, mem_id, key_word):
        params = {
            'txcode': 'A3341AB03',
        }
        headers = {
            'clientinfo': '',
            'user-agent': '%E5%BB%BA%E8%A1%8C%E7%94%9F%E6%B4%BB/2023031502 CFNetwork/1220.1 Darwin/20.3.0',
            'devicetype': 'iOS',
            'mbc-user-agent': 'MBCLOUDCCB/iPhone/iOS14.4.2/2.12/2.1.2/0/chinamworld/750*1334/2.1.2.001/1.0//iPad13,1/iOS/iOS14.4.2',
            'appversion': '2.1.2.001',
            'ua': 'IPHONE',
            'clientallver': '2.1.2.001',
            'accept-language': 'zh-cn',
            'deviceid': self.deviceid,
            'c-app-id': '03_64e1367661ee4091acc04ce98f3660e6',
            'accept': 'application/json',
            'content-type': 'application/json',
        }

        json_data = {
            'IS_CARE': '0',
            'REGION_CODE': '110000',
            'MEB_ID': mem_id,
            'CHANNEL_TYPE': '14',
            'LGT': '116.2445327671808',
            'LTT': '40.05567999910404',
            'DEVICE_NO': '',
            'REAL_REGION_CODE': '110000',
            'SECOND_AD_TYPE_LIST': [
                {
                    'SECOND_AD_TYPE': '6',
                },
                {
                    'SECOND_AD_TYPE': '7',
                },
                {
                    'SECOND_AD_TYPE': '10',
                },
                {
                    'SECOND_AD_TYPE': '11',
                },
                {
                    'SECOND_AD_TYPE': '12',
                },
                {
                    'SECOND_AD_TYPE': '24',
                },
                {
                    'SECOND_AD_TYPE': '25',
                },
                {
                    'SECOND_AD_TYPE': '37',
                },
                {
                    'SECOND_AD_TYPE': '38',
                },
                {
                    'SECOND_AD_TYPE': '39',
                },
                {
                    'SECOND_AD_TYPE': '40',
                },
                {
                    'SECOND_AD_TYPE': '41',
                },
                {
                    'SECOND_AD_TYPE': '42',
                },
                {
                    'SECOND_AD_TYPE': '75',
                },
                {
                    'SECOND_AD_TYPE': '93',
                },
                {
                    'SECOND_AD_TYPE': '94',
                },
                {
                    'SECOND_AD_TYPE': '95',
                },
                {
                    'SECOND_AD_TYPE': '96',
                },
            ],
            'FEED_AD_SHOW_STATUS': 0,
            'chnlType': '1',
            'regionCode': '110000',
        }

        response = requests.post('https://yunbusiness.ccb.com/basic_service/txCtrl', params = params, headers = headers,
                                 json = json_data)
        data = response.json().get('data', {})
        info = data.get('GIFT_AD_INFO', [])
        for d in info:
            if key_word in str(d):
                return d

    # 刷新session
    def auto_login(self, ccb_token):
        cookies = {
        }

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

        params = {
            'txcode': 'autoLogin',
        }

        data = {
            "Token": ccb_token}
        data = json.dumps(data)
        data = quote(self.encrypt(data))
        response = requests.post('https://yunbusiness.ccb.com/clp_service/txCtrl', params = params, cookies = cookies,
                                 headers = headers, data = data)

        setCookie = response.headers.get('Set-Cookie')
        if setCookie:
            session_cookie = re.search(r'SESSION=([^;]+)', setCookie)
            session_value = session_cookie.group(1)
            return session_value
        else:
            return None


if __name__ == "__main__":
    env_name = 'ccdck'
    py_name = '建行生活'
    token = os.getenv(env_name)
    if not token:
        print(f'⛔️未获取到ck变量：请检查变量 {env_name}是否填写')
        exit(0)
    cookies = re.split(r'[@\n]', token)
    print(f"{py_name}共获取到{len(cookies)}个账号")

    for i, cookie in enumerate(cookies, start = 1):
        print(f"\n======== ▷ 第 {i} 个账号 ◁ ========")
        CCD(cookie).ccbLife()
        print("\n随机等待5-10s进行下一个账号")
        time.sleep(random.randint(5, 10))
