import email
import imaplib
import re
import time


def fetch_latest_email_otp(
    personal_email: str = "805559297@qq.com",
    auth_code: str = "ucsmhjdaxhvwbcge",
    imap_server: str = "imap.qq.com",  # 若为 163 邮箱则填 imap.163.com
) -> str:
  """从个人邮箱秒级提取转发过来的宝尊 6 位验证码"""
  try:
    mail = imaplib.IMAP4_SSL(imap_server, 993)
    mail.login(personal_email, auth_code)
    mail.select("INBOX")

    # 获取最新 3 条邮件
    _, search_data = mail.search(None, "ALL")
    mail_ids = search_data[0].split()[-3:]

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
            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

          # 正则匹配 6 位数字验证码
          if "验证码" in body or "UAC" in body or "宝尊" in body:
            codes = re.findall(r"\b\d{6}\b", body)
            if codes:
              mail.logout()
              return codes[0]

    mail.logout()
  except Exception as e:
    print(f"提取验证码异常: {e}")

  return ""
