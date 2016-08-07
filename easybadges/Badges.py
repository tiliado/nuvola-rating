from PIL import Image, ImageFont, ImageDraw
import math

def Badge(A, B, fh = 14, pw = 6, ph = 4, r = 4, d = 1, color = (0x00, 0x7E, 0xC6), variants=None):
	font = ImageFont.truetype('Data/DejaVuSans.ttf', fh)
	A_size = font.getsize(A)[0]
	if variants:
		B_size = max([font.getsize(v)[0] for v in variants])
	else:
		B_size = font.getsize(B)[0]
	
	s = A_size + 2 * pw
	w = s + B_size + 2 * pw
	h = fh + 2 * ph

	left = (0x58, 0x58, 0x58, 0xFF)
	right = tuple(color) + (0xFF,)

	img = Image.new('RGBA', (w, h))
	px = img.load()

	def mulAlpha(px, i, j, a):
		px[i, j] = (px[i, j][0], px[i, j][1], px[i, j][2], round(px[i, j][3] * a))

	def blendColor(px, i, j, c, f):
		r = round(c[0] * f + px[i, j][0] * (1 - f))
		g = round(c[1] * f + px[i, j][1] * (1 - f))
		b = round(c[2] * f + px[i, j][2] * (1 - f))
		px[i, j] = (r, g, b, px[i, j][3])

	for i in range(s):
		for j in range(h):
			px[i, j] = left

	for i in range(s, w):
		for j in range(h):
			px[i, j] = right

	for i in range(r):
		for j in range(r):
			cx = r - 1
			cy = r - 1
			a = 1 - min(max(math.sqrt((i - cx) ** 2 + (j - cy) ** 2) - r + 1, 0), 1)
			mulAlpha(px, i, j, a)
			mulAlpha(px, w - i - 1, j, a)
			mulAlpha(px, i, h - j - 1, a)
			mulAlpha(px, w - i - 1, h - j - 1, a)

	for i in range(w):
		for j in range(h):
			grad = (
				round(0xB8 * (1 - j / (h - 1))),
				round(0xB8 * (1 - j / (h - 1))),
				round(0xB8 * (1 - j / (h - 1))),
			)
			blendColor(px, i, j, grad, 0.15)

	draw = ImageDraw.Draw(img)
	draw.text((pw, ph), A, font = font, fill = (0x48, 0x48, 0x48, 0xFF))
	draw.text((pw, ph - d), A, font = font, fill = (0xFF, 0xFF, 0xFF, 0xFF))
	draw.text((s + pw, ph), B, font = font, fill = (0x48, 0x48, 0x48, 0xFF))
	draw.text((s + pw, ph - d), B, font = font, fill = (0xFF, 0xFF, 0xFF, 0xFF))
	return img
