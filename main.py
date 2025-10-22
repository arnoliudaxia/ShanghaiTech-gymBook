import time
import requests
import datetime
import pytz
import json
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
import os
from icecream import ic
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

# 配置icecream
ic.configureOutput(prefix='🔍 调试 | ')

# 创建Rich控制台
console = Console()

# 加载环境变量
load_dotenv()

# 从环境变量中获取用户名和密码
username = os.getenv("MYUSERNAME")
password = os.getenv("PASSWORD")

# 设置Chrome选项
chrome_options = Options()
chrome_options.add_argument("--headless")  # 无头模式
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
# chrome_options.add_argument("--disable-dev-shm-usage")  # 解决资源限制问题
# chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # 避免被检测为自动化
# chrome_options.add_argument(f"--user-data-dir=/tmp/chrome_user_data_{os.getpid()}")  # 使用唯一的用户数据目录

# 启动Chrome浏览器
driver = webdriver.Chrome(options=chrome_options)

try:
    # 打开登录页面
    driver.get("https://oa.shanghaitech.edu.cn/workflow/request/AddRequest.jsp?workflowid=14862")

    # 输入用户名
    username_input = driver.find_element(By.ID, "username")
    username_input.send_keys(username)

    # 输入密码
    password_input = driver.find_element(By.ID, "password")
    password_input.send_keys(password)
    password_input.send_keys(Keys.RETURN)

    # 等待页面加载
    time.sleep(5)

    # 获取cookie中的shkjdx_session的值
    session_value = None
    cookies = driver.get_cookies()
    for cookie in cookies:
        if cookie['name'] == 'shkjdx_session':
            session_value = cookie['value']
            ic(session_value)
            console.print(f"[green]✓ 成功获取session: {session_value[:20]}...[/green]")
            break

finally:
    # 关闭浏览器
    driver.quit()

# 如果成功获取到session_value，继续获取场地空闲信息
if session_value:
    # 获取今天的日期（UTC+8时区）
    tz = pytz.timezone('Asia/Shanghai')
    today = datetime.datetime.now(tz).date()

    # POST请求头信息
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/plain, */*; q=0.01",
        "User-Agent": "Mozilla/5.0"
    }

    # 场地信息列表
    venues = [
        {"pid": "63_6", "name": "\u5ba4\u5185\u7fbd\u6bdb\u7403\u573a", "display_name": "🏸羽毛球场", "url": "https://oa.shanghaitech.edu.cn/formmode/tree/treebrowser/CustomTreeBrowserAjax.jsp?dataconditionParam=_sfn_31901_sfv_{}_sfn_31902_sfv_{}_sfn_32340_sfv_4&id=63"},
        {"pid": "63_7", "name": "\u5ba4\u5185\u4e52\u4e53\u7403\u573a", "display_name": "🏓乒乓球场", "url": "https://oa.shanghaitech.edu.cn/formmode/tree/treebrowser/CustomTreeBrowserAjax.jsp?dataconditionParam=_sfn_31901_sfv_{}_sfn_31902_sfv_{}_sfn_32340_sfv_4&id=63"},
        {"pid": "63_8", "name": "%E5%AE%A4%E5%A4%96%E7%BD%91%E7%90%83%E5%9C%BA", "display_name": "🎾网球场", "url": "https://oa.shanghaitech.edu.cn/formmode/tree/treebrowser/CustomTreeBrowserAjax.jsp?dataconditionParam=_sfn_31901_sfv_{}_sfn_31902_sfv_{}_sfn_32340_sfv_6&id=63"},
        {"pid": "63_64", "name": "%E5%8C%B9%E5%85%8B%E7%90%83%E5%9C%BA", "display_name": "🥎匹克球", "url": "https://oa.shanghaitech.edu.cn/formmode/tree/treebrowser/CustomTreeBrowserAjax.jsp?dataconditionParam=_sfn_31901_sfv_{}_sfn_31902_sfv_{}_sfn_32340_sfv_11&id=63"}
    ]

    # 时间段列表
    time_slots = [
        "11:00-12:00", "12:00-13:00", "13:00-14:00", "14:00-15:00", "15:00-16:00",
        "16:00-17:00", "17:00-18:00", "18:00-19:00", "19:00-20:00", "20:00-21:00", "21:00-22:00"
    ]

    # 创建data目录用于存储输出文件
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    
    for venue in venues:
        # 创建一个DataFrame来存储所有场地的空闲时间段
        availability_table = pd.DataFrame(columns=["Date"] + time_slots)

        for i in range(3):  # 只能看后两天的
            request_date = today + datetime.timedelta(days=i)
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
                    if len(res) > 0 and venue["pid"] != res[0]["id"]:
                        availability[time_slot] = "有"
                    else:
                        availability[time_slot] = ""
                except requests.exceptions.RequestException as e:
                    console.print(f"[red]✗ 错误: 场地 {venue['display_name']}, 日期 {formatted_date}, 时间段 {time_slot}: {e}[/red]")
                    availability[time_slot] = "Error"

            # 将当天的空闲情况添加到表格中
            availability_table.loc[len(availability_table)] = availability

        # 使用Rich创建美化的表格
        console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
        console.print(Panel(f"[bold yellow]{venue['display_name']} 空闲时间段查询结果[/bold yellow]",
                           style="bold magenta"))
        
        # 创建Rich表格
        table = Table(show_header=True, header_style="bold magenta",
                     title=f"{venue['display_name']} 未来3天空闲情况",
                     title_style="bold cyan")
        
        # 添加列：第一列是时间段，后续列是日期
        table.add_column("时间段", style="cyan", width=12)
        for date in availability_table["Date"]:
            table.add_column(date, justify="center", style="yellow")
        
        # 添加行：每行是一个时间段，显示各日期的空闲情况
        for time_slot in time_slots:
            row_data = [time_slot]
            for _, row in availability_table.iterrows():
                val = row[time_slot]
                if val == "有":
                    row_data.append("[green]✓ 有空位[/green]")
                elif val == "Error":
                    row_data.append("[red]✗ 错误[/red]")
                else:
                    row_data.append("[dim]—[/dim]")
            table.add_row(*row_data)
        
        console.print(table)
        console.print(f"[bold cyan]{'='*60}[/bold cyan]\n")
        
        # 保存DataFrame到CSV文件
        # 生成安全的文件名(移除emoji和特殊字符)
        safe_venue_name = venue['display_name'].strip()
        if not safe_venue_name:
            # 如果移除emoji后为空,使用原始name字段
            safe_venue_name = venue['name']
        
        # 保存为CSV格式(直接覆盖旧文件)
        csv_filename = os.path.join(output_dir, f"{safe_venue_name}.csv")
        availability_table.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        console.print(f"[green]✓ 已保存CSV文件: {csv_filename}[/green]")