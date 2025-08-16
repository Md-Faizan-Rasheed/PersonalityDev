from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import textwrap
import json
import re
from dotenv import load_dotenv 
from pydantic import BaseModel, EmailStr
from typing import Dict, List


# NEW
load_dotenv()                      # 1) load .env



import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import ssl

# Initialize FastAPI app
app = FastAPI()

# Allow CORS for all origins (you can restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# client = OpenAI(
#     base_url=os.getenv("OPENROUTER_BASE_URL"),
#     api_key=os.getenv("OPENAI_API_KEY")    # 2) required key
# )

# # ---------- 4. utility helpers ----------
# SENDER_EMAIL   = os.getenv("SENDER_EMAIL")
# SENDER_PWD     = os.getenv("SENDER_PASSWORD")

client = OpenAI(
    base_url=os.getenv("OPENROUTER_BASE_URL"),
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# # Environment variables
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PWD = os.getenv("SENDER_PASSWORD")


# Request body model
class QAItem(BaseModel):
    id: str
    question: str
    answer: str

class QARequest(BaseModel):
    qa_data: list[QAItem]

# Formatting function (same as your original)
def format_ai_response(text: str) -> str:
    lines = text.split("\n")
    formatted = []

    for line in lines:
        line = line.strip()
        if line.startswith(("1.", "2.", "3.", "-", "•")):
            formatted.append("  " + line)
        elif len(line) > 0 and len(line) < 50 and ":" not in line:
            formatted.append("\n" + line.upper() + "\n")
        else:
            formatted.append(textwrap.fill(line, width=80))
    return "\n".join(formatted)

class AnswerPayload(BaseModel):
    answers: Dict[int, int]  # key=questionId, value=optionIndex (0–3)



QUESTIONS =[
  {
    "id": 1,
    "question": "When you hear about a completely new idea in class, your first instinct is to:",
    "options": [
      "Imagine how it could be applied in different ways (creative spin).",
      "Research the basics before forming an opinion.",
      "Wait to see what others think before commenting.",
      "Avoid it unless it directly relates to your subject."
    ]
  },
  {
    "id": 2,
    "question": "If you have a group assignment due in 5 days, you will:",
    "options": [
      "Break tasks into a checklist and start immediately.",
      "Do small parts daily but without a fixed plan.",
      "Start the day before the deadline.",
      "Wait for group members to take the lead."
    ]
  },
  {
    "id": 3,
    "question": "At a networking event, you usually:",
    "options": [
      "Approach new people confidently and start conversations.",
      "Talk only to those you already know.",
      "Wait for someone to approach you first.",
      "Avoid interactions unless necessary."
    ]
  },
  {
    "id": 4,
    "question": "When a teammate makes a mistake in a project, you:",
    "options": [
      "Explain the mistake politely and help them fix it.",
      "Correct it yourself without mentioning it.",
      "Get frustrated but don’t say anything.",
      "Publicly point it out to avoid repeating errors."
    ]
  },
  {
    "id": 5,
    "question": "During an unexpected problem in your work, you usually:",
    "options": [
      "Stay calm, break the problem into steps, and solve it.",
      "Ask for advice before taking action.",
      "Feel stressed but still try to solve it.",
      "Panic and wait for others to handle it."
    ]
  },
  {
    "id": 6,
    "question": "When talking to someone, you:",
    "options": [
      "Listen carefully without interrupting, then respond.",
      "Listen but start forming your reply midway.",
      "Interrupt if you feel your point is more important.",
      "Mostly wait for your turn to speak."
    ]
  },
  {
    "id": 7,
    "question": "If you are asked to speak on stage in front of 100 students with 5 mins notice, you:",
    "options": [
      "Accept and speak confidently.",
      "Accept but feel nervous inside.",
      "Try to avoid it with an excuse.",
      "Flatly refuse."
    ]
  },
  {
    "id": 8,
    "question": "When meeting someone for the first time, your body language is usually:",
    "options": [
      "Open and friendly (eye contact, smile, relaxed posture).",
      "Neutral but polite.",
      "Reserved and slightly closed off.",
      "Nervous and awkward."
    ]
  },
  {
    "id": 9,
    "question": "In a debate, when someone strongly disagrees with you, you:",
    "options": [
      "Listen calmly and give logical counterpoints.",
      "Defend your point without listening much.",
      "Change the topic to avoid conflict.",
      "Get upset and stop talking."
    ]
  },
  {
    "id": 10,
    "question": "When deciding on an important step in life (e.g., career choice), you:",
    "options": [
      "List pros and cons before deciding.",
      "Discuss with family and friends first.",
      "Go with your gut feeling.",
      "Delay the decision hoping things get clear later."
    ]
  },
  {
    "id": 11,
    "question": "When learning a new skill, you prefer to:",
    "options": [
      "Practice hands-on immediately.",
      "Read/watch tutorials first.",
      "Observe others before trying yourself.",
      "Only learn if it’s necessary for work."
    ]
  },
  {
    "id": 12,
    "question": "If your team’s leader is absent, you:",
    "options": [
      "Step in to guide the team.",
      "Help coordinate tasks without being the leader.",
      "Wait for instructions from someone else.",
      "Focus only on your own work."
    ]
  },
  {
    "id": 13,
    "question": "When you fail at something, you:",
    "options": [
      "Analyze what went wrong and try again.",
      "Seek advice before retrying.",
      "Feel demotivated but continue slowly.",
      "Give up completely."
    ]
  },
  {
    "id": 14,
    "question": "When working in a group, you usually:",
    "options": [
      "Take initiative and delegate tasks.",
      "Do your share and let others lead.",
      "Work silently without much interaction.",
      "Wait for guidance before acting."
    ]
  },
  {
    "id": 15,
    "question": "When facing a challenge, your mindset is:",
    "options": [
      "Every problem has a solution.",
      "I’ll try, but not sure if it will work.",
      "I prefer avoiding risks.",
      "I feel anxious and doubt myself."
    ]
  },
  {
    "id": 16,
    "question": "When given feedback, you:",
    "options": [
      "Accept it positively and improve.",
      "Accept but feel slightly hurt.",
      "Ignore unless it’s from someone you respect.",
      "Defend your actions immediately."
    ]
  },
  {
    "id": 17,
    "question": "When you meet someone with a different opinion, you:",
    "options": [
      "Listen carefully and respect their view.",
      "Listen but stick to your own view.",
      "Try to convince them you are right.",
      "Avoid such conversations."
    ]
  },
  {
    "id": 18,
    "question": "If you’re given two tasks, one easy and one hard, you:",
    "options": [
      "Finish the hard one first.",
      "Finish the easy one first.",
      "Do whichever feels comfortable at the moment.",
      "Delay both until necessary."
    ]
  },
  {
    "id": 19,
    "question": "If a teammate is struggling, you:",
    "options": [
      "Offer help immediately.",
      "Help if they ask.",
      "Focus on your own work.",
      "Avoid getting involved."
    ]
  },
  {
    "id": 20,
    "question": "When learning from mistakes, you:",
    "options": [
      "Keep a record so you don’t repeat them.",
      "Remember mentally and move on.",
      "Forget about them after some time.",
      "Blame external factors."
    ]
  },
  {
    "id": 21,
    "question": "If someone compliments your work, you:",
    "options": [
      "Thank them genuinely.",
      "Feel happy but shy away.",
      "Downplay your effort.",
      "Ignore the compliment."
    ]
  },
  {
    "id": 22,
    "question": "When you have to explain a topic to others, you:",
    "options": [
      "Use examples and clear language.",
      "Give only necessary details.",
      "Speak quickly to finish soon.",
      "Avoid unless forced."
    ]
  },
  {
    "id": 23,
    "question": "If you miss an important deadline, you:",
    "options": [
      "Inform immediately and explain.",
      "Apologize and move on.",
      "Ignore unless asked.",
      "Blame circumstances."
    ]
  },
  {
    "id": 24,
    "question": "When solving a puzzle/problem, you:",
    "options": [
      "Enjoy the challenge.",
      "Feel impatient but try.",
      "Get frustrated easily.",
      "Avoid it completely."
    ]
  },
  {
    "id": 25,
    "question": "If given a choice between working alone or in a team, you:",
    "options": [
      "Prefer a team for better ideas.",
      "Prefer alone for focus.",
      "Depends on the situation.",
      "Avoid team work."
    ]
  },
  {
    "id": 26,
    "question": "When handling criticism, you:",
    "options": [
      "See it as a chance to grow.",
      "Accept but don’t act on it.",
      "Feel offended.",
      "Argue back."
    ]
  },
  {
    "id": 27,
    "question": "If you have free time at work/school, you:",
    "options": [
      "Use it to learn something new.",
      "Help others.",
      "Relax and chat.",
      "Browse aimlessly."
    ]
  },
  {
    "id": 28,
    "question": "When attending a workshop, you:",
    "options": [
      "Participate actively.",
      "Listen but don’t interact much.",
      "Stay quiet unless asked.",
      "Try to leave early."
    ]
  },
  {
    "id": 29,
    "question": "If you don’t understand something, you:",
    "options": [
      "Ask questions immediately.",
      "Research on your own first.",
      "Wait and hope it gets clear later.",
      "Ignore it."
    ]
  },
  {
    "id": 30,
    "question": "When you achieve something, you:",
    "options": [
      "Celebrate and share with others.",
      "Feel happy but keep it to yourself.",
      "Downplay your achievement.",
      "Feel it’s not a big deal."
    ]
  }
]

@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/submit-answers")
def submit_answers(payload: AnswerPayload):
    user_answers = []
    print("Users answers came")

    for q in QUESTIONS:
        qid = q["id"]
        if qid in payload.answers:
            chosen_index = payload.answers[qid]
            chosen_option = q["options"][chosen_index]
            user_answers.append({
                "id": qid,
                "question": q["question"],
                "chosen_option": chosen_option
            })

    print("user question+answer", user_answers)

    # Prepare instructions
    instructions = (
        "You act as a senior-level professional development and training teacher and your target audience in Indian people "
        "Analyze the following questions and answers based on your experience, and respond ONLY in the following JSON format:\n\n"
        "{\n"
        '  "title": "<a short professional title or personality description max three words>",\n'
        '  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],\n'
        '  "careers": ["<career option 1>", "<career option 2>", "<career option 3>"]\n'
        "}\n\n"
        "Base your analysis on:\n"
        "1. Identifying the person’s core personality.\n"
        "2. Determining careers that are suitable for them.\n"
        "3. Listing their key strengths.\n"
        "Do NOT add extra commentary outside of the JSON format."
    )

    # Prepare QA text (fix: use dict keys instead of .id / .question)
    qa_text = "\n".join([
        f"{q['id']}: {q['question']} — {q['chosen_option']}"
        for q in user_answers
    ])

    final_prompt = instructions + "\n" + qa_text
    print("Final prompt:", final_prompt)

    # Get LLM response
    completion = client.chat.completions.create(
        model="meta-llama/llama-3.3-70b-instruct:free",
        messages=[{"role": "user", "content": final_prompt}]
    )

    raw_response = completion.choices[0].message.content
    print("Raw response:", raw_response)

    # Remove markdown fences if present
    clean_response = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        raw_response.strip(),
        flags=re.MULTILINE
    )

    # Parse JSON
    try:
        llm_response = json.loads(clean_response)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON from model: {str(e)}", "raw": clean_response}

    print("Parsed response:", llm_response)

    cert_path = "certificate_like_second.png"
    print("Reciepent name",stored_name)
    create_certificate(
        recipient_name=stored_name,  # dynamic name from frontend
        personality_type=llm_response["title"],
        skills=llm_response["strengths"],
        careers=llm_response["careers"],
        icon_path="icon.png",
        output_file=cert_path
    )

    send_email_with_attachment_debug(
        sender_email=SENDER_EMAIL,
        sender_password=SENDER_PWD,
        receiver_email=stored_email,  # dynamic email from frontend
        subject="Your Personality Analysis Certificate",
        body="Hello, please find attached your personality analysis certificate.",
        file_path=cert_path
    )

    return {"analysis": llm_response, "email_status": "sent"}


# from PIL import Image, ImageDraw, ImageFont
# from datetime import datetime
# import os
# def get_text_size(draw, text, font):
#     """Get text width and height for Pillow ≥10."""
#     bbox = draw.textbbox((0, 0), text, font=font)
#     return bbox[2] - bbox[0], bbox[3] - bbox[1]

# def create_certificate(recipient_name, personality_type, skills, careers, icon_path, output_file="certificate.png"):
    # --- Canvas setup ---
    img_width, img_height = 1150, 650
    background_color = (255, 255, 255)
    text_color = (22, 50, 86)  # Dark blue
    yellow_color = (255, 204, 0)  # Bright yellow
    black_color = (0, 0, 0)

    img = Image.new("RGB", (img_width, img_height), background_color)
    draw = ImageDraw.Draw(img)

    # --- Fonts ---
    font_title = ImageFont.truetype("arialbd.ttf", 30)
    font_name = ImageFont.truetype("arialbd.ttf", 50)
    font_subtitle = ImageFont.truetype("arialbd.ttf", 28)
    font_section = ImageFont.truetype("arialbd.ttf", 20)
    font_text = ImageFont.truetype("arial.ttf", 20)
    font_small = ImageFont.truetype("arialbd.ttf", 18)
    font_big_logo = ImageFont.truetype("arialbd.ttf", 40)  # Large font for "College Skills"

    # --- Outer border ---
    border_margin = 20
    draw.rectangle(
        [border_margin, border_margin, img_width - border_margin, img_height - border_margin],
        outline=text_color, width=2
    )

    # --- "College Skills" text instead of logo ---
    left_x = 100
    logo_y = 60
    draw.text((left_x, logo_y), "College", fill=yellow_color, font=font_big_logo)
    draw.text((left_x, logo_y + 45), "Skills", fill=black_color, font=font_big_logo)

    # --- Right Icon ---
    try:
        icon = Image.open(icon_path).convert("RGBA")
        icon.thumbnail((160, 160))
        icon_y = 60
        icon_x = img_width - 100 - icon.width
        img.paste(icon, (icon_x, icon_y), icon)
    except Exception as e:
        print(f"⚠️ Icon load failed: {e}")

    # --- Title ---
    y_title = 160
    w, h = get_text_size(draw, "CERTIFICATE OF COMPLETION", font_title)
    draw.text(((img_width - w) / 2, y_title), "CERTIFICATE OF COMPLETION", font=font_title, fill=text_color)

    # --- Recipient Name ---
    y_name = y_title + h + 40
    w, h = get_text_size(draw, recipient_name, font_name)
    draw.text(((img_width - w) / 2, y_name), recipient_name, font=font_name, fill=text_color)

    # --- Personality Type ---
    y_type = y_name + h + 20
    w, h = get_text_size(draw, personality_type, font_subtitle)
    draw.text(((img_width - w) / 2, y_type), personality_type, font=font_subtitle, fill=text_color)

    # --- Two Columns ---
    y_section_start = y_type + h + 70
    col_x1 = 200
    col_x2 = 650

    draw.text((col_x1, y_section_start), "POSITIVE SKILLS", fill=text_color, font=font_section)
    draw.text((col_x2, y_section_start), "SUGGESTED CAREER AREAS", fill=text_color, font=font_section)

    for i, skill in enumerate(skills):
        draw.text((col_x1, y_section_start + 30 + (i * 30)), f"• {skill}", fill=black_color, font=font_text)

    for i, career in enumerate(careers):
        draw.text((col_x2, y_section_start + 30 + (i * 30)), f"• {career}", fill=black_color, font=font_text)

    # --- Bottom Date ---
    formatted_date = datetime.now().strftime("%d %B %Y")
    bottom_y = img_height - 70
    draw.text((col_x1, bottom_y), formatted_date, fill=text_color, font=font_small)

    img.save(output_file)
    print(f"✅ Certificate saved as {output_file}")



from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import os

def get_text_size(draw, text, font):
    """Get text width and height for Pillow ≥10."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def load_font(font_name, size):
    """Try to load a font from local 'fonts' dir, else use default."""
    try:
        font_path = os.path.join(os.path.dirname(__file__), "fonts", font_name)
        if os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)
        else:
            # Try system path (Linux)
            system_font_path = f"/usr/share/fonts/truetype/dejavu/{font_name}"
            if os.path.exists(system_font_path):
                return ImageFont.truetype(system_font_path, size)
            else:
                print(f"⚠️ Font '{font_name}' not found, using default font.")
                return ImageFont.load_default()
    except Exception as e:
        print(f"⚠️ Font load error ({font_name}): {e}")
        return ImageFont.load_default()

def create_certificate(recipient_name, personality_type, skills, careers, icon_path, output_file="certificate.png"):
    # --- Canvas setup ---
    img_width, img_height = 1150, 650
    background_color = (255, 255, 255)
    text_color = (22, 50, 86)  # Dark blue
    yellow_color = (255, 204, 0)  # Bright yellow
    black_color = (0, 0, 0)

    img = Image.new("RGB", (img_width, img_height), background_color)
    draw = ImageDraw.Draw(img)

    # --- Fonts ---
    font_title = load_font("DejaVuSans-Bold.ttf", 30)   # replaces arialbd.ttf
    font_name = load_font("DejaVuSans-Bold.ttf", 50)
    font_subtitle = load_font("DejaVuSans-Bold.ttf", 28)
    font_section = load_font("DejaVuSans-Bold.ttf", 20)
    font_text = load_font("DejaVuSans.ttf", 20)         # replaces arial.ttf
    font_small = load_font("DejaVuSans-Bold.ttf", 18)
    font_big_logo = load_font("DejaVuSans-Bold.ttf", 40)

    # --- Outer border ---
    border_margin = 20
    draw.rectangle(
        [border_margin, border_margin, img_width - border_margin, img_height - border_margin],
        outline=text_color, width=2
    )

    # --- "College Skills" text instead of logo ---
    left_x = 100
    logo_y = 60
    draw.text((left_x, logo_y), "College", fill=yellow_color, font=font_big_logo)
    draw.text((left_x, logo_y + 45), "Skills", fill=black_color, font=font_big_logo)

    # --- Right Icon ---
    try:
        icon = Image.open(icon_path).convert("RGBA")
        icon.thumbnail((160, 160))
        icon_y = 60
        icon_x = img_width - 100 - icon.width
        img.paste(icon, (icon_x, icon_y), icon)
    except Exception as e:
        print(f"⚠️ Icon load failed: {e}")

    # --- Title ---
    y_title = 160
    w, h = get_text_size(draw, "CERTIFICATE OF COMPLETION", font_title)
    draw.text(((img_width - w) / 2, y_title), "CERTIFICATE OF COMPLETION", font=font_title, fill=text_color)

    # --- Recipient Name ---
    y_name = y_title + h + 40
    w, h = get_text_size(draw, recipient_name, font_name)
    draw.text(((img_width - w) / 2, y_name), recipient_name, font=font_name, fill=text_color)

    # --- Personality Type ---
    y_type = y_name + h + 20
    w, h = get_text_size(draw, personality_type, font_subtitle)
    draw.text(((img_width - w) / 2, y_type), personality_type, font=font_subtitle, fill=text_color)

    # --- Two Columns ---
    y_section_start = y_type + h + 70
    col_x1 = 200
    col_x2 = 650

    draw.text((col_x1, y_section_start), "POSITIVE SKILLS", fill=text_color, font=font_section)
    draw.text((col_x2, y_section_start), "SUGGESTED CAREER AREAS", fill=text_color, font=font_section)

    for i, skill in enumerate(skills):
        draw.text((col_x1, y_section_start + 30 + (i * 30)), f"• {skill}", fill=black_color, font=font_text)

    for i, career in enumerate(careers):
        draw.text((col_x2, y_section_start + 30 + (i * 30)), f"• {career}", fill=black_color, font=font_text)

    # --- Bottom Date ---
    formatted_date = datetime.now().strftime("%d %B %Y")
    bottom_y = img_height - 70
    draw.text((col_x1, bottom_y), formatted_date, fill=text_color, font=font_small)

    img.save(output_file)
    print(f"✅ Certificate saved as {output_file}")



def send_email_with_attachment_debug(sender_email, sender_password, receiver_email, subject, body, file_path):
    try:
        print(f"🔍 DEBUG: Attempting to send email from {sender_email}")
        print(f"🔍 DEBUG: Password length: {len(sender_password)} characters")
        print(f"🔍 DEBUG: Using app password format: {'Yes' if len(sender_password) == 16 and sender_password.replace(' ', '').isalnum() else 'No - might be regular password'}")
        
        # Setup email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Attach the file if provided
        if file_path and os.path.exists(file_path):
            with open(file_path, 'rb') as attachment:
                mime = MIMEBase('application', 'octet-stream')
                mime.set_payload(attachment.read())
                encoders.encode_base64(mime)
                mime.add_header('Content-Disposition', f'attachment; filename={os.path.basename(file_path)}')
                msg.attach(mime)
            print(f"✅ File attached: {os.path.basename(file_path)}")
        elif file_path:
            print(f"⚠️ WARNING: File not found: {file_path}")

        print("🔗 Connecting to Gmail SMTP server...")
        
        # Method 1: Try with explicit SSL context (recommended)
        context = ssl.create_default_context()
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        
        print("🔐 Attempting login...")
        server.login(sender_email, sender_password)
        
        print("📤 Sending email...")
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()

        print("✅ Email sent successfully!")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Authentication Error: {e}")
        print("💡 Try these solutions:")
        print("   1. Generate a NEW App Password (old ones might expire)")
        print("   2. Ensure 2FA is enabled on your Google account")
        print("   3. Use the app password WITHOUT spaces")
        print("   4. Try signing out and back into your Google account")
        return False
        
    except smtplib.SMTPException as e:
        print(f"❌ SMTP Error: {e}")
        return False
        
    except Exception as e:
        print(f"❌ General Error: {e}")
        return False

def send_email_alternative_method(sender_email, sender_password, receiver_email, subject, body, file_path):
    """Alternative method using SSL on port 465"""
    try:
        print("🔄 Trying alternative method (SSL on port 465)...")
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        if file_path and os.path.exists(file_path):
            with open(file_path, 'rb') as attachment:
                mime = MIMEBase('application', 'octet-stream')
                mime.set_payload(attachment.read())
                encoders.encode_base64(mime)
                mime.add_header('Content-Disposition', f'attachment; filename={os.path.basename(file_path)}')
                msg.attach(mime)

        # Use SSL directly
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
            
        print("✅ Email sent successfully with alternative method!")
        return True
        
    except Exception as e:
        print(f"❌ Alternative method failed: {e}")
        return False

def test_email_setup(sender_email, sender_password):
    """Test basic SMTP connection and authentication"""
    try:
        print("🧪 Testing SMTP connection...")
        context = ssl.create_default_context()
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(sender_email, sender_password)
        server.quit()
        print("✅ SMTP connection and authentication successful!")
        return True
    except Exception as e:
        print(f"❌ SMTP test failed: {e}")
        return False

# Usage example with debugging
if __name__ == "__main__":
    # Replace with your details
    SENDER_EMAIL = "your-email@gmail.com"
    SENDER_PASSWORD = "your-app-password"  # 16-character app password
    RECEIVER_EMAIL = "receiver@example.com"
    
    # First, test the connection
    if test_email_setup(SENDER_EMAIL, SENDER_PASSWORD):
        # If test passes, try sending email
        success = send_email_with_attachment_debug(
            sender_email=SENDER_EMAIL,
            sender_password=SENDER_PASSWORD,
            receiver_email=stored_email,
            subject="Test Email",
            body="This is a test email.",
            file_path="path/to/your/file.pdf"  # or None if no attachment
        )
        
        # If first method fails, try alternative
        if not success:
            send_email_alternative_method(
                sender_email=SENDER_EMAIL,
                sender_password=SENDER_PASSWORD,
                receiver_email=RECEIVER_EMAIL,
                subject="Test Email",
                body="This is a test email.",
                file_path="path/to/your/file.pdf"
            )
    else:
        print("❌ Basic SMTP test failed. Check your credentials and try the steps below.")



 # Variables to store form data


stored_name = None
stored_email = None    

# Pydantic model for validation
class FormData(BaseModel):
    name: str
    phone: str
    email: EmailStr
    password: str   


@app.post("/submit-form")
async def submit_form(data: FormData):
    global stored_name, stored_email
    stored_name = data.name
    stored_email = data.email
    
    print("Form data received:", data.dict())
    print(f"Stored name: {stored_name}, Stored email: {stored_email}")
    
    return {"message": "Form submitted successfully!"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

# from fastapi import FastAPI, Request
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from openai import OpenAI
# import textwrap
# import json
# import re
# from dotenv import load_dotenv 
# from pydantic import BaseModel, EmailStr
# from typing import Dict, List
# import smtplib
# import os
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# from email.mime.base import MIMEBase
# from email import encoders
# import ssl
# from PIL import Image, ImageDraw, ImageFont
# from datetime import datetime

# # Load environment variables
# load_dotenv()

# # Initialize FastAPI app
# app = FastAPI()

# # Allow CORS for all origins (you can restrict in production)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# client = OpenAI(
#     base_url=os.getenv("OPENROUTER_BASE_URL"),
#     api_key=os.getenv("OPENAI_API_KEY")
# )

# # Environment variables
# SENDER_EMAIL = os.getenv("SENDER_EMAIL")
# SENDER_PWD = os.getenv("SENDER_PASSWORD")

# # Variables to store form data
# stored_name = None
# stored_email = None    

# # Pydantic models
# class QAItem(BaseModel):
#     id: str
#     question: str
#     answer: str

# class QARequest(BaseModel):
#     qa_data: list[QAItem]

# class AnswerPayload(BaseModel):
#     answers: Dict[int, int]  # key=questionId, value=optionIndex (0–3)

# class FormData(BaseModel):
#     name: str
#     phone: str
#     email: EmailStr
#     password: str   

# # Add root endpoint
# @app.get("/")
# def read_root():
#     return {"message": "Personality Development API is running!"}

# # Health check endpoint
# @app.get("/health")
# def health_check():
#     return {"status": "healthy"}

# def format_ai_response(text: str) -> str:
#     lines = text.split("\n")
#     formatted = []

#     for line in lines:
#         line = line.strip()
#         if line.startswith(("1.", "2.", "3.", "-", "•")):
#             formatted.append("  " + line)
#         elif len(line) > 0 and len(line) < 50 and ":" not in line:
#             formatted.append("\n" + line.upper() + "\n")
#         else:
#             formatted.append(textwrap.fill(line, width=80))
#     return "\n".join(formatted)

# QUESTIONS = [
#   {
#     "id": 1,
#     "question": "When you hear about a completely new idea in class, your first instinct is to:",
#     "options": [
#       "Imagine how it could be applied in different ways (creative spin).",
#       "Research the basics before forming an opinion.",
#       "Wait to see what others think before commenting.",
#       "Avoid it unless it directly relates to your subject."
#     ]
#   },
#   {
#     "id": 2,
#     "question": "If you have a group assignment due in 5 days, you will:",
#     "options": [
#       "Break tasks into a checklist and start immediately.",
#       "Do small parts daily but without a fixed plan.",
#       "Start the day before the deadline.",
#       "Wait for group members to take the lead."
#     ]
#   },
#   {
#     "id": 3,
#     "question": "At a networking event, you usually:",
#     "options": [
#       "Approach new people confidently and start conversations.",
#       "Talk only to those you already know.",
#       "Wait for someone to approach you first.",
#       "Avoid interactions unless necessary."
#     ]
#   },
#   {
#     "id": 4,
#     "question": "When a teammate makes a mistake in a project, you:",
#     "options": [
#       "Explain the mistake politely and help them fix it.",
#       "Correct it yourself without mentioning it.",
#       "Get frustrated but don't say anything.",
#       "Publicly point it out to avoid repeating errors."
#     ]
#   },
#   {
#     "id": 5,
#     "question": "During an unexpected problem in your work, you usually:",
#     "options": [
#       "Stay calm, break the problem into steps, and solve it.",
#       "Ask for advice before taking action.",
#       "Feel stressed but still try to solve it.",
#       "Panic and wait for others to handle it."
#     ]
#   },
#   {
#     "id": 6,
#     "question": "When talking to someone, you:",
#     "options": [
#       "Listen carefully without interrupting, then respond.",
#       "Listen but start forming your reply midway.",
#       "Interrupt if you feel your point is more important.",
#       "Mostly wait for your turn to speak."
#     ]
#   },
#   {
#     "id": 7,
#     "question": "If you are asked to speak on stage in front of 100 students with 5 mins notice, you:",
#     "options": [
#       "Accept and speak confidently.",
#       "Accept but feel nervous inside.",
#       "Try to avoid it with an excuse.",
#       "Flatly refuse."
#     ]
#   },
#   {
#     "id": 8,
#     "question": "When meeting someone for the first time, your body language is usually:",
#     "options": [
#       "Open and friendly (eye contact, smile, relaxed posture).",
#       "Neutral but polite.",
#       "Reserved and slightly closed off.",
#       "Nervous and awkward."
#     ]
#   },
#   {
#     "id": 9,
#     "question": "In a debate, when someone strongly disagrees with you, you:",
#     "options": [
#       "Listen calmly and give logical counterpoints.",
#       "Defend your point without listening much.",
#       "Change the topic to avoid conflict.",
#       "Get upset and stop talking."
#     ]
#   },
#   {
#     "id": 10,
#     "question": "When deciding on an important step in life (e.g., career choice), you:",
#     "options": [
#       "List pros and cons before deciding.",
#       "Discuss with family and friends first.",
#       "Go with your gut feeling.",
#       "Delay the decision hoping things get clear later."
#     ]
#   },
#   {
#     "id": 11,
#     "question": "When learning a new skill, you prefer to:",
#     "options": [
#       "Practice hands-on immediately.",
#       "Read/watch tutorials first.",
#       "Observe others before trying yourself.",
#       "Only learn if it's necessary for work."
#     ]
#   },
#   {
#     "id": 12,
#     "question": "If your team's leader is absent, you:",
#     "options": [
#       "Step in to guide the team.",
#       "Help coordinate tasks without being the leader.",
#       "Wait for instructions from someone else.",
#       "Focus only on your own work."
#     ]
#   },
#   {
#     "id": 13,
#     "question": "When you fail at something, you:",
#     "options": [
#       "Analyze what went wrong and try again.",
#       "Seek advice before retrying.",
#       "Feel demotivated but continue slowly.",
#       "Give up completely."
#     ]
#   },
#   {
#     "id": 14,
#     "question": "When working in a group, you usually:",
#     "options": [
#       "Take initiative and delegate tasks.",
#       "Do your share and let others lead.",
#       "Work silently without much interaction.",
#       "Wait for guidance before acting."
#     ]
#   },
#   {
#     "id": 15,
#     "question": "When facing a challenge, your mindset is:",
#     "options": [
#       "Every problem has a solution.",
#       "I'll try, but not sure if it will work.",
#       "I prefer avoiding risks.",
#       "I feel anxious and doubt myself."
#     ]
#   },
#   {
#     "id": 16,
#     "question": "When given feedback, you:",
#     "options": [
#       "Accept it positively and improve.",
#       "Accept but feel slightly hurt.",
#       "Ignore unless it's from someone you respect.",
#       "Defend your actions immediately."
#     ]
#   },
#   {
#     "id": 17,
#     "question": "When you meet someone with a different opinion, you:",
#     "options": [
#       "Listen carefully and respect their view.",
#       "Listen but stick to your own view.",
#       "Try to convince them you are right.",
#       "Avoid such conversations."
#     ]
#   },
#   {
#     "id": 18,
#     "question": "If you're given two tasks, one easy and one hard, you:",
#     "options": [
#       "Finish the hard one first.",
#       "Finish the easy one first.",
#       "Do whichever feels comfortable at the moment.",
#       "Delay both until necessary."
#     ]
#   },
#   {
#     "id": 19,
#     "question": "If a teammate is struggling, you:",
#     "options": [
#       "Offer help immediately.",
#       "Help if they ask.",
#       "Focus on your own work.",
#       "Avoid getting involved."
#     ]
#   },
#   {
#     "id": 20,
#     "question": "When learning from mistakes, you:",
#     "options": [
#       "Keep a record so you don't repeat them.",
#       "Remember mentally and move on.",
#       "Forget about them after some time.",
#       "Blame external factors."
#     ]
#   },
#   {
#     "id": 21,
#     "question": "If someone compliments your work, you:",
#     "options": [
#       "Thank them genuinely.",
#       "Feel happy but shy away.",
#       "Downplay your effort.",
#       "Ignore the compliment."
#     ]
#   },
#   {
#     "id": 22,
#     "question": "When you have to explain a topic to others, you:",
#     "options": [
#       "Use examples and clear language.",
#       "Give only necessary details.",
#       "Speak quickly to finish soon.",
#       "Avoid unless forced."
#     ]
#   },
#   {
#     "id": 23,
#     "question": "If you miss an important deadline, you:",
#     "options": [
#       "Inform immediately and explain.",
#       "Apologize and move on.",
#       "Ignore unless asked.",
#       "Blame circumstances."
#     ]
#   },
#   {
#     "id": 24,
#     "question": "When solving a puzzle/problem, you:",
#     "options": [
#       "Enjoy the challenge.",
#       "Feel impatient but try.",
#       "Get frustrated easily.",
#       "Avoid it completely."
#     ]
#   },
#   {
#     "id": 25,
#     "question": "If given a choice between working alone or in a team, you:",
#     "options": [
#       "Prefer a team for better ideas.",
#       "Prefer alone for focus.",
#       "Depends on the situation.",
#       "Avoid team work."
#     ]
#   },
#   {
#     "id": 26,
#     "question": "When handling criticism, you:",
#     "options": [
#       "See it as a chance to grow.",
#       "Accept but don't act on it.",
#       "Feel offended.",
#       "Argue back."
#     ]
#   },
#   {
#     "id": 27,
#     "question": "If you have free time at work/school, you:",
#     "options": [
#       "Use it to learn something new.",
#       "Help others.",
#       "Relax and chat.",
#       "Browse aimlessly."
#     ]
#   },
#   {
#     "id": 28,
#     "question": "When attending a workshop, you:",
#     "options": [
#       "Participate actively.",
#       "Listen but don't interact much.",
#       "Stay quiet unless asked.",
#       "Try to leave early."
#     ]
#   },
#   {
#     "id": 29,
#     "question": "If you don't understand something, you:",
#     "options": [
#       "Ask questions immediately.",
#       "Research on your own first.",
#       "Wait and hope it gets clear later.",
#       "Ignore it."
#     ]
#   },
#   {
#     "id": 30,
#     "question": "When you achieve something, you:",
#     "options": [
#       "Celebrate and share with others.",
#       "Feel happy but keep it to yourself.",
#       "Downplay your achievement.",
#       "Feel it's not a big deal."
#     ]
#   }
# ]

# def get_text_size(draw, text, font):
#     """Get text width and height for Pillow ≥10."""
#     bbox = draw.textbbox((0, 0), text, font=font)
#     return bbox[2] - bbox[0], bbox[3] - bbox[1]

# def get_default_font(size):
#     """Get a default font that works on most systems."""
#     try:
#         # Try common font names
#         font_names = ["DejaVuSans.ttf", "arial.ttf", "Arial.ttf", "Liberation Sans"]
#         for font_name in font_names:
#             try:
#                 return ImageFont.truetype(font_name, size)
#             except:
#                 continue
#         # If no truetype font works, use default
#         return ImageFont.load_default()
#     except:
#         return ImageFont.load_default()

# def create_certificate(recipient_name, personality_type, skills, careers, icon_path=None, output_file="certificate.png"):
#     # Canvas setup
#     img_width, img_height = 1150, 650
#     background_color = (255, 255, 255)
#     text_color = (22, 50, 86)  # Dark blue
#     yellow_color = (255, 204, 0)  # Bright yellow
#     black_color = (0, 0, 0)

#     img = Image.new("RGB", (img_width, img_height), background_color)
#     draw = ImageDraw.Draw(img)

#     # Fonts - use fallback system
#     font_title = get_default_font(30)
#     font_name = get_default_font(50)
#     font_subtitle = get_default_font(28)
#     font_section = get_default_font(20)
#     font_text = get_default_font(18)
#     font_small = get_default_font(16)
#     font_big_logo = get_default_font(40)

#     # Outer border
#     border_margin = 20
#     draw.rectangle(
#         [border_margin, border_margin, img_width - border_margin, img_height - border_margin],
#         outline=text_color, width=2
#     )

#     # "College Skills" text instead of logo
#     left_x = 100
#     logo_y = 60
#     draw.text((left_x, logo_y), "College", fill=yellow_color, font=font_big_logo)
#     draw.text((left_x, logo_y + 45), "Skills", fill=black_color, font=font_big_logo)

#     # Right Icon (optional)
#     if icon_path and os.path.exists(icon_path):
#         try:
#             icon = Image.open(icon_path).convert("RGBA")
#             icon.thumbnail((160, 160))
#             icon_y = 60
#             icon_x = img_width - 100 - icon.width
#             img.paste(icon, (icon_x, icon_y), icon)
#         except Exception as e:
#             print(f"⚠️ Icon load failed: {e}")

#     # Title
#     y_title = 160
#     w, h = get_text_size(draw, "CERTIFICATE OF COMPLETION", font_title)
#     draw.text(((img_width - w) / 2, y_title), "CERTIFICATE OF COMPLETION", font=font_title, fill=text_color)

#     # Recipient Name
#     y_name = y_title + h + 40
#     w, h = get_text_size(draw, recipient_name, font_name)
#     draw.text(((img_width - w) / 2, y_name), recipient_name, font=font_name, fill=text_color)

#     # Personality Type
#     y_type = y_name + h + 20
#     w, h = get_text_size(draw, personality_type, font_subtitle)
#     draw.text(((img_width - w) / 2, y_type), personality_type, font=font_subtitle, fill=text_color)

#     # Two Columns
#     y_section_start = y_type + h + 70
#     col_x1 = 200
#     col_x2 = 650

#     draw.text((col_x1, y_section_start), "POSITIVE SKILLS", fill=text_color, font=font_section)
#     draw.text((col_x2, y_section_start), "SUGGESTED CAREER AREAS", fill=text_color, font=font_section)

#     for i, skill in enumerate(skills):
#         draw.text((col_x1, y_section_start + 30 + (i * 30)), f"• {skill}", fill=black_color, font=font_text)

#     for i, career in enumerate(careers):
#         draw.text((col_x2, y_section_start + 30 + (i * 30)), f"• {career}", fill=black_color, font=font_text)

#     # Bottom Date
#     formatted_date = datetime.now().strftime("%d %B %Y")
#     bottom_y = img_height - 70
#     draw.text((col_x1, bottom_y), formatted_date, fill=text_color, font=font_small)

#     img.save(output_file)
#     print(f"✅ Certificate saved as {output_file}")

# def send_email_with_attachment_debug(sender_email, sender_password, receiver_email, subject, body, file_path):
#     try:
#         print(f"🔍 DEBUG: Attempting to send email from {sender_email}")
        
#         # Setup email
#         msg = MIMEMultipart()
#         msg['From'] = sender_email
#         msg['To'] = receiver_email
#         msg['Subject'] = subject
#         msg.attach(MIMEText(body, 'plain'))

#         # Attach the file if provided
#         if file_path and os.path.exists(file_path):
#             with open(file_path, 'rb') as attachment:
#                 mime = MIMEBase('application', 'octet-stream')
#                 mime.set_payload(attachment.read())
#                 encoders.encode_base64(mime)
#                 mime.add_header('Content-Disposition', f'attachment; filename={os.path.basename(file_path)}')
#                 msg.attach(mime)
#             print(f"✅ File attached: {os.path.basename(file_path)}")
#         elif file_path:
#             print(f"⚠️ WARNING: File not found: {file_path}")

#         print("🔗 Connecting to Gmail SMTP server...")
        
#         # Try with explicit SSL context
#         context = ssl.create_default_context()
#         server = smtplib.SMTP('smtp.gmail.com', 587)
#         server.ehlo()
#         server.starttls(context=context)
#         server.ehlo()
        
#         print("🔐 Attempting login...")
#         server.login(sender_email, sender_password)
        
#         print("📤 Sending email...")
#         text = msg.as_string()
#         server.sendmail(sender_email, receiver_email, text)
#         server.quit()

#         print("✅ Email sent successfully!")
#         return True
        
#     except Exception as e:
#         print(f"❌ Email Error: {e}")
#         return False

# @app.post("/submit-form")
# async def submit_form(data: FormData):
#     global stored_name, stored_email
#     stored_name = data.name
#     stored_email = data.email
    
#     print("Form data received:", data.dict())
#     print(f"Stored name: {stored_name}, Stored email: {stored_email}")
    
#     return {"message": "Form submitted successfully!"}

# @app.post("/submit-answers")
# def submit_answers(payload: AnswerPayload):
#     user_answers = []
#     print("Users answers came")

#     for q in QUESTIONS:
#         qid = q["id"]
#         if qid in payload.answers:
#             chosen_index = payload.answers[qid]
#             chosen_option = q["options"][chosen_index]
#             user_answers.append({
#                 "id": qid,
#                 "question": q["question"],
#                 "chosen_option": chosen_option
#             })

#     print("user question+answer", user_answers)

#     # Prepare instructions
#     instructions = (
#         "You act as a senior-level professional development and training teacher and your target audience in Indian people "
#         "Analyze the following questions and answers based on your experience, and respond ONLY in the following JSON format:\n\n"
#         "{\n"
#         '  "title": "<a short professional title or personality description max three words>",\n'
#         '  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],\n'
#         '  "careers": ["<career option 1>", "<career option 2>", "<career option 3>"]\n'
#         "}\n\n"
#         "Base your analysis on:\n"
#         "1. Identifying the person's core personality.\n"
#         "2. Determining careers that are suitable for them.\n"
#         "3. Listing their key strengths.\n"
#         "Do NOT add extra commentary outside of the JSON format."
#     )

#     # Prepare QA text
#     qa_text = "\n".join([
#         f"{q['id']}: {q['question']} — {q['chosen_option']}"
#         for q in user_answers
#     ])

#     final_prompt = instructions + "\n" + qa_text
#     print("Final prompt:", final_prompt)

#     # Get LLM response
#     try:
#         completion = client.chat.completions.create(
#             model="meta-llama/llama-3.3-70b-instruct:free",
#             messages=[{"role": "user", "content": final_prompt}]
#         )

#         raw_response = completion.choices[0].message.content
#         print("Raw response:", raw_response)

#         # Remove markdown fences if present
#         clean_response = re.sub(
#             r"^```(?:json)?\s*|\s*```$",
#             "",
#             raw_response.strip(),
#             flags=re.MULTILINE
#         )

#         # Parse JSON
#         llm_response = json.loads(clean_response)
#         print("Parsed response:", llm_response)

#         # Create certificate
#         cert_path = "certificate_like_second.png"
#         print("Recipient name:", stored_name)
        
#         create_certificate(
#             recipient_name=stored_name or "Student",
#             personality_type=llm_response["title"],
#             skills=llm_response["strengths"],
#             careers=llm_response["careers"],
#             output_file=cert_path
#         )

#         # Send email
#         email_status = "not_sent"
#         if SENDER_EMAIL and SENDER_PWD and stored_email:
#             success = send_email_with_attachment_debug(
#                 sender_email=SENDER_EMAIL,
#                 sender_password=SENDER_PWD,
#                 receiver_email=stored_email,
#                 subject="Your Personality Analysis Certificate",
#                 body="Hello, please find attached your personality analysis certificate.",
#                 file_path=cert_path
#             )
#             email_status = "sent" if success else "failed"

#         return {"analysis": llm_response, "email_status": email_status}

#     except json.JSONDecodeError as e:
#         return {"error": f"Invalid JSON from model: {str(e)}", "raw": clean_response}
#     except Exception as e:
#         return {"error": f"Processing error: {str(e)}"}

# # For local development and Render deployment
# if __name__ == "__main__":
#     import uvicorn
#     port = int(os.environ.get("PORT", 8000))
#     uvicorn.run("main:app", host="0.0.0.0", port=port)