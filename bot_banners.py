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

# Crear carpeta para fotos si no existe
os.makedirs("capturas", exist_ok=True)

async def monitorear_banners():
    async with async_playwright() as p:
        print("Iniciando navegador...")
        browser = await p.chromium.launch(headless=True)
        # Configurar pantalla grande para capturar bien los banners
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()
        
        resultados = []
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        contador_img = 1

        for sitio in Sitios:
            print(f"Navegando a {sitio['nombre']} ({sitio['url']})...")
            try:
                await page.goto(sitio["url"], wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(4000) # Esperar a que cargue el carrusel
                
                # Seleccionar solo enlaces e imágenes que estén realmente visibles
                banners_elementos = await page.query_selector_all("a, div[class*='banner'], div[class*='slider'], img")
                
                for elem in banners_elementos:
                    # Validar si el elemento es visible en pantalla
                    if not await elem.is_visible():
                        continue

                    texto = await elem.inner_text()
                    alt = await elem.get_attribute("alt") or ""
                    href = await elem.get_attribute("href") or ""
                    src = await elem.get_attribute("src") or ""
                    
                    contenido_comb = f"{texto} {alt} {href} {src}".lower()

                    for marca in MARCAS:
                        if marca in contenido_comb:
                            # Asegurar URL absoluta
                            url_completa = href
                            if href and not href.startswith("http"):
                                url_completa = sitio["url"].rstrip("/") + "/" + href.lstrip("/")

                            # Tomar foto del elemento banner
                            nombre_foto = f"capturas/banner_{contador_img}.png"
                            try:
                                await elem.screenshot(path=nombre_foto)
                                foto_url = f"capturas/banner_{contador_img}.png"
                            except Exception:
                                foto_url = ""

                            resultados.append({
                                "Fecha": fecha_actual,
                                "Supermercado": sitio["nombre"],
                                "Marca": marca.capitalize(),
                                "Texto / Banner": texto.strip() or alt.strip() or "Banner promocional visual",
                                "Enlace Promocional": url_completa or sitio["url"],
                                "Imagen": foto_url
                            })
                            contador_img += 1
                            break # Evitar duplicados por la misma marca en el mismo elemento
            except Exception as e:
                print(f"Error al revisar {sitio['nombre']}: {e}")

        await browser.close()
        
        # Guardar en JSON para la Web
        with open("reporte_banners.json", "w", encoding="utf-8") as f:
            json.dump(resultados, f, ensure_ascii=False, indent=4)
            print("✓ Guardado 'reporte_banners.json' con capturas.")

        # Guardar en Histórico
        historico = []
        if os.path.exists("historico_banners.json"):
            try:
                with open("historico_banners.json", "r", encoding="utf-8") as f:
                    historico = json.load(f)
            except Exception:
                historico = []
        
        historico.extend(resultados)
        with open("historico_banners.json", "w", encoding="utf-8") as f:
            json.dump(historico, f, ensure_ascii=False, indent=4)

        print(f"\n¡Éxito! Se detectaron y fotografiaron {len(resultados)} banners.")

if __name__ == "__main__":
    asyncio.run(monitorear_banners())
