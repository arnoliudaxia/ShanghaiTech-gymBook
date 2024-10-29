import requests
import datetime
import pytz
import json
import pandas as pd

def post_request():
    base_url = "https://oa.shanghaitech.edu.cn/formmode/tree/treebrowser/CustomTreeBrowserAjax.jsp?dataconditionParam=_sfn_31901_sfv_{}_sfn_31902_sfv_{}_sfn_32340_sfv_4&id=63"
    
    # 获取今天的日期（UTC+8时区）
    tz = pytz.timezone('Asia/Shanghai')
    today = datetime.datetime.now(tz).date()
    
    # 让用户输入 shkjdx_session 的值
    session_value = input("请输入 shkjdx_session 的值: ")
    
    # POST请求头信息
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/plain, */*; q=0.01",
        "User-Agent":"Mozilla/5.0"
    }
    
    # 发送的数据
    data = {
        "pid": "63_6",
        "name": "\u5ba4\u5185\u7fbd\u6bdb\u7403\u573a"  # 室内羽毛球场的Unicode编码
    }
    
    # 时间段列表
    time_slots = [
        "11:00-12:00", "12:00-13:00", "13:00-14:00", "14:00-15:00", "15:00-16:00",
        "16:00-17:00", "17:00-18:00", "18:00-19:00", "19:00-20:00", "20:00-21:00", "21:00-22:00"
    ]
    
    # 创建一个DataFrame来存储空闲时间段
    availability_table = pd.DataFrame(columns=["Date"] + time_slots)
    
    # 请求从今天开始的5天
    for i in range(5):
        request_date = today + datetime.timedelta(days=i + 1)
        formatted_date = request_date.strftime("%Y-%m-%d")
        availability = {"Date": formatted_date}

        # 遍历每个时间段
        for index, time_slot in enumerate(time_slots):
            url = base_url.format(formatted_date, index + 2)  # sfv_2_sfn字段对应时间段的index
            try:
                response = requests.post(url, headers=headers, data=data, cookies={"shkjdx_session": session_value}, timeout=1000)
                response.raise_for_status()  # 检查请求是否成功
                response.encoding = 'utf-8'
                res = response.text.strip()
                res = json.loads(res)
                
                # 判断该时间段是否有空位
                if len(res) > 0 and "羽毛球场地" in res[0]["name"]:
                    availability[time_slot] = "有"
                else:
                    availability[time_slot] = ""
            except requests.exceptions.RequestException as e:
                print(f"An error occurred for date {formatted_date}, time slot {time_slot}:", e)
                availability[time_slot] = "Error"
        
        # 将当天的空闲情况添加到表格中
        availability_table = availability_table.append(availability, ignore_index=True)
    
    # 输出空闲时间段表格
    print("\n接下来几天的羽毛球场空闲时间段如下:")
    print(availability_table.transpose().to_markdown(index=True))

if __name__ == "__main__":
    post_request()
