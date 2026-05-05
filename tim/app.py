import streamlit as st
import sqlite3
import pandas as pd
import re

DB_PATH = "tak.db"

st.set_page_config(layout="wide")
st.title("Tim the All Knowing 🧠")

# -----------------------
# PAGINATION CONFIG
# -----------------------
PAGE_SIZE = 60

if "page" not in st.session_state:
    st.session_state.page = 0

if "last_query" not in st.session_state:
    st.session_state.last_query = ""

# -----------------------
# DB CONNECTION
# -----------------------
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# -----------------------
# QUERY PARSER
# -----------------------
def parse_query(input_string):
    pattern = r'(\w+:"[^"]+"|\w+:[^\s]+|"[^"]+"|\S+)'
    return re.findall(pattern, input_string)

# -----------------------
# QUERY BUILDER
# -----------------------
def build_query(user_input):
    base_query = """
        SELECT c.id, c.name,
               p.image_url
        FROM cards c
        LEFT JOIN printings p ON p.card_id = c.id
    """

    conditions = []
    params = []
    joins = ""

    tokens = parse_query(user_input)

    for token in tokens:
        if ":" in token:
            key, value = token.split(":", 1)
            value = value.strip('"')

            if key in ["name"]:
                conditions.append("LOWER(c.name) LIKE LOWER(?)")
                params.append(f"%{value}%")

            elif key in ["o", "oracle"]:
                conditions.append("LOWER(c.oracle_text) LIKE LOWER(?)")
                params.append(f"%{value}%")

            elif key in ["type"]:
                conditions.append("LOWER(c.type_line) LIKE LOWER(?)")
                params.append(f"%{value}%")

            elif key in ["tag"]:
                joins = """
                    JOIN card_tags ct ON ct.card_id = c.id
                    JOIN tags t ON t.id = ct.tag_id
                """
                conditions.append("LOWER(t.name) = LOWER(?)")
                params.append(value)

        elif token.startswith('"') and token.endswith('"'):
            value = token.strip('"')
            conditions.append("""
                (LOWER(c.name) LIKE LOWER(?) OR LOWER(c.oracle_text) LIKE LOWER(?))
            """)
            params.append(f"%{value}%")
            params.append(f"%{value}%")

        else:
            conditions.append("LOWER(c.name) LIKE LOWER(?)")
            params.append(f"%{token}%")

    full_query = base_query + " " + joins

    if conditions:
        full_query += " WHERE " + " AND ".join(conditions)

    full_query += " GROUP BY c.id"

    return full_query, params

# -----------------------
# SEARCH INPUT
# -----------------------
query_input = st.text_input(
    "Search (type:creature o:\"draw a card\" tag:ramp)"
)

if query_input != st.session_state.last_query:
    st.session_state.page = 0
    st.session_state.last_query = query_input

# -----------------------
# RESULTS
# -----------------------
if query_input:
    sql, params = build_query(query_input)
    df = pd.read_sql_query(sql, conn, params=params)

    total_results = len(df)
    total_pages = max(1, (total_results - 1) // PAGE_SIZE + 1)

    start_idx = st.session_state.page * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE

    page_df = df.iloc[start_idx:end_idx]

    st.write(f"{total_results} results")

    # -----------------------
    # PAGINATION CONTROLS
    # -----------------------
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("⬅️ Previous") and st.session_state.page > 0:
            st.session_state.page -= 1
            st.rerun()

    with col2:
        st.markdown(
            f"<div style='text-align:center;'>Page {st.session_state.page + 1} of {total_pages}</div>",
            unsafe_allow_html=True
        )

    with col3:
        if st.button("Next ➡️") and st.session_state.page < total_pages - 1:
            st.session_state.page += 1
            st.rerun()

    # -----------------------
    # APPLY SELECT/DESELECT FLAGS
    # -----------------------
    if st.session_state.get("select_all_flag"):
        for _, card in page_df.iterrows():
            st.session_state[f"select_{card['id']}"] = True
        st.session_state["select_all_flag"] = False

    if st.session_state.get("deselect_all_flag"):
        for _, card in page_df.iterrows():
            st.session_state[f"select_{card['id']}"] = False
        st.session_state["deselect_all_flag"] = False

    # -----------------------
    # TRACK SELECTED CARDS
    # -----------------------
    selected_ids = []

    # -----------------------
    # GRID DISPLAY
    # -----------------------
    cols_per_row = 6

    for i in range(0, len(page_df), cols_per_row):
        row_slice = page_df.iloc[i:i + cols_per_row]
        cols = st.columns(cols_per_row)

        for j, (_, card) in enumerate(row_slice.iterrows()):
            with cols[j]:

                # -----------------------
                # NEW: CHECKBOX
                # -----------------------
                selected = st.checkbox(
                    "Select",
                    key=f"select_{card['id']}"
                )

                if selected:
                    selected_ids.append(card["id"])

                # IMAGE OR PLACEHOLDER
                if pd.notna(card["image_url"]):

                    # 1. clean URLs
                    urls = [u for u in str(card["image_url"]).split("|") if u]

                    # 2. if nothing valid → treat as no image
                    if not urls:
                        urls = []

                    flip_key = f"flip_{card['id']}"

                    if flip_key not in st.session_state:
                        st.session_state[flip_key] = 0

                    current_idx = st.session_state[flip_key]

                    # 3. clamp index safely
                    if urls:
                        current_idx = current_idx % len(urls)
                        st.session_state[flip_key] = current_idx

                        st.image(urls[current_idx], use_container_width=True)

                        if len(urls) > 1:
                            if st.button("🔄", key=f"btn_{card['id']}"):
                                st.session_state[flip_key] = (current_idx + 1) % len(urls)
                                st.rerun()

                    else:
                        # fallback if no valid images
                        st.markdown(f"""
                            <div style="
                                height: 260px;
                                display: flex;
                                flex-direction: column;
                                justify-content: center;
                                align-items: center;
                                border: 1px solid #ddd;
                                border-radius: 8px;
                                background-color: #f9f9f9;
                                text-align: center;
                                padding: 10px;
                            ">
                                <div style="font-weight: 600; color: #666;">{card['name']}</div>
                                <div style="font-style: italic; color: #666;">No image</div>
                            </div>
                        """, unsafe_allow_html=True)

                else:
                    # original no-image case
                    st.markdown(...)
    
                # -----------------------
                # TAGS
                # -----------------------
                st.markdown("<small><b>CARD TAGS</b></small>", unsafe_allow_html=True)

                tag_df = pd.read_sql_query("""
                    SELECT t.name
                    FROM tags t
                    JOIN card_tags ct ON t.id = ct.tag_id
                    WHERE ct.card_id = ?
                """, conn, params=(card["id"],))

                tags = tag_df["name"].tolist()

                st.caption(" | ".join(tags) if tags else "None")

                # -----------------------
                # ADD TAG
                # -----------------------
                st.markdown("<small><b>ADD TAG</b></small>", unsafe_allow_html=True)

                add_col1, add_col2 = st.columns([4, 1])

                with add_col1:
                    new_tag = st.text_input("", key=f"add_{card['id']}", label_visibility="collapsed")

                with add_col2:
                    if st.button("+", key=f"btn_add_{card['id']}"):
                        if new_tag:
                            cursor.execute("SELECT id FROM tags WHERE name = ?", (new_tag,))
                            tag_result = cursor.fetchone()

                            if tag_result:
                                tag_id = tag_result[0]
                            else:
                                cursor.execute(
                                    "INSERT INTO tags (name, category, source) VALUES (?, ?, ?)",
                                    (new_tag, "manual", "manual")
                                )
                                tag_id = cursor.lastrowid

                            cursor.execute("""
                                INSERT OR IGNORE INTO card_tags 
                                (card_id, tag_id, confidence_score, source, reviewed_status)
                                VALUES (?, ?, ?, ?, ?)
                            """, (card["id"], tag_id, 1.0, "manual", "manual"))

                            conn.commit()
                            st.rerun()

                # -----------------------
                # REMOVE TAG
                # -----------------------
                if tags:
                    st.markdown("<small><b>REMOVE TAG</b></small>", unsafe_allow_html=True)

                    rem_col1, rem_col2 = st.columns([4, 1])

                    with rem_col1:
                        tag_to_remove = st.selectbox("", tags, key=f"remove_{card['id']}", label_visibility="collapsed")

                    with rem_col2:
                        if st.button("-", key=f"btn_remove_{card['id']}"):
                            cursor.execute("""
                                DELETE FROM card_tags
                                WHERE card_id = ?
                                AND tag_id = (
                                    SELECT id FROM tags WHERE name = ?
                                )
                            """, (card["id"], tag_to_remove))

                            conn.commit()
                            st.rerun()

        # spacing
        st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

    # -----------------------
    # NEW: BULK ACTIONS (AFTER GRID)
    # -----------------------
    st.markdown("#### Bulk Add Tag")

    col1, col2 = st.columns([4, 1])

    with col1:
        bulk_tag = st.text_input("Tag to apply", key="bulk_tag")

    with col2:
        if st.button("Add to Selected"):

            if not selected_ids:
                st.warning("No cards selected")
            elif not bulk_tag:
                st.warning("Enter a tag")
            else:
                cursor.execute("SELECT id FROM tags WHERE name = ?", (bulk_tag,))
                tag_result = cursor.fetchone()

                if tag_result:
                    tag_id = tag_result[0]
                else:
                    cursor.execute(
                        "INSERT INTO tags (name, category, source) VALUES (?, ?, ?)",
                        (bulk_tag, "manual", "manual")
                    )
                    tag_id = cursor.lastrowid

                for card_id in selected_ids:
                    cursor.execute("""
                        INSERT OR IGNORE INTO card_tags 
                        (card_id, tag_id, confidence_score, source, reviewed_status)
                        VALUES (?, ?, ?, ?, ?)
                    """, (card_id, tag_id, 1.0, "manual", "manual"))

                conn.commit()
                st.success(f"Tag applied to {len(selected_ids)} cards")
                st.rerun()
    # -----------------------
    # BULK REMOVE TAG
    # -----------------------
    st.markdown("#### Bulk Remove Tag")
    
    # Get tags that exist on selected cards
    selected_tags = []

    if selected_ids:
        placeholder = ",".join(["?"] * len(selected_ids))

        tag_df = pd.read_sql_query(f"""
            SELECT DISTINCT t.name
            FROM tags t
            JOIN card_tags ct ON t.id = ct.tag_id
            WHERE ct.card_id IN ({placeholder})
        """, conn, params=selected_ids)

        selected_tags = tag_df["name"].tolist()

    col1, col2 = st.columns([4, 1])

    with col1:
        tag_to_remove_bulk = st.selectbox(
            "Select tag to remove",
            selected_tags,
            key="bulk_remove_tag"
        )

    with col2:
        if st.button("Remove from Selected"):

            if not selected_ids:
                st.warning("No cards selected")
            elif not selected_tags:
                st.warning("No tags available to remove")
            else:
                cursor.execute(
                    "SELECT id FROM tags WHERE name = ?",
                    (tag_to_remove_bulk,)
                )
                tag_result = cursor.fetchone()

                if tag_result:
                    tag_id = tag_result[0]

                    for card_id in selected_ids:
                        cursor.execute("""
                            DELETE FROM card_tags
                            WHERE card_id = ? AND tag_id = ?
                        """, (card_id, tag_id))

                    conn.commit()
                    st.success(f"Removed '{tag_to_remove_bulk}' from {len(selected_ids)} cards")
                    st.rerun()
                    
    # -----------------------
    # SELECT / DESELECT ALL (CURRENT PAGE)
    # -----------------------

    if st.button("Select All on Page"):
        st.session_state["select_all_flag"] = True
        st.rerun()

    if st.button("Deselect All on Page"):
        st.session_state["deselect_all_flag"] = True
        st.rerun()

conn.close()
