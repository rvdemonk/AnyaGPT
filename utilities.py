from pydub import AudioSegment


def convert_audio_to_mp3(source_path, target_path):
    audio = AudioSegment.from_file(source_path)
    audio.export(target_path, format="mp3")


def get_profile_system_prompt(name):
    try:
        with open(f"./profiles/{name}.txt", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return "Profile not found. Please ensure the profile name is correct."


def cache_telegram_audio(message_audio) -> str:
    telegram_file = await context.bot.get_file(audio_file.file_id)
    file_url = telegram_file.file_path
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as resp:
            if resp.status != 200:
                raise Exception(
                    "Error in caching telegram audio: response status != 200."
                )
            with NamedTemporaryFile(delete=False) as tmp_file:
                tmp_file_path = tmp_file.name
                while True:
                    chunk = await resp.content.read(1024)
                    if not chunk:
                        break
                    tmp_file.write(chunk)
            return tmp_file_path
