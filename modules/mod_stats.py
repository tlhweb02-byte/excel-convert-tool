import os
import json
import datetime
import streamlit as st

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

# 本地数据持久化文件路径 (备用/本地模式)
STATS_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stats_data.json")

# Google Sheets 表格名称（需在 Google Drive 中共享给服务账号）
SPREADSHEET_NAME = "提效中台数据统计"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_gspread_client():
    """获取与 Google Sheets 交互的 Client 凭据"""
    if not GSPREAD_AVAILABLE:
        return None
    try:
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=SCOPES
            )
            return gspread.authorize(creds)
    except Exception as e:
        print(f"Google Sheets Client Init Error: {e}")
    return None

def _get_worksheet():
    """获取或初始化 Google Sheet 工作表"""
    client = get_gspread_client()
    if client:
        try:
            try:
                sh = client.open(SPREADSHEET_NAME)
            except gspread.exceptions.SpreadsheetNotFound:
                sh = client.create(SPREADSHEET_NAME)
            ws = sh.sheet1
            headers = ws.row_values(1)
            if not headers:
                ws.append_row(["date", "compressed_images", "saved_bytes", "excel_cleaned", "last_updated"])
            return ws
        except Exception as e:
            print(f"Google Worksheet Access Error: {e}")
    return None

def _load_all_records():
    """优先从 Google Sheets 读取全量统计记录字典，未配置时回退读取本地 JSON"""
    ws = _get_worksheet()
    if ws:
        try:
            records = ws.get_all_records()
            stats_dict = {}
            for r in records:
                d = str(r.get("date", "")).strip()
                if d:
                    stats_dict[d] = {
                        "compressed_images": int(r.get("compressed_images", 0) or 0),
                        "saved_bytes": int(r.get("saved_bytes", 0) or 0),
                        "excel_cleaned": int(r.get("excel_cleaned", 0) or 0),
                        "last_updated": str(r.get("last_updated", ""))
                    }
            return stats_dict
        except Exception as e:
            print(f"Load from Sheet Error: {e}")

    # 回退到本地 JSON 模式
    if os.path.exists(STATS_FILE_PATH):
        try:
            with open(STATS_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_stats(data):
    """写回 Google Sheets，若未配置则回退写入本地 JSON 文件"""
    today = get_today_key()
    today_data = data.get(today, {})
    ws = _get_worksheet()

    if ws:
        try:
            row_data = [
                today,
                int(today_data.get("compressed_images", 0)),
                int(today_data.get("saved_bytes", 0)),
                int(today_data.get("excel_cleaned", 0)),
                str(today_data.get("last_updated", ""))
            ]
            try:
                cell = ws.find(today, in_column=1)
            except Exception:
                cell = None

            if cell:
                range_label = f"A{cell.row}:E{cell.row}"
                ws.update(range_name=range_label, values=[row_data])
            else:
                ws.append_row(row_data)
            return
        except Exception as e:
            print(f"Save to Sheet Error: {e}")

    # 回退写入本地 JSON
    try:
        with open(STATS_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Save local stats error: {e}")

def get_today_key():
    """获取当前日期 Key (YYYY-MM-DD)"""
    return datetime.date.today().isoformat()

def aggregate_stats_by_prefix(prefix=""):
    """
    按日期前缀聚合统计数据：
    - prefix="" -> 全量累计
    - prefix="2026" -> 2026 年度统计
    - prefix="2026-08" -> 2026 年 8 月月度统计
    - prefix="2026-08-09" -> 当天日度统计
    """
    all_data = _load_all_records()
    compressed_images = 0
    saved_bytes = 0
    excel_cleaned = 0

    for d, row in all_data.items():
        if d.startswith(prefix):
            compressed_images += row.get("compressed_images", 0)
            saved_bytes += row.get("saved_bytes", 0)
            excel_cleaned += row.get("excel_cleaned", 0)

    return {
        "compressed_images": compressed_images,
        "saved_bytes": saved_bytes,
        "excel_cleaned": excel_cleaned
    }

def record_image_compression(count=1, saved_bytes=0):
    """记录图片压缩调用与空间节省量"""
    if count <= 0:
        return
    data = _load_all_records()
    today = get_today_key()
    if today not in data:
        data[today] = {
            "compressed_images": 0,
            "saved_bytes": 0,
            "excel_cleaned": 0,
            "last_updated": ""
        }
    data[today]["compressed_images"] += count
    data[today]["saved_bytes"] += max(0, int(saved_bytes))
    data[today]["last_updated"] = datetime.datetime.now().strftime("%H:%M:%S")
    _save_stats(data)

def record_excel_cleaning(count=1):
    """记录 Excel 表格清洗转化调用"""
    if count <= 0:
        return
    data = _load_all_records()
    today = get_today_key()
    if today not in data:
        data[today] = {
            "compressed_images": 0,
            "saved_bytes": 0,
            "excel_cleaned": 0,
            "last_updated": ""
        }
    data[today]["excel_cleaned"] += count
    data[today]["last_updated"] = datetime.datetime.now().strftime("%H:%M:%S")
    _save_stats(data)

def calculate_hours_saved(excel_cleaned, compressed_images):
    """
    预估节约机械重复劳动小时数：
    - 每清洗 1 个 Excel 脏表：预估省 0.5 小时 (30 分钟)
    - 每压缩 1 张大图：预估省 0.05 小时 (3 分钟)
    """
    hours = (excel_cleaned * 0.5) + (compressed_images * 0.05)
    return round(hours, 2)

def format_bytes_to_gb(saved_bytes):
    """格式化节省的空间显示 (GB / MB)"""
    gb = saved_bytes / (1024 ** 3)
    if gb >= 0.01:
        return f"{gb:.2f} GB"
    else:
        mb = saved_bytes / (1024 ** 2)
        if mb >= 0.1:
            return f"{mb:.1f} MB ({gb:.3f} GB)"
        else:
            return f"{gb:.3f} GB"

def get_achievement_badge(hours):
    """根据节约工时评定成就称号与勋章"""
    if hours == 0:
        return "🌱 提效新星", "准备就绪！选择上方功能进行自动化，解锁提效成就！"
    elif hours < 1:
        return "⚡ 自动化启航", "打响第一枪！机械重复劳动正在被自动化中台消灭中~"
    elif hours < 10:
        return "🚀 提效狂魔", "战果累累！已为团队省下大量琐碎工时，产出翻倍！"
    elif hours < 50:
        return "🔥 生产力爆表", "炸裂！成功省出大量的团队人力，堪称团队核心引擎！"
    else:
        return "👑 机械劳动终结者", "无敌！机器一响黄金万两，您已彻底解放团队双手！"

def render_bottom_panel():
    """在 GUI 底部渲染多维度数据统计面板"""
    st.markdown("---")
    
    today_str = get_today_key()
    this_month_str = today_str[:7]
    this_year_str = today_str[:4]
    
    st.subheader("🏆 团队提效仪表盘 (Data Dashboard)")
    
    period_mode = st.radio(
        "选择统计时间维度：",
        ["📅 今日战报", "📆 本月汇总", "🚩 本年汇总", "🏆 历史全量累计"],
        horizontal=True,
        key="bottom_dashboard_period_mode"
    )
    
    if period_mode == "📅 今日战报":
        prefix = today_str
        sub_title = f"今日 ({today_str})"
    elif period_mode == "📆 本月汇总":
        prefix = this_month_str
        sub_title = f"本月 ({this_month_str})"
    elif period_mode == "🚩 本年汇总":
        prefix = this_year_str
        sub_title = f"本年 ({this_year_str} 年)"
    else:
        prefix = ""
        sub_title = "历史全量累计"
        
    stats = aggregate_stats_by_prefix(prefix)
    excel_cleaned = stats.get("excel_cleaned", 0)
    compressed_images = stats.get("compressed_images", 0)
    saved_bytes = stats.get("saved_bytes", 0)
    
    hours_saved = calculate_hours_saved(excel_cleaned, compressed_images)
    saved_gb_str = format_bytes_to_gb(saved_bytes)
    badge, slogan = get_achievement_badge(hours_saved)
    
    st.caption(f"📅 统计区间：**{sub_title}** | 自动化中台实时同步提效战果 ⚡")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🖼️ 压缩大图",
            value=f"{compressed_images} 张",
            help="通过中台进行画质衰减、格式转换与云端压缩的图片总量"
        )
        
    with col2:
        st.metric(
            label="💾 节省 GB 空间",
            value=saved_gb_str,
            help="压缩前后减少的文件体积累计总和"
        )
        
    with col3:
        st.metric(
            label="📊 清洗 Excel 脏表",
            value=f"{excel_cleaned} 个",
            help="完成智能切割、标题剪裁 (6-7字) 及标准化列输出的运营表格数"
        )
        
    with col4:
        st.metric(
            label="⏱️ 节约重复劳动",
            value=f"{hours_saved:.1f} 小时",
            help="计算公式：每清洗 1 表格省 0.5 小时，每压缩 1 图片省 0.05 小时"
        )
        
    st.success(f"**{badge}**｜{slogan} （区间内累计为团队免除 **{hours_saved:.1f}** 小时“机械重复劳动”）")

def render_ui():
    """全屏/独立模块页面渲染（支持按年、月、日精准查询与历史明细表）"""
    st.header("🏆 团队提效仪表盘 (Data Dashboard)")
    st.markdown("记录团队通过中台完成的自动化提效战果，支持按**年、月、日**精准追溯明细与全量统计！")
    
    all_data = _load_all_records()
    dates = sorted(list(all_data.keys()), reverse=True)
    
    years = sorted(list(set(d[:4] for d in dates if len(d) >= 4)), reverse=True)
    if not years:
        years = [get_today_key()[:4]]
        
    c_y, c_m = st.columns(2)
    with c_y:
        selected_year = st.selectbox("🗓️ 选择统计年份：", ["全部年份"] + years)
    with c_m:
        months_in_year = sorted(list(set(d[:7] for d in dates if selected_year == "全部年份" or d.startswith(selected_year))), reverse=True)
        selected_month = st.selectbox("📆 选择统计月份：", ["全部月份"] + months_in_year)
        
    if selected_month != "全部月份":
        prefix = selected_month
        label_text = f"{selected_month} 月度数据"
    elif selected_year != "全部年份":
        prefix = selected_year
        label_text = f"{selected_year} 年度数据"
    else:
        prefix = ""
        label_text = "全量历史累计数据"
        
    stats = aggregate_stats_by_prefix(prefix)
    excel_cleaned = stats.get("excel_cleaned", 0)
    compressed_images = stats.get("compressed_images", 0)
    saved_bytes = stats.get("saved_bytes", 0)
    hours_saved = calculate_hours_saved(excel_cleaned, compressed_images)
    saved_gb_str = format_bytes_to_gb(saved_bytes)
    badge, slogan = get_achievement_badge(hours_saved)
    
    st.info(f"🏅 **【{label_text}】勋章：{badge}**\n\n💬 {slogan}")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🖼️ 压缩大图数量", f"{compressed_images} 张")
    c2.metric("💾 节省空间大小", saved_gb_str)
    c3.metric("📊 清洗脏表数量", f"{excel_cleaned} 个")
    c4.metric("⏱️ 节约重复工时", f"{hours_saved:.1f} 小时")
    
    st.markdown("---")
    st.subheader("📋 每日历史提效明细账单")
    
    table_rows = []
    for d in dates:
        if not prefix or d.startswith(prefix):
            r = all_data[d]
            c_cnt = r.get("compressed_images", 0)
            e_cnt = r.get("excel_cleaned", 0)
            b_cnt = r.get("saved_bytes", 0)
            h_cnt = calculate_hours_saved(e_cnt, c_cnt)
            table_rows.append({
                "日期 (Date)": d,
                "压缩大图 (张)": c_cnt,
                "节省空间": format_bytes_to_gb(b_cnt),
                "清洗脏表 (个)": e_cnt,
                "释放重复工时 (小时)": h_cnt,
                "最后更新时间": r.get("last_updated", "")
            })
            
    if table_rows:
        import pandas as pd
        df_display = pd.DataFrame(table_rows)
        st.dataframe(df_display, use_container_width=True)
    else:
        st.write("暂无对应时间段的提效明细数据。")
        
    if st.button("🔄 刷新数据"):
        st.rerun()
