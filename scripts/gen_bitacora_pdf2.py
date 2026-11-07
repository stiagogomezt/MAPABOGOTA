from playwright.sync_api import sync_playwright
import pathlib
root = pathlib.Path(r"C:\Users\kevin\Desktop\mapabogota")
html_path = root/"web/bitacora/index.html"
out = root/"docs/Bitacora_MAPABOGOTA.pdf"
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.goto(html_path.as_uri(), wait_until="networkidle", timeout=60000)
    pg.wait_for_timeout(5000)
    # wait for images
    pg.wait_for_function("() => Array.from(document.images).every(i => i.complete)", timeout=30000)
    pg.pdf(path=str(out), format="Letter", margin={"top":"2cm","bottom":"2cm","left":"2cm","right":"2cm"}, display_header_footer=True, header_template="<div></div>", footer_template='<div style="width:100%;text-align:center;font-size:9px">Página <span class="pageNumber"></span> de <span class="totalPages"></span></div>', print_background=True)
    print("pdf ok", out.stat().st_size)
    b.close()
