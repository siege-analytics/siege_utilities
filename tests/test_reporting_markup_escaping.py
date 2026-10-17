"""Regression coverage for data embedded in reporting markup (#1565)."""

import io
import zipfile
from types import SimpleNamespace
from unittest.mock import Mock
from xml.dom import minidom
from xml.parsers.expat import ExpatError

import pytest

from siege_utilities.reporting.idml_export import IDMLExporter


DATA = 'A & B <x> "quoted"'
ESCAPED = 'A &amp; B &lt;x&gt; "quoted"'
PAYLOAD = '<img src=x onerror=alert(1)>'
COLORS = ('#112233', '#445566', '#778899')


@pytest.mark.parametrize('style', ['Head"ing & <1>', 'A & "B" \'C\''])
def test_idml_all_xml_members_are_well_formed(tmp_path, style):
    exporter = IDMLExporter()
    exporter.add_text_frame('x', style_name=style)
    output = exporter.save(tmp_path / 'escaped.idml')
    documents = {}
    errors = []
    with zipfile.ZipFile(output) as archive:
        for name in archive.namelist():
            if name.endswith('.xml'):
                try:
                    documents[name] = minidom.parseString(archive.read(name))
                except ExpatError as exc:
                    errors.append(f'{name}: {exc}')
    assert not errors, '\n'.join(errors)
    styles = documents['Resources/Styles.xml'].getElementsByTagName('ParagraphStyle')
    matching = [node for node in styles if node.getAttribute('Name') == style]
    assert len(matching) == 1
    assert matching[0].getAttribute('Self') == 'ParagraphStyle/' + style
    story = next(doc for name, doc in documents.items() if name.startswith('Stories/'))
    applied = story.getElementsByTagName('ParagraphStyleRange')[0]
    assert applied.getAttribute('AppliedParagraphStyle') == 'ParagraphStyle/' + style
    assert story.getElementsByTagName('Content')[0].firstChild.data == 'x'


@pytest.mark.parametrize('as_bytes', [True, False])
@pytest.mark.parametrize('placeholder', ['{{title}}', '{{date_range}}'])
def test_idml_raw_story_replacements_preserve_text(as_bytes, placeholder):
    original = f'<Story><Content>{placeholder}</Content></Story>'
    stories = {'Stories/Story.xml': original.encode() if as_bytes else original}
    pkg = SimpleNamespace(stories=list(stories), read=stories.__getitem__, writestr=stories.__setitem__)
    IDMLExporter._apply_replacements_raw_simpleidml(pkg, placeholder, DATA)
    xml = stories['Stories/Story.xml']
    assert b'A &amp; B &lt;x&gt;' in xml
    doc = minidom.parseString(xml)
    assert doc.getElementsByTagName('Content')[0].firstChild.data == DATA


def test_idml_manual_replacements_are_escaped_once(tmp_path):
    exporter = IDMLExporter()
    exporter.add_text_frame('{{title}}')
    exporter.replace_placeholder('{{title}}', DATA)
    with zipfile.ZipFile(exporter.save(tmp_path / 'replacement.idml')) as archive:
        story = next(name for name in archive.namelist() if name.startswith('Stories/'))
        doc = minidom.parseString(archive.read(story))
    assert doc.getElementsByTagName('Content')[0].firstChild.data == DATA


@pytest.fixture
def paragraph_api():
    pytest.importorskip('reportlab')
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph
    return Paragraph, getSampleStyleSheet()


@pytest.mark.parametrize('field', ['title', 'subtitle', 'author', 'date'])
def test_template_title_page_escapes_data(paragraph_api, field):
    from siege_utilities.reporting.templates.base_template import BaseReportTemplate
    Paragraph, styles = paragraph_api
    template = BaseReportTemplate.__new__(BaseReportTemplate)
    template.styles = styles
    kwargs = {'title': 'Report', field: DATA}
    paragraphs = [p for p in template.add_title_page(**kwargs) if isinstance(p, Paragraph)]
    assert any(ESCAPED in p.text for p in paragraphs)
    assert any(DATA in p.getPlainText() for p in paragraphs)


@pytest.mark.parametrize('section,field', [
    ('header', 'left_text'), ('header', 'right_text'),
    ('footer', 'left_text'), ('footer', 'right_text'), ('footer', 'page_number_format'),
])
def test_branding_text_escapes_data(paragraph_api, monkeypatch, section, field):
    from reportlab.pdfgen.canvas import Canvas
    from siege_utilities.reporting.templates import base_template
    Paragraph, styles = paragraph_api
    template = base_template.BaseReportTemplate.__new__(base_template.BaseReportTemplate)
    template.styles = {'HeaderFooter': styles['Normal']}
    template.branding_config = {section: {field: DATA + (' %s' if field == 'page_number_format' else '')}}
    spy = Mock(wraps=Paragraph)
    monkeypatch.setattr(base_template, 'Paragraph', spy)
    doc = SimpleNamespace(pagesize=(612, 792), topMargin=72, bottomMargin=72,
                          leftMargin=72, rightMargin=72, page=1)
    template._header_footer_on_page(Canvas(io.BytesIO()), doc)
    assert any(ESCAPED in call.args[0] for call in spy.call_args_list)


@pytest.mark.parametrize('method', ['caption', 'section'])
def test_chart_caption_and_section_escape_data(paragraph_api, method):
    from siege_utilities.reporting.engines.base_engine import BaseChartEngine
    Paragraph, styles = paragraph_api
    engine = BaseChartEngine.__new__(BaseChartEngine)
    engine.styles = styles
    if method == 'caption':
        content = engine.create_chart_with_caption(None, DATA)
        expected = 1
    else:
        content = engine.create_chart_section(DATA, [], description=DATA)
        expected = 2
    paragraphs = [p for p in content if isinstance(p, Paragraph)]
    assert len(paragraphs) == expected
    assert all(p.text == ESCAPED and p.getPlainText() == DATA for p in paragraphs)


@pytest.mark.parametrize('field', ['client_name', 'tagline', 'report_type', 'prepared_by', 'dates'])
def test_title_page_data_is_escaped(paragraph_api, field):
    from siege_utilities.reporting.pages.page_models import TitlePage
    Paragraph, _ = paragraph_api
    kwargs = dict(client_name='Client', client_url='https://example.test', prepared_by='Author')
    if field != 'dates':
        kwargs[field] = DATA
    page = TitlePage(*COLORS, **kwargs)
    dates = (DATA, DATA) if field == 'dates' else ('2026-01-01', '2026-01-31')
    content = page.build(*dates)
    paragraphs = [p for p in content if isinstance(p, Paragraph)]
    assert any(ESCAPED in p.text for p in paragraphs)
    assert any(DATA in p.getPlainText() for p in paragraphs)


@pytest.mark.parametrize('field,value,prefix', [
    ('client_url', 'https://example.test/?q="A"&next=<x>', ''),
    ('phone', '+1" & <2>', 'tel:'),
])
def test_title_page_link_attribute_round_trip(paragraph_api, field, value, prefix):
    from siege_utilities.reporting.pages.page_models import TitlePage
    Paragraph, _ = paragraph_api
    kwargs = dict(client_name='Client', client_url='https://example.test', prepared_by='Author')
    kwargs[field] = value
    paragraphs = [p for p in TitlePage(*COLORS, **kwargs).build('start', 'end') if isinstance(p, Paragraph)]
    text = next(p.text for p in paragraphs if ('Phone:' if field == 'phone' else 'Website:') in p.text)
    doc = minidom.parseString('<root>' + text + '</root>')
    anchor = doc.getElementsByTagName('a')[0]
    assert anchor.getAttribute('href') == prefix + value
    assert anchor.firstChild.data == value
    assert '&quot;' in text
    assert '<b>' in text and '<br/>' in text and '<a href="' in text


def test_table_of_contents_escapes_section_title_and_page(paragraph_api):
    from siege_utilities.reporting.pages.page_models import TableOfContentsPage
    Paragraph, _ = paragraph_api
    content = TableOfContentsPage(*COLORS).build([{'section': DATA, 'title': DATA, 'page_num': DATA}])
    paragraphs = [p for p in content if isinstance(p, Paragraph)]
    assert [p.text for p in paragraphs] == ['Table of Contents', ESCAPED, ESCAPED + ' · ' + ESCAPED]


@pytest.mark.parametrize('kind', ['bar', 'heatmap'])
@pytest.mark.parametrize('scenario', ['data', 'empty', 'characters'])
def test_text_charts_escape_data_inside_intentional_markup(kind, scenario):
    pd = pytest.importorskip('pandas')
    from siege_utilities.reporting.engines.bar_engine import BarChartMixin
    from siege_utilities.reporting.engines.stats_engine import StatsChartMixin
    data = pd.DataFrame({'label': [DATA], 'column': [DATA], 'value': [1]})
    if scenario == 'empty':
        data = data.iloc[:0]
    value_column = 'value'
    if kind == 'bar':
        text = BarChartMixin().create_proportional_text_bar_chart(
            data, 'label', value_column, title=DATA,
            bar_char='<' if scenario == 'characters' else '█',
        )
    else:
        text = StatsChartMixin().create_heatmap_text_chart(
            data, 'column', 'label', value_column, title=DATA,
            heat_chars='<&>' if scenario == 'characters' else ' ░▒▓█',
        )
    assert ESCAPED in text
    assert '<x>' not in text and '&amp;amp;' not in text
    if scenario == 'empty':
        assert text.startswith('<i>') and text.endswith('</i>')
    else:
        assert text.startswith(f'<b>{ESCAPED}</b><br/>')
        assert text.count(ESCAPED) >= (2 if kind == 'bar' else 3)
        if scenario == 'characters':
            assert '&lt;&lt;' in text
    try:
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph
    except ImportError:
        return
    Paragraph(text, getSampleStyleSheet()['Normal'])


@pytest.mark.parametrize('kind', ['bar', 'heatmap'])
def test_text_chart_errors_raise_instead_of_rendering_error_markup(kind):
    pd = pytest.importorskip('pandas')
    from siege_utilities.reporting.engines.bar_engine import BarChartMixin
    from siege_utilities.reporting.engines.stats_engine import StatsChartMixin

    data = pd.DataFrame({'label': [DATA], 'column': [DATA], 'value': [1]})
    with pytest.raises(RuntimeError) as exc:
        if kind == 'bar':
            BarChartMixin().create_proportional_text_bar_chart(data, 'label', DATA)
        else:
            StatsChartMixin().create_heatmap_text_chart(data, 'column', 'label', DATA)
    assert isinstance(exc.value.__cause__, KeyError)
    assert DATA in str(exc.value.__cause__)


def test_report_generator_existing_escape_is_not_doubled(paragraph_api):
    pytest.importorskip('pandas')
    from siege_utilities.reporting.report_generator import ReportGenerator
    Paragraph, styles = paragraph_api
    generator = ReportGenerator.__new__(ReportGenerator)
    section = {'title': DATA, 'content': f'{DATA}\n- {DATA}'}
    content = generator._build_section_content(section, SimpleNamespace(styles=styles))
    paragraphs = [p for p in content if isinstance(p, Paragraph)]
    assert [p.text for p in paragraphs] == [ESCAPED, ESCAPED, '&bull; ' + ESCAPED]


@pytest.mark.parametrize('kind', ['marker', 'cluster', 'flow'])
def test_folium_popup_html_escapes_stored_payload(kind, monkeypatch, tmp_path):
    try:
        import folium
    except ImportError:
        from siege_utilities.reporting._markup import _build_popup_html
        if kind == 'flow':
            text = _build_popup_html(details=[f'Flow: {PAYLOAD}'])
        else:
            details = [f'Cluster: {PAYLOAD}'] if kind == 'cluster' else []
            text = _build_popup_html(PAYLOAD, details)
    else:
        pd = pytest.importorskip('pandas')
        from siege_utilities.reporting.engines.map_engine import MapChartMixin
        engine = MapChartMixin()
        maps = []
        monkeypatch.setattr(engine, '_save_folium_map', lambda m, *args: maps.append(m), raising=False)
        if kind == 'marker':
            engine.create_marker_map({'lat': [40.0], 'lon': [-90.0], 'label': [PAYLOAD]},
                                     'lat', 'lon', label_column='label', map_style='OpenStreetMap')
        elif kind == 'cluster':
            engine.create_cluster_map({'lat': [40.0], 'lon': [-90.0], 'label': [PAYLOAD], 'group': [PAYLOAD]},
                                      'lat', 'lon', label_column='label', cluster_column='group')
        else:
            class LabeledFlow(float):
                """A numeric flow whose display label comes from external data."""
                def __str__(self):
                    return PAYLOAD
            data = pd.DataFrame({'lat': [40.0], 'lon': [-90.0], 'dest_lat': [41.0],
                                 'dest_lon': [-91.0], 'flow': [LabeledFlow(1)]}, dtype=object)
            engine.create_flow_map(data, 'lat', 'lon', 'dest_lat', 'dest_lon', flow_value_column='flow')
        assert len(maps) == 1
        assert isinstance(maps[0], folium.Map)
        output = tmp_path / f'{kind}.html'
        maps[0].save(output)
        text = output.read_text()
    assert '&lt;img src=x onerror=alert(1)&gt;' in text
    assert '<img' not in text
    if kind != 'flow':
        assert '<b>&lt;img' in text
    if kind == 'cluster':
        assert 'Cluster: &lt;img' in text


def test_geographic_example_popup_escapes_city_and_column(tmp_path):
    pytest.importorskip('folium')
    pd = pytest.importorskip('pandas')
    from siege_utilities.reporting.examples.ga_geographic_analysis import create_city_heatmap
    data = pd.DataFrame({'latitude': [40.0], 'longitude': [-90.0], 'city': [PAYLOAD], PAYLOAD: [1]})
    output = tmp_path / 'cities.html'
    create_city_heatmap(data, value_column=PAYLOAD, output_path=str(output))
    text = output.read_text()
    assert text.count('&lt;img src=x onerror=alert(1)&gt;') == 2
    assert '<img' not in text


def test_example_footnote_preserves_bold_markup(paragraph_api, monkeypatch):
    from siege_utilities.reporting.examples import google_analytics_report_example as example
    monkeypatch.setitem(example.GA_TERM_DEFINITIONS, 'a & b <x>', DATA)
    paragraph = example.create_footnote_paragraph(['a & b <x>'])
    assert paragraph.text == '<b>A &amp; B &lt;X&gt;:</b> ' + ESCAPED


def test_bivariate_map_layer_name_escapes_html(monkeypatch):
    folium = pytest.importorskip('folium')
    gpd = pytest.importorskip('geopandas')
    from shapely.geometry import Point
    from siege_utilities.reporting.engines.map_engine import MapChartMixin
    data = gpd.GeoDataFrame({'x': [1, 2, 3], 'y': [3, 2, 1]},
                            geometry=[Point(-90, 40), Point(-91, 41), Point(-92, 42)], crs='EPSG:4326')
    engine = MapChartMixin()
    maps = []
    monkeypatch.setattr(engine, '_save_folium_map', lambda m, *args: maps.append(m), raising=False)
    engine.create_bivariate_choropleth(data, value_column1='x', value_column2='y', title=PAYLOAD)
    layers = [child for child in maps[0]._children.values() if isinstance(child, folium.GeoJson)]
    assert layers[0].layer_name == '&lt;img src=x onerror=alert(1)&gt;'
