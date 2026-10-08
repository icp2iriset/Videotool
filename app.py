import streamlit as st
import os
import asyncio
import tempfile
import random
from PIL import Image, ImageOps, ImageFilter, ImageEnhance, ImageDraw, ImageFont

# --- PIL COMPATIBILITY PATCH FOR MOVIEPY ---
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

from mutagen.mp3 import MP3
from moviepy.editor import ImageClip, AudioFileClip, VideoFileClip, concatenate_videoclips
import edge_tts

st.set_page_config(page_title="VideoEditor by Vidya (Pro Suite)", page_icon="🎬", layout="wide")
st.title("🎬 VideoEditor by Vidya — Pro Suite")
st.write("Your all-in-one browser studio for Image-to-Video narration, Video Merging, and Precision Trimming.")

# --- NAVIGATION TABS ---
tab1, tab2, tab3 = st.tabs(["🎓 Image-to-Video Studio", "🔗 Video Merger", "✂️ Video Trimmer"])

# ==========================================
# TAB 1: IMAGE-TO-VIDEO STUDIO (ORIGINAL CONCEPT)
# ==========================================
with tab1:
    st.header("🎓 Widescreen Training Video Studio")
    st.write("Generate full HD 16:9 widescreen training videos with neural voiceover, lower-third subtitles, and cinematic zoom.")

    with st.sidebar:
        st.subheader("Studio Settings")
        voice_options = {
            "Prabhat (Male - Indian)": "en-IN-PrabhatNeural",
            "Neerja (Female - Indian)": "en-IN-NeerjaNeural",
            "Neerja Expressive (Female - Indian)": "en-IN-NeerjaExpressiveNeural"
        }
        selected_voice = st.selectbox("Select Voice Engine", list(voice_options.keys()), key="studio_voice")
        voice_id = voice_options[selected_voice]

        speed_options = {
            "Relaxed (0.9x)": "-10%",
            "Normal (1.0x)": "+0%",
            "Fast (1.1x)": "+10%"
        }
        selected_speed = st.selectbox("Narration Speed", list(speed_options.keys()), key="studio_speed")
        rate_str = speed_options[selected_speed]

        burn_subs = st.checkbox("✨ Burn Lower-Third Subtitles", value=True, key="studio_subs")
        ken_burns = st.checkbox("🎞️ Cinematic Zoom Animation", value=True, key="studio_zoom")
        custom_filename = st.text_input("Output Video Filename", value="VideoEditor_Training_Video", key="studio_fname")

    if "slides" not in st.session_state:
        st.session_state.slides = [
            {"img": None, "script": "Welcome to VideoEditor by Vidya training studio", "keyword": "Welcome"},
            {"img": None, "script": "Create professional widescreen media assets effortlessly", "keyword": "Studio Pro"}
        ]

    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        st.subheader("📋 Slide Segments & Narration Scripts")
    with col_h2:
        if st.button("➕ Add Slide", key="add_slide_btn"):
            st.session_state.slides.append({"img": None, "script": "", "keyword": ""})
            st.rerun()

    for i, slide in enumerate(st.session_state.slides):
        with st.expander(f"Slide Segment #{i+1}", expanded=True):
            c1, c2 = st.columns([2, 3])
            with c1:
                slide["img"] = st.file_uploader(f"Upload Image #{i+1}", type=["png", "jpg", "jpeg"], key=f"img_{i}")
            with c2:
                slide["keyword"] = st.text_input(f"Highlight Keyword #{i+1}", value=slide["keyword"], key=f"kw_{i}")
                slide["script"] = st.text_area(f"Narration Script #{i+1}", value=slide["script"], key=f"txt_{i}", height=75)
                
            if len(st.session_state.slides) > 1 and st.button(f"🗑️ Remove Segment #{i+1}", key=f"del_{i}"):
                st.session_state.slides.pop(i)
                st.rerun()

    def create_frame(img_bytes, text_chunk, keyword=""):
        raw_img = Image.open(img_bytes).convert("RGB")
        bg_fill = ImageOps.fit(raw_img, (1920, 1080), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        bg_fill = bg_fill.filter(ImageFilter.GaussianBlur(radius=30))
        bg_fill = ImageEnhance.Brightness(bg_fill).enhance(0.3)
        
        orig_w, orig_h = raw_img.size
        scale = min(1750 / orig_w, 920 / orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        resized_img = raw_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        canvas = bg_fill.copy()
        paste_x = (1920 - new_w) // 2
        paste_y = (1080 - new_h) // 2 - 35
        canvas.paste(resized_img, (paste_x, paste_y))
        
        draw = ImageDraw.Draw(canvas, "RGBA")
        try:
            font = ImageFont.truetype("arial.ttf", 40)
            kw_font = ImageFont.truetype("arial.ttf", 36)
        except:
            font = ImageFont.load_default()
            kw_font = ImageFont.load_default()
            
        if keyword:
            kw_w = int(kw_font.getlength(keyword)) + 40
            draw.rounded_rectangle([1920 - kw_w - 60, 40, 1920 - 60, 100], radius=12, fill=(13, 148, 136, 230))
            draw.text((1920 - kw_w - 40, 50), f"★ {keyword}", fill=(255, 255, 255), font=kw_font)
            
        if text_chunk:
            draw.rectangle([60, 1080 - 110, 1920 - 60, 1080 - 30], fill=(0, 0, 0, 200))
            draw.text((1920 // 2, 1080 - 70), text_chunk, fill=(255, 255, 255), font=font, anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0))
        return canvas

    async def generate_audio_studio(text, v_id, r_str, path):
        communicate = edge_tts.Communicate(text, v_id, rate=r_str)
        await communicate.save(path)

    if st.button("🚀 Compile Full HD Widescreen Video", type="primary", use_container_width=True, key="compile_studio"):
        valid = True
        for idx, s in enumerate(st.session_state.slides):
            if not s["img"] or not s["script"].strip():
                st.error(f"Please ensure Slide #{idx+1} has both an image and a script!")
                valid = False
                
        if valid:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            temp_dir = tempfile.gettempdir()
            safe_name = "".join(c for c in custom_filename if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
            output_path = os.path.join(temp_dir, f"{safe_name}.mp4")
            
            try:
                clips = []
                total_slides = len(st.session_state.slides)
                
                for idx, s in enumerate(st.session_state.slides):
                    status_text.text(f"Processing Segment {idx+1} of {total_slides}...")
                    progress_bar.progress(idx / total_slides)
                    
                    audio_path = os.path.join(temp_dir, f"audio_{random.randint(1000,9999)}.mp3")
                    asyncio.run(generate_audio_studio(s["script"], voice_id, rate_str, audio_path))
                    
                    duration = MP3(audio_path).info.length
                    audio_clip = AudioFileClip(audio_path)
                    
                    if burn_subs and s["script"].strip():
                        words = s["script"].split()
                        chunks = [" ".join(words[j:j+6]) for j in range(0, len(words), 6)]
                        sub_clips = []
                        for chunk in chunks:
                            chunk_dur = max(0.5, duration * (len(chunk.split()) / len(words)))
                            frame_img = create_frame(s["img"], chunk, s["keyword"])
                            img_path = os.path.join(temp_dir, f"frame_{random.randint(1000,9999)}.png")
                            frame_img.save(img_path)
                            
                            clip = ImageClip(img_path).set_duration(chunk_dur)
                            if ken_burns:
                                clip = clip.resize(lambda t: 1.0 + 0.06 * (t / chunk_dur))
                            sub_clips.append(clip)
                        slide_stream = concatenate_videoclips(sub_clips, method="compose")
                    else:
                        frame_img = create_frame(s["img"], "", s["keyword"])
                        img_path = os.path.join(temp_dir, f"frame_{random.randint(1000,9999)}.png")
                        frame_img.save(img_path)
                        slide_stream = ImageClip(img_path).set_duration(duration)
                        if ken_burns:
                            slide_stream = slide_stream.resize(lambda t: 1.0 + 0.06 * (t / duration))
                            
                    clips.append(slide_stream.set_audio(audio_clip))
                    
                status_text.text("Stitching final broadcast video stream...")
                final_video = concatenate_videoclips(clips, method="compose")
                final_video.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac', bitrate="5000k", logger=None)
                
                progress_bar.progress(1.0)
                status_text.text("Compilation successful!")
                st.success("🎉 Full HD Widescreen Video compiled successfully!")
                
                with open(output_path, "rb") as f:
                    st.download_button("📥 Download Compiled Video (.mp4)", f, file_name=f"{safe_name}.mp4", mime="video/mp4", use_container_width=True, key="dl_studio")
                    
            except Exception as e:
                st.error(f"An error occurred during video compilation: {e}")

# ==========================================
# TAB 2: VIDEO MERGER
# ==========================================
with tab2:
    st.header("🔗 Merge Multiple Video Files")
    st.write("Upload two or more videos in sequence to combine them into a single continuous video.")
    
    uploaded_videos = st.file_uploader(
        "Upload Video Files (MP4, MOV, AVI)", 
        type=["mp4", "mov", "avi"], 
        accept_multiple_files=True, 
        key="merge_files"
    )
    output_merge_name = st.text_input("Merged Output Filename", value="Merged_Video_Output", key="merge_fname")
    
    if st.button("🚀 Merge Videos", type="primary", key="merge_btn"):
        if uploaded_videos and len(uploaded_videos) >= 2:
            temp_dir = tempfile.gettempdir()
            safe_name = "".join(c for c in output_merge_name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
            output_path = os.path.join(temp_dir, f"{safe_name}.mp4")
            
            try:
                clips = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, v_file in enumerate(uploaded_videos):
                    status_text.text(f"Processing video {idx+1} of {len(uploaded_videos)} ({v_file.name})...")
                    v_path = os.path.join(temp_dir, f"vid_{idx}_{v_file.name}")
                    with open(v_path, "wb") as f:
                        f.write(v_file.read())
                    clips.append(VideoFileClip(v_path))
                    progress_bar.progress((idx + 1) / len(uploaded_videos))
                    
                status_text.text("Stitching video streams together...")
                final_clip = concatenate_videoclips(clips, method="compose")
                final_clip.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac', logger=None)
                
                progress_bar.progress(1.0)
                status_text.text("Merging complete!")
                st.success("🎉 Videos merged successfully!")
                
                with open(output_path, "rb") as f:
                    st.download_button(
                        "📥 Download Merged Video (.mp4)", 
                        f, 
                        file_name=f"{safe_name}.mp4", 
                        mime="video/mp4",
                        use_container_width=True,
                        key="dl_merge"
                    )
            except Exception as e:
                st.error(f"Error during video merging: {e}")
        else:
            st.warning("Please upload at least 2 video files to merge.")

# ==========================================
# TAB 3: VIDEO TRIMMER
# ==========================================
with tab3:
    st.header("✂️ Trim Video by Time Scale")
    st.write("Upload a video and select precise start and end times to clip out a specific segment.")
    
    trim_file = st.file_uploader("Upload Video to Trim", type=["mp4", "mov", "avi"], key="trim_file")
    
    if trim_file:
        temp_dir = tempfile.gettempdir()
        input_trim_path = os.path.join(temp_dir, trim_file.name)
        with open(input_trim_path, "wb") as f:
            f.write(trim_file.read())
            
        clip = VideoFileClip(input_trim_path)
        duration = clip.duration
        st.info(f"📹 Uploaded Video Duration: **{duration:.2f} seconds** (approx. {int(duration//60)} minutes {int(duration%60)} seconds)")
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            start_time = st.number_input("Start Time (seconds)", min_value=0.0, max_value=float(duration), value=0.0, step=0.1, key="start_t")
        with col_t2:
            end_time = st.number_input("End Time (seconds)", min_value=0.0, max_value=float(duration), value=float(duration), step=0.1, key="end_t")
            
        output_trim_name = st.text_input("Trimmed Output Filename", value="Trimmed_Video_Output", key="trim_fname")
        
        if st.button("✂️ Trim Video", type="primary", key="trim_btn"):
            if start_time >= end_time:
                st.error("Start time must be strictly less than the end time!")
            else:
                safe_trim_name = "".join(c for c in output_trim_name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
                trimmed_output_path = os.path.join(temp_dir, f"{safe_trim_name}.mp4")
                
                try:
                    with st.spinner("Trimming video segment..."):
                        trimmed_clip = clip.subclip(start_time, end_time)
                        trimmed_clip.write_videofile(trimmed_output_path, fps=24, codec='libx264', audio_codec='aac', logger=None)
                        
                    st.success("🎉 Video trimmed successfully!")
                    with open(trimmed_output_path, "rb") as f:
                        st.download_button(
                            "📥 Download Trimmed Video (.mp4)", 
                            f, 
                            file_name=f"{safe_trim_name}.mp4", 
                            mime="video/mp4",
                            use_container_width=True,
                            key="dl_trim"
                        )
                except Exception as e:
                    st.error(f"Error during video trimming: {e}")
