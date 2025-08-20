from pathlib import Path

# Path to the consolidated guide
GUIDE_PATH = Path(__file__).parent.parent / "docs/development/CONSOLIDATED_README_GUIDE.md"
README_PATH = Path(__file__).parent.parent / "twickenham_events/README.md"

# Helper: Read file

def read_file(path):
    with open(path, encoding="utf-8") as f:
        return f.read()

def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

# Helper: Use Copilot/AI agent for doc update

def ai_update_readme(readme, guide, context):
    """
    Use Gemini 2.5 Pro API to rewrite README using the consolidated guide and recent context.
    Requires: pip install google-generativeai
    """
    import os
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set. Skipping AI update.")
        return readme
    genai.configure(api_key=api_key)
    prompt = (
        "Rewrite the following README.md for a Python project. "
        "Follow the standards and structure in the provided documentation guide. "
        "Incorporate any recent environment/config/validator changes from the context. "
        "Do not use promotional language. Be factual, clear, and user-focused. "
        "Output only the updated README.md content.\n\n"
        "Documentation Guide:\n" + guide + "\n\n"
        "Current README.md:\n" + readme + "\n\n"
        "Recent context (changes):\n" + context
    )
    try:
        model = genai.GenerativeModel(model_name="gemini-2.5-pro")
        response = model.generate_content([prompt])
        updated = response.candidates[0].content.parts[0].text.strip()
        return updated
    except Exception as e:
        print(f"Gemini API call failed: {e}. Skipping AI update.")
        return readme

# Main logic

def main():
    guide = read_file(GUIDE_PATH)
    readme = read_file(README_PATH)
    # Gather context: env/config/validator changes
    context = ""  # Could be git diff, or recent commit messages
    # Call AI agent to update README
    updated_readme = ai_update_readme(readme, guide, context)
    if updated_readme != readme:
        write_file(README_PATH, updated_readme)
        print("README.md updated by AI agent.")
    else:
        print("README.md is already up to date.")

if __name__ == "__main__":
    main()
