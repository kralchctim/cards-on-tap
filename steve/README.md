# 🧠 Steve — MTG Card Recognition Tool

Steve is a Magic: The Gathering card recognition tool that processes images or video frames to identify cards using OCR and image matching.

The goal is simple:
Take a messy real-world image of cards → extract useful data → match it to real MTG cards.

---

## 🚀 Current Features

* 📸 Image input processing
* ✂️ Card segmentation (grid / contour-based)
* 🔍 Name extraction using OCR
* 🧾 Bottom strip extraction (set code, collector number)
* 🔗 Matching against Scryfall data
* 🖥️ Debug UI with:

  * Original image
  * Match candidates
  * OCR outputs

---

## 🧱 Project Structure

```
steve/
├── app/            # Core application logic
├── scripts/        # Entry points / runnable scripts
├── data/           # Reference data (e.g. Scryfall)
├── input/          # Test images/videos
├── output/         # Results + debug outputs
├── ui/             # UI / visualisation components
├── requirements.txt
├── README.md
```

---

## ⚙️ Setup

### 1. Clone the repo

```
git clone <your-repo-url>
cd steve
```

### 2. Create virtual environment

```
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
```

### 3. Install dependencies

```
pip install -r requirements.txt
```

---

## ▶️ Running Steve

Example:

```
python scripts/run.py
```

*(Update this once your actual entry script is locked in)*

---

## 🧪 How It Works (High Level)

1. **Input**

   * Image or frame is loaded

2. **Segmentation**

   * Cards are detected and cropped

3. **OCR**

   * Name region extracted
   * Bottom strip extracted

4. **Matching**

   * OCR text matched against Scryfall

5. **Output**

   * Best match returned
   * Debug visuals generated

---

## 🎯 Current Focus

* Improve OCR accuracy (names + set codes)
* Improve segmentation reliability
* Reduce false positives in matching
* Clean up pipeline between steps

---

## 🗺️ Roadmap (Next Steps)

* [ ] Reliable set code + collector number OCR
* [ ] Confidence scoring for matches
* [ ] Batch processing (multiple images)
* [ ] Archidekt / collection integration
* [ ] Store detected cards as a personal collection (source of truth)

---

## ⚠️ Known Limitations

* OCR struggles with:

  * Low lighting
  * Foils / glare
  * Weird fonts or older cards
* Matching can fail with noisy OCR output
* Segmentation assumes relatively clean layouts

---

## 🧠 Philosophy

Steve is being built iteratively:

* Keep things simple
* Make each step observable (debug output)
* Improve one piece at a time

No over-engineering. Just make it work, then make it better.

---

## 💾 Dev Workflow

* Work on one feature at a time
* Test immediately
* Commit often:

```
git add .
git commit -m "Describe what you changed"
git push
```

---

## 🤝 Notes

This is an in-progress project. Expect rough edges.

If something breaks:

* Check the debug output
* Check OCR text
* Check segmentation

It’s usually one of those three 😄

---

## 🧑‍💻 Author

Mitch (with a bit of AI help)
