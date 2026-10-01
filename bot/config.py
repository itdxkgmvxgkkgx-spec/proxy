"""تنظیمات سراسری پروژه — همه مسیرها و متغیرهای محیطی اینجاست."""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "proxybot.sqlite3")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
GH_PAT = os.environ.get("GH_PAT", "")
GH_REPO = os.environ.get("GH_REPO", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
RUN_ID = os.environ.get("RUN_ID", "local")

# ادمین اولیه از سکرت؛ بقیه ادمین‌ها از دیتابیس مدیریت می‌شن
INITIAL_ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or 0)

DEFAULT_SCAN_INTERVAL_MIN = 30      # هر چند دقیقه دنبال پروکسی جدید بگرده
DEFAULT_THREADS = 100               # تعداد تریدهای تست همزمان
PING_TIMEOUT = 6                    # تایم‌اوت تست پینگ (ثانیه)
SPEED_TIMEOUT = 15                  # تایم‌اوت تست دانلود/آپلود (ثانیه)
SPEED_TEST_URL = "https://speed.hetzner.de/100KB.bin"

LANGUAGES = ["en", "fa", "ar", "tr", "ru", "de", "fr", "es", "zh", "hi"]
DEFAULT_LANGUAGE = "en"  # پیش‌فرض انگلیسی، فارسی دومین گزینه لیست
