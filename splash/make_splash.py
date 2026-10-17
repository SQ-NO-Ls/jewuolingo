"""Generate the iOS launch screens (apple-touch-startup-image) in splash/.

    python3 -I splash/make_splash.py <FrankRuhlLibre[wght].ttf>

The TTF is only a build input (github.com/google/fonts, ofl/frankruhllibre);
PIL cannot read the woff2 files in fonts/. The mark is the header wordmark:
"Jewolingo" in Frank Ruhl Libre 900, --text2 on --bg, so the launch screen
hands over to the app's own header without a flash of the accent fill.
Each size needs a matching <link> in index.html's <head>.
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

BG = (0x0E, 0x0F, 0x14)      # --bg
INK = (0xA6, 0xA8, 0xB3)     # --text2
TEXT, PX, TRACK = 'Jewolingo', 28, -0.67   # CSS px; header is 21px / -.5px

# (width, height, device-pixel-ratio) in physical pixels, portrait.
SIZES = [(1125, 2436, 3), (1170, 2532, 3), (1179, 2556, 3), (1284, 2778, 3),
         (1290, 2796, 3), (1242, 2688, 3), (828, 1792, 2),
         (1206, 2622, 3), (1320, 2868, 3), (1260, 2736, 3),   # 16 Pro/17, Pro Max, Air
         (750, 1334, 2), (1080, 2340, 3)]                       # SE, mini

def make(ttf, w, h, dpr):
    im = Image.new('RGB', (w, h), BG)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(ttf, PX * dpr)
    f.set_variation_by_axes([900])
    xs = [f.getlength(TEXT[:i]) + i * TRACK * dpr for i in range(len(TEXT))]
    width = xs[-1] + f.getlength(TEXT[-1])
    top, bottom = f.getbbox(TEXT, anchor='ls')[1::2]
    x0, base = (w - width) / 2, (h - (bottom - top)) / 2 - top
    for ch, x in zip(TEXT, xs):
        d.text((x0 + x, base), ch, font=f, fill=INK, anchor='ls')
    return im.quantize(colors=32, method=Image.Quantize.MEDIANCUT)

if __name__ == '__main__':
    out = os.path.dirname(os.path.abspath(__file__))
    for w, h, dpr in SIZES:
        p = os.path.join(out, '%dx%d.png' % (w, h))
        make(sys.argv[1], w, h, dpr).save(p, optimize=True)
        print(p, os.path.getsize(p))
