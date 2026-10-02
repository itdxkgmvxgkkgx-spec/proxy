# ProxyBot — ربات شکارچی پروکسی MTProto تلگرام (۲۴ ساعته روی GitHub Actions)

> English version below ⬇️

ربات تلگرامی که **همیشه روشنه**، کل اینترنت رو دنبال پروکسی‌های MTProto می‌گرده، اون‌ها رو با **هندشیک واقعی MTProto** تست می‌کنه، سرعت می‌گیره، از **داخل ایران** چک می‌کنه و بهترین‌ها رو تحویلت می‌ده. یه **Proxy AI** با معماری Hermes Agent هم داره که می‌تونه کل پروژه رو ببینه، منابع جدید پیدا کنه، باگ فیکس کنه و با اجازه‌ی تو تغییر بده.

## ✅ امکانات

| بخش | چی داره |
|---|---|
| **۲۴/۷ روی GitHub Actions** | هر ران ~۵.۵ ساعت کار می‌کنه، دیتابیس رو کامیت می‌کنه و با `GH_PAT` ران بعدی رو خودش می‌زنه. جاب `relay` + کرون ساعتی هم watchdog هستن. اگه دو تا ران همزمان بشن، جدیده قدیمیه رو کنسل می‌کنه. |
| **هیچ دیتایی گم نمی‌شه** | همه چیز تو `data/proxybot.db` (SQLite WAL). هر ۳۰ ثانیه `data/` کامیت و پوش می‌شه + آرتیفکت. ران جدید دقیقاً از همونجا ادامه می‌ده (تنظیمات، ادمین‌ها، پروکسی‌ها، تاریخچه، حافظه و نشست‌های AI). |
| **پایپ‌لاین ۵ مرحله‌ای** | ۱) جمع‌آوری از ۶۰+ منبع (گیت‌هاب، APIها، ۴۰ کانال تلگرام) ۲) حذف تکراری ۳) پینگ = هندشیک کامل MTProto (fake-TLS + obfuscated2 + `req_pq_multi` → `resPQ`) ۴) تست سرعت ⬇️⬆️ ۵) فیلتر و امتیازدهی ۰-۱۰۰ + چک دسترسی **از نودهای ایران** (check-host.net) |
| **منابع خودافزا** | هر ۴ ران، GitHub Search رو می‌گرده و ریپوهای جدید پروکسی رو خودش اضافه می‌کنه (بدون کلید). Proxy AI هم با **Tavily** هر ۶ ران منبع جدید پیدا می‌کنه. منابع خراب بعد ۱۰ خطا خودکار غیرفعال می‌شن. |
| **ربات تلگرام** | منوی شیشه‌ای (inline) + کیبورد پایین + لیست کامند. ۱۰ زبان (پیش‌فرض انگلیسی، فارسی دوم). پروکسی‌ها: لیست / دونه‌دونه / یکجا / فایل txt+json، با تعداد قابل تنظیم. وضعیت، لاگ زنده (مرحله + شمارنده‌ها)، تاریخچه بر اساس تاریخ، تنظیمات کامل (ترد، تایم‌اوت، فاصله اسکن، …)، توضیح کامل نحوه کار. |
| **دسترسی** | پیش‌فرض خصوصی (مالک = `ADMIN_ID`). دکمه **🌍 Public** → همه می‌تونن پروکسی بگیرن ولی اسکن/تنظیمات/منابع/AI/ادمین محفوظه. ادمین جدید با آیدی (یا فوروارد) + دسترسی جداگانه (`scan settings sources ai admins logs` یا `*`). |
| **Proxy AI (Hermes-style)** | اولین بار `base_url` + `API key` می‌گیره، لیست مدل‌ها رو میاره تا انتخاب کنی. ۲۹ ابزار: خوندن/جستجوی فایل، شل، کوئری/نوشتن DB، تنظیمات، منابع، اجرای پایپ‌لاین، تست پروکسی، Tavily، حافظه، اسکیل، جستجوی نشست‌های قبلی، git commit. **کارهای حساس معلق می‌شن و با دکمه ✅/❌ تأیید می‌کنی**؛ کارهای خطرناک (حذف data، force push، چاپ سکرت) اصلاً اجرا نمی‌شن. حافظه‌ی محدود `MEMORY.md`/`USER.md` با نوتیف 💾 برای هر نوشتن، اسکیل‌های قابل یادگیری (`data/skills/`). |

## 🚀 راه‌اندازی (۵ دقیقه)

1. این ریپو رو **Fork** یا آپلود کن (public یا private فرقی نداره؛ private رایگان ۲۰۰۰ دقیقه/ماه داره، public نامحدود).
2. **Settings → Secrets and variables → Actions → New repository secret**:

   | Secret | مقدار |
   |---|---|
   | `BOT_TOKEN` | توکن ربات از @BotFather |
   | `ADMIN_ID` | آیدی عددی تلگرام خودت (از @userinfobot) |
   | `GH_PAT` | Personal Access Token (classic) با scope های `repo` و `workflow` — [ساخت](https://github.com/settings/tokens/new?scopes=repo,workflow) |
   | `TAVILY_API_KEY` | (اختیاری) کلید [Tavily](https://tavily.com) برای کشف منابع با AI |

3. **Settings → Actions → General → Workflow permissions → Read and write permissions** ✅
4. **Actions → proxybot → Run workflow**. (بعد از این دیگه خودش زنجیره‌ای ادامه می‌ده.)
5. تو تلگرام `/start` بزن → زبان رو انتخاب کن → ۲۰ ثانیه بعد اولین اسکن شروع می‌شه.
6. برای AI: `/ai_setup` → `base_url` (مثلاً `https://openrouter.ai/api/v1` یا `https://api.openai.com/v1`) → کلید → مدل.

## 🧭 دستورات
`/start` منو · `/proxies` · `/scan` · `/status` · `/log` · `/history` · `/settings` · `/sources` · `/ai` (یا هر پیام متنی) · `/ai_new` · `/ai_setup` · `/pending` · `/admins` · `/public` · `/lang` · `/explain` · `/ping` · `/cancel`

## 🗂 معماری فایل‌ها
```
run.py                          نقطه شروع: بات + زمان‌بند + ذخیره‌ساز + تحویل ۶ ساعته
.github/workflows/proxybot.yml  ورک‌فلو زنجیره‌ای (relay + cron watchdog + artifact)
proxybot/core/config.py         DEFAULT_SETTINGS (همه تنظیمات) + Secrets
proxybot/core/database.py       اسکیمای SQLite و همه کوئری‌ها
proxybot/core/persistence.py    commit/push خودکار data/ + workflow_dispatch
proxybot/core/logger.py         لاگ → stdout + فایل + جدول logs + set_stage()
proxybot/pipeline/sources.py    منابع پیش‌فرض + کشف خودکار از GitHub
proxybot/pipeline/parser.py     استخراج tg://proxy, t.me/proxy, JSON, host:port:secret
proxybot/pipeline/mtproto.py    تستر واقعی MTProto (fake-TLS, obfuscated2, req_pq) + سرعت
proxybot/pipeline/iran_check.py چک TCP از نودهای ایرانی check-host.net
proxybot/pipeline/runner.py     ۵ مرحله + compute_score
proxybot/bot/handlers.py        منوها، پروکسی، تنظیمات، ادمین، منابع، تاریخچه، لاگ
proxybot/bot/ai_handlers.py     چت AI، ویزارد setup، تأییدها، حافظه/اسکیل، کشف منابع
proxybot/bot/scheduler.py       اسکن دوره‌ای + کشف AI دوره‌ای + handover
proxybot/ai/agent.py            حلقه ایجنت (OpenAI-compatible tools loop)
proxybot/ai/tools.py            ۲۹ ابزار + طبقه‌بندی خطر (safe/approve/hardline)
proxybot/ai/prompts.py          سیستم‌پرامپت سه‌لایه (stable/context/volatile)
proxybot/ai/memory.py           MEMORY.md / USER.md (محدود، با اسکن تزریق)
proxybot/ai/skills.py           اسکیل‌ها (progressive disclosure)
proxybot/ai/bundled_skills/     اسکیل‌های پیش‌فرض: معماری پروژه، کشف منبع، باگ‌فیکس
proxybot/i18n/strings.py        ۱۰ زبان
data/                           ← همه دیتا (در گیت کامیت می‌شه)
tests/                          ۳۰ تست (parser, core, agent با LLM فیک, جریان بات)
```

## 🗄 دیتابیس (`data/proxybot.db`)
`settings` · `users` · `admins` · `sources` · `proxies` · `proxy_history` · `runs` · `logs` · `ai_sessions` · `ai_messages` · `ai_pending` · `kv`

## ⚙️ تنظیمات مهم (از ⚙️ یا با AI)
`scan_interval_min=15` · `threads=64` · `speed_threads=12` · `ping_timeout=4` · `max_ping_ms=1500` · `min_score=20` · `top_n=30` · `iran_check=1` · `retention_days=30` · `save_interval_sec=30` · `github_discover_every=4` · `ai_discover_every=6` · `ai_memory_notify=verbose` · `public_mode=0`

## 🧪 تست محلی
```bash
pip install -r requirements.txt
python -m pytest tests -q                  # 30 passed
BOT_TOKEN=x ADMIN_ID=1 python run.py --scan   # یه اسکن واقعی (نتیجه نمونه: 1559 یکتا → 1061 زنده در 147 ثانیه)
BOT_TOKEN=... ADMIN_ID=... python run.py      # اجرای کامل ربات
```

## ❗ نکات
- امتیاز سرعت نسبیه (MTProto بدون auth-key دانلود حجیم نداره)؛ ولی رتبه‌بندی پایداره.
- چک ایران فقط روی ۱۵ تای برتر هر ران انجام می‌شه (API رایگان و محدود).
- تغییر کد توسط AI بعد از `git_commit` با ران بعدی اعمال می‌شه (پوش خودکار با persister).
- اگه `TelegramConflictError` دیدی یعنی دو ران همزمان شدن؛ ربات خودش قدیمی رو کنسل می‌کنه و ۸ ثانیه صبر می‌کنه.

---

# ProxyBot (English)

Always-on Telegram MTProto proxy hunter that runs for free on GitHub Actions and chains itself with `GH_PAT`.

**Pipeline**: collect (60+ sources, self-growing via GitHub search + Tavily AI) → dedupe → real MTProto handshake ping (fake-TLS/obfuscated2/`req_pq_multi`) → throughput probe → score 0-100 with Iran-reachability check (check-host.net Iranian nodes).

**Bot**: inline + reply keyboards + command list, 10 languages (EN default, FA second), proxies as list / one-by-one / batch / txt+json file, live log with stage, history by date, full settings, public mode, admins with granular permissions, full "how it works" page.

**Proxy AI**: Hermes-Agent-style loop with 29 tools, bounded memory (`MEMORY.md`/`USER.md`) with 💾 notifications, learnable skills, session search, Tavily web search; dangerous actions are staged and approved with ✅/❌ buttons; hardline actions are blocked.

**Setup**: fork → secrets `BOT_TOKEN`, `ADMIN_ID`, `GH_PAT` (repo+workflow), optional `TAVILY_API_KEY` → Actions permissions read/write → run the `proxybot` workflow once → `/start` in Telegram → `/ai_setup` for the AI.

**Persistence**: single SQLite file in `data/` committed every 30 s + artifact copy; a new run resumes exactly where the previous one stopped.

Tests: `python -m pytest tests -q` (30 tests). Smoke: `BOT_TOKEN=x ADMIN_ID=1 python run.py --scan`.
