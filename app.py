from flask import Flask, render_template, request, jsonify, Response
import pickle
import string
import json
import csv
import random
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import Counter, defaultdict
from io import StringIO
import re 

app = Flask(__name__)

MODEL_PATH = Path("priority_model.pkl")
VECTORIZER_PATH = Path("vectorizer.pkl")
LOG_PATH = Path("messages_log.jsonl")
FEEDBACK_PATH = Path("feedback.jsonl")

model = pickle.load(open(MODEL_PATH, "rb"))
vectorizer = pickle.load(open(VECTORIZER_PATH, "rb"))

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def clean_text(text: str) -> str:
    text = (text or "").lower().strip()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return text

def append_jsonl(path: Path, obj: dict):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
def load_feedback_dict():
    feedback_list = []

    if not FEEDBACK_PATH.exists():
        return feedback_list

    with open(FEEDBACK_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                msg = clean_text(data.get("message", ""))
                correct = data.get("correct_priority", "")
                if msg and correct:
                    feedback_list.append((msg, correct))
            except:
                pass

    return feedback_list

risk_words = {
    "otp": 10, "verification": 9, "password": 9, "security": 9, "fraud": 10,
    "urgent": 8, "deadline": 8, "interview": 8,
    "salary": 7, "payment": 7, "bank": 7, "transaction": 7, "withdraw": 7,
    "aadhar": 7, "credit": 6, "debit": 6, "loan": 6, "alert": 6,
    "meeting": 5, "appointment": 5, "doctor": 5,
    "project": 4, "report": 4, "manager": 4, "boss": 4, "client": 4,
    "flight": 4, "ticket": 4, "invoice": 4,
    "reminder": 3, "schedule": 3, "update": 3, "discussion": 3, "plan": 3,
    "invite": 2, "invitation": 2, "event": 2, "party": 2, "newsletter": 2,
    "today": 1, "tomorrow": 1,
    "sale": -4, "offer": -4, "discount": -4, "promo": -4,
    "coupon": -3, "deal": -3, "free": -3,
    "advertisement": -5, "spam": -7, "meme": -2
}
category_keywords = {
    "OTP": {"otp", "verification", "password", "login", "security", "pin"},
    "Transactions": {"bank", "salary", "payment", "transaction", "withdraw", "debit", "credit", "loan", "invoice", "upi", "refund", "amount"},
    "Personal": {"friend", "family", "birthday", "party", "invite", "invitation", "photo", "message", "chat", "wedding", "trip", "plan"},
    "Work": {"meeting", "deadline", "project", "client", "manager", "boss", "interview", "report", "office", "review", "presentation", "submission"},
}

spam_keywords = {"spam", "offer", "sale", "discount", "promo", "advertisement", "coupon", "deal", "free"}

sample_messages = [
    "Your OTP is 483920",
    "Urgent meeting with manager at 5 PM",
    "Salary credited to your account",
    "Big sale on electronics - limited offer",
    "Doctor appointment confirmed for tomorrow",
    "Friend party invitation this weekend",
    "Bank alert: transaction detected",
    "Reminder for assignment submission today",
    "Interview scheduled tomorrow",
    "Loan repayment due today"
]

def detect_category(cleaned: str) -> tuple[str, list[str]]:
    words = set(cleaned.split())
    best_cat = "Personal"
    best_hits = []

    for cat, kws in category_keywords.items():
        hits = sorted(words.intersection(kws))
        if len(hits) > len(best_hits):
            best_cat = cat
            best_hits = hits

    return best_cat, best_hits

def calculate_consequence_score(cleaned_text: str):
    words = cleaned_text.split()
    score = 0
    matched = []
    for word in words:
        if word in risk_words:
            score += risk_words[word]
            matched.append(word)
    return score, matched

    if priority == "high":
        progress = 100
    elif priority == "Medium":
        progress = 60
    else:
        progress = 20

def action_label(priority: str, score: int):
    if score >= 6:
        return "Act Now"
    if score >= 3:
        return "Reply / Review"
    if score <= -3:
        return "Ignore Safe"
    if priority == "High":
        return "Act Now"
    if priority == "Low":
        return "Ignore Safe"
    return "Read Later"

def explain_decision(cleaned_text: str, confidence: float, score: int, matched_words: list, predicted_priority: str, category: str, category_hits: list):
    reasons = []
    if matched_words:
        reasons.append(f"Matched priority keywords: {', '.join(sorted(set(matched_words)))}")
    else:
        reasons.append("No strong priority keywords matched")

    if category_hits:
        reasons.append(f"Category signals: {category} ({', '.join(category_hits)})")
    else:
        reasons.append(f"Category inferred: {category}")

    reasons.append(f"Model confidence: {confidence:.2f}")
    reasons.append(f"Consequence score: {score}")

    if score >= 6:
        reasons.append("High consequence signal detected")
    elif score <= -3:
        reasons.append("Likely low-value / spam-like content")
    else:
        reasons.append(f"ML predicted: {predicted_priority}")

    return reasons

def predict_priority(msg: str, sender: str = "", privacy_mode: bool = False):
    cleaned = clean_text(msg)
    feedback_list = load_feedback_dict()
    for fb_msg, fb_priority in feedback_list:
        if fb_msg in cleaned:
            final_priority = fb_priority
            confidence = 1.0
            break
        else:
            final_priority = None
    vect = vectorizer.transform([cleaned])
    probs = model.predict_proba(vect)[0]
    classes = model.classes_
    top_idx = probs.argmax()
    ml_prediction = classes[top_idx]

    if final_priority is None:
        final_priority = ml_prediction
        confidence = float(probs[top_idx])
    score, matched_words = calculate_consequence_score(cleaned)
    category, category_hits = detect_category(cleaned)

    if score >= 6:
        final_priority = "High"
    elif score <= -3:
        final_priority = "Low"
    else:
        if confidence >= 0.6:
            final_priority = ml_prediction
        elif 0.4 <= confidence < 0.6:
            final_priority = "Medium"
        else:
            final_priority = "Medium"

    label = action_label(final_priority, score)
    reasons = explain_decision(cleaned, confidence, score, matched_words, ml_prediction, category, category_hits)

    record = {
        "timestamp": now_iso(),
        "message": msg if not privacy_mode else "[REDACTED]",
        "cleaned": cleaned if not privacy_mode else "[REDACTED]",
        "sender": sender,
        "priority": final_priority,
        "action_label": label,
        "category": category,
        "confidence": round(confidence, 2),
        "score": score,
        "matched_words": matched_words,
        "reasons": reasons,
        "privacy_mode": privacy_mode
    }

    append_jsonl(LOG_PATH, record)
    return record

def load_recent_logs(limit=50):
    if not LOG_PATH.exists():
        return []
    items = []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                items.append(json.loads(line))
            except Exception:
                pass
    return items[-limit:][::-1]

def get_stats():
    recent = load_recent_logs(500)
    priority_counts = Counter(item.get("priority", "Medium") for item in recent)
    category_counts = Counter(item.get("category", "Personal") for item in recent)

    # daily trend last 7 days
    today = datetime.now(timezone.utc).date()
    days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    daily = []
    for d in days:
        d_str = d.isoformat()
        count = sum(1 for item in recent if str(item.get("timestamp", "")).startswith(d_str))
        daily.append({"date": d_str, "count": count})

    return {
        "priority_counts": {
            "High": priority_counts.get("High", 0),
            "Medium": priority_counts.get("Medium", 0),
            "Low": priority_counts.get("Low", 0)
        },
        "category_counts": {
            "OTP": category_counts.get("OTP", 0),
            "Transactions": category_counts.get("Transactions", 0),
            "Personal": category_counts.get("Personal", 0),
            "Work": category_counts.get("Work", 0)
        },
        "daily_counts": daily
    }
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json(force=True)
    msg = (data.get("text") or "").strip()
    sender = (data.get("sender") or "").strip()
    privacy_mode = bool(data.get("privacy_mode", False))
    
    if not msg:
        return jsonify({
            "message": "",
            "cleaned": "",
            "priority": "Medium",
            "action_label": "Read Later",
            "category": "Personal",
            "confidence": 0.0,
            "score": 0,
            "matched_words": [],
            "reasons": ["Empty message"],
            "privacy_mode": privacy_mode
        })

    result = predict_priority(msg, sender=sender, privacy_mode=privacy_mode)
    return jsonify(result)

@app.route("/recent", methods=["GET"])
def recent():
    return jsonify({"items": load_recent_logs(50)})

@app.route("/stats", methods=["GET"])
def stats():
    return jsonify(get_stats())

@app.route("/feedback", methods=["POST"])
def feedback():
    data = request.get_json(force=True)

    entry = {
        "timestamp": now_iso(),
        "message": clean_text(data.get("message", "")),  # 🔥 FIX
        "predicted_priority": data.get("predicted_priority", ""),
        "correct_priority": data.get("correct_priority", ""),
        "action_label": data.get("action_label", ""),
        "confidence": data.get("confidence", 0),
        "score": data.get("score", 0),
        "matched_words": data.get("matched_words", []),
        "category": data.get("category", ""),
        "privacy_mode": data.get("privacy_mode", False)
    }

    append_jsonl(FEEDBACK_PATH, entry)

    return jsonify({"status": "saved"})

@app.route("/simulate", methods=["GET"])
def simulate():
    return jsonify({"message": random.choice(sample_messages)})

@app.route("/export", methods=["GET"])
def export():
    recent = load_recent_logs(10000)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "message", "priority", "action_label", "category", "confidence", "score", "sender", "privacy_mode"])
    for item in recent:
        writer.writerow([
            item.get("timestamp", ""),
            item.get("message", ""),
            item.get("priority", ""),
            item.get("action_label", ""),
            item.get("category", ""),
            item.get("confidence", ""),
            item.get("score", ""),
            item.get("sender", ""),
            item.get("privacy_mode", False),
        ])
    csv_data = output.getvalue()
    output.close()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=smartpriority_export.csv"}
    )


def clean_text(text: str) -> str:
    text = (text or "").lower().strip()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\d+", " number ", text)
    return text
if __name__ == "__main__":
    app.run(debug=True)