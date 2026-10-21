"""
Draft guard for first-contact messages to small businesses.

A draft passes only if it: ends with a question, has no link, no long dash (U+2014, U+2013),
no pitch or review word (matched as whole words, so "KI" never blocks "Kiez"), stays under the
limit, and quotes a detail that really is in the source text it was written from.

Stdlib only.
"""
import re
import unicodedata

PITCH = re.compile(r"\b(angebot\w*|preis\w*|kostenlos|gratis|rabatt|ki|ai|automatisier\w*|automation|"
                   r"automate\w*|software|app|offer\w*|price\w*|free|discount|bewertung\w*|rezension\w*|"
                   r"review\w*|google|sterne?)\b", re.I)
LINK = re.compile(r"https?://|www\.|\b\S+\.(de|com|net|io|org)\b", re.I)


def fold(s: str) -> str:
    s = (s or "").lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = unicodedata.normalize("NFKD", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", "".join(c for c in s if not unicodedata.combining(c)))
    return re.sub(r"\s+", " ", s).strip()




def guard(text: str, quoted: str, source: str, limit: int = 300) -> str | None:
    """Why a draft is refused, or None. Whole-word pitch match: 'KI' never blocks 'Kiez'."""
    if not text.strip().endswith("?"):
        return "does not end with a question"
    if "—" in text or "–" in text:
        return "long dash"
    if LINK.search(text):
        return "contains a link"
    m = PITCH.search(text)
    if m:
        return f"pitch or review word: {m.group(0)}"
    if len(text) > limit:
        return f"{len(text)} chars, limit {limit}"
    if not quoted or fold(quoted) not in fold(source):
        return "quoted detail is not in the source"
    return None


DM_RULES = """You write ONE short first Instagram direct message from Swaraj, who lives in Neukölln,
to a small local business. German, informal "ihr" is fine for cafés, salons and shops.
Rules, all hard:
- Mention ONE specific thing from the SOURCE (a line from their bio, a recent post, or a job ad).
  Put the exact words you relied on, copied character for character from SOURCE, in quoted_detail.
- Never mention reviews, ratings, complaints or anything negative about them.
- No offer, no pitch, no link, no price, no product names, no words like KI, AI, App, Software,
  Automatisierung, Angebot, kostenlos.
- End with one easy yes-or-no question about how they handle that thing today
  (bookings, orders, phone, messages, staff, online presence). The message ends with "?".
- Max 280 characters. Plain, warm, neighbourly. No long dashes (U+2014, U+2013). No emojis.
- Sign as "Swaraj" only if it fits in the limit."""

LI_RULES = """You write ONE LinkedIn connection note from Swaraj Yadav, Berlin, to the person named.
Language: the LANGUAGE given. Rules, all hard:
- Refer to their open job posting or recent announcement named in SOURCE. Put the exact words you relied on, copied
  character for character from SOURCE, in quoted_detail.
- No pitch, no offer, no link, no price. Do not use the words AI, KI, automation,
  Automatisierung, software, app, offer, Angebot, free, kostenlos.
- End with one easy yes-or-no question about how that work is done today. Ends with "?".
- Max 280 characters. No long dashes (U+2014, U+2013). No emojis."""




if __name__ == "__main__":
    src = "Frische Kekse aus dem Kiez, Termine nur per DM"
    assert guard("Eure Kekse aus dem Kiez sehen gut aus. Laufen Termine nur per DM?", "Termine nur per DM", src) is None
    assert "pitch" in guard("Ich baue KI für euch. Interesse?", "Kiez", src)
    assert "link" in guard("Schaut auf www.x.de, okay?", "Kiez", src)
    assert "dash" in guard("Hallo \u2014 kurz?", "Kiez", src)
    assert "source" in guard("Hallo, alles gut?", "erfunden", src)
    print("ok guard")
