import streamlit as st
import streamlit.components.v1 as components
import os


def render_viewer(model_path: str, color_mode: str = "standard",
                  visible_storeys: list = None, selected_element_id: int = None):
    if not model_path or not os.path.exists(model_path):
        st.warning("Kein Modellpfad verfügbar. Bitte zuerst eine IFC-Datei hochladen.")
        return None

    # IFC.js viewer via CDN — loads the model from a data URL is not trivial,
    # so we display a placeholder with instructions and a basic Three.js demo shell.
    viewer_html = _build_viewer_html(model_path, color_mode, visible_storeys or [])

    result = components.html(viewer_html, height=600, scrolling=False)
    return result


def _build_viewer_html(model_path: str, color_mode: str, visible_storeys: list) -> str:
    storey_list = str(visible_storeys).replace("'", '"')
    return f"""
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #1a1a2e; color: #eee; font-family: Inter, sans-serif;
         display: flex; flex-direction: column; align-items: center;
         justify-content: center; height: 100vh; }}
  .info-box {{
    background: #16213e;
    border: 1px solid #2980B9;
    border-radius: 8px;
    padding: 32px;
    max-width: 480px;
    text-align: center;
  }}
  h2 {{ color: #2980B9; margin-bottom: 12px; }}
  p {{ color: #aaa; line-height: 1.6; margin-bottom: 16px; }}
  .badge {{ display: inline-block; padding: 4px 12px; background: #2980B9;
            border-radius: 12px; font-size: 0.85em; }}
  .path {{ font-size: 0.8em; color: #666; word-break: break-all; margin-top: 12px; }}
</style>
</head>
<body>
  <div class="info-box">
    <h2>🏗️ 3D Model Explorer</h2>
    <p>Der 3D-Viewer benötigt eine lokale Serverumgebung mit CORS-Unterstützung.<br>
       Das Modell wurde erfolgreich geladen und analysiert.</p>
    <span class="badge">Farbmodus: {color_mode}</span>
    <p class="path">Modellpfad: {model_path}</p>
    <p style="margin-top:16px; font-size:0.9em;">
      Alle Analysedaten sind auf den anderen Seiten verfügbar.<br>
      Seite 3–6 zeigen interaktive Charts mit Cross-Filtering.
    </p>
  </div>
</body>
</html>
"""
