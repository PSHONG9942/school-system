import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- 1. 页面配置 ---
st.set_page_config(page_title="学校资料管理系统", layout="wide")

# --- 2. 连接 Google Sheets ---
@st.cache_resource
def get_connection():
    key_dict = {
        "type": "service_account",
        "project_id": st.secrets["project_id"],
        "private_key_id": st.secrets["private_key_id"],
        "private_key": st.secrets["private_key"],
        "client_email": st.secrets["client_email"],
        "client_id": st.secrets["client_id"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": st.secrets["client_x509_cert_url"],
        "universe_domain": "googleapis.com"
    }
    
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    # 你的表格 ID (保持不变)
    sheet = client.open_by_key("1yuqfbLmJ_IIFInB_XyKEula17Kyse6FGeqvZgh-Rn94").sheet1
    return sheet

try:
    sheet = get_connection()
except Exception as e:
    st.error(f"❌ 连接失败: {e}")
    st.stop()

# --- 3. 辅助函数：读取数据 (这是修复核心！) ---
def load_data():
    # 🟢 改动 1: 使用 get_all_values 而不是 get_all_records
    # 这样能保证读回来的全部是 String (纯文字)，0 不会被吃掉
    data = sheet.get_all_values()
    
    # 第一行是表头，后面是数据
    if len(data) > 0:
        headers = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=headers)
        return df
    else:
        return pd.DataFrame()

# --- 4. 界面逻辑 ---
with st.sidebar:
    st.title("🏫 校务系统")
    st.markdown(f"当前连接数据库: `school_database`")
    menu = st.radio("功能导航", ["📊 学生列表", "➕ 录入新学生", "🔍 资料查询"])

# === 功能 A: 学生列表 ===
if menu == "📊 学生列表":
    st.title("全校学生名册")
    
    if st.button("🔄 刷新数据"):
        st.cache_data.clear()
        
    df = load_data()
    
    if df.empty:
        st.info("表格为空，请先录入数据。")
    else:
        # 🟢 即使数据已经是文字了，我们还是强制配置一下，确保万无一失
        st.dataframe(
            df, 
            use_container_width=True,
            column_config={
                "身份证/MyKid": st.column_config.TextColumn("身份证/MyKid"),
                "监护人电话": st.column_config.TextColumn("监护人电话"),
                "父亲IC": st.column_config.TextColumn("父亲IC"),
                "母亲IC": st.column_config.TextColumn("母亲IC"),
            }
        )

# === 功能 B: 录入新学生 (修复版) ===
elif menu == "➕ 录入新学生":
    st.title("📝 新生/现有学生资料录入")
    st.info("💡 系统会自动根据身份证号判断是【新增】还是【更新】。")
    
    with st.form("add_student_form"):
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
            
            address = st.text_area("家庭住址")

        # === 标签页 2: 家长资料 ===
        with tab2:
            st.info("💡 提示：用于申请 RMT/KWAPM 援助金的重要资料")
            st.markdown("#### 👨 父亲资料 (Bapa)")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                father_name = st.text_input("父亲姓名")
                father_job = st.selectbox("父亲职业", ["公务员", "私人界", "自雇", "无业/退休", "已故"])
            with col_f2:
                father_ic = st.text_input("父亲 IC")
                father_income = st.number_input("父亲月收入 (RM)", min_value=0, step=100)

            st.divider()
            st.markdown("#### 👩 母亲资料 (Ibu)")
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                mother_name = st.text_input("母亲姓名")
                mother_job = st.selectbox("母亲职业", ["公务员", "私人界", "自雇", "家庭主妇", "已故"])
            with col_m2:
                mother_ic = st.text_input("母亲 IC")
                mother_income = st.number_input("母亲月收入 (RM)", min_value=0, step=100)
            
            st.divider()
            guardian_phone = st.text_input("📞 监护人/紧急电话")

        # === 提交逻辑 ===
        st.markdown("---")
        submitted = st.form_submit_button("💾 保存 / 更新资料", use_container_width=True)
        
        if submitted:
            if not name_en or not mykid:
                st.error("❌ 无法保存：学生姓名和身份证号必须填写！")
            else:
                with st.spinner("正在处理数据..."):
                    total_income = father_income + mother_income
                    # 准备写入的数据 (强制把数字转为 str 字符串)
                    new_row = [
                        name_en, name_cn, cls, str(mykid), 
                        gender.split(" ")[0], str(dob), 
                        race, religion, nationality, address, 
                        str(guardian_phone), 
                        father_name, str(father_ic), father_job, father_income,
                        mother_name, str(mother_ic), mother_job, mother_income,
                        total_income
                    ]
                    
                    try:
                        # 🟢 改动 2: 获取所有 ID 时，强制转为字符串 (str) 并且去掉空格 (strip)
                        # 这样能保证 "90402" 和 90402 也能匹配上
                        all_values = sheet.col_values(4) # 获取第4列
                        all_ids_str = [str(x).strip() for x in all_values] 
                        current_id = str(mykid).strip()
                        
                        if current_id in all_ids_str:
                            # === 更新 ===
                            row_index = all_ids_str.index(current_id) + 1
                            sheet.update(range_name=f"A{row_index}:T{row_index}", values=[new_row])
                            st.warning(f"⚠️ 检测到 IC {mykid} 已存在，已成功更新资料！")
                        else:
                            # === 新增 ===
                            sheet.append_row(new_row)
                            st.success(f"✅ 新增成功：{name_en}")
                            st.balloons()

                        st.cache_data.clear()
                        
                    except Exception as e:
                        st.error(f"发生错误: {e}")

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
            # 同样配置一下显示格式
            st.dataframe(result, use_container_width=True, 
                         column_config={"身份证/MyKid": st.column_config.TextColumn("身份证/MyKid")})
        else:
            st.warning("未找到相关记录。")
