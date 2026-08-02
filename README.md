# Mini CapCut

App web gratuita para montar vídeos: subes tus escenas en orden, las recortas,
le pones subtítulos automáticos (estilo CapCut) y una canción adaptada.

## Qué hace

1. **Escenas**: subes tus clips en orden. Puedes recortarlos (inicio/fin),
   reordenarlos con los botones ⬆️/⬇️ y quitar los que no quieras.
2. **Subtítulos**: transcribe el audio automáticamente (faster-whisper) y
   quema los subtítulos en el vídeo. Eliges fuente, tamaño, color y posición.
3. **Música**: subes una canción y se adapta automáticamente a la duración
   del vídeo (con fade out al final). Puedes bajar su volumen y activar que
   se reduzca automáticamente cuando hay voz (sidechain compression).
4. **Montar vídeo**: genera el vídeo final en 9:16, listo para descargar.

## Cómo desplegarlo gratis (igual que tus otras apps)

1. Crea un repositorio nuevo en GitHub y sube estos 3 archivos:
   `app.py`, `requirements.txt`, `packages.txt`
2. Ve a [share.streamlit.io](https://share.streamlit.io), conecta tu cuenta
   de GitHub y selecciona el repo.
3. Archivo principal: `app.py`. Dale a "Deploy".
4. La primera vez tardará varios minutos en instalar faster-whisper y ffmpeg.

## Notas importantes

- El plan gratuito de Streamlit Cloud tiene recursos limitados (CPU/RAM).
  Con vídeos largos o muchas escenas puede ir lento porque todo corre en
  CPU (transcripción y renderizado). Para uso personal va bien; si la
  compartes con más gente a la vez, puede saturarse.
- El modelo de Whisper usado es "small" (buen equilibrio calidad/velocidad
  en CPU). Se puede cambiar a "base" (más rápido, menos preciso) si hace
  falta más velocidad — está en `load_whisper_model()`.
- El corte y reordenado de escenas es con controles simples (sliders y
  botones), no un timeline visual tipo CapCut de arrastrar y soltar —
  Streamlit no permite eso de forma nativa. Si más adelante quieres un
  timeline visual de verdad, habría que construirlo aparte con HTML/JS
  (más trabajo, pero posible).
- Todo se guarda temporalmente en el servidor mientras usas la sesión;
  no hay almacenamiento persistente entre sesiones.

## Próximos pasos posibles

- Transiciones entre escenas (fundidos, cortes con movimiento)
- Plantillas de subtítulos guardadas (para no configurar cada vez)
- Librería de música libre de derechos integrada, para no tener que
  subir tú la canción cada vez
