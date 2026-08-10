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
        }
        if headers:
            default_headers.update(headers)
        self.session.headers.update(default_headers)

        if cookies:
            self.session.cookies.update(cookies)

    def upload_image(self, file_bytes: bytes, filename: str) -> str:
        """1. 上传图片到宝尊节点，获取 originalAttachmentCode"""
        # 优先尝试带 iforce/art/image/ 完整前缀的正确路由路径
        possible_urls = [
            f"{self.base_url}/iforce/art/image/upload/rename",
            f"{self.base_url}/iforce/art/image/upload",
            f"{self.base_url}/iforce/art/upload/rename",
            f"{self.base_url}/upload/rename",
        ]

        headers = {
            k: v
            for k, v in self.session.headers.items()
            if k.lower() != "content-type"
        }
        files = {"file": (filename, file_bytes)}

        attempt_logs = []
        for url in possible_urls:
            try:
                resp = self.session.post(
                    url, files=files, headers=headers, timeout=15
                )
                if resp.status_code == 200:
                    res_json = resp.json()
                    if res_json.get("success") or str(
                        res_json.get("status")
                    ) in ["200", "200.0"]:
                        data = res_json.get("data", {})
                        code = data.get(
                            "originalAttachmentCode"
                        ) or res_json.get("originalAttachmentCode")
                        if code:
                            return code
                    attempt_logs.append(
                        f"[{url}] 响应成功但未返回有效 code: {res_json}"
                    )
                else:
                    attempt_logs.append(f"[{url}] HTTP状态码 {resp.status_code}")
            except Exception as e:
                attempt_logs.append(f"[{url}] 请求失败: {str(e)}")

        raise ValueError(
            "所有上传接口路由均未成功返回附件 Code。详细尝试日志: "
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
        res_json = resp.json()

        if res_json.get("success") or str(res_json.get("status")) in [
            "200",
            "200.0",
        ]:
            data = res_json.get("data", {})
            return data.get("recordCode") or res_json.get("recordCode")
        raise ValueError(
            f"提交扩图任务失败: {res_json.get('message', '未知错误')}"
        )

    def get_image_expand_result(
        self, record_code: str, poll_interval: int = 2, timeout: int = 60
    ) -> list:
        """3. 轮询获取扩图生成结果，返回图片 URL 列表"""
        url = f"{self.base_url}/iforce/art/image/getImageExpand"
        start_time = time.time()

        while time.time() - start_time < timeout:
            resp = self.session.get(
                url, params={"recordCode": record_code}, timeout=15
            )
            resp.raise_for_status()
            res_json = resp.json()

            data = res_json.get("data", res_json)
            result_list = data.get("resultList", [])
            if result_list:
                return [item["attachmentPath"] for item in result_list]

            time.sleep(poll_interval)

        raise TimeoutError("扩图任务超时，未能在规定时间内获取到结果图")
