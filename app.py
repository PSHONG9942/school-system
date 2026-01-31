import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- 1. 页面配置 ---
st.set_page_config(page_title="学校资料管理系统", layout="wide")

# --- 2. 连接 Google Sheets (新版：更强壮的连接方式) ---
@st.cache_resource
def get_connection():
    # 直接构建字典，不再依赖容易出错的 JSON 字符串
    key_dict = {
        "type": "service_account",
        "project_id": st.secrets["project_id"],
        "private_key_id": st.secrets["private_key_id"],
        "private_key": st.secrets["private_key"],  # 这里会自动处理换行问题
        "client_email": st.secrets["client_email"],
        "client_id": st.secrets["client_id"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": st.secrets["client_x509_cert_url"],
        "universe_domain": "googleapis.com"
    }
    
    # 定义权限范围
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    
    # 打开你的表格 (记得确认表格 ID)
    sheet = client.open_by_key("1yuqfbLmJ_IIFInB_XyKEula17Kyse6FGeqvZgh-Rn94").sheet1
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

# === 功能 B: 录入新学生 (升级版) ===
elif menu == "➕ 录入新学生":
    st.title("📝 新生详细资料录入")
    st.info("请依照 idMe/APDM 标准填写以下资料。")
    
    with st.form("add_student_form"):
        # --- 第一部分：基本身份信息 ---
        st.subheader("1. 身份信息")
        col1, col2 = st.columns(2)
        with col1:
            name_en = st.text_input("学生姓名 (马来文/英文 Name)")
            mykid = st.text_input("身份证/MyKid 号码 (无横杠)")
            dob = st.date_input("出生日期")
        with col2:
            name_cn = st.text_input("中文姓名 (选填)")
            cls = st.selectbox("班级", ["1A", "1B", "1C", "1D", "2A", "2B", "3A", "3B", "4A", "4B", "5A", "5B", "6A", "6B"])
            gender = st.radio("性别", ["男 (Lelaki)", "女 (Perempuan)"], horizontal=True)

        # --- 第二部分：背景资料 (idMe 必填) ---
        st.subheader("2. 背景资料")
        col3, col4, col5 = st.columns(3)
        with col3:
            race = st.selectbox("种族 (Kaum)", ["华裔 (Cina)", "巫裔 (Melayu)", "印裔 (India)", "其他 (Lain-lain)"])
        with col4:
            religion = st.selectbox("宗教 (Agama)", ["佛教 (Buddha)", "伊斯兰教 (Islam)", "基督教 (Kristian)", "兴都教 (Hindu)", "道教 (Tao)", "其他"])
        with col5:
            nationality = st.selectbox("国籍 (Warganegara)", ["马来西亚公民", "非公民", "永久居民"])

        # --- 第三部分：联系方式 ---
        st.subheader("3. 家庭联系")
        address = st.text_area("家庭住址 (Alamat Rumah)")
        guardian_phone = st.text_input("监护人电话 (No. Telefon Penjaga)")
            
        # --- 提交按钮 ---
        submitted = st.form_submit_button("💾 保存完整资料")
        
        if submitted:
            if not name_en or not mykid:
                st.error("❌ 姓名(英文)和身份证号是必填项！")
            else:
                with st.spinner("正在写入 Google Sheets..."):
                    # 注意：这里的顺序必须和 Google Sheet 表头的顺序一模一样！
                    # 顺序：姓名 | 中文名 | 班级 | IC | 性别 | 生日 | 种族 | 宗教 | 国籍 | 地址 | 电话
                    new_row = [
                        name_en, 
                        name_cn, 
                        cls, 
                        str(mykid), # 强制转为文字防止变成科学计数法
                        gender.split(" ")[0], # 只取"男"或"女"
                        str(dob), 
                        race.split(" ")[0], # 只取"华裔"
                        religion.split(" ")[0], 
                        nationality, 
                        address, 
                        "'" + str(guardian_phone) # 加个单引号防止Excel把电话前面的0吃掉
                    ]
                    
                    sheet.append_row(new_row)
                    st.success(f"✅ 学生 {name_en} 资料已录入成功！")
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
