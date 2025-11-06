import os
import json
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
from ics import Calendar, Event
from ics.alarm import DisplayAlarm

# Here we will try to import google genai client, and if it is not available, then it will fallback to requests...
try:
    from google import genai
    GENAI_AVAILABLE = True
except Exception:
    GENAI_AVAILABLE = False

MODEL_NAME = "gemini-2.5-flash"

# Utility: call Gemini (Google GenAI SDK)
# Utility: call Gemini (Google GenAI SDK)
def call_gemini(prompt: str, max_output_tokens: int = 512) -> str:
    
    # 1. Get the API key from Streamlit's secrets
    api_key = st.secrets.get("GEMINI_API_KEY")

    if not api_key:
        return "[No Gemini API key found. Add it in .streamlit/secrets.toml as GEMINI_API_KEY.]"

    # If google-genai SDK is available
    if GENAI_AVAILABLE:
        try:
            # --- THIS IS THE NEW, CORRECT WAY ---
            # 2. Initialize the client with the API key
            client = genai.Client(api_key=api_key)
            
            # 3. Generate content using the client
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                generation_config={"max_output_tokens": max_output_tokens}
            )

            # Extract text safely
            if hasattr(response, "text"):
                return response.text
            return str(response)

        except Exception as e:
            # This will now show any new errors
            return f"[Gemini call failed: {e}]"

    # Fallback REST call (This part was fine)
    else:
        try:
            import requests

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"
            headers = {"Content-Type": "application/json"}
            params = {"key": api_key} # This will now have the correct key
            body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_output_tokens}
            }

            r = requests.post(url, headers=headers, params=params, json=body, timeout=30)

            if r.status_code == 200:
                data = r.json()
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except:
                    return json.dumps(data, indent=2)

            return f"[REST Gemini call failed: {r.status_code} - {r.text}]"

        except Exception as e:
            return f"[REST fallback also failed: {e}]"
# Note summarization
def summarize_text(text: str, style: str = "concise") -> str: # Added style parameter
    """SummarizeS given text into exam-friendly bullets points and adds memory tips.
    """
    HELLO_WORDS = ["hello","hi","hii","hiii","hiiii","helo","heloo","helloo","hey","heyy","heyyy","hya","hiya",
                   "yo","sup","whatsup","what's up","wassup","wassup?","hey there","hola","namaste",
                   "hlo","hloo","hlw","hlwo","hai","haii","haiii","greetings","good morning",
                   "good afternoon","good evening"
    ]
    user_text = text.strip().lower()
    
    if user_text in HELLO_WORDS:
        response = call_gemini("Hey! How can I help you today?")
        return response
    if style == "elaborate":
        style_prompt = "Explain this like I'm 5 years old. Use simple words and analogies."
    else:
        style_prompt = "Summarize this for a last-minute exam revision. Be concise."
        
    prompt = (
        f"You are an expert study coach. {style_prompt}\n\n"
        "Format the output using clean Markdown. "
        "DO NOT add weird characters, slashes, backslashes, escape symbols, or extra stars (*). "
        "Write smooth, readable bullet points. "
        "Output sections exactly as:\n\n"
        "SUMMARY\n\n"
        "---> bullet points here\n\n"
        "TIPS\n\n"
        "---> tips here\n\n"
        f"Notes:\n{text}"
    )
    response = call_gemini(prompt)
    return response

# Timetable parsing -> ICS generation
def parse_timetable_csv(file_buffer) -> pd.DataFrame:
    """Expect CSV with columns: Day, Start, End, Subject, Location (optional), Notes (optional)

    Times may be like '09:00' or '2:30PM'.
    """
    df = pd.read_csv(file_buffer)
    # Normalise column names
    df.columns = [c.strip().lower() for c in df.columns]
    required = ["day", "start", "end", "subject"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col} (example CSV header: Day, Start, End, Subject, Location)")
    return df


def create_calendar_from_df(df: pd.DataFrame, start_week_date: datetime, alarm_minutes: int = 30) -> bytes:
    """Create an .ics calendar bytes object with weekly recurring events for 1 week starting start_week_date.
    """
    cal = Calendar()
    weekday_map = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }

    for _, row in df.iterrows():
        day = str(row['day']).strip().lower()
        if day not in weekday_map:
            continue
        monday = start_week_date - timedelta(days=start_week_date.weekday())
        event_date = monday + timedelta(days=weekday_map[day])

        # parsingg start or end times
        try:
            start_time = pd.to_datetime(str(row['start'])).time()
            end_time = pd.to_datetime(str(row['end'])).time()
        except Exception:
            # fallback: assume start is hour only
            start_time = datetime.strptime(str(row['start']), "%H:%M").time()
            end_time = datetime.strptime(str(row['end']), "%H:%M").time()

        dt_start = datetime.combine(event_date.date(), start_time)
        dt_end = datetime.combine(event_date.date(), end_time)

        ev = Event()
        ev.name = str(row['subject'])
        loc = row.get('location') if 'location' in row else None
        if pd.notna(loc):
            ev.location = str(loc)
        notes = row.get('notes') if 'notes' in row else None
        if pd.notna(notes):
            ev.description = str(notes)
        ev.begin = dt_start
        ev.end = dt_end

        # Add alarm
        trigger = timedelta(minutes=-alarm_minutes)
        alarm = DisplayAlarm(
            trigger=trigger,
            display_text=f"Reminder: {ev.name}"
        )
        ev.alarms.append(alarm)
        cal.events.add(ev)

    return cal.serialize().encode('utf-8')

# Roadmap generation
def generate_roadmap(goal: str, timeframe_weeks: int = 12, background: str = "") -> str:
    prompt = (
        f"You are an expert study/career mentor. Create a clean, distraction-free {timeframe_weeks}-week roadmap for a student whose main goal is: {goal}."
        "Include: weekly milestones, daily time budgets, 8-12 curated learning resources (with short notes why each), and final deliverables to show on a resume."
        f"\nStudent background: {background}\nOutput: Use numbered weeks and bullet points; be concise.\nDon't use any weird slashes(\, or /), asterrisks(*) is unneccessary\n and provide concise and short easy to understand with bullet points way"
    )
    return call_gemini(prompt, max_output_tokens=800)



# Streamlit UI

st.set_page_config(page_title="SmartGrind — AI Study Assistant", layout="wide")

st.markdown("# Smart Grind App 📖📗")
st.write("""An AI-powered study assistant — quick summaries, calendar-ready timetables, and focus roadmaps.
""")

col1, col2 = st.columns([1, 1])

with col1:
    st.header("Notes -> Summary (Fast Revision)")
    notes_input_type = st.radio("Input type", ["Paste text", "Upload PDF/TXT"])

    raw_text = ""
    if notes_input_type == "Paste text":
        raw_text = st.text_area("Paste your notes or lecture text here", height=200,width=800)
    else:
        uploaded = st.file_uploader("Upload PDF or TXT file", type=["pdf", "txt"])
        if uploaded is not None:
            if uploaded.type == "application/pdf":
                try:
                    from PyPDF2 import PdfReader
                    reader = PdfReader(uploaded)
                    pages = [p.extract_text() or "" for p in reader.pages]
                    raw_text = "\n".join(pages)
                except Exception as e:
                    st.warning("PDF parsing failed - please paste text instead. Error: %s" % e)
            else:
                raw_text = uploaded.getvalue().decode('utf-8')

    col_summ, col_run = st.columns([3,1])
    style = col_summ.selectbox("Summary style", ["Concise for last-minute revision", "Explain like I'm 5 years kid."])
    run_summary = col_run.button("Generate Summary")

    if run_summary:
        if not raw_text or raw_text.strip() == "":
            st.error("Please paste your notes or upload a file first.")
        else:
            with st.spinner("Generating summary with Gemini..."):
                prompt_style = "concise" if "Concise" in style else "elaborate"
                summary = summarize_text(raw_text, style=prompt_style)
                st.success("Done — review and edit if needed")
                st.markdown("### Summary ")
                st.text_area("Summary output", value=summary, height=300, key="summary_out")
                st.markdown("### Quick Tips (copy to phone)")
                # extract TIPS section if present
                if "TIPS" in summary:
                    tips = summary.split("TIPS")[-1]
                    st.write(tips)

with col2:
    st.header("Timetable -> Calendar")
    st.write("Upload a CSV timetable with columns: Day, Start, End, Subject, Location(optional), Notes(optional)")
    tt_file = st.file_uploader("Upload timetable in CSV format only", type=["csv"], key="tt")
    start_week = st.date_input("Week starting (any date in desired week)", value=datetime.now().date())
    alarm_mins = st.number_input("Alarm before class (minutes)", min_value=0, max_value=1440, value=30)
    if st.button("Generate Calendar"):
        if not tt_file:
            st.error("Please upload a CSV timetable first.")
        else:
            try:
                df = parse_timetable_csv(tt_file)
                ics_bytes = create_calendar_from_df(df, datetime.combine(start_week, datetime.min.time()), alarm_minutes=alarm_mins)
                st.success("Calendar generated — download and import into Google Calendar or any calendar app.")
                st.download_button("Download timetable.ics", data=ics_bytes, file_name="smartgrind_timetable.ics", mime="text/calendar")
            except Exception as e:
                st.error(f"Failed to parse timetable: {e}")

st.markdown("---")

##Roadmap generator
st.header("Roadmap & Resources")
colA, colB = st.columns([3,1])
with colA:
    goal = st.text_input("What is your goal? (e.g., 'Crack SDE internships at FAANG, AI/ML roles, Data Science role, Finish ML portfolio')")
    background = st.text_area("Brief background (skills, time available per day)")
    weeks = st.slider("Roadmap length (weeks)", min_value=4, max_value=52, value=12)
    if st.button("Generate roadmap"):
        if not goal.strip():
            st.error("Please enter a clear goal")
        else:
            with st.spinner("Creating a focused roadmap..."):
                roadmap = generate_roadmap(goal, timeframe_weeks=weeks, background=background)
                st.markdown("### Roadmap (editable)")
                st.text_area("Roadmap output", value=roadmap, height=400, key="roadmap_out")

st.caption("💝🤗SmartGrind — built for focused last-minute revision, calendar automation, and non-distracting roadmaps. Customize prompts in the code for different study styles.")
