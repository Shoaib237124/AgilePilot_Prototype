import os

from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# SUPABASE DATABASE
# ============================================================

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port", "5432")
DBNAME = os.getenv("dbname", "postgres")


# ============================================================
# DEEPGRAM
# ============================================================

DEEPGRAM_API_KEY = os.getenv(
    "DEEPGRAM_API_KEY"
)


# ============================================================
# APPLICATION DIRECTORIES
# ============================================================

AUDIO_DIR = os.getenv(
    "AUDIO_DIR",
    "data/audio"
)

TRANSCRIPT_DIR = os.getenv(
    "TRANSCRIPT_DIR",
    "data/transcripts"
)


# ============================================================
# VALIDATION
# ============================================================

required_variables = {

    "user": USER,

    "password": PASSWORD,

    "host": HOST,

    "DEEPGRAM_API_KEY": DEEPGRAM_API_KEY,
}


missing_variables = [

    name

    for name, value
    in required_variables.items()

    if not value
]


if missing_variables:

    raise ValueError(

        "Missing required environment "
        "variables: "

        + ", ".join(
            missing_variables
        )
    )


# ============================================================
# CREATE DIRECTORIES
# ============================================================

Path(AUDIO_DIR).mkdir(
    parents=True,
    exist_ok=True
)

Path(TRANSCRIPT_DIR).mkdir(
    parents=True,
    exist_ok=True
)