from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)


DATABASE = os.path.join(
    os.path.dirname(__file__),
    "../database/gruhalakshmi.db"
)

CITIZEN_SERVICE_URL = os.getenv(
    "CITIZEN_SERVICE_URL",
    "http://localhost:5001"
)


def get_db():
    return sqlite3.connect(DATABASE)


def initialize_database():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            citizen_id INTEGER NOT NULL,
            ration_card TEXT NOT NULL,
            is_household_head INTEGER NOT NULL,
            annual_income REAL NOT NULL,
            eligibility TEXT NOT NULL,
            status TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            month TEXT NOT NULL,
            year INTEGER NOT NULL,
            status TEXT NOT NULL,
            paid_at TEXT NOT NULL,
            FOREIGN KEY (application_id)
            REFERENCES applications(id)
        )
    """)

    db.commit()
    db.close()


@app.route("/", methods=["GET"])
def home():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), "../frontend"),
        "index.html"
    )


@app.route("/style.css")
def style():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), "../frontend"),
        "style.css"
    )


@app.route("/script.js")
def script():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__), "../frontend"),
        "script.js"
    )
    
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "service": "Gruha Lakshmi Service",
        "status": "running"
    })


@app.route("/applications", methods=["POST"])
def create_application():

    data = request.json

    citizen_id = data.get("citizen_id")
    ration_card = data.get("ration_card")
    is_household_head = data.get("is_household_head")
    annual_income = data.get("annual_income")

    if citizen_id is None:
        return jsonify({
            "error": "citizen_id is required"
        }), 400

    if not ration_card:
        return jsonify({
            "error": "ration_card is required"
        }), 400

    if is_household_head is None:
        return jsonify({
            "error": "is_household_head is required"
        }), 400

    if annual_income is None:
        return jsonify({
            "error": "annual_income is required"
        }), 400

    # -------------------------------------------------------
    # Verify citizen using Citizen Service REST API
    # -------------------------------------------------------

    try:
        citizen_response = requests.get(
            f"{CITIZEN_SERVICE_URL}/citizens/{citizen_id}",
            timeout=3
        )

    except requests.RequestException:
        return jsonify({
            "error": "Citizen Service is unavailable"
        }), 503

    if citizen_response.status_code == 404:
        return jsonify({
            "error": "Citizen is not registered"
        }), 400

    if not citizen_response.ok:
        return jsonify({
            "error": "Unable to verify citizen"
        }), 502

    # -------------------------------------------------------
    # Simplified project eligibility rule
    # -------------------------------------------------------

    if not is_household_head:
        eligibility = "NOT_ELIGIBLE"
        status = "REJECTED"
    else:
        eligibility = "ELIGIBLE"
        status = "APPROVED"

    # -------------------------------------------------------
    # Save application
    # -------------------------------------------------------

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO applications
        (
            citizen_id,
            ration_card,
            is_household_head,
            annual_income,
            eligibility,
            status,
            applied_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        citizen_id,
        ration_card,
        int(bool(is_household_head)),
        float(annual_income),
        eligibility,
        status,
        datetime.now().isoformat()
    ))

    db.commit()

    application_id = cursor.lastrowid

    db.close()

    return jsonify({
        "application_id": application_id,
        "citizen_id": citizen_id,
        "ration_card": ration_card,
        "is_household_head": bool(is_household_head),
        "annual_income": annual_income,
        "eligibility": eligibility,
        "status": status,
        "citizen": citizen_response.json()
    }), 201


@app.route("/applications/<int:application_id>", methods=["GET"])
def get_application(application_id):

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT
            id,
            citizen_id,
            ration_card,
            is_household_head,
            annual_income,
            eligibility,
            status,
            applied_at
        FROM applications
        WHERE id = ?
    """, (application_id,))

    application = cursor.fetchone()

    db.close()

    if application is None:
        return jsonify({
            "error": "Application not found"
        }), 404

    return jsonify({
        "application_id": application[0],
        "citizen_id": application[1],
        "ration_card": application[2],
        "is_household_head": bool(application[3]),
        "annual_income": application[4],
        "eligibility": application[5],
        "status": application[6],
        "applied_at": application[7]
    })


@app.route("/applications/<int:application_id>/payment", methods=["POST"])
def make_payment(application_id):

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT id, citizen_id, eligibility, status
        FROM applications
        WHERE id = ?
    """, (application_id,))

    application = cursor.fetchone()

    if application is None:
        db.close()

        return jsonify({
            "error": "Application not found"
        }), 404

    eligibility = application[2]
    status = application[3]

    if eligibility != "ELIGIBLE" or status != "APPROVED":
        db.close()

        return jsonify({
            "error": "Applicant is not eligible for payment"
        }), 400

    # -------------------------------------------------------
    # Payment information
    # -------------------------------------------------------

    data = request.json or {}

    month = data.get(
        "month",
        datetime.now().strftime("%B")
    )

    year = int(data.get(
        "year",
        datetime.now().year
    ))

    amount = 2000

    # Prevent duplicate payment for same month/year
    cursor.execute("""
        SELECT id
        FROM payments
        WHERE application_id = ?
        AND month = ?
        AND year = ?
    """, (
        application_id,
        month,
        year
    ))

    existing_payment = cursor.fetchone()

    if existing_payment:

        db.close()

        return jsonify({
            "error": "Payment already made for this month",
            "payment_id": existing_payment[0]
        }), 409

    cursor.execute("""
        INSERT INTO payments
        (
            application_id,
            amount,
            month,
            year,
            status,
            paid_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        application_id,
        amount,
        month,
        year,
        "SUCCESS",
        datetime.now().isoformat()
    ))

    db.commit()

    payment_id = cursor.lastrowid

    db.close()

    return jsonify({
        "payment_id": payment_id,
        "application_id": application_id,
        "amount": amount,
        "month": month,
        "year": year,
        "status": "SUCCESS"
    }), 201


if __name__ == "__main__":

    initialize_database()

    app.run(
        port=5003,
        debug=True
    )
