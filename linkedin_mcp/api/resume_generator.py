"""
Resume generator module for LinkedIn MCP
Uses AI to create personalized resumes based on LinkedIn profile and job description
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import openai
from linkedin_mcp.api.auth import LinkedInAuth
from linkedin_mcp.api.job_search import LinkedInJobSearch
from linkedin_mcp.api.profile import LinkedInProfile
from linkedin_mcp.utils.config import get_config

logger = logging.getLogger("linkedin-mcp")

class ResumeGenerator:
    """
    Generates and tailors resumes based on LinkedIn profiles and job descriptions
    """
    
    def __init__(self):
        """Initialize the resume generator"""
        self.config = get_config()
        self.auth = LinkedInAuth()
        self.profile_service = LinkedInProfile()
        self.job_service = LinkedInJobSearch()
        
        self.data_dir = Path(self.config.get("data_dir", "data"))
        self.data_dir.mkdir(exist_ok=True)
        self.resumes_dir = self.data_dir / "resumes"
        self.resumes_dir.mkdir(exist_ok=True)
        
        # Set OpenAI API key if available
        openai_api_key = self.config.get("openai_api_key")
        if not openai_api_key:
            # Check environment variable
            openai_api_key = os.environ.get("OPENAI_API_KEY")
        
        if openai_api_key:
            openai.api_key = openai_api_key
    
    def generate_resume(self, profile_id: str, template: str = "standard", format_type: str = "pdf") -> Dict[str, Any]:
        """
        Generate a resume based on a LinkedIn profile
        
        Args:
            profile_id: LinkedIn profile ID
            template: Resume template to use
            format_type: Output format (pdf, docx, txt)
            
        Returns:
            Dict containing resume information and file path
        """
        logger.info(f"Generating resume for profile {profile_id} using template {template}")
        
        # Get profile data
        profile_data = self.profile_service.get_profile(profile_id)
        if not profile_data:
            raise Exception(f"Could not retrieve profile data for ID {profile_id}")
        
        # Generate resume content using AI
        resume_content = self._generate_resume_content(profile_data)
        
        # Apply template formatting
        formatted_resume = self._apply_resume_template(resume_content, template)
        
        # Convert to requested format
        resume_file = self._convert_resume_format(formatted_resume, profile_id, format_type)
        
        # Generate a resume ID
        resume_id = f"{profile_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Save metadata
        resume_meta = {
            "resume_id": resume_id,
            "profile_id": profile_id,
            "template": template,
            "format": format_type,
            "created_at": datetime.now().isoformat(),
            "file_path": str(resume_file),
            "tailored_for_job": None
        }
        
        meta_file = self.resumes_dir / f"{resume_id}_meta.json"
        with open(meta_file, "w") as f:
            json.dump(resume_meta, f, indent=2)
        
        return {
            "resume_id": resume_id,
            "profile_id": profile_id,
            "file_path": str(resume_file),
            "format": format_type
        }
    
    def tailor_resume(self, profile_id: str, job_id: str, template: str = "standard", format_type: str = "pdf") -> Dict[str, Any]:
        """
        Generate a resume tailored for a specific job
        
        Args:
            profile_id: LinkedIn profile ID
            job_id: LinkedIn job ID
            template: Resume template to use
            format_type: Output format (pdf, docx, txt)
            
        Returns:
            Dict containing resume information and file path
        """
        logger.info(f"Tailoring resume for profile {profile_id} for job {job_id}")
        
        # Get profile data
        profile_data = self.profile_service.get_profile(profile_id)
        if not profile_data:
            raise Exception(f"Could not retrieve profile data for ID {profile_id}")
        
        # Get job details
        job_data = self.job_service.get_job_details(job_id)
        if not job_data:
            raise Exception(f"Could not retrieve job data for ID {job_id}")
        
        # Generate tailored resume content using AI
        resume_content = self._generate_tailored_resume(profile_data, job_data)
        
        # Apply template formatting
        formatted_resume = self._apply_resume_template(resume_content, template)
        
        # Convert to requested format
        resume_file = self._convert_resume_format(formatted_resume, profile_id, format_type, job_id)
        
        # Generate a resume ID
        resume_id = f"{profile_id}_{job_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Save metadata
        resume_meta = {
            "resume_id": resume_id,
            "profile_id": profile_id,
            "job_id": job_id,
            "template": template,
            "format": format_type,
            "created_at": datetime.now().isoformat(),
            "file_path": str(resume_file),
            "tailored_for_job": True
        }
        
        meta_file = self.resumes_dir / f"{resume_id}_meta.json"
        with open(meta_file, "w") as f:
            json.dump(resume_meta, f, indent=2)
        
        return {
            "resume_id": resume_id,
            "profile_id": profile_id,
            "job_id": job_id,
            "file_path": str(resume_file),
            "format": format_type
        }
    
    def _generate_resume_content(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate resume content from profile data using AI
        
        Args:
            profile_data: LinkedIn profile data
            
        Returns:
            Dict containing structured resume content
        """
        use_ai = self.config.get("use_ai", True)
        if not use_ai:
            # Just structure the profile data without AI
            return self._structure_profile_data(profile_data)
        
        # Use AI to generate a better resume
        ai_provider = self.config.get("ai_provider", "openai")
        
        if ai_provider == "openai":
            return self._generate_resume_with_openai(profile_data)
        else:
            # Fall back to structured data
            logger.warning(f"Unsupported AI provider: {ai_provider}, falling back to structured data")
            return self._structure_profile_data(profile_data)
    
    def _generate_tailored_resume(self, profile_data: Dict[str, Any], job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a resume tailored for a specific job
        
        Args:
            profile_data: LinkedIn profile data
            job_data: LinkedIn job data
            
        Returns:
            Dict containing structured tailored resume content
        """
        use_ai = self.config.get("use_ai", True)
        if not use_ai:
            # Just structure the profile data without AI
            return self._structure_profile_data(profile_data)
        
        # Use AI to generate a tailored resume
        ai_provider = self.config.get("ai_provider", "openai")
        
        if ai_provider == "openai":
            return self._generate_tailored_resume_with_openai(profile_data, job_data)
        else:
            # Fall back to structured data
            logger.warning(f"Unsupported AI provider: {ai_provider}, falling back to structured data")
            return self._structure_profile_data(profile_data)
    
    def _structure_profile_data(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Structure profile data into resume format without using AI
        
        Args:
            profile_data: LinkedIn profile data
            
        Returns:
            Dict containing structured resume content
        """
        name = profile_data.get("name", "")
        headline = profile_data.get("headline", "")
        summary = profile_data.get("summary", "")
        
        # Extract and format experience
        experience_items = []
        for exp in profile_data.get("experience", []):
            item = {
                "title": exp.get("title", ""),
                "company": exp.get("company", ""),
                "location": exp.get("location", ""),
                "date_range": f"{exp.get('start_date', '')} - {exp.get('end_date', 'Present')}",
                "description": exp.get("description", "")
            }
            experience_items.append(item)
        
        # Extract and format education
        education_items = []
        for edu in profile_data.get("education", []):
            item = {
                "school": edu.get("school", ""),
                "degree": edu.get("degree", ""),
                "field": edu.get("field_of_study", ""),
                "date_range": f"{edu.get('start_date', '')} - {edu.get('end_date', 'Present')}",
                "description": edu.get("description", "")
            }
            education_items.append(item)
        
        # Create structured resume content
        resume_content = {
            "header": {
                "name": name,
                "headline": headline,
                "contact": {
                    "email": profile_data.get("email", ""),
                    "phone": profile_data.get("phone", ""),
                    "location": profile_data.get("location", ""),
                    "linkedin": profile_data.get("profile_url", "")
                }
            },
            "summary": summary,
            "experience": experience_items,
            "education": education_items,
            "skills": profile_data.get("skills", []),
            "certifications": profile_data.get("certifications", []),
            "projects": profile_data.get("projects", []),
            "languages": profile_data.get("languages", [])
        }
        
        return resume_content
    
    def _generate_resume_with_openai(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate resume content using OpenAI
        
        Args:
            profile_data: LinkedIn profile data
            
        Returns:
            Dict containing AI-enhanced resume content
        """
        if not openai.api_key:
            logger.warning("OpenAI API key not set, falling back to structured data")
            return self._structure_profile_data(profile_data)
        
        # First create structured data as a base
        structured_data = self._structure_profile_data(profile_data)
        
        try:
            # Create a prompt for OpenAI
            profile_summary = json.dumps({
                "name": profile_data.get("name", ""),
                "headline": profile_data.get("headline", ""),
                "summary": profile_data.get("summary", ""),
                "experience": [
                    {
                        "title": exp.get("title", ""),
                        "company": exp.get("company", ""),
                        "description": exp.get("description", "")
                    } for exp in profile_data.get("experience", [])[:5]  # Limit to 5 most recent
                ],
                "skills": profile_data.get("skills", [])[:20]  # Limit to top 20 skills
            }, indent=2)
            
            model = self.config.get("openai_model", "gpt-4")
            
            # Create system message
            system_message = """You are an expert resume writer for professionals. 
            Your task is to enhance the experience descriptions, summary, and skills in this LinkedIn profile data to create a powerful professional resume.
            Focus on quantifiable achievements, impact, and relevant skills.
            Keep content truthful but optimize the wording for impact.
            Return your answer as a JSON object with the following structure:
            {
                "summary": "enhanced professional summary",
                "experience": [
                    {"title": "role", "company": "company name", "description": "enhanced bullet points highlighting achievements"}
                ],
                "skills": ["prioritized skill 1", "prioritized skill 2", ...]
            }
            Be concise but impactful."""
            
            # Call OpenAI API
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Here is the LinkedIn profile data:\n{profile_summary}\n\nPlease enhance this for a professional resume."}
                ],
                temperature=0.5,
                max_tokens=2000
            )
            
            # Extract the enhanced content
            enhanced_content = json.loads(response.choices[0].message.content)
            
            # Update structured data with enhancements
            if "summary" in enhanced_content:
                structured_data["summary"] = enhanced_content["summary"]
            
            if "experience" in enhanced_content:
                # Map the enhanced descriptions back to our structure
                for i, exp in enumerate(enhanced_content["experience"]):
                    if i < len(structured_data["experience"]):
                        structured_data["experience"][i]["description"] = exp["description"]
            
            if "skills" in enhanced_content:
                # Replace with prioritized skills
                structured_data["skills"] = enhanced_content["skills"]
            
            return structured_data
        
        except Exception as e:
            logger.error(f"Error generating resume with OpenAI: {str(e)}")
            return structured_data
    
    def _generate_tailored_resume_with_openai(self, profile_data: Dict[str, Any], job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a resume tailored for a specific job using OpenAI
        
        Args:
            profile_data: LinkedIn profile data
            job_data: LinkedIn job data
            
        Returns:
            Dict containing AI-enhanced tailored resume content
        """
        if not openai.api_key:
            logger.warning("OpenAI API key not set, falling back to structured data")
            return self._structure_profile_data(profile_data)
        
        # First create structured data as a base
        structured_data = self._structure_profile_data(profile_data)
        
        try:
            # Prepare job data summary
            job_summary = {
                "title": job_data.get("title", ""),
                "company": job_data.get("company", ""),
                "description": job_data.get("description", ""),
                "skills": job_data.get("skills", []),
                "seniority_level": job_data.get("seniority_level", "")
            }
            
            # Create a prompt for OpenAI
            profile_summary = json.dumps({
                "name": profile_data.get("name", ""),
                "headline": profile_data.get("headline", ""),
                "summary": profile_data.get("summary", ""),
                "experience": [
                    {
                        "title": exp.get("title", ""),
                        "company": exp.get("company", ""),
                        "description": exp.get("description", "")
                    } for exp in profile_data.get("experience", [])[:5]  # Limit to 5 most recent
                ],
                "skills": profile_data.get("skills", [])[:20]  # Limit to top 20 skills
            }, indent=2)
            
            # Format job summary
            job_summary_str = json.dumps(job_summary, indent=2)
            
            model = self.config.get("openai_model", "gpt-4")
            
            # Create system message
            system_message = """You are an expert resume writer specializing in tailoring resumes for specific job opportunities.
            Your task is to enhance and tailor the candidate's profile data to create a resume specifically targeted for the job described.
            Focus on relevant experience, achievements, and skills that match the job requirements.
            Prioritize skills and experiences that are most relevant to the job.
            Keep content truthful but optimize the wording and ordering for relevance to this specific job.
            Return your answer as a JSON object with the following structure:
            {
                "summary": "tailored professional summary highlighting fit for this role",
                "experience": [
                    {"title": "role", "company": "company name", "description": "enhanced bullet points highlighting relevant achievements"}
                ],
                "skills": ["prioritized relevant skill 1", "prioritized relevant skill 2", ...]
            }
            Be concise but impactful."""
            
            # Call OpenAI API
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Here is the LinkedIn profile data:\n{profile_summary}\n\nHere is the job description:\n{job_summary_str}\n\nPlease tailor this resume for the job."}
                ],
                temperature=0.5,
                max_tokens=2000
            )
            
            # Extract the enhanced content
            enhanced_content = json.loads(response.choices[0].message.content)
            
            # Update structured data with enhancements
            if "summary" in enhanced_content:
                structured_data["summary"] = enhanced_content["summary"]
            
            if "experience" in enhanced_content:
                # Map the enhanced descriptions back to our structure
                for i, exp in enumerate(enhanced_content["experience"]):
                    if i < len(structured_data["experience"]):
                        structured_data["experience"][i]["description"] = exp["description"]
            
            if "skills" in enhanced_content:
                # Replace with prioritized skills
                structured_data["skills"] = enhanced_content["skills"]
            
            return structured_data
        
        except Exception as e:
            logger.error(f"Error generating tailored resume with OpenAI: {str(e)}")
            return structured_data
    
    def _apply_resume_template(self, resume_content: Dict[str, Any], template: str) -> str:
        """
        Apply a template to the resume content
        
        Args:
            resume_content: Structured resume content
            template: Template name to apply
            
        Returns:
            String containing formatted resume in HTML
        """
        # Get template directory
        templates_dir = Path(self.config.get("resume_templates_dir", "templates/resume"))
        
        # Default to standard template
        if template not in ["standard", "modern", "professional", "creative", "executive"]:
            template = "standard"
        
        # Check if template exists, otherwise use a basic template
        template_file = templates_dir / f"{template}.html"
        
        if not template_file.exists():
            # Use basic template
            return self._generate_basic_resume_html(resume_content)
        
        try:
            # Read template file
            with open(template_file, "r") as f:
                template_html = f.read()
            
            # Replace placeholders with content
            # Header section
            template_html = template_html.replace("{{name}}", resume_content["header"]["name"])
            template_html = template_html.replace("{{headline}}", resume_content["header"]["headline"])
            template_html = template_html.replace("{{email}}", resume_content["header"]["contact"].get("email", ""))
            template_html = template_html.replace("{{phone}}", resume_content["header"]["contact"].get("phone", ""))
            template_html = template_html.replace("{{location}}", resume_content["header"]["contact"].get("location", ""))
            template_html = template_html.replace("{{linkedin}}", resume_content["header"]["contact"].get("linkedin", ""))
            
            # Summary section
            template_html = template_html.replace("{{summary}}", resume_content["summary"])
            
            # Experience section
            experience_html = ""
            for exp in resume_content["experience"]:
                experience_html += f"<div class='experience-item'>"
                experience_html += f"<h3>{exp['title']} at {exp['company']}</h3>"
                experience_html += f"<p class='date-range'>{exp['date_range']}</p>"
                experience_html += f"<p class='location'>{exp.get('location', '')}</p>"
                
                # Format description
                if "\n" in exp["description"]:
                    # Assume bullet points
                    experience_html += "<ul>"
                    for bullet in exp["description"].split("\n"):
                        bullet = bullet.strip()
                        if bullet:
                            if bullet.startswith("- "):
                                bullet = bullet[2:]
                            experience_html += f"<li>{bullet}</li>"
                    experience_html += "</ul>"
                else:
                    experience_html += f"<p>{exp['description']}</p>"
                
                experience_html += "</div>"
            
            template_html = template_html.replace("{{experience}}", experience_html)
            
            # Education section
            education_html = ""
            for edu in resume_content["education"]:
                education_html += f"<div class='education-item'>"
                if edu.get("degree") and edu.get("field"):
                    education_html += f"<h3>{edu['degree']} in {edu['field']}</h3>"
                else:
                    education_html += f"<h3>{edu.get('degree', '') or edu.get('field', '')}</h3>"
                education_html += f"<p>{edu['school']}</p>"
                education_html += f"<p class='date-range'>{edu['date_range']}</p>"
                if edu.get("description"):
                    education_html += f"<p>{edu['description']}</p>"
                education_html += "</div>"
            
            template_html = template_html.replace("{{education}}", education_html)
            
            # Skills section
            skills_html = "<ul class='skills-list'>"
            for skill in resume_content["skills"]:
                skills_html += f"<li>{skill}</li>"
            skills_html += "</ul>"
            
            template_html = template_html.replace("{{skills}}", skills_html)
            
            return template_html
        
        except Exception as e:
            logger.error(f"Error applying resume template: {str(e)}")
            return self._generate_basic_resume_html(resume_content)
    
    def _generate_basic_resume_html(self, resume_content: Dict[str, Any]) -> str:
        """
        Generate basic resume HTML when a template is not available
        
        Args:
            resume_content: Structured resume content
            
        Returns:
            String containing basic resume HTML
        """
        html = """<!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Resume</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { text-align: center; margin-bottom: 20px; }
                .section { margin-bottom: 20px; }
                h1 { margin-bottom: 5px; }
                h2 { border-bottom: 1px solid #ccc; padding-bottom: 5px; }
                .experience-item, .education-item { margin-bottom: 15px; }
                .date-range { font-style: italic; color: #666; }
                .skills-list { columns: 3; }
                .contact-info { margin-top: 5px; }
            </style>
        </head>
        <body>
        """
        
        # Header section
        html += "<div class='header'>"
        html += f"<h1>{resume_content['header']['name']}</h1>"
        html += f"<p>{resume_content['header']['headline']}</p>"
        html += "<p class='contact-info'>"
        contact = resume_content['header']['contact']
        if contact.get('email'):
            html += f"{contact['email']} | "
        if contact.get('phone'):
            html += f"{contact['phone']} | "
        if contact.get('location'):
            html += f"{contact['location']}"
        html += "</p>"
        if contact.get('linkedin'):
            html += f"<p><a href='{contact['linkedin']}'>{contact['linkedin']}</a></p>"
        html += "</div>"
        
        # Summary section
        html += "<div class='section'>"
        html += "<h2>Summary</h2>"
        html += f"<p>{resume_content['summary']}</p>"
        html += "</div>"
        
        # Experience section
        html += "<div class='section'>"
        html += "<h2>Experience</h2>"
        for exp in resume_content["experience"]:
            html += "<div class='experience-item'>"
            html += f"<h3>{exp['title']} at {exp['company']}</h3>"
            html += f"<p class='date-range'>{exp['date_range']}</p>"
            if exp.get('location'):
                html += f"<p>{exp['location']}</p>"
            
            # Format description
            description = exp["description"]
            if "\n" in description:
                # Assume bullet points
                html += "<ul>"
                for bullet in description.split("\n"):
                    bullet = bullet.strip()
                    if bullet:
                        if bullet.startswith("- "):
                            bullet = bullet[2:]
                        html += f"<li>{bullet}</li>"
                html += "</ul>"
            else:
                html += f"<p>{description}</p>"
            
            html += "</div>"
        html += "</div>"
        
        # Education section
        html += "<div class='section'>"
        html += "<h2>Education</h2>"
        for edu in resume_content["education"]:
            html += "<div class='education-item'>"
            if edu.get("degree") and edu.get("field"):
                html += f"<h3>{edu['degree']} in {edu['field']}</h3>"
            else:
                html += f"<h3>{edu.get('degree', '') or edu.get('field', '')}</h3>"
            html += f"<p>{edu['school']}</p>"
            html += f"<p class='date-range'>{edu['date_range']}</p>"
            if edu.get("description"):
                html += f"<p>{edu['description']}</p>"
            html += "</div>"
        html += "</div>"
        
        # Skills section
        html += "<div class='section'>"
        html += "<h2>Skills</h2>"
        html += "<ul class='skills-list'>"
        for skill in resume_content["skills"]:
            html += f"<li>{skill}</li>"
        html += "</ul>"
        html += "</div>"
        
        # Close tags
        html += "</body></html>"
        
        return html
    
    def _convert_resume_format(self, html_content: str, profile_id: str, format_type: str, job_id: str = None) -> Path:
        """
        Convert resume HTML to the requested format
        
        Args:
            html_content: Resume in HTML format
            profile_id: LinkedIn profile ID
            format_type: Output format (pdf, docx, txt)
            job_id: Optional job ID for tailored resumes
            
        Returns:
            Path to the generated resume file
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        if job_id:
            base_filename = f"resume_{profile_id}_{job_id}_{timestamp}"
        else:
            base_filename = f"resume_{profile_id}_{timestamp}"
        
        # Always save HTML version
        html_file = self.resumes_dir / f"{base_filename}.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # Convert to requested format
        if format_type == "pdf":
            return self._convert_to_pdf(html_file, base_filename)
        elif format_type == "docx":
            return self._convert_to_docx(html_file, base_filename)
        elif format_type == "txt":
            return self._convert_to_txt(html_content, base_filename)
        else:
            # Default to HTML
            return html_file
    
    def _convert_to_pdf(self, html_file: Path, base_filename: str) -> Path:
        """
        Convert HTML to PDF
        
        Args:
            html_file: Path to HTML file
            base_filename: Base filename for output
            
        Returns:
            Path to the generated PDF file
        """
        try:
            # Try to use weasyprint for PDF conversion
            import weasyprint
            
            pdf_file = self.resumes_dir / f"{base_filename}.pdf"
            weasyprint.HTML(html_file).write_pdf(pdf_file)
            return pdf_file
        except ImportError:
            logger.warning("weasyprint not installed, returning HTML file instead of PDF")
            return html_file
    
    def _convert_to_docx(self, html_file: Path, base_filename: str) -> Path:
        """
        Convert HTML to DOCX
        
        Args:
            html_file: Path to HTML file
            base_filename: Base filename for output
            
        Returns:
            Path to the generated DOCX file
        """
        try:
            # Try to use pypandoc for conversion
            import pypandoc
            
            docx_file = self.resumes_dir / f"{base_filename}.docx"
            pypandoc.convert_file(
                str(html_file),
                "docx",
                outputfile=str(docx_file),
                extra_args=["--reference-doc=reference.docx"]
            )
            return docx_file
        except ImportError:
            logger.warning("pypandoc not installed, returning HTML file instead of DOCX")
            return html_file
    
    def _convert_to_txt(self, html_content: str, base_filename: str) -> Path:
        """
        Convert HTML to plain text
        
        Args:
            html_content: HTML content
            base_filename: Base filename for output
            
        Returns:
            Path to the generated text file
        """
        try:
            from bs4 import BeautifulSoup
            
            # Parse HTML and extract text
            soup = BeautifulSoup(html_content, "html.parser")
            text = soup.get_text("\n\n", strip=True)
            
            # Save to file
            txt_file = self.resumes_dir / f"{base_filename}.txt"
            with open(txt_file, "w", encoding="utf-8") as f:
                f.write(text)
                
            return txt_file
        except ImportError:
            logger.warning("BeautifulSoup not installed, creating basic text file")
            
            # Very basic HTML to text conversion
            import re
            
            text = html_content
            text = re.sub(r"<br\s*/?>\s*", "\n", text)
            text = re.sub(r"</(div|p|h1|h2|h3|li)>\s*", "\n", text)
            text = re.sub(r"<.*?>", "", text)
            
            # Save to file
            txt_file = self.resumes_dir / f"{base_filename}.txt"
            with open(txt_file, "w", encoding="utf-8") as f:
                f.write(text)
                
            return txt_file