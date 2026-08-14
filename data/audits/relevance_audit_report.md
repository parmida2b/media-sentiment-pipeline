# گزارش Relevance Audit (چک‌لیست §۱۴)

## کل نمونه
- تعداد بررسی‌شده: ۱۲۰
- Precision تصمیم Inclusion: ۶۱.۰٪ (n=۴۱ رکورد Included سیستم بررسی شد)
- نرخ Exclusion اشتباه: ۳۸.۵٪ (n=۵۲ رکورد Excluded سیستم بررسی شد)
- Uncertain (خارج از هر دو نرخ بالا): ۲۷

## به تفکیک پلتفرم

### reddit
- تعداد بررسی‌شده: ۴۰
- Precision تصمیم Inclusion: ۶۳.۶٪ (n=۱۱)
- نرخ Exclusion اشتباه: ۱۱.۱٪ (n=۱۸)
- Uncertain: ۱۱

### x
- تعداد بررسی‌شده: ۴۰
- Precision تصمیم Inclusion: ۶۸.۸٪ (n=۱۶)
- نرخ Exclusion اشتباه: ۵۷.۹٪ (n=۱۹)
- Uncertain: ۵

### youtube
- تعداد بررسی‌شده: ۴۰
- Precision تصمیم Inclusion: ۵۰.۰٪ (n=۱۴)
- نرخ Exclusion اشتباه: ۴۶.۷٪ (n=۱۵)
- Uncertain: ۱۱

## گروه Excluded، به تفکیک دلیل واقعی خروج (`primary_exclusion_reason`)

نرخ Exclusion اشتباه در بخش‌های بالا روی **همه‌ی** ردیف‌های Excluded سیستم حساب شده
(`context_only` + `audit_only` + `quarantine`، یعنی مجموع همه‌ی گیت‌های Eligibility با هم).
این عدد، خطاهای قاعده‌ی موضوعی (Topic relevance) را با کارکردِ درستِ گیت‌های دیگر
(بازه زمانی، Provenance، متن خالی) قاطی می‌کند — رکوردی که به‌درستی به‌خاطر خارج بودن از
بازه زمانی پروژه حذف شده، حتی اگر انسان متنش را مرتبط با موضوع بداند، باگ قاعده‌ی
Relevance نیست. طبق §۷/§۱۴ سند `eligibility_rules_v03.md`، فقط دلیل `out_of_scope`
واقعاً به مرحله‌ی Topic relevance مربوط می‌شود؛ بقیه‌ی ردیف‌ها اینجا صرفاً برای
شفافیت/تشخیص آورده شده‌اند.

- `deleted_or_removed`: n=۱۳، با این حال انسان مرتبط تشخیص داده = ۰.۰٪
- `empty_text`: n=۷، با این حال انسان مرتبط تشخیص داده = ۰.۰٪
- `missing_content_id`: n=۱۲، با این حال انسان مرتبط تشخیص داده = ۵۰.۰٪
- `out_of_window`: n=۲۰، با این حال انسان مرتبط تشخیص داده = ۷۰.۰٪

(هیچ ردیفی با دلیل `out_of_scope` در این نمونه نبود — یعنی خودِ قاعده‌ی موضوعی صفر
خطای Exclusion نشان داد.)

## خطا به تفکیک Query
- `RQ-001`: n=۷، Precision Inclusion=۱۰۰.۰٪ (n=۳)، نرخ Exclusion اشتباه=۰.۰٪ (n=۴)، uncertain=۰
- `RQ-002`: n=۵، Precision Inclusion=۱۰۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=۰.۰٪ (n=۴)، uncertain=۰
- `RQ-003`: n=۳، Precision Inclusion=۱۰۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=۰.۰٪ (n=۱)، uncertain=۱
- `RQ-004`: n=۱، Precision Inclusion=ندارد (n=۰)، نرخ Exclusion اشتباه=۰.۰٪ (n=۱)، uncertain=۰
- `RQ-005`: n=۳، Precision Inclusion=۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=ندارد (n=۰)، uncertain=۲
- `RQ-006`: n=۸، Precision Inclusion=۶۶.۷٪ (n=۳)، نرخ Exclusion اشتباه=۳۳.۳٪ (n=۳)، uncertain=۲
- `RQ-007`: n=۷، Precision Inclusion=۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=۰.۰٪ (n=۲)، uncertain=۴
- `RQ-008`: n=۱، Precision Inclusion=ندارد (n=۰)، نرخ Exclusion اشتباه=۱۰۰.۰٪ (n=۱)، uncertain=۰
- `RQ-018`: n=۵، Precision Inclusion=۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=۰.۰٪ (n=۲)، uncertain=۲
- `XQ-001`: n=۲، Precision Inclusion=۱۰۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=۰.۰٪ (n=۱)، uncertain=۰
- `XQ-002`: n=۲، Precision Inclusion=۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=۱۰۰.۰٪ (n=۱)، uncertain=۰
- `XQ-003`: n=۱، Precision Inclusion=ندارد (n=۰)، نرخ Exclusion اشتباه=۱۰۰.۰٪ (n=۱)، uncertain=۰
- `XQ-004`: n=۱، Precision Inclusion=ندارد (n=۰)، نرخ Exclusion اشتباه=۱۰۰.۰٪ (n=۱)، uncertain=۰
- `XQ-005`: n=۵، Precision Inclusion=۶۶.۷٪ (n=۳)، نرخ Exclusion اشتباه=۰.۰٪ (n=۲)، uncertain=۰
- `XQ-006`: n=۱، Precision Inclusion=۱۰۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=ندارد (n=۰)، uncertain=۰
- `XQ-007`: n=۴، Precision Inclusion=۳۳.۳٪ (n=۳)، نرخ Exclusion اشتباه=ندارد (n=۰)، uncertain=۱
- `XQ-008`: n=۲، Precision Inclusion=ندارد (n=۰)، نرخ Exclusion اشتباه=۰.۰٪ (n=۱)، uncertain=۱
- `XQ-009`: n=۳، Precision Inclusion=۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=۰.۰٪ (n=۲)، uncertain=۰
- `XQ-011`: n=۲، Precision Inclusion=ندارد (n=۰)، نرخ Exclusion اشتباه=۱۰۰.۰٪ (n=۲)، uncertain=۰
- `XQ-013`: n=۱، Precision Inclusion=۱۰۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=ندارد (n=۰)، uncertain=۰
- `XQ-014`: n=۱، Precision Inclusion=۱۰۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=ندارد (n=۰)، uncertain=۰
- `XQ-015`: n=۱، Precision Inclusion=ندارد (n=۰)، نرخ Exclusion اشتباه=۰.۰٪ (n=۱)، uncertain=۰
- `XQ-017`: n=۱، Precision Inclusion=ندارد (n=۰)، نرخ Exclusion اشتباه=۱۰۰.۰٪ (n=۱)، uncertain=۰
- `XQ-018`: n=۱، Precision Inclusion=۱۰۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=ندارد (n=۰)، uncertain=۰
- `XQ-019`: n=۲، Precision Inclusion=ندارد (n=۰)، نرخ Exclusion اشتباه=۰.۰٪ (n=۱)، uncertain=۱
- `XQ-023`: n=۱، Precision Inclusion=۱۰۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=ندارد (n=۰)، uncertain=۰
- `XQ-024`: n=۲، Precision Inclusion=۱۰۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=۱۰۰.۰٪ (n=۱)، uncertain=۰
- `XQ-H01`: n=۷، Precision Inclusion=۱۰۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=۱۰۰.۰٪ (n=۴)، uncertain=۲
- `q_en_topic_1`: n=۲، Precision Inclusion=۰.۰٪ (n=۲)، نرخ Exclusion اشتباه=ندارد (n=۰)، uncertain=۰
- بدون Query ثبت‌شده (`nan`): n=۳۵، Precision Inclusion=۵۸.۳٪ (n=۱۲)، نرخ Exclusion اشتباه=۴۶.۷٪ (n=۱۵)، uncertain=۸

## خطا به تفکیک Source
- `RD-001`: n=۱۲، Precision Inclusion=۷۵.۰٪ (n=۴)، نرخ Exclusion اشتباه=۰.۰٪ (n=۶)، uncertain=۲
- `RD-002`: n=۵، Precision Inclusion=۵۰.۰٪ (n=۲)، نرخ Exclusion اشتباه=۰.۰٪ (n=۳)، uncertain=۰
- `RD-006`: n=۳، Precision Inclusion=۱۰۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=۰.۰٪ (n=۲)، uncertain=۰
- `RD-011`: n=۱، Precision Inclusion=ندارد (n=۰)، نرخ Exclusion اشتباه=۰.۰٪ (n=۱)، uncertain=۰
- `RD-012`: n=۲، Precision Inclusion=۱۰۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=ندارد (n=۰)، uncertain=۱
- `RD-014`: n=۱، Precision Inclusion=ندارد (n=۰)، نرخ Exclusion اشتباه=۰.۰٪ (n=۱)، uncertain=۰
- `RD-018`: n=۱، Precision Inclusion=۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=ندارد (n=۰)، uncertain=۰
- `RD-022`: n=۵، Precision Inclusion=۱۰۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=۵۰.۰٪ (n=۲)، uncertain=۲
- `RD-024`: n=۱، Precision Inclusion=ندارد (n=۰)، نرخ Exclusion اشتباه=۰.۰٪ (n=۱)، uncertain=۰
- `RD-026`: n=۲، Precision Inclusion=۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=۰.۰٪ (n=۱)، uncertain=۰
- `RD-028`: n=۱، Precision Inclusion=ندارد (n=۰)، نرخ Exclusion اشتباه=۱۰۰.۰٪ (n=۱)، uncertain=۰
- `YT-003`: n=۳، Precision Inclusion=۳۳.۳٪ (n=۳)، نرخ Exclusion اشتباه=ندارد (n=۰)، uncertain=۰
- `YT-004`: n=۳، Precision Inclusion=۱۰۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=۰.۰٪ (n=۱)، uncertain=۱
- `YT-009`: n=۲، Precision Inclusion=۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=ندارد (n=۰)، uncertain=۱
- `YT-024`: n=۲، Precision Inclusion=۰.۰٪ (n=۱)، نرخ Exclusion اشتباه=۰.۰٪ (n=۱)، uncertain=۰
- `YT-026`: n=۱، Precision Inclusion=ندارد (n=۰)، نرخ Exclusion اشتباه=۱۰۰.۰٪ (n=۱)، uncertain=۰
- `YT-030`: n=۵، Precision Inclusion=۱۰۰.۰٪ (n=۴)، نرخ Exclusion اشتباه=ندارد (n=۰)، uncertain=۱
- بدون Source ثبت‌شده (`nan`): n=۶۱، Precision Inclusion=۶۰.۰٪ (n=۲۰)، نرخ Exclusion اشتباه=۵۴.۸٪ (n=۳۱)، uncertain=۱۰
