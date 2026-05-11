"""Test eksport qiluvchilar — HEMIS uchun formatlar."""
from __future__ import annotations

import base64
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom

from .models import Test, Question
from apps.converter.normalizer import normalize_for_hemis, normalize_for_hemis_txt
from apps.converter.latex_renderer import embed_formulas_as_images, embed_formulas_for_moodle


def _fix_cdata_sections(xml_bytes: bytes) -> bytes:
    """XML ning CDATA bloklarini to'g'ri formatlaydi.

    ElementTree matn tarkibidagi '<', '>' larni &lt; &gt; ga aylantiradi.
    Bu funksiya:
    1. &lt;![CDATA[  →  <![CDATA[   va   ]]&gt;  →  ]]>  (chegara belgisi)
    2. CDATA ichidagi &lt;→<  &gt;→>  &amp;→&  (HTML entities qaytarish)
    Natija: CDATA ichida haqiqiy HTML teglar saqlanadi.
    """
    xml_bytes = xml_bytes.replace(b'&lt;![CDATA[', b'<![CDATA[')
    xml_bytes = xml_bytes.replace(b']]&gt;', b']]>')

    def _unescape(m: re.Match) -> bytes:
        content = m.group(1)
        content = content.replace(b'&lt;', b'<')
        content = content.replace(b'&gt;', b'>')
        content = content.replace(b'&amp;', b'&')
        return b'<![CDATA[' + content + b']]>'

    return re.sub(rb'<!\[CDATA\[(.*?)\]\]>', _unescape, xml_bytes, flags=re.DOTALL)


_MIME_BY_EXT = {
    'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
    'png': 'image/png', 'gif': 'image/gif', 'webp': 'image/webp',
}


def _image_to_html(image_field) -> str:
    """ImageField → base64 <img> HTML tegi. Xato bo'lsa bo'sh string qaytaradi."""
    if not image_field:
        return ''
    try:
        image_field.open('rb')
        content = image_field.read()
        image_field.close()
        ext = image_field.name.rsplit('.', 1)[-1].lower() if '.' in image_field.name else ''
        mime = _MIME_BY_EXT.get(ext, 'image/jpeg')
        b64 = base64.standard_b64encode(content).decode()
        return f'<img src="data:{mime};base64,{b64}" style="max-width:100%;display:block;margin:6px 0"/>'
    except Exception:
        return ''


LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _letter(idx: int) -> str:
    """0->A, 25->Z, 26->AA, 27->AB ..."""
    if idx < 26:
        return LETTERS[idx]
    return LETTERS[idx // 26 - 1] + LETTERS[idx % 26]


def export_aiken(test: Test) -> str:
    """Aiken format — HEMIS va Moodle qo'llab-quvvatlaydigan oddiy matn.

    Savol matni
    A. variant 1
    B. variant 2
    C. variant 3
    D. variant 4
    ANSWER: A
    """
    lines: list[str] = []
    for q in test.questions.all().prefetch_related('choices'):
        lines.append(normalize_for_hemis(q.text))
        correct_letters: list[str] = []
        for idx, choice in enumerate(q.choices.all()):
            letter = _letter(idx)
            lines.append(f"{letter}. {normalize_for_hemis(choice.text)}")
            if choice.is_correct:
                correct_letters.append(letter)
        lines.append(f"ANSWER: {','.join(correct_letters) if correct_letters else 'A'}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def export_moodle_xml(test: Test) -> bytes:
    """Moodle XML format — HEMIS ham qabul qiladi (import turi: moodle).

    Formulalar $$formula$$ TeX notation sifatida yoziladi —
    HEMIS math filter yoki MathJax bu notatsiyani render qiladi.
    Data-URI PNG ishlatilmaydi (HEMIS sanitizatsiya qilib o'chiradi).
    """
    quiz = ET.Element('quiz')

    for q in test.questions.all().prefetch_related('choices'):
        qtype = 'multichoice'
        q_el = ET.SubElement(quiz, 'question', {'type': qtype})

        name_el = ET.SubElement(q_el, 'name')
        ET.SubElement(name_el, 'text').text = (q.text[:60] or f"Savol {q.pk}").strip()

        q_html = embed_formulas_for_moodle(q.text) + _image_to_html(q.image)
        text_el = ET.SubElement(q_el, 'questiontext', {'format': 'html'})
        ET.SubElement(text_el, 'text').text = f"<![CDATA[{q_html}]]>"

        ET.SubElement(q_el, 'defaultgrade').text = str(q.points)
        ET.SubElement(q_el, 'single').text = 'true' if q.qtype == 'single' else 'false'
        ET.SubElement(q_el, 'shuffleanswers').text = 'true'
        ET.SubElement(q_el, 'answernumbering').text = 'abc'

        correct_count = sum(1 for c in q.choices.all() if c.is_correct) or 1
        for choice in q.choices.all():
            fraction = str(round(100 / correct_count, 2)) if choice.is_correct else '0'
            ans_el = ET.SubElement(q_el, 'answer', {'fraction': fraction, 'format': 'html'})
            choice_html = embed_formulas_for_moodle(choice.text) + _image_to_html(choice.image)
            ET.SubElement(ans_el, 'text').text = f"<![CDATA[{choice_html}]]>"

        if q.explanation:
            fb_el = ET.SubElement(q_el, 'generalfeedback', {'format': 'html'})
            exp_html = embed_formulas_for_moodle(q.explanation)
            ET.SubElement(fb_el, 'text').text = f"<![CDATA[{exp_html}]]>"

    rough = ET.tostring(quiz, encoding='utf-8')
    pretty = minidom.parseString(rough).toprettyxml(indent='  ', encoding='utf-8')
    return _fix_cdata_sections(pretty)


def export_hemis_xml(test: Test) -> bytes:
    """HEMIS native XML — formulalar $$...$$ TeX notation sifatida.

    Savol va variant matnlari CDATA HTML sifatida joylashtiriladi,
    formulalar $$formula$$ formatda — HEMIS math filter render qiladi.
    """
    root = ET.Element('hemis-test', {
        'title': test.title,
        'subject': test.subject.name if test.subject else '',
        'time-limit': str(test.time_limit),
        'version': '1.0',
    })

    for idx, q in enumerate(test.questions.all().prefetch_related('choices'), 1):
        q_el = ET.SubElement(root, 'question', {
            'id': str(q.pk),
            'order': str(idx),
            'type': q.qtype,
            'points': str(q.points),
        })
        q_html = embed_formulas_for_moodle(q.text) + _image_to_html(q.image)
        ET.SubElement(q_el, 'text').text = f"<![CDATA[{q_html}]]>"

        choices_el = ET.SubElement(q_el, 'choices')
        for c_idx, choice in enumerate(q.choices.all(), 1):
            choice_html = embed_formulas_for_moodle(choice.text) + _image_to_html(choice.image)
            ET.SubElement(choices_el, 'choice', {
                'order': str(c_idx),
                'correct': 'true' if choice.is_correct else 'false',
            }).text = f"<![CDATA[{choice_html}]]>"

        if q.explanation:
            exp_html = embed_formulas_for_moodle(q.explanation)
            ET.SubElement(q_el, 'explanation').text = f"<![CDATA[{exp_html}]]>"

    rough = ET.tostring(root, encoding='utf-8')
    pretty = minidom.parseString(rough).toprettyxml(indent='  ', encoding='utf-8')
    return _fix_cdata_sections(pretty)


def export_hemis_txt(test: Test) -> str:
    """HEMIS uchun ++++/==== ajratgichli matn format.

    Har bir savol va variant o'rtasida bo'sh qator qo'yiladi —
    HEMIS importer tomonidan to'g'ri o'qilishi uchun.
    LaTeX $...$ formulalar Unicode belgilarga aylantiriladi
    ($\\sqrt{x}$ → √x) chunki matn formatda rasm joylashtirib bo'lmaydi.

    ++++

    Savol matni

    ====

    #to'g'ri variant

    ====

    variant 2
    ...
    """
    blocks: list[str] = []
    for q in test.questions.all().prefetch_related('choices'):
        lines: list[str] = [
            "++++",
            "",
            normalize_for_hemis_txt(q.text),
            "",
        ]
        for choice in q.choices.all():
            prefix = "#" if choice.is_correct else ""
            lines.extend([
                "====",
                "",
                f"{prefix}{normalize_for_hemis_txt(choice.text)}",
                "",
            ])
        blocks.append("\n".join(lines))
    return "\n".join(blocks) + "\n"


FORMATS = {
    'moodle': ('Moodle XML — formulalar rasm sifatida (.xml)', 'application/xml', 'xml', export_moodle_xml),
    'hemis': ('HEMIS XML (.xml)', 'application/xml', 'xml', export_hemis_xml),
    'hemis_txt': ('HEMIS matn (.txt)', 'text/plain; charset=utf-8', 'txt', export_hemis_txt),
}
