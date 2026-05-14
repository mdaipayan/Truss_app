import csv
import datetime
from pathlib import Path

FEEDBACK_COLUMNS = ["timestamp", "rating", "category", "comments"]
FEEDBACK_FILE = Path(__file__).resolve().parent / "feedback.csv"


def ensure_feedback_file(feedback_file=FEEDBACK_FILE):
    feedback_file = Path(feedback_file)
    feedback_file.parent.mkdir(parents=True, exist_ok=True)
    if not feedback_file.exists() or feedback_file.stat().st_size == 0:
        with feedback_file.open("w", newline="", encoding="utf-8") as csv_file:
            csv.DictWriter(csv_file, fieldnames=FEEDBACK_COLUMNS).writeheader()
    return feedback_file


def save_feedback(rating, category, comments, feedback_file=FEEDBACK_FILE):
    feedback_file = ensure_feedback_file(feedback_file)
    with feedback_file.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FEEDBACK_COLUMNS)
        writer.writerow({
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "rating": int(rating),
            "category": str(category),
            "comments": str(comments).strip(),
        })
    return feedback_file
