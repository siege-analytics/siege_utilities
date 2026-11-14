"""PowerPointGenerator map slides render their maps, missing or unreadable images
are never dropped silently, and the contents and agenda slides list the sections
given up front (#1933)."""

import logging
from pathlib import Path

import pytest

pptx = pytest.importorskip("pptx")
PILImage = pytest.importorskip("PIL.Image")

from pptx.enum.shapes import MSO_SHAPE_TYPE

from siege_utilities.reporting.powerpoint_generator import PowerPointGenerator

LOGGER = "siege_utilities.reporting.powerpoint_generator"


@pytest.fixture
def generator(tmp_path):
    return PowerPointGenerator("Maps", output_dir=tmp_path)


@pytest.fixture
def make_png(tmp_path):
    def make(name):
        path = tmp_path / f"{name}.png"
        PILImage.new("RGB", (24, 16), (30, 90, 160)).save(path)
        return path
    return make


def _deck(generator, include_toc=False, include_agenda=False, sections=None):
    return generator.create_comprehensive_presentation(
        "Deck", sections=sections or [], include_toc=include_toc, include_agenda=include_agenda,
    )


def _slides(generator, content, tmp_path):
    output = generator.generate_powerpoint_presentation(content, str(tmp_path / "deck.pptx"))
    return list(pptx.Presentation(str(output)).slides)


def _slide_titled(slides, title):
    return next(slide for slide in slides if slide.shapes.title is not None and slide.shapes.title.text == title)


def _pictures(slide):
    return [shape for shape in slide.shapes if shape.shape_type == MSO_SHAPE_TYPE.PICTURE]


def _text(slide):
    return "\n".join(shape.text_frame.text for shape in slide.shapes if shape.has_text_frame)


@pytest.mark.parametrize("as_type", [str, Path])
def test_map_slide_contains_its_map_and_description(generator, make_png, tmp_path, as_type):
    content = _deck(generator)
    generator.add_map_slide(content, "Regional map", [as_type(make_png("region"))], description="Population by region")

    slide = _slide_titled(_slides(generator, content, tmp_path), "Regional map")

    assert len(_pictures(slide)) == 1
    assert "Population by region" in _text(slide)


@pytest.mark.parametrize("count", [2, 3, 4])
def test_map_slide_places_up_to_four_maps(generator, make_png, tmp_path, count):
    content = _deck(generator)
    generator.add_map_slide(content, "Several maps", [make_png(f"map{i}") for i in range(count)])

    slides = _slides(generator, content, tmp_path)

    assert len(_pictures(_slide_titled(slides, "Several maps"))) == count
    assert not any(slide.shapes.title.text == "Several maps (continued)" for slide in slides)


def test_maps_beyond_four_go_on_a_continuation_slide(generator, make_png, tmp_path):
    content = _deck(generator)
    generator.add_map_slide(content, "Many maps", [make_png(f"map{i}") for i in range(5)], description="Five maps")

    slides = _slides(generator, content, tmp_path)

    assert len(_pictures(_slide_titled(slides, "Many maps"))) == 4
    assert len(_pictures(_slide_titled(slides, "Many maps (continued)"))) == 1


def test_missing_map_shows_a_placeholder_and_warns(generator, tmp_path, caplog):
    missing = tmp_path / "not-there.png"
    content = _deck(generator)
    generator.add_map_slide(content, "Missing map", [missing])

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        slide = _slide_titled(_slides(generator, content, tmp_path), "Missing map")

    assert _pictures(slide) == []
    assert "not-there.png" in _text(slide)
    warnings = [record.getMessage() for record in caplog.records if record.name == LOGGER and record.levelno == logging.WARNING]
    assert any(str(missing) in message and "Missing map" in message for message in warnings)


def test_map_slide_without_maps_warns(generator, tmp_path, caplog):
    content = _deck(generator)
    generator.add_map_slide(content, "Empty map slide", [], description="Nothing to show")

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        slide = _slide_titled(_slides(generator, content, tmp_path), "Empty map slide")

    assert _pictures(slide) == []
    warnings = [record.getMessage() for record in caplog.records if record.name == LOGGER and record.levelno == logging.WARNING]
    assert any("Empty map slide" in message and "no maps" in message for message in warnings)


def _engine_style_image(png_bytes):
    """A ReportLab Image built the way the chart and map engines build theirs:
    from the PNG buffer, with the PNG kept on ``filename`` as a data URI."""
    import base64
    import io

    from reportlab.platypus import Image as RLImage

    image = RLImage(io.BytesIO(png_bytes), width=72, height=48)
    image.filename = "data:image/png;base64," + base64.b64encode(png_bytes).decode()
    return image


def test_map_given_as_the_library_s_own_map_image_is_embedded(generator, make_png, tmp_path):
    pytest.importorskip("reportlab")
    content = _deck(generator)
    generator.add_map_slide(content, "Engine map", [_engine_style_image(make_png("engine").read_bytes())])

    slide = _slide_titled(_slides(generator, content, tmp_path), "Engine map")

    assert len(_pictures(slide)) == 1


def test_image_object_without_embedded_data_shows_a_placeholder_and_warns(generator, tmp_path, caplog):
    class ImageWithoutData:
        filename = "drawn-elsewhere"

        def __repr__(self):
            return "<image without data>"

    content = _deck(generator)
    generator.add_map_slide(content, "Undecodable map", [ImageWithoutData()])

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        slide = _slide_titled(_slides(generator, content, tmp_path), "Undecodable map")

    assert _pictures(slide) == []
    assert "[Map: <image without data>]" in _text(slide)
    warnings = [record.getMessage() for record in caplog.records if record.name == LOGGER and record.levelno == logging.WARNING]
    assert any("<image without data>" in message and "Undecodable map" in message for message in warnings)


def test_image_object_with_corrupt_data_raises_naming_the_slide(generator, tmp_path):
    import base64

    class CorruptImage:
        filename = "data:image/png;base64," + base64.b64encode(b"not an image").decode()

    content = _deck(generator)
    generator.add_map_slide(content, "Corrupt engine map", [CorruptImage()])

    with pytest.raises(PILImage.UnidentifiedImageError, match="Corrupt engine map"):
        generator.generate_powerpoint_presentation(content, str(tmp_path / "deck.pptx"))


def test_image_object_with_invalid_base64_raises_naming_the_slide(generator, tmp_path):
    class BadBase64Image:
        filename = "data:image/png;base64,abc"

    content = _deck(generator)
    generator.add_map_slide(content, "Bad base64 map", [BadBase64Image()])

    # A ValueError from a slide builder reaches the caller as RuntimeError,
    # as for every slide type.
    with pytest.raises(RuntimeError, match="Bad base64 map"):
        generator.generate_powerpoint_presentation(content, str(tmp_path / "deck.pptx"))


def test_map_that_is_not_an_image_path_shows_a_placeholder_and_warns(generator, tmp_path, caplog):
    class NotAPath:
        def __repr__(self):
            return "<in-memory map>"

    content = _deck(generator)
    generator.add_map_slide(content, "Object map", [NotAPath()])

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        slide = _slide_titled(_slides(generator, content, tmp_path), "Object map")

    assert _pictures(slide) == []
    assert "[Map: <in-memory map>]" in _text(slide)
    warnings = [record.getMessage() for record in caplog.records if record.name == LOGGER and record.levelno == logging.WARNING]
    assert any("<in-memory map>" in message and "Object map" in message for message in warnings)


def test_map_slide_speaker_notes_go_on_the_first_slide(generator, make_png, tmp_path):
    content = _deck(generator)
    generator.add_map_slide(content, "Noted maps", [make_png(f"map{i}") for i in range(5)])
    content["sections"][-1]["notes"] = "Talk about the regions"

    slides = _slides(generator, content, tmp_path)

    assert _slide_titled(slides, "Noted maps").notes_slide.notes_text_frame.text == "Talk about the regions"
    assert not _slide_titled(slides, "Noted maps (continued)").has_notes_slide


def test_map_path_that_cannot_be_opened_raises_the_original_error(generator, tmp_path):
    directory = tmp_path / "a-directory.png"
    directory.mkdir()
    content = _deck(generator)
    generator.add_map_slide(content, "Directory map", [directory])

    with pytest.raises(OSError, match="a-directory.png") as raised:
        generator.generate_powerpoint_presentation(content, str(tmp_path / "deck.pptx"))
    assert raised.value.errno is not None


def test_missing_chart_image_shows_a_placeholder_and_warns(generator, tmp_path, caplog):
    missing = tmp_path / "no-chart.png"
    content = _deck(generator)
    generator.add_chart_slide(content, "Missing chart", [str(missing)])

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        slide = _slide_titled(_slides(generator, content, tmp_path), "Missing chart")

    assert _pictures(slide) == []
    warnings = [record.getMessage() for record in caplog.records if record.name == LOGGER and record.levelno == logging.WARNING]
    assert any(str(missing) in message and "Missing chart" in message for message in warnings)


def test_chart_described_without_an_image_does_not_warn(generator, tmp_path, caplog):
    content = _deck(generator)
    generator.add_chart_slide(content, "Described chart", [{"title": "Revenue", "type": "bar"}])

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        slide = _slide_titled(_slides(generator, content, tmp_path), "Described chart")

    assert "[Chart: Revenue]" in _text(slide)
    assert not [record for record in caplog.records if record.name == LOGGER and record.levelno >= logging.WARNING]


@pytest.mark.parametrize("helper", ["map", "chart"])
def test_unreadable_image_raises_naming_the_file(generator, tmp_path, helper):
    unreadable = tmp_path / "corrupt.png"
    unreadable.write_bytes(b"not an image")
    content = _deck(generator)
    if helper == "map":
        generator.add_map_slide(content, "Corrupt map", [unreadable])
    else:
        generator.add_chart_slide(content, "Corrupt chart", [str(unreadable)])

    # PIL's own error type is kept, now naming the file and the slide.
    with pytest.raises(PILImage.UnidentifiedImageError, match="corrupt.png") as raised:
        generator.generate_powerpoint_presentation(content, str(tmp_path / "deck.pptx"))
    assert f"Corrupt {helper}" in str(raised.value)


@pytest.mark.parametrize("include_toc, include_agenda", [(True, False), (False, True), (True, True)])
def test_contents_or_agenda_without_sections_warns(generator, caplog, include_toc, include_agenda):
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        _deck(generator, include_toc=include_toc, include_agenda=include_agenda)

    warnings = [record.getMessage() for record in caplog.records if record.name == LOGGER and record.levelno == logging.WARNING]
    assert any("sections" in message and "Deck" in message for message in warnings)


def test_no_contents_warning_when_sections_are_given_or_slides_are_off(generator, caplog):
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        _deck(generator)
        _deck(generator, include_toc=True, include_agenda=True,
              sections=[{"type": "text_slide", "title": "Findings", "content": {"text": "Body"}}])

    assert not [record for record in caplog.records if record.name == LOGGER and record.levelno >= logging.WARNING]


def test_contents_and_agenda_list_the_sections_given_up_front(generator, tmp_path):
    content = _deck(generator, include_toc=True, include_agenda=True,
                    sections=[{"type": "text_slide", "title": "Findings", "content": {"text": "Body"}}])
    generator.add_text_slide(content, "Added later", "Later body")

    slides = _slides(generator, content, tmp_path)

    for title in ("Table of Contents", "Agenda"):
        text = _text(_slide_titled(slides, title))
        assert "Findings" in text
        assert "Added later" not in text
