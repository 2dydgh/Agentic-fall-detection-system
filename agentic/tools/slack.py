import requests
import json

def send_slack_alert(
    webhook_url: str,
    severity: str,
    scene_description: str,
    incident_id: str
) -> bool:
    """Slack으로 긴급 알림 발송"""
    emoji = "🚨" if severity == "HIGH" else "⚠️"

    payload = {
        "text": f"{emoji} *낙상 감지 - {severity}*",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{emoji} 낙상 감지 알림", "emoji": True}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*심각도:*\n{severity}"},
                    {"type": "mrkdwn", "text": f"*사건번호:*\n{incident_id}"}
                ]
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*상황:*\n{scene_description}"}
            }
        ]
    }

    try:
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Slack 알림 실패: {e}")
        return False
