# AI Interview Assistant

An AI-powered hiring assistant that screens candidates and generates technical questions with **Loom video responses** and **Supabase cloud storage** (with local JSON fallback).

## System Requirements

- **Python**: 3.8+
- **Ollama**: Installed and running (`llama3.2:3b` model)
- **Loom**: Desktop app or Chrome extension for recording
- **Internet**: Stable connection (for Supabase upload)

## Setup (Approx. 10-15 minutes)

### 1. Install Ollama
- Download from https://ollama.ai
- Run: `ollama pull llama3.2:3b`
- Start: `ollama serve` (keep running in a terminal)

### 2. Cloud Storage Setup (Supabase)
1. Sign up at [supabase.com](https://supabase.com) (free tier)
2. Create a new project.
3. Get your **Project URL** and **`anon` key** from Project Settings > API.
4. Create the `candidates` table in your Supabase database using the SQL schema provided in the project instructions.
5. Create a `.env` file in the project root (if you haven't already).
6. Add your Supabase credentials to the `.env` file:
   ```dotenv
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   ```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Application
```bash
streamlit run app.py
```

## Features
- Collects candidate personal and technical information.
- Generates personalized technical questions using Ollama.
- Accepts Loom video share links for question responses.
- Stores candidate data and Loom links in **Supabase** with a local **JSON file fallback** (`data/candidates.json`).
- Provides clear instructions on how to use Loom.
- Clean, professional interface.

## Troubleshooting

### Data Saving Issues
- **Supabase Save Failed**: Check internet connection, `.env` file credentials, and ensure the `candidates` table exists in Supabase. Data will automatically attempt to save to `data/candidates.json` as a fallback.
- **Local Save Failed**: Check disk space and file permissions for the `data/` directory.
- **NameError: name 'save_candidate_hybrid' is not defined**: Ensure the `supabase_client.py` file exists and the `save_candidate_hybrid` function is correctly implemented and imported in `app.py`.

### AI Question Generation Issues
- **Connection Error**: Make sure Ollama is running (`ollama serve`).
- **Model Not Found**: Run `ollama pull llama3.2:3b`.

### General Issues
- **Port Issues**: Change Streamlit port with `streamlit run app.py --server.port 8502`.

## Security Notes
- Never commit your `.env` file with real credentials to version control.
- Use environment variables for sensitive data (like Supabase keys).
- Candidate data (excluding video content, which is on Loom) is stored in your Supabase database and locally in `data/candidates.json`.
