import streamlit as st
from hisn import analyze

# ===== style: font, right-to-left, centering, and the Saudi pattern bar =====
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

# ===== Welcome page =====
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

# ===== Check page =====
else:
    st.title("حصن")
    password = st.text_input("كلمة المرور", type="password")
    st.caption("لا يحفظ حصن كلمة المرور ولا يسجّلها.")

    if st.button("افحص") and password:
        result = analyze(password)

        color = {"red": "red", "yellow": "orange", "green": "green"}[result["color"]]
        st.metric("الدرجة", f"{result['score']} / 100")
        st.markdown(f"**المستوى:** :{color}[{result['level']}]")
        st.progress(result["score"] / 100)

        if not result["findings"]:
            st.success("لم تُكتشف أي مشكلة واضحة.")
        for f in result["findings"]:
            if f["severity"] == "red":
                st.error(f["ar"])
            else:
                st.warning(f["ar"])

if st.session_state.page == "welcome":
    st.caption("لا يحفظ حصن كلمة المرور ولا يسجّلها.")
