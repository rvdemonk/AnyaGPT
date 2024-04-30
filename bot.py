import os
import logging
import aiohttp
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from utilities import convert_audio_to_mp3, get_profile_system_prompt
from openai import AsyncOpenAI
from tempfile import NamedTemporaryFile
from pprint import pprint


# Load environment variables from .env file
load_dotenv()
client = AsyncOpenAI()

# Environment variables for security
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

PROFILE = "anya5"
AI_GREETING = (
    "🙄 Can’t handle it on your own, huh? Alright, spill it – what do you need?"
)

conversations = {}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


async def transcribe_audio(original_file_path):
    # Assuming the original file might need conversion
    # Generate a temp path for the converted file
    with NamedTemporaryFile(delete=False, suffix=".mp3") as converted_file:
        convert_audio_to_mp3(original_file_path, converted_file.name)

        # Now, your converted file is ready for transcription
        with open(converted_file.name, "rb") as audio_file:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1", file=audio_file
            )
            print(transcript.text)
            # Cleanup: Ensure to remove the temporary file after use
            os.remove(converted_file.name)
            return transcript.text


async def audio_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Check if the message contains an audio file or voice note
    user_id = update.message.from_user.id
    print("#### audio from", user_id)
    audio_file = update.message.voice or update.message.audio
    if audio_file:
        # Get the file
        telegram_file = await context.bot.get_file(audio_file.file_id)

        # The URL to download the file from Telegram servers
        file_url = telegram_file.file_path

        transcript = ""
        conversation = conversations.get(
            user_id, [
            {"role": "system", "content": get_profile_system_prompt(PROFILE)},
            {"role": "assistant", "content": AI_GREETING},
        ]
        )

        # Use aiohttp to download the file
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                if resp.status == 200:
                    # Use a temporary file to hold the audio
                    with NamedTemporaryFile(delete=False) as tmp_file:
                        tmp_file_path = tmp_file.name
                        while True:
                            chunk = await resp.content.read(1024)
                            if not chunk:
                                break
                            tmp_file.write(chunk)

                    print(tmp_file_path)
                    # Proceed with transcription
                    transcript = await transcribe_audio(tmp_file_path)

                    # Send the transcription to the user
                    await update.message.reply_text(
                        f"_{transcript}_", parse_mode="Markdown"
                    )

                    # save user transcription to memory
                    conversation.append({"role": "user", "content": transcript})

                    # Cleanup: Remove the temporary file
                    os.remove(tmp_file_path)

        # Send message and get response
        ai_response = await get_gpt_response(user_id)
        await update.message.reply_text(ai_response, parse_mode="Markdown")
        conversation.append({"role": "assistant", "content": ai_response})
        conversations[user_id] = conversation
        pprint(conversations[user_id])


async def get_gpt_response(user_id):
    model = "gpt-4-turbo"
    sys_prompt = get_profile_system_prompt(PROFILE)
    messages = conversations.get(
        user_id,
        [
            {"role": "system", "content": get_profile_system_prompt(PROFILE)},
            {"role": "assistant", "content": AI_GREETING},
        ],
    )[-4:]
    messages[0] = {"role": "system", "content": get_profile_system_prompt(PROFILE)}
    try:
        print("Fetching GPT response...")
        response = await client.chat.completions.create(model=model, messages=messages)
        response_message = response.choices[0].message.content
        return response_message.strip()
    except Exception as e:
        print(f"### An OpenAI error occurred: {e}")
        return "Something's gone wrong and I cannot respond."


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user_id = update.message.from_user.id
    conversations[user_id] = [{"role": "assistant", "content": AI_GREETING}]
    await update.message.reply_text(AI_GREETING, parse_mode="Markdown")


async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply message using GPT."""
    user_id = update.message.from_user.id
    user_message = update.message.text
    print("#### text from", user_id, user_message)
    conversations[user_id].append({"role": "user", "content": user_message})

    ai_response = await get_gpt_response(user_id)
    print("AI:", ai_response)

    await update.message.reply_text(ai_response, parse_mode="Markdown")
    conversations[user_id].append({"role": "assistant", "content": ai_response})
    pprint(user_id)
    pprint(conversations[user_id])


if __name__ == "__main__":
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Existing handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

    # Add handler for voice messages or audio files
    application.add_handler(
        MessageHandler(filters.AUDIO | filters.VOICE, audio_message)
    )

    application.run_polling()
