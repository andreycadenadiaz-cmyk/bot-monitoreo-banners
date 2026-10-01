import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import json
import os
import pandas as pd

MARCAS = ["colgate", "oral-b", "sensodyne", "pepsodent"]

Sitios = [
    {"nombre": "Jumbo", "url": "https://www.jumbo.cl/"},
    {"nombre": "Lider (Walmart)", "url": "https://www.lider.cl/"}
]

os.makedirs("capturas", exist_ok=True)

async def monitorear_banners():
    async with async_playwright() as p:
        print("Iniciando navegador anti-bloqueo...")
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="es-CL",
            timezone_id="America/Santiago"
        )
        
        page = await context.new_page()
        
        # Evitar detección por webdriver
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        resultados = []
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        contador_img = 1

        for sitio in Sitios:
            print(f"Navegando a {sitio['nombre']} ({sitio['url']})...")
            try:
                response = await page.goto(sitio["url"], wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(4000)

                # Intentar cerrar modales/cookies si existen
                try:
                    btns_cerrar = await page.query_selector_all("button:has-text('Aceptar'), button:has-text('Entendido'), .close-modal")
                    for btn in btns_cerrar:
                        if await btn.is_visible():
                            await btn.click()
                            await page.wait_for_timeout(1000)
                except Exception:
                    pass

                # Scroll progresivo
                for _ in range(3):
                    await page.evaluate("window.scrollBy(0, 500)")
                    await page.wait_for_timeout(1000)

                # Capturar elementos
                elementos = await page.query_selector_all("a, img, div[class*='banner'], div[class*='slider']")

                for elem in elementos:
                    try:
                        href = await elem.get_attribute("href") or ""
                        src = await elem.get_attribute("src") or ""
                        alt = await elem.get_attribute("alt") or ""
                        texto = await elem.inner_text() or ""
                        
                        combo = f"{href} {src} {alt} {texto}".lower()

                        for marca in MARCAS:
                            if marca in combo:
                                url_completa = href
                                if href and not href.startswith("http"):
                                    url_completa = sitio["url"].rstrip("/") + "/" + href.lstrip("/")

                                # Tomar foto del banner
                                nombre_foto = f"capturas/banner_{contador_img}.png"
                                try:
                                    await elem.screenshot(path=nombre_foto)
                                    foto_url = nombre_foto
                                except Exception:
                                    foto_url = ""

                                resultados.append({
                                    "Fecha": fecha_actual,
                                    "Supermercado": sitio["nombre"],
                                    "Marca": marca.capitalize(),
                                    "Texto / Banner": texto.strip() or alt.strip() or f"Banner Promocional {marca.capitalize()}",
                                    "Enlace Promocional": url_completa or sitio["url"],
                                    "Imagen": foto_url
                                })
                                contador_img += 1
                                break
                    except Exception:
                        continue

            except Exception as e:
                print(f"Error revisando {sitio['nombre']}: {e}")

        await browser.close()

        # Limpiar duplicados
        if resultados:
            df = pd.DataFrame(resultados).drop_duplicates(subset=["Supermercado", "Marca", "Texto / Banner"])
            resultados_finales = df.to_dict(orient="records")
        else:
            resultados_finales = []

        # Guardar resultados
        with open("reporte_banners.json", "w", encoding="utf-8") as f:
            json.dump(resultados_finales, f, ensure_ascii=False, indent=4)
            print(f"✓ Guardados {len(resultados_finales)} banners capturados.")

        if resultados_finales:
            pd.DataFrame(resultados_finales).to_excel("reporte_banners_diario.xlsx", index=False)

if __name__ == "__main__":
    asyncio.run(monitorear_banners())
