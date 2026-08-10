from PIL import Image
import io
import streamlit as st


def render_baozun_expand_module():
    st.title("🖼️ 宝尊智能扩图 (ROSS)")
    st.caption("内置宝尊 ROSS AI 扩图引擎，无需手动打开 ROSS 网页。")

    # 配置 Cookie (可存放在 st.secrets 或配置文件中)
    user_cookies = st.session_state.get(
        "baozun_cookies", {}
    )  # 示例: {"SESSION": "xxxx"}

    col_left, col_right = st.columns()

    with col_left:
        st.subheader("1. 上传图片")
        uploaded_file = st.file_uploader(
            "选择需要扩展边距的图片", type=["jpg", "jpeg", "png", "webp"]
        )

        orig_w, orig_h = 390, 520
        if uploaded_file:
            # 读取图片获取原始宽高
            image = Image.open(uploaded_file)
            orig_w, orig_h = image.size
            st.image(
                image,
                caption=f"原图预览 ({orig_w}x{orig_h})",
                use_container_width=True,
            )

    with col_right:
        st.subheader("2. 扩图参数")
        bg_w = st.number_input("画布目标宽度 (px)", value=800, step=50)
        bg_h = st.number_input("画布目标高度 (px)", value=800, step=50)

        st.write("**扩展边距距离 (px)**")
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            top_d = st.number_input("上边距 (topDistance)", value=140)
            left_d = st.number_input("左边距 (leftDistance)", value=205)
        with m_col2:
            bottom_d = st.number_input(
                "下边距 (bottomDistance)", value=140
            )
            right_d = st.number_input(
                "右边距 (rightDistance)", value=205
            )

        gen_num = st.slider("生成图片数量", min_value=1, max_value=4, value=4)

        start_btn = st.button(
            "✨ 立即生成", type="primary", disabled=(not uploaded_file)
        )

    # 逻辑处理
    if start_btn and uploaded_file:
        status_box = st.status("正在处理扩图任务...", expanded=True)
        try:
            api = BaozunExpandAPI(cookies=user_cookies)

            status_box.write("正在上传图片至宝尊服务器...")
            attachment_code = api.upload_image(
                uploaded_file.getvalue(), uploaded_file.name
            )

            status_box.write("提交智能扩图任务...")
            record_code = api.submit_image_expand(
                original_attachment_code=attachment_code,
                top_distance=top_d,
                bottom_distance=bottom_d,
                left_distance=left_d,
                right_distance=right_d,
                background_weight=bg_w,
                background_height=bg_h,
                original_weight=orig_w,
                original_height=orig_h,
                generated_num=gen_num,
            )

            status_box.write("AI 正在扩图中，请稍候...")
            result_urls = api.get_image_expand_result(record_code)

            status_box.update(
                label="🎉 扩图生成成功！", state="complete", expanded=False
            )

            # 展示结果
            st.subheader("3. 生成结果预览与下载")
            grid_cols = st.columns(len(result_urls))
            for idx, url in enumerate(result_urls):
                with grid_cols[idx]:
                    st.image(
                        url,
                        caption=f"方案 {idx + 1}",
                        use_container_width=True,
                    )
                    st.markdown(
                        f"[点击下载图片]({url})", unsafe_allow_html=True
                    )

        except Exception as e:
            status_box.update(
                label=f"❌ 扩图失败: {str(e)}", state="error"
            )


if __name__ == "__main__":
    render_baozun_expand_module()
