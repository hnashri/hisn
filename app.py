import streamlit as st
from hisn import analyze

# style: font, right-to-left, centering, and the Saudi pattern bar
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, h1, h2, h3, p, button, input, label {
    font-family: 'IBM Plex Sans Arabic', sans-serif !important;
}
.main, .block-container { direction: rtl; }
.block-container { padding-top: 3.5rem; }
h1, h2, h3, p, label { text-align: right !important; direction: rtl; }
.center h1, .center h3, .center p { text-align: center !important; }
header[data-testid="stHeader"] {
    background:
      linear-gradient(45deg,  #2e5e3e 25%, transparent 25%) 0 0 / 24px 24px,
      linear-gradient(-45deg, #2e5e3e 25%, transparent 25%) 0 0 / 24px 24px,
      linear-gradient(45deg,  transparent 75%, #b08a4a 75%) 0 0 / 24px 24px,
      linear-gradient(-45deg, transparent 75%, #b08a4a 75%) 0 0 / 24px 24px,
      #ece0c8;
    height: 24px;
}
</style>
""", unsafe_allow_html=True)

# remember which page we are on (welcome or check)
if "page" not in st.session_state:
    st.session_state.page = "welcome"

# welcome page
if st.session_state.page == "welcome":
    st.markdown("""
    <div class="center">
      <h1>حصن</h1>
      <h3>كلمة مرورك، هل هي آمنة فعلًا؟</h3>
      <p>حصن يفحصها كما يفكر المخترق العربي.</p>
    </div>
    """, unsafe_allow_html=True)

    left, middle, right = st.columns([1, 2, 1])
    with middle:
        if st.button("ابدأ الفحص", use_container_width=True):
            st.session_state.page = "check"
            st.rerun()

# check page
else:
    st.title("حصن")
    password = st.text_input("كلمة المرور", type="password")
    st.caption("لا يحفظ حصن كلمة المرور ولا يسجّلها.")

    if st.button("افحص") and password:
        result = analyze(password)

        color = {"red": "red", "yellow": "orange", "green": "green"}[result["color"]]
        col1, col2 = st.columns(2)
        col1.metric("الدرجة", f"{result['score']} / 100")
        col2.metric("الوقت المتوقع للكسر", result["crack_time"])
        st.markdown(f"**المستوى:** :{color}[{result['level']}]")
        st.progress(result["score"] / 100)

        if not [f for f in result["findings"] if f["severity"] != "blue"]:
            st.success("لم تُكتشف أي مشكلة واضحة.")
        problems = [f for f in result["findings"] if f["severity"] != "blue"]
        infos = [f for f in result["findings"] if f["severity"] == "blue"]

        for f in problems:
            if f["severity"] == "red":
                st.error(f["ar"])
            else:
                st.warning(f["ar"])

        if infos:
            st.subheader("معلومات تهمك")
            for f in infos:
                st.info(f["ar"])

        with st.expander("اعرف أكثر عن معايير كلمات المرور"):
            st.markdown("""
- **المعيار العالمي (NIST SP 800-63B):** الحد الأدنى 8 أحرف، ويوصي بـ15، ويقبل المسافات وجميع الرموز، ولا يشترط تغيير كلمة المرور دوريًا إلا عند تسريبها.
- **الهيئة الوطنية للأمن السيبراني (الضابط 2-2-3-1):** تُلزم كل جهة بسياسة تشمل الطول والتعقيد ومدة الصلاحية والقفل، دون تحديد أرقام موحدة.
- **الوقت المتوقع للكسر:** تقدير تقريبي لهجوم سريع على جهاز قوي (10 مليارات محاولة في الثانية)، مع افتراض أن المخترق يجرب قوائم الأسماء والسنوات أولًا.
- **البنك المركزي السعودي (الضابط 3.1.5):** يشترط سياسة قوية لكلمات المرور، ويُقفل الحساب بعد 3 محاولات خاطئة.
""")

if st.session_state.page == "welcome":
    st.caption("لا يحفظ حصن كلمة المرور ولا يسجّلها.")
