import streamlit as st
import sqlite3
import pandas as pd

DB_PATH = "tak.db"

st.set_page_config(layout="wide")
st.title("Tim the All Knowing 🧠")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# -----------------------
# QUERY BUILDER
# -----------------------
def build_query(user_input):
    base_query = """
        SELECT c.id, c.name, c.type_line, c.mana_cost,
               c.oracle_text, c.power, c.toughness,
               c.colours, c.colour_identity, c.cmc,
               p.image_url
        FROM cards c
        LEFT JOIN printings p ON p.card_id = c.id
    """

    conditions = []
    params = []
    joins = ""

    tokens = user_input.split()

    for token in tokens:
        if ":" not in token:
            continue

        key, value = token.split(":", 1)

        if key == "name":
            conditions.append("LOWER(c.name) LIKE LOWER(?)")
            params.append(f"%{value}%")

        elif key == "type":
            conditions.append("LOWER(c.type_line) LIKE LOWER(?)")
            params.append(f"%{value}%")

        elif key == "text":
            conditions.append("LOWER(c.oracle_text) LIKE LOWER(?)")
            params.append(f"%{value}%")

        elif key == "cmc":
            conditions.append("c.cmc = ?")
            params.append(value)

        elif key == "colour":
            conditions.append("LOWER(c.colours) LIKE LOWER(?)")
            params.append(f"%{value}%")

        elif key == "identity":
            conditions.append("LOWER(c.colour_identity) LIKE LOWER(?)")
            params.append(f"%{value}%")

        elif key == "tag":
            joins = """
                JOIN card_tags ct ON ct.card_id = c.id
                JOIN tags t ON t.id = ct.tag_id
            """
            conditions.append("LOWER(t.name) = LOWER(?)")
            params.append(value)

        else:
            # fallback: treat as name search
            conditions.append("LOWER(c.name) LIKE LOWER(?)")
            params.append(f"%{token}%")

    full_query = base_query + " " + joins

    if conditions:
        full_query += " WHERE " + " AND ".join(conditions)

    full_query += " GROUP BY c.id LIMIT 50"

    return full_query, params


# -----------------------
# SEARCH INPUT
# -----------------------
query_input = st.text_input(
    "Search (e.g. 'dragon', 'type:creature tag:ramp', 'text:draw cmc:3')"
)

# -----------------------
# RESULTS
# -----------------------
if query_input:
    sql, params = build_query(query_input)
    df = pd.read_sql_query(sql, conn, params=params)

    st.write(f"{len(df)} results")

    for _, row in df.iterrows():
        with st.container():
            col1, col2 = st.columns([1, 2])

            # IMAGE
            with col1:
                if row["image_url"]:
                    st.image(row["image_url"], use_container_width=True)

            # DETAILS
            with col2:
                st.subheader(row["name"])
                st.write(row["type_line"])
                st.write(row["mana_cost"])
                st.write(row["oracle_text"])

                if row["power"] and row["toughness"]:
                    st.write(f"Power/Toughness: {row['power']}/{row['toughness']}")

                st.write(f"CMC: {row['cmc']}")
                st.write(f"Colours: {row['colours']}")
                st.write(f"Colour Identity: {row['colour_identity']}")

                # -----------------------
                # TAGS
                # -----------------------
                tag_df = pd.read_sql_query("""
                    SELECT t.name
                    FROM tags t
                    JOIN card_tags ct ON t.id = ct.tag_id
                    WHERE ct.card_id = ?
                """, conn, params=(row["id"],))

                tags = tag_df["name"].tolist()
                st.write("Tags:", ", ".join(tags) if tags else "None")

                # -----------------------
                # ADD TAG
                # -----------------------
                new_tag = st.text_input(
                    f"Add tag for {row['name']}",
                    key=f"add_{row['id']}"
                )

                if st.button("Add Tag", key=f"btn_add_{row['id']}"):
                    if new_tag:
                        # ensure tag exists
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

                        # insert relation
                        cursor.execute("""
                            INSERT OR IGNORE INTO card_tags 
                            (card_id, tag_id, confidence_score, source, reviewed_status)
                            VALUES (?, ?, ?, ?, ?)
                        """, (row["id"], tag_id, 1.0, "manual", "manual"))

                        conn.commit()
                        st.success("Tag added")

                # -----------------------
                # REMOVE TAG
                # -----------------------
                if tags:
                    tag_to_remove = st.selectbox(
                        "Remove tag",
                        tags,
                        key=f"remove_{row['id']}"
                    )

                    if st.button("Remove Tag", key=f"btn_remove_{row['id']}"):
                        cursor.execute("""
                            DELETE FROM card_tags
                            WHERE card_id = ?
                            AND tag_id = (
                                SELECT id FROM tags WHERE name = ?
                            )
                        """, (row["id"], tag_to_remove))

                        conn.commit()
                        st.success("Tag removed")

conn.close()
