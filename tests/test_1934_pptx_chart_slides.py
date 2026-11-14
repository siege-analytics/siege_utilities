"""PowerPoint chart slides never drop a chart or produce an empty slide
silently, show their description, and log only type names and keys for
unexpected items (#1934)."""

import logging

import pytest

pptx = pytest.importorskip("pptx")
PILImage = pytest.importorskip("PIL.Image")

from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Inches

from siege_utilities.reporting.powerpoint_generator import PowerPointGenerator

LOGGER = "siege_utilities.reporting.powerpoint_generator"


@pytest.fixture
def generator(tmp_path):
    return PowerPointGenerator("Charts", output_dir=tmp_path)


@pytest.fixture
def make_png(tmp_path):
    def make(name):
        path = tmp_path / f"{name}.png"
        PILImage.new("RGB", (24, 16), (160, 90, 30)).save(path)
        return str(path)
    return make


def _deck(generator):
    return generator.create_comprehensive_presentation(
        "Deck", sections=[], include_toc=False, include_agenda=False,
    )


def _slides(generator, content, tmp_path):
    output = generator.generate_powerpoint_presentation(content, str(tmp_path / "deck.pptx"))
    return list(pptx.Presentation(str(output)).slides)


def _slide_titled(slides, title):
    return next(slide for slide in slides if slide.shapes.title is not None and slide.shapes.title.text == title)


def _titles(slides):
    return [slide.shapes.title.text for slide in slides if slide.shapes.title is not None]


def _pictures(slide):
    return [shape for shape in slide.shapes if shape.shape_type == MSO_SHAPE_TYPE.PICTURE]


def _text(slide):
    return "\n".join(shape.text_frame.text for shape in slide.shapes if shape.has_text_frame)


def _warnings(caplog):
    return [record.getMessage() for record in caplog.records if record.name == LOGGER and record.levelno == logging.WARNING]


def test_single_chart_default_output_is_unchanged(generator, make_png, tmp_path):
    content = _deck(generator)
    generator.add_chart_slide(content, "One chart", [make_png("one")])

    slides = _slides(generator, content, tmp_path)
    slide = _slide_titled(slides, "One chart")

    assert slide.slide_layout.name == "Title and Content"
    (picture,) = _pictures(slide)
    assert (picture.left, picture.top, picture.width, picture.height) == (Inches(1), Inches(2), Inches(8), Inches(5))
    assert "One chart (continued)" not in _titles(slides)


EXPECTED_POSITIONS = {
    "two_charts": [(0.5, 2.0, 4.0, 4.0), (5.5, 2.0, 4.0, 4.0)],
    "grid": [(0.5, 2.0, 3.5, 2.5), (4.5, 2.0, 3.5, 2.5), (0.5, 4.8, 3.5, 2.5), (4.5, 4.8, 3.5, 2.5)],
}


@pytest.mark.parametrize("layout, count", [("two_charts", 2), ("two_charts", 1), ("grid", 4), ("grid", 3)])
def test_charts_take_the_layout_positions_in_order(generator, make_png, tmp_path, layout, count):
    content = _deck(generator)
    generator.add_chart_slide(content, "Placed", [make_png(f"c{i}") for i in range(count)], layout=layout)

    slide = _slide_titled(_slides(generator, content, tmp_path), "Placed")
    placed = sorted((p.left, p.top, p.width, p.height) for p in _pictures(slide))

    expected = sorted(
        (Inches(left), Inches(top), Inches(width), Inches(height))
        for left, top, width, height in EXPECTED_POSITIONS[layout][:count]
    )
    assert placed == expected


def test_none_under_charts_warns_and_keeps_the_title_slide(generator, tmp_path, caplog):
    content = _deck(generator)
    content["sections"].append({
        "type": "chart_slide", "title": "No chart list", "level": 1,
        "content": {"charts": None, "description": "", "layout": "single_chart"},
    })

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        slide = _slide_titled(_slides(generator, content, tmp_path), "No chart list")

    assert _pictures(slide) == []
    assert any("No chart list" in message and "no charts" in message for message in _warnings(caplog))


@pytest.mark.parametrize("charts, type_name", [
    ("chart.png", "str"),
    (b"chart.png", "bytes"),
    ({"image_path": "chart.png"}, "dict"),
])
def test_charts_that_are_not_a_list_are_rejected_when_the_slide_is_added(generator, charts, type_name):
    with pytest.raises(ValueError, match=f"'Not a list'.*{type_name}"):
        generator.add_chart_slide(_deck(generator), "Not a list", charts)


def test_charts_that_are_not_a_list_in_a_built_section_raise_when_generating(generator, tmp_path):
    content = _deck(generator)
    content["sections"].append({
        "type": "chart_slide", "title": "Bare string", "level": 1,
        "content": {"charts": "chart.png", "description": "", "layout": "single_chart"},
    })

    # Slide-building ValueErrors reach the caller as RuntimeError, keeping the message.
    with pytest.raises(RuntimeError, match="'Bare string'.*str"):
        generator.generate_powerpoint_presentation(content, str(tmp_path / "deck.pptx"))


def test_charts_given_as_a_tuple_are_placed(generator, make_png, tmp_path):
    content = _deck(generator)
    generator.add_chart_slide(content, "Tuple", (make_png("a"), make_png("b")), layout="two_charts")

    assert len(_pictures(_slide_titled(_slides(generator, content, tmp_path), "Tuple"))) == 2


def test_non_string_layout_raises_value_error(generator, make_png):
    with pytest.raises(ValueError, match="Unknown chart slide layout"):
        generator.add_chart_slide(_deck(generator), "List layout", [make_png("a")], layout=["grid"])


def test_two_charts_with_one_chart_shows_the_chart_and_description(generator, make_png, tmp_path):
    content = _deck(generator)
    generator.add_chart_slide(content, "Half full", [make_png("one")], description="Sessions by channel",
                              layout="two_charts")

    slide = _slide_titled(_slides(generator, content, tmp_path), "Half full")

    assert len(_pictures(slide)) == 1
    assert "Sessions by channel" in _text(slide)


@pytest.mark.parametrize("count", [1, 2, 3])
def test_grid_places_every_chart_it_is_given(generator, make_png, tmp_path, count):
    content = _deck(generator)
    generator.add_chart_slide(content, "Grid", [make_png(f"c{i}") for i in range(count)], layout="grid")

    slides = _slides(generator, content, tmp_path)

    assert len(_pictures(_slide_titled(slides, "Grid"))) == count
    assert "Grid (continued)" not in _titles(slides)


@pytest.mark.parametrize("layout, count, first, rest", [
    ("single_chart", 2, 1, [1]),
    ("single_chart", 3, 1, [1, 1]),
    ("two_charts", 3, 2, [1]),
    ("grid", 5, 4, [1]),
    ("grid", 9, 4, [4, 1]),
])
def test_extra_charts_continue_on_further_slides(generator, make_png, tmp_path, layout, count, first, rest):
    content = _deck(generator)
    generator.add_chart_slide(content, "Many", [make_png(f"c{i}") for i in range(count)], layout=layout)

    slides = _slides(generator, content, tmp_path)
    continued = [slide for slide in slides if slide.shapes.title.text == "Many (continued)"]

    assert len(_pictures(_slide_titled(slides, "Many"))) == first
    assert [len(_pictures(slide)) for slide in continued] == rest


def test_chart_slide_speaker_notes_go_on_the_first_slide(generator, make_png, tmp_path):
    content = _deck(generator)
    generator.add_chart_slide(content, "Noted", [make_png("a"), make_png("b")])
    content["sections"][-1]["notes"] = "Explain the trend"

    slides = _slides(generator, content, tmp_path)

    assert _slide_titled(slides, "Noted").notes_slide.notes_text_frame.text == "Explain the trend"


def test_unknown_layout_is_rejected_when_the_slide_is_added(generator, make_png):
    content = _deck(generator)

    with pytest.raises(ValueError, match="'three_up'") as raised:
        generator.add_chart_slide(content, "Bad layout", [make_png("a")], layout="three_up")
    for valid in ("single_chart", "two_charts", "grid"):
        assert valid in str(raised.value)


def test_unknown_layout_in_a_built_section_raises_when_generating(generator, make_png, tmp_path):
    content = _deck(generator)
    content["sections"].append({
        "type": "chart_slide", "title": "Hand built", "level": 1,
        "content": {"charts": [make_png("a")], "description": "", "layout": "three_up"},
    })

    # Slide-building ValueErrors reach the caller as RuntimeError, keeping the message.
    with pytest.raises(RuntimeError, match="'three_up'"):
        generator.generate_powerpoint_presentation(content, str(tmp_path / "deck.pptx"))


def test_chart_slide_without_charts_warns(generator, tmp_path, caplog):
    content = _deck(generator)
    generator.add_chart_slide(content, "Empty charts", [])

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        _slides(generator, content, tmp_path)

    assert any("Empty charts" in message and "no charts" in message for message in _warnings(caplog))


@pytest.mark.parametrize("key", ["image_path", "path"])
@pytest.mark.parametrize("value", [None, ""])
def test_described_chart_with_an_empty_image_key_warns(generator, tmp_path, caplog, key, value):
    content = _deck(generator)
    generator.add_chart_slide(content, "Lost image", [{"title": "Revenue", key: value}])

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        slide = _slide_titled(_slides(generator, content, tmp_path), "Lost image")

    assert "[Chart: Revenue]" in _text(slide)
    # The warning lists the mapping's keys, quoted, so 'path' is not matched
    # by 'image_path'.
    assert any("Lost image" in message and f"'{key}'" in message for message in _warnings(caplog))


def test_warning_for_an_unknown_mapping_names_its_keys_not_its_values(generator, tmp_path, caplog):
    content = _deck(generator)
    generator.add_chart_slide(content, "Odd mapping", [{"token": "s3cr3t-value", "size": 4}])

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        _slides(generator, content, tmp_path)

    warnings = [message for message in _warnings(caplog) if "Odd mapping" in message]
    assert warnings
    assert all("s3cr3t-value" not in message for message in warnings)
    assert any("['size', 'token']" in message for message in warnings)


def test_warning_for_an_unknown_object_names_its_type_not_its_repr(generator, tmp_path, caplog):
    class Opaque:
        def __repr__(self):
            return "<opaque holding s3cr3t-value>"

    content = _deck(generator)
    generator.add_chart_slide(content, "Odd object", [Opaque()])

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        _slides(generator, content, tmp_path)

    warnings = [message for message in _warnings(caplog) if "Odd object" in message]
    assert warnings
    assert all("s3cr3t-value" not in message for message in warnings)
    assert any("Opaque" in message for message in warnings)


def test_warning_for_an_image_object_without_data_names_its_type_not_its_repr(generator, tmp_path, caplog):
    class ImageWithoutData:
        filename = "drawn-elsewhere"

        def __repr__(self):
            return "<image holding s3cr3t-value>"

    content = _deck(generator)
    generator.add_chart_slide(content, "No data", [ImageWithoutData()])

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        _slides(generator, content, tmp_path)

    warnings = [message for message in _warnings(caplog) if "No data" in message]
    assert warnings
    assert all("s3cr3t-value" not in message for message in warnings)
    assert any("ImageWithoutData" in message for message in warnings)


def test_missing_image_path_is_still_named(generator, tmp_path, caplog):
    missing = str(tmp_path / "gone.png")
    content = _deck(generator)
    generator.add_chart_slide(content, "Missing", [missing])

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        _slides(generator, content, tmp_path)

    assert any(missing in message and "Missing" in message for message in _warnings(caplog))
