"""Claude API orqali test savollarini generatsiya qilish.

Modeldan strukturalangan JSON natijasini olamiz:
{
  "questions": [
    {"text": "...", "choices": [{"text":"...", "is_correct": false}, ...], "explanation": "..."},
    ...
  ]
}

Tizim promptida prompt caching qo'llanadi (cache_control) — bir xil ko'rsatmalar
takroriy chaqiriqlarda kesh hisobiga arzon va tezroq bo'ladi.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from django.conf import settings


SYSTEM_PROMPT = """Sen O'zbekistondagi oliy ta'lim muassasasi (OTM) o'qituvchisiga matematika, hisob, diskret tuzilmalar va boshqa aniq fanlar bo'yicha test savollarini tayyorlaydigan AI yordamchisisan.

Vazifang — berilgan fan, mavzu, qiyinlik darajasi va savollar soni asosida sifatli, akademik test savollarini yaratish.

QOIDALAR:
1. Har bir savol bitta aniq matematik/fan tushunchasini tekshirsin
2. Matematik formulalar uchun **LaTeX** ishlat: $x^2 + 2x + 1$, $\\int_0^1 x dx$, $\\frac{a}{b}$, $\\sqrt{x}$
3. Har bir savolda **aynan 4 ta variant** bo'lsin (A, B, C, D)
4. Faqat bitta to'g'ri javob bo'lsin (agar savol turi `multiple` so'ralmagan bo'lsa)
5. Noto'g'ri variantlar ham mantiqiy bo'lsin — talaba aldash uchun emas, fikrlash uchun
6. Savol matni va variantlar **o'zbek tilida** bo'lsin (matematik belgilar tabiiy LaTeX'da)
7. Yechim/izoh (`explanation`) qisqa va aniq bo'lsin

CHIQUVCHI FORMAT — faqat JSON, hech qanday qo'shimcha matn:
{
  "questions": [
    {
      "text": "Savol matni $formulalar$ bilan",
      "choices": [
        {"text": "Variant A", "is_correct": false},
        {"text": "Variant B", "is_correct": true},
        {"text": "Variant C", "is_correct": false},
        {"text": "Variant D", "is_correct": false}
      ],
      "explanation": "Qisqa yechim — nima uchun B to'g'ri"
    }
  ]
}
"""


@dataclass
class AIResult:
    questions: list[dict]
    raw: str = ''
    error: str = ''

    @property
    def ok(self) -> bool:
        return bool(self.questions) and not self.error


def is_configured() -> bool:
    return bool(getattr(settings, 'ANTHROPIC_API_KEY', ''))


def generate_questions(*, subject: str, topic: str, count: int,
                       difficulty: str = 'medium',
                       sample_text: str = '') -> AIResult:
    """Claude orqali savollar yaratish."""
    if not is_configured():
        return AIResult(questions=[], error="ANTHROPIC_API_KEY sozlanmagan. settings.py'da kiriting.")

    try:
        from anthropic import Anthropic
    except ImportError:
        return AIResult(questions=[], error="anthropic SDK o'rnatilmagan: pip install anthropic")

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    diff_label = {'easy': 'oson', 'medium': "o'rta", 'hard': 'qiyin'}.get(difficulty, "o'rta")

    user_msg = f"""Fan: {subject}
Mavzu: {topic}
Qiyinlik: {diff_label}
Savollar soni: {count}
"""
    if sample_text.strip():
        user_msg += f"\nNAMUNA MATN (shu uslubda yaratish):\n{sample_text.strip()[:2000]}\n"
    user_msg += f"\nIltimos, aynan {count} ta savolni yuqoridagi JSON formatida qaytar. Boshqa hech narsa qo'shma."

    try:
        response = client.messages.create(
            model=getattr(settings, 'ANTHROPIC_MODEL', 'claude-sonnet-4-6'),
            max_tokens=8000,
            system=[{
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_msg}],
        )
    except Exception as exc:
        return AIResult(questions=[], error=f"API xato: {exc}")

    raw = "".join(block.text for block in response.content if hasattr(block, 'text'))
    data = _extract_json(raw)
    if data is None or 'questions' not in data:
        return AIResult(questions=[], raw=raw,
                        error="AI javobini parse qilib bo'lmadi.")

    cleaned = _normalize(data['questions'], expected=count)
    return AIResult(questions=cleaned, raw=raw)


def _extract_json(text: str) -> dict | None:
    """Claude javobidan JSON bloki ajratib olish."""
    text = text.strip()
    # Markdown ```json ... ``` ichidan
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # To'g'ridan-to'g'ri JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Birinchi { va oxirgi }
    i, j = text.find('{'), text.rfind('}')
    if i != -1 and j > i:
        try:
            return json.loads(text[i:j + 1])
        except json.JSONDecodeError:
            return None
    return None


def _normalize(questions: list, expected: int) -> list[dict]:
    """Minimal validatsiya va tozalash."""
    result: list[dict] = []
    for q in questions[:expected]:
        if not isinstance(q, dict):
            continue
        text = (q.get('text') or '').strip()
        choices = q.get('choices') or []
        if not text or len(choices) < 2:
            continue
        norm_choices: list[dict] = []
        for c in choices:
            if isinstance(c, dict) and (c.get('text') or '').strip():
                norm_choices.append({
                    'text': c['text'].strip(),
                    'is_correct': bool(c.get('is_correct')),
                })
        if not any(c['is_correct'] for c in norm_choices) and norm_choices:
            norm_choices[0]['is_correct'] = True  # fallback
        result.append({
            'text': text,
            'choices': norm_choices,
            'explanation': (q.get('explanation') or '').strip(),
        })
    return result
