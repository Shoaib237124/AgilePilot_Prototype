# Installation and Setup

## Step 1: Clone the repository

Open PowerShell or the VS Code terminal:

git clone https://github.com/Shoaib237124/AgilePilot_Prototype.git

cd AgilePilot_Prototype

## Step 2: Open the backend directory

cd backend

## Step 3: Create a virtual environment

python -m venv .venv

Activate it in PowerShell:

.\.venv\Scripts\Activate.ps1

If PowerShell blocks activation, use Command Prompt instead:

.venv\Scripts\activate.bat

## Step 4: Install dependencies

Upgrade pip:

python -m pip install --upgrade pip


## Step 5: Start the backend

From inside the backend directory:

uvicorn main:app --reload

The server should start at:

http://127.0.0.1:8000


-------------------------------------------
## .env.example template

Create this file at backend/.env.example.

The following is a starting template. Verify the variable names against app/config.py, app/database/database.py, app/notion/client.py, and the graph nodes. Rename or add entries as needed so that they match the actual implementation.

## Deepgram

DEEPGRAM_API_KEY=your_deepgram_api_key


## Supabase PostgreSQL

Use the variable names expected by database.py.
These names match the database configuration described
in the current project setup.

user=your_database_user

password=your_database_password

host=your_supabase_database_host

port=5432

dbname=postgres


## Notion Integration

Verify these names against app/notion/client.py.

NOTION_API_KEY=your_notion_integration_token

NOTION_PARENT_PAGE_ID=your_notion_parent_page_id


## AI / LLM Provider

Add the exact variable names required by app/graph/nodes.py
and any related AI service modules.
Do not add unused credentials.

pip install -r requirements.txt
