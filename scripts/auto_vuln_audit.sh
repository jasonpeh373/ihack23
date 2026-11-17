#!/bin/bash
# ==============================================================================
# 【Root 专用：全自动漏洞与后门扫描器 (Web 源码 + Pwn 二进制 + 系统后门)】
# 用法：在自己靶机以 root 运行: bash auto_vuln_audit.sh [Web目录，默认 /var/www/html]
# ==============================================================================

WEB_DIR="${1:-/var/www/html}"

echo "======================================================================"
echo " [1] 当前靶机开放的端口与对应的服务程序 (重点看哪些是比赛题目)"
echo "======================================================================"
ss -tulpn 2>/dev/null || netstat -tulpn 2>/dev/null

echo ""
echo "======================================================================"
echo " [2] 系统后门与权限配置审计 (SSH公钥 / 隐藏root账号 / 定时任务 / SUID)"
echo "======================================================================"
echo "--- (2.1) 可登录系统的账号 (/bin/bash 或 /bin/sh) ---"
grep -E "(/bin/bash|/bin/sh|/bin/zsh)$" /etc/passwd

echo "--- (2.2) UID=0 的特权账号 (除 root 外若有其他均为后门!) ---"
awk -F: '($3 == 0) {print $1}' /etc/passwd

echo "--- (2.3) 已配置的 SSH 免密公钥 (检查是否有出题人预留公钥) ---"
head -n 20 /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys 2>/dev/null

echo "--- (2.4) 系统定时任务 (检查是否有定时执行的恶意脚本) ---"
crontab -l 2>/dev/null
grep -vE "^(#|$)" /etc/crontab /etc/cron.d/* /var/spool/cron/crontabs/* 2>/dev/null

echo "--- (2.5) 异常 SUID 提权文件 ---"
find / -perm -4000 -type f 2>/dev/null | grep -vE "^/usr/bin/(sudo|passwd|gpasswd|chsh|chfn|newgrp|mount|umount|su)|^/bin/(su|mount|umount|ping)"

echo ""
echo "======================================================================"
echo " [3] Web 源码高危漏洞自动定位 (目录: $WEB_DIR)"
echo "======================================================================"
if [ -d "$WEB_DIR" ]; then
    echo "--- 🔴 [高危 1: 命令执行 & 一句话木马 (RCE / Webshell)] ---"
    grep -rnE --color=always "(eval|system|passthru|shell_exec|exec|popen|proc_open|pcntl_exec|assert)\s*\(" "$WEB_DIR" 2>/dev/null | head -n 30

    echo ""
    echo "--- 🟠 [高危 2: 任意文件包含 / 任意文件读取 (LFI / File Read)] ---"
    grep -rnE --color=always "(include|include_once|require|require_once|file_get_contents|readfile|highlight_file|show_source)\s*\(.*\\\$_(GET|POST|REQUEST|COOKIE)" "$WEB_DIR" 2>/dev/null | head -n 30

    echo ""
    echo "--- 🟡 [高危 3: 任意文件上传 / 文件写入 (File Upload / Write)] ---"
    grep -rnE --color=always "(move_uploaded_file|file_put_contents|fwrite)\s*\(" "$WEB_DIR" 2>/dev/null | head -n 30

    echo ""
    echo "--- 🔵 [高危 4: 反序列化漏洞 (Deserialization)] ---"
    grep -rnE --color=always "(unserialize|pickle\.loads|yaml\.load)\s*\(" "$WEB_DIR" 2>/dev/null | head -n 20

    echo ""
    echo "--- 🟣 [高危 5: SQL 注入直接拼接变量 (SQL Injection)] ---"
    grep -rnEi --color=always "(select|insert|update|delete).*where.*\\\$_(GET|POST|REQUEST)" "$WEB_DIR" 2>/dev/null | head -n 30

    echo ""
    echo "--- ⚪ [高危 6: Python Flask / Node.js 常见命令执行与模板注入] ---"
    grep -rnE --color=always "(os\.system|os\.popen|subprocess\.|render_template_string|child_process)" "$WEB_DIR" 2>/dev/null | head -n 20
else
    echo "[-] 未找到 $WEB_DIR，如果 Web 目录在其他位置（如 /app 或 /opt），请运行: bash $0 /真实路径"
fi

echo ""
echo "======================================================================"
echo " [4] Pwn 题目二进制文件快速排查 (/home, /opt, /root, /srv)"
echo "======================================================================"
for bin in $(find /home /opt /srv /root -maxdepth 3 -type f -executable 2>/dev/null | grep -vE "\.(sh|py|php|pl|js)$"); do
    if file "$bin" 2>/dev/null | grep -q "ELF"; then
        echo "[*] 发现 ELF 二进制程序: $bin"
        echo "    危险函数/后门字符串: $(strings "$bin" 2>/dev/null | grep -E '^(gets|strcpy|sprintf|system|execve|/bin/sh|/bin/bash|cat .*flag)$' | tr '\n' ' ')"
    fi
done

