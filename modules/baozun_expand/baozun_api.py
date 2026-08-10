import time
import requests


def _safe_get(obj, key, default=None):
  """安全字段提取工具，防止对字符串等非字典类型调用 .get() 导致报错"""
  if isinstance(obj, dict):
    return obj.get(key, default)
  return default


class BaozunExpandAPI:

  def __init__(
      self,
      base_url: str = "https://union-gateway.baozun.com",
      cookies: dict = None,
      headers: dict = None,
  ):
    self.base_url = base_url.rstrip("/")
    self.session = requests.Session()

    default_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    }
    if headers:
      default_headers.update(headers)
    self.session.headers.update(default_headers)

    if cookies:
      self.session.cookies.update(cookies)

  def upload_image(self, file_bytes: bytes, filename: str) -> str:
    """1. 上传图片到宝尊节点，获取 originalAttachmentCode"""
    possible_urls = [
        f"{self.base_url}/iforce/art/image/upload/rename",
        f"{self.base_url}/iforce/art/image/upload",
        f"{self.base_url}/iforce/art/upload/rename",
        f"{self.base_url}/upload/rename",
    ]

    headers = {
        k: v for k, v in self.session.headers.items() if k.lower() != "content-type"
    }
    files = {"file": (filename, file_bytes)}

    attempt_logs = []
    for url in possible_urls:
      try:
        resp = self.session.post(
            url, files=files, headers=headers, timeout=15
        )
        if resp.status_code == 200:
          try:
            res_data = resp.json()
          except Exception:
            res_data = resp.text.strip().strip('"')

          # 1.1 如果接口直接返回字符串 Code
          if isinstance(res_data, str) and res_data.strip():
            return res_data.strip().strip('"')

          # 1.2 如果接口返回 JSON 字典
          elif isinstance(res_data, dict):
            data = res_data.get("data")
            if isinstance(data, str) and data.strip():
              return data.strip().strip('"')

            code = (
                _safe_get(data, "originalAttachmentCode")
                or _safe_get(res_data, "originalAttachmentCode")
                or _safe_get(res_data, "code")
            )
            if code:
              return str(code)

            attempt_logs.append(f"[{url}] JSON 字典未包含 Code: {res_data}")
        else:
          attempt_logs.append(f"[{url}] HTTP状态码 {resp.status_code}")
      except Exception as e:
        attempt_logs.append(f"[{url}] 请求失败: {str(e)}")

    raise ValueError(
        "所有上传接口路由均未成功返回附件 Code。详细日志: "
        + " | ".join(attempt_logs)
    )

  def submit_image_expand(
      self,
      original_attachment_code: str,
      top_distance: int = 140,
      bottom_distance: int = 140,
      left_distance: int = 205,
      right_distance: int = 205,
      background_weight: int = 800,
      background_height: int = 800,
      original_weight: int = 390,
      original_height: int = 520,
      generated_num: int = 4,
      ratio: str = "free",
      prompt: str = "",
  ) -> str:
    """2. 提交扩图任务，获取 recordCode"""
    url = f"{self.base_url}/iforce/art/image/imageExpand"

    payload = {
        "originalAttachmentCode": original_attachment_code,
        "topDistance": top_distance,
        "bottomDistance": bottom_distance,
        "leftDistance": left_distance,
        "rightDistance": right_distance,
        "backgroundWeight": background_weight,
        "backgroundHeight": background_height,
        "originalWeight": original_weight,
        "originalHeight": original_height,
        "generatedNum": generated_num,
        "ratio": ratio,
        "prompt": prompt,
        "generateChannel": 110,
    }

    resp = self.session.post(url, json=payload, timeout=15)
    resp.raise_for_status()

    try:
      res_data = resp.json()
    except Exception:
      res_data = resp.text.strip().strip('"')

    # 2.1 如果直接返回 Code 字符串
    if isinstance(res_data, str) and res_data.strip():
      return res_data.strip().strip('"')

    # 2.2 如果返回的是字典对象
    elif isinstance(res_data, dict):
      data = res_data.get("data")
      if isinstance(data, str) and data.strip():
        return data.strip().strip('"')

      record_code = (
          _safe_get(data, "recordCode")
          or _safe_get(res_data, "recordCode")
          or _safe_get(res_data, "id")
      )
      if record_code:
        return str(record_code)

    raise ValueError(f"提交扩图任务失败，返回内容为: {res_data}")

  def get_image_expand_result(
      self, record_code: str, poll_interval: int = 3, timeout: int = 180
  ) -> list:
    """3. 轮询获取扩图生成结果，返回图片 URL 列表"""
    url = f"{self.base_url}/iforce/art/image/getImageExpand"
    start_time = time.time()

    while time.time() - start_time < timeout:
      try:
        resp = self.session.get(
            url, params={"recordCode": record_code}, timeout=15
        )
        if resp.status_code == 200:
          res_data = resp.json()
          data = _safe_get(res_data, "data") or res_data

          if isinstance(data, dict):
            result_list = _safe_get(data, "resultList", [])
            if result_list and isinstance(result_list, list):
              urls = [
                  _safe_get(item, "attachmentPath")
                  for item in result_list
                  if isinstance(item, dict)
                  and _safe_get(item, "attachmentPath")
              ]
              if urls:
                return urls
      except Exception:
        pass

      time.sleep(poll_interval)

    raise TimeoutError(
        "扩图任务超时（已等待 3 分钟）。宝尊服务器生成较慢，请稍后重试或在 ROSS"
        " 历史记录中查看。"
    )
