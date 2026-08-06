import streamlit as st
import pandas as pd
import numpy as np
import io
import os
import zipfile
import re
from PIL import Image

try:
    import tinify
    TINIFY_AVAILABLE = True
except ImportError:
    TINIFY_AVAILABLE = False

LOCAL_API_KEYS = [
    "XDzl5YfGBk3HF7PJFlQw9HgzWTFlpH7D",
    "qdD7H1674MLP2MqX7ZDrs1wkXlT8LQBY",
    "t24GDhLWHQHHBG2XNqlH371NbzTR3w7F"
]

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

# ==============================================================
# 模块一：运营表格一键智能转化
# ==============================================================
def simplify_title(row):
    name_str = str(row.get('名称', '')).strip() if pd.notna(row.get('名称')) else ""
    feat_str = str(row.get('卖点', '')).strip() if pd.notna(row.get('卖点')) and str(row.get('卖点')).strip().lower() != 'nan' else ""

    if not name_str or name_str.lower() == 'nan':
        return ""

    if "耐高系列男女童大童速干双面穿篮球球衣" in name_str:
        return "大童速干篮球衣"

    # 1. 前缀识别
    prefix = ""
    if "大童" in name_str:
        prefix = "大童"
    elif "幼童" in name_str:
        prefix = "幼童"
    elif "婴童" in name_str or "宝宝" in name_str:
        prefix = "婴童"
    elif "男女童" in name_str or "男童" in name_str or "女童" in name_str or "儿童" in name_str:
        prefix = "大童"
    elif "男女" in name_str or "情侣" in name_str:
        prefix = "男女"
    elif "女子" in name_str or "女" in name_str:
        prefix = "女子"
    elif "男子" in name_str or "男" in name_str:
        prefix = "男子"
    else:
        prefix = "男子"

    # 2. 品类后缀
    suffix = ""
    if "篮球球衣" in name_str or "篮球衣" in name_str:
        suffix = "篮球衣"
    elif "球衣" in name_str:
        suffix = "球衣"
    elif "连体衣" in name_str:
        suffix = "连体衣"
    elif "半身裙" in name_str:
        suffix = "半身裙"
    elif "凉鞋" in name_str:
        suffix = "凉鞋"
    elif "紧身裤" in name_str:
        suffix = "紧身裤"
    elif "短裤" in name_str:
        suffix = "短裤"
    elif "长裤" in name_str or "运动裤" in name_str:
        suffix = "长裤"
    elif "卫衣" in name_str or "连帽衫" in name_str:
        suffix = "卫衣"
    elif "夹克" in name_str or "羽绒" in name_str or "棉服" in name_str:
        suffix = "夹克"
    elif "衬衫" in name_str:
        suffix = "衬衫"
    elif "POLO" in name_str.upper() or "翻领" in name_str:
        suffix = "T恤"
    elif "T恤" in name_str or "短袖" in name_str or "半袖" in name_str:
        suffix = "T恤"
    elif "上衣" in name_str:
        suffix = "上衣"
    elif "内衣" in name_str:
        suffix = "内衣"
    elif "跑步鞋" in name_str or "竞速" in name_str:
        suffix = "跑步鞋"
    elif "篮球鞋" in name_str:
        suffix = "篮球鞋"
    elif "童鞋" in name_str:
        suffix = "童鞋"
    elif "运动鞋" in name_str or "跑鞋" in name_str or "老爹鞋" in name_str or "气垫鞋" in name_str or "板鞋" in name_str or "鞋" in name_str:
        suffix = "运动鞋"
    else:
        suffix = "服装"

    # 3. 中间修饰词
    mid = ""
    if feat_str and feat_str != "双面":
        mid = feat_str
    elif "速干" in name_str and ("球衣" in name_str or "短裤" in name_str):
        mid = "速干"

    keywords = [
        "复古", "修身", "宽松", "速干", "纯棉", "休闲", "柔软", "舒适", "轻便", 
        "百搭", "干爽", "轻盈", "弹性", "耐穿", "随性", "短款", "梭织", "轻松", 
        "导湿", "中腰", "高腰", "顺滑", "贴合", "双面", "印花", "空军", "透气", 
        "机能", "赛博", "缓震", "防水", "稳程", "实战", "包头", "防晒", "时尚",
        "经典", "日常", "运动"
    ]

    if not mid:
        for kw in keywords:
            if kw in name_str and kw not in prefix and kw not in suffix:
                mid = kw
                break

    res = prefix + mid + suffix

    # 最少 6 字逻辑补充
    if len(res) < 6:
        for kw in keywords:
            if kw not in res:
                candidate = prefix + mid + kw + suffix
                if len(candidate) >= 6:
                    res = candidate
                    break

    if len(res) < 6:
        for fill in ["时尚", "运动", "经典", "休闲", "百搭"]:
            if fill not in res:
                candidate = prefix + fill + mid + suffix
                if len(candidate) >= 6:
                    res = candidate
                    break

    # 最长控制 7 字
    if len(res) > 7:
        res = res[:7]

    return res

def process_excel(uploaded_file):
    df_raw = pd.read_excel(uploaded_file, header=None)
    
    start_row, start_col = None, None
    for r in range(len(df_raw)):
        for c in range(len(df_raw.columns)):
            val = str(df_raw.iloc[r, c]).replace('\n', '').replace('\r', '').strip()
            if '模块' in val:
                start_row, start_col = r, c
                break
        if start_row is not None:
            break
            
    if start_row is None:
        raise ValueError("未在表格中找到包含 '模块' 关键词的单元格！")

    end_col = None
    for c in range(start_col, len(df_raw.columns)):
        val = str(df_raw.iloc[start_row, c]).replace('\n', '').replace('\r', '').strip()
        if '商品卖点' in val or '卖点' in val:
            end_col = c
            break
            
    if end_col is None:
        end_col = len(df_raw.columns) - 1

    end_row = len(df_raw)
    for r in range(start_row + 1, len(df_raw)):
        row_str = ' '.join([str(x) for x in df_raw.iloc[r].values if pd.notna(x)])
        if '热门分类导航' in row_str:
            end_row = r
            break

    headers = [str(df_raw.iloc[start_row, c]).replace('\n', '').replace('\r', '').strip() for c in range(start_col, end_col + 1)]
    df = df_raw.iloc[start_row + 1:end_row, start_col:end_col + 1].copy()
    df.columns = headers

    valid_cols = [c for c in df.columns if '热门分类导航' not in str(c)]
    df = df[valid_cols]

    rename_map = {}
    for col in df.columns:
        if col in ['图片链接', '产品图']:
            rename_map[col] = '商品图'
        elif col in ['商品卖点']:
            rename_map[col] = '卖点'
    df = df.rename(columns=rename_map)

    if '名称' in df.columns:
        df['中文名称'] = df.apply(simplify_title, axis=1)
        cols = list(df.columns)
        if '中文名称' in cols:
            cols.remove('中文名称')
            idx_name = cols.index('名称')
            cols.insert(idx_name + 1, '中文名称')
            df = df[cols]

    output_buffer = io.BytesIO()
    with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='首页线框', index=False)
        workbook = writer.book
        workbook.create_sheet('最终视觉稿')
        writer.sheets['首页线框'].views.sheetView[0].tabSelected = True
        if '最终视觉稿' in writer.sheets:
            writer.sheets['最终视觉稿'].views.sheetView[0].tabSelected = False

    output_buffer.seek(0)
    return df, output_buffer


# ==============================================================
# 模块二：智能图片压缩与降维
# ==============================================================
def has_actual_transparency(img):
    try:
        if img.mode in ('RGBA', 'LA', 'PA'):
            return img.getchannel('A').getextrema()[0] < 255
        elif img.mode == 'P' and 'transparency' in img.info:
            return True
        return False
    except Exception:
        return False

def compress_single_image(img_bytes, filename, target_kb):
    target_bytes = target_kb * 1024
    orig_size_kb = len(img_bytes) / 1024
    
    if orig_size_kb <= target_kb:
        return img_bytes, filename, f"⏩ [无需压缩] {filename} ({orig_size_kb:.1f}KB已达标)"

    out_name = filename

    try:
        with Image.open(io.BytesIO(img_bytes)) as img:
            fmt = img.format or 'JPEG'
            png_converted = False

            # 智能无透明区域 PNG 转 JPG
            if fmt == 'PNG' and not has_actual_transparency(img):
                img = img.convert('RGB')
                fmt = 'JPEG'
                out_name = os.path.splitext(filename)[0] + '.jpg'
                png_converted = True

            best_bytes = None
            min_size = float('inf')

            # 本地无损/画质直降测试
            if fmt in ['JPEG', 'WEBP']:
                for q in range(95, 40, -5):
                    with io.BytesIO() as buf:
                        img.save(buf, format=fmt, quality=q, optimize=True)
                        b_val = buf.getvalue()
                        b_len = len(b_val)
                        if b_len < min_size:
                            min_size = b_len
                            best_bytes = b_val

                        if b_len <= target_bytes:
                            msg = f"✅ [本地压缩] {filename} -> {out_name} ({orig_size_kb:.1f}KB -> {b_len/1024:.1f}KB, Quality={q})"
                            if png_converted:
                                msg += " (无透明底，强转JPG)"
                            return b_val, out_name, msg

            # 云端 Tinify 备用极限压缩
            if TINIFY_AVAILABLE:
                for key in LOCAL_API_KEYS:
                    try:
                        tinify.key = key
                        with io.BytesIO() as buf:
                            img.save(buf, format=fmt, quality=95 if fmt == 'JPEG' else None, optimize=True)
                            source_bytes = buf.getvalue()
                        
                        compressed_data = tinify.from_buffer(source_bytes).to_buffer()
                        c_len = len(compressed_data)
                        msg = f"☁️ [云端深度极限] {filename} -> {out_name} ({orig_size_kb:.1f}KB -> {c_len/1024:.1f}KB)"
                        if png_converted:
                            msg += " (无透明底，强转JPG)"
                        return compressed_data, out_name, msg
                    except Exception:
                        continue

            if best_bytes is not None:
                msg = f"⚠️ [尽力压缩] {filename} -> {out_name} ({orig_size_kb:.1f}KB -> {len(best_bytes)/1024:.1f}KB)"
                return best_bytes, out_name, msg

    except Exception as e:
        return img_bytes, filename, f"❌ [处理失败] {filename}: {e}"

    return img_bytes, filename, f"⏩ [原样输出] {filename}"


# ==============================================================
# UI 路由界面
# ==============================================================
if nav_choice == "📊 运营表格一键智能转化":
    st.header("📊 运营表格一键智能转化")
    st.markdown("上传原始运营 Excel 表格，自动截取有效区域、智能缩减商品标题（6~7字），并格式化输出标准清单。")

    uploaded_file = st.file_uploader("📂 请选择需要转化的 Excel 文件 (.xlsx, .xls)", type=["xlsx", "xls"])

    if uploaded_file is not None:
        try:
            with st.spinner("正在智能转换表格，请稍候..."):
                df_result, output_buffer = process_excel(uploaded_file)
            
            st.success("🎉 表格转化成功！")
            st.subheader("📋 转换数据预览 (前 10 行)")
            st.dataframe(df_result.head(10), use_container_width=True)
            
            st.download_button(
                label="📥 点击下载转化后的标准清单 Excel",
                data=output_buffer,
                file_name="生成的标准转化清单.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"❌ 转换过程中发生错误: {e}")

elif nav_choice == "🖼️ 智能图片压缩与降维":
    st.header("🖼️ 智能图片压缩与降维")
    st.markdown("支持 PNG 无损转 JPG 降维、画质自动衰减与极限云端压缩。可上传多张图片或单个包含目录结构的 ZIP 压缩包。")

    target_kb = st.slider("🎯 目标文件大小上限 (KB)", min_value=100, max_value=2000, value=500, step=50)

    upload_mode = st.radio("请选择上传模式：", ["多张图片上传", "ZIP 压缩包上传 (保持目录结构)"], horizontal=True)

    if upload_mode == "多张图片上传":
        files = st.file_uploader("📂 选择一张或多张图片", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
        
        if files:
            if st.button("🚀 开始极速压缩"):
                logs = []
                compressed_files = []

                progress_bar = st.progress(0)
                for idx, file in enumerate(files):
                    img_bytes = file.read()
                    out_bytes, out_name, log_msg = compress_single_image(img_bytes, file.name, target_kb)
                    logs.append(log_msg)
                    compressed_files.append((out_name, out_bytes))
                    progress_bar.progress((idx + 1) / len(files))

                st.success(f"🎉 压缩完成！共处理 {len(files)} 张图片。")

                st.subheader("📝 处理日志监控")
                st.code("\n".join(logs), language="text")

                # 打包为 ZIP 供一键下载
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for name, data in compressed_files:
                        zf.writestr(f"compressed_images/{name}", data)
                zip_buf.seek(0)

                st.download_button(
                    label="📥 一键打包下载所有压缩后的图片 (.zip)",
                    data=zip_buf,
                    file_name="compressed_images.zip",
                    mime="application/zip"
                )

    else:
        zip_file = st.file_uploader("📂 上传包含图片文件夹的 ZIP 压缩包", type=["zip"])
        
        if zip_file is not None:
            if st.button("🚀 解压并深度压缩 ZIP 包内所有图片"):
                logs = []
                out_zip_buf = io.BytesIO()

                with zipfile.ZipFile(zip_file, "r") as in_zf, zipfile.ZipFile(out_zip_buf, "w", zipfile.ZIP_DEFLATED) as out_zf:
                    file_list = [f for f in in_zf.namelist() if not f.endswith('/') and not f.startswith('__MACOSX')]
                    progress_bar = st.progress(0)

                    for idx, inner_path in enumerate(file_list):
                        file_data = in_zf.read(inner_path)
                        filename = os.path.basename(inner_path)
                        dirname = os.path.dirname(inner_path)

                        ext = os.path.splitext(filename).lower()
                        if ext in ['.jpg', '.jpeg', '.png', '.webp']:
                            out_bytes, out_name, log_msg = compress_single_image(file_data, filename, target_kb)
                            out_inner_path = os.path.join("compressed_images", dirname, out_name) if dirname else os.path.join("compressed_images", out_name)
                            out_zf.writestr(out_inner_path, out_bytes)
                            logs.append(log_msg)
                        else:
                            out_inner_path = os.path.join("compressed_images", inner_path)
                            out_zf.writestr(out_inner_path, file_data)
                            logs.append(f"⏩ [原样复制非图片] {filename}")

                        progress_bar.progress((idx + 1) / len(file_list))

                out_zip_buf.seek(0)
                st.success("🎉 ZIP 压缩包处理完成！已保持原嵌套目录结构。")

                st.subheader("📝 处理日志监控")
                st.code("\n".join(logs), language="text")

                st.download_button(
                    label="📥 一键下载精压缩后的 ZIP 压缩包",
                    data=out_zip_buf,
                    file_name="compressed_folder.zip",
                    mime="application/zip"
                )
