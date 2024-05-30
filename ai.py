from openai import AsyncOpenAI


client = AsyncOpenAI()


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
