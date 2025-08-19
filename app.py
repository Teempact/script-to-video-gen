# AI Script-to-Video Generator (Streamlit)
# ----------------------------------------
# Paste a script, click "Generate Video", and get an MP4 with narration (gTTS) + images (Pexels).
# If Pexels API key is missing, placeholder images are used.
# Deployment: Streamlit Community Cloud. Add PEXELS_API_KEY in app Secrets.

import os
import re
import time
import requests
import tempfile
import streamlit as st
from typing import List
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import textwrap

# ---- Safe import of MoviePy ----
try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    from moviepy.config import change_settings
    import imageio_ffmpeg
    MOVIEPY_AVAILABLE = True
    # Point MoviePy to bundled ffmpeg
    change_settings({"FFMPEG_BINARY": imageio_ffmpeg.get_ffmpeg_exe()})
except Exception as e:
    MOVIEPY_AVAILABLE = False
    MOVIEPY_ERROR = str(e)

# ---- Streamlit setup ----
st.set_page_config(page_title="AI Script-to-Video Generator", page_icon="🎬", layout="centered")
st.title("AI Script-to-Video Generator 🎬")

# If MoviePy is missing, stop early with clear message
if not MOVIEPY_AVAILABLE:
    st.error("⚠️ MoviePy or ffmpeg is not available in this environment.")
    st.write("To fix this, make sure your **requirements.txt** includes:")
    st.code("streamlit\ngTTS\nmoviepy\nimageio-ffmpeg\nrequests\nPillow\n")
    st.write("Error details:")
    st.code(MOVIEPY_ERROR)
    st.stop()

# --------------- Utilities ---------------

def split_into_scenes(script: str) -> List[str]:
    """Split script into scenes by blank lines; fallback to ~3-sentence chunks."""
    script = script.strip()
    if "\n\n" in script:
        parts = [p.strip() for p in script.split("\n\n") if p.strip()]
        if parts:
            return parts
    sentences = re.split(r'(?<=[.!?])\s+', script)
    sentences = [s.strip() for s in sentences if s.strip()]
    scenes, chunk = [], []
    for s in sentences:
        chunk.append(s)
        if len(chunk) >= 3:
            scenes.append(" ".join(chunk))
            chunk = []
    if chunk:
        scenes.append(" ".join(chunk))
    return scenes if scenes else [script]

def safe_keyword_text(text: str, fallback: str) -> str:
    cleaned = re.sub(r'[^A-Za-z0-9\s]', '', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    words = cleaned.split()
    if len(words) < 2 and fallback:
        return fallback
    return " ".join(words[:6]) if words else (fallback or "abstract background")

def fetch_image_from_pexels(query: str, dest_path: str) -> bool:
    api_key = st.secrets.get("PEXELS_API_KEY", "")
    if not api_key:
        return False
    headers = {"Authorization": api_key}
    params = {"query": query, "per_page": 1, "orientation": "landscape"}
    try:
        r = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        photos = data.get("photos", [])
        if not photos:
            return False
        src = photos[0]["src"].get("large") or photos[0]["src"].get("medium") or photos[0]["src"].get("original")
        if not src:
            return False
        img = requests.get(src, timeout=30)
        img.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(img.content)
        return True
    except Exception as e:
        st.warning(f"Pexels fetch failed for '{query}': {e}")
        return False

def make_placeholder_image(text: str, dest_path: str, size=(1280, 720)):
    img = Image.new("RGB", size, color=(20, 20, 20))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    wrapped = "\n".join(textwrap.wrap(text, width=40))[:400]
    w, h = draw.multiline_textsize(wrapped, font=font)
    x, y = (size[0] - w) // 2, (size[1] - h) // 2
    draw.multiline_text((x, y), wrapped, fill=(230, 230, 230), font=font, align="center")
    img.save(dest_path)

def build_video(scenes: List[str], topic_keywords: str, output_path: str, fps: int = 24):
    clips = []
    tempdir = tempfile.mkdtemp(prefix="s2v_")
    progress = st.progress(0, text="Generating narration and images...")
    total = max(len(scenes), 1)

    for i, scene in enumerate(scenes):
        # Narration
        tts = gTTS(scene)
        audio_file = os.path.join(tempdir, f"scene_{i}.mp3")
        tts.save(audio_file)
        audio_clip = AudioFileClip(audio_file)

        # Image
        img_file = os.path.join(tempdir, f"scene_{i}.jpg")
        query = safe_keyword_text(scene, topic_keywords)
        ok = fetch_image_from_pexels(query, img_file)
        if not ok:
            make_placeholder_image(scene[:120], img_file)

        ic = ImageClip(img_file).set_duration(max(audio_clip.duration, 0.1))
        ic = ic.resize(height=720).on_color(size=(1280, 720), color=(0, 0, 0), pos=("center", "center"))
        ic = ic.set_audio(audio_clip)
        clips.append(ic)
        progress.progress((i + 1) / total, text=f"Prepared scene {i+1}/{total}")

    final = concatenate_videoclips(clips, method="compose")
    try:
        final.write_videofile(output_path, fps=fps, codec="libx264", audio_codec="aac",
                              threads=2, verbose=False, logger=None)
    except Exception:
        final.write_videofile(output_path, fps=fps, codec="mpeg4", audio_codec="aac",
                              threads=2, verbose=False, logger=None)

# --------------- UI ---------------

st.write("Paste your script below. Separate scenes with a blank line for best results.")

with st.expander("ℹ️ Tips for good results"):
    st.markdown(
        "- Use short paragraphs (2–4 sentences) per scene.\n"
        "- Add **Topic keywords** (e.g., *space exploration, rockets*) so the image search is on point.\n"
        "- The app uses free **gTTS** for narration and **Pexels** for images. Set your PEXELS_API_KEY in **Secrets**."
    )

script = st.text_area("Your script", height=220, placeholder="Write or paste your script here. Use blank lines to separate scenes.")
keywords = st.text_input("Topic keywords (optional)", help="Used for image search when the scene text is too generic.")
make_btn = st.button("Generate Video", type="primary")

if make_btn:
    if not script.strip():
        st.error("Please paste a script first.")
        st.stop()

    if "PEXELS_API_KEY" not in st.secrets:
        st.warning("No PEXELS_API_KEY found in Streamlit Secrets. The app will use placeholder images.")

    scenes = split_into_scenes(script)
    st.write(f"Detected **{len(scenes)}** scene(s).")

    out_path = os.path.join(tempfile.gettempdir(), "script2video_output.mp4")
    with st.spinner("Building your video..."):
        build_video(scenes, keywords, out_path, fps=24)

    st.success("Done! Preview and download below.")
    st.video(out_path)
    with open(out_path, "rb") as f:
        st.download_button("Download MP4", f, file_name="video.mp4", mime="video/mp4")
