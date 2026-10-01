"""۱۰ زبان اصلی. پیش‌فرض انگلیسی، فارسی دومین زبان. هر زبان ناقص، به انگلیسی برمی‌گرده."""

LANG_NAMES = {
    "en": "🇬🇧 English", "fa": "🇮🇷 فارسی", "ar": "🇸🇦 العربية", "tr": "🇹🇷 Türkçe",
    "ru": "🇷🇺 Русский", "de": "🇩🇪 Deutsch", "fr": "🇫🇷 Français", "es": "🇪🇸 Español",
    "zh": "🇨🇳 中文", "hi": "🇮🇳 हिन्दी",
}

_T = {
"en": {
 "welcome": "👋 Welcome to **Proxy Hunter Bot**!\nI hunt MTProto proxies for Telegram that work in Iran 🇮🇷\nPick an option below 👇",
 "btn_list": "📋 Proxy List", "btn_scan": "🔍 Scan Now", "btn_settings": "⚙️ Settings",
 "btn_log": "📜 Live Log", "btn_help": "📖 How it works", "btn_lang": "🌐 Language",
 "btn_admin": "👑 Admins", "btn_public": "🌍 Public Mode", "btn_ai": "🧠 Proxy AI",
 "btn_back": "🔙 Back", "btn_file": "📄 Send as file", "btn_inline": "📝 Send as text",
 "scanning": "⏳ Scanning the whole internet for MTProto proxies...",
 "scan_done": "✅ Scan complete!\n🆕 New: {new}\n✅ Alive: {alive}\n❌ Dead: {dead}",
 "no_proxies": "No proxies yet. Run a scan first 🔍",
 "settings_txt": "⚙️ **Settings**\n🕐 Scan interval: {interval} min\n🧵 Threads: {threads}\n📦 Batch size: {batch}",
 "set_interval": "🕐 Send new scan interval (minutes):",
 "set_threads": "🧵 Send new thread count:",
 "set_batch": "📦 Send batch size (how many to send at once):",
 "saved": "✅ Saved!",
 "admin_only": "⛔ Admins only!",
 "choose_lang": "🌐 Choose your language:",
 "log_empty": "No logs yet.",
 "help": ("📖 **How the bot works**\n\n"
          "1️⃣ **Collect** — scrapes dozens of sources (GitHub lists, Telegram channels, APIs) for MTProto proxies.\n"
          "2️⃣ **Dedupe** — removes all duplicate proxies.\n"
          "3️⃣ **Ping test** — checks each proxy's latency.\n"
          "4️⃣ **Speed test** — measures download/upload through each proxy.\n"
          "5️⃣ **Filter** — ranks by score (ping 60% + speed 40%) and keeps the best.\n\n"
          "🤖 The bot runs 24/7 on GitHub Actions and restarts itself before each run expires.\n"
          "💾 Everything is saved to a local DB every second — nothing is ever lost.\n"
          "🧠 **Proxy AI** finds new sources with Tavily search and can manage the project."),
 "public_on": "🌍 Public mode ON — anyone can use the bot (sensitive actions still admin-only).",
 "public_off": "🔒 Public mode OFF — admins only.",
 "admin_list": "👑 **Admins:**\n{list}",
 "admin_add": "Send the user ID to add as admin:",
 "admin_del": "Send the user ID to remove:",
 "ai_need_cfg": "🧠 First-time AI setup.\nSend the **base_url** of your AI provider:",
 "ai_need_key": "🔑 Now send the **API key**:",
 "ai_models": "📡 Fetching available models...",
 "ai_pick": "Pick a model:",
 "ai_ready": "🧠 Proxy AI is ready! Chat with me — I can find sources, fix bugs, change the project (sensitive actions need your approval).",
 "ai_approve": "⚠️ Sensitive action requested:\n{action}\nApprove?",
 "proxy_line": "🔗 `tg://proxy?server={s}&port={p}&secret={k}`\n⚡ {ping}ms | ⬇️ {dl}KB/s ⬆️ {ul}KB/s | ⭐ {score}",
},
"fa": {
 "welcome": "👋 سلام داداش! به **بات شکارچی پروکسی** خوش اومدی!\nپروکسی‌های MTProto تلگرام که توی ایران کار می‌کنن رو برات پیدا می‌کنم 🇮🇷\nیکی از گزینه‌ها رو بزن 👇",
 "btn_list": "📋 لیست پروکسی‌ها", "btn_scan": "🔍 اسکن الان", "btn_settings": "⚙️ تنظیمات",
 "btn_log": "📜 لاگ زنده", "btn_help": "📖 طرز کار", "btn_lang": "🌐 زبان",
 "btn_admin": "👑 ادمین‌ها", "btn_public": "🌍 حالت عمومی", "btn_ai": "🧠 هوش مصنوعی",
 "btn_back": "🔙 برگشت", "btn_file": "📄 ارسال فایل", "btn_inline": "📝 ارسال متنی",
 "scanning": "⏳ دارم کل اینترنت رو برای پروکسی MTProto می‌گردم...",
 "scan_done": "✅ اسکن تموم شد!\n🆕 جدید: {new}\n✅ سالم: {alive}\n❌ مرده: {dead}",
 "no_proxies": "هنوز پروکسی‌ای نیست. اول اسکن بزن 🔍",
 "settings_txt": "⚙️ **تنظیمات**\n🕐 فاصله اسکن: {interval} دقیقه\n🧵 تعداد ترید: {threads}\n📦 تعداد هر دسته: {batch}",
 "set_interval": "🕐 فاصله اسکن جدید رو بفرست (دقیقه):",
 "set_threads": "🧵 تعداد ترید جدید رو بفرست:",
 "set_batch": "📦 تعداد پروکسی هر دسته رو بفرست:",
 "saved": "✅ ذخیره شد!",
 "admin_only": "⛔ فقط ادمین!",
 "choose_lang": "🌐 زبانت رو انتخاب کن:",
 "log_empty": "هنوز لاگی نیست.",
 "help": ("📖 **بات چطور کار می‌کنه**\n\n"
          "۱️⃣ **جمع‌آوری** — از ده‌ها منبع (لیست‌های گیت‌هاب، کانال‌های تلگرام، API) پروکسی MTProto جمع می‌کنه.\n"
          "۲️⃣ **حذف تکراری** — همه پروکسی‌های تکراری پاک می‌شن.\n"
          "۳️⃣ **تست پینگ** — تأخیر هر پروکسی چک می‌شه.\n"
          "۴️⃣ **تست سرعت** — دانلود و آپلود هر پروکسی سنجیده می‌شه.\n"
          "۵️⃣ **فیلتر نهایی** — بر اساس امتیاز (پینگ ۶۰٪ + سرعت ۴۰٪) بهترین‌ها نگه داشته می‌شن.\n\n"
          "🤖 بات ۲۴ ساعته روی GitHub Actions روشنه و قبل از تموم شدن هر ران، خودش ران جدید می‌زنه.\n"
          "💾 همه‌چیز هر ثانیه توی دیتابیس لوکال ذخیره می‌شه — هیچی گم نمی‌شه.\n"
          "🧠 **Proxy AI** با سرچ Tavily منابع جدید پیدا می‌کنه و می‌تونه پروژه رو مدیریت کنه."),
 "public_on": "🌍 حالت عمومی روشن شد — همه می‌تونن استفاده کنن (کارهای حساس فقط ادمین).",
 "public_off": "🔒 حالت عمومی خاموش شد — فقط ادمین‌ها.",
 "admin_list": "👑 **ادمین‌ها:**\n{list}",
 "admin_add": "آیدی عددی کاربر رو بفرست تا ادمین بشه:",
 "admin_del": "آیدی عددی کاربر رو بفرست تا حذف بشه:",
 "ai_need_cfg": "🧠 راه‌اندازی اولیه هوش مصنوعی.\n**base_url** سرویس AI رو بفرست:",
 "ai_need_key": "🔑 حالا **API key** رو بفرست:",
 "ai_models": "📡 دارم مدل‌های موجود رو می‌گیرم...",
 "ai_pick": "یه مدل انتخاب کن:",
 "ai_ready": "🧠 Proxy AI آماده‌ست! باهام حرف بزن — می‌تونم منابع جدید پیدا کنم، باگ فیکس کنم، پروژه رو تغییر بدم (کارهای حساس با اجازه تو).",
 "ai_approve": "⚠️ درخواست کار حساس:\n{action}\nتأیید می‌کنی؟",
 "proxy_line": "🔗 `tg://proxy?server={s}&port={p}&secret={k}`\n⚡ {ping}ms | ⬇️ {dl}KB/s ⬆️ {ul}KB/s | ⭐ {score}",
},
"ar": {"welcome": "👋 أهلاً بك في بوت صائد البروكسي!", "choose_lang": "🌐 اختر لغتك:"},
"tr": {"welcome": "👋 Proxy Avcısı Botuna hoş geldin!", "choose_lang": "🌐 Dilini seç:"},
"ru": {"welcome": "👋 Добро пожаловать в Proxy Hunter Bot!", "choose_lang": "🌐 Выберите язык:"},
"de": {"welcome": "👋 Willkommen beim Proxy Hunter Bot!", "choose_lang": "🌐 Sprache wählen:"},
"fr": {"welcome": "👋 Bienvenue sur Proxy Hunter Bot !", "choose_lang": "🌐 Choisissez votre langue :"},
"es": {"welcome": "👋 ¡Bienvenido a Proxy Hunter Bot!", "choose_lang": "🌐 Elige tu idioma:"},
"zh": {"welcome": "👋 欢迎使用代理猎手机器人！", "choose_lang": "🌐 请选择语言："},
"hi": {"welcome": "👋 प्रॉक्सी हंटर बॉट में स्वागत है!", "choose_lang": "🌐 अपनी भाषा चुनें:"},
}


def t(key, lang="en", **kw):
    s = _T.get(lang, {}).get(key) or _T["en"].get(key, key)
    return s.format(**kw) if kw else s
