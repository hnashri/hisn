# Hisn interface (Streamlit)
# run it with: python -m streamlit run app.py

import streamlit as st
from hisn import analyze

# the name i want on the browser tab instead of Streamlit
st.set_page_config(page_title="حصن")

# Arabic font right to left and the pattern bar at the top
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

# streamlit runs the whole file again on every click
# so I keep the current page in session_state
if "page" not in st.session_state:
    st.session_state.page = "welcome"

# welcome page
if st.session_state.page == "welcome":
    st.markdown("""
    <div class="center">
      <h1>حصن</h1>
      <h3>هل كلمة مرورك آمنة فعلًا؟</h3>
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
    # this is a demo online so i tell people to try a similar password not their real one
    st.caption("هذه نسخة تجريبية، جرّب كلمة مرور مشابهة لكلمتك وليست كلمتك الحقيقية.")

    if st.button("افحص") and password:
        result = analyze(password)

        # streamlit has no "yellow" text color so orange is used instead
        if result["color"] == "yellow":
            color = "orange"
        else:
            color = result["color"]
        col1, col2 = st.columns(2)
        col1.metric("الدرجة", f"{result['score']} / 100")
        col2.metric("الوقت المتوقع للكسر (أسوأ حالة)", result["crack_time"])
        st.markdown(f"**المستوى:** :{color}[{result['level']}]")
        # st.progress is always one color so I draw my own bar
        # red for weak orange for medium green for strong
        bar_colors = {"red": "#b3261e", "yellow": "#c77700", "green": "#2e5e3e"}
        bar = bar_colors[result["color"]]
        st.markdown(
            f'<div style="background:#ece0c8;border-radius:6px;height:10px">'
            f'<div style="background:{bar};width:{result["score"]}%;height:10px;border-radius:6px"></div></div>',
            unsafe_allow_html=True)

        # the time changes with the type of attack so I show all 3
        times = result["crack_times"]
        st.markdown(f"""
| نوع الهجوم | الوقت المتوقع |
|---|---|
| عبر الموقع نفسه (الموقع يحدّ من المحاولات) | {times["online"]} |
| قاعدة بيانات مسروقة بتشفير ضعيف (أسوأ حالة) | {times["fast"]} |
| قاعدة بيانات مسروقة بتشفير قوي مثل bcrypt | {times["slow"]} |
""")

        # problems (red/yellow) first blue notes after them
        problems = []
        infos = []
        for f in result["findings"]:
            if f["severity"] == "blue":
                infos.append(f)
            else:
                problems.append(f)

        if not problems:
            st.success("لم تُكتشف أي مشكلة واضحة.")

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
- **المعيار العالمي (NIST SP 800-63B-4، 2025):** 15 حرفًا على الأقل إذا كانت كلمة المرور وحدها تحمي الحساب، و8 أحرف فقط مع التحقق الثنائي. يمنع فرض خلط أنواع الأحرف، ويقبل المسافات وجميع الرموز، ولا يشترط تغيير كلمة المرور دوريًا إلا عند تسريبها.
- **الهيئة الوطنية للأمن السيبراني (الضابط 2-2-3-1):** تُلزم كل جهة بسياسة تشمل الطول والتعقيد ومدة الصلاحية والقفل، دون تحديد أرقام موحدة.
- **الوقت المتوقع للكسر:** تقدير تقريبي يفترض أن المخترق يجرب قوائم الأسماء والسنوات أولًا. يختلف حسب نوع الهجوم: عبر الموقع (100 محاولة في الساعة)، أو قاعدة بيانات مسروقة بتشفير ضعيف (10 مليارات محاولة في الثانية)، أو بتشفير قوي مثل bcrypt (10 آلاف محاولة في الثانية). والدرجة تُحسب من أسوأ حالة، فكلما طال الوقت ارتفعت الدرجة.
- **البنك المركزي السعودي (الضابط 3.1.5):** يطلب من الجهات سياسة قوية لكلمات المرور، تشمل إيقاف الوصول بعد 3 محاولات خاطئة متتالية.
""")

# privacy note at the bottom of the welcome page
if st.session_state.page == "welcome":
    st.caption("لا يحفظ حصن كلمة المرور ولا يسجّلها.")
