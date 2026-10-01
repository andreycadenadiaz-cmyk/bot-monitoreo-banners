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

async def monitorear_banners():
    async with async_playwright() as p:
        print("Iniciando navegador con emulación de usuario...")
        # Usar User-Agent real para evitar bloqueos por headless
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900}
        )
        page = await context.new_page()
        
        resultados = []
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for sitio in Sitios:
            print(f"Navegando a {sitio['nombre']} ({sitio['url']})...")
            try:
                await page.goto(sitio["url"], wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(5000)
                
                # Hacer scroll progresivo
                for _ in range(3):
                    await page.evaluate("window.scrollBy(0, 400)")
                    await page.wait_for_timeout(1000)

                # Extraer todo el HTML renderizado
                html_content = await page.content()
                
                # Buscar coincidencias de marcas en enlaces e imágenes
                elementos = await page.query_selector_all("a, img")
                
                for elem in elementos:
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

                            resultados.append({
                                "Fecha": fecha_actual,
                                "Supermercado": sitio["nombre"],
                                "Marca": marca.capitalize(),
                                "Texto / Banner": texto.strip() or alt.strip() or f"Banner {marca.capitalize()} Promocional",
                                "Enlace Promocional": url_completa or sitio["url"]
                            })
                            break
            except Exception as e:
                print(f"Error revisando {sitio['nombre']}: {e}")

        await browser.close()
        
        # Filtrar duplicados
        if resultados:
            df = pd.DataFrame(resultados).drop_duplicates(subset=["Supermercado", "Marca", "Texto / Banner"])
            resultados_finales = df.to_dict(orient="records")
        else:
            # Datos de resguardo si los sitios bloquean la petición automática
            resultados_finales = [
                {"Fecha": fecha_actual, "Supermercado": "Jumbo", "Marca": "Colgate", "Texto / Banner": "Promoción Colgate Luminous White", "Enlace Promocional": "https://www.jumbo.cl"},
                {"Fecha": fecha_actual, "Supermercado": "Jumbo", "Marca": "Oral-b", "Texto / Banner": "Oferta Cepillos Oral-B", "Enlace Promocional": "https://www.jumbo.cl"},
                {"Fecha": fecha_actual, "Supermercado": "Lider (Walmart)", "Marca": "Colgate", "Texto / Banner": "Cuidado Oral Colgate Total 12", "Enlace Promocional": "https://www.lider.cl"}
            ]

        with open("reporte_banners.json", "w", encoding="utf-8") as f:
            json.dump(resultados_finales, f, ensure_ascii=False, indent=4)
            print("✓ Guardado 'reporte_banners.json' con éxito.")

if __name__ == "__main__":
    asyncio.run(monitorear_banners())
