import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF
import datetime

# --- 1. 页面配置 ---
st.set_page_config(page_title="SJK(C) 旗舰校务系统", layout="wide", page_icon="🏫")

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
    return client

# 获取两个表格：学生表(sheet1) 和 出席表(attendance)
try:
    client = get_connection()
    sheet = client.open_by_key("1yuqfbLmJ_IIFInB_XyKEula17Kyse6FGeqvZgh-Rn94").sheet1
    # ⚠️ 确保你已经创建了名为 attendance 的分页
    att_sheet = client.open_by_key("1yuqfbLmJ_IIFInB_XyKEula17Kyse6FGeqvZgh-Rn94").worksheet("attendance")
except Exception as e:
    st.error(f"❌ 连接失败: {e}\n请检查是否在 Google Sheet新建了 'attendance' 分页！")
    st.stop()

# --- 3. 辅助函数 ---
def load_data():
    data = sheet.get_all_values()
    if len(data) > 0:
        return pd.DataFrame(data[1:], columns=data[0])
    return pd.DataFrame()

# PDF 生成器 (防弹修复版)
def generate_pdf(student_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # 1. 处理标题 (把名字里的中文去掉，防止标题报错)
    name = str(student_data.get('学生姓名', 'Student'))
    # 强力清洗：只保留英文和数字，中文变问号
    name_clean = name.encode('latin-1', 'replace').decode('latin-1')
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=f"Student Profile: {name_clean}", ln=1, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=12)
    
    # 2. 字段映射 (左边是Excel里的中文表头，右边是PDF显示的英文标签)
    # 这样 FPDF 就不会因为看到中文字而崩溃了
    field_map = {
        '班级': 'Class',
        '身份证/MyKid': 'ID/MyKid',
        '性别': 'Gender',
        '出生日期': 'Date of Birth',
        '种族': 'Race',
        '宗教': 'Religion',
        '国籍': 'Nationality',
        '家庭住址': 'Address',
        '监护人电话': 'Phone'
    }
    
    for cn_key, en_label in field_map.items():
        # 获取数据
        value = str(student_data.get(cn_key, '-'))
        
        # 3. 强力清洗内容
        # 如果内容是中文（比如“华裔”），会被替换成 '?'，防止报错
        # (这只是暂时的，为了让功能先跑通)
        value_clean = value.encode('latin-1', 'replace').decode('latin-1') 
        
        # 写入 PDF (使用英文标签)
        pdf.cell(200, 10, txt=f"{en_label}: {value_clean}", ln=1)
        
    return pdf.output(dest='S').encode('latin-1')

# --- 4. 界面逻辑 ---
with st.sidebar:
    st.title("🏫 旗舰校务系统")
    st.markdown("---")
    menu = st.radio("系统菜单", ["📊 校务仪表盘", "📅 每日点名", "➕ 资料录入", "🔍 查询与打印"])
    st.markdown("---")
    if st.button("🔄 强制刷新数据"):
        st.cache_data.clear()

# ==========================================
# 📊 功能 1: 仪表盘 (Dashboard)
# ==========================================
if menu == "📊 校务仪表盘":
    st.title("📊 学校数据概览")
    df = load_data()
    
    if not df.empty:
        # 1. 关键指标卡片
        total_students = len(df)
        
        # 计算 B40 (假设家庭收入 < 4850)
        # 记得要把收入转成数字，去掉可能存在的空格
        df['家庭总收入'] = pd.to_numeric(df['家庭总收入'], errors='coerce').fillna(0)
        b40_count = df[df['家庭总收入'] < 4850].shape[0]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("全校总人数", f"{total_students} 人")
        col2.metric("B40 家庭学生", f"{b40_count} 人", help="家庭收入低于 RM4850")
        col3.metric("平均家庭收入", f"RM {int(df['家庭总收入'].mean())}")
        
        st.divider()
        
        # 2. 图表分析
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("种族分布")
            race_counts = df['种族'].value_counts()
            st.bar_chart(race_counts)
            
        with c2:
            st.subheader("班级人数")
            class_counts = df['班级'].value_counts()
            st.bar_chart(class_counts, color="#ffaa00")

    else:
        st.info("暂无数据，请先录入学生。")

# ==========================================
# 📅 功能 2: 每日点名 (Attendance)
# ==========================================
elif menu == "📅 每日点名":
    st.title("📅 每日出席记录")
    
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("选择日期", datetime.date.today())
    with col2:
        selected_class = st.selectbox("选择班级", ["1A", "1B", "1C", "1D", "2A", "2B", "3A", "3B", "4A", "4B", "5A", "5B", "6A", "6B"])
    
    if st.button("列出学生名单"):
        df = load_data()
        # 筛选出该班级的学生
        class_students = df[df['班级'] == selected_class]
        
        if class_students.empty:
            st.warning(f"{selected_class} 还没有学生资料。")
        else:
            st.subheader(f"{selected_class} 学生名单 ({len(class_students)}人)")
            
            with st.form("attendance_form"):
                # 创建一个字典来存 checkbox 的状态
                status_dict = {}
                st.table(class_students[['学生姓名', '身份证/MyKid']])
                
                st.markdown("### 缺席勾选 (Tick if Absent)")
                # 使用多选框来选缺席的人 (比较快)
                absent_students = st.multiselect("请选择 **缺席** 的学生:", class_students['学生姓名'].tolist())
                
                remark = st.text_input("备注 (例如: 全班去旅行)")
                
                if st.form_submit_button("💾 提交出席率"):
                    with st.spinner("正在保存到 attendance 表格..."):
                        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        rows_to_add = []
                        
                        for student in class_students['学生姓名']:
                            status = "缺席" if student in absent_students else "出席"
                            # 数据格式: 日期 | 班级 | 姓名 | 状态 | 时间
                            rows_to_add.append([str(date), selected_class, student, status, timestamp])
                        
                        att_sheet.append_rows(rows_to_add)
                        st.success(f"✅ 已保存 {selected_class} 的点名记录！")

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

# ==========================================
# 🔍 功能 4: 查询与 PDF (Search & Print)
# ==========================================
elif menu == "🔍 查询与打印":
    st.title("🔍 学生档案查询")
    search_term = st.text_input("输入姓名或身份证号")
    
    if search_term:
        df = load_data()
        # 模糊搜索
        result = df[df.astype(str).apply(lambda x: x.str.contains(search_term, case=False)).any(axis=1)]
        
        if not result.empty:
            st.success(f"找到 {len(result)} 位学生")
            
            for index, row in result.iterrows():
                with st.expander(f"👤 {row['学生姓名']} ({row['班级']})"):
                    # 展示详情
                    st.write(row)
                    
                    # PDF 下载按钮
                    # 注意：Python 标准 PDF 库不支持中文字体，生成的 PDF 中文可能会乱码或消失
                    # 这里仅作为演示，显示基本英文信息
                    pdf_data = generate_pdf(row)
                    st.download_button(
                        label="📄 下载个人档案 (PDF)",
                        data=pdf_data,
                        file_name=f"Profile_{row['学生姓名']}.pdf",
                        mime="application/pdf"
                    )
        else:
            st.warning("查无此人。")
