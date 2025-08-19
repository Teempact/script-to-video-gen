
# AI Script-to-Video Generator (Streamlit)

Create YouTube-ready videos from plain text scripts in minutes. Narration via free **gTTS**, images via **Pexels API**, stitching via **MoviePy**.

## Quick Start (Local)
```bash
pip install -r requirements.txt
streamlit run app.py
```
Set your Pexels API key in Streamlit **Secrets** (preferred) or create `.streamlit/secrets.toml` locally:
```toml
PEXELS_API_KEY = "YOUR_KEY"
```

## Deploy (Streamlit Community Cloud)
1. Push this folder to GitHub.
2. In Streamlit Cloud: **New app → Connect your repo → Select `app.py`**.
3. In **Settings → Secrets**, add:
```
PEXELS_API_KEY = "YOUR_KEY"
```
4. Deploy.

## Notes
- If no API key is set or an image isn't found, the app auto-generates a text placeholder image.
- Scenes are split by blank lines; otherwise it groups ~3 sentences per scene.
- Output is 1280×720 MP4 at 24 fps.
