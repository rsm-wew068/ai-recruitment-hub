import os
import sys
sys.path.append('../code')

import pandas as pd
import numpy as np
from dotenv import load_dotenv
import json
from IPython.display import Markdown, display
import markdown
from shiny import reactive, render, ui, req
from shiny.express import render as render_express
from google.api_core.exceptions import ResourceExhausted
from pathlib import Path
import tempfile

load_dotenv()

import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

from llm_connect import get_response
from context import get_all_candidates, get_all_jobs
import uuid


# === TOOL FUNCTION === #

import plotly.express as px
import plotly.io as pio

def generate_plot(df: pd.DataFrame, chart_x: str, chart_y: str = None, chart_type: str = "scatter"):
    width = 1000
    height = 600

    if chart_x not in df.columns:
        raise ValueError(f"Column '{chart_x}' not in DataFrame.")
    if chart_type != "histogram" and (not chart_y or chart_y not in df.columns):
        raise ValueError(f"Column '{chart_y}' not in DataFrame.")

    if chart_type == "scatter":
        fig = px.scatter(df, x=chart_x, y=chart_y, title=f"Scatter Plot: {chart_y} vs {chart_x}", width=width, height=height)
    elif chart_type == "bar":
        fig = px.bar(df, x=chart_x, y=chart_y, title=f"Bar Chart: {chart_y} vs {chart_x}", width=width, height=height)
    elif chart_type == "line":
        fig = px.line(df, x=chart_x, y=chart_y, title=f"Line Chart: {chart_y} vs {chart_x}", width=width, height=height)
    elif chart_type == "histogram":
        fig = px.histogram(df, x=chart_x, title=f"Histogram of {chart_x}", width=width, height=height)
    else:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    return fig



# === REGISTER TOOL === #
plot_func_schema = FunctionDeclaration(
    name="generate_plot",
    description="Generate and return a chart from candidate data.",
    parameters={
        "type": "object",
        "properties": {
            "chart_x": {
                "type": "string",
                "description": "The x-axis column to plot."
            },
            "chart_y": {
                "type": "string",
                "description": "The y-axis column to plot (omit for histogram)."
            },
            "chart_type": {
                "type": "string",
                "enum": ["scatter", "bar", "line", "histogram"],
                "description": "Type of chart to render."
            }
        },
        "required": ["chart_x", "chart_type"]
    }
)

plot_tool = Tool(function_declarations=[plot_func_schema])
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash", tools=[plot_tool])


# === MAIN SHINY SERVER FUNCTION ===

def server(input, output, session):
    print("✅ Entered server()")

    last_cols = reactive.Value(('', ''))
    last_type = reactive.Value('')
    last_chat = reactive.Value(None)
    last_chart_spec = reactive.Value(None)

    @reactive.effect
    def _populate_job_ids():
        raw_candidates = get_all_candidates()
        job_ids_used = {c.get("job_id") for c in raw_candidates.values() if "job_id" in c}

        all_jobs = get_all_jobs()

        chart_choices = {
            job_id: f"{job_data.get('title', 'Untitled')} ({job_id[:8]})"
            for job_id, job_data in all_jobs.items()
            if job_id in job_ids_used
        }

        print(f"📊 Chart Job IDs: {len(chart_choices)} loaded")
        ui.update_select("chart_job_id", choices=chart_choices, selected="")
    
    @reactive.Calc
    def candidates():
        raw = get_all_candidates()
        filtered_job = input.chart_job_id()
        if not filtered_job:
            print("⚠️ No job selected.")
            return pd.DataFrame()
        df = pd.DataFrame([c for c in raw.values() if c.get("job_id") == filtered_job])
        return df
    
    @reactive.Calc
    def plot_inputs():
        df = candidates()
        chart_x = input.chart_x()
        chart_y = input.chart_y()
        chart_type = input.chart_type()

        if df.empty or not chart_x or (chart_type != "histogram" and not chart_y):
            return None

        return (df, chart_x, chart_y, chart_type)


    @reactive.effect
    def column_dropdowns():
        selected_job = input.chart_job_id()
        if not selected_job:
            # Clear dropdowns if no job selected
            ui.update_select("chart_x", choices=[], selected="")
            ui.update_select("chart_y", choices=[], selected="")
            return
        
        df = candidates()
        if df.empty:
            return 
        exclude = {"Name", "Email", "Resume File", "Key Skills", "Llama Summary", "Gemini Summary",
                   "Note", "candidate_id", "job_id", "application_date", "source"}
        valid = [c for c in df.columns if c not in exclude]
        default_x = valid[0] if valid else ""
        default_y = valid[1] if len(valid) > 1 else default_x
        ui.update_select("chart_x", choices=valid, selected=default_x)
        ui.update_select("chart_y", choices=valid, selected=default_y)
    

    @output
    @render.ui
    @reactive.event(input.generate_plot)
    def generate_display_plot():
        print("⚡ generate_display_plot triggered")

        inputs = plot_inputs()
        if inputs is None:
            print("❌ Inputs not ready")
            return ui.p("Please complete all selections before generating a chart.")

        df, chart_x, chart_y, chart_type = inputs

        try:
            fig = generate_plot(df, chart_x, chart_y if chart_type != "histogram" else None, chart_type)
            html = fig.to_html(full_html=False, include_plotlyjs="div")

            last_chart_spec.set(fig.to_json())
            last_cols.set((chart_x, chart_y))
            last_type.set(chart_type)

            return ui.HTML(html + f"<div style='display:none'>{uuid.uuid4()}</div>")

        except Exception as e:
            print(f"❌ Chart generation failed: {e}")
            return ui.p(f"Chart generation error: {e}")



        
    @output
    @render.ui
    @reactive.event(input.generate_plot)
    def llm_explain_plot():
        df = candidates()
        chart_x = input.chart_x()
        chart_y = input.chart_y()
        chart_type = input.chart_type()
        spec_json = last_chart_spec.get()

        if df.empty or not chart_x or (chart_type != "histogram" and not chart_y):
            return ui.p("⚠️ Please select valid columns and chart type.")

        try:
            columns = [chart_x] + ([chart_y] if chart_y else [])
            summary = df[columns].describe().to_string()

            if spec_json:
                plot = pio.from_json(spec_json)

            prompt = (
                f"Here is the data, summary and plot of {chart_x} vs {chart_y} used to generate a {chart_type} plot"
                f"Plot: \n{plot}\n\n"
                f"Data: {df}\n\n"
                f"Summary: {summary}\n\n"
                "Explain the chart to a recruiter, focusing on insights, trends and implications for hiring.\n\n"
                "Do not call any tool or function. Respond in natural language only."
                "Be detailed and be clear of why the chart shapes up the way it did."
            )

            chat = model.start_chat()
            response = chat.send_message(prompt)
            explanation = markdown.markdown(response.text.strip())
            last_chat.set(chat)
        except Exception as e:
            explanation = f"⚠️ Gemini error: {str(e)}"

        return ui.HTML(f"{explanation}")

    @output
    @render.ui
    @reactive.event(input.chart_chat_send)
    def chat_followup():
        user_msg = input.chart_chat_input().strip()
        chat = last_chat.get()
        df = candidates()

        chart_x, chart_y = last_cols.get()
        chart_type = last_type.get()
        spec_json = last_chart_spec.get()

        if not user_msg:
            return ui.HTML("⚠️ Please enter a follow-up question.")
        if not chat:
            return ui.HTML("⚠️ Please generate a chart first.")
        if not chart_x or not chart_type:
            return ui.HTML("⚠️ Please choose chart variables and/or type first.")
        
        # Provide full data context for Gemini: 10 rows, all columns
        clean_df = df.drop(columns=["Resume File", "Llama Summary", "Gemini Summary"], errors="ignore")
        sample_json = json.dumps(clean_df.head(10).to_dict(orient="records"), indent=2)
            
        if spec_json:
            plot = pio.from_json(spec_json)

        followup = (
            f"Here is a sample of the first 10 rows of candidate data: \n{sample_json}\n\n"
            f"This is the generated {chart_type} chart between '{chart_x}' and '{chart_y}:"
            f"Plot: {plot}"
            f"The user asked: \"{user_msg}\"\n\n"
            f"Respond helpfully based on the chart context and question. Be detailed and clear in your explanation"
        )

        try:
            chat = model.start_chat()
            response = chat.send_message(followup)
            if hasattr(response, "text") and response.text:
                explanation = markdown.markdown(response.text.strip())
            else:
                explanation = "⚠️ Gemini responded with a tool function call instead of natural language. Try adjusting the prompt."
        except ResourceExhausted:
            explanation = "<b>❌ Gemini quota exceeded. Try again soon.</b>"
        except Exception as e:
            explanation = f"<b>❌ Gemini error:</b> {str(e)}"

        return ui.HTML(explanation)
    
    @reactive.effect
    def log_generate_trigger():
        _ = input.generate_plot()
        print("👆 generate_plot button was clicked")

