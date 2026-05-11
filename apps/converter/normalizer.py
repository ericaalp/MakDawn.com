"""Matnni HEMIS uchun moslab tozalovchi modul.

HEMIS UTF-8 ni qabul qiladi va matematik belgilarni chiroyli ko'rsatadi.

Vazifa:
  - normalize_for_hemis(): LaTeX $...$ bloklarini SAQLAB qoladi (KaTeX uchun).
    Faqat LaTeX tashqarisidagi ASCII yozuvlarni Unicode ga aylantiradi.
  - normalize_for_hemis_txt(): HEMIS .txt eksport uchun — LaTeX → Unicode.
    pylatexenc + kuchli regex fallback ishlatiladi.
"""
from __future__ import annotations

import html as html_lib
import re
import unicodedata

try:
    from pylatexenc.latex2text import LatexNodes2Text
    _LATEX = LatexNodes2Text()
except ImportError:  # pragma: no cover
    _LATEX = None


# ─── Yunoncha harflar ────────────────────────────────────────────────────────
_GREEK_LETTERS: dict[str, str] = {
    'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'delta': 'δ',
    'epsilon': 'ε', 'varepsilon': 'ε', 'zeta': 'ζ', 'eta': 'η',
    'theta': 'θ', 'vartheta': 'ϑ', 'iota': 'ι', 'kappa': 'κ',
    'lambda': 'λ', 'mu': 'μ', 'nu': 'ν', 'xi': 'ξ',
    'pi': 'π', 'varpi': 'ϖ', 'rho': 'ρ', 'varrho': 'ϱ',
    'sigma': 'σ', 'varsigma': 'ς', 'tau': 'τ', 'upsilon': 'υ',
    'phi': 'φ', 'varphi': 'φ', 'chi': 'χ', 'psi': 'ψ', 'omega': 'ω',
    # Katta yunoncha
    'Alpha': 'Α', 'Beta': 'Β', 'Gamma': 'Γ', 'Delta': 'Δ', 'Epsilon': 'Ε',
    'Zeta': 'Ζ', 'Eta': 'Η', 'Theta': 'Θ', 'Iota': 'Ι', 'Kappa': 'Κ',
    'Lambda': 'Λ', 'Mu': 'Μ', 'Nu': 'Ν', 'Xi': 'Ξ', 'Pi': 'Π',
    'Rho': 'Ρ', 'Sigma': 'Σ', 'Tau': 'Τ', 'Upsilon': 'Υ', 'Phi': 'Φ',
    'Chi': 'Χ', 'Psi': 'Ψ', 'Omega': 'Ω',
}

# ─── Matematik operatorlar ────────────────────────────────────────────────────
_MATH_OPERATORS: dict[str, str] = {
    r'\times': '×', r'\div': '÷', r'\pm': '±', r'\mp': '∓',
    r'\cdot': '·', r'\bullet': '•', r'\circ': '∘',
    r'\leq': '≤', r'\le': '≤', r'\geq': '≥', r'\ge': '≥',
    r'\neq': '≠', r'\ne': '≠', r'\approx': '≈', r'\equiv': '≡',
    r'\sim': '∼', r'\simeq': '≃', r'\cong': '≅', r'\propto': '∝',
    r'\ll': '≪', r'\gg': '≫',
    # To'plamlar
    r'\subset': '⊂', r'\supset': '⊃', r'\subseteq': '⊆', r'\supseteq': '⊇',
    r'\in': '∈', r'\notin': '∉', r'\ni': '∋',
    r'\cup': '∪', r'\cap': '∩', r'\emptyset': '∅', r'\varnothing': '∅',
    r'\setminus': '∖',
    # Hisob
    r'\infty': '∞', r'\partial': '∂', r'\nabla': '∇',
    r'\forall': '∀', r'\exists': '∃', r'\nexists': '∄',
    # Mantiq
    r'\land': '∧', r'\wedge': '∧', r'\lor': '∨', r'\vee': '∨',
    r'\lnot': '¬', r'\neg': '¬',
    # O'qlar
    r'\rightarrow': '→', r'\leftarrow': '←', r'\leftrightarrow': '↔',
    r'\Rightarrow': '⇒', r'\Leftarrow': '⇐', r'\Leftrightarrow': '⇔',
    r'\to': '→', r'\gets': '←', r'\mapsto': '↦',
    r'\uparrow': '↑', r'\downarrow': '↓', r'\updownarrow': '↕',
    r'\nearrow': '↗', r'\searrow': '↘', r'\swarrow': '↙', r'\nwarrow': '↖',
    # Nuqtalar
    r'\ldots': '…', r'\cdots': '⋯', r'\vdots': '⋮', r'\ddots': '⋱',
    # Qavslar
    r'\langle': '⟨', r'\rangle': '⟩',
    r'\lceil': '⌈', r'\rceil': '⌉', r'\lfloor': '⌊', r'\rfloor': '⌋',
    r'\lvert': '|', r'\rvert': '|', r'\lVert': '‖', r'\rVert': '‖',
    # Geometriya
    r'\perp': '⊥', r'\parallel': '∥', r'\angle': '∠', r'\triangle': '△',
    r'\square': '□', r'\diamond': '◇',
    # Maxsus
    r'\hbar': 'ℏ', r'\ell': 'ℓ', r'\Re': 'ℜ', r'\Im': 'ℑ',
    r'\aleph': 'ℵ', r'\wp': '℘',
    # Oddiy belgilar
    r'\%': '%', r'\$': '$', r'\#': '#', r'\&': '&',
    r'\_': '_', r'\{': '{', r'\}': '}',
    r'\|': '‖', r'\\': '\n',
}

# ─── Matematik funksiyalar ───────────────────────────────────────────────────
_MATH_FUNCTIONS: list[str] = [
    'arcsin', 'arccos', 'arctan', 'arccot', 'arcsec', 'arccsc',
    'sinh', 'cosh', 'tanh', 'coth', 'sech', 'csch',
    'sin', 'cos', 'tan', 'cot', 'sec', 'csc',
    'log', 'lg', 'ln', 'exp',
    'lim', 'limsup', 'liminf',
    'max', 'min', 'sup', 'inf', 'gcd', 'lcm',
    'det', 'dim', 'ker', 'deg', 'rank',
    'mod', 'arg', 'sgn',
]

# ─── Daraja (superscript) va indeks (subscript) ───────────────────────────────
SUP_DIGITS = str.maketrans(
    '0123456789+-=()abcdefghijklmnoprstuvwxyzABDEGHIJKLMNOPRTUVW',
    '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻᴬᴮᴰᴱᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾᴿᵀᵁⱽᵂ',
)
SUP_ALLOWED = set('0123456789+-=()abcdefghijklmnoprstuvwxyzABDEGHIJKLMNOPRTUVW')
SUB_DIGITS = str.maketrans('0123456789+-=()', '₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎')

_QUOTES = {
    '"': '"', '"': '"', '„': '"',
    '«': '"', '»': '"',
    ''': "'", ''': "'",
}

ASCII_TO_PRETTY = {
    '>=': '≥', '<=': '≤', '!=': '≠', '~=': '≈', '+/-': '±', '-/+': '∓',
    '->': '→', '<-': '←', '<->': '↔', '=>': '⇒', '<=>': '⇔',
}

FUNC_TO_SYMBOL = {
    'sqrt': '√', 'cbrt': '∛',
    'sum':  '∑', 'prod': '∏',
    'integral': '∫', 'oint': '∮',
    'inf': '∞', 'infinity': '∞',
    'empty': '∅',
    'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'delta': 'δ',
    'theta': 'θ', 'lambda': 'λ', 'mu': 'μ', 'sigma': 'σ',
    'phi': 'φ', 'omega': 'ω', 'pi': 'π',
    'Delta': 'Δ', 'Sigma': 'Σ', 'Pi': 'Π', 'Omega': 'Ω',
}


# ─── Regex asosida kuchli fallback konverteri ─────────────────────────────────

def _latex_to_unicode_fallback(text: str) -> str:
    """pylatexenc muvaffaqiyatsiz bo'lganda ishlaydigan regex konverteri.

    Universitetdagi eng ko'p uchraydigan matematik formulalarni qamrab oladi:
    integrallar, kasr, ildiz, limit, yig'indi, yunon harflari, operatorlar.
    Ichma-ich formulalar uchun bir necha marta o'tkaziladi.
    """
    # Bir daraja ichma-ich qavslarni qamrab oladigan pattern
    _B = r'(?:[^{}]|\{[^{}]*\})*'   # {bir daraja ichida nima bo'lsa ham}

    # 0. Formatlash buyruqlarini ENG AVVAL olib tashlash
    #    (shunda \left → olib tashlash, \le → ≤ muammosi bo'lmaydi)
    _early_remove = (
        'displaystyle', 'textstyle', 'scriptstyle', 'scriptscriptstyle',
        'mathrm', 'mathbf', 'mathit', 'mathcal', 'mathbb', 'mathsf', 'mathtt',
        'boldsymbol', 'pmb', 'text', 'mbox', 'hbox',
        'overline', 'underline', 'widehat', 'widetilde', 'overbrace', 'underbrace',
        'bar', 'hat', 'tilde', 'vec', 'dot', 'ddot', 'dddot', 'breve', 'check',
        'left', 'right', 'big', 'Big', 'bigg', 'Bigg',
        'bigl', 'bigr', 'Bigl', 'Bigr',
        'quad', 'qquad',
        'not',
    )
    for _cmd in sorted(_early_remove, key=len, reverse=True):
        text = re.sub(r'\\' + re.escape(_cmd) + r'(?![a-zA-Z])', '', text)
    # \, \; \: \! → bo'sh joy (early)
    text = re.sub(r'\\[,;:! ]', ' ', text)

    for _pass in range(4):
        # 1. \sqrt[n]{x} → (x)^(1/n)  [frac dan OLDIN qilinishi kerak]
        text = re.sub(
            r'\\sqrt\[(\d+)\]\{(' + _B + r')\}',
            lambda m: f'({m.group(2)})^(1/{m.group(1)})',
            text,
        )
        # \sqrt{x} → √(x)
        text = re.sub(r'\\sqrt\{(' + _B + r')\}', r'√(\1)', text)
        text = re.sub(r'\\sqrt\s', '√', text)

        # 2. \frac, \tfrac, \dfrac, \cfrac → (num)/(den)
        text = re.sub(
            r'\\[dct]?frac\{(' + _B + r')\}\{(' + _B + r')\}',
            lambda m: f'({m.group(1)})/({m.group(2)})',
            text,
        )

        # 3. \binom{n}{k} → C(n,k)
        text = re.sub(
            r'\\binom\{(' + _B + r')\}\{(' + _B + r')\}',
            lambda m: f'C({m.group(1)},{m.group(2)})',
            text,
        )

    # 4. \int_{a}^{b} → ∫[a→b]
    text = re.sub(
        r'\\int_\{(' + _B + r')\}\^\{(' + _B + r')\}',
        lambda m: f'∫[{m.group(1)}→{m.group(2)}]',
        text,
    )
    text = re.sub(
        r'\\int_([^{\\^{\s])\^([^{\\^{\s])',
        lambda m: f'∫[{m.group(1)}→{m.group(2)}]',
        text,
    )
    # \iint, \iiint, \oint (uzunroqlardan boshlab)
    for sym, uni in (('\\iiint', '∭'), ('\\iint', '∬'), ('\\oint', '∮'), ('\\int', '∫')):
        text = text.replace(sym, uni)

    # 5. \sum_{i=0}^{n} → ∑[i=0→n]
    text = re.sub(
        r'\\sum_\{(' + _B + r')\}\^\{(' + _B + r')\}',
        lambda m: f'∑[{m.group(1)}→{m.group(2)}]',
        text,
    )
    text = re.sub(
        r'\\sum_([^{\\^{\s])\^([^{\\^{\s])',
        lambda m: f'∑[{m.group(1)}→{m.group(2)}]',
        text,
    )
    text = text.replace('\\sum', '∑')

    # 6. \prod_{i=0}^{n} → ∏[i=0→n]
    text = re.sub(
        r'\\prod_\{(' + _B + r')\}\^\{(' + _B + r')\}',
        lambda m: f'∏[{m.group(1)}→{m.group(2)}]',
        text,
    )
    text = text.replace('\\prod', '∏')

    # 7. \lim_{x \to 0} → lim[x→0]
    text = re.sub(r'\\lim_\{(' + _B + r')\}', lambda m: f'lim[{m.group(1)}]', text)
    text = text.replace('\\lim', 'lim')

    # 8. \max_{...}, \min_{...}, \sup_{...}, \inf_{...}
    for fn in ('max', 'min', 'sup', 'inf', 'limsup', 'liminf'):
        text = re.sub(
            r'\\' + fn + r'_\{(' + _B + r')\}',
            lambda m, f=fn: f'{f}[{m.group(1)}]',
            text,
        )

    # 9. Yunon harflari: \alpha → α (uzun nomdan boshlab)
    for name in sorted(_GREEK_LETTERS, key=len, reverse=True):
        text = re.sub(r'\\' + re.escape(name) + r'(?![a-zA-Z])', _GREEK_LETTERS[name], text)

    # 10. Matematik funksiyalar: \sin → sin
    for fn in sorted(_MATH_FUNCTIONS, key=len, reverse=True):
        text = re.sub(r'\\' + re.escape(fn) + r'(?![a-zA-Z])', fn, text)

    # 11. Operatorlar (to'liq so'z replacelari — regex kerak emas)
    for cmd, sym in sorted(_MATH_OPERATORS.items(), key=lambda x: len(x[0]), reverse=True):
        text = text.replace(cmd, sym)

    # 12. Superscript: ^{abc} → ⁰¹² yoki oddiy ^abc
    def _sup_block(m: re.Match) -> str:
        inner = m.group(1)
        out = ''
        for c in inner:
            out += c.translate(SUP_DIGITS) if c in SUP_ALLOWED else c
        return out

    text = re.sub(r'\^\{([^{}]*)\}', _sup_block, text)
    text = re.sub(
        r'\^(-?[A-Za-z0-9]+)',
        lambda m: ''.join(c.translate(SUP_DIGITS) if c in SUP_ALLOWED else c
                          for c in m.group(1)),
        text,
    )

    # 13. Subscript: _{abc} → ₀₁₂ yoki oddiy _abc
    def _sub_block(m: re.Match) -> str:
        inner = m.group(1)
        out = ''
        for c in inner:
            out += c.translate(SUB_DIGITS) if c in '0123456789+-=()' else c
        return out

    text = re.sub(r'_\{([^{}]*)\}', _sub_block, text)
    text = re.sub(r'_([0-9])', lambda m: m.group(1).translate(SUB_DIGITS), text)

    # 14. Matritsa muhiti (sodda ko'rinishga aylantirish)
    text = re.sub(
        r'\\begin\{(?:pmatrix|bmatrix|vmatrix|matrix)\}(.*?)\\end\{(?:pmatrix|bmatrix|vmatrix|matrix)\}',
        lambda m: '[' + m.group(1).replace('\\\\', '; ').replace('&', ', ').strip() + ']',
        text,
        flags=re.DOTALL,
    )
    # Qolgan begin/end muhitlarni olib tashlash
    text = re.sub(r'\\begin\{[^}]*\}', '', text)
    text = re.sub(r'\\end\{[^}]*\}', '', text)

    # 15. Qopqichlar ichidagi matnni saqlab qolish
    for _ in range(5):
        text = re.sub(r'\{([^{}]*)\}', r'\1', text)
    text = text.replace('{', '').replace('}', '')

    # Qolgan \\cmd → olib tashlash (step 0 da olib tashlanmaganlar)
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    text = text.replace('\\', '')

    # 17. Probellarni tartibga solish
    text = re.sub(r'[ \t]+', ' ', text).strip()
    return text


def _convert_superscript(text: str) -> str:
    """x^2 -> x²,  x^(n+1) -> x⁽ⁿ⁺¹⁾,  e^(-2x) -> e⁻²ˣ"""
    def paren(m):
        inner = m.group(1)
        if all(c in SUP_ALLOWED for c in inner):
            return inner.translate(SUP_DIGITS)
        return m.group(0)
    text = re.sub(r'\^\(([^()]+)\)', paren, text)

    def simple(m):
        inner = m.group(1)
        if all(c in SUP_ALLOWED for c in inner):
            return inner.translate(SUP_DIGITS)
        return m.group(0)
    text = re.sub(r'\^(-?[A-Za-z0-9]+)', simple, text)
    return text


def _convert_subscript(text: str) -> str:
    """H_2O -> H₂O,  x_(12) -> x₍₁₂₎"""
    def paren(m):
        inner = m.group(1)
        if all(c in '0123456789+-=()' for c in inner):
            return inner.translate(SUB_DIGITS)
        return m.group(0)
    text = re.sub(r'_\(([^()]+)\)', paren, text)
    text = re.sub(r'_([0-9]+)', lambda m: m.group(1).translate(SUB_DIGITS), text)
    return text


def _convert_funcs(text: str) -> str:
    """sqrt(144) -> √144,  pi -> π (faqat alohida so'z)"""
    for name, sym in FUNC_TO_SYMBOL.items():
        pattern = r'(?<![A-Za-z\\])' + re.escape(name) + r'(?![A-Za-z])'
        text = re.sub(pattern, sym, text)
    text = re.sub(r'(√|∛)\(([^()]+)\)', r'\1\2', text)
    return text


def _convert_ascii_ops(text: str) -> str:
    for src in sorted(ASCII_TO_PRETTY, key=len, reverse=True):
        text = text.replace(src, ASCII_TO_PRETTY[src])
    return text


def _strip_latex(text: str) -> str:
    """LaTeX $...$ → oddiy Unicode matn.

    Ishlash tartibi:
      1. pylatexenc bilan urinib ko'riladi
      2. Natijada hali \\ qolsa yoki xato bo'lsa — regex fallback
      3. Ikkala urinish ham muvaffaqiyatsiz bo'lsa — _latex_to_unicode_fallback
    """
    if '\\' not in text and '$' not in text and r'\[' not in text:
        return text

    def _convert_formula(formula: str) -> str:
        if _LATEX is not None:
            try:
                result = _LATEX.latex_to_text(formula)
                # pylatexenc muvaffaqiyatli: agar '\' qolmagan bo'lsa — ishlatamiz
                if '\\' not in result:
                    return result.strip()
            except Exception:
                pass
        # Fallback: o'z konverterimiz
        return _latex_to_unicode_fallback(formula)

    # $$...$$ display math
    text = re.sub(
        r'\$\$(.+?)\$\$',
        lambda m: _convert_formula(m.group(1)),
        text,
        flags=re.DOTALL,
    )
    # $...$ inline math
    text = re.sub(
        r'\$([^$\n]+?)\$',
        lambda m: _convert_formula(m.group(1)),
        text,
    )
    # \[...\] display math
    text = re.sub(
        r'\\\[(.+?)\\\]',
        lambda m: _convert_formula(m.group(1)),
        text,
        flags=re.DOTALL,
    )
    # \(...\) inline math
    text = re.sub(
        r'\\\((.+?)\\\)',
        lambda m: _convert_formula(m.group(1)),
        text,
        flags=re.DOTALL,
    )

    # Hali ham \\ qolgan bo'lsa — to'liq fallback
    if '\\' in text:
        text = _latex_to_unicode_fallback(text)

    return text


def _split_on_latex(text: str) -> list[tuple[str, bool]]:
    """Matnni LaTeX ($...$, $$...$$) va oddiy qismlarga ajratadi.
    Qaytaradi: [(qism, is_latex_block), ...]
    """
    parts: list[tuple[str, bool]] = []
    pos = 0
    for m in re.finditer(r'\$\$[\s\S]+?\$\$|\$[^$\n]+?\$', text):
        if m.start() > pos:
            parts.append((text[pos:m.start()], False))
        parts.append((m.group(0), True))
        pos = m.end()
    if pos < len(text):
        parts.append((text[pos:], False))
    return parts


def _apply_ascii_conversions(text: str) -> str:
    """LaTeX himoyasiz ASCII → Unicode konversiyalari."""
    text = _convert_funcs(text)
    text = _convert_superscript(text)
    text = _convert_subscript(text)
    text = _convert_ascii_ops(text)
    return text


def _clean_common(text: str) -> str:
    """Har ikki normalizatsiya uchun umumiy yakuniy tozalash."""
    for src, dst in _QUOTES.items():
        text = text.replace(src, dst)
    text = ''.join(
        ch for ch in text
        if ch in '\n\t' or unicodedata.category(ch)[0] != 'C'
    )
    text = re.sub(r'[ \t]+', ' ', text).strip()
    return text


def normalize_for_hemis(text: str) -> str:
    """Matnni HEMIS/HTML ko'rsatish uchun moslab tozalaydi.

    LaTeX $...$ bloklari KaTeX orqali renderlanishi uchun SAQLANADI.
    Faqat LaTeX tashqarisidagi ASCII yozuvlar Unicode ga aylantiriladi:
      sqrt(x) → √x,  x^2 → x²,  >= → ≥  (ammo  $x^2$ → $x^2$ o'zgarishsiz).
    """
    if not text:
        return ''
    text = html_lib.unescape(text)
    text = unicodedata.normalize('NFC', text)

    if '$' in text:
        parts = _split_on_latex(text)
        processed = [
            chunk if is_latex else _apply_ascii_conversions(chunk)
            for chunk, is_latex in parts
        ]
        text = ''.join(processed)
    else:
        text = _apply_ascii_conversions(text)

    return _clean_common(text)


def normalize_for_hemis_txt(text: str) -> str:
    """HEMIS .txt eksport uchun normalizatsiya.

    LaTeX $...$ → Unicode belgilarga aylantiriladi:
      $\\sqrt{x}$ → √(x),  $\\frac{a}{b}$ → (a)/(b),  $x^2$ → x²
      $\\int_0^1 f dx$ → ∫[0→1] f dx
    HEMIS matn formatida LaTeX ko'rsatilmasligi sababli.
    """
    if not text:
        return ''
    text = html_lib.unescape(text)
    text = _strip_latex(text)
    text = unicodedata.normalize('NFC', text)
    text = _apply_ascii_conversions(text)
    return _clean_common(text)


def normalize_for_html(text: str) -> str:
    """XML/HTML eksport uchun: avval HEMIS normalizatsiya, keyin HTML escape."""
    return html_lib.escape(normalize_for_hemis(text), quote=False)
