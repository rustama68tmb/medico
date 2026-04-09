"""
app.py - демо-бот «МЕДИКО» для записи пациентов
Streamlit MVP / воронка лидогенерации
"""

import json
import csv
import os
import re
from datetime import datetime
import streamlit as st

# ── Загрузка данных ────────────────────────────────────────────────
with open("data.json", "r", encoding="utf-8") as f:
    DATA = json.load(f)

CONTACTS = DATA["contacts"]
DOCTORS = DATA["doctors"]
SERVICES = DATA["services"]
PROMOTIONS = DATA["promotions"]
ROUTES = DATA["symptoms_routes"]
URGENT = DATA["urgent_triggers"]
UNCLEAR = DATA["unclear_clarification"]

LEADS_FILE = "leads.csv"

# ── Настройки страницы ─────────────────────────────────────────────
st.set_page_config(
    page_title="МЕДИКО — Запись на приём",
    page_icon="🏥",
    layout="centered",
)

# ── Стили ──────────────────────────────────────────────────────────
st.markdown("""
<style>
.block-container {
    max-width: 680px;
    margin: auto;
    padding-top: 1.5rem;
}
.clinic-header {
    text-align: center;
    padding: 1rem 0 0.5rem;
}
.clinic-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: #1a5276;
}
.clinic-sub {
    font-size: 0.95rem;
    color: #666;
    margin-top: 0.2rem;
}
.card {
    background: #f4f9ff;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin: 0.6rem 0;
    border-left: 4px solid #1a5276;
}
.urgent-card {
    background: #fff0f0;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin: 0.6rem 0;
    border-left: 4px solid #c0392b;
}
.success-card {
    background: #eafaf1;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin: 0.6rem 0;
    border-left: 4px solid #27ae60;
}
.price-tag {
    font-size: 1.1rem;
    font-weight: 700;
    color: #1a5276;
}
.promo-tag {
    font-size: 1rem;
    font-weight: 700;
    color: #c0392b;
}
.doctor-card {
    background: #eaf4fb;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    margin: 0.4rem 0;
}
div[data-testid="column"] .stButton > button {
    width: 100%;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.95rem;
    padding: 0.6rem 0.4rem;
}
.stTextInput > div > input, .stTextArea > div > textarea {
    border-radius: 8px;
}
hr {
    border: none;
    border-top: 1px solid #ddd;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

# ── Инициализация состояния ────────────────────────────────────────
def init():
    defaults = {
        "screen": "main",          # main | symptom | clarify | route | offer | form | confirm | admin
        "complaint": "",
        "duration": "",
        "visit_type": "",
        "route": None,
        "leads": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init()

# ── Вспомогательные функции ────────────────────────────────────────
def go(screen):
    st.session_state.screen = screen
    st.rerun()

def is_urgent(text):
    t = text.lower()
    return any(trigger in t for trigger in URGENT)

def is_unclear(text):
    t = text.lower()
    return any(word in t for word in UNCLEAR) and len(text.split()) <= 3

def find_route(text):
    t = text.lower()
    for route in ROUTES:
        if any(sym in t for sym in route["symptoms"]):
            return route
    return None

def save_lead(data):
    fieldnames = ["timestamp", "name", "phone", "date", "complaint", "comment"]
    exists = os.path.exists(LEADS_FILE)
    with open(LEADS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow(data)
    st.session_state.leads.append(data)

def get_doctor(key):
    return DOCTORS.get(key, {})

def get_promo(name):
    for p in PROMOTIONS:
        if p["name"] == name:
            return p
    return None

# ── Заголовок ──────────────────────────────────────────────────────
st.markdown(f"""
<div class='clinic-header'>
    <div class='clinic-title'>🏥 {CONTACTS['name']}</div>
    <div class='clinic-sub'>{CONTACTS['tagline']} · {CONTACTS['phone']}</div>
</div>
""", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# ЭКРАН 1 - ГЛАВНОЕ МЕНЮ
# ══════════════════════════════════════════════════════════════════
if st.session_state.screen == "main":
    st.markdown("### Чем можем помочь?")
    st.markdown("Выберите один из вариантов или опишите ваш запрос:")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("📅 Записаться\nна приём", use_container_width=True):
            st.session_state.visit_type = "record"
            go("symptom")
    with c2:
        if st.button("👨‍⚕️ Подобрать\nспециалиста", use_container_width=True):
            st.session_state.visit_type = "specialist"
            go("symptom")
    with c3:
        if st.button("🎁 Узнать\nакцию", use_container_width=True):
            st.session_state.visit_type = "promo"
            go("symptom")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("**Или опишите что вас беспокоит:**")
    free_input = st.text_input(
        label="",
        placeholder="Например: болит спина, боль в колене, онемение...",
        key="main_input",
        label_visibility="collapsed"
    )
    if free_input and free_input.strip():
        st.session_state.complaint = free_input.strip()
        st.session_state.visit_type = "free"
        if is_urgent(free_input):
            go("urgent")
        elif is_unclear(free_input):
            go("clarify")
        else:
            route = find_route(free_input)
            if route:
                st.session_state.route = route
                go("route")
            else:
                go("clarify")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(f"📍 {CONTACTS['address']} · ⏰ {CONTACTS['hours']}")

# ══════════════════════════════════════════════════════════════════
# ЭКРАН - СРОЧНЫЙ СИМПТОМ
# ══════════════════════════════════════════════════════════════════
elif st.session_state.screen == "urgent":
    st.markdown("""
<div class='urgent-card'>
⚠️ <b>Описанные симптомы требуют срочной консультации.</b><br><br>
Пожалуйста, свяжитесь с клиникой прямо сейчас или обратитесь за неотложной помощью.
</div>
""", unsafe_allow_html=True)

    st.markdown(f"### 📞 {CONTACTS['phone']}")
    st.markdown(f"⏰ Работаем {CONTACTS['hours']}")

    c1, c2 = st.columns(2)
    with c1:
        st.link_button("📞 Позвонить", f"tel:{CONTACTS['phone']}", use_container_width=True)
    with c2:
        st.link_button("💬 WhatsApp", CONTACTS["whatsapp"], use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("← Вернуться в начало"):
        st.session_state.screen = "main"
        st.rerun()

# ══════════════════════════════════════════════════════════════════
# ЭКРАН 2 - ВЫБОР СИМПТОМА
# ══════════════════════════════════════════════════════════════════
elif st.session_state.screen == "symptom":
    st.markdown("### Что вас беспокоит?")
    st.markdown("Выберите наиболее подходящее:")

    symptom_buttons = [
        ("🔴 Боль в спине / пояснице", ROUTES[0]),
        ("🦵 Боль в суставах (колено, плечо, тазобедренный)", ROUTES[1]),
        ("🔵 Боль в шее / головные боли", ROUTES[2]),
        ("⚡ Онемение / мурашки в руках или ногах", ROUTES[3]),
        ("🏃 Реабилитация после травмы", ROUTES[4]),
        ("💆 Массаж / снятие спазмов", ROUTES[5]),
    ]

    for label, route in symptom_buttons:
        if st.button(label, use_container_width=True):
            st.session_state.complaint = route["label"]
            st.session_state.route = route
            go("duration")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("**Не нашли свой вариант? Опишите жалобу:**")
    other = st.text_input(
        label="",
        placeholder="Опишите симптом своими словами...",
        key="symptom_other",
        label_visibility="collapsed"
    )
    if other and other.strip():
        st.session_state.complaint = other.strip()
        if is_urgent(other):
            go("urgent")
        else:
            route = find_route(other)
            if route:
                st.session_state.route = route
                go("duration")
            else:
                go("clarify")

    if st.button("← Назад"):
        go("main")

# ══════════════════════════════════════════════════════════════════
# ЭКРАН - УТОЧНЕНИЕ ДЛИТЕЛЬНОСТИ
# ══════════════════════════════════════════════════════════════════
elif st.session_state.screen == "duration":
    st.markdown(f"### {st.session_state.complaint}")
    st.markdown("**Как давно беспокоит?**")

    durations = [
        "Впервые / несколько дней",
        "1-4 недели",
        "1-3 месяца",
        "Более 3 месяцев",
        "Хроническая проблема"
    ]
    for d in durations:
        if st.button(d, use_container_width=True):
            st.session_state.duration = d
            go("visit_type_q")

    if st.button("← Назад"):
        go("symptom")

# ══════════════════════════════════════════════════════════════════
# ЭКРАН - ТИП ВИЗИТА
# ══════════════════════════════════════════════════════════════════
elif st.session_state.screen == "visit_type_q":
    st.markdown("**Нужен первичный приём или продолжение лечения?**")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🆕 Первичный приём", use_container_width=True):
            st.session_state.visit_type = "primary"
            go("route")
    with c2:
        if st.button("🔄 Продолжение лечения", use_container_width=True):
            st.session_state.visit_type = "continue"
            go("route")

    if st.button("← Назад"):
        go("duration")

# ══════════════════════════════════════════════════════════════════
# ЭКРАН - УТОЧНЕНИЕ (РАЗМЫТЫЙ ЗАПРОС)
# ══════════════════════════════════════════════════════════════════
elif st.session_state.screen == "clarify":
    st.markdown("### Уточните, пожалуйста")
    st.markdown("""
<div class='card'>
Где именно беспокоит? Выберите область:<br><br>
<b>поясница · тазобедренная область · низ живота · ягодица · пах · колено · шея · плечо · рука · нога</b>
</div>
""", unsafe_allow_html=True)

    clarify_input = st.text_input(
        label="Уточните область или симптом:",
        placeholder="Например: поясница, колено, шея...",
        key="clarify_input"
    )
    if clarify_input and clarify_input.strip():
        if is_urgent(clarify_input):
            go("urgent")
        else:
            route = find_route(clarify_input)
            if route:
                st.session_state.complaint = clarify_input.strip()
                st.session_state.route = route
                go("route")
            else:
                st.info("По описанию сложно точно подобрать специалиста. Оставьте телефон - администратор поможет.")
                st.session_state.complaint = clarify_input.strip()
                go("form")

    if st.button("← Назад"):
        go("main")

# ══════════════════════════════════════════════════════════════════
# ЭКРАН 3 - МАРШРУТ К СПЕЦИАЛИСТУ
# ══════════════════════════════════════════════════════════════════
elif st.session_state.screen == "route":
    route = st.session_state.route
    doctor = get_doctor(route["doctor"])

    st.markdown("### Подобрали специалиста для вас")

    st.markdown(f"""
<div class='doctor-card'>
👨‍⚕️ <b>{doctor.get('name', '')}</b><br>
{doctor.get('role', '')} · Стаж {doctor.get('experience', '')}
</div>
""", unsafe_allow_html=True)

    st.markdown("**Рекомендуемые процедуры:**")
    for svc_name in route["services"]:
        svc = next((s for s in SERVICES if s["name"] == svc_name), None)
        if svc:
            st.markdown(f"""
<div class='card'>
<b>{svc['name']}</b> - <span class='price-tag'>{svc['price']:,} руб.</span><br>
<span style='color:#555;font-size:0.9rem'>{svc['description']}</span>
</div>
""", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("➡️ Узнать об акции →", use_container_width=True, type="primary"):
        go("offer")

    if st.button("📝 Сразу записаться", use_container_width=True):
        go("form")

    if st.button("← Назад"):
        go("symptom")

# ══════════════════════════════════════════════════════════════════
# ЭКРАН 4 - ОФФЕР / АКЦИЯ
# ══════════════════════════════════════════════════════════════════
elif st.session_state.screen == "offer":
    route = st.session_state.route
    promo = get_promo(route.get("promo", ""))

    st.markdown("### 🎁 Специальное предложение для вас")

    if promo:
        original = f"~~{promo['original']:,} руб.~~" if promo.get("original") else ""
        st.markdown(f"""
<div class='card'>
<b>{promo['name']}</b><br>
<span class='promo-tag'>{promo['price']:,} руб.</span> {original}
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class='card'>
✅ Также доступны комплексные курсы лечения:<br>
• Комплекс из 2 процедур — <b>2 700 руб.</b> (-20%)<br>
• Комплекс из 3 процедур — <b>3 500 руб.</b> (-30%)<br>
• Полный курс из 12 процедур — <b>36 000 руб.</b>
</div>
""", unsafe_allow_html=True)

    st.markdown("**Оставьте заявку - администратор подберёт удобное время и расскажет подробнее.**")

    if st.button("📝 Оставить заявку", use_container_width=True, type="primary"):
        go("form")

    if st.button("← Назад"):
        go("route")

# ══════════════════════════════════════════════════════════════════
# ЭКРАН 5 - ФОРМА ЗАЯВКИ
# ══════════════════════════════════════════════════════════════════
elif st.session_state.screen == "form":
    st.markdown("### 📝 Оставить заявку")
    st.markdown("Администратор свяжется с вами и подберёт удобное время.")

    with st.form("lead_form"):
        name = st.text_input("Ваше имя *", placeholder="Иван Иванович")
        phone = st.text_input("Телефон *", placeholder="+7 (___) ___-__-__")
        date_pref = st.text_input("Желаемая дата приёма", placeholder="Например: завтра, 15 апреля, любое время")
        comment = st.text_area("Комментарий (необязательно)", placeholder="Уточните что беспокоит или задайте вопрос...")
        agree = st.checkbox("Согласен на обработку персональных данных *")

        submitted = st.form_submit_button("✅ Отправить заявку", use_container_width=True, type="primary")

        if submitted:
            if not name.strip():
                st.error("Пожалуйста, укажите имя.")
            elif not re.search(r'\d{7,}', phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")):
                st.error("Пожалуйста, укажите корректный номер телефона.")
            elif not agree:
                st.error("Необходимо согласие на обработку персональных данных.")
            else:
                lead = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "name": name.strip(),
                    "phone": phone.strip(),
                    "date": date_pref.strip(),
                    "complaint": st.session_state.complaint,
                    "comment": comment.strip(),
                }
                save_lead(lead)
                go("confirm")

    if st.button("← Назад"):
        go("offer")

# ══════════════════════════════════════════════════════════════════
# ЭКРАН 6 - ПОДТВЕРЖДЕНИЕ
# ══════════════════════════════════════════════════════════════════
elif st.session_state.screen == "confirm":
    st.markdown("""
<div class='success-card'>
✅ <b>Заявка принята!</b><br><br>
Администратор свяжется с вами в ближайшее время и подберёт удобный день и время приёма.
</div>
""", unsafe_allow_html=True)

    st.markdown(f"**{CONTACTS['name']}**")
    st.markdown(f"📍 {CONTACTS['address']}")
    st.markdown(f"⏰ {CONTACTS['hours']}")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("**Если нужна срочная связь:**")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.link_button("📞 Позвонить", f"tel:{CONTACTS['phone']}", use_container_width=True)
    with c2:
        st.link_button("💬 WhatsApp", CONTACTS["whatsapp"], use_container_width=True)
    with c3:
        st.link_button("✈️ Telegram", CONTACTS["telegram"], use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("🔄 Новая заявка", use_container_width=True):
        for key in ["screen", "complaint", "duration", "visit_type", "route"]:
            if key == "screen":
                st.session_state[key] = "main"
            else:
                st.session_state[key] = "" if key != "route" else None
        st.rerun()

# ══════════════════════════════════════════════════════════════════
# ЭКРАН ADMIN - ПРОСМОТР ЗАЯВОК
# ══════════════════════════════════════════════════════════════════
elif st.session_state.screen == "admin":
    st.markdown("### 📊 Заявки клиники МЕДИКО")

    if os.path.exists(LEADS_FILE):
        import pandas as pd
        df = pd.read_csv(LEADS_FILE)
        st.markdown(f"**Всего заявок: {len(df)}**")

        if not df.empty:
            st.markdown("**По направлениям:**")
            complaint_counts = df["complaint"].value_counts()
            st.bar_chart(complaint_counts)

            st.markdown("**Все заявки:**")
            st.dataframe(df, use_container_width=True)
    else:
        st.info("Заявок пока нет.")

    if st.button("← Вернуться"):
        go("main")

# ── Кнопка режима владельца (скрытая) ─────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
c1, c2 = st.columns([3, 1])
with c2:
    if st.button("⚙️", help="Режим владельца"):
        go("admin")
