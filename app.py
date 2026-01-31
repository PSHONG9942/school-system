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

try:
    client = get_connection()
    sheet = client.open_by_key("1yuqfbLmJ_IIFInB_XyKEula17Kyse6FGeqvZgh-Rn94").sheet1
    att_sheet = client.open_by_key("1yuqfbLmJ_IIFInB_XyKEula17Kyse6FGeqvZgh-Rn94").worksheet("attendance")
except Exception as e:
    st.error(f"❌ 连接失败: {e}")
    st.stop()

# --- 3. 辅助函数 ---
def load_data():
    data = sheet.get_all_values()
    if len(data) > 0:
        return pd.DataFrame(data[1:], columns=data[0])
    return pd.DataFrame()

# 日期转换辅助函数 (把字符串转回日期对象)
def parse_date(date_str):
    try:
        return datetime.datetime.strptime(str(date_str), "%Y-%m-%d").date()
    except:
        return datetime.date.today() # 如果格式不对，默认今天

# PDF 生成器
def generate_pdf(student_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('NotoSansSC', '', 'NotoSansSC-Regular.ttf', uni=True)
    pdf.set_font("NotoSansSC", size=12)
    name = str(student_data.get('学生姓名', 'Student'))
    pdf.set_font_size(16)
    pdf.cell(200, 10, txt=f"学生个人档案: {name}", ln=1, align='C')
    pdf.ln(10)
    pdf.set_font_size(12)
    fields = ['班级', '身份证/MyKid', '性别', '出生日期', '种族', '宗教', '国籍', '家庭住址', '监护人电话']
    for field in fields:
        value = str(student_data.get(field, '-'))
        pdf.cell(200, 10, txt=f"{field}: {value}", ln=1)
    return pdf.output(dest='S').encode('latin-1')

# --- 4. 界面逻辑 ---

# 🌟 定义输入框的 Keys 列表 (方便批量管理)
input_keys = [
    "name_en", "mykid", "dob", "name_cn", "cls", "gender",
    "race", "religion", "nationality", "address",
    "father_name", "father_job", "father_ic", "father_income",
    "mother_name", "mother_job", "mother_ic", "mother_income",
    "guardian_phone"
]

with st.sidebar:
    st.title("🏫 旗舰校务系统")
    st.markdown("---")
    
    # 🌟 关键修改：给菜单加 key，这样我们可以用代码控制它跳转
    # 如果 session_state 里没有菜单状态，初始化为默认
    if "menu_nav" not in st.session_state:
        st.session_state["menu_nav"] = "📊 学生列表"

    menu = st.radio(
        "系统菜单", 
        ["📊 学生列表", "📅 每日点名", "➕ 录入新学生", "🔍 查询与打印"],
        key="menu_nav" # 绑定到 session_state
    )
    
    st.markdown("---")
    if st.button("🔄 强制刷新数据"):
        st.cache_data.clear()

# ==========================================
# 📊 功能 A: 智能分班名册 + 编辑功能 (修复版)
# ==========================================
if menu == "📊 学生列表":
    st.title("📚 分班学生名册")
    df = load_data()
    
    # --- 🟢 定义回调函数：专门处理跳转和填表逻辑 ---
    # 这个函数会在点击按钮的一瞬间运行，早于页面刷新
    def edit_student_callback(row):
        # 1. 切换菜单到录入页
        st.session_state["menu_nav"] = "➕ 录入新学生"
        
        # 2. 填入所有资料
        st.session_state['name_en'] = row['学生姓名']
        st.session_state['name_cn'] = row['中文姓名']
        st.session_state['cls'] = row['班级']
        st.session_state['mykid'] = str(row['身份证/MyKid'])
        st.session_state['dob'] = parse_date(row['出生日期'])
        
        # 性别处理 (确保和 Radio 选项完全一致)
        # 如果你的 Excel 里存的是 "男"，这里就没问题
        st.session_state['gender'] = row['性别'] 

        st.session_state['race'] = row['种族']
        st.session_state['religion'] = row['宗教']
        st.session_state['nationality'] = row['国籍']
        st.session_state['address'] = row['住址']
        st.session_state['guardian_phone'] = str(row['监护人电话'])
        
        st.session_state['father_name'] = row['父亲姓名']
        st.session_state['father_ic'] = str(row['父亲IC'])
        st.session_state['father_job'] = row['父亲职业']
        try: st.session_state['father_income'] = int(float(row['父亲收入']))
        except: st.session_state['father_income'] = 0

        st.session_state['mother_name'] = row['母亲姓名']
        st.session_state['mother_ic'] = str(row['母亲IC'])
        st.session_state['mother_job'] = row['母亲职业']
        try: st.session_state['mother_income'] = int(float(row['母亲收入']))
        except: st.session_state['mother_income'] = 0

    # ---------------------------------------------

    if df.empty:
        st.warning("⚠️ 数据库为空。")
    else:
        if '班级' in df.columns:
            available_classes = sorted(df['班级'].unique().tolist())
        else:
            available_classes = []

        col1, col2 = st.columns([1, 3])
        with col1:
            selected_class = st.selectbox(
                "📂 请选择要查看的班级：", 
                ["请选择..."] + available_classes
            )
        
        if selected_class != "请选择...":
            class_df = df[df['班级'] == selected_class]
            
            # --- 顶部统计 ---
            boys = class_df[class_df['性别'].astype(str).str.contains('男')].shape[0] if '性别' in class_df.columns else 0
            girls = class_df[class_df['性别'].astype(str).str.contains('女')].shape[0] if '性别' in class_df.columns else 0
            
            m1, m2, m3 = st.columns(3)
            m1.metric("👩‍🎓 全班人数", f"{len(class_df)} 人")
            m2.metric("👦 男生", f"{boys} 人")
            m3.metric("👧 女生", f"{girls} 人")
            st.divider()
            
            # --- 🛠️ 修改资料功能 (修复报错的关键点) ---
            st.markdown("#### 🛠️ 修改资料")
            student_list = class_df['学生姓名'].tolist()
            student_to_edit = st.selectbox("选择要修改的学生:", ["(请选择)"] + student_list)
            
            if student_to_edit != "(请选择)":
                # 1. 先把这一行数据找出来
                student_row = class_df[class_df['学生姓名'] == student_to_edit].iloc[0]
                
                # 2. 🟢 按钮绑定 on_click 回调
                # 注意：这里我们不再在 if 里写逻辑，而是把逻辑交给 edit_student_callback
                st.button(
                    f"✏️ 编辑 {student_to_edit} 的资料", 
                    type="primary",
                    on_click=edit_student_callback,  # 绑定函数
                    args=(student_row,)              # 把学生资料传给函数
                )
                # 点击后，页面会自动刷新并跳转，且不会报错！

            st.divider()
            
            # --- 底部：名单表格 ---
            st.dataframe(
                class_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "身份证/MyKid": st.column_config.TextColumn("身份证/MyKid"),
                    "监护人电话": st.column_config.TextColumn("监护人电话"),
                    "父亲IC": st.column_config.TextColumn("父亲IC"),
                    "母亲IC": st.column_config.TextColumn("母亲IC"),
                    "家庭总收入": st.column_config.NumberColumn("家庭总收入", format="RM %d")
                }
            )

# ==========================================
# 📅 功能 2: 智能每日点名
# ==========================================
elif menu == "📅 每日点名":
    st.title("📅 每日出席记录")
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("选择日期", datetime.date.today())
    with col2:
        selected_class = st.selectbox("选择班级", ["1A", "2A", "3A", "4A", "5A", "6A"])
    
    st.divider()

    if st.button("🚀 开始点名", type="primary"):
        st.session_state['attendance_loaded'] = True
    
    if st.session_state.get('attendance_loaded'):
        df = load_data()
        class_students = df[df['班级'] == selected_class]
        
        if class_students.empty:
            st.warning(f"⚠️ {selected_class} 还没有学生资料。")
        else:
            st.subheader(f"📋 {selected_class} 点名表")
            attendance_df = class_students[['学生姓名', '身份证/MyKid']].copy()
            attendance_df['当前状态'] = "✅ 出席"
            attendance_df['缺席备注'] = ""

            edited_df = st.data_editor(
                attendance_df,
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                column_config={
                    "学生姓名": st.column_config.TextColumn("学生姓名", disabled=True),
                    "身份证/MyKid": st.column_config.TextColumn("身份证/MyKid", disabled=True),
                    "当前状态": st.column_config.SelectboxColumn(
                        "出席状态",
                        options=["✅ 出席", "😷 病假 (Sakit)", "🏠 事假 (Urusan Keluarga)", "❌ 旷课 (Ponteng)", "📝 迟到 (Lewat)", "🏫 代表学校 (Wakil Sekolah)", "❓ 其他 (Lain-lain)"],
                        required=True
                    ),
                    "缺席备注": st.column_config.TextColumn("备注 (如有)")
                }
            )

            if st.button("💾 提交今日记录", use_container_width=True):
                with st.spinner("正在写入..."):
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    rows_to_add = []
                    for index, row in edited_df.iterrows():
                        rows_to_add.append([
                            str(date), selected_class, row['学生姓名'], row['当前状态'], row['缺席备注'], timestamp
                        ])
                    att_sheet.append_rows(rows_to_add)
                    st.success("✅ 点名完成！")
                    st.balloons()

# ==========================================
# ➕ 功能 B: 录入新学生 (手动清空 & 预填充版)
# ==========================================
elif menu == "➕ 录入新学生":
    st.title("📝 资料录入 / 修改")
    
    # 1. 顶部操作栏
    c1, c2 = st.columns([3, 1])
    with c1:
        st.info("💾 保存后表单【不会】自动清空，方便您检查。如需录入下一位，请点击右侧【🆕 新增学生】按钮。")
    with c2:
        # 🌟 新增功能：手动清空按钮
        if st.button("🆕 新增学生 (清空)", type="secondary", use_container_width=True):
            # 清除所有 Session State 里的输入框记录
            for key in input_keys:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    with st.form("add_student_form"):
        tab1, tab2 = st.tabs(["👤 学生个人资料", "👨‍👩‍👧‍👦 父母家庭资料"])
        
        with tab1:
            st.subheader("基本信息")
            col1, col2 = st.columns(2)
            with col1:
                name_en = st.text_input("学生姓名 (Name)", key="name_en")
                mykid = st.text_input("身份证/MyKid (无横杠)", key="mykid", help="这是识别学生身份的唯一号码，修改时以此为准")
                dob = st.date_input("出生日期", key="dob")
            with col2:
                name_cn = st.text_input("中文姓名", key="name_cn")
                cls = st.selectbox("班级", ["1A", "2A", "3A", "4A", "5A", "6A"], key="cls")
                gender = st.radio("性别", ["男", "女"], horizontal=True, key="gender")

            st.subheader("背景资料")
            col3, col4, col5 = st.columns(3)
            with col3:
                race = st.selectbox("种族", ["华裔", "巫裔", "印裔", "其他"], key="race")
            with col4:
                religion = st.selectbox("宗教", ["佛教", "伊斯兰教", "基督教", "兴都教", "道教", "其他"], key="religion")
            with col5:
                nationality = st.selectbox("国籍", ["马来西亚公民", "非公民", "永久居民"], key="nationality")
            address = st.text_area("家庭住址", key="address")

        with tab2:
            st.markdown("#### 👨 父亲资料")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                father_name = st.text_input("父亲姓名", key="father_name")
                father_job = st.selectbox("父亲职业", ["公务员", "私人界", "自雇", "无业/退休", "已故"], key="father_job")
            with col_f2:
                father_ic = st.text_input("父亲 IC", key="father_ic")
                father_income = st.number_input("父亲月收入 (RM)", min_value=0, step=100, key="father_income")

            st.divider()
            st.markdown("#### 👩 母亲资料")
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                mother_name = st.text_input("母亲姓名", key="mother_name")
                mother_job = st.selectbox("母亲职业", ["公务员", "私人界", "自雇", "家庭主妇", "已故"], key="mother_job")
            with col_m2:
                mother_ic = st.text_input("母亲 IC", key="mother_ic")
                mother_income = st.number_input("母亲月收入 (RM)", min_value=0, step=100, key="mother_income")
            
            st.divider()
            guardian_phone = st.text_input("📞 监护人/紧急电话", key="guardian_phone")

        st.markdown("---")
        if st.form_submit_button("💾 保存 / 更新资料", use_container_width=True):
            if not name_en or not mykid:
                st.error("❌ 姓名和身份证号必须填写！")
            else:
                with st.spinner("正在处理..."):
                    total_income = father_income + mother_income
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
                        all_values = sheet.col_values(4) 
                        all_ids_str = [str(x).strip() for x in all_values] 
                        current_id = str(mykid).strip()
                        
                        if current_id in all_ids_str:
                            row_index = all_ids_str.index(current_id) + 1
                            sheet.update(range_name=f"A{row_index}:T{row_index}", values=[new_row])
                            st.success(f"✅ 更新成功：{name_en} 的资料已保存！")
                        else:
                            sheet.append_row(new_row)
                            st.success(f"✅ 新增成功：{name_en}")
                        
                        st.cache_data.clear()
                        # ⚠️ 这里去掉了清空和 st.rerun()，所以资料会保留在屏幕上
                        
                    except Exception as e:
                        st.error(f"发生错误: {e}")

# ==========================================
# 🔍 功能 4: 查询与 PDF
# ==========================================
elif menu == "🔍 查询与打印":
    st.title("🔍 学生档案查询")
    search_term = st.text_input("输入姓名或身份证号")
    if search_term:
        df = load_data()
        result = df[df.astype(str).apply(lambda x: x.str.contains(search_term, case=False)).any(axis=1)]
        if not result.empty:
            st.success(f"找到 {len(result)} 位学生")
            for index, row in result.iterrows():
                with st.expander(f"👤 {row['学生姓名']} ({row['班级']})"):
                    st.write(row)
                    pdf_data = generate_pdf(row)
                    st.download_button(label="📄 下载 PDF", data=pdf_data, file_name=f"{row['学生姓名']}.pdf", mime="application/pdf")
        else:
            st.warning("查无此人。")
