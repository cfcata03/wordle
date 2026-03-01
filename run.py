"""
Launch the Wordle web app (Flask).
  python run.py
Then open http://127.0.0.1:5000 in your browser.
"""
from app import app

if __name__ == "__main__":
    app.run(debug=True, port=5000)
