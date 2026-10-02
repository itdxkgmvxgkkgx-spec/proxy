# flake8: noqa
"""UI strings. English + Persian are complete; the other 8 languages cover the
whole menu surface and fall back to English for the long explanatory texts."""

EN = {
    "welcome": "👋 Welcome to <b>ProxyBot</b> — a 24/7 Telegram MTProto proxy hunter.\n\nChoose your language first:",
    "lang_set": "✅ Language set to {lang}.",
    "main_menu": "🏠 <b>Main menu</b>\nStatus: {status}\nAlive proxies: <b>{alive}</b> · listed: <b>{listed}</b> · total known: {total}\nNext scan in: {next}",
    "not_allowed": "⛔ This bot is private. Ask the owner to enable public mode or add you as admin.",
    "admin_only": "🔒 Admins only.",
    "owner_only": "🔒 Owner only.",
    "no_perm": "🔒 You lack the <code>{perm}</code> permission.",
    "cancel": "❌ Cancel", "back": "🔙 Back", "done": "✅ Done.", "yes": "✅ Yes", "no": "❌ No",
    "cancelled": "Cancelled.", "invalid_number": "Please send a valid number.",
    "ping": "🏓 pong — {ms} ms",
    "btn_proxies": "📡 Proxies", "btn_scan": "🔄 Scan now", "btn_status": "📊 Status", "btn_log": "📜 Log",
    "btn_settings": "⚙️ Settings", "btn_history": "🗓 History", "btn_ai": "🤖 Proxy AI", "btn_explain": "📖 How it works",
    "btn_admins": "👮 Admins", "btn_lang": "🌐 Language", "btn_sources": "🔗 Sources", "btn_public": "🌍 Public: {state}",
    "btn_help": "❓ Help", "on": "ON", "off": "OFF",
    "proxies_menu": "📡 <b>Proxies</b> — {n} alive, {listed} pass the filter.\nHow do you want them?",
    "btn_send_single": "📤 One by one", "btn_send_batch": "📦 All in one message", "btn_send_file": "📄 As file",
    "btn_count": "🔢 Count: {n}", "btn_list": "📋 List top {n}",
    "no_proxies": "😕 No alive proxies yet. Run a scan first.",
    "proxy_card": "{i}. <b>{host}</b>:{port}\n   ⏱ {ping} ms · ⬇️ {down} KB/s · ⬆️ {up} KB/s · ⭐ {score}\n   🇮🇷 {iran} · type: {stype}\n   <a href=\"{link}\">Connect</a>",
    "proxy_line": "{i}. ⏱{ping}ms ⭐{score} <a href=\"{link}\">{host}:{port}</a>",
    "iran_ok": "reachable from Iran", "iran_bad": "BLOCKED in Iran", "iran_unknown": "Iran: untested",
    "file_caption": "📄 Top {n} proxies — {ts}",
    "ask_count": "How many proxies? (1-{max})",
    "scan_started": "🔄 Scan started. I'll report when done. Use 📜 Log to watch progress.",
    "scan_running": "⏳ A scan is already running (stage: {stage}).",
    "scan_done": "✅ <b>Scan finished</b> in {sec}s\n• sources ok/failed: {ok}/{failed}\n• found: {found} · unique: {uniq}\n• alive: {alive} · speed-tested: {speed}\n• listed: <b>{listed}</b>",
    "status": "📊 <b>Status</b>\nStage: <b>{stage}</b> {detail} {progress}\nRun #{run} on GitHub run <code>{gh}</code> · uptime {uptime}\nProxies: alive {alive} · flaky {flaky} · dead {dead} · total {total}\nSources: {src_on} enabled / {src_all}\nUsers: {users} · Admins: {admins}\nAuto scan: {auto} every {interval} min · next in {next}\nLast save: {save} · saves this run: {saves}\nAI: {ai}",
    "log_title": "📜 <b>Log</b> — current stage: <b>{stage}</b> {detail} {progress}\n\n",
    "log_empty": "No log lines yet.",
    "btn_log_refresh": "🔄 Refresh", "btn_log_errors": "⚠️ Errors only", "btn_log_all": "📜 All",
    "history_title": "🗓 <b>History</b> (last {days} days). Tap a day:",
    "history_day": "🗓 <b>{day}</b> — {n} alive proxies tested that day:\n\n",
    "history_empty": "No history yet.",
    "history_row": "{day} · tested {tested} · alive {alive} · avg {avg} ms",
    "settings_title": "⚙️ <b>Settings</b> — tap to change",
    "set_prompt": "Send new value for <b>{key}</b>\n<i>{desc}</i>\nCurrent: <code>{cur}</code>",
    "set_ok": "✅ <b>{key}</b> = <code>{val}</code>",
    "set_err": "❌ Invalid value: {err}",
    "grp_sched": "⏰ Scheduler", "grp_pipe": "🧪 Pipeline", "grp_bot": "🤖 Bot", "grp_ai": "🧠 AI",
    "public_on": "🌍 Public mode <b>ON</b> — anyone can use proxy menus. Admin menus stay protected.",
    "public_off": "🔒 Public mode <b>OFF</b> — only admins can use the bot.",
    "admins_title": "👮 <b>Admins</b>\n{list}\n\nPermissions: <code>*</code> all · <code>scan</code> · <code>settings</code> · <code>sources</code> · <code>ai</code> · <code>admins</code> · <code>logs</code>",
    "btn_add_admin": "➕ Add admin", "btn_del_admin": "➖ Remove admin", "btn_perm_admin": "🔧 Permissions",
    "ask_admin_id": "Send the Telegram user id (number) of the new admin. You can also forward a message from them.",
    "ask_admin_perms": "Send permissions separated by spaces, e.g. <code>scan logs ai</code> — or <code>*</code> for everything.",
    "admin_added": "✅ Admin {id} added with {perms}.",
    "admin_removed": "✅ Admin {id} removed.",
    "admin_cannot_remove_owner": "❌ Cannot remove the owner.",
    "admin_pick": "Pick an admin:",
    "sources_title": "🔗 <b>Sources</b> — {on} enabled / {all} total · last run: {ok} ok, {failed} failed\nBuilt-in: {builtin} · AI-found: {ai} · manual: {manual}",
    "btn_add_source": "➕ Add URL", "btn_list_sources": "📋 Top sources", "btn_bad_sources": "💀 Failing sources",
    "btn_ai_discover": "🧠 AI discover now",
    "ask_source_url": "Send the source URL (raw list, page or https://t.me/s/channel).",
    "source_added": "✅ Source added.", "source_exists": "Already in the list.",
    "explain": """📖 <b>How ProxyBot works</b>

<b>Runtime</b>
Runs as a GitHub Actions job (free). GitHub kills jobs after 6h, so ~5.5h in the bot commits its database, triggers the next workflow run with your <code>GH_PAT</code> and exits. The new run checks out the repo (with the fresh <code>data/</code>) and continues — nothing is lost. Every 30s (setting <code>save_interval_sec</code>) <code>data/</code> is committed &amp; pushed, and the SQLite file is also uploaded as an artifact as a second safety net.

<b>Storage</b> — one SQLite file <code>data/proxybot.db</code> (WAL mode): settings, users, admins, sources, proxies, per-run history, logs, AI sessions, pending approvals. AI long-term memory lives in <code>data/memory/MEMORY.md</code> &amp; <code>USER.md</code>, skills in <code>data/skills/*/SKILL.md</code>.

<b>Pipeline (5 stages)</b>
1️⃣ <b>Collect</b> — fetch every enabled source in parallel (GitHub lists, aggregator APIs, public Telegram channels via t.me/s/…). Parses tg://proxy links, t.me/proxy links, JSON and host:port:secret triples.
2️⃣ <b>Dedupe</b> — unique (host, port, secret); previously alive proxies are re-tested even if no source lists them any more.
3️⃣ <b>Ping</b> — not a TCP ping: a <i>real MTProto handshake</i> (fake-TLS ClientHello + HMAC check for <code>ee</code> secrets, Obfuscated2 init, <code>req_pq_multi</code> to Telegram DC2 through the proxy; the <code>resPQ</code> answer must echo our nonce). <code>threads</code> proxies in parallel.
4️⃣ <b>Speed</b> — repeated handshake round-trips through the proxy give relative ⬇️/⬆️ KB/s (<code>speed_threads</code>, <code>speed_bytes</code>).
5️⃣ <b>Filter</b> — score 0-100 = 45% ping + 30% throughput + 15% stability (last 10 tests) + 10% Iran reachability (checked from Iranian nodes of check-host.net; blocked = −40). Proxies slower than <code>max_ping_ms</code> or under <code>min_score</code> are dropped; the best <code>top_n</code> are listed.

<b>Scheduler</b> — every <code>scan_interval_min</code> minutes (change in ⚙️). Old proxies are kept <code>retention_days</code> days so 🗓 History can show any date.

<b>Proxy AI</b> — a Hermes-Agent-style assistant with tools: read/write project files, run shell commands, query the DB, change settings, run the pipeline, search the web with Tavily, learn skills, and persistent memory. Dangerous actions (shell, file writes, deleting, settings) are <b>staged</b> and you approve them with buttons. Every memory write sends you a 💾 notification.

<b>Access</b> — private by default (owner = <code>ADMIN_ID</code>). 🌍 Public lets anyone fetch proxies; scan/settings/sources/AI/admins stay admin-only with per-admin permissions.""",
    "help": "Commands:\n/start — menu\n/proxies — get proxies\n/scan — run pipeline\n/status — status\n/log — live log\n/history — by date\n/settings — settings\n/sources — proxy sources\n/ai — talk to Proxy AI\n/ai_new — new AI session\n/ai_setup — configure AI\n/pending — approve AI actions\n/admins — manage admins\n/public — toggle public mode\n/lang — language\n/explain — how it works\n/ping — bot latency\n/cancel — cancel current input",
    "ai_setup_url": "🤖 <b>Proxy AI setup</b> (step 1/3)\nSend the OpenAI-compatible <b>base_url</b>, e.g. <code>https://api.openai.com/v1</code> or <code>https://openrouter.ai/api/v1</code>",
    "ai_setup_key": "Step 2/3 — send the <b>API key</b>. (Your message will be deleted.)",
    "ai_setup_models": "Step 3/3 — fetched <b>{n}</b> models. Pick one (or send the model id):",
    "ai_setup_models_fail": "Could not list models ({err}). Send the model id manually:",
    "ai_setup_done": "✅ AI configured: <code>{model}</code> @ {url}",
    "ai_not_configured": "🤖 AI is not configured yet. Run /ai_setup.",
    "ai_menu": "🤖 <b>Proxy AI</b>\nModel: <code>{model}</code>\nSession #{sid} · {msgs} messages · pending approvals: {pending}\nMemory: {mem_pct}% · User profile: {user_pct}%\n\nJust send me a message to talk. Tools: {tools}",
    "btn_ai_new": "🆕 New session", "btn_ai_setup": "🔧 Setup", "btn_ai_model": "🧠 Model", "btn_ai_memory": "💾 Memory",
    "btn_ai_pending": "⏳ Pending ({n})", "btn_ai_skills": "📚 Skills", "btn_ai_discover": "🔎 Discover sources",
    "ai_thinking": "🤔 thinking…",
    "ai_tool": "🔧 <code>{tool}</code> {args}",
    "ai_approval": "⚠️ <b>Approval needed</b> #{id}\nTool: <code>{tool}</code>\n{reason}\n<pre>{args}</pre>",
    "btn_approve": "✅ Approve", "btn_deny": "❌ Deny", "btn_approve_all": "✅ Approve all", "btn_deny_all": "❌ Deny all",
    "ai_approved": "✅ #{id} approved — running…", "ai_denied": "❌ #{id} denied.",
    "ai_no_pending": "No pending actions.",
    "ai_memory_saved": "💾 Memory {action} ({target}): <i>{text}</i>",
    "ai_skill_saved": "📚 Skill <b>{name}</b> {action}",
    "ai_new_session": "🆕 New AI session started. The old one is searchable with session_search.",
    "ai_error": "❌ AI error: {err}",
    "ai_memory_view": "💾 <b>MEMORY.md</b> ({m_used}/{m_max})\n<pre>{memory}</pre>\n\n👤 <b>USER.md</b> ({u_used}/{u_max})\n<pre>{user}</pre>",
    "ai_discover_started": "🔎 Asking the AI to hunt for new proxy sources with Tavily…",
    "ai_busy": "⏳ The AI is still working on your previous message.",
    "ai_models_pick": "Pick a model:",
    "ai_skills_view": "📚 <b>Skills</b>\n{list}",
    "handover": "♻️ Run budget reached — handing over to a fresh GitHub run. Back in ~1 minute.",
}

FA = {
    "welcome": "👋 به <b>ProxyBot</b> خوش اومدی — شکارچی ۲۴ ساعته پروکسی MTProto تلگرام.\n\nاول زبانت رو انتخاب کن:",
    "lang_set": "✅ زبان روی {lang} تنظیم شد.",
    "main_menu": "🏠 <b>منوی اصلی</b>\nوضعیت: {status}\nپروکسی زنده: <b>{alive}</b> · لیست‌شده: <b>{listed}</b> · کل شناخته‌شده: {total}\nاسکن بعدی تا: {next}",
    "not_allowed": "⛔ این ربات خصوصیه. از مالک بخواه حالت عمومی رو فعال کنه یا تو رو ادمین کنه.",
    "admin_only": "🔒 فقط ادمین‌ها.", "owner_only": "🔒 فقط مالک.",
    "no_perm": "🔒 دسترسی <code>{perm}</code> نداری.",
    "cancel": "❌ لغو", "back": "🔙 برگشت", "done": "✅ انجام شد.", "yes": "✅ بله", "no": "❌ نه",
    "cancelled": "لغو شد.", "invalid_number": "لطفاً یه عدد معتبر بفرست.",
    "ping": "🏓 pong — {ms} میلی‌ثانیه",
    "btn_proxies": "📡 پروکسی‌ها", "btn_scan": "🔄 اسکن الان", "btn_status": "📊 وضعیت", "btn_log": "📜 لاگ",
    "btn_settings": "⚙️ تنظیمات", "btn_history": "🗓 تاریخچه", "btn_ai": "🤖 Proxy AI", "btn_explain": "📖 توضیح کامل",
    "btn_admins": "👮 ادمین‌ها", "btn_lang": "🌐 زبان", "btn_sources": "🔗 منابع", "btn_public": "🌍 عمومی: {state}",
    "btn_help": "❓ راهنما", "on": "روشن", "off": "خاموش",
    "proxies_menu": "📡 <b>پروکسی‌ها</b> — {n} زنده، {listed} از فیلتر رد شدن.\nچطوری می‌خوای؟",
    "btn_send_single": "📤 دونه‌دونه", "btn_send_batch": "📦 همه تو یه پیام", "btn_send_file": "📄 به صورت فایل",
    "btn_count": "🔢 تعداد: {n}", "btn_list": "📋 لیست {n} تای برتر",
    "no_proxies": "😕 هنوز پروکسی زنده‌ای نداریم. اول یه اسکن بزن.",
    "proxy_card": "{i}. <b>{host}</b>:{port}\n   ⏱ {ping} ms · ⬇️ {down} KB/s · ⬆️ {up} KB/s · ⭐ {score}\n   🇮🇷 {iran} · نوع: {stype}\n   <a href=\"{link}\">اتصال</a>",
    "proxy_line": "{i}. ⏱{ping}ms ⭐{score} <a href=\"{link}\">{host}:{port}</a>",
    "iran_ok": "از ایران در دسترسه", "iran_bad": "در ایران فیلتره", "iran_unknown": "ایران: تست نشده",
    "file_caption": "📄 {n} پروکسی برتر — {ts}",
    "ask_count": "چند تا پروکسی؟ (۱ تا {max})",
    "scan_started": "🔄 اسکن شروع شد. تموم شد خبر می‌دم. با 📜 لاگ می‌تونی پیشرفت رو ببینی.",
    "scan_running": "⏳ یه اسکن در حال اجراست (مرحله: {stage}).",
    "scan_done": "✅ <b>اسکن تموم شد</b> در {sec} ثانیه\n• منابع موفق/ناموفق: {ok}/{failed}\n• پیدا شده: {found} · یکتا: {uniq}\n• زنده: {alive} · تست سرعت: {speed}\n• لیست‌شده: <b>{listed}</b>",
    "status": "📊 <b>وضعیت</b>\nمرحله: <b>{stage}</b> {detail} {progress}\nران #{run} روی ران گیت‌هاب <code>{gh}</code> · آپتایم {uptime}\nپروکسی: زنده {alive} · ناپایدار {flaky} · مرده {dead} · کل {total}\nمنابع: {src_on} فعال / {src_all}\nکاربران: {users} · ادمین‌ها: {admins}\nاسکن خودکار: {auto} هر {interval} دقیقه · بعدی تا {next}\nآخرین ذخیره: {save} · ذخیره‌های این ران: {saves}\nAI: {ai}",
    "log_title": "📜 <b>لاگ</b> — مرحله فعلی: <b>{stage}</b> {detail} {progress}\n\n",
    "log_empty": "هنوز لاگی نیست.",
    "btn_log_refresh": "🔄 بروزرسانی", "btn_log_errors": "⚠️ فقط خطاها", "btn_log_all": "📜 همه",
    "history_title": "🗓 <b>تاریخچه</b> ({days} روز اخیر). روی یه روز بزن:",
    "history_day": "🗓 <b>{day}</b> — {n} پروکسی زنده اون روز تست شدن:\n\n",
    "history_empty": "هنوز تاریخچه‌ای نیست.",
    "history_row": "{day} · تست {tested} · زنده {alive} · میانگین {avg} ms",
    "settings_title": "⚙️ <b>تنظیمات</b> — برای تغییر بزن",
    "set_prompt": "مقدار جدید برای <b>{key}</b> بفرست\n<i>{desc}</i>\nفعلی: <code>{cur}</code>",
    "set_ok": "✅ <b>{key}</b> = <code>{val}</code>",
    "set_err": "❌ مقدار نامعتبر: {err}",
    "grp_sched": "⏰ زمان‌بندی", "grp_pipe": "🧪 پایپ‌لاین", "grp_bot": "🤖 ربات", "grp_ai": "🧠 هوش مصنوعی",
    "public_on": "🌍 حالت عمومی <b>روشن</b> — همه می‌تونن پروکسی بگیرن. منوهای ادمین محفوظ می‌مونن.",
    "public_off": "🔒 حالت عمومی <b>خاموش</b> — فقط ادمین‌ها می‌تونن از ربات استفاده کنن.",
    "admins_title": "👮 <b>ادمین‌ها</b>\n{list}\n\nدسترسی‌ها: <code>*</code> همه · <code>scan</code> · <code>settings</code> · <code>sources</code> · <code>ai</code> · <code>admins</code> · <code>logs</code>",
    "btn_add_admin": "➕ ادمین جدید", "btn_del_admin": "➖ حذف ادمین", "btn_perm_admin": "🔧 دسترسی‌ها",
    "ask_admin_id": "آیدی عددی تلگرام ادمین جدید رو بفرست. می‌تونی یه پیام ازش فوروارد کنی.",
    "ask_admin_perms": "دسترسی‌ها رو با فاصله بفرست، مثلاً <code>scan logs ai</code> — یا <code>*</code> برای همه.",
    "admin_added": "✅ ادمین {id} با دسترسی {perms} اضافه شد.",
    "admin_removed": "✅ ادمین {id} حذف شد.",
    "admin_cannot_remove_owner": "❌ مالک رو نمی‌شه حذف کرد.",
    "admin_pick": "یه ادمین انتخاب کن:",
    "sources_title": "🔗 <b>منابع</b> — {on} فعال / {all} کل · ران آخر: {ok} موفق، {failed} ناموفق\nپیش‌فرض: {builtin} · AI پیدا کرده: {ai} · دستی: {manual}",
    "btn_add_source": "➕ افزودن URL", "btn_list_sources": "📋 بهترین منابع", "btn_bad_sources": "💀 منابع خراب",
    "btn_ai_discover": "🧠 کشف با AI",
    "ask_source_url": "آدرس منبع رو بفرست (لیست خام، صفحه یا https://t.me/s/channel).",
    "source_added": "✅ منبع اضافه شد.", "source_exists": "قبلاً تو لیست بوده.",
    "explain": """📖 <b>ProxyBot چطوری کار می‌کنه</b>

<b>اجرا</b>
به صورت یه جاب GitHub Actions (رایگان) اجرا می‌شه. گیت‌هاب جاب‌ها رو بعد ۶ ساعت می‌کُشه، پس حدود ۵.۵ ساعت که گذشت ربات دیتابیسش رو کامیت می‌کنه، با <code>GH_PAT</code> ران بعدی رو می‌زنه و خارج می‌شه. ران جدید ریپو رو با <code>data/</code> تازه چک‌اوت می‌کنه و ادامه می‌ده — هیچی از دست نمی‌ره. هر ۳۰ ثانیه (تنظیم <code>save_interval_sec</code>) پوشه <code>data/</code> کامیت و پوش می‌شه و فایل SQLite هم به عنوان آرتیفکت آپلود می‌شه (پشتیبان دوم).

<b>ذخیره‌سازی</b> — یه فایل SQLite <code>data/proxybot.db</code> (حالت WAL): تنظیمات، کاربران، ادمین‌ها، منابع، پروکسی‌ها، تاریخچه هر ران، لاگ‌ها، نشست‌های AI، کارهای معلق. حافظه بلندمدت AI تو <code>data/memory/MEMORY.md</code> و <code>USER.md</code>، اسکیل‌ها تو <code>data/skills/*/SKILL.md</code>.

<b>پایپ‌لاین (۵ مرحله)</b>
1️⃣ <b>جمع‌آوری</b> — همه منابع فعال موازی دانلود می‌شن (لیست‌های گیت‌هاب، APIهای تجمیع‌کننده، کانال‌های عمومی تلگرام از طریق t.me/s/…). لینک‌های tg://proxy و t.me/proxy، JSON و host:port:secret پارس می‌شن.
2️⃣ <b>حذف تکراری</b> — یکتا بر اساس (host, port, secret)؛ پروکسی‌هایی که قبلاً زنده بودن حتی اگه دیگه تو هیچ منبعی نباشن دوباره تست می‌شن.
3️⃣ <b>پینگ</b> — نه TCP ping ساده: یه <i>هندشیک واقعی MTProto</i> (ClientHello فیک‌TLS + بررسی HMAC برای سکرت‌های <code>ee</code>، init Obfuscated2، ارسال <code>req_pq_multi</code> به DC2 تلگرام از طریق پروکسی؛ جواب <code>resPQ</code> باید nonce ما رو برگردونه). <code>threads</code> پروکسی همزمان.
4️⃣ <b>سرعت</b> — رفت‌وبرگشت‌های تکراری از طریق پروکسی ⬇️/⬆️ نسبی KB/s می‌ده (<code>speed_threads</code>, <code>speed_bytes</code>).
5️⃣ <b>فیلتر</b> — امتیاز ۰ تا ۱۰۰ = ۴۵٪ پینگ + ۳۰٪ سرعت + ۱۵٪ پایداری (۱۰ تست آخر) + ۱۰٪ دسترسی از ایران (از نودهای ایرانی check-host.net؛ فیلتر = −۴۰). پروکسی‌های کندتر از <code>max_ping_ms</code> یا زیر <code>min_score</code> حذف و <code>top_n</code> تای برتر لیست می‌شن.

<b>زمان‌بندی</b> — هر <code>scan_interval_min</code> دقیقه (تو ⚙️ عوض کن). پروکسی‌های قدیمی <code>retention_days</code> روز نگه داشته می‌شن تا 🗓 تاریخچه هر تاریخی رو نشون بده.

<b>Proxy AI</b> — دستیار با معماری Hermes Agent و ابزارها: خوندن/نوشتن فایل‌های پروژه، اجرای دستور شل، کوئری دیتابیس، تغییر تنظیمات، اجرای پایپ‌لاین، جستجوی وب با Tavily، یادگیری اسکیل و حافظه دائمی. کارهای حساس (شل، نوشتن فایل، حذف، تنظیمات) <b>معلق</b> می‌شن و تو با دکمه تأیید می‌کنی. هر نوشتن تو حافظه یه نوتیف 💾 می‌فرسته.

<b>دسترسی</b> — پیش‌فرض خصوصی (مالک = <code>ADMIN_ID</code>). 🌍 عمومی اجازه می‌ده همه پروکسی بگیرن؛ اسکن/تنظیمات/منابع/AI/ادمین‌ها فقط برای ادمین‌ها با دسترسی جداگانه.""",
    "help": "دستورات:\n/start — منو\n/proxies — گرفتن پروکسی\n/scan — اجرای پایپ‌لاین\n/status — وضعیت\n/log — لاگ زنده\n/history — بر اساس تاریخ\n/settings — تنظیمات\n/sources — منابع پروکسی\n/ai — صحبت با Proxy AI\n/ai_new — نشست جدید AI\n/ai_setup — تنظیم AI\n/pending — تأیید کارهای AI\n/admins — مدیریت ادمین‌ها\n/public — حالت عمومی\n/lang — زبان\n/explain — توضیح کامل\n/ping — تأخیر ربات\n/cancel — لغو ورودی فعلی",
    "ai_setup_url": "🤖 <b>تنظیم Proxy AI</b> (مرحله ۱/۳)\n<b>base_url</b> سازگار با OpenAI رو بفرست، مثلاً <code>https://api.openai.com/v1</code> یا <code>https://openrouter.ai/api/v1</code>",
    "ai_setup_key": "مرحله ۲/۳ — <b>API key</b> رو بفرست. (پیامت پاک می‌شه.)",
    "ai_setup_models": "مرحله ۳/۳ — <b>{n}</b> مدل پیدا شد. یکی رو انتخاب کن (یا آیدی مدل رو بفرست):",
    "ai_setup_models_fail": "نشد لیست مدل‌ها رو بگیرم ({err}). آیدی مدل رو دستی بفرست:",
    "ai_setup_done": "✅ AI تنظیم شد: <code>{model}</code> @ {url}",
    "ai_not_configured": "🤖 AI هنوز تنظیم نشده. /ai_setup رو بزن.",
    "ai_menu": "🤖 <b>Proxy AI</b>\nمدل: <code>{model}</code>\nنشست #{sid} · {msgs} پیام · منتظر تأیید: {pending}\nحافظه: {mem_pct}% · پروفایل کاربر: {user_pct}%\n\nفقط پیام بده تا حرف بزنیم. ابزارها: {tools}",
    "btn_ai_new": "🆕 نشست جدید", "btn_ai_setup": "🔧 تنظیم", "btn_ai_model": "🧠 مدل", "btn_ai_memory": "💾 حافظه",
    "btn_ai_pending": "⏳ معلق ({n})", "btn_ai_skills": "📚 اسکیل‌ها", "btn_ai_discover": "🔎 کشف منابع",
    "ai_thinking": "🤔 دارم فکر می‌کنم…",
    "ai_tool": "🔧 <code>{tool}</code> {args}",
    "ai_approval": "⚠️ <b>نیاز به تأیید</b> #{id}\nابزار: <code>{tool}</code>\n{reason}\n<pre>{args}</pre>",
    "btn_approve": "✅ تأیید", "btn_deny": "❌ رد", "btn_approve_all": "✅ تأیید همه", "btn_deny_all": "❌ رد همه",
    "ai_approved": "✅ #{id} تأیید شد — در حال اجرا…", "ai_denied": "❌ #{id} رد شد.",
    "ai_no_pending": "کار معلقی نیست.",
    "ai_memory_saved": "💾 حافظه {action} ({target}): <i>{text}</i>",
    "ai_skill_saved": "📚 اسکیل <b>{name}</b> {action}",
    "ai_new_session": "🆕 نشست جدید AI شروع شد. قبلی با session_search قابل جستجوئه.",
    "ai_error": "❌ خطای AI: {err}",
    "ai_memory_view": "💾 <b>MEMORY.md</b> ({m_used}/{m_max})\n<pre>{memory}</pre>\n\n👤 <b>USER.md</b> ({u_used}/{u_max})\n<pre>{user}</pre>",
    "ai_discover_started": "🔎 از AI می‌خوام با Tavily دنبال منابع جدید پروکسی بگرده…",
    "ai_busy": "⏳ AI هنوز داره روی پیام قبلیت کار می‌کنه.",
    "ai_models_pick": "یه مدل انتخاب کن:",
    "ai_skills_view": "📚 <b>اسکیل‌ها</b>\n{list}",
    "handover": "♻️ بودجه زمانی این ران تموم شد — دارم به یه ران جدید گیت‌هاب تحویل می‌دم. تا ~۱ دقیقه دیگه برمی‌گردم.",
}


def _menu(d):
    """Short language packs: full menu surface, long texts fall back to EN."""
    return d


RU = _menu({
    "welcome": "👋 Добро пожаловать в <b>ProxyBot</b> — круглосуточный охотник за MTProto-прокси.\n\nСначала выберите язык:",
    "lang_set": "✅ Язык: {lang}.",
    "main_menu": "🏠 <b>Главное меню</b>\nСтатус: {status}\nЖивых прокси: <b>{alive}</b> · в списке: <b>{listed}</b> · всего: {total}\nСледующее сканирование через: {next}",
    "not_allowed": "⛔ Бот приватный. Попросите владельца включить публичный режим.",
    "admin_only": "🔒 Только для админов.", "owner_only": "🔒 Только владелец.",
    "cancel": "❌ Отмена", "back": "🔙 Назад", "done": "✅ Готово.", "yes": "✅ Да", "no": "❌ Нет", "cancelled": "Отменено.",
    "invalid_number": "Введите корректное число.", "ping": "🏓 pong — {ms} мс", "on": "ВКЛ", "off": "ВЫКЛ",
    "btn_proxies": "📡 Прокси", "btn_scan": "🔄 Сканировать", "btn_status": "📊 Статус", "btn_log": "📜 Лог",
    "btn_settings": "⚙️ Настройки", "btn_history": "🗓 История", "btn_ai": "🤖 Proxy AI", "btn_explain": "📖 Как это работает",
    "btn_admins": "👮 Админы", "btn_lang": "🌐 Язык", "btn_sources": "🔗 Источники", "btn_public": "🌍 Публичный: {state}", "btn_help": "❓ Помощь",
    "proxies_menu": "📡 <b>Прокси</b> — {n} живых, {listed} прошли фильтр.\nКак отправить?",
    "btn_send_single": "📤 По одному", "btn_send_batch": "📦 Одним сообщением", "btn_send_file": "📄 Файлом",
    "btn_count": "🔢 Кол-во: {n}", "btn_list": "📋 Топ {n}", "no_proxies": "😕 Пока нет живых прокси. Запустите сканирование.",
    "iran_ok": "доступен из Ирана", "iran_bad": "ЗАБЛОКИРОВАН в Иране", "iran_unknown": "Иран: не проверен",
    "scan_started": "🔄 Сканирование запущено.", "scan_running": "⏳ Сканирование уже идёт (этап: {stage}).",
    "settings_title": "⚙️ <b>Настройки</b>", "log_empty": "Лог пуст.", "history_empty": "Истории пока нет.",
    "public_on": "🌍 Публичный режим <b>ВКЛ</b>.", "public_off": "🔒 Публичный режим <b>ВЫКЛ</b>.",
    "ai_not_configured": "🤖 AI ещё не настроен. /ai_setup", "ai_thinking": "🤔 думаю…",
    "btn_approve": "✅ Одобрить", "btn_deny": "❌ Отклонить", "ai_no_pending": "Нет ожидающих действий.",
})

AR = _menu({
    "welcome": "👋 أهلاً بك في <b>ProxyBot</b> — صيّاد بروكسي MTProto يعمل على مدار الساعة.\n\nاختر لغتك أولاً:",
    "lang_set": "✅ تم ضبط اللغة: {lang}.",
    "main_menu": "🏠 <b>القائمة الرئيسية</b>\nالحالة: {status}\nبروكسيات حية: <b>{alive}</b> · مدرجة: <b>{listed}</b> · الإجمالي: {total}\nالفحص التالي بعد: {next}",
    "not_allowed": "⛔ هذا البوت خاص.", "admin_only": "🔒 للمشرفين فقط.", "owner_only": "🔒 للمالك فقط.",
    "cancel": "❌ إلغاء", "back": "🔙 رجوع", "done": "✅ تم.", "yes": "✅ نعم", "no": "❌ لا", "cancelled": "أُلغي.",
    "invalid_number": "أرسل رقماً صحيحاً.", "ping": "🏓 pong — {ms} مللي ثانية", "on": "مفعّل", "off": "معطّل",
    "btn_proxies": "📡 البروكسيات", "btn_scan": "🔄 فحص الآن", "btn_status": "📊 الحالة", "btn_log": "📜 السجل",
    "btn_settings": "⚙️ الإعدادات", "btn_history": "🗓 التاريخ", "btn_ai": "🤖 Proxy AI", "btn_explain": "📖 كيف يعمل",
    "btn_admins": "👮 المشرفون", "btn_lang": "🌐 اللغة", "btn_sources": "🔗 المصادر", "btn_public": "🌍 عام: {state}", "btn_help": "❓ مساعدة",
    "proxies_menu": "📡 <b>البروكسيات</b> — {n} حية، {listed} اجتازت الفلتر.\nكيف تريدها؟",
    "btn_send_single": "📤 واحداً تلو الآخر", "btn_send_batch": "📦 في رسالة واحدة", "btn_send_file": "📄 كملف",
    "btn_count": "🔢 العدد: {n}", "btn_list": "📋 أفضل {n}", "no_proxies": "😕 لا توجد بروكسيات حية بعد.",
    "iran_ok": "متاح من إيران", "iran_bad": "محجوب في إيران", "iran_unknown": "إيران: غير مُختبر",
    "scan_started": "🔄 بدأ الفحص.", "scan_running": "⏳ هناك فحص جارٍ (المرحلة: {stage}).",
    "settings_title": "⚙️ <b>الإعدادات</b>", "log_empty": "لا سجل بعد.", "history_empty": "لا يوجد تاريخ بعد.",
    "public_on": "🌍 الوضع العام <b>مفعّل</b>.", "public_off": "🔒 الوضع العام <b>معطّل</b>.",
    "ai_not_configured": "🤖 لم يتم إعداد الذكاء الاصطناعي. /ai_setup", "ai_thinking": "🤔 أفكر…",
    "btn_approve": "✅ موافقة", "btn_deny": "❌ رفض", "ai_no_pending": "لا إجراءات معلّقة.",
})

TR = _menu({
    "welcome": "👋 <b>ProxyBot</b>'a hoş geldin — 7/24 MTProto proxy avcısı.\n\nÖnce dilini seç:",
    "lang_set": "✅ Dil: {lang}.",
    "main_menu": "🏠 <b>Ana menü</b>\nDurum: {status}\nCanlı proxy: <b>{alive}</b> · listelenen: <b>{listed}</b> · toplam: {total}\nSonraki tarama: {next}",
    "not_allowed": "⛔ Bu bot özel.", "admin_only": "🔒 Sadece yöneticiler.", "owner_only": "🔒 Sadece sahip.",
    "cancel": "❌ İptal", "back": "🔙 Geri", "done": "✅ Tamam.", "yes": "✅ Evet", "no": "❌ Hayır", "cancelled": "İptal edildi.",
    "invalid_number": "Geçerli bir sayı gönder.", "ping": "🏓 pong — {ms} ms", "on": "AÇIK", "off": "KAPALI",
    "btn_proxies": "📡 Proxyler", "btn_scan": "🔄 Şimdi tara", "btn_status": "📊 Durum", "btn_log": "📜 Günlük",
    "btn_settings": "⚙️ Ayarlar", "btn_history": "🗓 Geçmiş", "btn_ai": "🤖 Proxy AI", "btn_explain": "📖 Nasıl çalışır",
    "btn_admins": "👮 Yöneticiler", "btn_lang": "🌐 Dil", "btn_sources": "🔗 Kaynaklar", "btn_public": "🌍 Herkese açık: {state}", "btn_help": "❓ Yardım",
    "proxies_menu": "📡 <b>Proxyler</b> — {n} canlı, {listed} filtreyi geçti.\nNasıl istersin?",
    "btn_send_single": "📤 Tek tek", "btn_send_batch": "📦 Tek mesajda", "btn_send_file": "📄 Dosya olarak",
    "btn_count": "🔢 Adet: {n}", "btn_list": "📋 İlk {n}", "no_proxies": "😕 Henüz canlı proxy yok.",
    "iran_ok": "İran'dan erişilebilir", "iran_bad": "İran'da ENGELLİ", "iran_unknown": "İran: test edilmedi",
    "scan_started": "🔄 Tarama başladı.", "scan_running": "⏳ Tarama zaten çalışıyor ({stage}).",
    "settings_title": "⚙️ <b>Ayarlar</b>", "log_empty": "Günlük boş.", "history_empty": "Henüz geçmiş yok.",
    "public_on": "🌍 Herkese açık mod <b>AÇIK</b>.", "public_off": "🔒 Herkese açık mod <b>KAPALI</b>.",
    "ai_not_configured": "🤖 AI henüz ayarlanmadı. /ai_setup", "ai_thinking": "🤔 düşünüyorum…",
    "btn_approve": "✅ Onayla", "btn_deny": "❌ Reddet", "ai_no_pending": "Bekleyen işlem yok.",
})

ZH = _menu({
    "welcome": "👋 欢迎使用 <b>ProxyBot</b> — 全天候 Telegram MTProto 代理猎手。\n\n请先选择语言：",
    "lang_set": "✅ 语言已设置为 {lang}。",
    "main_menu": "🏠 <b>主菜单</b>\n状态：{status}\n存活代理：<b>{alive}</b> · 已列出：<b>{listed}</b> · 总计：{total}\n下次扫描：{next}",
    "not_allowed": "⛔ 此机器人为私有。", "admin_only": "🔒 仅限管理员。", "owner_only": "🔒 仅限所有者。",
    "cancel": "❌ 取消", "back": "🔙 返回", "done": "✅ 完成。", "yes": "✅ 是", "no": "❌ 否", "cancelled": "已取消。",
    "invalid_number": "请输入有效数字。", "ping": "🏓 pong — {ms} 毫秒", "on": "开", "off": "关",
    "btn_proxies": "📡 代理", "btn_scan": "🔄 立即扫描", "btn_status": "📊 状态", "btn_log": "📜 日志",
    "btn_settings": "⚙️ 设置", "btn_history": "🗓 历史", "btn_ai": "🤖 Proxy AI", "btn_explain": "📖 工作原理",
    "btn_admins": "👮 管理员", "btn_lang": "🌐 语言", "btn_sources": "🔗 来源", "btn_public": "🌍 公开：{state}", "btn_help": "❓ 帮助",
    "proxies_menu": "📡 <b>代理</b> — {n} 个存活，{listed} 个通过筛选。\n如何发送？",
    "btn_send_single": "📤 逐个发送", "btn_send_batch": "📦 合并一条消息", "btn_send_file": "📄 作为文件",
    "btn_count": "🔢 数量：{n}", "btn_list": "📋 前 {n} 名", "no_proxies": "😕 还没有存活代理。",
    "iran_ok": "伊朗可访问", "iran_bad": "伊朗已封锁", "iran_unknown": "伊朗：未测试",
    "scan_started": "🔄 扫描已开始。", "scan_running": "⏳ 扫描正在进行（{stage}）。",
    "settings_title": "⚙️ <b>设置</b>", "log_empty": "暂无日志。", "history_empty": "暂无历史。",
    "public_on": "🌍 公开模式<b>开启</b>。", "public_off": "🔒 公开模式<b>关闭</b>。",
    "ai_not_configured": "🤖 AI 尚未配置。/ai_setup", "ai_thinking": "🤔 思考中…",
    "btn_approve": "✅ 批准", "btn_deny": "❌ 拒绝", "ai_no_pending": "没有待处理操作。",
})

ES = _menu({
    "welcome": "👋 Bienvenido a <b>ProxyBot</b> — cazador de proxies MTProto 24/7.\n\nElige tu idioma:",
    "lang_set": "✅ Idioma: {lang}.",
    "main_menu": "🏠 <b>Menú principal</b>\nEstado: {status}\nProxies vivos: <b>{alive}</b> · listados: <b>{listed}</b> · total: {total}\nPróximo escaneo en: {next}",
    "not_allowed": "⛔ Este bot es privado.", "admin_only": "🔒 Solo administradores.", "owner_only": "🔒 Solo el propietario.",
    "cancel": "❌ Cancelar", "back": "🔙 Atrás", "done": "✅ Hecho.", "yes": "✅ Sí", "no": "❌ No", "cancelled": "Cancelado.",
    "invalid_number": "Envía un número válido.", "ping": "🏓 pong — {ms} ms", "on": "ON", "off": "OFF",
    "btn_proxies": "📡 Proxies", "btn_scan": "🔄 Escanear", "btn_status": "📊 Estado", "btn_log": "📜 Registro",
    "btn_settings": "⚙️ Ajustes", "btn_history": "🗓 Historial", "btn_ai": "🤖 Proxy AI", "btn_explain": "📖 Cómo funciona",
    "btn_admins": "👮 Admins", "btn_lang": "🌐 Idioma", "btn_sources": "🔗 Fuentes", "btn_public": "🌍 Público: {state}", "btn_help": "❓ Ayuda",
    "proxies_menu": "📡 <b>Proxies</b> — {n} vivos, {listed} pasan el filtro.\n¿Cómo los quieres?",
    "btn_send_single": "📤 Uno a uno", "btn_send_batch": "📦 En un mensaje", "btn_send_file": "📄 Como archivo",
    "btn_count": "🔢 Cantidad: {n}", "btn_list": "📋 Top {n}", "no_proxies": "😕 Aún no hay proxies vivos.",
    "iran_ok": "accesible desde Irán", "iran_bad": "BLOQUEADO en Irán", "iran_unknown": "Irán: sin probar",
    "scan_started": "🔄 Escaneo iniciado.", "scan_running": "⏳ Ya hay un escaneo en curso ({stage}).",
    "settings_title": "⚙️ <b>Ajustes</b>", "log_empty": "Sin registros.", "history_empty": "Sin historial.",
    "public_on": "🌍 Modo público <b>ACTIVADO</b>.", "public_off": "🔒 Modo público <b>DESACTIVADO</b>.",
    "ai_not_configured": "🤖 La IA no está configurada. /ai_setup", "ai_thinking": "🤔 pensando…",
    "btn_approve": "✅ Aprobar", "btn_deny": "❌ Rechazar", "ai_no_pending": "No hay acciones pendientes.",
})

DE = _menu({
    "welcome": "👋 Willkommen bei <b>ProxyBot</b> — 24/7 MTProto-Proxy-Jäger.\n\nWähle zuerst deine Sprache:",
    "lang_set": "✅ Sprache: {lang}.",
    "main_menu": "🏠 <b>Hauptmenü</b>\nStatus: {status}\nLebende Proxys: <b>{alive}</b> · gelistet: <b>{listed}</b> · gesamt: {total}\nNächster Scan in: {next}",
    "not_allowed": "⛔ Dieser Bot ist privat.", "admin_only": "🔒 Nur Admins.", "owner_only": "🔒 Nur Besitzer.",
    "cancel": "❌ Abbrechen", "back": "🔙 Zurück", "done": "✅ Fertig.", "yes": "✅ Ja", "no": "❌ Nein", "cancelled": "Abgebrochen.",
    "invalid_number": "Bitte eine gültige Zahl senden.", "ping": "🏓 pong — {ms} ms", "on": "AN", "off": "AUS",
    "btn_proxies": "📡 Proxys", "btn_scan": "🔄 Jetzt scannen", "btn_status": "📊 Status", "btn_log": "📜 Log",
    "btn_settings": "⚙️ Einstellungen", "btn_history": "🗓 Verlauf", "btn_ai": "🤖 Proxy AI", "btn_explain": "📖 Funktionsweise",
    "btn_admins": "👮 Admins", "btn_lang": "🌐 Sprache", "btn_sources": "🔗 Quellen", "btn_public": "🌍 Öffentlich: {state}", "btn_help": "❓ Hilfe",
    "proxies_menu": "📡 <b>Proxys</b> — {n} lebend, {listed} bestehen den Filter.\nWie möchtest du sie?",
    "btn_send_single": "📤 Einzeln", "btn_send_batch": "📦 In einer Nachricht", "btn_send_file": "📄 Als Datei",
    "btn_count": "🔢 Anzahl: {n}", "btn_list": "📋 Top {n}", "no_proxies": "😕 Noch keine lebenden Proxys.",
    "iran_ok": "aus Iran erreichbar", "iran_bad": "im Iran BLOCKIERT", "iran_unknown": "Iran: ungetestet",
    "scan_started": "🔄 Scan gestartet.", "scan_running": "⏳ Ein Scan läuft bereits ({stage}).",
    "settings_title": "⚙️ <b>Einstellungen</b>", "log_empty": "Noch keine Logs.", "history_empty": "Noch kein Verlauf.",
    "public_on": "🌍 Öffentlicher Modus <b>AN</b>.", "public_off": "🔒 Öffentlicher Modus <b>AUS</b>.",
    "ai_not_configured": "🤖 KI noch nicht konfiguriert. /ai_setup", "ai_thinking": "🤔 denke nach…",
    "btn_approve": "✅ Genehmigen", "btn_deny": "❌ Ablehnen", "ai_no_pending": "Keine ausstehenden Aktionen.",
})

FR = _menu({
    "welcome": "👋 Bienvenue sur <b>ProxyBot</b> — chasseur de proxys MTProto 24h/24.\n\nChoisissez d'abord votre langue :",
    "lang_set": "✅ Langue : {lang}.",
    "main_menu": "🏠 <b>Menu principal</b>\nÉtat : {status}\nProxys actifs : <b>{alive}</b> · listés : <b>{listed}</b> · total : {total}\nProchain scan dans : {next}",
    "not_allowed": "⛔ Ce bot est privé.", "admin_only": "🔒 Admins uniquement.", "owner_only": "🔒 Propriétaire uniquement.",
    "cancel": "❌ Annuler", "back": "🔙 Retour", "done": "✅ Terminé.", "yes": "✅ Oui", "no": "❌ Non", "cancelled": "Annulé.",
    "invalid_number": "Envoyez un nombre valide.", "ping": "🏓 pong — {ms} ms", "on": "ON", "off": "OFF",
    "btn_proxies": "📡 Proxys", "btn_scan": "🔄 Scanner", "btn_status": "📊 État", "btn_log": "📜 Journal",
    "btn_settings": "⚙️ Réglages", "btn_history": "🗓 Historique", "btn_ai": "🤖 Proxy AI", "btn_explain": "📖 Fonctionnement",
    "btn_admins": "👮 Admins", "btn_lang": "🌐 Langue", "btn_sources": "🔗 Sources", "btn_public": "🌍 Public : {state}", "btn_help": "❓ Aide",
    "proxies_menu": "📡 <b>Proxys</b> — {n} actifs, {listed} passent le filtre.\nComment les voulez-vous ?",
    "btn_send_single": "📤 Un par un", "btn_send_batch": "📦 En un message", "btn_send_file": "📄 En fichier",
    "btn_count": "🔢 Nombre : {n}", "btn_list": "📋 Top {n}", "no_proxies": "😕 Aucun proxy actif pour l'instant.",
    "iran_ok": "accessible depuis l'Iran", "iran_bad": "BLOQUÉ en Iran", "iran_unknown": "Iran : non testé",
    "scan_started": "🔄 Scan lancé.", "scan_running": "⏳ Un scan est déjà en cours ({stage}).",
    "settings_title": "⚙️ <b>Réglages</b>", "log_empty": "Pas encore de journal.", "history_empty": "Pas encore d'historique.",
    "public_on": "🌍 Mode public <b>ACTIVÉ</b>.", "public_off": "🔒 Mode public <b>DÉSACTIVÉ</b>.",
    "ai_not_configured": "🤖 IA non configurée. /ai_setup", "ai_thinking": "🤔 je réfléchis…",
    "btn_approve": "✅ Approuver", "btn_deny": "❌ Refuser", "ai_no_pending": "Aucune action en attente.",
})

HI = _menu({
    "welcome": "👋 <b>ProxyBot</b> में आपका स्वागत है — 24/7 MTProto प्रॉक्सी खोजी।\n\nपहले अपनी भाषा चुनें:",
    "lang_set": "✅ भाषा: {lang}.",
    "main_menu": "🏠 <b>मुख्य मेनू</b>\nस्थिति: {status}\nसक्रिय प्रॉक्सी: <b>{alive}</b> · सूचीबद्ध: <b>{listed}</b> · कुल: {total}\nअगला स्कैन: {next}",
    "not_allowed": "⛔ यह बॉट निजी है।", "admin_only": "🔒 केवल एडमिन।", "owner_only": "🔒 केवल मालिक।",
    "cancel": "❌ रद्द करें", "back": "🔙 वापस", "done": "✅ हो गया।", "yes": "✅ हाँ", "no": "❌ नहीं", "cancelled": "रद्द किया गया।",
    "invalid_number": "कृपया मान्य संख्या भेजें।", "ping": "🏓 pong — {ms} ms", "on": "चालू", "off": "बंद",
    "btn_proxies": "📡 प्रॉक्सी", "btn_scan": "🔄 अभी स्कैन करें", "btn_status": "📊 स्थिति", "btn_log": "📜 लॉग",
    "btn_settings": "⚙️ सेटिंग्स", "btn_history": "🗓 इतिहास", "btn_ai": "🤖 Proxy AI", "btn_explain": "📖 कैसे काम करता है",
    "btn_admins": "👮 एडमिन", "btn_lang": "🌐 भाषा", "btn_sources": "🔗 स्रोत", "btn_public": "🌍 सार्वजनिक: {state}", "btn_help": "❓ सहायता",
    "proxies_menu": "📡 <b>प्रॉक्सी</b> — {n} सक्रिय, {listed} फ़िल्टर पास।\nकैसे चाहिए?",
    "btn_send_single": "📤 एक-एक करके", "btn_send_batch": "📦 एक संदेश में", "btn_send_file": "📄 फ़ाइल के रूप में",
    "btn_count": "🔢 संख्या: {n}", "btn_list": "📋 शीर्ष {n}", "no_proxies": "😕 अभी कोई सक्रिय प्रॉक्सी नहीं।",
    "iran_ok": "ईरान से उपलब्ध", "iran_bad": "ईरान में अवरुद्ध", "iran_unknown": "ईरान: परीक्षण नहीं",
    "scan_started": "🔄 स्कैन शुरू।", "scan_running": "⏳ स्कैन पहले से चल रहा है ({stage})।",
    "settings_title": "⚙️ <b>सेटिंग्स</b>", "log_empty": "अभी कोई लॉग नहीं।", "history_empty": "अभी कोई इतिहास नहीं।",
    "public_on": "🌍 सार्वजनिक मोड <b>चालू</b>।", "public_off": "🔒 सार्वजनिक मोड <b>बंद</b>।",
    "ai_not_configured": "🤖 AI अभी कॉन्फ़िगर नहीं है। /ai_setup", "ai_thinking": "🤔 सोच रहा हूँ…",
    "btn_approve": "✅ स्वीकृत", "btn_deny": "❌ अस्वीकार", "ai_no_pending": "कोई लंबित कार्रवाई नहीं।",
})

STRINGS = {"en": EN, "fa": FA, "ru": RU, "ar": AR, "tr": TR, "zh": ZH, "es": ES, "de": DE, "fr": FR, "hi": HI}
