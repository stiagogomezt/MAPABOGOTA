import pathlib
root = pathlib.Path(r"C:\Users\kevin\Desktop\mapabogota")
md = (root/"docs/BITACORA_PROYECTO.md").read_text(encoding="utf-8")
# simple md to html conversion using markdown library if available, else fallback
try:
    import markdown
    html_body = markdown.markdown(md, extensions=["tables","fenced_code"])
except Exception as e:
    # fallback: escape
    html_body = "<pre>"+md.replace("<","&lt;")+"</pre>"

# fix image paths: bitacora/img/ -> img/
html_body = html_body.replace("bitacora/img/", "img/")
# mermaid: replace the code block with div
html_body = html_body.replace('<pre><code class="language-mermaid">', '<pre><code class="language-mermaid" style="display:none">')
# Actually mermaid.js will handle pre code.mermaid
html_body = html_body.replace('language-mermaid', 'mermaid')

html = f"""<!DOCTYPE html>
<html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bitácora final MAPABOGOTA</title>
<link rel="stylesheet" href="../assets/tokens.css">
<link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600&family=Spectral:wght@600&display=swap" rel="stylesheet">
<style>
body{{background:#EDE7DA;color:#0F1B1E;font-family:Barlow,system-ui,sans-serif;margin:0;padding:0}}
h1,h2,h3{{font-family:Spectral,serif;color:#0F1B1E}}
h2{{border-bottom:2px solid #D6A24E;padding-bottom:6px;margin-top:36px}}
.wrap{{max-width:900px;margin:0 auto;padding:24px}}
.toc{{background:rgba(15,27,30,.06);border:1px solid rgba(15,27,30,.15);border-radius:12px;padding:16px;margin:16px 0}}
figure{{margin:24px 0}}
figure img{{max-width:100%;border-radius:8px;border:1px solid #ccc}}
figcaption{{font-size:13px;color:#333;margin-top:6px}}
table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:13px}}
th,td{{border:1px solid #bbb;padding:6px 8px;text-align:left}}
th{{background:#0F1B1E;color:#EDE7DA}}
pre{{background:#0F1B1E;color:#EDE7DA;padding:12px;border-radius:8px;overflow:auto;font-size:12px}}
a{{color:#8a6a2a}}
</style>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
</head><body>
<div class="wrap">
<nav class="toc"><strong>Índice</strong><ul>
<li><a href="#s1">1 Portada</a></li><li><a href="#s2">2 Resumen</a></li><li><a href="#s3">3 Objetivo</a></li><li><a href="#s4">4 Herramientas</a></li><li><a href="#s5">5 Declaración IA</a></li><li><a href="#s6">6 Datos</a></li><li><a href="#s7">7 Metodología</a></li><li><a href="#s8">8 Cronología</a></li><li><a href="#s9">9 Decisiones</a></li><li><a href="#s10">10 Problemas</a></li><li><a href="#s11">11 Calidad</a></li><li><a href="#s12">12 Estructura</a></li><li><a href="#s13">13 Reproducir</a></li><li><a href="#s14">14 Limitaciones</a></li><li><a href="#s15">15 Reflexión</a></li><li><a href="#s16">16 Licencias</a></li><li><a href="#s17">17 Anexos</a></li>
</ul></nav>
{html_body}
</div>
<script>mermaid.initialize({{startOnLoad:true}});</script>
</body></html>
"""
out = root/"web/bitacora/index.html"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(html, encoding="utf-8")
print("ok", out)
# also add anchor ids for sections? simple replace h2
