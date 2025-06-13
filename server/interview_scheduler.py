import sys
import os, sys, json, io, zipfile
import json
import requests
from dotenv import load_dotenv
from shiny import reactive, render, ui

# Access code/context.py

from context import get_all_candidates
from llm_connect import get_response

from datetime import datetime
from fpdf import FPDF
from PyPDF2 import PdfReader
import markdown

# Load Calendly token
load_dotenv()
CALENDLY_API_KEY = os.getenv('CALENDLY_API_KEY')
if not CALENDLY_API_KEY:
    raise RuntimeError("❌ CALENDLY_API_KEY not set.")

HEADERS = {
    'Authorization': f"Bearer {CALENDLY_API_KEY}",
    'Content-Type': 'application/json'
}

_event_url_cache = None

def get_user_uri():
    response = requests.get("https://api.calendly.com/users/me", headers=HEADERS, timeout=5)
    response.raise_for_status()
    return response.json()['resource']['uri']

def get_event_type_link(user_uri):
    response = requests.get(f"https://api.calendly.com/event_types?user={user_uri}", headers=HEADERS, timeout=5)
    response.raise_for_status()
    return response.json()['collection'][0]['scheduling_url']

def schedule_interview(name, email):
    global _event_url_cache
    if _event_url_cache is None:
        user_uri = get_user_uri()
        _event_url_cache = get_event_type_link(user_uri)
    return f"{_event_url_cache}?name={name.replace(' ', '+')}&email={email}"


def draft_invite_email_with_llm(name, email, link, job_data):
    prompt = (
        f"You are a recruiter inviting a candidate to schedule an interview.\n\n"
        f"Candidate Name: {name}\n"
        f"Candidate Email: {email}\n\n"
        f"Job Title: {job_data.get('title', 'Unknown')}\n"
        f"Specialization: {job_data.get('specialization', '')}\n"
        f"Job Description:\n{job_data.get('job_description', '')}\n\n"
        f"Scheduling Link: {link}\n\n"
        f"Write a professional, warm, and concise email inviting the candidate to schedule an interview. "
        f"Include the scheduling link. Return only the email body text. No formatting or extra explanation.\n"
        f"Sign under the company name, DO NOT USE MY NAME"
    )

    return get_response(
        input=prompt,
        template=lambda x: x,
        llm="llama",
        md=False,
        temperature=0.7,
        max_tokens=500,
    )

def export_email_as_pdf(name, email_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    for line in email_text.strip().split("\n"):
        pdf.multi_cell(0, 10, line)
    output_dir = os.path.join(os.path.dirname(__file__), "emails")
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"{name.replace(' ', '_')}.pdf")
    pdf.output(filename)
    return filename



# === MAIN SHINY SERVER FUNCTION ===
def server(input, output, session):
    print("✅ Entered interview scheduler server()")

    if not hasattr(session, "_memo"):
        session._memo = {}  # 🛠 manually initialize in-memory store

    @reactive.Calc
    def job_options():
        raw_candidates = get_all_candidates()
        job_ids_used = {c.get("job_id") for c in raw_candidates.values() if "job_id" in c}

        path = "/tmp/data/context.json"
        try:
            with open(path, "r") as f:
                full = json.load(f)
                all_jobs = full.get("jobs", {})
                session._memo["all_jobs"] = all_jobs
                session._memo["all_candidates"] = full.get("candidates", {})

            # Build job_id: label mapping only for jobs with candidates
            job_choices = {
                job_id: f"{job_data.get('title', 'Untitled')} ({job_id[:8]})"
                for job_id, job_data in all_jobs.items()
                if job_id in job_ids_used
            }

            print(f"📊 Loaded {len(job_choices)} job IDs with candidates")
            return job_choices
        except Exception as e:
            print("❌ Failed to load job/candidate context:", e)
            return {}


    @output
    @render.ui
    def name_selector():
        job_ids = job_options()
        if not job_ids:
            return ui.p("No jobs available.")
        return ui.div(
            ui.input_select("selected_job", "Select Job ID", choices=job_ids),
            ui.output_ui("candidate_checkbox")
        )

    @output
    @render.ui
    def candidate_checkbox():
        job_id = input.selected_job()
        if not job_id:
            return ui.p("Select a job to view candidates.")

        candidates = session._memo.get("all_candidates", {})
        filtered = [
            {
                "label": f"{c['Name']} ({c['Email']})",
                "name": c["Name"],
                "email": c["Email"]
            }
            for c in candidates.values()
            if str(c.get("job_id", "")).strip() == str(job_id).strip()
        ]

        session._memo["filtered_candidates"] = filtered

        if not filtered:
            return ui.p("No candidates match this job.")

        return ui.input_checkbox_group(
            "selected_names",
            "Select candidates to schedule",
            choices=[c["label"] for c in filtered]
        )

    @output
    @render.ui
    @reactive.event(input.generate_links)
    def output_links_html():
        selected = input.selected_names()
        if not selected:
            return ui.p("No candidates selected.")

        job_id = input.selected_job()
        session._memo["active_job_id"] = job_id

        job_data = session._memo.get("all_jobs", {}).get(job_id, {})
        candidates = {
            f"{c['name']} ({c['email']})": c
            for c in session._memo.get("filtered_candidates", [])
        }

        results = []
        pdf_paths = []

        for label in selected:
            c = candidates.get(label)
            if not c:
                results.append(ui.p(f"{label}: Not found"))
                continue
            try:
                link = schedule_interview(c['name'], c['email'])
                email_text = draft_invite_email_with_llm(c['name'], c['email'], link, job_data)

                # Sanitize name + timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_name = f"{c['name'].replace(' ', '_')}_{timestamp}"
                filename = f"{safe_name}.pdf"

                # Correct folder: data/emails/{job_id}/
                output_dir = f"/tmp/data/{job_id}/emails"

                os.makedirs(output_dir, exist_ok=True)

                # Full path to PDF file
                pdf_path = os.path.join(output_dir, filename)

                # Generate PDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.set_font("Arial", size=12)
                for line in email_text.strip().split("\n"):
                    pdf.multi_cell(0, 10, line)
                pdf.output(pdf_path)

                # Store PDF
                pdf_paths.append(pdf_path)

                results.append(
                    ui.HTML(f"<p><b>{c['name']}</b>: <a href='{link}' target='_blank'>📅 Schedule</a> — PDF ready</p>")
                )

            except Exception as e:
                results.append(ui.p(f"{c['name']}: ERROR - {e}"))

        session._memo["pdf_paths"] = pdf_paths
        return ui.div(*results)


    @output
    @render.ui
    @reactive.event(input.generate_links)  # 🔁 Trigger update after generate button
    def pdf_selector():
        files = session._memo.get("pdf_paths", [])
        if not files:
            return ui.p("No PDFs to preview.")

        default_pdf = os.path.basename(files[0])
        return ui.input_select(
            "selected_pdf",
            "Preview PDF",
            choices=[os.path.basename(f) for f in files],
            selected=default_pdf
        )


    @output
    @render.ui
    @reactive.Calc
    def pdf_preview():
        selected = input.selected_pdf()
        job_id = session._memo.get("active_job_id", "").strip()

        # ✅ DEBUG: show raw values
        print("📄 pdf_preview triggered")
        print("🔍 selected_pdf:", selected)
        print("📁 active_job_id:", job_id)

        if not selected:
            return ui.p("⚠️ No PDF selected.")
        if not job_id:
            return ui.p("⚠️ No active job selected.")

        file_path = f"/tmp/data/{job_id}/emails/{selected}"

        if not os.path.exists(file_path):
            print("❌ File not found on disk.")
            return ui.p(f"❌ PDF not found: {selected}")

        try:
            reader = PdfReader(file_path)
            text = "\n".join([page.extract_text() or "" for page in reader.pages])
            print("✅ PDF text extracted.")
        except Exception as e:
            print("❌ Exception during PDF read:", e)
            return ui.p(f"❌ Failed to extract PDF text: {e}")

        html = markdown.markdown(text)
        return ui.HTML(f"""
            <div style='padding: 1em; font-family: Georgia, serif; font-size: 1rem; line-height: 1.6;'>
                {html}
            </div>
        """)




    @output
    @render.download(filename="Interview_Emails.zip")
    def download_emails():
        pdf_paths = session._memo.get("pdf_paths", [])
        if not pdf_paths:
            return None  # nothing to download

        job_id = session._memo.get("active_job_id", "").strip()
        zip_path = f"/tmp/data/{job_id}/emails/Interview_Emails.zip"

        if os.path.exists(zip_path):
            os.remove(zip_path)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for path in pdf_paths:
                zipf.write(path, arcname=os.path.basename(path))

        return zip_path

    @output
    @render.text
    @reactive.event(input.submit_chat)
    def refined_output():
        user_instruction = input.chat_prompt().strip()
        selected = input.selected_pdf()
        job_id = session._memo.get("active_job_id", "").strip()

        if not selected or not job_id:
            return "⚠️ Select a PDF to edit."

        # Load original text
        pdf_path = f"/tmp/data/{job_id}/emails/{selected}"

        if not os.path.exists(pdf_path):
            return "❌ Could not find the original PDF."

        reader = PdfReader(pdf_path)
        original_text = "\n".join([page.extract_text() or "" for page in reader.pages])

        # Call your LLM with edit prompt
        full_prompt = (
            f"The following is an email invitation for a first round interview at a company:\n\n"
            f"{original_text}\n\n"
            f"User instruction: {user_instruction}\n\n"
            f"Please revise the email accordingly. Return only the revised email."
        )

        try:
            revised = get_response(
                input=full_prompt,
                template=lambda x: x,
                llm="llama",
                md=False,
                temperature=0.6,
                max_tokens=600
            )

            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Arial", size=12)
            for line in revised.strip().split("\n"):
                pdf.multi_cell(0, 10, line)
            pdf.output(pdf_path)
            pdf_files = [f for f in os.listdir(f"/tmp/data/{job_id}/emails/") if f.endswith(".pdf")]

            ui.update_select("pdf_selector", choices=pdf_files)
            ui.update_text_area("edit_text", value=revised.strip())
            return revised.strip()
        except Exception as e:
            return f"❌ LLM failed: {e}"
        

    @reactive.effect
    @reactive.event(input.toggle_edit)
    def load_pdf_for_editing():
        selected = input.selected_pdf()
        job_id = session._memo.get("active_job_id", "").strip()
        if not selected or not job_id:
            return

        file_path = f"/tmp/data/{job_id}/emails/{selected}"

        if not os.path.exists(file_path):
            return
        reader = PdfReader(file_path)
        text = "\n".join([page.extract_text() or "" for page in reader.pages])

        ui.update_text_area("edit_text", value=text)



    @reactive.effect
    @reactive.event(input.save_edit)
    def save_edited_pdf():
        selected = input.selected_pdf()
        job_id = session._memo.get("active_job_id", "").strip()
        new_text = input.edit_text().strip()

        if not selected or not job_id or not new_text:
            return

        file_path = f"/tmp/data/{job_id}/emails/{selected}"

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=12)
        for line in new_text.splitlines():
            pdf.multi_cell(0, 10, line)
        pdf.output(file_path)

        print(f"✅ Overwrote PDF: {file_path}")
        pdf_files = [f for f in os.listdir(f"/tmp/data/{job_id}/emails") if f.endswith(".pdf")]
        ui.update_select("pdf_selector", choices=pdf_files)

        session.send_input_message("selected_pdf", {"value": selected})


    @output
    @render.ui
    def edit_ui_block():
        if input.toggle_edit() % 2 == 1:
            return ui.div(
                ui.input_text_area("edit_text", "Edit Email Text:", rows=20),
                ui.input_action_button("save_edit", "💾 Overwrite PDF"),
                style="margin-top: 1em;"
            )
        else:
            return None



