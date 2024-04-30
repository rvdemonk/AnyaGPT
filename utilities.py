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


