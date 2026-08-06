import streamlit as st

# 导入 modules 文件夹下的各个独立模块
from modules import mod_07_excel, mod_05_compress

# 页面基础配置
st.set_page_config(
    page_title="作图自动化在线中台",
    page_icon="⚡",
    layout="wide"
)

# 侧边栏功能导航
st.sidebar.title("⚡ 自动化中台")
nav_choice = st.sidebar.radio(
    "请选择功能模块：",
    ["📊 运营表格一键智能转化", "🖼️ 智能图片压缩与降维"]
)

# 路由渲染
if nav_choice == "📊 运营表格一键智能转化":
    mod_07_excel.render_ui()

elif nav_choice == "🖼️ 智能图片压缩与降维":
    mod_05_compress.render_ui()
