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

# === 功能 B: 录入新学生 (最终完整版) ===
elif menu == "➕ 录入新学生":
    st.title("📝 新生详细资料录入")
    
    with st.form("add_student_form"):
        # 创建两个标签页，把复杂的资料分开填
        tab1, tab2 = st.tabs(["👤 学生个人资料", "👨‍👩‍👧‍👦 父母家庭资料"])
        
        # === 标签页 1: 学生资料 ===
        with tab1:
            st.subheader("基本信息")
            col1, col2 = st.columns(2)
            with col1:
                name_en = st.text_input("学生姓名 (Name)")
                mykid = st.text_input("身份证/MyKid (无横杠)")
                dob = st.date_input("出生日期")
            with col2:
                name_cn = st.text_input("中文姓名")
                cls = st.selectbox("班级", ["1A", "1B", "1C", "1D", "2A", "2B", "3A", "3B", "4A", "4B", "5A", "5B", "6A", "6B"])
                gender = st.radio("性别", ["男", "女"], horizontal=True)

            st.subheader("背景资料")
            col3, col4, col5 = st.columns(3)
            with col3:
                race = st.selectbox("种族", ["华裔", "巫裔", "印裔", "其他"])
            with col4:
                religion = st.selectbox("宗教", ["佛教", "伊斯兰教", "基督教", "兴都教", "道教", "其他"])
            with col5:
                nationality = st.selectbox("国籍", ["马来西亚公民", "非公民", "永久居民"])
            
            address = st.text_area("家庭住址 (Alamat Rumah)")

        # === 标签页 2: 家长资料 ===
        with tab2:
            st.info("💡 提示：用于申请 RMT/KWAPM 援助金的重要资料")
            
            # --- 父亲资料 ---
            st.markdown("#### 👨 父亲资料 (Bapa)")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                father_name = st.text_input("父亲姓名")
                father_job = st.selectbox("父亲职业", ["公务员", "私人界", "自雇", "无业/退休", "已故"])
            with col_f2:
                father_ic = st.text_input("父亲 IC")
                father_income = st.number_input("父亲月收入 (RM)", min_value=0, step=100)

            st.divider() # 画一条分割线

            # --- 母亲资料 ---
            st.markdown("#### 👩 母亲资料 (Ibu)")
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                mother_name = st.text_input("母亲姓名")
                mother_job = st.selectbox("母亲职业", ["公务员", "私人界", "自雇", "家庭主妇", "已故"])
            with col_m2:
                mother_ic = st.text_input("母亲 IC")
                mother_income = st.number_input("母亲月收入 (RM)", min_value=0, step=100)
            
            st.divider()
            
            # --- 紧急联系 ---
            guardian_phone = st.text_input("📞 监护人/紧急电话")

        # === 提交区域 ===
        st.markdown("---")
        submitted = st.form_submit_button("💾 保存完整档案", use_container_width=True)
        
        if submitted:
            if not name_en or not mykid:
                st.error("❌ 无法保存：学生姓名和身份证号必须填写！")
            else:
                with st.spinner("正在计算家庭收入并写入数据库..."):
                    # 自动计算总收入
                    total_income = father_income + mother_income
                    
                    # 准备写入的数据 (共 20 列)
                    # 顺序要对应: A-K (旧) + L-T (新)
                    new_row = [
                        name_en, name_cn, cls, "'" + str(mykid), 
                        gender.split(" ")[0], str(dob), 
                        race, religion, nationality, address, 
                        "'" + str(guardian_phone),
                        # 新增的家长部分
                        father_name, "'" + str(father_ic), father_job, father_income,
                        mother_name, "'" + str(mother_ic), mother_job, mother_income,
                        total_income # 自动算的
                    ]
                    
                    sheet.append_row(new_row)
                    st.success(f"✅ 成功录入：{name_en} (家庭总收入: RM {total_income})")
                    st.balloons() # 放个气球庆祝一下
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
