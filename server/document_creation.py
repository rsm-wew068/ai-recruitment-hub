import os
from shiny import reactive, render, ui
from context import (
    get_candidate_context,
    get_job_context,
    get_team_summary,
    save_candidate_context,
    get_all_jobs,
    get_all_candidates
)
from llm_connect import get_response

from fpdf import FPDF
import markdown
import io


def draft_offer_letter(candidate_name, job_title, compensation, start_date, team_summary, job_description, hiring_manager_notes):
    prompt = (
        f"Candidate Name: {candidate_name}\n"
        f"Job Title: {job_title}\n"
        f"Compensation: {compensation}\n"
        f"Start Date: {start_date}\n\n"
        f"Job Description:\n{job_description}\n\n"
        f"Team Summary:\n{team_summary}\n\n"
        f"Hiring Manager Notes:\n{hiring_manager_notes}\n\n"
        "Write a professional, clear, and positive offer letter for this candidate. "
        "Include a summary of the role, compensation details, start date, and a warm welcome. "
        "Avoid excessive legal language but maintain formality."
    )

    return get_response(
        input=prompt,
        template=lambda x: x,
        llm="llama",
        md=False,
        temperature=0.5,
        max_tokens=600
    ).strip()


def generate_full_contract(candidate_name, job_title, compensation, start_date, clauses, company_policies, legal_notes):
    prompt = (
        f"Candidate Name: {candidate_name}\n"
        f"Job Title: {job_title}\n"
        f"Compensation: {compensation}\n"
        f"Start Date: {start_date}\n\n"
        f"Clauses:\n{clauses}\n\n"
        f"Company Policies:\n{company_policies}\n\n"
        f"Legal Notes:\n{legal_notes}\n\n"
        "Draft a complete employment contract using the information above. "
        "Structure it with proper headings, include all clauses, and align with common HR compliance standards. "
        "Use formal legal language where appropriate."
    )

    return get_response(
        input=prompt,
        template=lambda x: x,
        llm="llama",
        md=False,
        temperature=0.4,
        max_tokens=1200
    ).strip()


def server(input, output, session):
    print("✅ Entered document generation server()")
    # === Update job dropdown from context ===
    @reactive.effect
    def _populate_job_dropdown():
        jobs = get_all_jobs()
        # value = job_id (UUID), label = title
        job_choices = {
            k: f"{v.get('title', 'Untitled')} ({k[:8]})"
            for k, v in jobs.items()
        }
        ui.update_select("job_dropdown_doc", choices=job_choices)


    # === Update candidate dropdown based on selected job ===
    @reactive.effect
    def _populate_candidate_dropdown():
        job_id = input.job_dropdown_doc()
        print("📎 selected job_id:", job_id)

        if not job_id:
            ui.update_select("candidate_dropdown_doc", choices={"⬅️ Select a job first": ""})
            return

        candidates = get_all_candidates()

        filtered = {
            cid: f"{v.get('Name', cid)} ({v.get('Resume File', 'N/A')})"
            for cid, v in candidates.items()
            if v.get("job_id") == job_id and v.get("Resume File")
        }


        print(f"✅ Found {len(filtered)} candidates for job {job_id}")

        if filtered:
            ui.update_select("candidate_dropdown_doc", choices=filtered)
        else:
            ui.update_select("candidate_dropdown_doc", choices={"❌ No matching resumes": ""})




    # === Offer letter generation ===
    @output
    @render.text
    @reactive.event(input.generate_offer)
    def offer_letter_text():
        candidate_id = input.candidate_dropdown_doc()
        job_id = input.job_dropdown_doc()

        print("📦 candidate_id:", candidate_id)
        print("📦 job_id:", job_id)

        if not candidate_id or not job_id:
            return "❌ Select a resume and a job."

        ctx = get_candidate_context(candidate_id)
        job = get_job_context(job_id)

        print("📁 ctx loaded:", bool(ctx))
        print("📁 job loaded:", bool(job))

        if not ctx or not job:
            return "❌ Missing candidate or job context."

        comp_override = input.override_compensation().strip()
        start_override = input.override_start_date().strip()
        notes_override = input.override_notes().strip()

        offer = draft_offer_letter(
            candidate_name=ctx.get("Name", "Candidate"),
            job_title=job.get("title", "Unknown Role"),
            compensation=comp_override or job.get("compensation", "TBD"),
            start_date=start_override or job.get("start_date", "TBD"),
            team_summary=get_team_summary(),
            job_description=job.get("job_description", ""),
            hiring_manager_notes=notes_override or job.get("notes", "")
        )

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=12)

        for line in offer.split("\n"):
            pdf.multi_cell(0, 10, line)

        os.makedirs(f'/tmp/data/{job_id}/offers', exist_ok=True)
        pdf_path = f'/tmp/data/{job_id}/offers/Offer_Letter_{candidate_id}.pdf'
        pdf.output(pdf_path)

        return ui.HTML(f"<pre style='font-family: Georgia; font-size: 1rem'>{offer}</pre>")

    # === Contract generation ===
    @output
    @render.text
    @reactive.event(input.generate_contract)
    def contract_text():
        candidate_id = input.candidate_dropdown_doc()
        job_id = input.job_dropdown_doc()

        if not candidate_id or not job_id:
            return "❌ Select a resume and a job."

        ctx = get_candidate_context(candidate_id)
        job = get_job_context(job_id)

        if not ctx or not job:
            return "❌ Missing candidate or job context."

        comp_override = input.override_compensation().strip()
        start_override = input.override_start_date().strip()

        contract = generate_full_contract(
            candidate_name=ctx.get("Name", "Candidate"),
            job_title=job.get("title", "Unknown Role"),
            compensation=comp_override or job.get("compensation", "TBD"),
            start_date=start_override or job.get("start_date", "TBD"),
            clauses=job.get("clauses", "Standard IP, termination, arbitration clauses."),
            company_policies=job.get("policies", "All standard company HR policies apply."),
            legal_notes=job.get("legal_notes", "Subject to U.S. labor law.")
        )

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=12)

        for line in contract.split("\n"):
            pdf.multi_cell(0, 10, line)

        os.makedirs(f'/tmp/data/{job_id}/contracts', exist_ok=True)
        pdf_path = f'/tmp/data/{job_id}/contracts/Contract_{candidate_id}.pdf'
        pdf.output(pdf_path)

        return ui.HTML(f"<pre style='font-family: Georgia; font-size: 1rem'>{contract}</pre>")

    @output
    @render.download(filename="Offer_Letter.pdf")
    def download_offer():
        candidate_id = input.candidate_dropdown_doc()
        job_id = input.job_dropdown_doc()
        pdf = f'/tmp/data/{job_id}/offers/Offer_Letter_{candidate_id}.pdf'
        
        return pdf


    @output
    @render.download(filename="Contract.pdf")
    def download_contract():
        candidate_id = input.candidate_dropdown_doc()
        job_id = input.job_dropdown_doc()
        pdf = f"/tmp/data/{job_id}/contracts/Contract_{candidate_id}.pdf"
        return pdf


