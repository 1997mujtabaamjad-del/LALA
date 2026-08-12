"""Email Sending SMTP Automator supporting CC recipients & Gmail Dashboard Integration."""

import os
import smtplib
import webbrowser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class EmailAutomatorAgent:
    """SMTP Email Automator for sending CC emails and launching Gmail Dashboard."""

    def __init__(self, smtp_server: str = "smtp.gmail.com", port: int = 587):
        self.smtp_server = os.getenv("SMTP_SERVER", smtp_server)
        self.port = int(os.getenv("SMTP_PORT", port))
        self.sender_email = os.getenv("SENDER_EMAIL", "")
        self.sender_password = os.getenv("SENDER_PASSWORD", "")

    def send_email(self, to_email: str, subject: str, body: str, cc_list: list = None) -> str:
        """Send email with optional CC recipients via SMTP."""
        if not self.sender_email or not self.sender_password:
            # Fallback: Compose draft in default mail client / Gmail browser
            cc_str = f"&cc={','.join(cc_list)}" if cc_list else ""
            mailto_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={to_email}&su={subject}&body={body}{cc_str}"
            webbrowser.open(mailto_url)
            return f"Gmail web composer opened for recipient '{to_email}' with CC list: {cc_list or []}."

        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject

            recipients = [to_email]
            if cc_list:
                msg['Cc'] = ", ".join(cc_list)
                recipients.extend(cc_list)

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.smtp_server, self.port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, recipients, msg.as_string())
            server.quit()

            return f"Email successfully sent to '{to_email}' with CC recipients: {cc_list or 'None'}."
        except Exception as e:
            return f"Failed to send email via SMTP: {e}"

    def open_gmail_dashboard(self) -> str:
        """Open Gmail Dashboard web interface."""
        webbrowser.open("https://mail.google.com/mail/u/0/#inbox")
        return "Gmail Dashboard Dashboard opened in web browser."
