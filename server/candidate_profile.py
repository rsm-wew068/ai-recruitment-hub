import os
import fitz
import json
import re
from shiny import reactive, render, ui
from context import get_candidate_context, save_candidate_context, get_team_summary, get_job_context, get_all_jobs, get_all_candidates
from llm_connect import get_response
import html
import markdown


RESUME_DIR = "/tmp/data/"

def extract_text_from_pdf(filename, job_id):
    path = os.path.join(RESUME_DIR, job_id, 'resumes', filename) + '.pdf'
    if not os.path.exists(path):
        print(f"❌ Resume not found: {path}")
        return None, None
    try:
        doc = fitz.open(path)
        return "\n".join([page.get_text() for page in doc]), path
    except Exception as e:
        print("❌ PDF error:", e)
        return None, None

def parse_resume_with_llm(resume_text, job_description_text, team_profiles, team_summary):
    prompt = (
        f"You are evaluating a candidate for the following job posting:\n\n"
        f"{job_description_text}\n\n"
        f"Here is the candidate's resume:\n\n"
        f"{resume_text}\n\n"
        f"Here are the profiles of the current team members:\n\n{team_profiles}\n\n"
        f"Here is the team summary:\n\n{team_summary}\n\n"
        "Extract the following fields into a valid JSON object:\n"
        "- Name\n"
        "- Email\n"
        "- Years of Experience\n"
        "- Key Skills (as a list)\n"
        "- Llama Score (judge the candidate's overall fit for the job on a scale of 1–10)\n\n"
        "⚠️ Return ONLY a single valid JSON object and nothing else.\n"
    )

    response_text = get_response(
        input=prompt,
        template=lambda x: x,
        llm="llama",
        md=False,
        temperature=0.0,
        max_tokens=700,
    )

    response_text = response_text.strip().replace("```json", "").replace("```", "").strip()
    match = re.search(r'\{\s*".+?"\s*:.+?\}', response_text, re.DOTALL)
    if not match:
        raise ValueError("No valid JSON object found in LLM response.")
    return json.loads(match.group(0))

def review_llama_score(resume_text, job_description_text, score, team_profiles, team_summary):
    prompt = (
        f"You are evaluating a candidate for the following posting:\n\n"
        f"{job_description_text}\n\n"
        f"Resume:\n{resume_text}\n\n"
        f"Team Profiles:\n{team_profiles}\n\n"
        f"Team Summary:\n{team_summary}\n\n"
        f"Llama gave this candidate a score of {score}/10.\n"
        "What is your score (1–10)? Only return the number."
    )

    return get_response(
        input=prompt,
        template=lambda x: x,
        llm="gemini",
        md=False,
        temperature=0.0,
        max_tokens=10,
        model_name ='gemini-2.0-flash-lite'
    ).strip()

def summarize_entire_resume(resume_text, job_description_text, score, team_profiles, team_summary):
    prompt = (
        f"Job Description:\n{job_description_text}\n\n"
        f"Resume:\n{resume_text}\n\n"
        f"Team Profiles:\n{team_profiles}\n\n"
        f"Team Summary:\n{team_summary}\n\n"
        f"The candidate received a score of {score}/10.\n"
        "Write a detailed, honest summary of this candidate's qualifications and fit."
    )

    return get_response(
        input=prompt,
        template=lambda x: x,
        llm="llama",
        md=False,
        temperature=0.7,
        max_tokens=500
    ).strip()

def review_llama_summary(resume_text, job_description_text, score, llama_review, team_profiles, team_summary):
    prompt = (
        f"You are reviewing this Llama summary for a candidate:\n\n"
        f"Job Description:\n{job_description_text}\n\n"
        f"Resume:\n{resume_text}\n\n"
        f"Llama Summary:\n{llama_review}\n\n"
        f"Team Profiles:\n{team_profiles}\n\n"
        f"Team Summary:\n{team_summary}\n\n"
        f"Llama scored this candidate {score}/10.\n"
        "Write your own short evaluation and state if you agree or disagree with Llama’s score."
    )

    return get_response(
        input=prompt,
        template=lambda x: x,
        llm="gemini",
        md=False,
        temperature=0.7,
        max_tokens=500
    ).strip()

def server(input, output, session):


    @reactive.effect
    def _populate_job_dropdown():
        jobs = get_all_jobs()
        job_choices = {
            k: f"{v.get('title', 'Untitled')} ({k[:8]})"
            for k, v in jobs.items()
        }
        print(job_choices)
        ui.update_select("job_dropdown_for_doc", choices=job_choices)


    @reactive.effect
    def _populate_candidate_dropdown():
        job_id = input.job_dropdown_for_doc()
        print("📎 selected job_id:", job_id)

        if not job_id:
            ui.update_select("candidate_dropdown_for_doc", choices={"⬅️ Select a job first": ""})
            return

        candidates = get_all_candidates()

        filtered = {
            cid: f"{v.get('Name', cid)} ({v.get('Resume File', 'N/A')})"
            for cid, v in candidates.items()
            if str(v.get("job_id")) == str(job_id) and v.get("Resume File")
        }

        print(f"✅ Found {len(filtered)} candidates for job {job_id}")

        if filtered:
            ui.update_select("candidate_dropdown_for_doc", choices=filtered)
        else:
            ui.update_select("candidate_dropdown_for_doc", choices={"❌ No matching resumes": ""})




    @output
    @render.ui
    def summary():
        input.show_gemini()             # ✅ force reactive trigger
        input.job_dropdown_for_doc()
        input.candidate_dropdown_for_doc()

        filename = input.candidate_dropdown_for_doc()
        job_id = input.job_dropdown_for_doc()  # 🔧 ADD THIS LINE
        use_gemini = input.show_gemini() 

        if not filename or not job_id:
            return "Please select both resume and job ID."

        job_context = get_job_context(job_id)  # ✅ This now works
        job_description_text = job_context.get("job_description", "No job description available.")
        team_profiles = job_context.get("team_profiles", "No team profile available.")
        team_summary = get_team_summary()

        candidate_id = os.path.splitext(filename)[0]
        ctx = get_candidate_context(candidate_id)


        # ✅ If already evaluated for this job, return cached summary
        if ctx.get("job_id") == job_id and "Llama Summary" in ctx:
            use_gemini = input.show_gemini()
            print(f"🧪 Cached summary found for {candidate_id} / job {job_id} | Gemini: {use_gemini}")

            if 'Note' not in ctx.keys():
                ctx['Note'] = ''
                save_candidate_context(candidate_id, ctx)

            raw = ctx.get("Gemini Summary" if use_gemini else "Llama Summary", "No summary available")
            rendered = markdown.markdown(raw.strip())

            return ui.HTML(
                f"""
                <div style="
                    font-family: 'Inter', 'Segoe UI', 'Helvetica Neue', sans-serif;
                    font-size: 1rem;
                    line-height: 1.6;
                    white-space: normal;
                    word-wrap: break-word;
                    max-width: 900px;
                ">
                    {rendered}
                </div>
                """
            )



        # ✅ Run full pipeline
        resume_text, resume_path = extract_text_from_pdf(filename, job_id)
        if not resume_text:
            return "Failed to extract resume."

        try:
            parsed = parse_resume_with_llm(resume_text, job_description_text, team_profiles, team_summary)
        except Exception as e:
            return f"❌ LLM field extraction failed: {e}"

        llama_score = parsed["Llama Score"]
        gemini_score = review_llama_score(resume_text, job_description_text, llama_score, team_profiles, team_summary)
        try:
            gemini_score = int(gemini_score)
        except:
            gemini_score = None

        avg_score = (
            (llama_score + gemini_score) / 2
            if isinstance(llama_score, int) and isinstance(gemini_score, int)
            else "N/A"
        )

        llama_summary = summarize_entire_resume(resume_text, job_description_text, llama_score, team_profiles, team_summary)
        gemini_review = review_llama_summary(resume_text, job_description_text, llama_score, llama_summary, team_profiles, team_summary)

        # ✅ Save new result
        ctx.update({
            "job_id": job_id,
            "Resume File": filename,
            "Name": parsed.get("Name"),
            "Email": parsed.get("Email"),
            "Years of Experience": parsed.get("Years of Experience"),
            "Key Skills": parsed.get("Key Skills", []),
            "Llama Score": llama_score,
            "Gemini Score": gemini_score,
            "avg_score": avg_score,
            "Llama Summary": llama_summary,
            "Gemini Summary": gemini_review,
            "Note": ""
        })

        save_candidate_context(candidate_id, ctx)

        print(use_gemini)
        summary_text = gemini_review if use_gemini else llama_summary
        rendered = markdown.markdown(summary_text)


        return ui.HTML(f"""
            <div style="
                font-family: 'Inter', 'Segoe UI', 'Helvetica Neue', sans-serif;
                font-size: 1rem;
                line-height: 1.6;
                white-space: normal;
                word-wrap: break-word;
                max-width: 900px;
            ">
                {rendered}
            </div>
        """)

    
    @output
    @render.ui
    def score():
        filename = input.candidate_dropdown_for_doc()
        job_id = input.job_dropdown_for_doc()

        if not filename or not job_id:
            return ui.HTML("<p style='color: #888;'>Select a resume and job to view score.</p>")

        candidate_id = os.path.splitext(filename)[0]
        ctx = get_candidate_context(candidate_id)

        if ctx.get("job_id") == str(job_id) and "avg_score" in ctx:
            score = ctx["avg_score"]

            # Choose a color based on the score
            if isinstance(score, (int, float)):
                color = (
                    "green" if score >= 8 else
                    "orange" if score >= 5 else
                    "red"
                )
            else:
                color = "gray"

            return ui.HTML(f"""
                <div style="
                    background-color: {color};
                    color: white;
                    font-weight: bold;
                    font-size: 1.1rem;
                    padding: 0.6rem 1.2rem;
                    border-radius: 8px;
                    display: inline-block;
                ">
                    Average Score: {score}
                </div>
            """)

        return ui.HTML("<p style='color: #888;'>Score not available. Generate profile first.</p>")

    
    @output
    @render.text
    def candidate_note_ui():
        filename = input.candidate_dropdown_for_doc()
        job_id = input.job_dropdown_for_doc()
        if not filename or not job_id:
            return ui.input_text_area("candidate_note", "Add a note:", rows=3)

        candidate_id = os.path.splitext(filename)[0]
        ctx = get_candidate_context(candidate_id)
        note = ctx.get("Note", "") if ctx.get("job_id") == job_id else ""
        return ui.input_text_area("candidate_note", "Add a note:", value=note, rows=3)

    @output
    @render.ui
    def candidate_tags_ui():
        filename = input.candidate_dropdown_for_doc()
        job_id = input.job_dropdown_for_doc()
        if not filename or not job_id:
            return ui.input_text("candidate_tags", "Tags (comma-separated):")

        candidate_id = os.path.splitext(filename)[0]
        ctx = get_candidate_context(candidate_id)
        tags = ", ".join(ctx.get("Tags", [])) if ctx.get("job_id") == job_id else ""
        return ui.input_text("candidate_tags", "Tags (comma-separated):", value=tags)


    @output
    @render.text
    def note_preview():
        filename = input.candidate_dropdown_for_doc()
        job_id = input.job_dropdown_for_doc()
        if not filename or not job_id:
            return ""

        candidate_id = os.path.splitext(filename)[0]
        ctx = get_candidate_context(candidate_id)

        if ctx.get("job_id") != job_id:
            return ""

        note = ctx.get("Note", "[No note]")
        tags = ctx.get("Tags", [])
        return f"📝 Note:\n{note}\n\n🏷️ Tags: {', '.join(tags)}"
    
    @output
    @render.text
    @reactive.event(input.save_note_tags)
    def note_tag_status():
        filename = input.candidate_dropdown_for_doc()
        job_id = input.job_dropdown_for_doc()
        if not filename or not job_id:
            return "❌ Please select both a resume and a job ID."

        candidate_id = os.path.splitext(filename)[0]
        ctx = get_candidate_context(candidate_id)

        # Only update if job_id matches
        if ctx.get("job_id") != job_id:
            return "⚠️ Cannot save notes — no profile generated for this candidate/job combination."

        # Get input
        note = input.candidate_note().strip()
        tags_raw = input.candidate_tags()
        tags = [tag.strip() for tag in tags_raw.split(",") if tag.strip()]

        # Save to context
        ctx["Note"] = note
        ctx["Tags"] = tags
        save_candidate_context(candidate_id, ctx)

        return "✅ Note and tags saved."

