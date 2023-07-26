import json
import os
from pathlib import Path

import requests
import slack
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from slackeventsapi import SlackEventAdapter

env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)


SLACK_API_TOKEN = os.environ["SLACK_TOKEN"]
SLACK_CHANNEL_ID = "#general"  # Replace with the ID of your target Slack channel


@app.route("/receive-messages", methods=["POST"])
def receive_messages():
    try:
        data = request.get_json()  # Assuming the data sent by the Apps Script is in JSON format
        print("Received message:")
        print(data)

        # Assuming the message content is in the 'message' field of the data dictionary
        # message_content = data.get("message", "")

        # Send the message to Slack with buttons
        send_to_slack(data)

        return "Message received successfully", 200
    except Exception as e:
        print("Error while processing the message:", e)
        return "Error processing the message", 500


def send_to_slack(data):
    print("Send To Slack: ", data)
    formatted_message = json.dumps(data, indent=2)
    accept_url = "https://48f9-102-89-33-154.ngrok.io/accept-action"
    reject_url = "https://48f9-102-89-33-154.ngrok.io/reject-action"

    payload = {
        "channel": SLACK_CHANNEL_ID,
        "text": "*Here's the message content and form responses:*",
        "attachments": [
            {
                "fallback": "You are unable to accept or reject the message",
                "text": f"```{formatted_message}```",
                "callback_id": "accept_or_reject_message",
                "actions": [
                    {"name": "accept", "text": "Accept", "type": "button", "value": "accept", "url": accept_url},
                    {"name": "reject", "text": "Reject", "type": "button", "value": "reject", "url": reject_url},
                ],
            }
        ],
    }

    # Make a POST request to Slack API to send the message
    url = "https://slack.com/api/chat.postMessage"
    headers = {"Authorization": f"Bearer {SLACK_API_TOKEN}"}
    response = requests.post(url, json=payload, headers=headers)

    # Check if the message was sent successfully
    if response.status_code == 200 and response.json().get("ok", False):
        print("Message sent to Slack successfully.")
    else:
        print("Error while sending message to Slack.")
        print(response.json())


@app.route("/slack-interaction", methods=["POST"])
def slack_interaction():
    # Extract the user's name from the Slack interaction payload
    payload = request.get_json()
    user_name = payload["user"]["name"]
    action = payload["actions"][0]["value"]

    # Determine the action and send the corresponding message to the other Slack channel
    if action == "accept":
        message = f"{user_name} accepts"
    elif action == "reject":
        message = f"{user_name} rejects"
    else:
        message = "Unknown action"

    # Send the message to the other Slack channel
    payload = {
        "channel": "#bots",
        "text": message,
    }
    url = "https://slack.com/api/chat.postMessage"
    headers = {"Authorization": f"Bearer {SLACK_API_TOKEN}"}
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200 and response.json().get("ok", False):
        print("Message sent to the other Slack channel successfully.")
    else:
        print("Error while sending message to the other Slack channel.")
        print(response.json())

    return jsonify({"message": "Interaction handled successfully"}), 200


slack_event_adapter = SlackEventAdapter(os.environ["SIGNING"], "/slack/events", app)


client = slack.WebClient(token=os.environ["SLACK_TOKEN"])
BOT_ID = client.api_call("auth.test")["user_id"]


@slack_event_adapter.on("message")
def message(payload):
    print(payload)
    event = payload.get("event", {})
    channel_id = event.get("channel")
    user_id = event.get("user")
    text = event.get("text")

    if BOT_ID != user_id:
        client.chat_postMessage(channel=channel_id, text=text)


if __name__ == "__main__":
    app.run(debug=True)
