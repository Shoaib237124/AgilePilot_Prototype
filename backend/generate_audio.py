import asyncio
import os
import subprocess
import shutil
import edge_tts


# ============================================================
# CONFIGURATION
# ============================================================

OUTPUT_FILE = "sample.wav"

TEMP_DIR = "meeting_audio_temp"

# Microsoft Edge Neural TTS voices
PM_VOICE = "en-US-GuyNeural"
CLIENT_VOICE = "en-US-JennyNeural"

# Speech rates
PM_RATE = "+0%"
CLIENT_RATE = "-3%"

# Volume
PM_VOLUME = "+0%"
CLIENT_VOLUME = "+0%"

# Pitch
PM_PITCH = "+0Hz"
CLIENT_PITCH = "+0Hz"


# ============================================================
# MEETING SCRIPT
# ============================================================

SCRIPT = [
    (
        "PM",
        "Thanks for hopping on the call today. "
        "I wanted to quickly walk you through our Phase 1 progress "
        "and confirm our next sprint goals."
    ),

    (
        "CLIENT",
        "Thanks for setting this up. "
        "We are really keen to see how the transcription "
        "and database pipeline are coming along."
    ),

    (
        "PM",
        "Everything on the backend is moving smoothly. "
        "We have integrated the PostgreSQL schema and configured "
        "Deepgram for 2-speaker diarization."
    ),

    (
        "CLIENT",
        "That is great news. Are we still on track to wrap up "
        "the REST API endpoints by Friday?"
    ),

    (
        "PM",
        "Yes, we are on schedule for Friday. "
        "The core data models and Pydantic validation schemas "
        "are fully implemented."
    ),

    (
        "CLIENT",
        "Awesome. One concern we had from the last review was "
        "handling high-concurrency requests. "
        "How is the database connection structured?"
    ),

    (
        "PM",
        "We configured Supabase using a transaction pooler on port 6543 "
        "with SQLAlchemy NullPool, so scaling concurrent requests "
        "will not exhaust DB connections."
    ),

    (
        "CLIENT",
        "Perfect, that addresses our main infrastructure worry. "
        "What about the frontend dashboard integration?"
    ),

    (
        "PM",
        "That will kick off in Phase 2. "
        "Once we finalize the transcript storage pipeline today, "
        "we will start wireframing the UI components."
    ),

    (
        "CLIENT",
        "Sounds like a solid plan. "
        "Send over the staging environment credentials after this call "
        "so our team can start testing."
    ),

    (
        "PM",
        "Will do. I will share the staging link and API documentation "
        "in our Slack channel right after we log off. Talk soon!"
    )
]


# ============================================================
# GENERATE ONE AUDIO SEGMENT
# ============================================================

async def generate_segment(
    text,
    voice,
    output_file,
    rate,
    volume,
    pitch
):
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        volume=volume,
        pitch=pitch
    )

    await communicate.save(output_file)


# ============================================================
# GENERATE ALL SEGMENTS
# ============================================================

async def generate_all_segments():

    os.makedirs(TEMP_DIR, exist_ok=True)

    generated_files = []

    total = len(SCRIPT)

    for index, (speaker, text) in enumerate(SCRIPT):

        print()
        print("=" * 60)
        print(f"Generating {index + 1}/{total}")
        print(f"Speaker: {speaker}")
        print("=" * 60)

        if speaker == "PM":

            voice = PM_VOICE
            rate = PM_RATE
            volume = PM_VOLUME
            pitch = PM_PITCH

        else:

            voice = CLIENT_VOICE
            rate = CLIENT_RATE
            volume = CLIENT_VOLUME
            pitch = CLIENT_PITCH

        output_file = os.path.join(
            TEMP_DIR,
            f"segment_{index:02d}.mp3"
        )

        print(f"Voice: {voice}")
        print(f"Output: {output_file}")

        try:

            await generate_segment(
                text=text,
                voice=voice,
                output_file=output_file,
                rate=rate,
                volume=volume,
                pitch=pitch
            )

            if os.path.exists(output_file):

                generated_files.append(output_file)

                print("✓ Generated successfully")

            else:

                print("✗ Audio file was not created")

        except Exception as e:

            print()
            print("ERROR generating segment:")
            print(e)
            raise

    return generated_files


# ============================================================
# CREATE SILENCE FILE
# ============================================================

def create_silence():

    silence_file = os.path.join(
        TEMP_DIR,
        "silence.mp3"
    )

    print()
    print("Creating natural pauses...")

    command = [
        "ffmpeg",
        "-y",

        "-f",
        "lavfi",

        "-i",
        "anullsrc=r=24000:cl=mono",

        "-t",
        "0.35",

        "-c:a",
        "libmp3lame",

        "-b:a",
        "128k",

        silence_file
    ]

    subprocess.run(
        command,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    return silence_file


# ============================================================
# COMBINE AUDIO
# ============================================================

def combine_audio(segment_files):

    print()
    print("=" * 60)
    print("Combining meeting audio")
    print("=" * 60)

    silence_file = create_silence()

    concat_file = os.path.join(
        TEMP_DIR,
        "concat.txt"
    )

    # --------------------------------------------------------
    # Create FFmpeg concat file
    # --------------------------------------------------------

    with open(
        concat_file,
        "w",
        encoding="utf-8"
    ) as f:

        for segment in segment_files:

            absolute_path = os.path.abspath(segment)

            absolute_path = absolute_path.replace("\\", "/")

            f.write(
                f"file '{absolute_path}'\n"
            )

            # Add pause after each speaker turn
            f.write(
                f"file '{os.path.abspath(silence_file).replace(chr(92), '/')}'\n"
            )

    # --------------------------------------------------------
    # Combine
    # --------------------------------------------------------

    command = [
        "ffmpeg",
        "-y",

        "-f",
        "concat",

        "-safe",
        "0",

        "-i",
        concat_file,

        # Convert final result to WAV
        "-ar",
        "16000",

        "-ac",
        "1",

        "-c:a",
        "pcm_s16le",

        OUTPUT_FILE
    ]

    print()
    print("Running FFmpeg...")

    subprocess.run(
        command,
        check=True
    )

    print()
    print("✓ Audio combination complete")


# ============================================================
# CLEANUP
# ============================================================

def cleanup():

    if os.path.exists(TEMP_DIR):

        print()
        print("Cleaning temporary files...")

        shutil.rmtree(TEMP_DIR)

        print("✓ Temporary files removed")


# ============================================================
# MAIN
# ============================================================

async def main():

    print()
    print("=" * 60)
    print("AGILEPILOT MEETING AUDIO GENERATOR")
    print("=" * 60)

    print()
    print("PM voice:")
    print(PM_VOICE)

    print()
    print("CLIENT voice:")
    print(CLIENT_VOICE)

    print()

    try:

        # ----------------------------------------------------
        # Step 1: Generate individual voices
        # ----------------------------------------------------

        segment_files = await generate_all_segments()

        # ----------------------------------------------------
        # Verify
        # ----------------------------------------------------

        if len(segment_files) != len(SCRIPT):

            raise RuntimeError(
                f"Only generated {len(segment_files)} "
                f"of {len(SCRIPT)} audio segments."
            )

        # ----------------------------------------------------
        # Step 2: Combine
        # ----------------------------------------------------

        combine_audio(segment_files)

        # ----------------------------------------------------
        # Step 3: Verify final file
        # ----------------------------------------------------

        if os.path.exists(OUTPUT_FILE):

            file_size = os.path.getsize(
                OUTPUT_FILE
            )

            print()
            print("=" * 60)
            print("SUCCESS!")
            print("=" * 60)

            print()
            print(f"Output file: {OUTPUT_FILE}")

            print(
                f"File size: {file_size / 1024 / 1024:.2f} MB"
            )

            print()
            print(
                "The meeting recording is ready for Deepgram."
            )

        else:

            raise RuntimeError(
                "sample.wav was not created."
            )

    finally:

        cleanup()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    asyncio.run(main())