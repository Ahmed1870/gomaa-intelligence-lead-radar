from app.matching.services import match

def build(company, sector, lang="ar"):
    services=match(sector)
    labels=[m["label_ar"] if lang=="ar" else m["label_en"] for _,m in services]
    if lang=="ar":
        subject=f"فكرة عملية لتحويل بيانات {company} إلى قرارات أفضل"
        body=f"""مرحباً فريق {company}،

أراجع حالياً فرص تحسين استخدام البيانات داخل الشركات في قطاعكم، ولاحظت أن {company} قد تستفيد من تنظيم وتحليل البيانات بشكل يساعد على رؤية أوضح للأداء والعملاء.

في Gomaa Intelligence نساعد الشركات في:
• {labels[0]}
• {labels[1] if len(labels)>1 else labels[0]}
• {labels[2] if len(labels)>2 else labels[0]}

الهدف ليس مجرد تقرير؛ بل تحويل البيانات المتاحة إلى مؤشرات واضحة تساعدكم على معرفة أين توجد الفرصة وما الذي يستحق المتابعة.

استعرض الخدمات والتفاصيل:
https://gomaaintelligence.me/services/

تحياتي،
أحمد جمعة
Gomaa Intelligence"""
    else:
        subject=f"A practical way to turn {company}'s data into better decisions"
        body=f"""Hello {company} team,

Gomaa Intelligence helps businesses turn operational data into clear, decision-ready insights.

Relevant capabilities include:
• {labels[0]}
• {labels[1] if len(labels)>1 else labels[0]}
• {labels[2] if len(labels)>2 else labels[0]}

Services and details:
https://gomaaintelligence.me/services/

Best regards,
Ahmed Gomaa
Gomaa Intelligence"""
    return subject, body
