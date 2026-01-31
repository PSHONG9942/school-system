import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- 1. 页面配置 ---
st.set_page_config(page_title="学校资料管理系统", layout="wide")

# --- 2. 连接 Google Sheets (核心部分) ---
# 使用缓存功能，避免每次操作都重新连接，提高速度
@st.cache_resource
def get_connection():
    # 从 Streamlit Secrets 里读取我们刚才藏好的钥匙
    key_dict = json.loads(st.secrets["google_creds"]["json_content"])
    
    # 定义权限范围
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    
    # 打开你的表格 (确保你的 Google Sheet 名字叫 school_database)
    sheet = client.open_by_key("1yuqfbLmJ_IIfInB_XyKEula17Kyse6FGeqvZgh-Rn94").sheet1
    return sheet

# 尝试连接，如果连不上（比如表格名字不对）就报错提示
try:
    sheet = get_connection()
except Exception as e:
    st.error(f"❌ 连接数据库失败！请检查：1. Google Sheet 是否已创建？ 2. 名字是否叫 school_database？ 3. 是否已经 Share 给机器人邮箱？\n错误信息: {e}")
    st.stop()

# --- 3. 辅助函数：读取数据 ---
def load_data():
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# --- 4. 界面逻辑 ---
with st.sidebar:
    st.title("🏫 校务系统")
    st.markdown(f"当前连接数据库: `school_database`")
    menu = st.radio("功能导航", ["📊 学生列表", "➕ 录入新学生", "🔍 资料查询"])

# === 功能 A: 学生列表 ===
if menu == "📊 学生列表":
    st.title("全校学生名册")
    
    # 添加一个刷新按钮
    if st.button("🔄 刷新数据"):
        st.cache_data.clear()
        
    # 读取数据
    df = load_data()
    
    if df.empty:
        st.info("目前表格是空的，快去录入数据吧！")
    else:
        st.dataframe(df, use_container_width=True)

# === 功能 B: 录入新学生 ===
elif menu == "➕ 录入新学生":
    st.title("新生资料录入")
    
    with st.form("add_student_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("学生姓名 (必填)")
            ic_no = st.text_input("身份证号")
        with col2:
            cls = st.selectbox("班级", ["1A", "1B", "1C", "1D", "2A", "2B"])
            
        submitted = st.form_submit_button("💾 保存到云端")
        
        if submitted:
            if not name:
                st.error("❌ 姓名不能为空！")
            else:
                with st.spinner("正在写入 Google Sheets..."):
                    # 把新数据添加到表格最后一行
                    new_row = [name, cls, ic_no]
                    sheet.append_row(new_row)
                    st.success(f"✅ 已成功保存：{name}")
                    # 稍微等一下让数据同步
                    st.cache_data.clear()

# === 功能 C: 简单查询 ===
elif menu == "🔍 资料查询":
    st.title("快速搜索")
    search_term = st.text_input("输入姓名或身份证号")
    
    if search_term:
        df = load_data()
        # 模糊搜索
        result = df[df.astype(str).apply(lambda x: x.str.contains(search_term, case=False)).any(axis=1)]
        
        if not result.empty:
            st.success(f"找到 {len(result)} 条结果：")
            st.table(result)
        else:
            st.warning("未找到相关记录。")
