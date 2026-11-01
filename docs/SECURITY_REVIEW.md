# بازبینی امنیتی فاز صفر

**تاریخ:** 2026-11-01  
**مبنای بررسی:** شاخه `feat/database-backed-auth-rate-limit` (روی PR پایه امنیتی)  
**نوع بررسی:** بازبینی ایستا و طراحی تست؛ نه ممیزی نفوذ مستقل  
**وضعیت:** یافته‌ها ثبت شده‌اند؛ موارد باز باید پیش از عرضه عمومی بسته شوند.

## خلاصه

در بررسی فعلی، کنترل‌های پایه‌ای مانند هش Argon2، توکن نشست تصادفی با ذخیره digest، انقضای نشست، اعتبارسنجی ورودی و جداسازی مالکیت منابع در Backend مشاهده شد. این کنترل‌ها مفیدند، اما برای عرضه عمومی کافی نیستند.

## یافته‌ها و اولویت

| اولویت | موضوع | وضعیت فعلی | اقدام لازم |
|---|---|---|---|
| P1 | Rate limiting ورود و ثبت‌نام | پیاده‌سازی شد؛ Backend و Frontend CI موفق | محدودیت دیتابیس‌محور مشترک: ثبت‌نام ۲۰ درخواست در ساعت به‌ازای IP و ورود ۵ درخواست در ۱۵ دقیقه به‌ازای IP+حساب؛ بررسی رفتار در محیط Production و تنظیم آستانه‌ها باقی است |
| P1 | ذخیره Bearer token در localStorage | در Frontend استفاده می‌شود؛ پیشنهاد معماری Cookie امن ثبت شده اما پیاده‌سازی نشده | تهیه دامنه اختصاصی مشترک برای app و API، سپس پیاده‌سازی و تست HttpOnly Cookie، CSRF و CORS پیش از عرضه عمومی |
| P1 | چرخه عمر حساب | تأیید ایمیل و بازیابی رمز وجود ندارد | تعریف جریان‌های امن و سیاست حذف حساب |
| P1 | بودجه و محدودیت درخواست AI | کنترل مصرف SaaS هنوز وجود ندارد | محدودیت زمان، هم‌زمانی، اندازه و بودجه در Backend |
| P2 | نشست‌های منقضی‌شده | هنگام استفاده حذف می‌شوند؛ پاک‌سازی زمان‌بندی‌شده نیست | job پاک‌سازی با batch و retention مشخص |
| P2 | پایش امنیتی | پوشش کامل نیست | ثبت رخدادهای ورود/خروج و هشدار بدون ثبت secret |
| P2 | مدیریت schema | Alembic فعال است؛ startup نیز create_all دارد | حفظ migrationهای صریح و آزمون upgrade روی schema قدیمی و تازه |
| P2 | CORS | originها از env محدود می‌شوند | بررسی تنظیم production و عدم استفاده از wildcard |

## کنترل‌های تأییدشده در کد

- Argon2 از طریق `pwdlib` برای هش رمز عبور.
- توکن نشست با `secrets.token_urlsafe` و ذخیره SHA-256 digest.
- انقضای نشست پس از ۷ روز.
- اعتبارسنجی Bearer token در dependency مشترک.
- جداسازی مالکیت Project، Conversation، Agent و Task در queryهای Backend.
- محدودیت طول ورودی‌ها با Pydantic.
- کلید AI Provider فقط در Backend خوانده می‌شود.
- endpoint آمادگی دیتابیس فقط `SELECT 1` اجرا می‌کند و جزئیات اتصال را افشا نمی‌کند.

## به‌روزرسانی پیاده‌سازی محدودسازی درخواست‌ها

- شمارنده‌های اتمیک fixed-window در دیتابیس مشترک ذخیره می‌شوند و بین پردازه‌ها/نمونه‌های Backend مشترک‌اند.
- شناسه bucket فقط به‌صورت SHA-256 ذخیره می‌شود؛ ایمیل و IP خام در جدول limiter نوشته نمی‌شوند.
- پاسخ محدودیت HTTP 429 همراه Retry-After است؛ در صورت خرابی storage، احراز هویت با HTTP 503 متوقف می‌شود (fail closed).
- migration با baseline فعلی سازگار شده و برای دیتابیس تازه و دیتابیس موجود طراحی شده است.
- Backend API tests و Frontend build checks روی commit `d6719cfd91d0434a96842c42da1834c138fab22c` موفق شدند (runs `41279651417` و `41279651386`). رفتار limiter روی سرویس Production هنوز آزمایش نشده است.

## تصمیم معماری برای Cookie امن

- پیشنهاد مهاجرت در `docs/AUTH_COOKIE_MIGRATION.md` و نسخه فارسی آن در `docs/fa/AUTH_COOKIE_MIGRATION.md` ثبت شد.
- به‌دلیل تفاوت site بین `github.io` و دامنه Render، استفاده مستقیم از third-party cookie برای Production انتخاب نشد.
- معماری هدف به زیردامنه‌های HTTPS زیر یک دامنه مشترک، Cookie نشست host-only با پیشوند `__Host-`، CORS دقیق و CSRF وابسته به نشست نیاز دارد.
- این تغییر صرفاً مستندسازی است؛ کد احراز هویت، DNS، دامنه، تنظیمات Production و روش Bearer فعلی تغییر نکرده‌اند.

## کار انجام‌شده در PR پایه

- تست دسترسی بدون احراز هویت برای فهرست، جزئیات و رویدادهای Task اضافه شد.
- تست عدم دسترسی کاربر دوم به Task و رویدادهای کاربر اول اضافه شد.
- مستندات احراز هویت با وضعیت واقعی Alembic و خطر localStorage همگام شد.
- نقشه معماری از ادعاهای قدیمی درباره نبود migration اصلاح شد.

## خارج از دامنه این مرحله

- تغییر روش ذخیره توکن به Cookie.
- افزودن سرویس rate-limit خارجی؛ limiter دیتابیس‌محور در این شاخه اضافه شده است.
- تغییرات schema خارج از migration صریح؛ migration `0002_auth_rate_limits` در این شاخه اضافه شده است.
- تغییر پیکربندی Production یا کلیدهای Provider.
- تست نفوذ یا ادعای تأیید امنیت مستقل.

## معیار خروج فاز صفر

1. تست‌های Backend روی آخرین commit موفق باشند.
2. تست مالکیت برای مسیرهای حساس داده موجود باشد.
3. مسیرهای ورود/ثبت‌نام، storage توکن، CORS و rate limiting برای عرضه عمومی تصمیم و مالک مشخص داشته باشند.
4. migration روی دیتابیس تازه و schema موجود در CI آزمایش شود.
5. هیچ secret یا داده شخصی در log و مخزن ثبت نشود.
6. یافته‌های P1 یا رفع شوند یا با تصمیم آگاهانه و محدودیت عرضه بتا پذیرفته شوند.

## محدودیت بررسی

این سند بر اساس خواندن کد و تست‌های مخزن تهیه شده است. پیکربندی واقعی همه سرویس‌های میزبانی، گزارش‌های زیرساخت، تست نفوذ و رفتار همه وابستگی‌های بیرونی در این بررسی تأیید نشده‌اند.


### Authentication rate-limit bucket retention

The database-backed limiter removes expired fixed-window buckets opportunistically during authentication requests. Cleanup uses the indexed `window_start` column and is limited to 500 rows per request to bound maintenance work. Buckets within the longest configured window are retained. This table is not an audit log. The stored SHA-256 bucket key is pseudonymous data, not guaranteed anonymous data.

- Validation coverage includes separate database sessions for shared limiter state, plus Alembic upgrade tests for fresh and pre-existing databases. CI execution is required before considering the change ready.
