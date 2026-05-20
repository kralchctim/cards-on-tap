import streamlit as st
import sqlite3
import pandas as pd

from search import build_search_query

DB_PATH = "tak.db"

st.set_page_config(layout="wide")
st.markdown("""
    <style>

    /* Import font */
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');

    /* Main app background + font */
    .stApp {
        background-color: #2B102B;
        font-family: 'Nunito', sans-serif;
    }

    /* ALL text */
    html, body, [class*="css"]  {
        font-family: 'Nunito', sans-serif;
    }

    /* Buttons */
    .stButton > button {
        font-family: 'Nunito', sans-serif;
        font-weight: 700;
        border-radius: 12px;
    }

    /* Text inputs */
    .stTextInput input {
        font-family: 'Nunito', sans-serif;
    }

    /* Selectboxes */
    .stSelectbox div[data-baseweb="select"] {
        font-family: 'Nunito', sans-serif;
    }

    </style>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 1, 1])

with col2:
    st.image("banner.png", use_container_width=True)

st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

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
# SEARCH INPUT
# -----------------------
query_input = st.text_input(
    "Search (Scryfall syntax: t:creature o:\"draw a card\" tag:ramp f:commander c:rg)"
)
include_extras = st.checkbox(
    "Include extras",
    value=False,
    help="Vanguard, Plane, Scheme, Phenomenon, Tokens, Emblems, memorabilia sets",
)

if query_input != st.session_state.last_query:
    st.session_state.page = 0
    st.session_state.last_query = query_input

# -----------------------
# RESULTS
# -----------------------
if query_input:
    sql, params, warnings = build_search_query(
        query_input,
        include_extras=include_extras,
    )

    for warning in warnings:
        st.warning(warning)

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
                # VIEW DETAILS BUTTON
                # -----------------------
                if st.button("View Details (below)", key=f"details_{card['id']}"):
                    st.session_state["selected_card"] = card["id"]
    
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

                    # Get all existing tags
                    all_tags_df = pd.read_sql_query("""
                        SELECT name
                        FROM tags
                        ORDER BY name
                    """, conn)

                    all_tags = all_tags_df["name"].tolist()

                    # Add special option
                    tag_options = [""] + ["Create New Tag"] + all_tags

                    selected_tag_option = st.selectbox(
                        "",
                        tag_options,
                        key=f"tag_select_{card['id']}",
                        label_visibility="collapsed"
                    )
                    # Show description for existing tags
                    if (
                        selected_tag_option != ""
                        and selected_tag_option != "Create New Tag"
                    ):

                        tag_desc_df = pd.read_sql_query("""
                            SELECT description
                            FROM tags
                            WHERE name = ?
                        """, conn, params=(selected_tag_option,))

                        existing_description = None

                        if not tag_desc_df.empty:
                            existing_description = tag_desc_df.iloc[0]["description"]

                        # Existing description → display it
                        if existing_description and str(existing_description).strip():

                            st.caption(existing_description)

                            new_tag_description = existing_description

                        # No description → allow user to add one
                        else:

                            new_tag_description = st.text_area(
                                "Add description (optional)",
                                key=f"missing_desc_{card['id']}",
                                height=80
                            )

                    else:
                        new_tag_description = None

                    # If creating new tag → show text box
                    if selected_tag_option == "Create New Tag":

                        new_tag = st.text_input(
                            "New tag name",
                            key=f"new_tag_{card['id']}"
                        )

                        new_tag_description = st.text_area(
                            "Tag description (optional)",
                            key=f"new_tag_desc_{card['id']}",
                            height=80
                        )

                    else:
                        new_tag = selected_tag_option
                        # Keep description entered for existing tags (if any).

                with add_col2:
                    if st.button("+", key=f"btn_add_{card['id']}"):
                        if new_tag:
                            cursor.execute("SELECT id FROM tags WHERE name = ?", (new_tag,))
                            tag_result = cursor.fetchone()

                            if tag_result:
                                tag_id = tag_result[0]
                                if new_tag_description and str(new_tag_description).strip():
                                    cursor.execute(
                                        """
                                        UPDATE tags
                                        SET description = ?
                                        WHERE id = ?
                                        AND (description IS NULL OR TRIM(description) = '')
                                        """,
                                        (new_tag_description.strip(), tag_id)
                                    )
                            else:
                                cursor.execute(
                                    """
                                    INSERT INTO tags (
                                        name,
                                        category,
                                        description,
                                        source
                                    )
                                    VALUES (?, ?, ?, ?)
                                    """,
                                    (
                                        new_tag,
                                        "manual",
                                        new_tag_description,
                                        "manual"
                                    )
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

    # -----------------------
    # LOAD EXISTING TAGS
    # -----------------------
    all_tags_df = pd.read_sql_query("""
        SELECT name
        FROM tags
        ORDER BY name
    """, conn)

    all_tags = all_tags_df["name"].tolist()

    tag_options = ["Create New Tag"] + all_tags

    col1, col2 = st.columns([4, 1])

    with col1:

        selected_bulk_tag_option = st.selectbox(
            "Select tag",
            tag_options,
            key="bulk_tag_select"
        )
        # Show description for existing tags
        if selected_bulk_tag_option != "Create New Tag":

            bulk_tag_desc_df = pd.read_sql_query("""
                SELECT description
                FROM tags
                WHERE name = ?
            """, conn, params=(selected_bulk_tag_option,))

            if not bulk_tag_desc_df.empty:

                bulk_tag_description_display = bulk_tag_desc_df.iloc[0]["description"]

                if bulk_tag_description_display:
                    st.caption(bulk_tag_description_display)

        if selected_bulk_tag_option == "Create New Tag":

            bulk_tag = st.text_input(
                "New tag name",
                key="bulk_new_tag"
            )

            bulk_tag_description = st.text_area(
                "Description (optional)",
                key="bulk_new_tag_desc",
                height=80
            )

        else:
            bulk_tag = selected_bulk_tag_option
            bulk_tag_description = None

    with col2:
        if st.button("Add to Selected"):

            if not selected_ids:
                st.warning("No cards selected")

            elif not bulk_tag:
                st.warning("Enter a tag")

            else:
                cursor.execute(
                    "SELECT id FROM tags WHERE name = ?",
                    (bulk_tag,)
                )

                tag_result = cursor.fetchone()

                if tag_result:
                    tag_id = tag_result[0]

                else:
                    cursor.execute("""
                        INSERT INTO tags (
                            name,
                            category,
                            description,
                            source
                        )
                        VALUES (?, ?, ?, ?)
                    """, (
                        bulk_tag,
                        "manual",
                        bulk_tag_description,
                        "manual"
                    ))

                    tag_id = cursor.lastrowid

                for card_id in selected_ids:
                    cursor.execute("""
                        INSERT OR IGNORE INTO card_tags 
                        (card_id, tag_id, confidence_score, source, reviewed_status)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        card_id,
                        tag_id,
                        1.0,
                        "manual",
                        "manual"
                    ))

                conn.commit()

                st.success(
                    f"Tag applied to {len(selected_ids)} cards"
                )

                st.rerun()

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

# -----------------------
# CARD DETAILS PANEL
# -----------------------
selected_card_id = st.session_state.get("selected_card")

if selected_card_id:

    detail_df = pd.read_sql_query("""
        SELECT *
        FROM cards
        WHERE id = ?
    """, conn, params=(selected_card_id,))

    if not detail_df.empty:

        card_data = detail_df.iloc[0]

        st.markdown("---")
        st.header(card_data["name"])

        with st.expander("Card Details", expanded=True):

            st.write("**Mana Cost:**", card_data["mana_cost"])
            st.write("**Type:**", card_data["type_line"])
            st.write("**Oracle Text:**", card_data["oracle_text"])
            st.write("**CMC:**", card_data["cmc"])
            st.write("**Colours:**", card_data["colours"])
            st.write("**Colour Identity:**", card_data["colour_identity"])
            st.write("**Power:**", card_data["power"])
            st.write("**Toughness:**", card_data["toughness"])
            st.write("**Keywords:**", card_data["keywords"])

            # -----------------------
            # TAGS
            # -----------------------
            tag_df = pd.read_sql_query("""
                SELECT t.name
                FROM tags t
                JOIN card_tags ct ON t.id = ct.tag_id
                WHERE ct.card_id = ?
            """, conn, params=(selected_card_id,))

            tags = tag_df["name"].tolist()

            st.write("**Tags:**", ", ".join(tags) if tags else "None")

            # -----------------------
            # RAW JSON
            # -----------------------
            with st.expander("Raw Scryfall JSON"):

                st.json(card_data["raw_scryfall_json"])

conn.close()
