#!/usr/bin/env python3
"""
تبدیل متن «رساله آموزشی» (فایل متنی استخراج‌شده از EPUB سایت leader.ir)
به داده‌ی اپ:  data/lessons.json

اجرا:
    python3 tools/build_data.py <مسیر فایل txt> [مسیر خروجی]

ساختار:
  - بخش اول (درس ۱ تا ۷۷): با عنوان‌های «درس N: ...» جدا می‌شود.
  - بخش دوم (معاملات و ...): در متن استخراج‌شده عنوان درس‌ها حذف شده؛
    مرزها از جدول SECTIONS_B (بر اساس موضوع) گرفته می‌شود. اگر فایل EPUB
    اصلی را دارید و فهرست دقیق درس‌ها را می‌خواهید، فقط همین جدول را عوض کنید.
"""
import html
import json
import re
import sys
from pathlib import Path

_args = [a for a in sys.argv[1:] if not a.startswith("--")]
SRC = Path(_args[0]) if _args else Path("booklet_137__Leader_ir__epub.txt")
OUT = Path(_args[1]) if len(_args) > 1 else Path(__file__).resolve().parent.parent / "data" / "lessons.json"

lines = SRC.read_text(encoding="utf-8").split("\n")
# بخش لاگ انتهای فایل را حذف کن
for i, l in enumerate(lines):
    if l.startswith("# Log: Leader"):
        lines = lines[:i]
        break
N = len(lines)

FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


MI = re.compile(
    r"(?<![ء-ی])(ن?می)(?=(?:شود|شوند|کند|کنند|توان|تواند|توانند|باشد|باشند|رسد|رسند|گیرد|گیرند|دهد|دهند|"
    r"گویند|گوید|خورد|خواهد|دانند|داند|بیند|آید|آیند|کرد|شد|شدند|بایست|توانست|پذیرد|پذیرند|افتد|ماند|مانند|"
    r"گذارد|گذارند|خواند|خوانند|رود|روند|نویسد|ساز|سازد|سازند|فروش|خرد|خرند|گردد|گردند|نماید|نمایند|"
    r"تواند|فرستد|کشد|کشند|زند|زنند|پرداز|پردازد|یابد|یابند|دارد|دارند|داشت|ریزد|ریزند|بخشد|بخشند))"
)


def fa(s):
    """ارقام را فقط در متن (نه داخل تگ‌ها) فارسی کن."""
    return re.sub(r"(<[^>]+>)|([^<]+)", lambda m: m.group(1) or MI.sub("\\1\u200c", m.group(2).translate(FA)), s)


def clean_title(t):
    t = t.replace("*", "")
    t = re.sub(r"\s+", " ", t).strip()
    return t


# ---------------------------------------------------------------- بخش اول
LESSON_RE = re.compile(r"^\**\s*درس\s*([0-9]+)\s*[:：]?\s*(.*)$")
ORD = {"دوم": 2, "سوم": 3}

starts = {}  # شماره درس -> (شماره خط 0-based, عنوان)
for i, l in enumerate(lines):
    s = l.strip()
    m = LESSON_RE.match(s)
    if m and i < 5700:
        starts[int(m.group(1))] = (i, clean_title(m.group(2)))
        continue
    m2 = re.match(r"^درس\s+(دوم|سوم)\s*\((.*)\)\s*$", s)
    if m2 and i < 5700:
        starts[ORD[m2.group(1)]] = (i, clean_title(m2.group(2)))

NUMQ = re.compile(r"^\s*\**\s*\d+\s*[\.\-\)]")


def after_questions(i):
    """اولین خط بعد از بلوک پرسش‌های شماره‌دار که از i شروع می‌شود."""
    j = i
    while j < N and (not lines[j].strip() or NUMQ.match(lines[j])):
        j += 1
    return j


# درس‌های ۱، ۴ و ۷ عنوان ندارند (متن استخراج‌شده)
starts[1] = (0, "مقدمه، تکلیف و تقلید (۱)")
tam = [i for i, l in enumerate(lines) if re.match(r"^\**\s*تمرین", l.strip()) and i < 5700]
starts[4] = (after_questions(tam[2] + 1), "تقلید (۴)")  # پایان تمرین درس ۳
starts[7] = (after_questions(tam[5] + 1), "انواع نجاسات (۱)")  # پایان تمرین درس ۶

lesson_nums = sorted(starts)
GROUPS_A = [
    (1, 26, "احکام تقلید و طهارت"),
    (27, 57, "نماز"),
    (58, 65, "روزه"),
    (66, 77, "خمس، انفال، جهاد و امر به معروف"),
]

# بخش دوم: بر اساس موضوع.  (عبارت جست‌وجو برای مرز | عنوان | گروه)
GROUP_M1 = "معاملات حرام"
GROUP_M2 = "احکام عمومی معاملات"
GROUP_M3 = "عقود و معاملات خاص"
GROUP_M4 = "مسائل متفرقه"


def find_after(pattern, start=0):
    r = re.compile(pattern)
    for i in range(start, N):
        if r.search(lines[i]):
            return i
    raise SystemExit("مرز پیدا نشد: " + pattern)


b_first = find_after(r"^\**معاملات\[1\] از نظر")
b_riba = find_after(r"ربا از گناهان", 7077)
# شماره خط‌ها 1-based در گزارش بررسی؛ اینجا 0-based
SECTIONS_B = [
    (b_first, "کلیات معاملات و انواع معاملات حرام", GROUP_M1),
    (5649, "معامله‌ی عین نجس (میته، خون، خوک، شراب، متنجس)", GROUP_M1),
    (5815, "آلات قمار، لهو و سلاح", GROUP_M1),
    (5967, "مالیت، تدلیس و مسائل متفرقه", GROUP_M1),
    (6028, "کم‌فروشی (تطفیف)", GROUP_M1),
    (6104, "کهانت و سحر", GROUP_M1),
    (6151, "کسب با چیزِ مُضِلّ", GROUP_M1),
    (6182, "رشوه، هدیه و معامله‌ی محاباتی", GROUP_M1),
    (6315, "سبّ مؤمن", GROUP_M1),
    (6355, "غیبت", GROUP_M1),
    (6536, "دروغ و نمیمه", GROUP_M1),
    (6607, "قمار", GROUP_M1),
    (6672, "غش و نَجْش", GROUP_M1),
    (6788, "غنا و موسیقی", GROUP_M1),
    (7062, "رقص، مجسمه‌سازی و کمک به ظالم", GROUP_M1),
    (b_riba, "ربا", GROUP_M1),
    (7225, "شرایط معامله و عاقدان", GROUP_M2),
    (7304, "معامله‌ی فضولی و مال مشکوک", GROUP_M2),
    (7384, "اولیای تصرف و ممنوعان از تصرف", GROUP_M2),
    (7530, "معامله‌ی نقد و نسیه", GROUP_M2),
    (7647, "حق شفعه", GROUP_M2),
    (7735, "خیارات (۱)", GROUP_M2),
    (7877, "خیارات (۲)", GROUP_M2),
    (7945, "خیارات (۳)", GROUP_M2),
    (7997, "قبض و تسلیم", GROUP_M2),
    (8047, "اقاله", GROUP_M2),
    (8099, "اجاره", GROUP_M3),
    (8215, "فسخ و بطلان اجاره", GROUP_M3),
    (8318, "شرکت", GROUP_M3),
    (8494, "رهن", GROUP_M3),
    (8810, "وکالت", GROUP_M3),
    (8909, "وقف", GROUP_M3),
    (9336, "صدقه", GROUP_M3),
    (9409, "وصیت", GROUP_M3),
    (9700, "نذر", GROUP_M3),
    (9799, "قسم و عهد", GROUP_M3),
    (9858, "مضاربه", GROUP_M3),
    (10088, "قرض", GROUP_M3),
    (10183, "دین", GROUP_M3),
    (10281, "ودیعه", GROUP_M3),
    (10436, "عاریه", GROUP_M3),
    (10527, "پوشش و نگاه کردن", GROUP_M4),
    (10621, "نگاه به نامحرم و عورت", GROUP_M4),
    (10679, "مسائل پزشکی: جلوگیری از بارداری", GROUP_M4),
    (10749, "تلقیح مصنوعی", GROUP_M4),
    (10796, "تشریح، پیوند و مرگ مغزی", GROUP_M4),
    (10850, "نگاه و لمس در درمان", GROUP_M4),
    (10874, "تعلیم و تعلم", GROUP_M4),
    (10900, "حقوق مؤلف و چاپ و نشر", GROUP_M4),
    (10940, "مراسم عزاداری و اعیاد", GROUP_M4),
]

TITLE_FIX = {
    2: "تقلید (۲)", 3: "تقلید (۳)", 5: "آب‌ها", 24: "نماز میت و طریقه‌ی خواندن آن (۳)",
    28: "لباس نمازگزار: مقدار پوشش در نماز (۱)", 32: "محرمات مسجد (۱)", 38: "واجبات نماز (۱)",
    52: "نماز مسافر (۲)", 69: "مؤونه در خمس (۲)", 68: "مؤونه در خمس (۱)", 15: "شرایط وضو (۲)",
    9: "چگونگی اثبات نجاست وسایل پاک", 70: "نمونه‌هایی از موارد انطباق مؤونه",
    47: "ترجمه‌ی سوره‌ی حمد و توحید", 61: "فرو بردن سر در آب، بقا بر جنابت، حیض و نفاس تا اذان صبح",
    41: "جهر و اخفات (بلند و آهسته خواندن) در قرائت",
}
for _n, _t in TITLE_FIX.items():
    if _n in starts:
        starts[_n] = (starts[_n][0], _t)

# ---------------------------------------------------------------- بخش‌بندی نهایی
sections = []  # dict(id, num, title, group, start, end)
for k, n in enumerate(lesson_nums):
    s, title = starts[n]
    e = starts[lesson_nums[k + 1]][0] if k + 1 < len(lesson_nums) else b_first
    grp = next(g for a, b, g in GROUPS_A if a <= n <= b)
    sections.append(dict(id=f"l{n}", num=n, title=title, group=grp, start=s, end=e, part="A"))

for k, (s, title, grp) in enumerate(SECTIONS_B):
    e = SECTIONS_B[k + 1][0] if k + 1 < len(SECTIONS_B) else N
    sections.append(dict(id=f"m{k + 1}", num=k + 1, title=title, group=grp, start=s, end=e, part="B"))

# ---------------------------------------------------------------- تبدیل متن به HTML
FN_LINK = re.compile(r"\[\[(\d+)\]\]\([^)]*\)")
FN_LINK2 = re.compile(r"\[(\d+)\]\(https?://[^)]*\)")
FN_DEF = re.compile(r"^\[(\d+)\]\s*\.?\s*(.*)$")
BOLD = re.compile(r"\*\*(.+?)\*\*")
NOTE_LABELS = {"توجه", "نکته", "تذکر", "توضیح"}


LEAD_LINK = re.compile(r"\[([^\[\]]*(?:\[[^\]]*\])?[^\[\]]*)\]+\((?:https?://)[^)]*?#_ftn(?:ref)?(\d+)\)")


def inline(s):
    s = s.replace("****", "")
    s = LEAD_LINK.sub(lambda m: "[" + (re.findall(r"\d+", m.group(1)) or [m.group(2)])[0] + "]", s)
    s = FN_LINK.sub(r"[\1]", s)
    s = FN_LINK2.sub(r"[\1]", s)
    if s.count("**") % 2:
        s = s.replace("**", "")
    s = html.escape(s, quote=False)
    s = BOLD.sub(r"<b>\1</b>", s)
    s = s.replace("*", "")
    s = re.sub(r"\[(\d{1,2})\]", r'<sup class="fr">\1</sup>', s)
    return s.strip()


def _norm_bold(s):
    t = s.strip().replace("****", "")
    t = re.sub(r"\*\*\s+\*\*", " ", t)  # «** **» بین دو تکه‌ی بولد
    t = re.sub(r"\*{3,}$", "**", t)         # «:***» در انتهای خط
    t = re.sub(r"\*\*\s*([:：.]?)\s*$", r"\1**", t) if t.endswith("**") else t
    t = re.sub(r"^(\*\*[^*]+?)\*\*\s*[:：.]\s*$", r"\1**", t)  # «**عنوان**:»
    return t


def is_bold_only(s):
    t = _norm_bold(s)
    return bool(re.fullmatch(r"\*\*[^*]+\*\*", t)) and len(t) <= 100


def bold_text(s):
    return clean_title(_norm_bold(s))


def table_html(caption, header, rows):
    out = ['<div class="tbl"><table>']
    if caption:
        out.append(f"<caption>{html.escape(caption)}</caption>")
    out.append("<thead><tr>" + "".join(f"<th>{html.escape(h)}</th>" for h in header) + "</tr></thead><tbody>")
    for r in rows:
        r = list(r) + [""] * (len(header) - len(r))
        out.append("<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def consume_table(L, i):
    """جدول‌های تخت‌شده‌ی متن را دوباره جدول می‌کند. (html, اندیس بعدی) یا None."""
    s = L[i].strip().replace("****", "")
    nxt = [x.strip().replace("****", "") for x in L[i + 1:i + 14] if x.strip()]
    # جدول ۱: مثال‌های ربا
    if s.startswith("**جدول مثال"):
        j = i + 1
        cells = []
        while j < len(L):
            t = L[j].strip()
            if re.match(r"^\d+\s*[\.\)]\s", t):
                break
            if t:
                cells.append(t.replace("**", "").replace("****", ""))
            j += 1
        hdr = cells[:7]
        body = cells[7:]
        rows, cur = [], None
        for c in body:
            if re.fullmatch(r"\d+", c):
                cur = [c]
                rows.append(cur)
            elif cur is not None:
                cur.append(c)
        header = ["ردیف", "جنس فروخته‌شده", "جنس در مقابل آن", "نحوه‌ی اندازه‌گیری", "توضیحات"]
        return table_html("مثال‌های معامله‌ی ربوی", header, rows), j
    # جدول ۲: اولیای تصرف (دست‌نویس)
    if s.startswith("**جدول اولیای تصرف"):
        j = i + 1
        while j < len(L) and not L[j].strip().startswith("آنچه بیشتر"):
            j += 1
        header = ["شخص", "اولویت ۱", "اولویت ۲", "اولویت ۳", "اولویت ۴", "اولویت ۵"]
        rows = [
            ["نابالغ", "پدر یا جد پدری", "قیّمی که پدر یا جد تعیین کرده", "حاکم شرع", "مؤمنین عادل", "مؤمنین فاسق"],
            ["سفیه و دیوانه (با حال سفاهت بالغ شده)", "پدر یا جد پدری", "قیّمی که پدر یا جد تعیین کرده", "حاکم شرع", "مؤمنین عادل", "مؤمنین فاسق"],
            ["سفیه و دیوانه (اول بلوغ بوده، بعد سفاهت)", "حاکم شرع"],
            ["ورشکسته", "حاکم شرع"],
        ]
        return table_html("اولیای تصرف", header, rows), j
    # جدول ۳: خیار غبن
    if s == "**ردیف**" and nxt and nxt[0] == "**قیمت روز معامله**":
        j = i
        cells = []
        while j < len(L):
            t = L[j].strip()
            if t and (t.startswith("**") or len(t) <= 40) and not re.match(r"^\d+\s*[\.\)]\s", t):
                cells.append(t.replace("**", ""))
                j += 1
            elif not t:
                j += 1
            else:
                break
        header = cells[:5]
        rows, cur = [], None
        for c in cells[5:]:
            if re.fullmatch(r"\d+", c):
                cur = [c]
                rows.append(cur)
            elif cur is not None:
                cur.append(c)
        return table_html("نمونه‌هایی از خیار غبن", header, rows), j
    # جدول ۴: مثال‌های وقف
    if s == "**شماره**" and nxt and nxt[0] == "**مثال**":
        j = i + 4  # شماره، مثال، (خالی)، حکم
        rows, cur, mode = [], None, "ex"
        while j < len(L):
            t = L[j].strip()
            if not t:
                j += 1
                continue
            if not t.startswith("**"):
                break
            c = t.replace("****", "").replace("**", "").strip()
            if t == "****":
                mode = "rule"
            elif re.fullmatch(r"\d+", c):
                cur = [c, "", ""]
                rows.append(cur)
                mode = "ex"
            elif cur is not None:
                idx = 1 if mode == "ex" else 2
                cur[idx] = (cur[idx] + " " + c).strip()
            j += 1
        return table_html("مثال‌های وقف و مصرف آن", ["شماره", "مثال", "حکم"], rows), j
    return None


PLAIN_HEADS = []


def convert(sec):
    L = lines[sec["start"]:sec["end"]]
    blocks = []  # لیست رشته‌ی HTML
    note = None  # (label, [blocks])
    ex_pending = False
    items = []  # آیتم‌های لیست جاری: ("ul"|"ol", text, num)
    fns = []

    def emit(h):
        nonlocal note
        if note is not None:
            lab = note[0]
            note = None
            blocks.append(f'<aside class="note"><b class="nl">{html.escape(lab)}</b>{h}</aside>')
        else:
            blocks.append(h)

    def flush_items():
        nonlocal items
        if not items:
            return
        kind = items[0][0]
        if kind == "ol":
            qn = sum(1 for _, t, _ in items if t.rstrip().rstrip("*").endswith("؟"))
            if ex_pending or (len(items) >= 3 and qn / len(items) >= 0.6):
                inner = "".join(f'<div class="ni"><span class="n">{n}</span><div>{inline(t)}</div></div>' for _, t, n in items)
                emit(f'<section class="ex"><h4>تمرین و پرسش</h4>{inner}</section>')
            else:
                inner = "".join(f'<div class="ni"><span class="n">{n}</span><div>{inline(t)}</div></div>' for _, t, n in items)
                emit(f'<div class="ol">{inner}</div>')
        else:
            inner = "".join(f"<li>{inline(t)}</li>" for _, t, _ in items)
            emit(f"<ul>{inner}</ul>")
        items = []

    def flush_fns():
        nonlocal fns
        if fns:
            inner = "".join(f'<p><span class="fnn">{n}</span>{inline(t)}</p>' for n, t in fns)
            emit(f'<div class="fns">{inner}</div>')
            fns = []

    def close_note():
        nonlocal note
        flush_items()
        flush_fns()
        if note is not None:
            lab, inner = note
            note = None
            if inner:
                blocks.append(f'<aside class="note"><b class="nl">{html.escape(lab)}</b>{"".join(inner)}</aside>')
            else:
                blocks.append(f'<p class="lab">{html.escape(lab)}</p>')

    i = 0
    # خط عنوان درس را از متن حذف کن
    if sec["part"] == "A" and sec["num"] not in (1, 4, 7):
        i = 1
    while i < len(L):
        raw = L[i]
        s = raw.strip()
        s = re.sub(r"^(\d+)\*\*\s*\.?\s*(.+?)\*\*$", r"**\1. \2**", s)
        if not s:
            i += 1
            continue
        if re.fullmatch(r"-{3,}", s):
            flush_items()
            i += 1
            continue
        # جدول‌ها
        if sec["part"] == "B":
            r = consume_table(L, i)
            if r:
                flush_items(); flush_fns()
                emit(r[0])
                i = r[1]
                continue
        # پاورقی
        m = FN_DEF.match(FN_LINK.sub(r"[\1]", FN_LINK2.sub(r"[\1]", s)))
        if m and (s.startswith("[") or s.startswith("[[")):
            flush_items()
            fns.append((m.group(1), m.group(2)))
            i += 1
            continue
        flush_fns()
        # عنوان
        if is_bold_only(s):
            t = bold_text(s)
            flush_items()
            if t == "تمرین":
                close_note()
                ex_pending = True
                i += 1
                continue
            if t in NOTE_LABELS:
                close_note()
                note = (t, [])
                i += 1
                continue
            close_note()
            ex_pending = False
            lvl = "h3"
            emit(f"<{lvl}>{inline('**' + t + '**').replace('<b>', '').replace('</b>', '')}</{lvl}>")
            i += 1
            continue
        if re.fullmatch(r"تمرین", s):
            flush_items(); close_note()
            ex_pending = True
            i += 1
            continue
        # فهرست‌ها
        m = re.match(r"^(\d+)\s*[\.\)\-]\s*(.*)$", s)
        if m and m.group(2):
            if items and items[0][0] != "ol":
                flush_items()
            items.append(("ol", m.group(2), m.group(1)))
            i += 1
            continue
        m = re.match(r"^[-•]\s*(?:-\s*)?(.+)$", s)
        if m:
            if items and items[0][0] != "ul":
                flush_items()
            items.append(("ul", m.group(1), ""))
            i += 1
            continue
        flush_items()
        if ex_pending:
            ex_pending = False
        # سرفصل ساده (بدون بولد در متن مبدأ): خط کوتاه، تنها، بدون نقطه‌گذاری پایانی
        prev_blank = i == 0 or not L[i - 1].strip()
        nxt_nonblank = next((x for x in L[i + 1:i + 3] if x.strip()), "")
        if (prev_blank and nxt_nonblank and 2 <= len(s) <= 42
                and not re.search(r"[\.،؛!؟,:：\"”»*]", s)
                and "(" not in s.replace("(1)", "")
                and not re.match(r"^(?:الف|ب|ج|د|ه|ﻫ|و|ز|\d+)\s*[\)\.\-ـ]", s)
                and not re.match(r"^(مثال|توضیح|سؤال|سوال|جواب|پاسخ|تعریف|نکته|توجه|مسئله|فرع)\b", s)
                and not s.startswith(("[", "(", "-", "•"))):
            close_note()
            PLAIN_HEADS.append((sec["id"], s))
            emit(f"<h3>{inline(s.rstrip(':：').strip())}</h3>")
            i += 1
            continue
        # پاراگراف
        emit(f"<p>{inline(s)}</p>")
        i += 1
    close_note()
    flush_items()
    flush_fns()
    # سرِ بخش تمرین ممکن است بدون ol بماند؛ مهم نیست
    return [fa(b) for b in blocks]


out_sections = []
for sec in sections:
    blocks = convert(sec)
    out_sections.append(
        dict(
            id=sec["id"],
            n=sec["num"],
            part=sec["part"],
            title=fa(sec["title"]),
            group=sec["group"],
            blocks=blocks,
        )
    )

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"sections": out_sections}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

tot = sum(len(b) for s in out_sections for b in s["blocks"])
if "--heads" in sys.argv:
    for sid, t in PLAIN_HEADS:
        print("HEAD", sid, t)
print(f"{len(out_sections)} بخش، {sum(len(s['blocks']) for s in out_sections)} بلوک، {tot/1024:.0f} KB →", OUT)
for s in out_sections:
    print(f"{s['id']:>5} | {len(s['blocks']):4d} بلوک | {s['title']}")
