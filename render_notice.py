from PIL import Image, ImageDraw, ImageFont

S = 2  # supersample scale
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def f(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size * S)


def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


W = 560
CARD_X0, CARD_X1 = 50, 510
PAD = 28
BODY_W = (CARD_X1 - CARD_X0) - 2 * PAD

tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
lead_f, body_f, hi_f, terms_f, sign_f, head_f, foot_f = (
    f(15, True), f(15), f(14), f(13), f(14), f(15, True), f(11))

lead = wrap(tmp, "We've observed that this account is being used on multiple devices.", lead_f, BODY_W * S)
para = wrap(tmp, "All devices have now been logged out.", body_f, BODY_W * S)
hi = wrap(tmp, "Please reconnect using one device only, and do not sign in from multiple devices at the same time.", hi_f, (BODY_W - 32) * S)

LINE = 25  # line height 1x
HEADER_H = 60
y = HEADER_H + PAD
y += len(lead) * LINE + 16
y += len(para) * LINE + 16
hi_box_h = len(hi) * 22 + 24
y += hi_box_h + 16
y += 22  # terms
y += 24 + 18  # signoff margin + border padding
y += 22 + 20  # name + role
y += PAD
FOOTER_H = 42
card_h = y + FOOTER_H
H = card_h + 100

img = Image.new("RGB", (W * S, H * S), "#eef1f5")
d = ImageDraw.Draw(img)


def card_y(v):
    return (50 + v) * S


r = 14 * S
cx0, cx1 = CARD_X0 * S, CARD_X1 * S
cy0, cy1 = 50 * S, (50 + card_h) * S
# white card
d.rounded_rectangle([cx0, cy0, cx1, cy1], radius=r, fill="#ffffff")
# header (blue, rounded top)
d.rounded_rectangle([cx0, cy0, cx1, cy0 + HEADER_H * S], radius=r, fill="#2563eb")
d.rectangle([cx0, cy0 + HEADER_H * S - r, cx1, cy0 + HEADER_H * S], fill="#2563eb")

# bell icon
bx, by = (CARD_X0 + PAD) * S, card_y(30)
br = 9 * S
d.pieslice([bx - br, by - br, bx + br, by + br], 180, 360, fill="#ffffff")
d.rectangle([bx - br, by, bx + br, by + 2 * S], fill="#ffffff")
d.ellipse([bx - 3 * S, by + 2 * S, bx + 3 * S, by + 8 * S], fill="#ffffff")
d.ellipse([bx - 2 * S, by - br - 4 * S, bx + 2 * S, by - br], fill="#ffffff")
d.text(((CARD_X0 + PAD + 26) * S, card_y(21)), "ACCOUNT NOTICE", font=head_f, fill="#ffffff")

tx = (CARD_X0 + PAD) * S
y = HEADER_H + PAD
for ln in lead:
    d.text((tx, card_y(y)), ln, font=lead_f, fill="#1f2937")
    y += LINE
y += 16
for ln in para:
    d.text((tx, card_y(y)), ln, font=body_f, fill="#1f2937")
    y += LINE
y += 16

# highlight box
hb0, hb1 = card_y(y), card_y(y + hi_box_h)
d.rounded_rectangle([tx, hb0, cx1 - PAD * S, hb1], radius=6 * S, fill="#fef3c7")
d.rectangle([tx, hb0, tx + 4 * S, hb1], fill="#f59e0b")
hy = y + 12
for ln in hi:
    d.text((tx + 16 * S, card_y(hy)), ln, font=hi_f, fill="#92400e")
    hy += 22
y += hi_box_h + 16

d.text((tx, card_y(y)), "Kindly follow the terms and conditions.", font=terms_f, fill="#6b7280")
y += 22 + 24

# signoff divider
d.line([tx, card_y(y), cx1 - PAD * S, card_y(y)], fill="#e5e7eb", width=S)
y += 18
d.text((tx, card_y(y)), "— [Your name]", font=sign_f, fill="#111827")
y += 22
d.text((tx, card_y(y)), "Account owner", font=sign_f, fill="#374151")
y += 20 + PAD

# footer bar
fy0 = card_y(y)
d.rounded_rectangle([cx0, fy0, cx1, cy1], radius=r, fill="#f9fafb")
d.rectangle([cx0, fy0, cx1, fy0 + r], fill="#f9fafb")
foot = "This is a personal notice from the account owner."
fw = d.textlength(foot, font=foot_f)
d.text(((cx0 + cx1) / 2 - fw / 2, fy0 + 15 * S), foot, font=foot_f, fill="#9ca3af")

img = img.resize((W, H), Image.LANCZOS)
img.save("/home/user/faheem/account-notice.png")
print("saved", img.size)
