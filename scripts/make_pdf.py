"""
LALA one-pager PDF (dark, on-brand, hero artwork embedded).
  .venv/bin/python scripts/make_pdf.py   ->  LALA-one-pager.pdf
"""

import os

from fpdf import FPDF

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CY = (34, 211, 238)
VI = (167, 139, 250)
OK = (52, 211, 153)
DIM = (143, 154, 176)
WHT = (238, 241, 248)
BG = (5, 5, 7)


class PDF(FPDF):
    def dark(self):
        self.set_fill_color(*BG)
        self.rect(0, 0, 210, 297, "F")


pdf = PDF()
pdf.set_auto_page_break(False)
pdf.add_page()
pdf.dark()

# header
pdf.set_text_color(*CY)
pdf.set_font("Helvetica", "B", 26)
pdf.set_xy(15, 14)
pdf.cell(0, 12, "LALA", ln=True)
pdf.set_text_color(*DIM)
pdf.set_font("Helvetica", "", 10)
pdf.cell(0, 6, "Autonomous desktop voice assistant  ·  v1.0 -> v2.1  ·  MIT", ln=True)

# hero artwork
try:
    pdf.image(os.path.join(ROOT, "assets", "hero-brain.png"), x=15, y=30, w=180)
except Exception as e:
    print("artwork skipped:", e)

# tagline
pdf.set_xy(15, 134)
pdf.set_text_color(*WHT)
pdf.set_font("Helvetica", "B", 13)
pdf.multi_cell(180, 7, 'Say "Hey Laala" - your desktop just listens. '
                       'One brain, nine layers, zero paid dependencies.')

# pipeline
pdf.set_xy(15, 152)
pdf.set_text_color(*VI)
pdf.set_font("Helvetica", "B", 10)
pdf.cell(0, 6, "PIPELINE", ln=True)
pdf.set_text_color(*WHT)
pdf.set_font("Helvetica", "", 9)
pdf.cell(0, 6, "Wake -> Streaming STT -> Intent -> CEO/Planner -> Tools -> Response -> Streaming TTS  (+barge-in)", ln=True)

# nine layers (two columns)
layers = [
    ("Multi-Agent Brain", "CEO delegates to Research/Coding/Vision/Finance/Scheduler/Health/Home"),
    ("Long-Term Memory", "5 layers + consent-gated voiceprints"),
    ("World Model", "network/battery/weather/calendar/processes/devices"),
    ("Autonomous Planning", "interview prep: research->resume->questions->reminders"),
    ("Computer Vision", "screen capture + OCR; webcam/face consent-ready"),
    ("Digital Twin", "live env mirror + what-changed diffs"),
    ("Voice Pipeline", "streaming end-to-end, sub-second simple commands"),
    ("Tool Ecosystem", "terminal/code/email/calendar/maps/finance/home/PDF, gated"),
    ("Robotics", "ESP32/Pi/arms/drones via HTTP; motion confirmed"),
]
y = 168
pdf.set_text_color(*VI)
pdf.set_font("Helvetica", "B", 10)
pdf.set_xy(15, y - 6)
pdf.cell(0, 6, "THE NINE LAYERS", ln=True)
pdf.set_font("Helvetica", "", 8.4)
for i, (t, d) in enumerate(layers):
    col = i % 2
    row = i // 2
    x = 15 + col * 92
    yy = y + row * 14
    pdf.set_xy(x, yy)
    pdf.set_text_color(*CY)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(90, 5, t, ln=True)
    pdf.set_xy(x, yy + 5)
    pdf.set_text_color(*DIM)
    pdf.set_font("Helvetica", "", 7.6)
    pdf.multi_cell(88, 4, d)

# install + audit at bottom
y2 = 243
pdf.set_text_color(*VI)
pdf.set_font("Helvetica", "B", 10)
pdf.set_xy(15, y2)
pdf.cell(0, 6, "INSTALL - ONE CLICK", ln=True)
pdf.set_text_color(*WHT)
pdf.set_font("Courier", "", 8)
pdf.multi_cell(180, 5,
               "git clone https://github.com/1997mujtabaamjad-del/LALA.git && bash install.sh\n"
               "Win:  iwr .../install.ps1 -UseBasicParsing | iex     Mac: curl .../install-mac.sh | bash\n"
               "Single file: LALA-ALL-IN-ONE.html (app + effects + docs)")

pdf.set_xy(15, 266)
pdf.set_text_color(*VI)
pdf.set_font("Helvetica", "B", 10)
pdf.cell(0, 6, "SELF-VERIFIED", ln=True)
pdf.set_font("Helvetica", "", 8.4)
pdf.set_text_color(*OK)
pdf.cell(0, 6, "54/54 functional checks   98 python tests   19 js tests   secrets masked   exec confirm-gated", ln=True)
pdf.set_text_color(*DIM)
pdf.cell(0, 5, "bash scripts/autorun.sh   ·   lala --milestone   ·   lala --bench", ln=True)

pdf.set_xy(15, 285)
pdf.set_text_color(*DIM)
pdf.set_font("Helvetica", "", 8)
pdf.cell(0, 5, "LALA  ·  intellect x enterprise  ·  github.com/1997mujtabaamjad-del/LALA", ln=True)

out = os.path.join(ROOT, "LALA-one-pager.pdf")
pdf.output(out)
print("PDF written:", out, os.path.getsize(out), "bytes")
