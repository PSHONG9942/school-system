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

# --- PDF 生成器 (中文完美版) ---
def generate_pdf(student_data):
    pdf = FPDF()
    pdf.add_page()
    
    # ============================================
    # 关键步骤：加载中文字体！
    # 确保你已经把 NotoSans-Regular.ttf 上传到了 GitHub
    # ============================================
    # 参数说明：'NotoSans'是给字体起的名字，''是样式(默认)，后面是文件名，uni=True表示使用Unicode
    pdf.add_font('NotoSansSC', '', 'NotoSansSC-Regular.ttf', uni=True)
    
    # 设置使用刚才加载的字体
    pdf.set_font("NotoSansSC", size=12)
    
    # --- 1. 标题 ---
    # 获取学生姓名，如果没有就显示 'Student'
    name = str(student_data.get('学生姓名', 'Student'))
    
    pdf.set_font_size(16) # 设置标题字号
    # 写入标题 (现在可以直接写中文了！)
    pdf.cell(200, 10, txt=f"学生个人档案: {name}", ln=1, align='C')
    pdf.ln(10) # 空一行
    
    # --- 2. 内容 ---
    pdf.set_font_size(12) # 设置正文字号
    
    # 需要打印的字段 (可以直接用中文表头了)
    fields = ['班级', '身份证/MyKid', '性别', '出生日期', '种族', '宗教', '国籍', '家庭住址', '监护人电话']
    
    for field in fields:
        # 获取数据，如果为空就显示 '-'
        value = str(student_data.get(field, '-'))
        
        # 写入 PDF (直接拼接，不需要之前的那些 encode/decode 清洗了)
        pdf.cell(200, 10, txt=f"{field}: {value}", ln=1)
        
    # 输出 PDF 文件数据
    return pdf.output(dest='S').encode('latin-1')

# --- 4. 界面逻辑 ---
with st.sidebar:
    st.title("🏫 旗舰校务系统")
    st.markdown("---")
    menu = st.radio("系统菜单", ["📊 学生列表", "📅 每日点名", "➕ 资料录入", "🔍 查询与打印"])
    st.markdown("---")
    if st.button("🔄 强制刷新数据"):
        st.cache_data.clear()

# ==========================================
# 📊 功能 A: 智能分班名册 (Student List)
# ==========================================
if menu == "📊 学生列表":
    st.title("📚 分班学生名册")
    
    # 1. 先读取所有数据
    df = load_data()
    
    if df.empty:
        st.warning("⚠️ 数据库为空，请先去【资料录入】添加学生。")
    else:
        # --- 步骤 1: 提取所有班级选项 ---
        # 自动从表格里找出所有的班级，并自动排序 (例如 1A, 1B, 2A...)
        # 这里的 '班级' 必须和你 Google Sheet 的表头文字一模一样
        if '班级' in df.columns:
            available_classes = sorted(df['班级'].unique().tolist())
        else:
            st.error("❌ 错误：表格中找不到【班级】这一列，请检查 Google Sheet 表头！")
            st.stop()
            
        # --- 步骤 2: 班级选择器 (核心功能) ---
        # 默认加一个 "请选择" 的选项，让界面更清爽
        col1, col2 = st.columns([1, 3])
        with col1:
            selected_class = st.selectbox(
                "📂 请选择要查看的班级：", 
                ["请选择..."] + available_classes  # 列表合并
            )
        
        # --- 步骤 3: 根据选择显示内容 ---
        if selected_class == "请选择...":
            st.info("👈 请在左上方选择一个班级以查看名单。")
            st.image("https://cdn-icons-png.flaticon.com/512/2921/2921226.png", width=100) # 加个小图标装饰
            
        else:
            # === 过滤数据：只保留该班级的学生 ===
            class_df = df[df['班级'] == selected_class]
            
            # === 顶部：班级小统计 (Dashboard style) ===
            st.markdown(f"### 🏫 {selected_class} 班级概况")
            
            # 计算男女生人数 (防止表格里没有性别列报错)
            if '性别' in class_df.columns:
                boys = class_df[class_df['性别'].astype(str).str.contains('男')].shape[0]
                girls = class_df[class_df['性别'].astype(str).str.contains('女')].shape[0]
            else:
                boys = 0
                girls = 0
            
            # 显示漂亮的统计卡片
            m1, m2, m3 = st.columns(3)
            m1.metric("👩‍🎓 全班人数", f"{len(class_df)} 人")
            m2.metric("👦 男生", f"{boys} 人")
            m3.metric("👧 女生", f"{girls} 人")
            
            st.divider()
            
            # === 底部：详细名单表格 ===
            # 这里依然保留我们要的 column_config，防止 0 被吃掉
            st.dataframe(
                class_df,
                use_container_width=True,
                hide_index=True, # 隐藏左边那列 0,1,2 序号，看起来更干净
                column_config={
                    "身份证/MyKid": st.column_config.TextColumn("身份证/MyKid", help="身份识别码"),
                    "监护人电话": st.column_config.TextColumn("监护人电话"),
                    "父亲IC": st.column_config.TextColumn("父亲IC"),
                    "母亲IC": st.column_config.TextColumn("母亲IC"),
                    "家庭总收入": st.column_config.NumberColumn("家庭总收入", format="RM %d") # 顺便给钱加个RM单位
                }
            )
            
            # === 额外功能：一键下载该班名单 ===
            # 把当前筛选出来的 class_df 转成 CSV 供下载
            csv = class_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"📥 下载 {selected_class} 班名单 (Excel/CSV)",
                data=csv,
                file_name=f"NameList_{selected_class}.csv",
                mime='text/csv',
            )

# ==========================================
# 📅 功能 2: 智能每日点名 (Excel 模式)
# ==========================================
elif menu == "📅 每日点名":
    st.title("📅 每日出席记录")
    
    # 1. 顶部选择器
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("选择日期", datetime.date.today())
    with col2:
        # 这里保留了我们之前约定的 A 班制
        selected_class = st.selectbox("选择班级", ["1A", "2A", "3A", "4A", "5A", "6A"])
    
    st.divider()

    # 2. 加载数据
    if st.button("🚀 开始点名", type="primary"):
        st.session_state['attendance_loaded'] = True
    
    # 使用 session_state 防止刷新后表格消失
    if st.session_state.get('attendance_loaded'):
        df = load_data()
        class_students = df[df['班级'] == selected_class]
        
        if class_students.empty:
            st.warning(f"⚠️ {selected_class} 还没有学生资料，请先去录入。")
        else:
            st.subheader(f"📋 {selected_class} 点名表")
            st.caption("💡 提示：所有学生默认为【出席】，直接在表格里修改缺席学生的状态即可。")

            # --- A. 准备点名表格数据 ---
            # 只取姓名和IC，防止无关信息干扰
            attendance_df = class_students[['学生姓名', '身份证/MyKid']].copy()
            # 核心魔法：增加两列，默认设为 "出席" 和 空白
            attendance_df['当前状态'] = "✅ 出席"
            attendance_df['缺席备注'] = ""

            # --- B. 显示智能表格 (Data Editor) ---
            # 这是一个可以编辑的表格！
            edited_df = st.data_editor(
                attendance_df,
                use_container_width=True,
                hide_index=True,  # 隐藏左边的序号
                num_rows="fixed", # 禁止添加/删除行，只能改状态
                column_config={
                    "学生姓名": st.column_config.TextColumn("学生姓名", disabled=True), # 锁住名字不让改
                    "身份证/MyKid": st.column_config.TextColumn("身份证/MyKid", disabled=True),
                    
                    # ✨ 重点：把“当前状态”变成下拉菜单 ✨
                    "当前状态": st.column_config.SelectboxColumn(
                        "出席状态 (点击修改)",
                        help="请选择缺席原因",
                        width="medium",
                        options=[
                            "✅ 出席",
                            "😷 病假 (Sakit)",
                            "🏠 事假 (Urusan Keluarga)",
                            "❌ 旷课 (Ponteng)",
                            "📝 迟到 (Lewat)",
                            "🏫 代表学校 (Wakil Sekolah)",
                            "❓ 其他 (Lain-lain)"
                        ],
                        required=True
                    ),
                    "缺席备注": st.column_config.TextColumn(
                        "备注 (如有)",
                        help="例如：发烧、回乡、车坏...",
                        width="large"
                    )
                }
            )

            # --- C. 保存按钮 ---
            st.markdown("---")
            if st.button("💾 提交今日记录", use_container_width=True):
                with st.spinner("正在写入云端数据库..."):
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    rows_to_add = []
                    
                    # 遍历刚才编辑过的表格 (edited_df)
                    for index, row in edited_df.iterrows():
                        status = row['当前状态']
                        
                        # 只有当状态不是“出席”时，才视为有记录需要特别关注
                        # 但为了记录完整性，我们通常把全班都存进去，方便算出席率
                        
                        # 数据格式: 日期 | 班级 | 姓名 | 状态 | 备注 | 记录时间
                        # (注意：我们在 Excel 也要多加一列“备注”)
                        rows_to_add.append([
                            str(date), 
                            selected_class, 
                            row['学生姓名'], 
                            status,          # 这里会保存 "😷 病假 (Sakit)" 这种详细原因
                            row['缺席备注'], # 具体的备注内容
                            timestamp
                        ])
                    
                    # 写入 Google Sheet 的 attendance 分页
                    att_sheet.append_rows(rows_to_add)
                    st.success(f"✅ {selected_class} 点名完成！已保存 {len(rows_to_add)} 条记录。")
                    st.balloons()
                    # 可以在这里加个清除 session 的操作让表格重置，看你习惯

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
                cls = st.selectbox("班级", ["1A", "2A", "3A", "4A", "5A", "6A"])
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
