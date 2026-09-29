import base64
import os
import tempfile

import yagmail
from flask import Flask, jsonify, request

app = Flask(__name__)

GMAIL_USER     = os.environ.get("GMAIL_USER")
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD")


def get_yag():
    """Return a fresh yagmail SMTP client."""
    return yagmail.SMTP(GMAIL_USER, GMAIL_PASSWORD)


@app.route("/api/<sender_id>/email", methods=["POST"])
def send_email(sender_id):
    data = request.get_json(force=True, silent=True) or {}

    address = data.get("Address") or data.get("address")
    subject = data.get("Subject") or data.get("subject") or "Notification"
    message = data.get("Message") or data.get("message") or ""

    if not address or not message:
        return jsonify(False), 400

    try:
        get_yag().send(
            to=address,
            subject=subject,
            contents=[yagmail.inline(message)] if "<" in message else message,
        )
        app.logger.info("Plain email sent to %s (from sender: %s)", address, sender_id)
        return jsonify(True), 200
    except Exception as exc:
        app.logger.error("Failed to send plain email to %s: %s", address, exc)
        return jsonify(False), 500


@app.route("/api/<sender_id>/emailwithattachement", methods=["POST"])
def send_email_with_attachment(sender_id):
    data = request.get_json(force=True, silent=True) or {}

    address    = data.get("Address")    or data.get("address")
    subject    = data.get("Subject")    or data.get("subject")    or "Notification"
    message    = data.get("Message")    or data.get("message")    or ""
    attachment = data.get("Attachment") or data.get("attachment") 
    file_name  = data.get("FileName")   or data.get("fileName")   or "attachment.xlsx"

    if not address or not attachment:
        return jsonify(False), 400

    try:
        file_bytes = base64.b64decode(attachment)
    except Exception as exc:
        app.logger.error("Bad base64 attachment: %s", exc)
        return jsonify(False), 400

    suffix = os.path.splitext(file_name)[-1] or ".xlsx"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        tmp.write(file_bytes)
        tmp.flush()
        tmp.close()

        recipients = [e.strip() for e in address.split(",") if e.strip()]

        get_yag().send(
            to=recipients,
            subject=subject,
            contents=[yagmail.inline(message)] if "<" in message else message,
            attachments=tmp.name,
        )
        app.logger.info(
            "Email with attachment '%s' sent to %s (from sender: %s)",
            file_name, recipients, sender_id,
        )
        return jsonify(True), 200

    except Exception as exc:
        app.logger.error(
            "Failed to send attachment email to %s: %s", address, exc
        )
        return jsonify(False), 500

    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "user": GMAIL_USER}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=False)
