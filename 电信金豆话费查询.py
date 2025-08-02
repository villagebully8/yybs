"""
cron: 00 20 * * *
new Env('电信金豆话费获取查询');
"""
"""
使用方法：
    啥也不用设置，调用的面板配置的推送
"""
import json
from collections import defaultdict
import sys
import os  # 导入os模块用于检查文件是否存在


# 控制变量，用于控制是否发送通知
enable_notification = 1  # 0 不发送     1发送通知

# 如果需要发送通知，则尝试导入notify模块
if enable_notification:
    try:
        from notify import send
    except ModuleNotFoundError:
        print("警告：未找到notify.py模块。程序将退出。")
        sys.exit(1)

# 定义日志文件路径
log_file_path = '电信金豆换话费.log'

# 检查日志文件是否存在
if not os.path.exists(log_file_path):
    print("垃圾都没中，还统计个锤子")
    sys.exit(0)

# 读取日志数据
def read_log_data(log_file_path):
    try:
        with open(log_file_path, 'r', encoding='utf-8') as file:
            log_data = json.load(file)
        return log_data
    except Exception as e:
        print(f"读取日志数据时发生错误: {e}")
        return None

# 格式化日志输出
def generate_log_output(log_data):
    log_lines = []
    
    # 遍历每个月的数据
    for month, fees in log_data.items():
        log_lines.append(f"--- {month} ---")  # 分割线，标识月份
        
        # 收集每个手机号获得的所有话费类型
        phone_to_fees = defaultdict(set)
        
        for fee_type, phones in fees.items():
            # 获取手机号列表
            phone_numbers = phones.strip('#').split('#') if phones else []
            
            # 格式化输出日志行
            if phone_numbers:
                log_line = f"{fee_type} : " + ", ".join(phone_numbers)
                for phone in phone_numbers:
                    phone_to_fees[phone].add(fee_type)  # 记录手机号对应的所有话费类型
            else:
                log_line = f"{fee_type} : 还没有中的哦"
            
            log_lines.append(log_line)
        
        # 添加每个月的手机号统计信息
        log_lines.append("统计信息：")
        for phone, fee_types in phone_to_fees.items():
            log_lines.append(f"{phone} 中了: {', '.join(fee_types)}")
        
        log_lines.append("")  # 每个月份后添加空行，分隔月份数据
    
    # 返回生成的日志内容
    return "\n".join(log_lines)

# 获取日志内容
def get_log_content():
    log_data = read_log_data(log_file_path)
    if log_data:
        log_content = generate_log_output(log_data)
        return log_content
    return None

# 调用函数获取日志内容
log_content = get_log_content()

# 如果获取到日志内容，则打印或者推送
if log_content:
    print(log_content)  # 在这里输出日志，您可以修改为推送日志的代码
    send('电信当月兑换统计', log_content)