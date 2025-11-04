# app.py - BSNL KNOWLEDGE PORTAL MRM (Final — dynamic Settings + drag-and-drop ordering + styled accordions + header control)
import streamlit as st
import json
import os
import re
from streamlit_quill import st_quill

# Try to import streamlit-sortables for drag & drop ordering in settings.
# If not available, the Settings UI will fall back to numeric ordering inputs.
try:
    from streamlit_sortables import sort_items
    SORTABLES_AVAILABLE = True
except Exception:
    SORTABLES_AVAILABLE = False

# ------------------ Config / Files ------------------
st.set_page_config(page_title="BSNL KNOWLEDGE PORTAL MRM", layout="wide", page_icon="📘")

DATA_FILE = "bsnl_data.json"
USERS_FILE = "users.json"
NOTICE_FILE = "announcements.json"
SETTINGS_FILE = "settings.json"
UPLOAD_DIR = "uploads"

# ensure folders & files exist
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, indent=4)

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump({"admin": {"password": "admin123", "role": "Admin"}}, f, indent=4)

if not os.path.exists(NOTICE_FILE):
    with open(NOTICE_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, indent=4)

DEFAULT_SETTINGS = {
    "background_color": "#0f172a",
    "font_color": "#ffffff",
    "font_family": "Sans",
    "font_size": 16,
    "default_icon": "📘",
    "announcement_bg": "#1f6feb",
    "theme_mode": "dark",
    # New dynamic settings (defaults)
    "header_visible": True,
    "header_title": "📘 BSNL KNOWLEDGE PORTAL MRM",
    "header_logo": "",  # path to uploaded logo file under uploads/
    # finer header controls
    "show_title": True,
    "show_logo": True,
    "hide_header": False,
    "feature_toggles": {
        "announcements": True,
        "editor_tools": True,
        "user_management": True,
        "settings_menu": True
    },
    "visible_sections": {},     # will be filled lazily with keys from sections
    "user_privileges": {},      # { username: { "Topic" or "Topic / Subtopic": ["view","edit"], ... } }
    "topic_order": [],         # list of top-level topic names (order)
    "subtopic_order": {}       # { "Topic": ["sub1","sub2"] }
}

if not os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_SETTINGS, f, indent=4)

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# ------------------ Utility ------------------
def safe_load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        return default

def safe_save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

sections = safe_load_json(DATA_FILE, {})
users = safe_load_json(USERS_FILE, {"admin": {"password": "admin123", "role": "Admin"}})
settings = safe_load_json(SETTINGS_FILE, DEFAULT_SETTINGS.copy())
notices = safe_load_json(NOTICE_FILE, [])

# Ensure new keys exist in settings (upgrade-safe)
def ensure_settings_defaults():
    changed = False
    for k, v in DEFAULT_SETTINGS.items():
        if k not in settings:
            settings[k] = v
            changed = True
    # visible_sections defaults: mark every top-level section visible if not present
    if "visible_sections" not in settings or not isinstance(settings["visible_sections"], dict):
        settings["visible_sections"] = {}
        changed = True
    for top in sections.keys():
        if top not in settings["visible_sections"]:
            settings["visible_sections"][top] = True
            changed = True
    # topic_order default
    if not settings.get("topic_order"):
        settings["topic_order"] = list(sections.keys())
        changed = True
    # subtopic_order defaults
    if "subtopic_order" not in settings or not isinstance(settings["subtopic_order"], dict):
        settings["subtopic_order"] = {}
        changed = True
    for top, val in sections.items():
        subs = list(val.get("subtopics", {}).keys())
        if top not in settings["subtopic_order"]:
            settings["subtopic_order"][top] = subs
            changed = True
        else:
            # ensure all subs present
            for s in subs:
                if s not in settings["subtopic_order"].get(top, []):
                    settings["subtopic_order"][top].append(s)
                    changed = True
    if changed:
        safe_save_json(SETTINGS_FILE, settings)

ensure_settings_defaults()

# ------------------ Session ------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "path" not in st.session_state:
    st.session_state.path = []
if "view" not in st.session_state:
    st.session_state.view = "portal"
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "live_settings" not in st.session_state:
    st.session_state.live_settings = settings.copy()

# ------------------ Helpers ------------------
def save_data(): safe_save_json(DATA_FILE, sections)
def save_users(): safe_save_json(USERS_FILE, users)
def save_notices(n): safe_save_json(NOTICE_FILE, n)
def save_settings(s):
    safe_save_json(SETTINGS_FILE, s)
    # apply live settings
    st.session_state.live_settings = s.copy()
    # update global settings var too
    global settings
    settings = s

def apply_global_styles(st_settings):
    font_map = {
        "Sans": "Segoe UI, Tahoma, Geneva, Verdana, sans-serif",
        "Serif": "Georgia, 'Times New Roman', Times, serif",
        "Monospace": "Menlo, Monaco, Consolas, 'Courier New', monospace"
    }
    font_family_css = font_map.get(st_settings.get("font_family", "Sans"), font_map["Sans"])
    bg = st_settings.get("background_color", DEFAULT_SETTINGS["background_color"])
    color = st_settings.get("font_color", DEFAULT_SETTINGS["font_color"])
    font_size = st_settings.get("font_size", DEFAULT_SETTINGS["font_size"])
    ann_bg = st_settings.get("announcement_bg", DEFAULT_SETTINGS["announcement_bg"])

    # Additional CSS: style expander to look like card/accordion and small animation
    css = f"""
    <style>
    .stApp {{
        background-color: {bg};
        color: {color};
        font-family: {font_family_css};
        font-size: {font_size}px;
    }}
    h1,h2,h3,h4,h5,h6{{color:{color};}}
    .announcement-banner{{background-color:{ann_bg};padding:8px 12px;border-radius:6px;margin-bottom:12px;}}
    .announcement-text{{color:white;font-weight:700;text-align:center;margin:0;font-size:{font_size}px;}}
    a{{color:#4ea8ff;}}

    /* Accordion/Expander card look */
    .streamlit-expanderHeader {{
        background-color: rgba(255,255,255,0.02) !important;
        border-radius: 10px;
        padding: 10px 12px !important;
        margin-bottom: 6px;
        transition: transform .12s ease, box-shadow .12s ease;
        box-shadow: 0 1px 0 rgba(0,0,0,0.2);
    }}
    .streamlit-expanderHeader:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(0,0,0,0.25);
    }}
    .streamlit-expanderContent {{
        background-color: rgba(255,255,255,0.01) !important;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
    }}
    .portal-header {{
        text-align:center;
        font-size:28px;
        font-weight:bold;
        margin-top:10px;
        margin-bottom:20px;
        color:{color};
    }}
    .settings-section {{
        border: 1px solid rgba(255,255,255,0.03);
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 14px;
        background: rgba(255,255,255,0.01);
    }}
    .user-priv-box {{
        border:1px solid rgba(255,255,255,0.04);
        padding:8px;
        border-radius:8px;
        margin-bottom:8px;
        background: rgba(0,0,0,0.02);
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def breadcrumb_label(path): return " / ".join(path) if path else "🏠 Home"

def search_in_data(data, query, path=None):
    if path is None: path = []
    results = []
    for key, value in data.items():
        if query.lower() in key.lower(): results.append(path + [key])
        if isinstance(value, dict):
            content = value.get("content", "")
            if isinstance(content, str) and query.lower() in content.lower():
                results.append(path + [key])
            if "subtopics" in value:
                results.extend(search_in_data(value["subtopics"], query, path + [key]))
    return results

def get_all_topic_paths(data, prefix=None):
    """Return list of strings 'Top' or 'Top / Sub' for all topics recursively."""
    if prefix is None:
        prefix = []
    out = []
    for k, v in data.items():
        cur = prefix + [k]
        out.append(" / ".join(cur))
        if isinstance(v, dict) and v.get("subtopics"):
            out.extend(get_all_topic_paths(v["subtopics"], cur))
    return out

def has_privilege(username, path, action):
    """
    path: either list or string like 'Top / Sub'
    action: 'view' or 'edit'
    Checks exact path, then parent paths e.g. if user has permission on 'Top' it applies to 'Top / Sub' as well.
    """
    if not username:
        return False
    if users.get(username, {}).get("role") == "Admin":
        return True
    if isinstance(path, list):
        path_str = " / ".join(path)
    else:
        path_str = str(path)
    priv = settings.get("user_privileges", {})
    userp = priv.get(username, {})
    # exact
    perms = userp.get(path_str, [])
    if action in perms:
        return True
    # check parents
    parts = path_str.split(" / ")
    for i in range(len(parts)-1, 0, -1):
        parent = " / ".join(parts[:i])
        pperms = userp.get(parent, [])
        if action in pperms:
            return True
    return False

def render_header():
    # central header shown on each page
    # respects hide_header, show_logo, show_title
    if settings.get("hide_header", False):
        return
    header_visible = settings.get("header_visible", True)
    if not header_visible:
        return
    logo = settings.get("header_logo", "") or ""
    title = settings.get("header_title", "📘 BSNL KNOWLEDGE PORTAL MRM")
    show_logo = settings.get("show_logo", True)
    show_title = settings.get("show_title", True)
    cols = st.columns([1, 6, 1])
    with cols[1]:
        if show_logo and logo and os.path.exists(logo):
            try:
                st.image(logo, width=150)
            except Exception:
                if show_title:
                    st.markdown(f"<div class='portal-header'>{title}</div>", unsafe_allow_html=True)
                else:
                    st.markdown("", unsafe_allow_html=True)
        else:
            if show_title:
                st.markdown(f"<div class='portal-header'>{title}</div>", unsafe_allow_html=True)
            else:
                st.markdown("", unsafe_allow_html=True)

# ------------------ Auth ------------------
def login(username, password):
    if username in users and users[username]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.role = users[username]["role"]
        st.session_state.view = "portal"
        st.rerun()
    else:
        st.error("Invalid username or password.")

def logout():
    st.session_state.clear()
    st.session_state.logged_in = False
    st.session_state.view = "login"
    st.rerun()

def login_page():
    render_header()
    st.title("🔐 Login to BSNL KNOWLEDGE PORTAL")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        login(u, p)

# ------------------ Announcements ------------------
def render_announcements_on_home():
    try:
        local_notices = json.load(open(NOTICE_FILE, "r", encoding="utf-8"))
    except:
        local_notices = []
    if settings.get("feature_toggles", {}).get("announcements", True):
        st.markdown("<div class='announcement-banner'><p class='announcement-text'>📢 Announcements</p></div>", unsafe_allow_html=True)
        if local_notices:
            for i, n in enumerate(local_notices, 1):
                st.markdown(f"<p class='announcement-text'>{i}. {n}</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p style='color:lightgray;text-align:center;'>No active announcements.</p>", unsafe_allow_html=True)
    if st.session_state.role in ["Admin", "Editor"]:
        st.divider()
        st.markdown("### ✏️ Manage Announcements")
        if not settings.get("feature_toggles", {}).get("announcements", True):
            st.info("Announcements module is currently disabled via Settings.")
        new_notice = st_quill(value="")
        if st.button("📢 Post Announcement"):
            if new_notice.strip():
                local_notices.append(new_notice)
                save_notices(local_notices)
                st.success("Announcement posted.")
                st.rerun()
        if local_notices:
            sel = st.selectbox("Select announcement to delete", [""] + [f"{i+1}. {n[:60]}..." for i, n in enumerate(local_notices)])
            if sel and st.button("🗑️ Delete Selected"):
                local_notices.pop(int(sel.split(".")[0]) - 1)
                save_notices(local_notices)
                st.warning("Deleted.")
                st.rerun()

# ------------------ Settings (Enhanced with styled accordions + header control) ------------------
def settings_page():
    render_header()
    st.title("⚙️ Settings")

    if st.session_state.role != "Admin":
        st.warning("Only Admins can modify settings (you can still view).")

    # Load live copy from session
    live = st.session_state.live_settings

    # We will put each section inside a styled expander to look like accordions.
    # Appearance Section
    with st.expander("🎨 Appearance", expanded=False):
        st.markdown("<div class='settings-section'>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            bg = st.color_picker("Background color", value=live.get("background_color", DEFAULT_SETTINGS["background_color"]))
            ann_bg = st.color_picker("Announcement banner color", value=live.get("announcement_bg", DEFAULT_SETTINGS["announcement_bg"]))
            font_color = st.color_picker("Font color", value=live.get("font_color", DEFAULT_SETTINGS["font_color"]))
        with c2:
            font_family = st.selectbox("Font family", ["Sans", "Serif", "Monospace"], index=["Sans", "Serif", "Monospace"].index(live.get("font_family", "Sans")))
            font_size = st.slider("Font size (px)", 12, 24, int(live.get("font_size", 16)))
            default_icon = st.text_input("Default icon", value=live.get("default_icon", "📘"))
        st.markdown("</div>", unsafe_allow_html=True)

    # Header Section
    with st.expander("🧱 Header Options", expanded=False):
        st.markdown("<div class='settings-section'>", unsafe_allow_html=True)
        colh1, colh2 = st.columns([3,1])
        with colh1:
            # new toggles: show_title, show_logo, hide_header
            header_visible = st.checkbox("Enable header area (title/logo)", value=live.get("header_visible", True))
            show_title = st.checkbox("Show header title text", value=live.get("show_title", True))
            show_logo = st.checkbox("Show header logo", value=live.get("show_logo", True))
            hide_header = st.checkbox("Hide entire header (overrides above)", value=live.get("hide_header", False))
            header_title = st.text_input("Header title text", value=live.get("header_title", DEFAULT_SETTINGS.get("header_title", "BSNL")))
            logo_upload = st.file_uploader("Upload header logo (PNG/JPG) — will not be previewed here", type=["png", "jpg", "jpeg"])
            # show filename if exists (no preview in admin)
            current_logo = live.get("header_logo", "")
            if current_logo:
                st.markdown(f"Current logo file: `{os.path.basename(current_logo)}` (used in header if visible)")
        with colh2:
            if logo_upload:
                os.makedirs(UPLOAD_DIR, exist_ok=True)
                logo_path = os.path.join(UPLOAD_DIR, f"header_logo_{logo_upload.name}")
                with open(logo_path, "wb") as f:
                    f.write(logo_upload.read())
                st.success("Header logo uploaded and saved.")
                # update live and persistent settings immediately
                live["header_logo"] = logo_path
                save_settings(live)
                # re-run so header reflects new logo immediately
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Feature Toggles Section
    with st.expander("⚙️ Feature Toggles", expanded=False):
        st.markdown("<div class='settings-section'>", unsafe_allow_html=True)
        ft = live.get("feature_toggles", DEFAULT_SETTINGS.get("feature_toggles", {}))
        ft_ann = st.checkbox("Enable Announcements", value=ft.get("announcements", True))
        ft_editor = st.checkbox("Enable Editor Tools", value=ft.get("editor_tools", True))
        ft_users = st.checkbox("Enable User Management (sidebar)", value=ft.get("user_management", True))
        ft_settings_menu = st.checkbox("Enable Settings Menu (visible to Admins)", value=ft.get("settings_menu", True))
        st.markdown("</div>", unsafe_allow_html=True)

    # Menu Visibility Section
    with st.expander("📋 Menu Visibility (Top-level sections)", expanded=False):
        st.markdown("<div class='settings-section'>", unsafe_allow_html=True)
        vs = live.get("visible_sections", {})
        for t in list(sections.keys()):
            if t not in vs:
                vs[t] = True
        topic_order = live.get("topic_order", list(sections.keys()))
        ordered_topics = [t for t in topic_order if t in sections] + [t for t in sections if t not in topic_order]
        new_vs = {}
        cols = st.columns(2)
        for i, t in enumerate(ordered_topics):
            key = f"vis_{t}"
            val = st.checkbox(f"{t}", value=vs.get(t, True), key=key)
            new_vs[t] = val
        st.markdown("</div>", unsafe_allow_html=True)

    # Ordering Section
    with st.expander("🔀 Topic & Subtopic Ordering", expanded=False):
        st.markdown("<div class='settings-section'>", unsafe_allow_html=True)
        st.caption("Drag to reorder top-level sections (requires `streamlit-sortables`), fallback to numbered order inputs if not available.")
        topics_for_order = list(ordered_topics)
        if SORTABLES_AVAILABLE:
            new_topic_order = sort_items(items=topics_for_order, key="topic_order")
        else:
            st.info("Drag-and-drop not available — pip install streamlit-sortables for DnD. Use numeric order inputs below.")
            new_topic_order = []
            for idx, t in enumerate(topics_for_order):
                num = st.number_input(f"Position for '{t}'", min_value=1, max_value=len(topics_for_order), value=idx+1, key=f"num_{t}")
                new_topic_order.append((t, num))
            new_topic_order = [t for t, n in sorted(new_topic_order, key=lambda x: x[1])]

        # Subtopic ordering per topic
        new_subtopic_order = live.get("subtopic_order", {}).copy()
        for t in list(sections.keys()):
            st.markdown(f"**{t} subtopics**")
            subs = list(sections.get(t, {}).get("subtopics", {}).keys())
            if not subs:
                st.markdown("_No subtopics_")
                continue
            cur_order = live.get("subtopic_order", {}).get(t, subs)
            cur_order = [s for s in cur_order if s in subs] + [s for s in subs if s not in cur_order]
            if SORTABLES_AVAILABLE:
                res = sort_items(items=cur_order, key=f"sub_order_{t}")
                new_subtopic_order[t] = res
            else:
                arr = []
                for idx, s in enumerate(cur_order):
                    num = st.number_input(f"Position for '{s}' in {t}", min_value=1, max_value=len(cur_order), value=idx+1, key=f"num_{t}_{s}")
                    arr.append((s, num))
                new_subtopic_order[t] = [s for s, n in sorted(arr, key=lambda x: x[1])]
        st.markdown("</div>", unsafe_allow_html=True)

    # User Privileges Section - show a top-level expander, but DO NOT nest expanders inside it.
    with st.expander("👥 User Privileges", expanded=False):
        st.markdown("<div class='settings-section'>", unsafe_allow_html=True)
        st.caption("Select a user from the list below and edit their privileges. Admins always have full privileges.")
        all_users = list(users.keys())
        # For each user, open a container (NOT an inner expander) to avoid nesting expanders.
        for u in all_users:
            # container looks like a card/mini-accordion entry
            st.markdown(f"<div class='user-priv-box'><strong>User: {u}</strong> &nbsp; <span style='opacity:0.7'>({users[u]['role']})</span></div>", unsafe_allow_html=True)
            # Now show multi-selects for view/edit across all topic+subtopic paths
            user_privs = settings.get("user_privileges", {}).get(u, {})
            all_topic_paths = get_all_topic_paths(sections)
            cur_view = [p for p, perms in user_privs.items() if "view" in perms]
            cur_edit = [p for p, perms in user_privs.items() if "edit" in perms]
            colv, cole = st.columns([1,1])
            with colv:
                view_sel = st.multiselect(f"Grant VIEW access for {u}:", options=all_topic_paths, default=cur_view, key=f"view_{u}")
            with cole:
                edit_sel = st.multiselect(f"Grant EDIT access for {u}:", options=all_topic_paths, default=cur_edit, key=f"edit_{u}")
            if st.button(f"Save privileges for {u}", key=f"save_priv_{u}"):
                up = settings.get("user_privileges", {})
                mapping = {}
                for p in view_sel:
                    mapping.setdefault(p, [])
                    if "view" not in mapping[p]:
                        mapping[p].append("view")
                for p in edit_sel:
                    mapping.setdefault(p, [])
                    if "edit" not in mapping[p]:
                        mapping[p].append("edit")
                up[u] = mapping
                settings["user_privileges"] = up
                save_settings(settings)
                st.success(f"Privileges saved for {u}")
        st.markdown("</div>", unsafe_allow_html=True)

    # Save / Reset Buttons as a final collapsible control
    with st.expander("💾 Save / Reset Settings", expanded=False):
        st.markdown("<div class='settings-section'>", unsafe_allow_html=True)
        if st.button("💾 Save Settings"):
            # update live dict and persist
            live.update({
                "background_color": bg,
                "announcement_bg": ann_bg,
                "font_color": font_color,
                "font_family": font_family,
                "font_size": font_size,
                "default_icon": default_icon,
                "header_visible": header_visible,
                "header_title": header_title,
                "show_title": show_title,
                "show_logo": show_logo,
                "hide_header": hide_header
            })
            live["feature_toggles"] = {
                "announcements": ft_ann,
                "editor_tools": ft_editor,
                "user_management": ft_users,
                "settings_menu": ft_settings_menu
            }
            live["visible_sections"] = new_vs
            live["topic_order"] = new_topic_order
            live["subtopic_order"] = new_subtopic_order
            save_settings(live)
            st.success("Settings saved and applied.")
            st.rerun()
        if st.button("🔄 Reset to Defaults"):
            safe_save_json(SETTINGS_FILE, DEFAULT_SETTINGS.copy())
            st.success("Settings reset to defaults. Reloading...")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ------------------ User Management ------------------
def manage_users_page():
    render_header()
    st.title("👥 Manage Users")
    tabs = st.tabs(["📋 View All","➕ Add","✏️ Edit","🗑️ Delete"])
    with tabs[0]:
        st.table([{"Username":u,"Role":users[u]["role"]} for u in users])
    with tabs[1]:
        u = st.text_input("Username"); p = st.text_input("Password", type="password")
        r = st.selectbox("Role", ["Admin","Editor","User"])
        if st.button("Add"): 
            if u in users: st.error("Exists.")
            else:
                users[u] = {"password": p,"role": r}
                save_users(); st.success("Added."); st.rerun()
    with tabs[2]:
        e = st.selectbox("Edit user", [""]+list(users.keys()))
        if e:
            r = st.selectbox("Role", ["Admin","Editor","User"], index=["Admin","Editor","User"].index(users[e]["role"]))
            p = st.text_input("New password", type="password")
            if st.button("Save"): 
                if p: users[e]["password"]=p
                users[e]["role"]=r; save_users(); st.success("Updated."); st.rerun()
    with tabs[3]:
        d = st.selectbox("Delete user", [""]+list(users.keys()))
        if d and d!="admin" and st.button("Delete"):
            users.pop(d,None); save_users(); st.warning("Deleted."); st.rerun()
        elif d=="admin": st.info("Cannot delete admin.")

# ------------------ Main Portal Rendering ------------------
def _rewrite_links_to_new_tab(html_text):
    # Add target="_blank" to anchor tags to open in new tab
    # Works if content contains HTML <a href="..."> links
    return re.sub(r'<a\s+href=', r'<a target="_blank" href=', html_text, flags=re.IGNORECASE)

def render_section(level, node):
    render_header()
    if not level:
        # show announcements only if feature enabled
        if settings.get("feature_toggles", {}).get("announcements", True):
            render_announcements_on_home()
    st.markdown(f"## {breadcrumb_label(level)}")
    if level and st.button("⬅️ Back"):
        st.session_state.path = st.session_state.path[:-1]
        st.rerun()

    q = st.text_input("🔍 Search", key="search_box")
    if q:
        st.session_state.search_results = search_in_data(sections, q)
        for p in st.session_state.search_results:
            if st.button(" → ".join(p), key=f"s_{'_'.join(p)}"):
                st.session_state.path = p
                st.rerun()

    # Show subtopics but filter by visible_sections and use ordering
    subtopics = node.get("subtopics", {}) if isinstance(node, dict) else {}

    # When listing subtopics in a top-level page, use settings.subtopic_order to order
    ordered_subs = list(subtopics.keys())
    if level:
        parent = level[-1]
        sorder = settings.get("subtopic_order", {}).get(parent, [])
        ordered_subs = [s for s in sorder if s in subtopics] + [s for s in subtopics if s not in sorder]

    cols = st.columns(4)
    for i, topic in enumerate(ordered_subs):
        data = subtopics.get(topic, {})
        visible_sections = settings.get("visible_sections", {})
        if not level:
            if visible_sections.get(topic, True) is False:
                continue
        icon = data.get("icon", st.session_state.live_settings.get("default_icon","📘"))
        col = cols[i % 4]
        if col.button(f"{icon} {topic}", key=f"btn_{'_'.join(level+[topic])}"):
            st.session_state.path.append(topic)
            st.rerun()

    # content and files
    if isinstance(node, dict):
        content = node.get("content","")
        if content:
            st.markdown("---")
            try:
                safe_html = _rewrite_links_to_new_tab(content)
                st.markdown(safe_html, unsafe_allow_html=True)
            except Exception:
                st.markdown(content, unsafe_allow_html=True)

        # Show uploaded files for everyone (only where uploaded)
        # ====== IMPORTANT CHANGE: show files ONLY when `level` is truthy (i.e. not home)
        if level:
            path_id = "_".join(level)
            page_dir = os.path.join(UPLOAD_DIR, path_id)
            if os.path.exists(page_dir):
                files = sorted(os.listdir(page_dir))
                if files:
                    st.markdown("---")
                    c = st.columns(5)
                    for i, f in enumerate(files):
                        fp = os.path.join(page_dir, f)
                        ext = f.split(".")[-1].lower()
                        if ext in ["png", "jpg", "jpeg"]:
                            try:
                                c[i%5].image(fp, caption=f, width=120)
                            except Exception:
                                c[i%5].markdown(f"🖼️ [{f}]({fp})")
                        else:
                            c[i%5].markdown(f"📄 [{f}]({fp})")

    # Editor controls governed by feature toggle and user privileges
    cur_path_str = " / ".join(level) if level else ""
    if settings.get("feature_toggles", {}).get("editor_tools", True) and (st.session_state.role == "Admin" or has_privilege(st.session_state.username, cur_path_str, "edit")):
        st.markdown("---")
        st.subheader("⚙️ Admin/Editor Controls")
        edited = st_quill(value=node.get("content",""), key=f"edit_{len(level)}")
        if settings.get("feature_toggles", {}).get("editor_tools", True):
            if st.button("💾 Save Content"):
                if isinstance(node, dict):
                    node["content"] = edited
                save_data()
                st.success("Saved.")
                st.rerun()
        up = st.file_uploader("📤 Upload File", type=["png","jpg","jpeg","pdf","xlsx","xls","docx"])
        if up:
            # Ensure page_dir variable exists (compute only if level present, else use 'home' but do not display home files)
            if level:
                page_dir = os.path.join(UPLOAD_DIR, "_".join(level))
            else:
                page_dir = os.path.join(UPLOAD_DIR, "home")
            os.makedirs(page_dir, exist_ok=True)
            with open(os.path.join(page_dir, up.name),"wb") as f:
                f.write(up.read())
            st.success(f"Uploaded {up.name}")
            st.rerun()
        # Delete list for current page
        if level:
            page_dir = os.path.join(UPLOAD_DIR, "_".join(level))
            files = sorted(os.listdir(page_dir)) if os.path.exists(page_dir) else []
        else:
            files = []
        if files:
            sel = st.selectbox("Delete file", [""] + files)
            if sel and st.button("🗑️ Delete"):
                os.remove(os.path.join(page_dir, sel))
                st.warning(f"Deleted {sel}")
                st.rerun()

        # Subtopic management (Admins or users with edit privilege)
        st.markdown("---")
        st.subheader("📁 Subtopic Management")
        new = st.text_input("Add new subtopic"); icon = st.text_input("Icon", value="📘")
        if st.button("➕ Add") and new.strip():
            node.setdefault("subtopics", {})[new] = {"icon": icon, "content": "", "subtopics": {}}
            # update ordering defaults
            settings.setdefault("subtopic_order", {})
            parent = level[-1] if level else "home"
            settings["subtopic_order"].setdefault(parent, [])
            settings["subtopic_order"][parent].append(new)
            save_data()
            save_settings(settings)
            st.success("Added.")
            st.rerun()
        subs = list(node.get("subtopics", {}).keys())
        if subs:
            s = st.selectbox("Rename subtopic", [""] + subs)
            if s:
                n = st.text_input("New name", value=s)
                if st.button("Save rename"):
                    node["subtopics"][n] = node["subtopics"].pop(s)
                    # update subtopic_order
                    parent = level[-1] if level else "home"
                    arr = settings.get("subtopic_order", {}).get(parent, [])
                    settings["subtopic_order"][parent] = [n if x == s else x for x in arr]
                    save_data(); save_settings(settings)
                    st.success("Renamed.")
                    st.rerun()
            d = st.selectbox("Delete subtopic", [""] + subs, key=f"d_{len(level)}")
            if d and st.button("🗑️ Delete subtopic"):
                node["subtopics"].pop(d, None)
                # remove from ordering too
                parent = level[-1] if level else "home"
                if parent in settings.get("subtopic_order", {}):
                    settings["subtopic_order"][parent] = [x for x in settings["subtopic_order"][parent] if x != d]
                    save_settings(settings)
                save_data(); st.warning("Deleted."); st.rerun()

# ------------------ Guard ------------------
if not st.session_state.get("logged_in", False):
    login_page()
    st.stop()

# ------------------ Sidebar ------------------
apply_global_styles(st.session_state.live_settings)
with st.sidebar:
    # show header logo or small title in sidebar top (keeps minimal preview)
    logo = settings.get("header_logo", "")
    # do NOT preview large uploaded images in admin sidebar; show only small logo if exists
    if logo and os.path.exists(logo) and settings.get("show_logo", True) and not settings.get("hide_header", False):
        try:
            st.image(logo, width=110)
        except Exception:
            st.image("https://upload.wikimedia.org/wikipedia/en/5/5a/Bharat_Sanchar_Nigam_Limited_Logo.png", width=110)
    else:
        st.image("https://upload.wikimedia.org/wikipedia/en/5/5a/Bharat_Sanchar_Nigam_Limited_Logo.png", width=110)
    st.markdown(f"### 👤 {st.session_state.username}")
    st.markdown(f"**Role:** {st.session_state.role}")
    st.divider()
    st.button("🏠 Home", on_click=lambda: st.session_state.update({"path": [], "view": "portal"}), use_container_width=True)
    # feature toggle: user management visibility
    if settings.get("feature_toggles", {}).get("user_management", True) and st.session_state.role == "Admin":
        st.button("👥 Manage Users", on_click=lambda: st.session_state.update({"view": "users"}), use_container_width=True)
    # settings menu visible only if toggle on and current user is admin
    if settings.get("feature_toggles", {}).get("settings_menu", True) and st.session_state.role == "Admin":
        st.button("⚙️ Settings", on_click=lambda: st.session_state.update({"view": "settings"}), use_container_width=True)
    st.button("🚪 Logout", on_click=logout, use_container_width=True)
    st.divider()

# ------------------ Router ------------------
if st.session_state.view == "settings" and st.session_state.role == "Admin":
    settings_page()
elif st.session_state.view == "users" and st.session_state.role == "Admin":
    manage_users_page()
else:
    # Render home/top-level using topic_order and visible_sections
    # Build ordered top-level list using settings.topic_order
    top_order = settings.get("topic_order", list(sections.keys()))
    ordered_top = [t for t in top_order if t in sections] + [t for t in sections if t not in top_order]
    # Filter by visible_sections
    visible = settings.get("visible_sections", {})
    # build pseudo root node to pass into render_section if at home
    if not st.session_state.path:
        # build a temporary node with only visible sections in desired order
        node = {"subtopics": {}}
        for t in ordered_top:
            if visible.get(t, True):
                node["subtopics"][t] = sections.get(t, {})
        render_section([], node)
    else:
        cur = sections
        valid = True
        for step in st.session_state.path[:-1]:
            cur = cur.get(step, {}).get("subtopics", {})
            if cur is None:
                valid = False
                break
        last = st.session_state.path[-1] if st.session_state.path else None
        if not valid or last not in cur:
            st.session_state.path = []
            st.rerun()
        node_to_render = cur.get(last, {})
        render_section(st.session_state.path, node_to_render)

# ------------------ Persist and apply saved settings if changed on disk externally ------------------
saved = safe_load_json(SETTINGS_FILE, DEFAULT_SETTINGS.copy())
if saved != st.session_state.live_settings:
    st.session_state.live_settings = saved.copy()
    settings.update(saved)
    apply_global_styles(st.session_state.live_settings)

st.markdown("<p style='text-align:center;color:lightgray;margin-top:20px;'>Developed for BSNL Customer Care Marthandam 📍 | Jijo Shaji</p>", unsafe_allow_html=True)
