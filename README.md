**SmartGrind App 📖**

This is a simple study helper app built with Streamlit and Python.

SmartGrind is a small chat app to help students study smarter. It uses AI (Google's Gemini) to make 

hard tasks easier.

**✨ What can it do?**

The app has three main tools:

1. Make Summaries

What it does: You paste your long class notes or upload a file (like a PDF).

What you get: The app reads it and gives you a short, clean summary and some study tips. Perfect 

for last-minute revision!

2. Makes a Calendar from your Timetable

**What it does:** Upload your class timetable as a simple CSV file (with columns like Day, Start, End, 

Subject).

**What you get:** It instantly creates a calendar file (.ics). You can download this file and add 

it to your Google Calendar or phone. It even adds alarms so you're never late!

3. Make a Study Plan (Roadmap)

**What it does:** Tell the app your goal (like "Learn to code in Python" or "Prepare for my data 

science internship").

**What you get:** The app gives you a step-by-step weekly plan. It tells you what to learn, how 

much time to spend, and good websites to use.

**🚀 How to Run It**

**Get the code:** Download or clone this project.

**Install the stuff:** You need to install the Python parts listed in the file. You can usually do 

**Execute this in your terminal:**
```bash
pip install streamlit pandas ics google-genai pypdf2

Add your API Key: The AI parts need a Google Gemini API key to work.

Create a new folder in your project named .streamlit

Inside that folder, make a new file named secrets.toml

In that file, add your key like this:

GEMINI_API_KEY = "your_key_goes_here"
```
**Run the app:** 

Open your terminal in the project folder and run:
```bash
streamlit run app.py
```
