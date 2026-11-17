#!/bin/bash
# ==============================================================================
# 【纯 Web Log 实时监控脚本】
# 用法：在自己靶机运行: bash simple_monitor.sh [Web目录，默认 /var/www/html]
# ==============================================================================

WEB_DIR="${1:-/var/www/html}"
touch /tmp/web_post.log
chmod 666 /tmp/web_post.log

# 1. 自动挂载 PHP 请求日志钩子（为了在日志里也能看到别人发过来的 POST 参数）
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

# 2. 实时滚动显示所有 Web 日志 (Apache / Nginx / Lighttpd / PHP POST 日志)
echo "==================== 正在实时监控所有 Web Log (按 Ctrl+C 停止) ===================="
tail -f /tmp/web_post.log /var/log/apache2/*access*.log /var/log/nginx/*access*.log /var/log/httpd/*access*.log /var/log/lighttpd/*access*.log 2>/dev/null
