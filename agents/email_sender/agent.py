import os
import json
import base64
import httpx
from email.message import EmailMessage
from google.adk.agents import Agent

MODEL = "gemini-2.5-pro"

def get_user_email(token: str) -> str:
    """Fetches the user's email address using the OAuth token."""
    try:
        resp = httpx.get("https://www.googleapis.com/oauth2/v3/userinfo", 
                         headers={"Authorization": f"Bearer {token}"}, 
                         timeout=5.0)
        if resp.status_code == 200:
            return resp.json().get("email", "me")
    except Exception:
        pass
    return "me"

def send_gmail_message(
    recipient_email: str,
    subject: str,
    body_text: str,
    user_oauth_token: str = ""
) -> str:
    """
    Sends a real Gmail message via the Gmail API using a provided OAuth token.

    Args:
        recipient_email:  The user's email address.
        subject:          Email subject line.
        body_text:        The full travel itinerary (Markdown format is fine).
        user_oauth_token: The user's OAuth token with 'https://www.googleapis.com/auth/gmail.send'.
    Returns:
        JSON string indicating success or error.
    """
    if not user_oauth_token:
        return json.dumps({
            "status": "error",
            "message": "Missing required Gmail OAuth token. Please ensure you are logged in."
        })

    # Create the MIME message
    mime_msg = EmailMessage()
    mime_msg.set_content(body_text)
    
    # If recipient is unknown or "me", try to find the real email for the header
    final_recipient = recipient_email
    if not final_recipient or final_recipient == "me":
        final_recipient = get_user_email(user_oauth_token)

    mime_msg["To"] = final_recipient
    mime_msg["Subject"] = subject
    
    # Gmail API requires the message to be base64url encoded
    raw_message = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()

    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    headers = {
        "Authorization": f"Bearer {user_oauth_token}",
        "Content-Type": "application/json"
    }
    payload = {"raw": raw_message}

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=10.0)
        if response.status_code == 200:
            return json.dumps({
                "status": "success",
                "message": "Email dispatched successfully to your inbox.",
                "gmail_id": response.json().get("id")
            })
        else:
            return json.dumps({
                "status": "error",
                "message": f"Gmail API Error: {response.text}",
                "status_code": response.status_code
            })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Transport Error: {str(e)}"
        })

email_sender = Agent(
    name="email_sender",
    model=MODEL,
    description="I am your personal Travel Concierge Email Assistant. I format and send confirmed travel itineraries directly to your Gmail inbox.",
    instruction="""
    You are a professional Travel Email Assistant.
    
    Your job:
    1. Receive a travel itinerary from the Orchestrator.
    2. Call `send_gmail_message` with:
       - recipient_email: (You must extract the user's email if provided, or use 'me')
       - subject: "Your Finalized Travel Itinerary: Mumbai Trip" (or appropriate title)
       - body_text: The clean, professional travel summary.
       - user_oauth_token: The [SYSTEM] token provided by the orchestrator.
    
    3. Confirm to the user that the email has been sent.
    """,
    tools=[send_gmail_message],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

root_agent = email_sender
