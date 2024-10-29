import requests
import datetime
import pytz
import json
import pandas as pd
import time

def post_request():
    
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
    
    # 场地信息列表
    venues = [
        {"pid": "63_6", "name": "\u5ba4\u5185\u7fbd\u6bdb\u7403\u573a", "display_name": "🏸羽毛球场", "url":"https://oa.shanghaitech.edu.cn/formmode/tree/treebrowser/CustomTreeBrowserAjax.jsp?dataconditionParam=_sfn_31901_sfv_{}_sfn_31902_sfv_{}_sfn_32340_sfv_4&id=63"},
        {"pid": "63_7", "name": "\u5ba4\u5185\u4e52\u4e53\u7403\u573a", "display_name": "🏓乒乓球场", "url":"https://oa.shanghaitech.edu.cn/formmode/tree/treebrowser/CustomTreeBrowserAjax.jsp?dataconditionParam=_sfn_31901_sfv_{}_sfn_31902_sfv_{}_sfn_32340_sfv_4&id=63"},
        {"pid": "63_8", "name": "%E5%AE%A4%E5%A4%96%E7%BD%91%E7%90%83%E5%9C%BA", "display_name": "🎾网球场", "url":"https://oa.shanghaitech.edu.cn/formmode/tree/treebrowser/CustomTreeBrowserAjax.jsp?dataconditionParam=_sfn_31901_sfv_{}_sfn_31902_sfv_{}_sfn_32340_sfv_6&id=63"}
    ]
    
    # 时间段列表
    time_slots = [
        "11:00-12:00", "12:00-13:00", "13:00-14:00", "14:00-15:00", "15:00-16:00",
        "16:00-17:00", "17:00-18:00", "18:00-19:00", "19:00-20:00", "20:00-21:00", "21:00-22:00"
    ]
    
    # 创建一个DataFrame来存储所有场地的空闲时间段
    availability_tables = {}
    
    # 请求每个场地从今天开始的5天
    for venue in venues:
        availability_table = pd.DataFrame(columns=["Date"] + time_slots)
        
        for i in range(2):
            request_date = today + datetime.timedelta(days=i + 1)
            formatted_date = request_date.strftime("%Y-%m-%d")
            availability = {"Date": formatted_date}

            # 遍历每个时间段
            for index, time_slot in enumerate(time_slots):
                url = venue["url"].format(formatted_date, index + 2)  # sfv_2_sfn字段对应时间段的index
                try:
                    # 发送的数据
                    data = {
                        "pid": venue["pid"],
                        "name": venue["name"]
                    }
                    
                    response = requests.post(url, headers=headers, data=data, cookies={"shkjdx_session": session_value}, timeout=2)
                    time.sleep(0.1)
                    response.raise_for_status()  # 检查请求是否成功
                    response.encoding = 'utf-8'
                    res = response.text.strip()
                    res = json.loads(res)
                    
                    # 判断该时间段是否有空位
                    if len(res)>0 and venue["pid"] != res[0]["id"]:
                        availability[time_slot] = "有"
                    else:
                        availability[time_slot] = ""
                except requests.exceptions.RequestException as e:
                    print(f"An error occurred for venue {venue['display_name']}, date {formatted_date}, time slot {time_slot}:", e)
                    availability[time_slot] = "Error"
            
            # 将当天的空闲情况添加到表格中
            availability_table.loc[len(availability_table)] = availability
        
        # 将该场地的空闲情况表格保存到字典中
        availability_tables[venue["display_name"]] = availability_table
    
    # 输出所有场地的空闲时间段表格
    for venue_name, table in availability_tables.items():
        print(f"\n接下来几天的{venue_name}空闲时间段如下:")
        print(table.transpose().to_markdown(index=True))
    
    input("按回车键退出......")

if __name__ == "__main__":
    post_request()
