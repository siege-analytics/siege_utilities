"""Regression tests for issue #2000.

``ReportGenerator`` embedded PIL images passed to ``add_chart_section`` as
full-resolution lossless PNG. The ``width``/``height`` arguments only scale
the *displayed* box, so every source pixel was stored, and photographs were
re-encoded losslessly: the PDF came out ~8-10x larger than the inputs.

PIL images are now downsampled to the display box at the embed DPI. Images
with transparency, and colour images with at most 256 colours in the original
(including every bilevel and palette image), stay lossless PNG. Any other
image is stored as JPEG only when the JPEG is at most a third of the size of
the lossless PNG of the same pixels, which keeps charts, diagrams and
screenshots lossless while photographs (colour or greyscale) become JPEG.
"""

import io

import pytest

pytest.importorskip("reportlab")
PIL_Image = pytest.importorskip("PIL.Image")
np = pytest.importorskip("numpy")
PyPDF2 = pytest.importorskip("PyPDF2")

from siege_utilities import ReportGenerator

DISPLAY_W_IN, DISPLAY_H_IN = 6, 4  # _process_chart_list defaults
EMBED_DPI = 200


def _photo(size=(1600, 1200), seed=0):
    """A deterministic photo-like image: smooth gradients plus sensor noise."""
    w, h = size
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    base = np.stack([
        128 + 100 * np.sin(xx / 97.0) * np.cos(yy / 131.0),
        128 + 90 * np.cos(xx / 53.0 + yy / 211.0),
        128 + 80 * np.sin((xx + yy) / 173.0),
    ], axis=-1)
    noisy = base + rng.normal(0, 12, size=base.shape)
    return PIL_Image.fromarray(np.clip(noisy, 0, 255).astype(np.uint8), "RGB")


def _png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return len(buf.getvalue())


def _render(tmp_path, images):
    rg = ReportGenerator(client_name="Demo", output_dir=tmp_path)
    doc = rg.create_comprehensive_report(title="Photos", report_type="field",
                                         table_of_contents=False)
    for i, img in enumerate(images):
        rg.add_chart_section(doc, f"Site photo {i}", [img], layout="vertical")
    out = tmp_path / "photos.pdf"
    rg.generate_pdf_report(doc, str(out))
    return out


def _image_xobjects(pdf_path):
    """Yield (filter, width, height, has_smask) for every image in the PDF."""
    reader = PyPDF2.PdfReader(str(pdf_path))
    found = []
    for page in reader.pages:
        resources = page.get("/Resources") or {}
        xobjects = resources.get("/XObject") or {}
        for ref in xobjects.values():
            obj = ref.get_object()
            if obj.get("/Subtype") != "/Image":
                continue
            filt = obj.get("/Filter")
            if isinstance(filt, list):
                filt = list(filt)
            else:
                filt = [filt]
            found.append((filt, int(obj["/Width"]), int(obj["/Height"]),
                          "/SMask" in obj))
    return found


def test_photo_heavy_report_is_not_bloated(tmp_path):
    """The issue's scenario: several ~1600px photos, one per section."""
    photos = [_photo(seed=i) for i in range(3)]
    full_res_png = sum(_png_bytes(p) for p in photos)

    out = _render(tmp_path, photos)
    pdf_bytes = out.stat().st_size

    # Pre-fix the PDF carried the full-resolution lossless PNG pixels, so it
    # was at least as large as the PNGs. Downsampled JPEG is far smaller.
    assert pdf_bytes < full_res_png / 4, (pdf_bytes, full_res_png)


def test_photo_is_jpeg_and_downsampled_to_display_box(tmp_path):
    out = _render(tmp_path, [_photo(size=(4000, 3000))])
    images = _image_xobjects(out)
    assert len(images) == 1
    filters, w, h, _ = images[0]
    assert "/DCTDecode" in filters
    # Uniform downsample (aspect preserved) to the smallest size that still
    # covers the 6x4in box at the embed DPI in both directions:
    # scale = max(1200/4000, 800/3000) = 0.3 -> 1200 x 900.
    assert (w, h) == (1200, 900)


def test_small_image_is_not_upsampled(tmp_path):
    out = _render(tmp_path, [_photo(size=(300, 200))])
    (filters, w, h, _), = _image_xobjects(out)
    assert (w, h) == (300, 200)


def test_alpha_image_stays_lossless_with_transparency(tmp_path):
    rgba = _photo(size=(2000, 1500)).convert("RGBA")
    alpha = PIL_Image.new("L", rgba.size, 0)
    alpha.paste(255, (100, 100, 1900, 1400))
    rgba.putalpha(alpha)

    out = _render(tmp_path, [rgba])
    (filters, w, h, has_smask), = _image_xobjects(out)
    assert "/DCTDecode" not in filters
    assert has_smask, "transparency must be preserved"
    assert w <= DISPLAY_W_IN * EMBED_DPI + 1  # still downsampled


def test_flat_colour_image_stays_lossless(tmp_path):
    flat = PIL_Image.new("RGB", (2400, 1600), "white")
    flat.paste((19, 41, 61), (0, 0, 1200, 800))
    flat.paste((200, 30, 30), (1200, 800, 2400, 1600))

    out = _render(tmp_path, [flat])
    (filters, w, h, _), = _image_xobjects(out)
    assert "/DCTDecode" not in filters
    assert w <= DISPLAY_W_IN * EMBED_DPI + 1


def test_callers_image_is_not_modified(tmp_path):
    photo = _photo(size=(2000, 1500))
    before = (photo.size, photo.mode, photo.tobytes()[:64])
    _render(tmp_path, [photo])
    assert (photo.size, photo.mode, photo.tobytes()[:64]) == before


@pytest.mark.parametrize("mode", ["L", "CMYK", "P"])
def test_other_modes_embed(tmp_path, mode):
    img = _photo(size=(1800, 1200)).convert(mode)
    out = _render(tmp_path, [img])
    (filters, w, h, _), = _image_xobjects(out)
    assert w <= DISPLAY_W_IN * EMBED_DPI + 1


# --- pixel-level checks ------------------------------------------------------

def _embedded_pixels(pdf_path):
    """[(filters, PIL image)] for every image XObject, decoded from the PDF."""
    reader = PyPDF2.PdfReader(str(pdf_path))
    found = []
    for page in reader.pages:
        xobjects = (page.get("/Resources") or {}).get("/XObject") or {}
        for ref in xobjects.values():
            obj = ref.get_object()
            if obj.get("/Subtype") != "/Image":
                continue
            filt = obj.get("/Filter")
            filt = [str(f) for f in filt] if isinstance(filt, list) else [str(filt)]
            w, h = int(obj["/Width"]), int(obj["/Height"])
            data = obj.get_data()
            if "/DCTDecode" in filt:
                pil = PIL_Image.open(io.BytesIO(data))
                pil.load()
            else:
                mode = {"/DeviceRGB": "RGB", "/DeviceGray": "L"}[str(obj["/ColorSpace"])]
                pil = PIL_Image.frombytes(mode, (w, h), data)
            found.append((filt, pil))
    return found


def _line_art(mode, size=(2550, 3300), step=37):
    """A scan-like page: white with 1-px black vertical rules every ``step`` px."""
    from PIL import ImageDraw
    img = PIL_Image.new("L", size, 255)
    draw = ImageDraw.Draw(img)
    xs = list(range(40, size[0] - 40, step))
    for x in xs:
        draw.line([(x, 40), (x, size[1] - 40)], fill=0, width=1)
    return img.convert(mode), xs


@pytest.mark.parametrize("mode", ["1", "P", "L", "RGB"])
def test_thin_lines_survive_downsampling(tmp_path, mode):
    """Bilevel and palette images are resampled smoothly, not decimated."""
    img, xs = _line_art(mode)
    out = _render(tmp_path, [img])
    (filt, pil), = _embedded_pixels(out)
    grey = np.asarray(pil.convert("L"), dtype=np.float64)
    w, h = pil.size
    scale = w / img.size[0]
    middle = grey[h // 2 - 5: h // 2 + 5, :]
    survived = sum(1 for x in xs
                   if middle[:, max(0, int(x * scale) - 1): int(x * scale) + 3].min() < 235)
    assert survived == len(xs)


def _matplotlib_chart():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 4), dpi=200)
    x = np.linspace(0, 10, 200)
    for k, colour in enumerate(["tab:blue", "tab:red", "tab:green", "tab:orange"]):
        ax.plot(x, np.sin(x + k) * (k + 1), color=colour, linewidth=1.0, label=f"Series {k}")
    ax.set_title("Weekly sessions by channel")
    ax.grid(True, linewidth=0.4)
    ax.legend(fontsize=6)
    fig.canvas.draw()
    rgba = np.asarray(fig.canvas.buffer_rgba())
    plt.close(fig)
    return PIL_Image.fromarray(rgba, "RGBA").convert("RGB")


def _screenshot(size=(1440, 900)):
    """UI-like RGB image: antialiased text and thin rules on a light gradient."""
    from PIL import ImageDraw, ImageFont
    w, h = size
    shade = np.linspace(244, 250, h, dtype=np.float32)[:, None]
    arr = np.repeat(np.repeat(shade, w, axis=1)[:, :, None], 3, axis=2).astype(np.uint8)
    img = PIL_Image.fromarray(arr, "RGB")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=14)
    for row in range(40):
        y = 20 + row * 22
        draw.text((24, y), f"Row {row:02d}  sessions 12,34{row}  bounce 41.{row}%",
                  fill=(30, 30, 30), font=font)
        draw.line([(20, y + 19), (w - 20, y + 19)], fill=(205, 60, 60), width=1)
    return img


def _flat_diagram(size=(2400, 1600)):
    from PIL import ImageDraw
    img = PIL_Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)
    rng = np.random.RandomState(3)
    for i in range(12):
        colour = tuple(int(v) for v in rng.randint(0, 255, 3))
        x0 = 100 + i * 185
        draw.rectangle([x0, size[1] - 150 - (i + 2) * 95, x0 + 140, size[1] - 150], fill=colour)
    return img


def test_rgb_chart_with_thousands_of_colours_stays_lossless(tmp_path):
    chart = _matplotlib_chart()  # 1200 x 800: no resize, > 256 colours
    assert chart.getcolors(maxcolors=256) is None
    out = _render(tmp_path, [chart])
    (filt, pil), = _embedded_pixels(out)
    assert "/DCTDecode" not in filt
    assert np.array_equal(np.asarray(pil.convert("RGB")), np.asarray(chart))


def test_screenshot_stays_lossless(tmp_path):
    shot = _screenshot()
    out = _render(tmp_path, [shot])
    (filt, pil), = _embedded_pixels(out)
    assert "/DCTDecode" not in filt
    reference = shot.resize(pil.size, PIL_Image.Resampling.LANCZOS)
    assert np.array_equal(np.asarray(pil.convert("RGB")), np.asarray(reference))


def test_flat_diagram_larger_than_box_is_classified_before_resizing(tmp_path):
    """14 colours in the original; resampling adds hundreds, but it stays PNG."""
    diagram = _flat_diagram()
    assert diagram.getcolors(maxcolors=256) is not None
    out = _render(tmp_path, [diagram])
    (filt, pil), = _embedded_pixels(out)
    assert "/DCTDecode" not in filt
    assert pil.size == (1200, 800)


def test_greyscale_photo_follows_the_size_rule(tmp_path):
    grey = _photo((1600, 1200), seed=2).convert("L")
    out = _render(tmp_path, [grey])
    (filt, pil), = _embedded_pixels(out)
    assert "/DCTDecode" in filt
    assert pil.mode == "L"


@pytest.mark.parametrize("make,expect_jpeg", [
    (lambda: _photo((1600, 1200), seed=7), True),
    (lambda: _photo((1600, 1200), seed=7).convert("L"), True),
    (_matplotlib_chart, False),
    (_screenshot, False),
], ids=["colour-photo", "grey-photo", "chart", "screenshot"])
def test_jpeg_only_when_at_most_a_third_of_the_png(make, expect_jpeg):
    """Both sides of the size rule, measured directly on the encoder."""
    image = make()
    buf = ReportGenerator._encode_pil_image(image, 6, 4, 200, 85)
    data = buf.getvalue()
    is_jpeg = data[:2] == b"\xff\xd8"
    assert is_jpeg is expect_jpeg
    if not is_jpeg:
        return
    # The JPEG it chose is at most a third of a lossless PNG of the same pixels.
    decoded = PIL_Image.open(io.BytesIO(data))
    target = image.resize(decoded.size, PIL_Image.Resampling.LANCZOS)
    lossless = io.BytesIO()
    target.save(lossless, format="PNG")
    assert len(data) <= len(lossless.getvalue()) / 3


def test_palette_logo_with_transparency_keeps_its_lines(tmp_path):
    """A GIF/PNG-8 style logo larger than the box: lines must not break up."""
    from PIL import ImageDraw
    big = PIL_Image.new("RGBA", (2400, 1600), (0, 0, 0, 0))
    draw = ImageDraw.Draw(big)
    for k in range(60):
        draw.line([(100 + k * 38, 100), (300 + k * 38, 1500)], fill=(19, 41, 61, 255), width=1)
    buf = io.BytesIO()
    big.save(buf, "GIF")
    buf.seek(0)
    gif = PIL_Image.open(buf)
    gif.load()
    assert gif.mode == "P" and "transparency" in gif.info
    out = _render(tmp_path, [gif])
    (filters, w, h, has_smask), = _image_xobjects(out)
    assert has_smask
    (filt, pil), = _embedded_pixels(out)
    arr = np.asarray(pil.convert("L"), dtype=np.int16)
    background = np.bincount(arr.astype(np.int64).ravel()).argmax()
    rows = arr[int(h * 0.2): int(h * 0.8)] != background
    starts = (rows[:, 1:] & ~rows[:, :-1]).sum(axis=1)
    assert starts.min() >= 55  # 60 lines drawn; none broken into gaps


@pytest.mark.parametrize("size", [(0, 0), (0, 10), (10, 0)])
def test_empty_image_is_skipped_not_fatal(tmp_path, size, caplog):
    import logging
    caplog.set_level(logging.ERROR)
    out = _render(tmp_path, [_photo((300, 200)), PIL_Image.new("RGB", size)])
    assert len(_image_xobjects(out)) == 1
    assert any("cannot embed an empty image" in r.getMessage() for r in caplog.records)


def test_16_bit_greyscale_is_scaled_to_8_bits(tmp_path):
    base = _photo((1800, 1200), seed=5).convert("L")
    sixteen = PIL_Image.fromarray(np.asarray(base, dtype=np.uint16) * 257)
    assert sixteen.mode == "I;16"
    out = _render(tmp_path, [sixteen])
    (filt, pil), = _embedded_pixels(out)
    reference = base.resize(pil.size, PIL_Image.Resampling.LANCZOS)
    mean_error = np.abs(np.asarray(pil.convert("L"), dtype=np.float64)
                        - np.asarray(reference, dtype=np.float64)).mean()
    assert mean_error < 5


def test_large_pa_image_keeps_its_colours(tmp_path):
    pa = (_photo((1800, 1200), seed=5)
          .convert("P", palette=PIL_Image.Palette.ADAPTIVE, colors=256).convert("PA"))
    out = _render(tmp_path, [pa])
    (filt, pil), = _embedded_pixels(out)
    reference = pa.convert("RGB").resize(pil.size, PIL_Image.Resampling.LANCZOS)
    mean_error = np.abs(np.asarray(pil.convert("RGB"), dtype=np.float64)
                        - np.asarray(reference, dtype=np.float64)).mean()
    assert mean_error < 5


class _ImageLike:
    """Only ``save`` and ``mode``: embedded as before, without resizing."""

    def __init__(self, image):
        self._image = image
        self.mode = image.mode

    def save(self, fp, format=None, **kwargs):
        self._image.save(fp, format=format, **kwargs)


def test_duck_typed_image_is_still_embedded(tmp_path):
    out = _render(tmp_path, [_ImageLike(_photo((300, 200)))])
    (filters, w, h, _), = _image_xobjects(out)
    assert (w, h) == (300, 200)
