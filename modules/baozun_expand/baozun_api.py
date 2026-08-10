import time
import requests


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
            "Content-Type": "application/json",
        }
        if headers:
            default_headers.update(headers)
        self.session.headers.update(default_headers)

        if cookies:
            self.session.cookies.update(cookies)

def upload_image(self, file_bytes: bytes, filename: str) -> str:
        """1. 上传图片到宝尊节点，获取 originalAttachmentCode"""
        # 网关完整路由路径列表（优先尝试带 iforce/art/image 前缀的完整路径）
        possible_urls = [
            f"{self.base_url}/iforce/art/image/upload/rename",
            f"{self.base_url}/iforce/art/upload/rename",
            f"{self.base_url}/iforce/upload/rename",
            f"{self.base_url}/upload/rename",
        ]

        headers = {
            k: v
            for k, v in self.session.headers.items()
            if k.lower() != "content-type"
        }
        files = {"file": (filename, file_bytes)}

        last_resp_msg = ""
        for url in possible_urls:
            try:
                resp = requests.post(
                    url,
                    files=files,
                    cookies=self.session.cookies,
                    headers=headers,
                    timeout=10,
                )
                if resp.status_code == 200:
                    res_json = resp.json()
                    if res_json.get("success") or res_json.get("status") in [
                        200,
                        "200",
                    ]:
                        data = res_json.get("data", {})
                        code = data.get("originalAttachmentCode") or res_json.get(
                            "originalAttachmentCode"
                        )
                        if code:
                            return code
                last_resp_msg = f"Status {resp.status_code}: {resp.text[:100]}"
            except Exception as e:
                last_resp_msg = str(e)

        raise ValueError(
            f"图片上传接口路由匹配失败，请在 F12 中确认上传接口的完整 URL。详细信息: {last_resp_msg}"
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

        resp = self.session.post(url, json=payload)
        resp.raise_for_status()
        res_json = resp.json()

        if res_json.get("success") or res_json.get("status") in [200, "200"]:
            data = res_json.get("data", {})
            return data.get("recordCode") or res_json.get("recordCode")
        raise ValueError(
            f"提交扩图任务失败: {res_json.get('message', '未知错误')}"
        )

    def get_image_expand_result(
        self, record_code: str, poll_interval: int = 2, timeout: int = 60
    ) -> list:
        url = f"{self.base_url}/iforce/art/image/getImageExpand"
        start_time = time.time()

        while time.time() - start_time < timeout:
            resp = self.session.get(url, params={"recordCode": record_code})
            resp.raise_for_status()
            res_json = resp.json()

            data = res_json.get("data", res_json)
            result_list = data.get("resultList", [])
            if result_list:
                return [item["attachmentPath"] for item in result_list]

            time.sleep(poll_interval)

        raise TimeoutError("扩图任务超时，未能在规定时间内获取到结果图")
