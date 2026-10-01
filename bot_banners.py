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
        print("Iniciando navegador...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()
        
        resultados = []
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        contador_img = 1

        for sitio in Sitios:
            print(f"Navegando a {sitio['nombre']} ({sitio['url']})...")
            try:
                await page.goto(sitio["url"], wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(3000)
                
                # Simular scroll para forzar la carga de componentes dinámicos
                await page.evaluate("window.scrollBy(0, 600)")
                await page.wait_for_timeout(2000)

                # Buscar en todos los elementos interactivos o de imagen
                banners_elementos = await page.query_selector_all("a, img, div[class*='banner'], div[class*='slider'], div[class*='carousel']")
                
                for elem in banners_elementos:
                    texto = await elem.inner_text() or ""
                    alt = await elem.get_attribute("alt") or ""
                    href = await elem.get_attribute("href") or ""
                    src = await elem.get_attribute("src") or ""
                    
                    contenido_comb = f"{texto} {alt} {href} {src}".lower()

                    for marca in MARCAS:
                        if marca in contenido_comb:
                            url_completa = href
                            if href and not href.startswith("http"):
                                url_completa = sitio["url"].rstrip("/") + "/" + href.lstrip("/")

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
                                "Texto / Banner": texto.strip() or alt.strip() or f"Banner {marca.capitalize()} detectado",
                                "Enlace Promocional": url_completa or sitio["url"],
                                "Imagen": foto_url
                            })
                            contador_img += 1
                            break
            except Exception as e:
                print(f"Error al revisar {sitio['nombre']}: {e}")

        await browser.close()
        
        # Eliminar duplicados en base a Supermercado + Marca + Texto
        if resultados:
            df = pd.DataFrame(resultados).drop_duplicates(subset=["Supermercado", "Marca", "Texto / Banner"])
            resultados_limpios = df.to_dict(orient="records")
        else:
            resultados_limpios = []

        # 1. Guardar en JSON para el Dashboard Web
        with open("reporte_banners.json", "w", encoding="utf-8") as f:
            json.dump(resultados_limpios, f, ensure_ascii=False, indent=4)
            print("✓ Guardado 'reporte_banners.json' correctamente.")

        # 2. Acumular en el Histórico
        historico = []
        if os.path.exists("historico_banners.json"):
            try:
                with open("historico_banners.json", "r", encoding="utf-8") as f:
                    historico = json.load(f)
            except Exception:
                historico = []
        
        historico.extend(resultados_limpios)
        with open("historico_banners.json", "w", encoding="utf-8") as f:
            json.dump(historico, f, ensure_ascii=False, indent=4)

        print(f"\n¡Proceso finalizado! Se registraron {len(resultados_limpios)} banners.")

if __name__ == "__main__":
    asyncio.run(monitorear_banners())
