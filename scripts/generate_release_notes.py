import subprocess
from pathlib import Path

def get_latest_tag():
    result = subprocess.run(["git", "tag", "--sort=-creatordate"], capture_output=True, text=True)
    tags = result.stdout.strip().split("\n")
    return tags[0] if tags else None

def get_commits_since(tag):
    result = subprocess.run(["git", "log", f"{tag}..HEAD", "--oneline", "--no-merges"], capture_output=True, text=True)
    return result.stdout.strip().split("\n")

def ai_generate_release_notes(commits):
    """
    Use Gemini 2.5 Pro API to summarize commit messages into clear, user-focused release notes.
    Requires: pip install google-generativeai
    """
    import os
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set. Falling back to raw commit list.")
        return "\n".join([f"- {c[8:]}" if len(c) > 8 else f"- {c}" for c in commits])
    genai.configure(api_key=api_key)
    prompt = (
        "Summarize the following git commit messages into concise, user-focused release notes. "
        "Do not use promotional language. Group related changes. Use bullet points. "
        "Follow factual, clear style.\n\nCommit messages:\n" + "\n".join(commits)
    )
    try:
        model = genai.GenerativeModel(model_name="gemini-2.5-pro")
        response = model.generate_content([prompt])
        notes = response.candidates[0].content.parts[0].text.strip()
        return notes
    except Exception as e:
        print(f"Gemini API call failed: {e}. Falling back to raw commit list.")
        return "\n".join([f"- {c[8:]}" if len(c) > 8 else f"- {c}" for c in commits])

def main():
    tag = get_latest_tag()
    if not tag:
        print("No tags found.")
        return
    commits = get_commits_since(tag)
    notes = ai_generate_release_notes(commits)
    notes_path = Path(__file__).parent.parent / "release_notes.txt"
    with open(notes_path, "w", encoding="utf-8") as f:
        f.write(notes)
    print(f"Release notes generated at {notes_path}")

if __name__ == "__main__":
    main()
