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
        print("Iniciando navegador...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        resultados = []
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for sitio in Sitios:
            print(f"Navegando a {sitio['nombre']} ({sitio['url']})...")
            try:
                await page.goto(sitio["url"], wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)
                
                banners_elementos = await page.query_selector_all("a, div[class*='banner'], img[alt], img[src]")
                
                for elem in banners_elementos:
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

                            resultados.append({
                                "Fecha": fecha_actual,
                                "Supermercado": sitio["nombre"],
                                "Marca": marca.capitalize(),
                                "Texto / Banner": texto.strip() or alt.strip() or "Banner gráfico detectado",
                                "Enlace Promocional": url_completa or sitio["url"]
                            })
            except Exception as e:
                print(f"Error al revisar {sitio['nombre']}: {e}")

        await browser.close()
        
        # Eliminar duplicados simples
        df_resultados = pd.DataFrame(resultados).drop_duplicates().to_dict(orient="records") if resultados else []

        # 1. Guardar el reporte del día en JSON (Para la Web)
        with open("reporte_banners.json", "w", encoding="utf-8") as f:
            json.dump(df_resultados, f, ensure_ascii=False, indent=4)
            print("✓ Guardado 'reporte_banners.json' para el Dashboard Web.")

        # 2. Acumular en el Histórico General (Para analítica semanal/mensual)
        historico = []
        if os.path.exists("historico_banners.json"):
            try:
                with open("historico_banners.json", "r", encoding="utf-8") as f:
                    historico = json.load(f)
            except Exception:
                historico = []
        
        historico.extend(df_resultados)
        
        with open("historico_banners.json", "w", encoding="utf-8") as f:
            json.dump(historico, f, ensure_ascii=False, indent=4)
            print("✓ Histórico actualizado en 'historico_banners.json'.")

        # 3. Exportar a Excel del día
        if df_resultados:
            pd.DataFrame(df_resultados).to_excel("reporte_banners_diario.xlsx", index=False)
            print(f"\n¡Éxito! Se detectaron {len(df_resultados)} banners activos hoy.")
        else:
            print("\nMonitoreo finalizado: No se detectaron banners de estas marcas hoy.")

if __name__ == "__main__":
    asyncio.run(monitorear_banners())
