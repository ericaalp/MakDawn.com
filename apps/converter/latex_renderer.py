"""LaTeX formulalarni render qilish va formatlash moduli.

Eksport turlari uchun turli funksiyalar:
  - embed_formulas_for_moodle()  → Moodle/HEMIS XML uchun $$...$$ notation
                                    (HEMIS math filter yoki MathJax render qiladi)
  - embed_formulas_as_images()   → PNG data-URI uchun (kelajakda ham saqlanadi)
  - formula_to_png()             → bitta formulani PNG ga aylantirish

Raw LaTeX ($siz) ham qo'llab-quvvatlanadi:
  \\frac{a}{b}, \\sqrt{x}, \\int_0^1 ... va h.k.
"""
from __future__ import annotations

import base64
import io
import logging
import re

logger = logging.getLogger(__name__)

_DISPLAY_RE = re.compile(r'\$\$(.+?)\$\$', re.DOTALL)
_INLINE_RE  = re.compile(r'\$([^$\n]+?)\$')

# Raw LaTeX ni aniqlash: bu buyruqlar bo'lsa formula hisoblanadi
_RAW_LATEX_RE = re.compile(
    r'\\(?:'
    r'frac|dfrac|tfrac|cfrac|binom|'
    r'sqrt|'
    r'int|iint|iiint|oint|'
    r'sum|prod|'
    r'lim|limsup|liminf|'
    r'alpha|beta|gamma|delta|epsilon|varepsilon|zeta|eta|theta|iota|kappa|'
    r'lambda|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|varphi|chi|psi|omega|'
    r'Gamma|Delta|Theta|Lambda|Pi|Sigma|Phi|Psi|Omega|'
    r'infty|partial|nabla|'
    r'sin|cos|tan|cot|sec|csc|arcsin|arccos|arctan|sinh|cosh|tanh|'
    r'log|ln|exp|'
    r'leq|geq|neq|approx|equiv|times|div|pm|cdot|'
    r'rightarrow|leftarrow|Rightarrow|Leftarrow|to|leftrightarrow|'
    r'overline|underline|hat|vec|dot|bar|tilde|'
    r'mathbb|mathrm|mathbf|mathit|mathcal|boldsymbol'
    r')(?![a-zA-Z])'
)


def _is_pure_formula(text: str) -> bool:
    """Butun matn raw LaTeX formula ekanligini aniqlaydi ($...$ belgisiz)."""
    t = text.strip()
    if re.match(r'^\\[a-zA-Z]', t):
        return True
    plain = re.sub(r'\\[a-zA-Z]+|\{[^{}]*\}|\d|[+\-*/=.,;:()\[\]^_ ]', '', t)
    return len(plain) < 4 and len(t) < 120


def _formula_to_unicode(formula: str) -> str:
    """Unicode fallback — formulani o'qiladigan Unicode matnga o'giradi."""
    from .normalizer import _latex_to_unicode_fallback
    return _latex_to_unicode_fallback(formula)


# ─── Moodle/HEMIS XML uchun $$...$$ notation ─────────────────────────────────

_DOLLAR_RE = re.compile(r'\$\$(.+?)\$\$|\$([^$\n]+?)\$', re.DOTALL)


def embed_formulas_for_moodle(text: str) -> str:
    """Formulalarni Moodle/HEMIS TeX notation ga o'giradi: $$formula$$.

    HEMIS math filter va MathJax ikkalasi ham $$...$$ ni taniydi.
    Data-URI PNG ishlatilmaydi — LaTeX matn sifatida qoladi,
    HEMIS o'zi server tomonda yoki brauzerda render qiladi.

    Qamrov:
      $...$   inline  → $$formula$$
      $$...$$ display → $$formula$$   (bitta combined regex — ikki karra match yo'q)
      \\frac{a}{b}   raw LaTeX → $$formula$$
      Aralash matn + raw LaTeX → Unicode konversiya
    """
    if not text:
        return text

    had_dollar = '$' in text

    if had_dollar:
        # Bitta o'tish: $$...$$ va $...$ ni alohida ajratmaymiz — overlap muammosi yo'q
        def _to_moodle(m: re.Match) -> str:
            formula = (m.group(1) or m.group(2) or '').strip()
            return f'$${formula}$$'
        text = _DOLLAR_RE.sub(_to_moodle, text)

    # Raw LaTeX ($siz): FAQAT agar original matnda $ bo'lmagan bo'lsa
    if not had_dollar and '\\' in text and _RAW_LATEX_RE.search(text):
        if _is_pure_formula(text):
            text = f'$${text.strip()}$$'
        else:
            text = _formula_to_unicode(text)

    return text


# ─── PNG rendering (ixtiyoriy, saqlanadi) ────────────────────────────────────

def formula_to_png(formula: str, fontsize: int = 16, dpi: int = 200) -> bytes | None:
    """LaTeX formulasini PNG baytlar sifatida qaytaradi. Xato bo'lsa None.

    Yaxshi sifat uchun: oq fon, DPI=200, fontsize=16.
    """
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        math_str = f'${formula.strip()}$'

        fig, ax = plt.subplots(figsize=(8, 1.8))
        ax.set_axis_off()
        # Oq fon — shaffof o'rniga (HEMIS dark background da ham ko'rinadi)
        fig.patch.set_facecolor('white')
        ax.patch.set_facecolor('white')

        ax.text(
            0.5, 0.5, math_str,
            fontsize=fontsize,
            ha='center', va='center',
            transform=ax.transAxes,
            color='black',
        )

        buf = io.BytesIO()
        fig.savefig(
            buf, format='png', dpi=dpi,
            bbox_inches='tight',
            facecolor='white',
            pad_inches=0.08,
        )
        plt.close(fig)
        return buf.getvalue()

    except Exception as exc:
        logger.warning("LaTeX PNG render xatosi '%s': %s", formula[:40], exc)
        return None


def formula_to_data_uri(formula: str, display: bool = False) -> str | None:
    """PNG → data:image/png;base64,... URI. Xato bo'lsa None."""
    fontsize = 18 if display else 16
    png = formula_to_png(formula, fontsize=fontsize)
    if png is None:
        return None
    b64 = base64.standard_b64encode(png).decode()
    return f'data:image/png;base64,{b64}'


def _replace_display(m: re.Match) -> str:
    formula = m.group(1).strip()
    uri = formula_to_data_uri(formula, display=True)
    if uri:
        alt = formula.replace('"', '&quot;')
        return (
            f'<img src="{uri}" alt="{alt}" '
            f'style="display:block;margin:6px auto;max-width:100%"/>'
        )
    return f'<span class="formula-text">{_formula_to_unicode(formula)}</span>'


def _replace_inline(m: re.Match) -> str:
    formula = m.group(1).strip()
    uri = formula_to_data_uri(formula, display=False)
    if uri:
        alt = formula.replace('"', '&quot;')
        return (
            f'<img src="{uri}" alt="{alt}" '
            f'style="vertical-align:middle;max-height:1.6em"/>'
        )
    return f'<span class="formula-text">{_formula_to_unicode(formula)}</span>'


def _process_raw_latex_in_text(text: str) -> str:
    if _is_pure_formula(text):
        stripped = text.strip()
        uri = formula_to_data_uri(stripped, display=len(stripped) > 25)
        if uri:
            alt = stripped.replace('"', '&quot;')
            return f'<img src="{uri}" alt="{alt}" style="display:inline-block;vertical-align:middle;max-width:100%"/>'
        return f'<span class="formula-text">{_formula_to_unicode(stripped)}</span>'
    from .normalizer import _latex_to_unicode_fallback
    return _latex_to_unicode_fallback(text)


def embed_formulas_as_images(text: str) -> str:
    """PNG data-URI sifatida render (ixtiyoriy foydalanish uchun saqlanadi).

    Moodle/HEMIS XML uchun embed_formulas_for_moodle() ishlatish tavsiya etiladi.
    """
    if not text:
        return text
    if '$' in text:
        text = _DISPLAY_RE.sub(_replace_display, text)
        text = _INLINE_RE.sub(_replace_inline, text)
    if '\\' in text and _RAW_LATEX_RE.search(text):
        text = _process_raw_latex_in_text(text)
    return text
