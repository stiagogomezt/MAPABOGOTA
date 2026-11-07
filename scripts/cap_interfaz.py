from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    for w,h,name in [(1440,900,'interfaz_1440.png'),(1366,768,'interfaz_1366.png'),(390,844,'interfaz_390.png')]:
        pg = b.new_page(viewport={'width':w,'height':h})
        pg.goto('http://127.0.0.1:8000/', wait_until='commit', timeout=60000)
        pg.wait_for_timeout(4000)
        pg.screenshot(path='docs/capturas/'+name, timeout=60000)
        print(name, 'ok')
        pg.close()
    b.close()
