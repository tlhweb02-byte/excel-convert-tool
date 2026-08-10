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
        url = f"{self.base_url}/upload/rename"
        headers = {
            k: v
            for k, v in self.session.headers.items()
            if k.lower() != "content-type"
        }
        files = {"file": (filename, file_bytes)}

        resp = requests.post(
            url, files=files, cookies=self.session.cookies, headers=headers
        )
        resp.raise_for_status()
        res_json = resp.json()

        if res_json.get("success") or res_json.get("status") in [200, "200"]:
            data = res_json.get("data", {})
            return data.get(
                "originalAttachmentCode"
            ) or res_json.get("originalAttachmentCode")
        raise ValueError(
            f"图片上传失败: {res_json.get('message', '未知错误')}"
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
