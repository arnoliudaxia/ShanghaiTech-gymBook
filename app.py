import streamlit as st
import pandas as pd
import os
from pathlib import Path

# 设置页面配置
st.set_page_config(
    page_title="上科大体育场馆预订查询",
    page_icon="🏃",
    layout="wide"
)

# 标题
st.title("🏃 上科大体育场馆空闲时间查询")

# 数据目录
data_dir = "data"

# 检查data目录是否存在
if not os.path.exists(data_dir):
    st.error(f"❌ 数据目录 '{data_dir}' 不存在，请先运行 main.py 获取数据")
    st.stop()

# 获取所有CSV文件
csv_files = list(Path(data_dir).glob("*.csv"))

if not csv_files:
    st.warning(f"⚠️ 在 '{data_dir}' 目录中没有找到CSV文件，请先运行 main.py 获取数据")
    st.stop()

# 获取最新的文件修改时间作为全局更新时间
from datetime import datetime
latest_mtime = max(os.path.getmtime(f) for f in csv_files)
latest_update_time = datetime.fromtimestamp(latest_mtime).strftime("%Y-%m-%d %H:%M:%S")
st.info(f"📅 数据最后更新时间: **{latest_update_time}**")

st.markdown("---")

# 场地emoji映射
venue_emojis = {
    "羽毛球场": "🏸",
    "乒乓球场": "🏓",
    "网球场": "🎾",
    "匹克球": "🥎"
}

# 为每个场地创建一个标签页
venue_names = [f.stem for f in csv_files]
tabs = st.tabs([f"{venue_emojis.get(name, '🏟️')} {name}" for name in venue_names])

# 在每个标签页中显示对应场地的数据
for tab, csv_file, venue_name in zip(tabs, csv_files, venue_names):
    with tab:
        try:
            # 读取CSV文件
            df = pd.read_csv(csv_file)
            
            # 转置数据框以便更好地显示
            # 将Date列设为索引
            df_display = df.set_index('Date').T
            
            # 自定义样式函数
            def highlight_available(val):
                """高亮显示有空位的单元格"""
                if val == "有":
                    return 'background-color: #E6F9EE; color: #098237; font-weight: bold'
                elif val == "Error":
                    return 'background-color: #FFB6C6; color: black'
                else:
                    return 'background-color: #F0F0F0; color: #999999'
            
            # 应用样式并显示
            styled_df = df_display.style.map(highlight_available)
            st.dataframe(styled_df)
            # st.dataframe(styled_df, height=500)
            
            # 显示统计信息
            st.markdown("### 📊 统计信息")
            col1, col2, col3 = st.columns(3)
            
            # 计算每天的空闲时段数
            for idx, date in enumerate(df['Date']):
                available_count = (df.iloc[idx, 1:] == "有").sum()
                total_slots = len(df.columns) - 1
                
                with [col1, col2, col3][idx % 3]:
                    percentage = (available_count / total_slots) * 100
                    st.metric(
                        label=f"{date}",
                        value=f"{available_count}/{total_slots} 个时段",
                        delta=f"{percentage:.1f}% 可用"
                    )
            
        except Exception as e:
            st.error(f"❌ 读取文件 {csv_file} 时出错: {str(e)}")

# 添加说明
st.markdown("---")
st.markdown("""
### 📖 使用说明
- **绿色**: 该时段有空位可预订
- **灰色**: 该时段已被预订或不可用
- **粉色**: 查询该时段时出现错误

### 🔄 更新数据
运行以下命令更新数据:
```bash
python main.py
```
然后刷新此页面即可看到最新数据。
""")