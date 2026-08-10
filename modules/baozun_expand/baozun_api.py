import email
import imaplib
import json
import os
import re
import time
from playwright.sync_api import sync_playwright
import requests

# 本地 Cookie 缓存路径
COOKIE_CACHE_FILE = os.path.join(
    os.path.dirname(__file__), "baozun_cookie_cache.json"
)


def parse_cookie_string(cookie_str: str) -> dict:
  """解析 Cookie 字符串为字典格式"""
  cookies = {}
  if not cookie_str:
    return cookies
  for item in cookie_str.split(";"):
    if "=" in item:
      key, val = item.strip().split("=", 1)
      cookies[key.strip()] = val.strip()
  return cookies


class BaozunAccountAPI:

  def __init__(
      self,
      username: str = "JM038153",  # 填入您的宝尊账号
      password: str = "Xl@20177",  # 填入您的宝尊密码
      qq_email: str = "805559297@qq.com",  # 填入您的 QQ 邮箱
      qq_auth_code: str = "ucsmhjdaxhvwbcge",  # 填入 QQ 邮箱 IMAP 授权码
      imap_server: str = "imap.qq.com",
  ):
    self.username = username
    self.password = password
    self.qq_email = qq_email
    self.qq_auth_code = qq_auth_code
    self.imap_server = imap_server
    self.login_url = "https://account-dop.baozun.com/login?redirectUrl=https%3A%2F%2Fross.baozun.com&appkey=ross-modern-api&lang=zh_CN"

  def fetch_latest_email_otp(
      self, timeout: int = 60, poll_interval: int = 3
  ) -> str:
    """从 QQ 邮箱秒级提取 Outlook 自动转发过来的宝尊 6 位验证码"""
    start_time = time.time()

    while time.time() - start_time < timeout:
      try:
        mail = imaplib.IMAP4_SSL(self.imap_server, 993)
        mail.login(self.qq_email, self.qq_auth_code)
        mail.select("INBOX")

        _, search_data = mail.search(None, "ALL")
        mail_ids = search_data[0].split()[-5:]

        for mail_id in reversed(mail_ids):
          _, msg_data = mail.fetch(mail_id, "(RFC822)")
          for response_part in msg_data:
            if isinstance(response_part, tuple):
              msg = email.message_from_bytes(response_part)

              body = ""
              if msg.is_multipart():
                for part in msg.walk():
                  if part.get_content_type() in ["text/plain", "text/html"]:
                    body += part.get_payload(decode=True).decode(
                        "utf-8", errors="ignore"
                    )
              else:
                body = msg.get_payload(decode=True).decode(
                    "utf-8", errors="ignore"
                )

              if "验证码" in body or "UAC" in body or "宝尊" in body:
                codes = re.findall(r"\b\d{6}\b", body)
                if codes:
                  mail.logout()
                  return codes[0]

        mail.logout()
      except Exception as e:
        print(f"自动提取验证码中: {e}")

      time.sleep(poll_interval)

    raise TimeoutError("读取验证码超时，请确认 Outlook 自动转发配置")

  def login_and_get_cookie_str(self) -> str:
    """用 Playwright 在后台精准模拟多层登录页面，自动提取 Cookie"""
    print("[后台自动登录] 正在启动后台浏览器执行登录...")
    with sync_playwright() as p:
      # 启动后台无头浏览器（不弹窗）
      browser = p.chromium.launch(
          headless=True,
          args=["--no-sandbox", "--disable-setuid-sandbox"],
      )
      context = browser.new_context()
      page = context.new_page()

      try:
        # 1. 打开宝尊 dop 登录统一入口
        page.goto(self.login_url, timeout=30000)
        page.wait_for_load_state("networkidle")

        # 2. 填写账号与密码
        page.fill(
            'input[type="text"], input[placeholder*="账号"],'
            ' input[placeholder*="用户名"]',
            self.username,
        )
        page.fill('input[type="password"]', self.password)

        # 点击登录按钮提交
        page.click(
            'button:has-text("登录"), input[type="submit"],'
            ' .el-button--primary'
        )
        time.sleep(2)

        # 3. 如果需要验证码，自动点击发送验证码按钮
        send_code_btn = page.query_selector(
            'button:has-text("验证码"), button:has-text("发送"),'
            ' :text("获取验证码")'
        )
        if send_code_btn:
          send_code_btn.click()
          time.sleep(2)

        # 4. 从 QQ 邮箱自动拿验证码
        print("[后台自动登录] 正在等待 Outlook 转发验证码邮件...")
        otp_code = self.fetch_latest_email_otp(timeout=45)
        print(f"[后台自动登录] 成功获取到验证码: {otp_code}")

        # 5. 自动填入验证码并确认
        page.fill(
            'input[placeholder*="验证码"], input[name*="code"]', otp_code
        )
        page.click(
            'button:has-text("确定"), button:has-text("登录"),'
            ' button:has-text("提交")'
        )

        # 6. 等待成功跳转
        time.sleep(3)

        # 7. 提取 Cookies
        cookies = context.cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

        browser.close()

        # 缓存到本地
        self.save_cached_cookie(cookie_str)
        print("[后台自动登录] 登录成功，已更新宝尊鉴权 Cookie！")
        return cookie_str

      except Exception as e:
        browser.close()
        raise RuntimeError(f"Playwright 后台自动登录失败: {str(e)}")

  def get_valid_cookie(self) -> str:
    """对外入口：优先使用本地缓存 Cookie，失效时才自动启动后台无头浏览器登录"""
    cached_cookie = self.load_cached_cookie()
    if cached_cookie and self.check_cookie_valid(cached_cookie):
      return cached_cookie

    return self.login_and_get_cookie_str()

  def check_cookie_valid(self, cookie_str: str) -> bool:
    """校验 Cookie 是否依然具备请求权限"""
    try:
      headers = {
          "Cookie": cookie_str,
          "User-Agent": (
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          ),
      }
      resp = requests.get(
          "https://union-gateway.baozun.com/iforce/art/image/getImageExpand",
          params={"recordCode": "test"},
          headers=headers,
          timeout=5,
      )
      if resp.status_code == 200 and "UAAC" not in resp.text:
        return True
    except Exception:
      pass
    return False

  def save_cached_cookie(self, cookie_str: str):
    try:
      with open(COOKIE_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({"cookie": cookie_str, "update_time": time.time()}, f)
    except Exception:
      pass

  def load_cached_cookie(self) -> str:
    if os.path.exists(COOKIE_CACHE_FILE):
      try:
        with open(COOKIE_CACHE_FILE, "r", encoding="utf-8") as f:
          data = json.load(f)
          return data.get("cookie", "")
      except Exception:
        pass
    return ""
