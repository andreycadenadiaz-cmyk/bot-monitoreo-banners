import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import json
import pandas as pd

MARCAS = ["colgate", "oral-b", "sensodyne", "pepsodent"]

Sitios = [
    {"nombre": "Jumbo", "url": "https://www.jumbo.cl/"},
    {"nombre": "Lider (Walmart)", "url": "https://www.lider.cl/"}
]

async def monitorear_banners():
    async with async_playwright() as p:
        print("Iniciando navegador...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        resultados = []
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for sitio in Sitios:
            print(f"Navegando a {sitio['nombre']} ({sitio['url']})...")
            try:
                await page.goto(sitio["url"], wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000) # Espera ligera para carga dinámica
                
                # Buscar elementos con enlaces, imágenes o divs de banners
                banners_elementos = await page.query_selector_all("a, div[class*='banner'], img[alt], img[src]")
                
                for elem in banners_elementos:
                    texto = await elem.inner_text()
                    alt = await elem.get_attribute("alt") or ""
                    href = await elem.get_attribute("href") or ""
                    src = await elem.get_attribute("src") or ""
                    
                    contenido_comb = f"{texto} {alt} {href} {src}".lower()

                    for marca in MARCAS:
                        if marca in contenido_comb:
                            resultados.append({
                                "Fecha": fecha_actual,
                                "Supermercado": sitio["nombre"],
                                "Marca": marca.capitalize(),
                                "Texto / Banner": texto.strip() or alt.strip() or "Banner gráfico detectado",
                                "Enlace Promocional": href
                            })
            except Exception as e:
                print(f"Error al revisar {sitio['nombre']}: {e}")

        await browser.close()
        
        # Exportar a Excel consolidado
        if resultados:
            df = pd.DataFrame(resultados).drop_duplicates()
            df.to_excel("reporte_banners_diario.xlsx", index=False)
            print(f"\n¡Éxito! Se creó 'reporte_banners_diario.xlsx' con {len(df)} hallazgos en total.")
        else:
            print("\nMonitoreo finalizado: No se detectaron banners de estas marcas hoy.")

if __name__ == "__main__":
    asyncio.run(monitorear_banners())