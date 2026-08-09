import os
import json
import datetime
import streamlit as st

# 本地数据持久化文件路径
STATS_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stats_data.json")

def _load_stats():
    """读取本地 JSON 统计记录"""
    if os.path.exists(STATS_FILE_PATH):
        try:
            with open(STATS_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_stats(data):
    """保存统计数据到本地 JSON 文件"""
    try:
        with open(STATS_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Stats save error: {e}")

def get_today_key():
    """获取当前日期 Key (YYYY-MM-DD)"""
    return datetime.date.today().isoformat()

def get_today_stats():
    """获取今天的统计数据字典"""
    data = _load_stats()
    today = get_today_key()
    today_data = data.get(today, {
        "compressed_images": 0,
        "saved_bytes": 0,
        "excel_cleaned": 0,
        "last_updated": ""
    })
    return today_data

def record_image_compression(count=1, saved_bytes=0):
    """记录图片压缩调用与空间节省量"""
    if count <= 0:
        return
    data = _load_stats()
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
    data = _load_stats()
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
    - 每清洗 1 个 Excel 脏表：切表 + 6~7字智能缩标题 + 对齐卖点列 -> 预估省 0.5 小时 (30 分钟)
    - 每压缩 1 张大图：格式转换 + 降维衰减 + 目录还原 -> 预估省 0.05 小时 (3 分钟)
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
        return "🌱 提效新星", "准备就绪！选择上方功能进行自动化，解锁今日提效成就！"
    elif hours < 1:
        return "⚡ 自动化启航", "打响第一枪！机械重复劳动正在被自动化中台消灭中~"
    elif hours < 3:
        return "🚀 提效狂魔", "战果累累！已为团队省下大量的琐碎工时，产出翻倍！"
    elif hours < 6:
        return "🔥 生产力爆表", "炸裂！今天成功省出近半天的人力时间，堪称团队核心英雄！"
    else:
        return "👑 机械劳动终结者", "无敌！机器一响黄金万两，您已彻底解放团队双手！"

def render_bottom_panel():
    """在 GUI 底部渲染简单的“数据统计面板”"""
    st.markdown("---")
    
    stats = get_today_stats()
    excel_cleaned = stats.get("excel_cleaned", 0)
    compressed_images = stats.get("compressed_images", 0)
    saved_bytes = stats.get("saved_bytes", 0)
    
    hours_saved = calculate_hours_saved(excel_cleaned, compressed_images)
    saved_gb_str = format_bytes_to_gb(saved_bytes)
    badge, slogan = get_achievement_badge(hours_saved)
    
    st.subheader("🏆 团队提效仪表盘 (Data Dashboard)")
    st.caption(f"📅 统计范围：今日 ({get_today_key()}) | 自动化中台实时记录提效战果 ⚡")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🖼️ 压缩大图",
            value=f"{compressed_images} 张",
            delta=f"+{compressed_images} 张" if compressed_images > 0 else None,
            help="通过中台进行画质衰减、格式转换与云端压缩的图片总量"
        )
        
    with col2:
        st.metric(
            label="💾 节省 GB 空间",
            value=saved_gb_str,
            delta="存储降本" if saved_bytes > 0 else None,
            help="压缩前后减少的文件体积累计总和"
        )
        
    with col3:
        st.metric(
            label="📊 清洗 Excel 脏表",
            value=f"{excel_cleaned} 个",
            delta=f"+{excel_cleaned} 个" if excel_cleaned > 0 else None,
            help="完成智能切割、标题剪裁 (6-7字) 及标准化列输出的运营表格数"
        )
        
    with col4:
        st.metric(
            label="⏱️ 节约重复劳动",
            value=f"{hours_saved:.1f} 小时",
            delta="机械工时释放" if hours_saved > 0 else None,
            help="计算公式：每清洗 1 表格省 0.5 小时，每压缩 1 图片省 0.05 小时"
        )
        
    st.success(f"**{badge}**｜{slogan} （今日累计为团队免除 **{hours_saved:.1f}** 小时“机械重复劳动”）")

def render_ui():
    """全屏/独立模块页面渲染"""
    st.header("🏆 团队提效仪表盘 (Data Dashboard)")
    st.markdown("记录这台电脑/团队今天通过中台完成的自动化提效战果，让每一次使用都有满屏的成就感！")
    
    stats = get_today_stats()
    excel_cleaned = stats.get("excel_cleaned", 0)
    compressed_images = stats.get("compressed_images", 0)
    saved_bytes = stats.get("saved_bytes", 0)
    hours_saved = calculate_hours_saved(excel_cleaned, compressed_images)
    saved_gb_str = format_bytes_to_gb(saved_bytes)
    badge, slogan = get_achievement_badge(hours_saved)
    
    st.info(f"🏅 **当前称号：{badge}**\n\n💬 {slogan}")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🖼️ 压缩大图数量", f"{compressed_images} 张")
    c2.metric("💾 节省空间大小", saved_gb_str)
    c3.metric("📊 清洗脏表数量", f"{excel_cleaned} 个")
    c4.metric("⏱️ 节约重复工时", f"{hours_saved:.1f} 小时")
    
    st.markdown("---")
    st.markdown("### 💡 提效折算价值说明")
    st.markdown("""
    - **📊 清洗 Excel 脏表**：自动定位有效区域、剔除导航列、智能压缩标题至 6~7 字并格式化排版（原人工单表平均约 30 分钟 = **0.5 小时**）。
    - **🖼️ 智能图片压缩**：自动转换无透明底 PNG 至 JPG、降低分辨率与质量衰减、云端深度压缩（原人工单图处理平均约 3 分钟 = **0.05 小时**）。
    - **💾 节省存储空间**：实时汇总原始文件与压缩后文件的体积差距，自动换算为 **GB** 级别显示。
    """)
    
    if st.button("🔄 刷新仪表盘"):
        st.rerun()
