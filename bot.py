import os, re, logging
import anthropic
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
from youtube_transcript_api import YouTubeTranscriptApi

load_dotenv()
logging.basicConfig(level=logging.INFO)
client = anthropic.Anthropic()  # يقرأ ANTHROPIC_API_KEY من البيئة
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
MAX_CHARS = 150_000

YT_RE = re.compile(r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|shorts/|embed/|live/))([A-Za-z0-9_-]{11})")

PROMPT = """أنت مساعد يكتب ملاحظات دراسية بالعربية من نص فيديو.
اكتب ملاحظات مفصلة ومنظمة:
- عنوان للفيديو، ثم ملخص في 3 أسطر.
- أقسام بعناوين واضحة حسب تسلسل الفيديو.
- نقاط مرتبة، مع الأرقام والأمثلة والتعريفات المهمة.
- في النهاية: أهم الخلاصات.
لا تضف معلومات غير موجودة في النص.

نص الفيديو:
"""

def get_transcript(video_id: str) -> str:
    snippets = YouTubeTranscriptApi().fetch(video_id, languages=["ar", "en"])
    return " ".join(s.text for s in snippets)[:MAX_CHARS]

def make_notes(transcript: str) -> str:
    msg = client.messages.create(
        model=MODEL, max_tokens=4000,
        messages=[{"role": "user", "content": PROMPT + transcript}],
    )
    return msg.content[0].text

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً! ابعتلي رابط فيديو يوتيوب وهرجعلك ملاحظات عربية مفصلة.")

async def handle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    m = YT_RE.search(update.message.text or "")
    if not m:
        await update.message.reply_text("ابعت رابط يوتيوب صحيح من فضلك.")
        return
    wait = await update.message.reply_text("⏳ جاري تحليل الفيديو...")
    try:
        transcript = get_transcript(m.group(1))
        notes = make_notes(transcript)
    except Exception as e:
        logging.exception("failed")
        await wait.edit_text("تعذر جلب نص الفيديو. غالباً الفيديو مفيهوش ترجمة مكتوبة.")
        return
    await wait.delete()
    for i in range(0, len(notes), 4000):
        await update.message.reply_text(notes[i:i + 4000])

def main():
    app = ApplicationBuilder().token(os.environ["TELEGRAM_BOT_TOKEN"]).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling()

if __name__ == "__main__":
    main()
