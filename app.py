import streamlit as st
import json
import os

# ========== CONFIG ==========
st.set_page_config(page_title="KNOWLEDGE PORTAL BSNL CC MRM", layout="wide")

USERS_FILE = "users.json"
DATA_FILE = "bsnl_data.json"

# ========== DEFAULT ADMIN ==========
DEFAULT_ADMIN = {
    "admin": {"password": "admin123", "role": "Admin"}
}

# ========== INITIALIZE USER DB ==========
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_ADMIN, f, indent=4)

with open(USERS_FILE, "r", encoding="utf-8") as f:
    users = json.load(f)

# ========== LOAD DATA ==========
with open(DATA_FILE, "r", encoding="utf-8") as f:
    sections = json.load(f)

# ========== SESSION STATE ==========
for key in ["logged_in", "username", "role", "section", "subpage", "sub_subpage", "search_term"]:
    if key not in st.session_state:
        st.session_state[key] = None if key not in ["logged_in", "search_term"] else (False if key == "logged_in" else "")

# ========== AUTH FUNCTIONS ==========
def save_users():
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4)

def login(username, password):
    if username in users and users[username]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.role = users[username]["role"]
        return True
    return False

def logout():
    for key in ["logged_in", "username", "role", "section", "subpage", "sub_subpage", "search_term"]:
        st.session_state[key] = None if key not in ["logged_in", "search_term"] else (False if key == "logged_in" else "")

def reset_all():
    st.session_state.section = None
    st.session_state.subpage = None
    st.session_state.sub_subpage = None
    st.session_state.search_term = ""

def back_navigation():
    if st.session_state.sub_subpage:
        st.session_state.sub_subpage = None
    elif st.session_state.subpage:
        st.session_state.subpage = None
    elif st.session_state.section:
        st.session_state.section = None

# ========== SEARCH FILTER FUNCTIONS ==========
def get_filtered_sections(search):
    filtered = {}
    for sec, details in sections.items():
        if search in sec.lower():
            filtered[sec] = details
            continue
        for sub, sub_data in details["subtopics"].items():
            if search in sub.lower() or search in sub_data.get("content", "").lower():
                filtered[sec] = details
                break
            for sub_sub in sub_data.get("sub_subtopics", {}):
                if search in sub_sub.lower() or search in sub_data["sub_subtopics"][sub_sub].lower():
                    filtered[sec] = details
                    break
    return filtered

def get_filtered_subtopics(section, search):
    subs = sections[section]["subtopics"]
    if search == "":
        return subs
    filtered = {}
    for sub, sub_data in subs.items():
        if search in sub.lower() or search in sub_data.get("content", "").lower():
            filtered[sub] = sub_data
            continue
        filtered_sub_subs = {k:v for k,v in sub_data.get("sub_subtopics", {}).items()
                             if search in k.lower() or search in v.lower()}
        if filtered_sub_subs:
            filtered[sub] = {"content": sub_data.get("content", ""), "sub_subtopics": filtered_sub_subs}
    return filtered

def get_filtered_sub_subtopics(section, subpage, search):
    sub_subs = sections[section]["subtopics"][subpage].get("sub_subtopics", {})
    if search == "":
        return sub_subs
    return {k:v for k,v in sub_subs.items() if search in k.lower() or search in v.lower()}

# ========== LOGIN SCREEN ==========
if not st.session_state.logged_in:
    st.markdown("""
        <h1 style='text-align:center; color:#0066cc;'>📘 BSNL Knowledge Portal Login</h1>
        <hr>
    """, unsafe_allow_html=True)
    username = st.text_input("👤 Username")
    password = st.text_input("🔒 Password", type="password")
    if st.button("Login"):
        if login(username, password):
            st.success(f"Welcome, {username} ({st.session_state.role})!")
            st.rerun()
        else:
            st.error("Invalid username or password.")
    st.stop()

# ========== HEADER ==========
st.markdown(f"""
    <h1 style='text-align:center; color:#0066cc;'>
        📞 BSNL Customer Care Marthandam
    </h1>
    <p style='text-align:center; color:gray;'>Logged in as: {st.session_state.username} ({st.session_state.role})</p>
    <hr style='border:1px solid #0066cc;'>
""", unsafe_allow_html=True)

# ========== ADMIN PANEL ==========
if st.session_state.role == "Admin":
    with st.expander("⚙️ User Management"):
        st.subheader("Add / Modify / Delete Users")
        col1, col2, col3 = st.columns(3)
        with col1:
            new_user = st.text_input("Username")
        with col2:
            new_pass = st.text_input("Password")
        with col3:
            role = st.selectbox("Role", ["User", "Report Manager", "Admin"])
        if st.button("Add / Update User"):
            users[new_user] = {"password": new_pass, "role": role}
            save_users()
            st.success(f"User '{new_user}' added/updated successfully!")

        del_user = st.selectbox("Select user to delete", list(users.keys()))
        if st.button("Delete User"):
            if del_user != "admin":
                del users[del_user]
                save_users()
                st.warning(f"User '{del_user}' deleted!")
            else:
                st.error("Cannot delete default admin user.")

st.markdown("---")

# ========== NAVIGATION ==========
nav1, nav2, nav3, nav4 = st.columns([1,3,1,1])

with nav1:
    if st.button("🏠 Home"):
        reset_all()

with nav2:
    search_input = st.text_input("🔍 Search sections, subtopics or options", st.session_state.search_term)
    if search_input != st.session_state.search_term:
        st.session_state.search_term = search_input.lower()
        reset_all()

with nav3:
    if any([st.session_state.section, st.session_state.subpage, st.session_state.sub_subpage]):
        if st.button("⬅️ Back"):
            back_navigation()

with nav4:
    if st.button("🚪 Logout"):
        logout()
        st.rerun()

st.markdown("---")

search = st.session_state.search_term.strip().lower()

# ========== MAIN CONTENT AREA ==========
if st.session_state.sub_subpage:
    sec = st.session_state.section
    sub = st.session_state.subpage
    sub_sub = st.session_state.sub_subpage
    icon = sections[sec]["icon"]

    st.markdown(f"<h3 style='color:{sections[sec]['color']}'>{icon} {sec} → {sub} → {sub_sub}</h3>", unsafe_allow_html=True)
    st.markdown("---")

    # Fetch the existing content if available
    sub_sub_content = sections[sec]["subtopics"][sub]["sub_subtopics"].get(sub_sub, "")

    # Editable only by Admins
    if st.session_state.role == "Admin":
        st.info("✏️ Admin can write or update content below:")
        new_content = st.text_area("Enter content here:", value=sub_sub_content, height=250)
        if st.button("💾 Save Content"):
            sections[sec]["subtopics"][sub]["sub_subtopics"][sub_sub] = new_content
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(sections, f, indent=4)
            st.success("Content saved successfully!")
    else:
        if sub_sub_content.strip() == "":
            st.warning("No content added yet. Please contact Admin.")
        else:
            st.markdown(sub_sub_content)

elif st.session_state.subpage:
    icon = sections[st.session_state.section]["icon"]
    sub_data = sections[st.session_state.section]["subtopics"][st.session_state.subpage]
    st.markdown(f"<h3 style='color:{sections[st.session_state.section]['color']}'>{icon} {st.session_state.section} → {st.session_state.subpage}</h3>", unsafe_allow_html=True)
    st.markdown("---")
    sub_subtopics = get_filtered_sub_subtopics(st.session_state.section, st.session_state.subpage, search)
    if sub_subtopics:
        cols = st.columns(2)
        for i, sub_sub in enumerate(sub_subtopics.keys()):
            col = cols[i % 2]
            if col.button(sub_sub):
                st.session_state.sub_subpage = sub_sub
    else:
        st.write(sub_data.get("content", ""))

else:
    if st.session_state.section:
        filtered_subs = get_filtered_subtopics(st.session_state.section, search)
        if not filtered_subs:
            st.warning("No subtopics found.")
        else:
            st.markdown(f"<h3 style='color:{sections[st.session_state.section]['color']}'>{sections[st.session_state.section]['icon']} {st.session_state.section} Subtopics</h3>", unsafe_allow_html=True)
            cols = st.columns(2)
            for i, sub in enumerate(filtered_subs.keys()):
                col = cols[i % 2]
                if col.button(sub):
                    st.session_state.subpage = sub
    else:
        filtered_secs = get_filtered_sections(search)
        if not filtered_secs:
            st.warning("No sections found.")
        else:
            st.markdown("### Select a Section")
            cols = st.columns(3)
            for i, (sec, details) in enumerate(filtered_secs.items()):
                col = cols[i % 3]
                if col.button(f"{details['icon']} {sec}"):
                    st.session_state.section = sec

st.markdown("---")
st.info("Developed for BSNL Customer Care Marthandam 📍 | Jijo Shaji")
