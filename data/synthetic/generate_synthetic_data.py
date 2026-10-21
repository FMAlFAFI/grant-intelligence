"""Generate a SYNTHETIC grant dataset for the grant-intelligence project.

Everything produced here is invented: names, titles, scores, papers and DOIs.
Run:  python generate_synthetic_data.py --out synthetic-data --seed 42
Needs: python-docx
"""
import argparse
import csv
import random
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, RGBColor

BANNER_EN = "SYNTHETIC DATA - FOR TESTING ONLY - NOT REAL RECORDS"
BANNER_AR = "بيانات اصطناعية لأغراض الاختبار فقط - ليست سجلات حقيقية"

PRIORITIES = {
    1: ("National Security", "الأمن الوطني"),
    2: ("Cybercrimes and Financial Crimes", "الجرائم السيبرانية والجرائم المالية"),
    3: ("AI and Emerging Technologies", "الذكاء الاصطناعي والتقنيات الناشئة"),
    4: ("Transnational Security Threats", "التهديدات الأمنية العابرة للحدود"),
    5: ("Narcotics and Psychotropic Substances", "المخدرات والمؤثرات العقلية"),
}

# Topic banks: (english topic, arabic topic, english keywords, arabic keywords)
TOPICS = {
    1: [
        ("critical infrastructure protection against coordinated attacks", "حماية البنية التحتية الحيوية من الهجمات المنسقة",
         ["critical infrastructure", "risk assessment", "resilience"], ["البنية التحتية الحيوية", "تقييم المخاطر", "المرونة"]),
        ("early warning indicators of violent extremism among youth", "مؤشرات الإنذار المبكر للتطرف العنيف لدى الشباب",
         ["extremism", "early warning", "youth"], ["التطرف", "الإنذار المبكر", "الشباب"]),
        ("crisis management capacity in public security agencies", "قدرات إدارة الأزمات في الأجهزة الأمنية",
         ["crisis management", "emergency response", "security agencies"], ["إدارة الأزمات", "الاستجابة للطوارئ", "الأجهزة الأمنية"]),
        ("community policing and public trust in security services", "الشرطة المجتمعية وثقة الجمهور في الأجهزة الأمنية",
         ["community policing", "public trust", "social cohesion"], ["الشرطة المجتمعية", "ثقة الجمهور", "التماسك الاجتماعي"]),
        ("protection of national borders and strategic facilities", "تأمين الحدود الوطنية والمنشآت الاستراتيجية",
         ["border security", "strategic facilities", "surveillance"], ["أمن الحدود", "المنشآت الاستراتيجية", "المراقبة"]),
    ],
    2: [
        ("detection of money laundering in digital banking transactions", "كشف غسل الأموال في المعاملات المصرفية الرقمية",
         ["money laundering", "banking fraud", "transaction monitoring"], ["غسل الأموال", "الاحتيال المصرفي", "مراقبة المعاملات"]),
        ("ransomware attacks on government networks", "هجمات برامج الفدية على الشبكات الحكومية",
         ["ransomware", "incident response", "network security"], ["برامج الفدية", "الاستجابة للحوادث", "أمن الشبكات"]),
        ("phishing and social engineering fraud against citizens", "التصيد الاحتيالي والهندسة الاجتماعية ضد المواطنين",
         ["phishing", "social engineering", "online fraud"], ["التصيد الاحتيالي", "الهندسة الاجتماعية", "الاحتيال الإلكتروني"]),
        ("digital evidence handling in cybercrime investigations", "التعامل مع الأدلة الرقمية في التحقيقات السيبرانية",
         ["digital forensics", "digital evidence", "cybercrime investigation"], ["الأدلة الجنائية الرقمية", "الدليل الرقمي", "التحقيق السيبراني"]),
        ("cryptocurrency misuse in financial crime", "إساءة استخدام العملات المشفرة في الجرائم المالية",
         ["cryptocurrency", "financial crime", "blockchain analysis"], ["العملات المشفرة", "الجرائم المالية", "تحليل سلسلة الكتل"]),
    ],
    3: [
        ("machine learning for crime pattern prediction", "تعلم الآلة للتنبؤ بأنماط الجريمة",
         ["machine learning", "predictive policing", "crime analytics"], ["تعلم الآلة", "الشرطة التنبؤية", "تحليل الجريمة"]),
        ("deepfake detection in audio and video evidence", "كشف التزييف العميق في الأدلة الصوتية والمرئية",
         ["deepfake", "computer vision", "media forensics"], ["التزييف العميق", "الرؤية الحاسوبية", "التحليل الجنائي للوسائط"]),
        ("large language models for Arabic security document analysis", "النماذج اللغوية الكبيرة لتحليل الوثائق الأمنية العربية",
         ["large language models", "Arabic NLP", "text classification"], ["النماذج اللغوية الكبيرة", "معالجة اللغة العربية", "تصنيف النصوص"]),
        ("drone surveillance using computer vision", "المراقبة بالطائرات المسيرة باستخدام الرؤية الحاسوبية",
         ["drones", "object detection", "computer vision"], ["الطائرات المسيرة", "كشف الأجسام", "الرؤية الحاسوبية"]),
        ("ethical governance of artificial intelligence in law enforcement", "الحوكمة الأخلاقية للذكاء الاصطناعي في إنفاذ القانون",
         ["AI ethics", "governance", "law enforcement"], ["أخلاقيات الذكاء الاصطناعي", "الحوكمة", "إنفاذ القانون"]),
    ],
    4: [
        ("human trafficking networks across regional borders", "شبكات الاتجار بالبشر عبر الحدود الإقليمية",
         ["human trafficking", "organized crime", "victim identification"], ["الاتجار بالبشر", "الجريمة المنظمة", "تحديد الضحايا"]),
        ("arms smuggling routes and regional cooperation", "مسارات تهريب الأسلحة والتعاون الإقليمي",
         ["arms smuggling", "regional cooperation", "intelligence sharing"], ["تهريب الأسلحة", "التعاون الإقليمي", "تبادل المعلومات"]),
        ("terrorist financing through transnational networks", "تمويل الإرهاب عبر الشبكات العابرة للحدود",
         ["terrorist financing", "transnational networks", "sanctions"], ["تمويل الإرهاب", "الشبكات العابرة للحدود", "العقوبات"]),
        ("illegal migration and document fraud", "الهجرة غير النظامية وتزوير الوثائق",
         ["illegal migration", "document fraud", "border control"], ["الهجرة غير النظامية", "تزوير الوثائق", "ضبط الحدود"]),
        ("maritime piracy and smuggling in regional waters", "القرصنة البحرية والتهريب في المياه الإقليمية",
         ["maritime security", "piracy", "smuggling"], ["الأمن البحري", "القرصنة", "التهريب"]),
    ],
    5: [
        ("synthetic drug abuse among university students", "تعاطي المخدرات المصنعة بين طلاب الجامعات",
         ["synthetic drugs", "substance abuse", "students"], ["المخدرات المصنعة", "تعاطي المواد", "الطلاب"]),
        ("amphetamine trafficking and seizure patterns", "أنماط تهريب الأمفيتامين وضبطه",
         ["amphetamine", "drug trafficking", "seizure data"], ["الأمفيتامين", "تهريب المخدرات", "بيانات الضبط"]),
        ("rehabilitation outcomes for drug addiction treatment", "نتائج إعادة التأهيل لعلاج الإدمان على المخدرات",
         ["addiction", "rehabilitation", "relapse"], ["الإدمان", "إعادة التأهيل", "الانتكاس"]),
        ("forensic toxicology of new psychoactive substances", "السموم الجنائية للمؤثرات العقلية الجديدة",
         ["toxicology", "psychoactive substances", "laboratory analysis"], ["علم السموم", "المؤثرات العقلية", "التحليل المخبري"]),
        ("family and school prevention programs against narcotics", "برامج الوقاية الأسرية والمدرسية من المخدرات",
         ["prevention", "family", "narcotics awareness"], ["الوقاية", "الأسرة", "التوعية بالمخدرات"]),
    ],
}

METHODS_EN = ["a mixed-methods design combining surveys and interviews", "a quantitative analysis of administrative records",
              "a comparative case study of regional agencies", "an experimental evaluation of a prototype system",
              "a systematic review followed by expert validation"]
METHODS_AR = ["منهج مختلط يجمع بين الاستبانات والمقابلات", "تحليل كمي للسجلات الإدارية",
              "دراسة حالة مقارنة للأجهزة الإقليمية", "تقييم تجريبي لنموذج أولي", "مراجعة منهجية تليها مصادقة الخبراء"]

COLLEGES = [
    ("College of Criminal Justice", "كلية العدالة الجنائية", ["Department of Criminal Justice", "Department of Security Studies"],
     ["قسم العدالة الجنائية", "قسم الدراسات الأمنية"]),
    ("College of Computer and Information Security", "كلية الحاسب وأمن المعلومات", ["Department of Information Security", "Department of Data Science"],
     ["قسم أمن المعلومات", "قسم علوم البيانات"]),
    ("College of Forensic Sciences", "كلية علوم الأدلة الجنائية", ["Department of Forensic Sciences", "Department of Toxicology"],
     ["قسم علوم الأدلة الجنائية", "قسم علم السموم"]),
    ("College of Strategic Sciences", "كلية العلوم الاستراتيجية", ["Department of Strategic Studies", "Department of Social Sciences"],
     ["قسم الدراسات الاستراتيجية", "قسم العلوم الاجتماعية"]),
]
# Which college usually hosts which priority (keeps the portfolio map realistic)
PRIORITY_COLLEGE = {1: [0, 3], 2: [1, 0], 3: [1], 4: [3, 0], 5: [2, 0]}

FIRST_EN = ["Fake-Ahmed", "Fake-Sara", "Fake-Khalid", "Fake-Noura", "Fake-Omar", "Fake-Huda", "Fake-Faisal", "Fake-Reem",
            "Fake-Yousef", "Fake-Lama", "Fake-Majed", "Fake-Dana"]
FIRST_AR = ["أحمد", "سارة", "خالد", "نورة", "عمر", "هدى", "فيصل", "ريم", "يوسف", "لمى", "ماجد", "دانة"]
LAST_EN = ["Alpha", "Bravo", "Cedar", "Delta", "Echo", "Falcon", "Granite", "Harbor"]
LAST_AR = ["الوهمي", "التجريبي", "الافتراضي", "المثالي", "الاختباري"]

TYPES = {"small": (150_000, 12), "medium": (300_000, 18), "large": (600_000, 24)}
ROUNDS = {1: 2023, 2: 2024, 3: 2025}
START_QUARTER = {1: 1, 2: 1, 3: 3}  # round 3 grants started in July 2025, so many are still running
REPORT_DATE_YEAR = 2026  # "today" for the synthetic world: progress is reported up to Q3 2026

STAGES = [("Literature review", "مراجعة الأدبيات"), ("Instrument design", "تصميم الأدوات"),
          ("Ethics approval", "الموافقة الأخلاقية"), ("Data collection", "جمع البيانات"),
          ("Data analysis", "تحليل البيانات"), ("Writing results", "كتابة النتائج"),
          ("Paper submission", "تقديم الأوراق العلمية"), ("Final report", "التقرير النهائي")]

# 15 reviewer criteria as on the real reviewer form (maxima sum to 100)
CRITERIA = [
    ("A1", "Title reflects importance, correct scientific style", "العنوان يعكس أهمية الموضوع بأسلوب علمي صحيح", 5),
    ("A2", "Originality and novelty", "الأصالة والجدة", 15),
    ("A3", "Objectives clear, measurable, achievable", "الأهداف واضحة وقابلة للقياس والتحقيق", 10),
    ("A4", "Objectives linked to research topic", "ارتباط الأهداف بموضوع البحث", 5),
    ("A5", "Justification, background depth, recent sources", "المبررات وعمق الخلفية وحداثة المصادر", 15),
    ("B1", "Methodology appropriate", "ملاءمة المنهجية", 3),
    ("B2", "Plan specifies procedures and time frame", "الخطة تحدد الإجراءات والإطار الزمني", 5),
    ("B3C", "Population and sampling", "المجتمع والعينة", 3),
    ("B3D", "Data collection methods", "أدوات جمع البيانات", 3),
    ("B3E", "Statistical analysis", "التحليل الإحصائي", 3),
    ("B3F", "Ethical considerations", "الاعتبارات الأخلاقية", 3),
    ("C1", "Targeted papers clear and consistent with objectives", "الأوراق المستهدفة واضحة ومتسقة مع الأهداف", 10),
    ("D1", "Team expertise related to topic", "خبرة الفريق مرتبطة بالموضوع", 5),
    ("E1", "Budget suitable and connected to proposal", "الميزانية مناسبة ومرتبطة بالمقترح", 10),
    ("D2", "Team size and roles suitable", "حجم الفريق وأدواره مناسبة", 5),
]
VARIANT_CODES = {"B3C", "B3D", "B3E", "B3F"}

CONCERNS_EN = ["The sample size is too small to support the conclusions.", "The timetable is unrealistic for the planned data collection.",
               "The budget for equipment is not justified.", "Recent sources (last five years) are missing from the background.",
               "Ethical approval procedures are not described.", "The expected publications are not linked to the objectives.",
               "The team lacks a member with statistical expertise."]
CONCERNS_AR = ["حجم العينة صغير ولا يدعم الاستنتاجات.", "الجدول الزمني غير واقعي لجمع البيانات المخطط.",
               "ميزانية الأجهزة غير مبررة.", "تفتقر الخلفية إلى مصادر حديثة خلال السنوات الخمس الأخيرة.",
               "لم توضح إجراءات الموافقة الأخلاقية.", "الأوراق المتوقعة غير مرتبطة بالأهداف.",
               "يفتقر الفريق إلى عضو متخصص في الإحصاء."]
PRAISE_EN = ["The topic is relevant and well motivated.", "The objectives are clearly written.", "The methodology is sound."]
PRAISE_AR = ["الموضوع مهم ومبرر بشكل جيد.", "الأهداف مكتوبة بوضوح.", "المنهجية سليمة."]

JOURNALS = ["Journal of Synthetic Security Studies", "International Review of Test Criminology",
            "Synthetic Journal of Digital Forensics", "Placeholder Journal of AI and Society", "Test Journal of Drug Policy"]


# ---------------------------------------------------------------- docx helpers
def set_rtl(paragraph):
    pPr = paragraph._p.get_or_add_pPr()
    bidi = OxmlElement("w:bidi")
    bidi.set(qn("w:val"), "1")
    pPr.append(bidi)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT


def new_doc(lang, form_code, title_en, title_ar):
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(10)
    style.element.rPr.rFonts.set(qn("w:cs"), "Arial")
    b = doc.add_paragraph()
    r = b.add_run(f"{BANNER_EN}  |  {BANNER_AR}")
    r.bold = True
    r.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
    doc.core_properties.comments = "SYNTHETIC DATA - generated for testing the grant-intelligence pipeline"
    doc.core_properties.keywords = "synthetic"
    h = doc.add_heading(f"{title_ar}\n{title_en}" if lang == "ar" else f"{title_en}\n{title_ar}", level=1)
    if lang == "ar":
        set_rtl(h)
    doc.add_paragraph(f"Form: {form_code}")
    return doc


def add_kv_table(doc, rows, lang):
    """Two-column bilingual label/value table, like the institutional forms."""
    t = doc.add_table(rows=0, cols=2)
    t.style = "Table Grid"
    for label_en, label_ar, value in rows:
        cells = t.add_row().cells
        cells[0].text = f"{label_ar} / {label_en}"
        cells[1].text = "" if value is None else str(value)
        if lang == "ar":
            for c in cells:
                for p in c.paragraphs:
                    set_rtl(p)
    doc.add_paragraph()
    return t


def add_grid(doc, header, rows, lang):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    for i, h in enumerate(header):
        t.rows[0].cells[i].text = h
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = "" if v is None else str(v)
    if lang == "ar":
        for row in t.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    set_rtl(p)
    doc.add_paragraph()
    return t


def add_section(doc, heading_en, heading_ar, text, lang):
    h = doc.add_heading(f"{heading_ar} / {heading_en}", level=2)
    p = doc.add_paragraph("" if text is None else text)
    if lang == "ar":
        set_rtl(h)
        set_rtl(p)


# ---------------------------------------------------------------- content
def person(rng, lang):
    if lang == "ar":
        return f"د. {rng.choice(FIRST_AR)} {rng.choice(LAST_AR)}"
    return f"Dr. {rng.choice(FIRST_EN)} {rng.choice(LAST_EN)}"


def abstract_text(rng, lang, topic, secondary):
    en, ar, _, _ = topic
    sec_en, sec_ar = (secondary[0], secondary[1]) if secondary else (None, None)
    mi = rng.randrange(len(METHODS_EN))
    if lang == "en":
        s = [f"This study investigates {en} in the Arab region.",
             f"The research addresses a growing gap in evidence on {en}, which affects security institutions and society.",
             f"We use {METHODS_EN[mi]} to measure the scale of the problem and its drivers."]
        if sec_en:
            s.append(f"The project also examines links with {sec_en}.")
        s += ["The expected results will support policy makers and practitioners with practical recommendations.",
              "Findings will be published in indexed journals and shared through training workshops."]
    else:
        s = [f"تتناول هذه الدراسة {ar} في المنطقة العربية.",
             f"يعالج البحث فجوة متزايدة في الأدلة حول {ar} مما يؤثر على المؤسسات الأمنية والمجتمع.",
             f"نستخدم {METHODS_AR[mi]} لقياس حجم المشكلة ومسبباتها."]
        if sec_ar:
            s.append(f"كما يدرس المشروع العلاقة مع {sec_ar}.")
        s += ["ستدعم النتائج المتوقعة صناع القرار والممارسين بتوصيات عملية.",
              "ستنشر النتائج في مجلات محكمة ومفهرسة وتعرض في ورش عمل تدريبية."]
    return " ".join(s), mi


def proposal_record(rng, i, rnd):
    content_p = rng.choices([1, 2, 3, 4, 5], weights=[20, 22, 24, 16, 18])[0]
    lang = "ar" if rng.random() < 0.6 else "en"
    topic = rng.choice(TOPICS[content_p])
    # ~15% of applicants claim a different priority than their content
    mismatch = rng.random() < 0.15
    claimed_p = rng.choice([p for p in PRIORITIES if p != content_p]) if mismatch else content_p
    # ~20% of proposals mention a second priority topic (harder, ambiguous cases)
    secondary = None
    if rng.random() < 0.2:
        sp = rng.choice([p for p in PRIORITIES if p != content_p])
        secondary = rng.choice(TOPICS[sp])[:2]
    gtype = rng.choices(list(TYPES), weights=[45, 35, 20])[0]
    col = rng.choice(PRIORITY_COLLEGE[content_p])
    dept = rng.randrange(2)
    return dict(grant_id=f"NAUSS-{ROUNDS[rnd] % 100}-R{rnd:02d}-{i:03d}", round=rnd, year=ROUNDS[rnd], lang=lang,
                content_priority=content_p, claimed_priority=claimed_p, claim_matches_content=int(claimed_p == content_p),
                ambiguous=int(secondary is not None), topic=topic, secondary=secondary, type=gtype,
                budget=int(TYPES[gtype][0] * rng.uniform(0.7, 1.0) // 1000 * 1000), planned_months=TYPES[gtype][1],
                college=col, dept=dept, team_size=rng.randint(2, 6))


def write_proposal(rng, rec, out):
    lang = rec["lang"]
    en, ar, kw_en, kw_ar = rec["topic"]
    title = (f"Assessing {en}" if lang == "en" else f"تقييم {ar}")
    abstract, mi = abstract_text(rng, lang, rec["topic"], rec["secondary"])
    keywords = kw_en if lang == "en" else kw_ar
    if lang == "ar" and rng.random() < 0.4:   # mixed-language keywords, common in real Arabic forms
        keywords = kw_ar + [kw_en[0]]
    col = COLLEGES[rec["college"]]
    missing = []

    def maybe_empty(field, value, p=0.07):
        if rng.random() < p:
            missing.append(field)
            return ""
        return value

    pi = person(rng, lang)
    doc = new_doc(lang, "PROPOSAL", "Research Proposal Form", "نموذج مقترح بحثي")
    pri_en, pri_ar = PRIORITIES[rec["claimed_priority"]]
    add_section(doc, "1. Basic information", "1. المعلومات الأساسية", None, lang)
    add_kv_table(doc, [
        ("Proposal number", "رقم المقترح", rec["grant_id"]),
        ("Funding round", "دورة التمويل", f"Round {rec['round']} ({rec['year']})"),
        ("Research priority", "الأولوية البحثية", pri_ar if lang == "ar" else pri_en),
        ("Project type", "نوع المشروع", rec["type"]),
        ("Title", "العنوان", title),
        ("Principal investigator", "الباحث الرئيس", pi),
        ("College", "الكلية", col[1] if lang == "ar" else col[0]),
        ("Department", "القسم", maybe_empty("department", col[3][rec["dept"]] if lang == "ar" else col[2][rec["dept"]], 0.05)),
        ("Requested budget (SAR)", "الميزانية المطلوبة (ريال)", rec["budget"]),
        ("Duration (months)", "المدة (بالأشهر)", rec["planned_months"]),
    ], lang)
    add_section(doc, "2. Research team", "2. فريق البحث", None, lang)
    team = [(pi, "PI" if lang == "en" else "باحث رئيس")] + [
        (person(rng, lang), "Co-investigator" if lang == "en" else "باحث مشارك") for _ in range(rec["team_size"] - 1)]
    add_grid(doc, ["Name / الاسم", "Role / الدور"], team, lang)
    add_section(doc, "3. Abstract", "3. الملخص", abstract, lang)
    add_section(doc, "4. Keywords", "4. الكلمات المفتاحية", maybe_empty("keywords", ", ".join(keywords)), lang)
    bg = (f"Previous studies on {en} remain limited and mostly descriptive." if lang == "en"
          else f"لا تزال الدراسات السابقة حول {ar} محدودة ويغلب عليها الطابع الوصفي.")
    add_section(doc, "5. Background and justification", "5. الخلفية والمبررات", bg, lang)
    add_section(doc, "6. Objectives", "6. الأهداف",
                ("1) Measure the current situation. 2) Identify the main factors. 3) Propose recommendations."
                 if lang == "en" else "1) قياس الوضع الراهن. 2) تحديد العوامل الرئيسة. 3) اقتراح توصيات."), lang)
    meth = METHODS_EN[mi] if lang == "en" else METHODS_AR[mi]
    for code, h_en, h_ar in [("7.1", "Methodology", "المنهجية"), ("7.2", "Population and sample", "المجتمع والعينة"),
                             ("7.3", "Data collection", "جمع البيانات"), ("7.4", "Statistical analysis", "التحليل الإحصائي"),
                             ("7.5", "Ethical considerations", "الاعتبارات الأخلاقية")]:
        txt = meth if code == "7.1" else ("As described in the research plan." if lang == "en" else "كما هو موضح في خطة البحث.")
        add_section(doc, f"{code} {h_en}", f"{code} {h_ar}", maybe_empty(f"method_{code}", txt, 0.05), lang)
    n_pubs = rng.randint(1, 3) if rec["type"] != "large" else rng.randint(2, 4)
    exp = (f"{n_pubs} papers in Q1/Q2 indexed journals on {en}." if lang == "en"
           else f"{n_pubs} أوراق علمية في مجلات مفهرسة من الفئة Q1/Q2 حول {ar}.")
    add_section(doc, "8. Expected publications", "8. المنشورات المتوقعة", maybe_empty("expected_publications", exp, 0.08), lang)
    add_section(doc, "9. Timetable", "9. الجدول الزمني", None, lang)
    pm = rec["planned_months"]
    bounds = [0, 1, 2, 3, round(pm * 0.55), round(pm * 0.75), round(pm * 0.9), pm - 1, pm]
    rows = []
    for k, (s_en, s_ar) in enumerate(STAGES):
        rows.append((s_ar if lang == "ar" else s_en, team[k % len(team)][0], bounds[k] + 1, bounds[k + 1]))
    add_grid(doc, ["Task / المهمة", "Researcher / الباحث", "From month / من الشهر", "To month / إلى الشهر"], rows, lang)
    add_section(doc, "10. Itemised budget", "10. تفاصيل الميزانية", None, lang)
    b = rec["budget"]
    shares = {"Personnel / الأجور": 0.5, "Equipment / الأجهزة": rng.uniform(0.1, 0.25),
              "Travel / السفر": 0.08, "Publication / النشر": 0.05}
    shares["Other / أخرى"] = max(0.0, 1 - sum(shares.values()))
    add_grid(doc, ["Item / البند", "Amount (SAR) / المبلغ"], [(k, int(b * v)) for k, v in shares.items()], lang)
    add_section(doc, "11. Team publications (last 5 years)", "11. منشورات الفريق (آخر 5 سنوات)", None, lang)
    prior = rng.randint(0, 8)
    add_grid(doc, ["Title / العنوان", "Year / السنة", "Journal / المجلة"],
             [(f"Synthetic prior paper {k + 1} on {en}", rng.randint(2018, rec["year"] - 1), rng.choice(JOURNALS))
              for k in range(prior)], lang)
    add_section(doc, "12. Declaration", "12. الإقرار",
                "The PI confirms the information is accurate." if lang == "en" else "يقر الباحث الرئيس بصحة المعلومات.", lang)
    path = out / "proposals" / f"{rec['grant_id']}_proposal_{lang}.docx"
    doc.save(path)
    rec.update(title=title, pi=pi, n_expected_pubs=n_pubs, prior_pubs=prior, missing_fields=";".join(missing),
               equipment_share=round(shares["Equipment / الأجهزة"], 3))


def write_assessment(rng, rec, out):
    lang = rec["lang"]
    decision = rng.choices(["approve", "revise", "reject"], weights=[70, 15, 15])[0]
    yes = lambda: "Yes / نعم" if decision != "reject" or rng.random() < 0.5 else "No / لا"
    doc = new_doc(lang, "ASSESSMENT", "Initial Assessment of a Research Proposal", "نموذج تقييم مبدئي لمقترح بحثي")
    add_kv_table(doc, [("Proposal number", "رقم المقترح", rec["grant_id"]), ("Proposal title", "عنوان المقترح", rec["title"])], lang)
    add_grid(doc, ["Criterion / المعيار", "Yes-No / نعم-لا", "Notes / ملاحظات"], [
        ("Research topic: title relevant, clear, sound / موضوع البحث", yes(), ""),
        ("Team expertise / خبرة الفريق", yes(), ""),
        ("Budget reasonable and justified / الميزانية", yes(), ""),
        ("Methodology appropriate / المنهجية", yes(), ""),
    ], lang)
    dec_ar = {"approve": "موافقة", "revise": "تعديل", "reject": "رفض"}[decision]
    add_kv_table(doc, [("Recommendation", "التوصية", f"{decision} / {dec_ar}")], lang)
    doc.save(out / "assessments" / f"{rec['grant_id']}_assessment.docx")
    rec["assessment"] = decision


def write_reviews(rng, rec, out, review_rows):
    lang = rec["lang"]
    quality = rng.gauss(0, 1)              # latent proposal quality, drives scores AND later outcomes
    rec["quality"] = quality
    n_rev = 2 if rng.random() < 0.75 else 1
    rec["n_reviews"] = n_rev
    totals = []
    for r in range(n_rev):
        rid = f"{rec['grant_id']}-{'AB'[r]}"
        variant = rng.random() < 0.2      # methodology C-F marked as one score out of 12
        severity = rng.gauss(0, 0.5)      # reviewer leniency, makes agreement imperfect
        scores = {}
        for code, _, _, mx in CRITERIA:
            frac = min(1.0, max(0.1, 0.72 + 0.12 * quality + 0.08 * severity + rng.gauss(0, 0.1)))
            scores[code] = round(mx * frac)
        if variant:
            combined = sum(scores[c] for c in VARIANT_CODES)
            for c in VARIANT_CODES:
                scores[c] = None
        total = sum(v for v in scores.values() if v is not None) + (combined if variant else 0)
        totals.append(total)
        concerns = rng.sample(range(len(CONCERNS_EN)), k=rng.randint(0, 2) if quality > 0 else rng.randint(1, 3))
        praise = PRAISE_EN if lang == "en" else PRAISE_AR
        conc = CONCERNS_EN if lang == "en" else CONCERNS_AR
        general = " ".join([rng.choice(praise)] + [conc[c] for c in concerns])
        doc = new_doc(lang, "REVIEW", "Research Proposal Review Form", "نموذج تحكيم مقترح بحثي")
        pri_en, pri_ar = PRIORITIES[rec["claimed_priority"]]
        add_kv_table(doc, [("Proposal number", "رقم المقترح", rec["grant_id"]), ("Title", "العنوان", rec["title"]),
                           ("Research priority", "الأولوية البحثية", pri_ar if lang == "ar" else pri_en),
                           ("Reviewer", "المحكم", person(rng, lang)), ("University", "الجامعة", "Synthetic University / جامعة اصطناعية"),
                           ("Form variant", "نوع النموذج", "methodology C-F combined (out of 12)" if variant else "standard 15 criteria")], lang)
        rows = []
        for code, c_en, c_ar, mx in CRITERIA:
            if variant and code in VARIANT_CODES:
                continue
            rows.append((code, f"{c_ar} / {c_en}", mx, scores[code], ""))
            if variant and code == "B2":
                rows.append(("B3", "المنهجية ج-و مجتمعة / Methodology C-F combined", 12, combined, ""))
        rows.append(("", "Total / المجموع", 100, total, ""))
        add_grid(doc, ["Code", "Criterion / المعيار", "Max / الدرجة القصوى", "Score / الدرجة", "Comment / تعليق"], rows, lang)
        add_kv_table(doc, [("Research classification", "تصنيف البحث", rng.choice(["Applied / تطبيقي", "Basic / أساسي"])),
                           ("General comments to the team", "ملاحظات عامة للفريق", general)], lang)
        doc.save(out / "reviews" / f"{rid}_review.docx")
        row = dict(review_id=rid, grant_id=rec["grant_id"], variant_combined_CF=int(variant), total=total,
                   concern_ids=";".join(str(c) for c in concerns))
        row.update({c: scores[c] for c, *_ in CRITERIA})
        row["B3_combined"] = combined if variant else ""
        review_rows.append(row)
    rec["mean_review_total"] = round(sum(totals) / len(totals), 1)


def simulate_progress(rng, rec):
    """Quarterly 8-stage percentage vectors with realistic stalls."""
    pm = rec["planned_months"]
    start_q = (rec["year"] - 2023) * 4 + START_QUARTER[rec["round"]]
    now_q = (REPORT_DATE_YEAR - 2023) * 4 + 3        # last quarter with a report
    speed = max(0.45, 1 + 0.15 * rec["quality"] + rng.gauss(0, 0.15))
    stall_stage = rng.choices([None, 2, 3, 4, 6], weights=[55, 15, 15, 10, 5])[0]
    stall_len = rng.randint(2, 4) if stall_stage is not None else 0
    plan_end = [1, 2, 3, round(pm * 0.55), round(pm * 0.75), round(pm * 0.9), pm - 1, pm]
    plan_start = [0] + plan_end[:-1]
    reports, month_eff, stalled_left = [], 0.0, stall_len
    q = start_q
    while q <= now_q:
        month_eff += 3 * speed
        vec = []
        for k in range(8):
            span = max(1, plan_end[k] - plan_start[k])
            pct = min(100, max(0, round(100 * (month_eff - plan_start[k]) / span)))
            vec.append(pct)
        if stall_stage is not None and vec[stall_stage] > 0 and stalled_left > 0 and vec[stall_stage] < 100:
            stalled_left -= 1
            month_eff -= 3 * speed                    # nothing moved this quarter
            vec = reports[-1]["stages"][:] if reports else vec
        pubs = sum(1 for _ in range(2) if vec[6] == 100 and rng.random() < 0.5) if vec[6] == 100 else 0
        reports.append(dict(quarter=q - start_q + 1, stages=vec, self_reported_pubs=pubs,
                            budget_spent=int(rec["budget"] * min(1, sum(vec) / 800) * rng.uniform(0.9, 1.05))))
        if all(v == 100 for v in vec):
            break
        q += 1
    elapsed_months = len(reports) * 3
    rec.update(stall_stage=STAGES[stall_stage][0] if stall_stage is not None else "", stall_quarters=stall_len,
               completed=int(all(v == 100 for v in reports[-1]["stages"])), actual_months=elapsed_months)
    rec["extended"] = int(elapsed_months > pm + 2 or (not rec["completed"] and elapsed_months > pm))
    return reports


def write_progress(rng, rec, reports, out, progress_rows):
    lang = rec["lang"]
    for rp in reports:
        doc = new_doc(lang, "PROGRESS", "Quarterly Progress Report", "تقرير الإنجاز الربعي")
        add_kv_table(doc, [("Project number", "رقم المشروع", rec["grant_id"]), ("Title", "العنوان", rec["title"]),
                           ("Quarter", "الربع", rp["quarter"]),
                           ("Budget spent (SAR)", "المصروف من الميزانية", rp["budget_spent"]),
                           ("Self-reported publications this quarter", "المنشورات المعلنة في هذا الربع", rp["self_reported_pubs"]),
                           ("Ethics approval number", "رقم الموافقة الأخلاقية",
                            f"ETH-SYN-{rng.randint(100, 999)}" if rp["stages"][2] == 100 else "")], lang)
        add_grid(doc, ["Stage / المرحلة", "Completion % / نسبة الإنجاز"],
                 [(f"{s_ar} / {s_en}", v) for (s_en, s_ar), v in zip(STAGES, rp["stages"])], lang)
        doc.save(out / "progress_reports" / f"{rec['grant_id']}_Q{rp['quarter']:02d}_progress.docx")
        progress_rows.append(dict(grant_id=rec["grant_id"], quarter=rp["quarter"], budget_spent=rp["budget_spent"],
                                  self_reported_pubs=rp["self_reported_pubs"],
                                  **{f"stage{k + 1}": v for k, v in enumerate(rp["stages"])}))


def write_final(rng, rec, out, paper_rows):
    lang = rec["lang"]
    en, ar, _, _ = rec["topic"]
    p_pub = 0.45 + 0.15 * rec["quality"] + 0.03 * rec["prior_pubs"]
    n_pubs = sum(1 for _ in range(rec["n_expected_pubs"] + 1) if rng.random() < p_pub)
    # ~25% drift: the papers end up on a different topic than the proposal promised
    drift = rng.random() < 0.25
    if drift:
        other = rng.choice(TOPICS[rng.choice([p for p in PRIORITIES if p != rec["content_priority"]])])
        paper_topic = other[0]
    else:
        paper_topic = en
    papers = []
    for k in range(n_pubs):
        doi = f"10.99999/synthetic.{rec['grant_id'].lower()}.{k + 1}"   # 10.99999 is not a real prefix: never resolves
        papers.append((f"{rng.choice(['Evidence on', 'A study of', 'Measuring', 'New findings on'])} {paper_topic}",
                       f"{rng.randint(rec['year'] + 1, 2026)}-{rng.randint(1, 12):02d}", rng.choice(JOURNALS),
                       rng.choice(["Q1", "Q2", "Q3", "Q4"]), doi))
        paper_rows.append(dict(grant_id=rec["grant_id"], title=papers[-1][0], doi=doi, drifted=int(drift)))
    col = COLLEGES[rec["college"]]
    doc = new_doc(lang, "VPSR-R06", "Final Project Report", "التقرير النهائي للمشروع")
    add_kv_table(doc, [
        ("Project title", "عنوان المشروع", rec["title"]), ("Project No.", "رقم المشروع", rec["grant_id"]),
        ("College/Center", "الكلية/المركز", col[1] if lang == "ar" else col[0]),
        ("Department", "القسم", col[3][rec["dept"]] if lang == "ar" else col[2][rec["dept"]]),
        ("Submitted by", "مقدم من", rec["pi"]), ("Start date", "تاريخ البدء", f"{rec['year']}-{3 * START_QUARTER[rec['round']] - 2:02d}-01"),
        ("Duration (months)", "المدة (بالأشهر)", rec["actual_months"]), ("Budget", "الميزانية", rec["budget"]),
        ("Disbursed amount", "المبلغ المصروف", int(rec["budget"] * 0.97)),
        ("Remaining amount", "المبلغ المتبقي", int(rec["budget"] * 0.03)),
    ], lang)
    add_grid(doc, ["Amendment / التعديل", "Yes-No / نعم-لا", "Request date / تاريخ الطلب", "Approval date / تاريخ الموافقة"], [
        ("Period extended / تمديد المدة", "Yes / نعم" if rec["extended"] else "No / لا",
         f"{rec['year'] + 1}-{rng.randint(1, 12):02d}-01" if rec["extended"] else "",
         f"{rec['year'] + 1}-{rng.randint(1, 12):02d}-15" if rec["extended"] else ""),
        ("Title changed / تغيير العنوان", "No / لا", "", ""),
    ], lang)
    add_grid(doc, ["Paper title / عنوان الورقة", "Publication date / تاريخ النشر", "Journal / المجلة",
                   "Quartile / الفئة", "DOI"], papers, lang)
    summary = (f"The project studied {en} and produced {n_pubs} papers." if lang == "en"
               else f"درس المشروع {ar} وأنتج {n_pubs} أوراق علمية.")
    add_section(doc, "Contribution summary", "ملخص الإسهام", summary, lang)
    doc.save(out / "final_reports" / f"{rec['grant_id']}_final_report_{lang}.docx")
    rec.update(actual_pubs=n_pubs, output_drift=int(drift))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="synthetic-data")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--per-round", type=int, nargs=3, default=[30, 35, 35])
    args = ap.parse_args()
    rng = random.Random(args.seed)
    out = Path(args.out)
    raw = out / "raw"
    for d in ["proposals", "assessments", "reviews", "progress_reports", "final_reports"]:
        (raw / d).mkdir(parents=True, exist_ok=True)
    (out / "ground_truth").mkdir(parents=True, exist_ok=True)

    grants, reviews, progress, papers = [], [], [], []
    for rnd, n in zip((1, 2, 3), args.per_round):
        for i in range(1, n + 1):
            rec = proposal_record(rng, i, rnd)
            write_proposal(rng, rec, raw)
            write_assessment(rng, rec, raw)
            rec.update(n_reviews=0, mean_review_total="", funded=0, completed="", extended="", actual_pubs="",
                       output_drift="", stall_stage="", stall_quarters="", actual_months="", quality=rng.gauss(0, 1))
            if rec["assessment"] != "reject":
                write_reviews(rng, rec, raw, reviews)
                rec["funded"] = int(rec["mean_review_total"] >= 65)
            if rec["funded"]:
                reps = simulate_progress(rng, rec)
                write_progress(rng, rec, reps, raw, progress)
                if rec["completed"]:
                    write_final(rng, rec, raw, papers)
            grants.append(rec)

    col_names = ["grant_id", "round", "year", "lang", "type", "college", "department", "budget", "planned_months",
                 "team_size", "claimed_priority", "content_priority", "claim_matches_content", "ambiguous",
                 "assessment", "n_reviews", "mean_review_total", "funded", "completed", "extended", "actual_months",
                 "stall_stage", "stall_quarters", "n_expected_pubs", "actual_pubs", "output_drift", "prior_pubs",
                 "equipment_share", "missing_fields"]
    with open(out / "ground_truth" / "grants.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=col_names)
        w.writeheader()
        for g in grants:
            row = {k: g.get(k, "") for k in col_names}
            row["college"] = COLLEGES[g["college"]][0]
            row["department"] = COLLEGES[g["college"]][2][g["dept"]]
            row["claimed_priority"] = PRIORITIES[g["claimed_priority"]][0]
            row["content_priority"] = PRIORITIES[g["content_priority"]][0]
            w.writerow(row)
    for name, rows in [("reviews.csv", reviews), ("progress.csv", progress), ("papers.csv", papers)]:
        if rows:
            with open(out / "ground_truth" / name, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
    print(f"grants={len(grants)} reviews={len(reviews)} progress_reports={len(progress)} papers={len(papers)}")


if __name__ == "__main__":
    main()
