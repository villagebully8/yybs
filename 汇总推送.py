"""
cron: 30 59 23 * * *
new Env('电信汇总推送');
"""
import json
import requests
import os
import logging
import datetime

# 设置日志记录
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 检查环境变量
required_env_vars = ["WXPUSHER_APP_TOKEN", "WXPUSHER_UID"]
for var in required_env_vars:
    if not os.getenv(var):
        logging.error(f"环境变量 {var} 未设置")
        exit(1)

# 读取文件内容
try:
    with open('电信金豆换话费2.log', 'r', encoding='utf-8') as f:
        data = json.load(f)
        logging.info("文件读取成功")
except FileNotFoundError:
    logging.error("文件未找到，请检查文件路径。")
    exit(1)
except json.JSONDecodeError:
    logging.error("文件内容不是有效的JSON格式。")
    exit(1)

# 定义推送函数
def send_wxpusher_notification(title, summary, content):
    appToken = os.getenv("WXPUSHER_APP_TOKEN")
    uid = os.getenv("WXPUSHER_UID")
    
    url = "https://wxpusher.zjiecode.com/api/send/message"
    payload = {
        "appToken": appToken,
        "content": content,
        "summary": summary,  # 设置通知栏摘要
        "contentType": 2,  # 使用HTML格式
        "uids": [uid],
        "title": title  # 设置通知栏标题
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # 检查请求是否成功
        return response.json()
    except requests.RequestException as e:
        logging.error(f"推送失败: {e}")
        return {"success": False, "msg": str(e)}

# 整理内容为HTML表格
def format_as_html_table(data, current_month):
    all_fees = {"0.5元话费", "1元话费", "5元话费", "10元话费"}
    fee_order = ["0.5元话费", "1元话费", "5元话费", "10元话费"]
    
    # 初始化汇总计数器
    total_redeemed = {"0.5": 0, "1": 0, "5": 0, "10": 0}
    total_accounts = 0
    total_unredeemed_amount = 0
    
    # 创建HTML表格
    table = """
    <style>
        table {
            width: 100%;
            border-collapse: collapse;
            border: 2px solid black;
            text-align: center;
        }
        th, td {
            padding: 8px;
            border: 1px solid black;
            text-align: center;
            color: white;  /* 设置文本颜色为白色 */
        }
        th {
            background-color: #444;  /* 设置表头背景颜色为深灰色 */
            font-size: 1.2em;  /* 设置表头字体大小 */
        }
        tr:nth-child(even) {
            background-color: #666;  /* 设置偶数行背景颜色为深灰色 */
        }
        tr:nth-child(odd) {
            background-color: #555;  /* 设置奇数行背景颜色为稍浅的深灰色 */
        }
        .summary-title {
            font-size: 1.5em;  /* 设置汇总标题字体大小 */
            font-weight: bold;  /* 设置汇总标题加粗 */
            text-align: center;  /* 设置汇总标题居中 */
        }
    </style>
    <table>
        <tr>
            <th>手机号</th>
            <th>已兑换到</th>
            <th>未兑换到</th>
        </tr>
    """
    
    for phone, details in data.items():
        if len(phone) != 11:
            continue
        
        hidden_phone = phone[:3] + "****" + phone[-4:]
        
        if current_month in details:
            fees = set(details[current_month])
        else:
            fees = set()
        
        unredeemed_fees = all_fees - fees
        fees = {fee.replace('元话费', '').replace('元', '') for fee in fees}
        unredeemed_fees = {fee.replace('元话费', '').replace('元', '') for fee in unredeemed_fees}
        redeemed_str = '-'.join(sorted(fees, key=lambda x: fee_order.index(x + '元话费') if x + '元话费' in fee_order else float('inf')))
        if unredeemed_fees:
            unredeemed_str = '-'.join(sorted(unredeemed_fees, key=lambda x: fee_order.index(x + '元话费') if x + '元话费' in fee_order else float('inf')))
        else:
            unredeemed_str = "全部兑换"
        table += f"<tr><td>{hidden_phone}</td><td>{redeemed_str}</td><td>{unredeemed_str}</td></tr>"
        
        for fee in fees:
            if fee in total_redeemed:
                total_redeemed[fee] += 1
        total_accounts += 1
        
        for fee in unredeemed_fees:
            total_unredeemed_amount += float(fee)
    
    total_amount = {fee: count * float(fee) for fee, count in total_redeemed.items()}
    total_sum = sum(total_amount.values())
    
    for fee, count in total_redeemed.items():
        amount = count * float(fee)
        unredeemed_amount = (total_accounts - count) * float(fee)
        table += f"<tr><td>{fee}元共{count}个</td><td>共得{amount:.1f}元</td><td>未得{unredeemed_amount:.1f}元</td></tr>"
    
    table += f"<tr><td>总共{total_accounts}个</td><td>共得{total_sum:.1f}元</td><td>未得{total_unredeemed_amount:.1f}元</td></tr>"
    
    total_5_and_10 = total_redeemed["5"] * 5 + total_redeemed["10"] * 10
    final_amount = total_5_and_10 / 2
    
    unredeemed_5_and_10 = (total_accounts - total_redeemed["5"]) * 5 + (total_accounts - total_redeemed["10"]) * 10
    unredeemed_final_amount = unredeemed_5_and_10 / 2
    
    table += f"<tr><td>总共赚得</td><td>共赚{final_amount:.1f}元</td><td>可赚{unredeemed_final_amount:.1f}元</td></tr>"
    
    table += "</table>"
    
    return table

# 获取当前日期
current_month = datetime.datetime.now().strftime("%Y%m")

# 获取当前日期
current_month2 = datetime.datetime.now().strftime("%m-%d")

# 将内容整理成HTML表格
final_content = format_as_html_table(data, current_month)

# 修改业务状态变更通知的变更类型
notification_content = f"""
<p class="summary-title">电信金豆兑换话费汇总 ({current_month})</p>
{final_content}
"""

# 设置通知栏标题和摘要
title = "电信推送"
summary = f"数据更新\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n金豆换话费\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n电信金豆兑换话费 ({current_month2})"

# 发送推送通知
response = send_wxpusher_notification(title, summary, notification_content)
if response.get("success"):
    logging.info("推送通知已发送")
    print("推送通知已发送")
else:
    logging.error(f"推送失败: {response.get('msg')}")
    print(f"推送失败: {response.get('msg')}")