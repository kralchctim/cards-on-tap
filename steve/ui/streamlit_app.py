import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from app.modules.card_name_loader import load_card_names
from app.ui_scan import scan_image_for_name

st.title("MTG Card Scanner")
st.write("Testing bench UI")

st.subheader("Images found in input/images")

images_dir = Path("input/images")

if not images_dir.exists():
    st.error("input/images does not exist.")
else:
    image_paths = []
    for pattern in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        image_paths.extend(images_dir.glob(pattern))

    image_paths = sorted(image_paths)

    if not image_paths:
        st.warning("No image files found.")
    else:
        if "image_page" not in st.session_state:
            st.session_state.image_page = 0

        n = len(image_paths)
        idx = st.session_state.image_page
        idx = max(0, min(idx, n - 1))
        st.session_state.image_page = idx

        candidate_names = load_card_names()
        image_path = image_paths[idx]

        nav_prev, nav_mid, nav_next = st.columns([1, 2, 1])
        with nav_prev:
            if st.button("← Previous", disabled=idx == 0, key="nav_prev"):
                st.session_state.image_page = idx - 1
                st.rerun()
        with nav_mid:
            st.markdown(f"**Image {idx + 1} of {n}**  \n`{image_path.name}`")
        with nav_next:
            if st.button("Next →", disabled=idx >= n - 1, key="nav_next"):
                st.session_state.image_page = idx + 1
                st.rerun()

        with st.container():
            st.write(f"### {image_path.name}")

            button_key = f"scan_{image_path.name}"
            scan_clicked = st.button("Scan this image", key=button_key)

            if scan_clicked:
                result = scan_image_for_name(image_path, candidate_names)

                col1, col2, col3 = st.columns([1, 1, 1])

                # LEFT COLUMN: original image
                with col1:
                    st.write("**Original image**")
                    st.image(str(image_path), width=300)

                # MIDDLE COLUMN: matches
                with col2:
                    st.write("**Card-name matches**")
                    for name, score in result["top_matches"]:
                        st.write(f"- {name} ({score:.1f})")

                    st.write("**Set-code matches**")
                    st.write(f"Using card name: {result['chosen_card_name_for_debug']}")
                    for set_code, score in result["set_top_matches"]:
                        st.write(f"- {set_code} ({score:.1f})")

                    st.write("**Collector-number matches**")
                    st.write(f"Using set code: {result['chosen_set_for_debug']}")
                    for collector_number, score in result["collector_top_matches"]:
                        st.write(f"- {collector_number} ({score:.1f})")

                # RIGHT COLUMN: crops + OCR evidence
                with col3:
                    st.write("**Name crop**")
                    st.image(result["name_region_image"], width=300)
                    st.write(f"Best OCR variant: {result['best_variant']}")
                    st.write(f"Best raw OCR text: {result['best_raw_text']}")
                    st.write(f"Best OCR name guess: {result['best_guess']}")

                    st.write("**Bottom-strip crop**")
                    st.image(result["bottom_strip_image"], width=300)
                    st.write(f"Bottom strip OCR variant: {result['bottom_best_variant']}")
                    st.write(f"Bottom strip raw OCR text: {result['bottom_best_raw_text']}")

                    parsed_bottom = result["parsed_bottom"]
                    st.write("**Parsed bottom strip**")
                    st.write(f"- Collector number: {parsed_bottom.get('collector_number', '')}")
                    st.write(f"- Set code: {parsed_bottom.get('set_code', '')}")
                    st.write(f"- Rarity: {parsed_bottom.get('rarity', '')}")
                    st.write(f"- Language: {parsed_bottom.get('language', '')}")
            else:
                st.image(str(image_path), width=200)

        bot_prev, bot_mid, bot_next = st.columns([1, 2, 1])
        with bot_prev:
            if st.button("← Previous", disabled=idx == 0, key="nav_prev_bottom"):
                st.session_state.image_page = idx - 1
                st.rerun()
        with bot_mid:
            st.caption(f"{idx + 1} / {n}")
        with bot_next:
            if st.button("Next →", disabled=idx >= n - 1, key="nav_next_bottom"):
                st.session_state.image_page = idx + 1
                st.rerun()
