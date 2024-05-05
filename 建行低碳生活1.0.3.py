# 软件:建行生活
# 活动信息: 低碳生活，碳能量换取立减金，外卖券
# 格式 ccdck =  deviceid值#meb_id值#手机号#token值
# 定时：0 57 6,20 * * *
# 注: 此脚本仅限个人使用,不得传播
# 更新日志:
#   - [1.1]:
#   - [4.23]: [增加自动兑换]
# 说明: 抢兑一般为早上7点，8点,自己根据不同券定时。提前两三分钟会定时。早上不上传步数。
import os
import random
import re
import time
import datetime
import json
from urllib.parse import quote

import requests

exchange_name = ""  # 兑换奖品名称  【地球日低碳特惠】外卖满10元减4元券(xx) 只需填写外卖满10元减4元券


class CCD:
    def __init__(self, ccb_cookie):
        self.GLOBAL_DEBUG = False
        ccb_cookie_parts = ccb_cookie.split("#")
        self.deviceid, self.meb_id, self.phone, self.ccb_token = ccb_cookie_parts
        self.user_id = None
        self.user_city = None
        self.Cst_ID = None
        self.base_url = "https://iss.ccb.com/JQCXLCL/B2CMainPlat_13？"
        self.token_headers = {
            'Host': 'iss.ccb.com',
            'accept': 'application/json, text/plain, */*',
            'origin': 'https://iss.ccb.com',
            'x-requested-with': 'com.ccb.longjiLife',
            'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'content-type': 'application/json;charset=UTF-8',
            'referer': 'https://iss.ccb.com/JQCXStaRes/lctgamepage/index.html'
        }

    def send_request(self, url, headers=None, params=None, data=None, cookies=None, method='GET', debug=None):
        try:
            debug = debug if debug is not None else self.GLOBAL_DEBUG

            with requests.Session() as session:
                session.headers.update(headers or {})
                if cookies is not None:
                    session.cookies.update(cookies)

                if isinstance(data, dict):
                    response = session.request(method, url, params = params, json = data)
                else:
                    response = session.request(method, url, params = params, data = data)

                response.raise_for_status()

                if debug:
                    print(response.text)

                return response

        except requests.RequestException as e:
            print("请求错误:", str(e))

        return None

    def encrypt(self, text):
        res = requests.post('http://82.157.10.108:8086/get_jhenc', data = {'encdata': text})
        return res.text

    # 刷新session,param
    def get_param(self):
        try:
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
                "Token": self.ccb_token}
            data = json.dumps(data)
            data = quote(self.encrypt(data))
            response = requests.post('https://yunbusiness.ccb.com/clp_service/txCtrl', params = params,
                                     cookies = cookies,
                                     headers = headers, data = data)

            setCookie = response.headers.get('Set-Cookie')
            if setCookie:
                session_cookie = re.search(r'SESSION=([^;]+)', setCookie)
                session_value = session_cookie.group(1)

                param_url = 'https://yunbusiness.ccb.com/basic_service/txCtrl?txcode=A3341SB06'
                param_payload = {
                    "regionCode": "110000",
                    "PLATFORM_ID": "YS44000008000397",
                    "chnlType": "1",
                    "APPEND_PARAM": "",
                    "ENCRYPT_MSG": f"BGCOLOR=&userid={self.meb_id}&mobile={self.phone}&orderid=&PLATFLOWNO=1051000101693904952945620&cityid=610100&openid=&Usr_Name=&USERID={self.meb_id}&MOBILE={self.phone}&ORDERID=&CITYID=610100&OPENID=&userCityId=360400&lgt=116.25548583307314&ltt=29.36255293895674&USERCITYID=360400&LGT=116.25548583307314&LTT=29.36255293895674&GPS_TYPE=gcj02&MOBILE={self.phone}&CrdtType=1010&CrdtNo=231212"
                }

                headers['cookie'] = f'SESSION={session_value}'
                param_data = requests.post(param_url, headers = headers, json = param_payload).json()
                errCode = param_data.get('errCode')
                if errCode != '0':
                    print(param_data)
                    return None
                else:
                    jhsh_Param = param_data.get('data', {}).get('ENCRYPTED_MSG', '')
                    return jhsh_Param
            else:
                print(f'session刷新失败，{response.text}')
                return None
        except Exception as e:
            print(f"错误信息:{e}")

    # 登录
    def login(self):
        try:
            param = self.get_param()
            login_payload = {
                "ccbParam": param,
                "chlno": "LCL005",
                "sourceid": 1
            }

            login_data = self.query("LCL154", data = login_payload, param = param)
            if login_data is not None:
                # 成功
                auth_token = login_data.get('authToken')
                self.token_headers['authorization'] = auth_token
                user_name = login_data.get('userName')  # 昵称
                self.Cst_ID = login_data.get('lclP6Userid')  # 556..
                self.user_id = login_data.get('userid')  # 000..
                self.user_info(user_name)
            else:
                # 失败
                print(f'-登录失败,ck可能失效')

        except Exception as e:
            print(e)

    # 用户信息
    def user_info(self, user_name):
        try:
            # 等级
            level_data = self.query("LCL193")
            if level_data is not None:
                # 成功
                tree_level = level_data.get('tree_level')
                island_name = level_data.get('island_name')  # 名称
                carbon_emission = level_data.get('carbon_emission')  # 碳排放量
                print(f'-用户【{user_name}】等级【{tree_level}】: {island_name}')
            else:
                # 失败
                print('-查询失败')
            # 积分
            remain_payload = {
                "Cst_ID": self.Cst_ID,
                "Cst_APAcc_SN": "",
                "pageSize": "10",
                "page": "1"
            }
            remain_data = self.query("LCL146", data = remain_payload)
            APnt_Bal = None
            if remain_data is not None:
                # 成功
                APnt_Bal = remain_data.get('APnt_Bal')  # 可用积分
                print(f'-当前账户碳能量: {APnt_Bal}')
            else:
                # 失败
                print('-查询失败')

            now = datetime.datetime.now()

            if now.hour < 12:
                self.award_list(APnt_Bal)
            else:
                # 可捡能量
                rcrd_num_payload = {
                    "Cst_ID": self.Cst_ID,
                    "Cst_APAcc_SN": "",
                    "pageSize": "20",
                    "page": "1"
                }
                rcrd_num_data = self.query("LCL148", data = rcrd_num_payload)
                if rcrd_num_data is not None:
                    Rvl_Rcrd_Num = int(rcrd_num_data.get('Rvl_Rcrd_Num'))
                    Avl_APnt = rcrd_num_data.get('Avl_APnt')
                    if Rvl_Rcrd_Num == 0:
                        print(f'-当前可捡次数: {Rvl_Rcrd_Num}')
                    else:
                        print(f'-当前可捡次数: {Rvl_Rcrd_Num},待领取能量值: {Avl_APnt}')
                        LIST1 = rcrd_num_data.get('LIST1')  # 领取列表1
                        for value in LIST1:
                            time.sleep(2)
                            Txn_Ordr_No = value.get('Txn_Ordr_No')
                            Itm_Tp_ID = value.get('Itm_Tp_ID')
                            Apnt_Hpn_Num = value.get('Apnt_Hpn_Num')
                            receive_payload = {
                                "Cst_ID": self.Cst_ID,
                                "USER_ID": self.user_id,
                                "Txn_Ordr_No": Txn_Ordr_No,
                                "Itm_Tp_ID": Itm_Tp_ID,
                                "Apnt_Hpn_Num": Apnt_Hpn_Num,
                                "pageSize": "1",
                                "page": "1",
                                "sourceid": "1"
                            }
                            receive_data = self.query("LCL149", data = receive_payload)
                            if receive_data is not None:
                                APnt_Hpn_Num = receive_data.get('APnt_Hpn_Num')
                                print(f'-领取成功，获得能量: {APnt_Hpn_Num}')
                            else:
                                print('-领取失败')
                else:
                    print('-捡能量失败')
                # 上传步数
                print('-上传步数，假装走了很多步~')
                # 获取当前时间
                current_time = datetime.datetime.now()

                # 格式化成特定的字符串
                formatted_time = current_time.strftime('%Y-%m-%d %H:%M:%S')
                upload_payload = {
                    "txnAmt": random.randint(23800, 26000),
                    "openTime": formatted_time,
                    "phoneType": "0"
                }

                upload_data = self.query("LCL213", data = upload_payload)
                if upload_data is not None:
                    Apnt_Hpn_Num = upload_data.get('Apnt_Hpn_Num')
                    print(f'-上传步数成功，获得能量: {Apnt_Hpn_Num}')
                else:
                    print('-上传步数失败')
        except Exception as e:
            print(f'错误信息: {e}')

    # 奖品列表
    def award_list(self, APnt_Bal):
        try:
            if exchange_name == "":
                print('用户未开启兑换')
                return
            list_payload = {
                "curPage": 1,
                "chlno": "LCL005",
                "regionCode": "110000"
            }

            list_res = self.query("LCL155", data = list_payload)
            if list_res is not None:
                lcld = list_res.get('lcld')
                coupon_title, coupon_id, type, coupon_price = self.find_prize(lcld)
                if coupon_title is None:
                    print(f'未找到{exchange_name}，请检查是否有该类型的奖品。')
                    return
                elif int(APnt_Bal) < int(coupon_price):
                    print('当前碳能量不足，无法兑换~~')
                    return
                else:
                    # 开始兑换
                    code_payload = {
                        "Channel_Business": type,
                        "Coupon_id": coupon_id
                    }

                    code_res = self.query("LCL206", data = code_payload)
                    coupon_code = code_res.get("MSPS_ENTITY")[0].get("Coupon_ID")
                    Remain_Num = code_res.get("MSPS_ENTITY")[0].get("Remain_Num")
                    print(f'开始兑换: {coupon_title}, 库存数量: {Remain_Num}')

                    exchange_payload = {
                        "Channel_Business": type,
                        "chlno": "LCL005",
                        "Cst_ID": self.Cst_ID,
                        "coupon_id": coupon_id,
                        "coupon_code": coupon_code,
                        "DcCp_Avy_Nm": coupon_title,
                        "Adj_APnt_Num": coupon_price,
                        "tel": self.phone,
                        "coupon_an_name": "",
                        "Discount_Id": "",
                        "Opr_Blng_Inst_ECD": ""
                    }
                    # 获取当前时间
                    now = datetime.datetime.now()

                    if now.minute <= 15 or (30 <= now.minute < 45):
                        time_to_next_run = 0
                    elif now.minute < 30:
                        time_to_next_run = (30 - now.minute) * 60 - now.second
                    else:
                        time_to_next_run = (60 - now.minute) * 60 - now.second

                    print(f'将在:{time_to_next_run}秒后继续执行')

                    time.sleep(time_to_next_run)

                    for _ in range(3):
                        exchange_res = self.query("LCL207", data = exchange_payload)
                        if exchange_res is not None:
                            print(exchange_res)
                            break

            else:
                print("获取奖品列表失败")

        except Exception as e:
            print(f'兑换奖品出差:{e}')

    def find_prize(self, exchange_lists):
        for val in exchange_lists:
            coupon_title = val.get("coupon_title")
            coupon_id = val.get("coupon_id")
            type = val.get("type")
            coupon_price = val.get("coupon_price")  # 价格
            if exchange_name in coupon_title:
                print(coupon_title)

                return coupon_title, coupon_id, type, coupon_price
        return None, None, None, None

    # 查询
    def query(self, code, data=None, param=None):
        try:
            base_url = 'https://iss.ccb.com/JQCXLCL/B2CMainPlat_13'
            servlet_name = 'B2CMainPlat_13'
            ccb_version = 'V6'
            pt_style = '3'
            chlno = 'LCL005'
            url = f'{base_url}?SERVLET_NAME={servlet_name}&CCB_IBSVersion={ccb_version}&PT_STYLE={pt_style}&TXCODE={code}&chlno={chlno}'
            if param is not None:
                url = f'{url}&ccbParam={param}'

            data = data or {}
            time.sleep(0.1)
            response = self.send_request(url, headers = self.token_headers, data = data, method = "POST").text

            # 去除空格
            response_without_space = response.lstrip()

            # 解析 JSON 数据
            json_data = json.loads(response_without_space)
            if json_data.get('success'):
                return json_data.get('data')
            else:
                error_msg = json_data.get('msg')
                print(error_msg)
                return None

        except Exception as e:
            print(f"错误信息：{e}")


if __name__ == "__main__":
    env_name = 'ccdck'
    token = os.getenv(env_name)
    if not token:
        print(f'⛔️未获取到ck变量：请检查变量 {env_name}是否填写')
        exit(0)
    cookies = re.split(r'[@\n]', token)
    msg = f"低碳生活共获取到{len(cookies)}个账号"
    print(msg)

    for i, cookie in enumerate(cookies, start = 1):
        print(f"\n======== ▷ 第 {i} 个账号 ◁ ========")
        CCD(cookie).login()
        print("\n随机等待5-10s进行下一个账号")
        time.sleep(random.randint(5, 10))
