import time
import requests
import datetime
import pytz
import json
import base64
import socket
from urllib.parse import urljoin
import pandas as pd
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
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

# 将校园服务域名解析到内网 IP，绕过 Clash fake-ip 劫持
# （TLS SNI 仍使用原域名，证书校验不受影响）
INTERNAL_IPS = {
    "oa.shanghaitech.edu.cn": "10.15.44.82",
    "ids.shanghaitech.edu.cn": "10.15.44.192",
}
_orig_getaddrinfo = socket.getaddrinfo

def _patched_getaddrinfo(host, port, *args, **kwargs):
    host = INTERNAL_IPS.get(host, host)
    return _orig_getaddrinfo(host, port, *args, **kwargs)

socket.getaddrinfo = _patched_getaddrinfo

OA_BASE_URL = "https://oa.shanghaitech.edu.cn"
LOGIN_ENTRY = f"{OA_BASE_URL}/workflow/request/AddRequest.jsp?workflowid=14862"


class LoginError(Exception):
    pass


def encrypt_password(password: str, salt: str) -> str:
    """CAS 登录密码加密：AES-CBC，key 为 pwdEncryptSalt，固定 IV"""
    prefix = b"Nu1L" * 16
    combined = prefix + password.encode()
    iv = b"Nu1LNu1LNu1LNu1L"
    key = salt.encode()
    encrypted = AES.new(key, AES.MODE_CBC, iv).encrypt(pad(combined, AES.block_size))
    return base64.b64encode(encrypted).decode()


def _collect_data(html: str, name: str, end_tag: str = "/>") -> str:
    """从 CAS 登录页 HTML 中提取隐藏字段的 value"""
    start = html.find(f'id="{name}"') if name == "pwdEncryptSalt" else html.find(f'name="{name}"')
    if start == -1:
        return ""
    end = html.find(end_tag, start)
    raw = html[start:end]
    value_start = raw.find('value="') + 7
    value_end = raw.find('"', value_start)
    return raw[value_start:value_end]


def login_oa(student_id: str, password: str) -> str:
    """通过学校 CAS 统一认证登录 OA 系统，返回 shkjdx_session 的值"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    })

    # 访问 OA 受保护页面，被重定向到 CAS 登录页
    resp = session.get(LOGIN_ENTRY, allow_redirects=False, timeout=30)
    if not (300 <= resp.status_code < 400):
        raise LoginError(f"OA入口未返回重定向，状态码 {resp.status_code}")

    for _ in range(10):
        resp = session.get(urljoin(resp.url, resp.headers["Location"]),
                           allow_redirects=False, timeout=30)
        if resp.status_code == 200:
            break
        if not (300 <= resp.status_code < 400):
            raise LoginError(f"重定向链中断，状态码 {resp.status_code}")

    ids_html = resp.text
    salt = _collect_data(ids_html, "pwdEncryptSalt")
    execution = _collect_data(ids_html, "execution")
    lt = _collect_data(ids_html, "lt")
    if not salt or not execution:
        raise LoginError("未能从CAS登录页提取 pwdEncryptSalt/execution")

    # 提交登录表单
    form_data = {
        "username": student_id,
        "password": encrypt_password(password, salt),
        "lt": lt,
        "dllt": "generalLogin",
        "execution": execution,
        "_eventId": "submit",
        "rmShown": "1",
    }
    post_resp = session.post(resp.url, data=form_data, allow_redirects=False, timeout=30)

    # 跟随重定向回到 OA，session 自动携带种下的 cookie
    for _ in range(10):
        if not (300 <= post_resp.status_code < 400):
            break
        post_resp = session.get(urljoin(post_resp.url, post_resp.headers.get("Location", "")),
                                allow_redirects=False, timeout=30)

    if any(k in post_resp.text for k in ("authError", "用户名或密码", "incorrectPassword")):
        raise LoginError("用户名或密码错误")

    session_value = session.cookies.get("shkjdx_session")
    if not session_value:
        raise LoginError("登录流程结束但未拿到 shkjdx_session cookie")
    return session_value


# 执行 CAS 登录
session_value = None
try:
    session_value = login_oa(username, password)
    ic(session_value[:20] + "...")  # 只显示session值的前20个字符
    console.print(f"[green]✓ CAS登录成功，已获取session[/green]")
except Exception as e:
    console.print(f"[red]✗ 登录流程出现异常: {e}[/red]")

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