import streamlit as st
import pandas as pd

# 1. 页面基本设置
st.set_page_config(page_title="简易学校管理系统", layout="wide")

# 初始化数据
if 'students' not in st.session_state:
    st.session_state['students'] = pd.DataFrame({
        "姓名": ["张伟", "李敏"],
        "班级": ["1A", "1B"],
        "身份证号": ["150101-10-1234", "150202-10-5678"]
    })

# 2. 侧边栏菜单
with st.sidebar:
    st.title("🏫 校务系统")
    menu = st.radio("功能导航", ["📊 学生列表", "➕ 录入新学生", "🔍 资料查询"])

# --- 页面 1：查看列表 ---
if menu == "📊 学生列表":
    st.title("全校学生名册")
    st.info("提示：当前为演示版，数据存储在临时内存中。")
    df = st.session_state['students']
    st.dataframe(df, use_container_width=True)

# --- 页面 2：录入数据 ---
elif menu == "➕ 录入新学生":
    st.title("新生资料录入")
    with st.form("add_student_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("学生姓名")
            ic_no = st.text_input("身份证号")
        with col2:
            cls = st.selectbox("班级", ["1A", "1B", "1C", "1D", "2A"])
            gender = st.radio("性别", ["男", "女"], horizontal=True)
        submitted = st.form_submit_button("💾 保存资料")
        if submitted:
            new_student = pd.DataFrame({"姓名": [name], "班级": [cls], "身份证号": [ic_no]})
            st.session_state['students'] = pd.concat([st.session_state['students'], new_student], ignore_index=True)
            st.success(f"✅ 成功录入学生：{name}")

# --- 页面 3：简单查询 ---
elif menu == "🔍 资料查询":
    st.title("快速搜索")
    search_term = st.text_input("输入姓名或身份证号进行查找")
    if search_term:
        df = st.session_state['students']
        result = df[df.astype(str).apply(lambda x: x.str.contains(search_term, case=False)).any(axis=1)]
        if not result.empty:
            st.success(f"找到 {len(result)} 条结果：")
            st.table(result)
        else:
            st.warning("未找到相关学生。")
