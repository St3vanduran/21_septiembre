#!/usr/bin/env python3
"""Prepara la galería de flores amarillas.

Qué hace
  1. Lee las fotos originales de IMG/ (NO las modifica: se publican tal cual,
     así se conserva la calidad máxima).
  2. Crea versiones ligeras en miniaturas/ (900 px y 1800 px de lado mayor)
     que solo se usan para que la cuadrícula cargue rápido. Al tocar una foto,
     la página abre el ORIGINAL completo.
  3. Genera og.jpg (la vista previa que aparece al compartir el enlace).
  4. Reescribe la galería dentro de index.html y valeria.html (entre GALERIA:INICIO y FIN).

Para añadir fotos nuevas: cópialas a IMG/ y ejecuta de nuevo
    python herramientas/generar_galeria.py
Las que no estén en la lista FOTOS se agregan al final.

Requiere Pillow:  pip install pillow
"""
import base64
import html
import io
import re
import sys
from pathlib import Path

from PIL import Image, ImageOps

RAIZ = Path(__file__).resolve().parent.parent
IMG = RAIZ / "IMG"
MINI = RAIZ / "miniaturas"
PAGINAS = [RAIZ / "index.html", RAIZ / "valeria.html"]   # páginas cuya galería se mantiene al día
OG = RAIZ / "og.jpg"

LADOS = (900, 1800)          # lado mayor (px) de cada versión ligera
CALIDAD = {900: 86, 1800: 88}
EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp"}

# Orden de aparición y texto alternativo (para lectores de pantalla).
# Cada tupla: (archivo, descripción)
FOTOS = [
    ("20171122_0.jpg", "Mariposa monarca posada entre rudbeckias amarillas de centro oscuro"),
    ("20171122_0903121.jpg", "Caléndula naranja con gotas de rocío"),
    ("20171122_0903127.jpg", "Girasol de pétalos dorados y centro oscuro"),
    ("20171122_090.jpg", "Lirios amarillos y sus botones sobre un fondo oscuro"),
    ("20171012_112511.jpg", "Diente de león abierto sobre el pasto"),
    ("20171122_0903123.jpg", "Rosa de tono amarillo anaranjado entre hojas brillantes"),
    ("20171122_09.jpg", "Flor amarilla de pétalos redondeados y centro naranja sobre un fondo verde"),
    ("20171122_09031255.jpg", "Flor amarilla esponjosa, como un pompón, entre hojas oscuras"),
    ("20171122_09031222.jpg", "Racimo de rudbeckias amarillas de centro negro entre hojas verdes"),
    ("20171122_0903126.jpg", "Flor amarilla brillante entre hojas verdes"),
    ("20171122_090314.jpg", "Racimo de flores amarillas tipo margarita"),
    ("20171122_090312.jpg", "Flor amarilla grande sobre un fondo negro"),
    ("20171122_090318.jpg", "Flores doradas de muchos pétalos con el fondo desenfocado"),
    ("20171122_090312E.jpg", "Flores amarillas entre hojas verdes brillantes"),
    ("20171122_0903.jpg", "Flor amarilla de pétalos finos en lo alto de un tallo"),
    ("20171122.jpg", "Flores naranjas de centro negro y pétalos largos y delgados"),
    ("2022-07-31-120458677.jpg", "Flor amarilla de centro texturizado y pétalos anchos"),
    ("IMG_20220605_125111-01.jpeg", "Racimo de flores amarillo anaranjado con fondo oscuro"),
    ("20171122_0903120.jpg", "Pequeñas flores amarillas sobre un fondo verde azulado"),
    ("20171122_0903124.jpg", "Flor amarilla de pétalos alargados entre pasto y hojas"),
    ("20171122_09031211.jpg", "Ramillete de flores amarillas bañadas en luz dorada"),
    ("20171122_090311.jpg", "Flores amarillas de centro café bajo una luz cálida"),
    ("20171122_0903129.jpg", "Florecitas amarillas entre hojas verdes"),
    ("20171122_0903125.jpg", "Flores amarillas entre hojas verdes con fondo suave"),
    ("20171122_090315.jpg", "Flores naranjas de centro oscuro entre hojas verdes oscuras"),
    ("20171122_090317.jpg", "Flores amarillas pequeñas entre hojas oscuras"),
    ("20171122_0903122.jpg", "Margaritas amarillas de pétalos finos sobre un fondo verde grisáceo"),
    ("20171122_091.jpg", "Flor amarilla clara sobre un fondo suave"),
    ("20171122_0903128.JPG", "Flores de amarillo pálido con el fondo desenfocado"),
]

# Vista previa para compartir (WhatsApp, Telegram...): tres franjas de 1200x630.
# (archivo, ancho de la franja, punto de interés (x, y) entre 0 y 1)
OG_FRANJAS = [
    ("20171122_0903121.jpg", 340, (0.50, 0.50)),
    ("20171122_0903127.jpg", 520, (0.50, 0.50)),
    ("20171122_0.jpg", 340, (0.55, 0.42)),
]

# Alturas de fila de la cuadrícula: deben coincidir con --fila en index.html
FILA = {"movil": 210, "medio": 240, "ancho": 280, "xl": 320}


def orientada(ruta):
    """Abre la imagen aplicando la rotación EXIF (algunas fotos vienen de lado)."""
    im = Image.open(ruta)
    icc = im.info.get("icc_profile")
    im = ImageOps.exif_transpose(im)
    if im.mode != "RGB":
        im = im.convert("RGB")
    return im, icc


def redimensionar(im, lado):
    w, h = im.size
    largo = max(w, h)
    if largo <= lado:
        return im
    k = lado / largo
    return im.resize((max(1, round(w * k)), max(1, round(h * k))), Image.LANCZOS)


def guardar_jpg(im, destino, calidad, icc, submuestreo=2):
    kw = dict(quality=calidad, optimize=True, progressive=True, subsampling=submuestreo)
    if icc:
        kw["icc_profile"] = icc
    im.save(destino, "JPEG", **kw)


def lqip(im):
    """Miniatura diminuta (borrosa) incrustada en la página mientras carga la foto."""
    t = im.copy()
    t.thumbnail((24, 24), Image.LANCZOS)
    buf = io.BytesIO()
    t.save(buf, "JPEG", quality=42, optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def color_medio(im):
    r, g, b = im.resize((1, 1), Image.BOX).getpixel((0, 0))
    return f"#{r:02x}{g:02x}{b:02x}"


def sizes_attr(ar):
    """Ancho aproximado con el que se mostrará la foto (ayuda al navegador a elegir la versión)."""
    movil = max(44, min(92, round(ar * 60)))
    f = 1.2  # las filas se estiran un poco para llenar el ancho
    return (
        f"(max-width: 599px) {movil}vw, "
        f"(max-width: 899px) {round(ar * FILA['medio'] * f)}px, "
        f"(max-width: 1299px) {round(ar * FILA['ancho'] * f)}px, "
        f"{round(ar * FILA['xl'] * f)}px"
    )


def hacer_og(forzar):
    if OG.exists() and not forzar:
        return
    ancho_total, alto = 1200, 630
    lienzo = Image.new("RGB", (ancho_total, alto), (11, 31, 24))
    x = 0
    for nombre, ancho, (fx, fy) in OG_FRANJAS:
        im, _ = orientada(IMG / nombre)
        w, h = im.size
        # recorte con la proporción de la franja, centrado en el punto de interés
        cw = min(w, round(h * ancho / alto))
        ch = round(cw * alto / ancho)
        if ch > h:
            ch = h
            cw = round(ch * ancho / alto)
        izq = min(max(round(fx * w - cw / 2), 0), w - cw)
        arr = min(max(round(fy * h - ch / 2), 0), h - ch)
        franja = im.crop((izq, arr, izq + cw, arr + ch)).resize((ancho, alto), Image.LANCZOS)
        lienzo.paste(franja, (x, 0))
        x += ancho
    # WhatsApp descarta previsualizaciones de más de ~300 KB
    for q in (88, 84, 80, 76, 72):
        guardar_jpg(lienzo, OG, q, None)
        if OG.stat().st_size < 290_000:
            break
    print(f"  og.jpg  {OG.stat().st_size / 1024:.0f} KB")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    forzar = "--forzar" in sys.argv
    MINI.mkdir(exist_ok=True)

    nombres = {n for n, _ in FOTOS}
    en_img = {p.name: p for p in IMG.iterdir() if p.suffix.lower() in EXTENSIONES}
    presentes = dict(en_img)
    # Carpetas extra donde buscar originales que no estén en IMG/ (solo lectura):
    #   python herramientas/generar_galeria.py --fuente C:\Users\yo\Pictures
    for i, a in enumerate(sys.argv[:-1]):
        if a == "--fuente":
            for p in Path(sys.argv[i + 1]).iterdir():
                if p.name in nombres and p.name not in presentes:
                    presentes[p.name] = p
    lista = [(n, a) for n, a in FOTOS if n in presentes]
    faltan = [n for n, _ in FOTOS if n not in presentes]
    extras = sorted(n for n in en_img if n not in nombres)
    if faltan:
        print("Faltan originales:", ", ".join(faltan))
        if "--permitir-faltantes" not in sys.argv:
            print("No se modificó ninguna página, para no perder fotos de la galería.")
            print("Pon esos archivos en IMG/, indica su carpeta con --fuente RUTA,")
            print("o usa --permitir-faltantes si de verdad quieres omitirlos.")
            return
    lista += [(n, "Flor amarilla") for n in extras]
    if extras:
        print("Se añaden al final:", ", ".join(extras))

    total = len(lista)
    items = []
    peso_mini = 0
    peso_orig = 0
    for i, (nombre, alt) in enumerate(lista, 1):
        ruta = presentes[nombre]
        stem = ruta.stem
        im, icc = orientada(ruta)
        w, h = im.size
        ar = w / h
        anchos = {}
        for lado in LADOS:
            destino = MINI / f"{stem}-{lado}.jpg"
            v = redimensionar(im, lado)
            anchos[lado] = v.size[0]
            fresco = destino.exists() and destino.stat().st_mtime >= ruta.stat().st_mtime
            if forzar or not fresco:
                # 4:4:4 en la versión grande para no ensuciar los amarillos saturados
                guardar_jpg(v, destino, CALIDAD[lado], icc, 0 if lado == max(LADOS) else 2)
            peso_mini += destino.stat().st_size
        mb = ruta.stat().st_size / 1e6
        peso_orig += ruta.stat().st_size
        eager = i <= 3
        items.append(
            f'      <li class="foto" style="--ar:{ar:.4f};background:{color_medio(im)} '
            f'url(data:image/jpeg;base64,{lqip(im)}) center/cover">\n'
            f'        <a href="IMG/{ruta.name}" data-med="miniaturas/{stem}-{max(LADOS)}.jpg" '
            f'data-w="{w}" data-h="{h}" data-mb="{mb:.2f}">\n'
            f'          <img src="miniaturas/{stem}-{min(LADOS)}.jpg" '
            f'srcset="miniaturas/{stem}-{min(LADOS)}.jpg {anchos[min(LADOS)]}w, '
            f'miniaturas/{stem}-{max(LADOS)}.jpg {anchos[max(LADOS)]}w" '
            f'sizes="{sizes_attr(ar)}" width="{w}" height="{h}" alt="{html.escape(alt, quote=True)}" '
            f'{"fetchpriority=" + chr(34) + "high" + chr(34) if eager else "loading=" + chr(34) + "lazy" + chr(34)} '
            f'decoding="async">\n'
            f'        </a>\n'
            f'      </li>'
        )
        print(f"  {i:2d}/{total} {ruta.name:30s} {w}x{h}  original {mb:5.2f} MB")

    hacer_og(forzar)

    patron = re.compile(r"(<!-- GALERIA:INICIO -->\n).*?(\n\s*<!-- GALERIA:FIN -->)", re.S)
    for pagina in PAGINAS:
        if not pagina.exists():
            continue
        txt = pagina.read_text(encoding="utf-8")
        if patron.search(txt):
            txt = patron.sub(lambda m: m.group(1) + "\n".join(items) + m.group(2), txt)
            txt = re.sub(r"(<span data-total>)\d*(</span>)", rf"\g<1>{total}\g<2>", txt)
            pagina.write_text(txt, encoding="utf-8", newline="\n")
            print(f"{pagina.name} actualizado con {total} fotos")
        else:
            print(f"{pagina.name} no tiene los marcadores GALERIA:INICIO / GALERIA:FIN")
    print(
        f"Originales: {peso_orig / 1e6:.1f} MB  |  miniaturas: {peso_mini / 1e6:.1f} MB  "
        f"|  total publicado ~ {(peso_orig + peso_mini) / 1e6:.1f} MB"
    )


if __name__ == "__main__":
    main()
