"""
Mini CapCut - Editor de vídeo automático
Javi: sube tus escenas, ordénalas y córtalas, añade subtítulos automáticos
y una canción adaptada al vídeo. Todo en una interfaz web sencilla.
"""

import os
import shutil
import subprocess
import tempfile
import uuid

import streamlit as st
from faster_whisper import WhisperModel

st.set_page_config(page_title="Mini CapCut", layout="wide")

WORKDIR = tempfile.gettempdir()
SESSION_ID = st.session_state.get("session_id") or str(uuid.uuid4())[:8]
st.session_state["session_id"] = SESSION_ID
PROJECT_DIR = os.path.join(WORKDIR, f"minicapcut_{SESSION_ID}")
os.makedirs(PROJECT_DIR, exist_ok=True)

FONT_OPTIONS = {
    "Impact (estilo meme)": "Impact",
    "Montserrat Bold": "Montserrat-Bold",
    "Arial Bold": "Arial-Bold",
    "Comic Sans": "Comic Sans MS",
}

# ---------- Utilidades ----------

def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        st.error(f"Error ejecutando ffmpeg:\n{result.stderr[-2000:]}")
        st.stop()
    return result


def get_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


@st.cache_resource
def load_whisper_model():
    return WhisperModel("small", device="cpu", compute_type="int8")


def seconds_to_ass_time(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_ass_subtitles(segments, ass_path, font_name, font_size, color_hex,
                         outline_color_hex, position):
    def hex_to_ass_color(hex_color):
        hex_color = hex_color.lstrip("#")
        r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
        return f"&H00{b}{g}{r}"

    primary = hex_to_ass_color(color_hex)
    outline = hex_to_ass_color(outline_color_hex)
    alignment = {"Abajo": 2, "Centro": 5, "Arriba": 8}[position]

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary},{primary},{outline},&H00000000,1,0,0,0,100,100,0,0,1,4,0,{alignment},60,60,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for seg in segments:
        start = seconds_to_ass_time(seg["start"])
        end = seconds_to_ass_time(seg["end"])
        text = seg["text"].strip().replace("\n", " ")
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(lines))


# ---------- Estado del proyecto ----------

if "scenes" not in st.session_state:
    st.session_state.scenes = []  # cada escena: dict(path, name, start, end, duration)

st.title("🎬 Mini CapCut")
st.caption("Sube tus escenas en orden, córtalas, añade subtítulos automáticos y música.")

# ---------- 1. Subida de escenas ----------

st.header("1. Escenas")
uploaded_files = st.file_uploader(
    "Sube tus clips de vídeo en el orden que quieras montarlos",
    type=["mp4", "mov", "mkv"], accept_multiple_files=True
)

if uploaded_files:
    existing_names = {s["name"] for s in st.session_state.scenes}
    for uf in uploaded_files:
        if uf.name in existing_names:
            continue
        scene_path = os.path.join(PROJECT_DIR, uf.name)
        with open(scene_path, "wb") as f:
            f.write(uf.getbuffer())
        dur = get_duration(scene_path)
        st.session_state.scenes.append({
            "path": scene_path, "name": uf.name,
            "start": 0.0, "end": dur, "duration": dur
        })

if st.session_state.scenes:
    for i, scene in enumerate(st.session_state.scenes):
        with st.expander(f"Escena {i+1}: {scene['name']} ({scene['duration']:.1f}s)", expanded=True):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col2:
                start, end = st.slider(
                    "Recorte (segundos) — arrastra para ajustar inicio y fin",
                    0.0, scene["duration"],
                    (scene["start"], scene["end"]), step=0.1, key=f"trim_{i}"
                )
                scene["start"], scene["end"] = start, end
                st.caption(f"Duración tras el recorte: {end - start:.1f}s")
            with col1:
                # Vista previa del recorte: se regenera cada vez que mueves el slider
                preview_key = f"preview_{i}_{start}_{end}"
                preview_path = os.path.join(PROJECT_DIR, f"preview_{i}.mp4")
                if st.session_state.get(f"preview_cache_{i}") != preview_key:
                    with st.spinner("Actualizando vista previa..."):
                        fast = subprocess.run([
                            "ffmpeg", "-y", "-ss", str(start), "-to", str(end),
                            "-i", scene["path"], "-c", "copy", "-avoid_negative_ts", "make_zero",
                            preview_path
                        ], capture_output=True)
                        if fast.returncode != 0:
                            # El recorte rápido (sin recodificar) puede fallar según los
                            # keyframes del clip; recodificamos como respaldo.
                            subprocess.run([
                                "ffmpeg", "-y", "-ss", str(start), "-to", str(end),
                                "-i", scene["path"], "-c:v", "libx264", "-c:a", "aac",
                                preview_path
                            ], capture_output=True)
                    st.session_state[f"preview_cache_{i}"] = preview_key
                st.video(preview_path)
                st.caption("👆 Así queda esta escena con el recorte actual")
            with col3:
                if i > 0 and st.button("⬆️ Subir", key=f"up_{i}"):
                    st.session_state.scenes[i-1], st.session_state.scenes[i] = \
                        st.session_state.scenes[i], st.session_state.scenes[i-1]
                    st.rerun()
                if i < len(st.session_state.scenes) - 1 and st.button("⬇️ Bajar", key=f"down_{i}"):
                    st.session_state.scenes[i+1], st.session_state.scenes[i] = \
                        st.session_state.scenes[i], st.session_state.scenes[i+1]
                    st.rerun()
                if st.button("🗑️ Quitar", key=f"del_{i}"):
                    st.session_state.scenes.pop(i)
                    st.rerun()
else:
    st.info("Sube al menos una escena para empezar.")

# ---------- 2. Subtítulos ----------

st.header("2. Subtítulos automáticos")
enable_subs = st.checkbox("Generar subtítulos automáticos", value=True)
if enable_subs:
    c1, c2, c3 = st.columns(3)
    with c1:
        font_label = st.selectbox("Fuente", list(FONT_OPTIONS.keys()))
        font_name = FONT_OPTIONS[font_label]
    with c2:
        font_size = st.slider("Tamaño de letra", 40, 120, 70)
        position = st.selectbox("Posición", ["Abajo", "Centro", "Arriba"])
    with c3:
        color_hex = st.color_picker("Color del texto", "#FFFFFF")
        outline_hex = st.color_picker("Color del borde", "#000000")

# ---------- 3. Música ----------

st.header("3. Música")
music_file = st.file_uploader("Sube una canción (opcional)", type=["mp3", "wav", "m4a"])
music_volume = st.slider("Volumen de la música", 0.0, 1.0, 0.25)
duck_original = st.checkbox("Bajar la música cuando hay voz en el vídeo", value=True)

# ---------- 4. Render ----------

st.header("4. Generar vídeo final")

if st.button("🚀 Montar vídeo", type="primary", disabled=not st.session_state.scenes):
    with st.spinner("Cortando y uniendo escenas..."):
        trimmed_paths = []
        for i, scene in enumerate(st.session_state.scenes):
            trimmed_path = os.path.join(PROJECT_DIR, f"trim_{i}.mp4")
            run([
                "ffmpeg", "-y", "-ss", str(scene["start"]), "-to", str(scene["end"]),
                "-i", scene["path"],
                "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                "-c:v", "libx264", "-c:a", "aac", "-r", "30", trimmed_path
            ])
            trimmed_paths.append(trimmed_path)

        concat_list = os.path.join(PROJECT_DIR, "concat.txt")
        with open(concat_list, "w") as f:
            for p in trimmed_paths:
                f.write(f"file '{p}'\n")

        merged_path = os.path.join(PROJECT_DIR, "merged.mp4")
        run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
            "-c", "copy", merged_path
        ])

    current_video = merged_path

    if enable_subs:
        with st.spinner("Transcribiendo audio y generando subtítulos..."):
            model = load_whisper_model()
            segments_gen, _ = model.transcribe(current_video, language="es")
            segments = [{"start": s.start, "end": s.end, "text": s.text} for s in segments_gen]

        ass_path = os.path.join(PROJECT_DIR, "subs.ass")
        build_ass_subtitles(segments, ass_path, font_name, font_size,
                             color_hex, outline_hex, position)

        with st.spinner("Quemando subtítulos en el vídeo..."):
            subbed_path = os.path.join(PROJECT_DIR, "subbed.mp4")
            run([
                "ffmpeg", "-y", "-i", current_video,
                "-vf", f"ass={ass_path}",
                "-c:v", "libx264", "-c:a", "copy", subbed_path
            ])
            current_video = subbed_path

    if music_file is not None:
        with st.spinner("Adaptando la música al vídeo..."):
            music_path = os.path.join(PROJECT_DIR, "music_input" + os.path.splitext(music_file.name)[1])
            with open(music_path, "wb") as f:
                f.write(music_file.getbuffer())

            video_duration = get_duration(current_video)
            final_path = os.path.join(PROJECT_DIR, "final.mp4")

            if duck_original:
                filter_complex = (
                    f"[1:a]aloop=loop=-1:size=2e9,atrim=0:{video_duration},"
                    f"afade=t=out:st={max(video_duration-2,0)}:d=2,volume={music_volume}[music];"
                    f"[0:a][music]sidechaincompress=threshold=0.05:ratio=8:attack=20:release=300[aout]"
                )
                map_audio = "[aout]"
            else:
                filter_complex = (
                    f"[1:a]aloop=loop=-1:size=2e9,atrim=0:{video_duration},"
                    f"afade=t=out:st={max(video_duration-2,0)}:d=2,volume={music_volume}[music];"
                    f"[0:a][music]amix=inputs=2:duration=first[aout]"
                )
                map_audio = "[aout]"

            run([
                "ffmpeg", "-y", "-i", current_video, "-i", music_path,
                "-filter_complex", filter_complex,
                "-map", "0:v", "-map", map_audio,
                "-c:v", "copy", "-c:a", "aac", final_path
            ])
            current_video = final_path
    else:
        final_path = os.path.join(PROJECT_DIR, "final.mp4")
        shutil.copy(current_video, final_path)
        current_video = final_path

    st.success("¡Vídeo montado!")
    st.video(current_video)
    with open(current_video, "rb") as f:
        st.download_button("⬇️ Descargar vídeo", f, file_name="video_final.mp4", mime="video/mp4")