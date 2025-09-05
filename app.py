"""
Resume Analyzer - Analyzer-only Streamlit app
Keeps all features from the original analyzer page:
- Job category / role selection and role info
- PDF / DOCX extraction (via ResumeAnalyzer helpers)
- Full analysis call (analyze_resume) and displays:
  ATS score, keyword match + missing skills, format & section scores,
  suggestions (contact, summary, skills, experience, education, format),
  course/video recommendations, JSON download
- Saves resume + analysis to DB via save_resume_data / save_analysis_data
"""
import streamlit as st
from datetime import datetime
import io
import json

# Project modules required by the analyzer
from utils.resume_analyzer import ResumeAnalyzer
from config.job_roles import JOB_ROLES
from config.courses import (
    COURSES_BY_CATEGORY, RESUME_VIDEOS, INTERVIEW_VIDEOS,
    get_courses_for_role, get_category_for_role
)
from config.database import init_database, save_resume_data, save_analysis_data
from ui_components import apply_modern_styles, page_header

st.set_page_config(page_title="Resume Analyzer", page_icon="📝", layout="wide")

class ResumeAnalyzerApp:
    def __init__(self):
        init_database()  # ensure DB ready (implementation in config/database.py)
        self.analyzer = ResumeAnalyzer()
        self.job_roles = JOB_ROLES
        apply_modern_styles()

    def render_empty_state(self, icon, message):
        return f"""
            <div style='text-align: center; padding: 2rem; color: #9aa7a6;'>
                <i class='{icon}' style='font-size: 2rem; margin-bottom: 1rem; color: #9adf9a;'></i>
                <p style='margin: 0;'>{message}</p>
            </div>
        """

    def display_analysis(self, analysis):
        # Scores
        st.markdown("### Analysis Results")
        cols = st.columns(4)
        cols[0].metric("ATS Match", f"{int(analysis.get('ats_score',0))}%")
        cols[1].metric("Keyword Match", f"{int(analysis.get('keyword_match',{}).get('score',0))}%")
        cols[2].metric("Format Score", f"{int(analysis.get('format_score',0))}%")
        cols[3].metric("Section Coverage", f"{int(analysis.get('section_score',0))}%")

        # Missing skills
        st.markdown("#### Missing / Recommended Skills")
        missing = analysis.get("keyword_match", {}).get("missing_skills", [])
        if missing:
            st.write(", ".join(missing))
        else:
            st.write("No missing skills detected for the selected role.")

        # Recommendations
        st.markdown("#### Recommendations")
        suggestions = analysis.get("suggestions") or []
        if isinstance(suggestions, str):
            st.write(suggestions)
        else:
            for s in suggestions:
                st.markdown(f"- {s}")

        # Detailed categorized suggestions (preserve UX)
        for key in [
            "contact_suggestions", "summary_suggestions", "skills_suggestions",
            "experience_suggestions", "education_suggestions", "format_suggestions"
        ]:
            items = analysis.get(key, [])
            if items:
                st.markdown(f"#### {key.replace('_',' ').title()}")
                for it in items:
                    st.markdown(f"- {it}")

        # Raw JSON + download
        st.markdown("#### Raw Analysis (JSON)")
        st.json(analysis)
        buf = io.BytesIO(json.dumps(analysis, indent=2).encode("utf-8"))
        st.download_button("Download Analysis JSON", buf, file_name=f"analysis_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.json")

    def render(self):
        page_header("Resume Analyzer", "Upload a resume and get instant AI-powered feedback optimized for your target role.")
        # Role selection
        categories = list(self.job_roles.keys())
        if not categories:
            st.error("No job categories configured. See config/job_roles.py")
            return
        selected_category = st.selectbox("Job Category", categories)
        roles = list(self.job_roles.get(selected_category, {}).keys()) or ["General"]
        selected_role = st.selectbox("Specific Role", roles)
        role_info = self.job_roles.get(selected_category, {}).get(selected_role, {})

        # Role info block
        st.markdown(
            f"""
            <div style='background-color:#111; padding:16px; border-radius:8px;'>
                <h3 style='margin:0'>{selected_role}</h3>
                <p style='color:#cfcfcf;margin:0.25rem 0'>{role_info.get('description','No description')}</p>
                <strong style='color:#9adf9a'>Required Skills:</strong>
                <p style='color:#cfcfcf;margin:0.25rem 0'>{', '.join(role_info.get('required_skills',[])) or '—'}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("---")
        uploaded_file = st.file_uploader("Upload your resume (PDF or DOCX)", type=["pdf","docx"])
        if not uploaded_file:
            st.markdown(self.render_empty_state("fas fa-cloud-upload-alt","Upload your resume to get started with AI-powered analysis"), unsafe_allow_html=True)

        if uploaded_file:
            with st.spinner("Extracting text and running analysis..."):
                try:
                    # Use analyzer helper extractors if available
                    if hasattr(self.analyzer, "extract_text_from_pdf") and uploaded_file.type == "application/pdf":
                        text = self.analyzer.extract_text_from_pdf(uploaded_file)
                    elif hasattr(self.analyzer, "extract_text_from_docx") and uploaded_file.type in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document","application/msword"):
                        text = self.analyzer.extract_text_from_docx(uploaded_file)
                    else:
                        uploaded_file.seek(0)
                        text = uploaded_file.getvalue().decode(errors="ignore")
                except Exception as e:
                    st.error(f"Could not extract text: {e}")
                    return

                # Call analyzer (preserve existing contract: analyze_resume(document_dict, role_info))
                analysis = self.analyzer.analyze_resume({'raw_text': text}, role_info)

                # Save resume + analysis to DB (preserve existing behavior; config/database should provide these)
                try:
                    resume_payload = {
                        'personal_info': {
                            'name': analysis.get('name',''),
                            'email': analysis.get('email',''),
                            'phone': analysis.get('phone',''),
                            'linkedin': analysis.get('linkedin',''),
                            'github': analysis.get('github',''),
                            'portfolio': analysis.get('portfolio','')
                        },
                        'summary': analysis.get('summary',''),
                        'target_role': selected_role,
                        'target_category': selected_category,
                        'education': analysis.get('education',[]),
                        'experience': analysis.get('experience',[]),
                        'projects': analysis.get('projects',[]),
                        'skills': analysis.get('skills',[]),
                        'template': ''
                    }
                    resume_id = save_resume_data(resume_payload)

                    recs = analysis.get('suggestions', [])
                    if isinstance(recs, str):
                        recs = [recs]

                    analysis_payload = {
                        'resume_id': resume_id,
                        'ats_score': analysis.get('ats_score'),
                        'keyword_match_score': analysis.get('keyword_match',{}).get('score'),
                        'format_score': analysis.get('format_score'),
                        'section_score': analysis.get('section_score'),
                        'missing_skills': ','.join(analysis.get('keyword_match',{}).get('missing_skills',[])),
                        'recommendations': ','.join(recs)
                    }
                    save_analysis_data(resume_id, analysis_payload)
                    st.success("Resume and analysis saved.")
                except Exception as e:
                    st.warning(f"Could not save resume/analysis: {e}")

                # If analyzer detects non-resume
                if analysis.get('document_type') and analysis.get('document_type') != 'resume':
                    st.error(f"⚠️ Detected document type: {analysis.get('document_type')}. Upload a resume for full ATS analysis.")
                    return

                # Display analysis results
                self.display_analysis(analysis)

                # Courses and videos recommendations (fixed safe lookup)
                st.markdown("### Recommended Courses & Resources")
                category = get_category_for_role(selected_role)
                courses = get_courses_for_role(selected_role)
                if not courses:
                    courses = COURSES_BY_CATEGORY.get(category, {}).get(selected_role, [])
                if courses:
                    cols = st.columns(2)
                    for i, course in enumerate(courses[:6]):
                        with cols[i % 2]:
                            st.markdown(f"- [{course[0]}]({course[1]})")
                else:
                    st.write("No course recommendations found.")

                tab1, tab2 = st.tabs(["Resume Tips", "Interview Tips"])
                with tab1:
                    for cat, videos in RESUME_VIDEOS.items():
                        st.subheader(cat)
                        for _, url in videos:
                            st.video(url)
                with tab2:
                    for cat, videos in INTERVIEW_VIDEOS.items():
                        st.subheader(cat)
                        for _, url in videos:
                            st.video(url)

def main():
    app = ResumeAnalyzerApp()
    app.render()

if __name__ == "__main__":
    main()
