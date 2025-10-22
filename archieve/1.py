import requests
import datetime
import pytz
import json
import pandas as pd
import time
import webbrowser

Version="v1.2"
print(f"当前版本 {Version}")


def get_latest_tag():
    # GitHub API URL
    url = "https://gh-proxy.com/api.github.com/repos/arnoliudaxia/ShanghaiTech-gymBook/tags"

    # 设置请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
    }

    # 发送 GET 请求
    response = requests.get(url, headers=headers, timeout=2)

    # 检查请求是否成功
    if response.status_code == 200:
        tags = response.json()
        if tags:
            # 返回最新的标签
            return tags[0]['name']
        else:
            return "没有找到标签"
    else:
        return f"请求失败，状态码: {response.status_code}"

def check_for_update(current_version, latest_version):
    # 比较版本号
    if current_version != latest_version:
        print(f"有新版本可用: {latest_version}")
        # 打开 GitHub Releases 页面
        webbrowser.open(f"https://github.com/arnoliudaxia/ShanghaiTech-gymBook/releases/tag/{latest_version}")
    else:
        print("当前版本是最新的。")

# 获取最新标签
latest_tag = get_latest_tag()

# 检查是否需要更新
if latest_tag and "请求失败" not in latest_tag:
    check_for_update(Version, latest_tag)
else:
    webbrowser.open(f"https://github.com/arnoliudaxia/ShanghaiTech-gymBook/releases/tag/{latest_tag}")


def post_request():
    
    # 获取今天的日期（UTC+8时区）
    tz = pytz.timezone('Asia/Shanghai')
    today = datetime.datetime.now(tz).date()

    # 让用户输入 shkjdx_session 的值
    url = "https://oa.shanghaitech.edu.cn/workflow/request/AddRequest.jsp?workflowid=14862"
    webbrowser.open(url)
    session_value = input(f"请访问 {url} 并输入 shkjdx_session (cookie) 的值: ")

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
        {"pid": "63_8", "name": "%E5%AE%A4%E5%A4%96%E7%BD%91%E7%90%83%E5%9C%BA", "display_name": "🎾网球场", "url":"https://oa.shanghaitech.edu.cn/formmode/tree/treebrowser/CustomTreeBrowserAjax.jsp?dataconditionParam=_sfn_31901_sfv_{}_sfn_31902_sfv_{}_sfn_32340_sfv_6&id=63"},
        {"pid": "63_64", "name": "%E5%8C%B9%E5%85%8B%E7%90%83%E5%9C%BA", "display_name": "🥎匹克球", "url":"https://oa.shanghaitech.edu.cn/formmode/tree/treebrowser/CustomTreeBrowserAjax.jsp?dataconditionParam=_sfn_31901_sfv_{}_sfn_31902_sfv_{}_sfn_32340_sfv_11&id=63"}
    ]
    
    # 时间段列表
    time_slots = [
        "11:00-12:00", "12:00-13:00", "13:00-14:00", "14:00-15:00", "15:00-16:00",
        "16:00-17:00", "17:00-18:00", "18:00-19:00", "19:00-20:00", "20:00-21:00", "21:00-22:00"
    ]

    for venue in venues:
        # 创建一个DataFrame来存储所有场地的空闲时间段
        availability_table = pd.DataFrame(columns=["Date"] + time_slots)
        
        for i in range(3): # 只能看后两天的
            request_date = today  + datetime.timedelta(days=i)
            formatted_date = request_date.strftime("%Y-%m-%d")
            availability = {"Date": formatted_date}

            # 遍历每个时间段
            for index, time_slot in enumerate(time_slots):
                url = venue["url"].format(formatted_date, index + 1)  # sfv_2_sfn字段对应时间段的index
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

        print(f"\n接下来几天的{venue['display_name']}空闲时间段如下:")
        print(availability_table.transpose().to_markdown(index=True))

    
    input("按回车键退出......")

if __name__ == "__main__":
    post_request()
