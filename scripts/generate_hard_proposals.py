import argparse
import csv
import importlib.util
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent

HARD_TOPICS = {
    1: [
        ("readiness of civil protection units during mass gatherings", "جاهزية وحدات الحماية المدنية أثناء التجمعات الكبرى",
         ["mass gatherings", "civil protection", "preparedness"], ["التجمعات الكبرى", "الحماية المدنية", "الجاهزية"]),
        ("online spread of violent ideologies among teenagers", "انتشار الأفكار العنيفة بين المراهقين عبر الإنترنت",
         ["violent ideologies", "teenagers", "online influence"], ["الأفكار العنيفة", "المراهقون", "التأثير الرقمي"]),
        ("security of water and power utilities", "أمن مرافق المياه والكهرباء",
         ["utilities", "power grid", "water supply"], ["المرافق", "شبكة الكهرباء", "إمدادات المياه"]),
        ("neighbourhood watch schemes and citizen cooperation with police", "برامج الأحياء الآمنة وتعاون المواطنين مع الشرطة",
         ["neighbourhood watch", "citizen cooperation", "police legitimacy"], ["الأحياء الآمنة", "تعاون المواطنين", "شرعية الشرطة"]),
        ("hybrid threats to state stability", "التهديدات الهجينة لاستقرار الدولة",
         ["hybrid threats", "state stability", "disinformation"], ["التهديدات الهجينة", "استقرار الدولة", "التضليل"]),
    ],
    2: [
        ("identity theft through fake e-commerce sites", "سرقة الهوية عبر مواقع التجارة الإلكترونية المزيفة",
         ["identity theft", "e-commerce", "fake websites"], ["سرقة الهوية", "التجارة الإلكترونية", "المواقع المزيفة"]),
        ("hacking of hospital information systems", "اختراق أنظمة المعلومات في المستشفيات",
         ["hacking", "health information systems", "data breach"], ["الاختراق", "أنظمة المعلومات الصحية", "تسريب البيانات"]),
        ("illicit use of mobile wallets for laundering criminal proceeds", "الاستخدام غير المشروع للمحافظ الإلكترونية لتبييض عائدات الجريمة",
         ["mobile wallets", "criminal proceeds", "fintech"], ["المحافظ الإلكترونية", "عائدات الجريمة", "التقنية المالية"]),
        ("online extortion of minors through social media", "الابتزاز الإلكتروني للقاصرين عبر وسائل التواصل",
         ["online extortion", "minors", "social media"], ["الابتزاز الإلكتروني", "القاصرون", "وسائل التواصل"]),
        ("insider embezzlement in public procurement", "الاختلاس الداخلي في المشتريات الحكومية",
         ["embezzlement", "procurement", "corruption"], ["الاختلاس", "المشتريات الحكومية", "الفساد"]),
    ],
    3: [
        ("automatic speaker recognition in recorded calls", "التعرف الآلي على المتحدث في المكالمات المسجلة",
         ["speaker recognition", "speech processing", "audio"], ["التعرف على المتحدث", "معالجة الكلام", "الصوت"]),
        ("smart camera analytics for crowd density estimation", "تحليلات الكاميرات الذكية لتقدير كثافة الحشود",
         ["smart cameras", "crowd density", "video analytics"], ["الكاميرات الذكية", "كثافة الحشود", "تحليل الفيديو"]),
        ("chatbots for answering citizen enquiries in police services", "روبوتات المحادثة للرد على استفسارات المواطنين في خدمات الشرطة",
         ["chatbots", "conversational agents", "e-government"], ["روبوتات المحادثة", "الوكلاء الحواريون", "الحكومة الإلكترونية"]),
        ("generative models for synthetic training data", "النماذج التوليدية لإنتاج بيانات تدريب اصطناعية",
         ["generative models", "synthetic data", "data augmentation"], ["النماذج التوليدية", "البيانات الاصطناعية", "زيادة البيانات"]),
        ("algorithmic bias in automated risk scoring", "التحيز الخوارزمي في أنظمة تقدير المخاطر الآلية",
         ["algorithmic bias", "fairness", "automated decisions"], ["التحيز الخوارزمي", "العدالة الخوارزمية", "القرارات الآلية"]),
    ],
    4: [
        ("exploitation of migrant workers by recruitment networks", "استغلال العمالة الوافدة من قبل شبكات الاستقدام",
         ["labour exploitation", "migrant workers", "recruitment networks"], ["استغلال العمالة", "العمالة الوافدة", "شبكات الاستقدام"]),
        ("foreign fighters returning from conflict zones", "عودة المقاتلين الأجانب من مناطق النزاع",
         ["foreign fighters", "conflict zones", "reintegration"], ["المقاتلون الأجانب", "مناطق النزاع", "إعادة الإدماج"]),
        ("counterfeit goods entering through free trade zones", "دخول السلع المقلدة عبر المناطق الحرة",
         ["counterfeit goods", "free trade zones", "customs"], ["السلع المقلدة", "المناطق الحرة", "الجمارك"]),
        ("wildlife and antiquities trafficking routes", "مسارات الاتجار بالحياة البرية والآثار",
         ["wildlife trafficking", "antiquities", "illicit trade"], ["الاتجار بالحياة البرية", "الآثار", "التجارة غير المشروعة"]),
        ("cooperation between interpol bureaus on fugitives", "التعاون بين مكاتب الإنتربول في ملاحقة الفارين",
         ["interpol", "fugitives", "extradition"], ["الإنتربول", "الفارون", "تسليم المطلوبين"]),
    ],
    5: [
        ("cannabis use among young adults", "استخدام القنب بين الشباب البالغين",
         ["cannabis", "young adults", "use patterns"], ["القنب", "الشباب البالغون", "أنماط الاستخدام"]),
        ("misuse of prescription painkillers", "سوء استخدام المسكنات الموصوفة طبيا",
         ["prescription opioids", "painkillers", "pharmacies"], ["المسكنات الأفيونية", "المسكنات", "الصيدليات"]),
        ("captagon pill production and distribution", "إنتاج حبوب الكبتاغون وتوزيعها",
         ["captagon", "pill production", "distribution networks"], ["الكبتاغون", "إنتاج الحبوب", "شبكات التوزيع"]),
        ("wastewater testing to estimate community drug consumption", "تحليل مياه الصرف لتقدير الاستهلاك المجتمعي للمواد المخدرة",
         ["wastewater epidemiology", "consumption estimates", "biomarkers"], ["وبائيات مياه الصرف", "تقدير الاستهلاك", "المؤشرات الحيوية"]),
        ("peer support groups for recovering users", "مجموعات دعم الأقران للمتعافين من التعاطي",
         ["peer support", "recovery", "harm reduction"], ["دعم الأقران", "التعافي", "الحد من الضرر"]),
    ],
}


def load_generator():
    spec = importlib.util.spec_from_file_location("generate_synthetic_data", HERE / "generate_synthetic_data.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/synthetic_hard")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--mixed-share", type=float, default=0.4)
    args = parser.parse_args()

    gen = load_generator()
    gen.TOPICS = HARD_TOPICS
    rng = random.Random(args.seed)
    out = Path(args.out)
    (out / "raw" / "proposals").mkdir(parents=True, exist_ok=True)
    (out / "ground_truth").mkdir(parents=True, exist_ok=True)

    rows = []
    for i in range(1, args.n + 1):
        rnd = rng.choice([1, 2, 3])
        rec = gen.proposal_record(rng, i, rnd)
        if rec["secondary"] is None and rng.random() < args.mixed_share:
            other = rng.choice([p for p in gen.PRIORITIES if p != rec["content_priority"]])
            rec["secondary"] = rng.choice(HARD_TOPICS[other])[:2]
            rec["ambiguous"] = 1
        gen.write_proposal(rng, rec, out / "raw")
        rows.append({
            "grant_id": rec["grant_id"],
            "lang": rec["lang"],
            "claimed_priority": gen.PRIORITIES[rec["claimed_priority"]][0],
            "content_priority": gen.PRIORITIES[rec["content_priority"]][0],
            "claim_matches_content": rec["claim_matches_content"],
            "ambiguous": rec["ambiguous"],
            "missing_fields": rec["missing_fields"],
        })

    with open(out / "ground_truth" / "grants.csv", "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} hard proposals to {out / 'raw' / 'proposals'}")


if __name__ == "__main__":
    main()
