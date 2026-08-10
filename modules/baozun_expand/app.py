from PIL import Image
import streamlit as st

# 导入 API 封装类
try:
  from .baozun_api import BaozunExpandAPI
except ImportError:
  from modules.baozun_expand.baozun_api import BaozunExpandAPI


# 关键：函数名必须叫做 render_ui
def render_ui():
  st.title("🎨 宝尊智能扩图 (ROSS)")
  st.caption("选择图片并配置参数，自动调用宝尊 ROSS 引擎扩展背景。")

  col_left, col_right = st.columns(2)

  with col_left:
    st.subheader("1. 上传图片")
    uploaded_file = st.file_uploader(
        "选择图片", type=["jpg", "jpeg", "png", "webp"]
    )

    orig_w, orig_h = 390, 520
    if uploaded_file:
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
      bottom_d = st.number_input("下边距 (bottomDistance)", value=140)
      right_d = st.number_input("右边距 (rightDistance)", value=205)

    gen_num = st.slider("生成图片数量", min_value=1, max_value=4, value=4)

    start_btn = st.button(
        "✨ 立即生成", type="primary", disabled=(not uploaded_file)
    )

  if start_btn and uploaded_file:
    status_box = st.status("正在处理扩图任务...", expanded=True)
    try:
      api = BaozunExpandAPI()

      status_box.write("正在上传图片到宝尊服务器...")
      attachment_code = api.upload_image(
          uploaded_file.getvalue(), uploaded_file.name
      )

      status_box.write("正在提交智能扩图任务...")
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

      status_box.write("AI 正在渲染生成图片...")
      result_urls = api.get_image_expand_result(record_code)

      status_box.update(
          label="🎉 扩图生成完成！", state="complete", expanded=False
      )

      st.subheader("3. 生成结果")
      grid_cols = st.columns(len(result_urls))
      for idx, url in enumerate(result_urls):
        with grid_cols[idx]:
          st.image(url, caption=f"方案 {idx + 1}", use_container_width=True)
          st.markdown(
              f"[点击下载图片]({url})", unsafe_allow_html=True
          )

    except Exception as e:
      status_box.update(label=f"❌ 扩图失败: {str(e)}", state="error")
