"""WhatsApp Texting, Chat Search, Draft Typing, and Voice/Video Calling Automation Agent."""

import time
import urllib.parse
import webbrowser

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except Exception:
    pyautogui = None
    HAS_PYAUTOGUI = False

try:
    import pywhatkit
    HAS_PYWHATKIT = True
except Exception:
    pywhatkit = None
    HAS_PYWHATKIT = False


class WhatsAppAgent:
    """WhatsApp Texting, Chat Search, Draft Typing, and Voice/Video Calling Agent."""

    def send_message(self, target: str, message: str) -> str:
        """Send WhatsApp message to contact name or phone number."""
        clean_target = target.strip()
        clean_msg = message.strip()

        if clean_target.startswith("+") or clean_target.isdigit():
            if HAS_PYWHATKIT and pywhatkit:
                try:
                    pywhatkit.sendwhatmsg_instantly(clean_target, clean_msg, wait_time=8, tab_close=True)
                    return f"WhatsApp message instantly sent to {clean_target}: '{clean_msg}'"
                except Exception as e:
                    print(f"[WhatsAppAgent] PyWhatKit send info: {e}")

        url = f"https://web.whatsapp.com/send?phone={urllib.parse.quote(clean_target)}&text={urllib.parse.quote(clean_msg)}"
        webbrowser.open(url)
        return f"WhatsApp chat opened for {clean_target} with message draft: '{clean_msg}'"

    def open_chat(self, contact_name: str) -> str:
        """Open WhatsApp chat window for contact."""
        webbrowser.open("https://web.whatsapp.com")
        if HAS_PYAUTOGUI and pyautogui:
            time.sleep(3)
            pyautogui.hotkey("ctrl", "alt", "/")
            pyautogui.write(contact_name, interval=0.1)
            pyautogui.press("enter")
        return f"WhatsApp Web opened and chat search initiated for contact: '{contact_name}'"

    def search_chat(self, contact_name: str) -> str:
        """Search WhatsApp chat history for contact."""
        return self.open_chat(contact_name)

    def type_message_draft(self, text: str) -> str:
        """Type message into active WhatsApp chat window without sending."""
        if HAS_PYAUTOGUI and pyautogui:
            pyautogui.write(text, interval=0.05)
            return f"Draft message typed into active WhatsApp chat window: '{text}'"
        return f"Message drafted: '{text}'"

    def make_call(self, contact_name: str, call_type: str = "voice") -> str:
        """Dispatch WhatsApp voice or video call to contact."""
        self.open_chat(contact_name)
        if HAS_PYAUTOGUI and pyautogui:
            time.sleep(2)
            if call_type.lower() == "video":
                pyautogui.hotkey("ctrl", "alt", "v")
                return f"WhatsApp Video Call initiated to '{contact_name}'."
            else:
                pyautogui.hotkey("ctrl", "alt", "c")
                return f"WhatsApp Voice Call initiated to '{contact_name}'."
        return f"WhatsApp opened to call '{contact_name}'."
