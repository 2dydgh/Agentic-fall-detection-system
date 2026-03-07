import os
import smtplib
from email.message import EmailMessage

def send_email_alert(
    sender_email: str,
    sender_password: str,
    receiver_email: str,
    severity: str,
    scene_description: str,
    incident_id: str,
    snapshot_path: str = None,
    report_path: str = None
) -> bool:
    """이메일로 긴급 알림 및 사진/보고서 발송"""
    emoji = "🚨" if severity == "HIGH" else "⚠️"
    subject = f"{emoji} [긴급] 낙상 감지 알림 - 심각도: {severity}"
    
    body = f"""
✅ 낙상 감지 시스템 경보

사건번호: {incident_id}
심각도: {severity}

[현장 상황 요약]
{scene_description}

빠른 확인 및 조치를 부탁드립니다.
자세한 내용은 첨부된 스냅샷과 보고서를 확인하세요.
    """
    
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg.set_content(body)

    # 스냅샷 첨부
    if snapshot_path and os.path.exists(snapshot_path):
        with open(snapshot_path, 'rb') as img:
            img_data = img.read()
            msg.add_attachment(img_data, maintype='image', subtype='jpeg', filename=os.path.basename(snapshot_path))

    # 텍스트 보고서 첨부
    if report_path and os.path.exists(report_path):
        with open(report_path, 'r', encoding='utf-8') as txt:
            txt_data = txt.read()
            msg.add_attachment(txt_data.encode('utf-8'), maintype='text', subtype='plain', filename=os.path.basename(report_path))

    try:
        # Gmail SMTP 서버 설정 (보안 연결)
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        
        # Remove spaces from app password which can cause auth failures
        clean_password = sender_password.replace(" ", "") if sender_password else ""
        
        server.login(sender_email, clean_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"이메일 발송 실패: {e}")
        return False
