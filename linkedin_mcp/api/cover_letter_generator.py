"""
Cover letter generator module for LinkedIn MCP
Uses AI to create personalized cover letters based on LinkedIn profile and job description
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import openai
from linkedin_mcp.api.auth import LinkedInAuth
from linkedin_mcp.api.job_search import LinkedInJobSearch
from linkedin_mcp.api.profile import LinkedInProfile
from linkedin_mcp.utils.config import get_config

logger = logging.getLogger("linkedin-mcp")

class CoverLetterGenerator:
    """
    Generates personalized cover letters based on LinkedIn profiles and job descriptions
    """
    
    def __init__(self):
        """Initialize the cover letter generator"""
        self.config = get_config()
        self.auth = LinkedInAuth()
        self.profile_service = LinkedInProfile()
        self.job_service = LinkedInJobSearch()
        
        self.data_dir = Path(self.config.get("data_dir", "data"))
        self.data_dir.mkdir(exist_ok=True)
        self.cover_letters_dir = self.data_dir / "cover_letters"
        self.cover_letters_dir.mkdir(exist_ok=True)
        
        # Set OpenAI API key if available
        openai_api_key = self.config.get("openai_api_key")
        if not openai_api_key:
            # Check environment variable
            openai_api_key = os.environ.get("OPENAI_API_KEY")
        
        if openai_api_key:
            openai.api_key = openai_api_key
    
    def generate_cover_letter(self, profile_id: str, job_id: str, template: str = "standard", format_type: str = "pdf") -> Dict[str, Any]:
        """
        Generate a cover letter tailored for a specific job based on user's profile
        
        Args:
            profile_id: LinkedIn profile ID
            job_id: LinkedIn job ID
            template: Cover letter template to use
            format_type: Output format (pdf, docx, txt)
            
        Returns:
            Dict containing cover letter information and file path
        """
        logger.info(f"Generating cover letter for profile {profile_id} and job {job_id} using template {template}")
        
        # Get profile data
        profile_data = self.profile_service.get_profile(profile_id)
        if not profile_data:
            raise Exception(f"Could not retrieve profile data for ID {profile_id}")
        
        # Get job details
        job_data = self.job_service.get_job_details(job_id)
        if not job_data:
            raise Exception(f"Could not retrieve job data for ID {job_id}")
        
        # Generate cover letter content
        cover_letter_content = self._generate_cover_letter_content(profile_data, job_data)
        
        # Apply template formatting
        formatted_cover_letter = self._apply_cover_letter_template(cover_letter_content, template)
        
        # Convert to requested format
        cover_letter_file = self._convert_cover_letter_format(formatted_cover_letter, profile_id, job_id, format_type)
        
        # Generate a cover letter ID
        cover_letter_id = f"{profile_id}_{job_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Save metadata
        cover_letter_meta = {
            "cover_letter_id": cover_letter_id,
            "profile_id": profile_id,
            "job_id": job_id,
            "template": template,
            "format": format_type,
            "created_at": datetime.now().isoformat(),
            "file_path": str(cover_letter_file)
        }
        
        meta_file = self.cover_letters_dir / f"{cover_letter_id}_meta.json"
        with open(meta_file, "w") as f:
            json.dump(cover_letter_meta, f, indent=2)
        
        return {
            "cover_letter_id": cover_letter_id,
            "profile_id": profile_id,
            "job_id": job_id,
            "file_path": str(cover_letter_file),
            "format": format_type
        }
    
    def _generate_cover_letter_content(self, profile_data: Dict[str, Any], job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate cover letter content using AI
        
        Args:
            profile_data: LinkedIn profile data
            job_data: LinkedIn job data
            
        Returns:
            Dict containing structured cover letter content
        """
        use_ai = self.config.get("use_ai", True)
        if not use_ai:
            # Just create a basic cover letter without AI
            return self._create_basic_cover_letter(profile_data, job_data)
        
        # Use AI to generate a personalized cover letter
        ai_provider = self.config.get("ai_provider", "openai")
        
        if ai_provider == "openai":
            return self._generate_cover_letter_with_openai(profile_data, job_data)
        else:
            # Fall back to basic cover letter
            logger.warning(f"Unsupported AI provider: {ai_provider}, falling back to basic cover letter")
            return self._create_basic_cover_letter(profile_data, job_data)
    
    def _create_basic_cover_letter(self, profile_data: Dict[str, Any], job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a basic cover letter without AI
        
        Args:
            profile_data: LinkedIn profile data
            job_data: LinkedIn job data
            
        Returns:
            Dict containing structured cover letter content
        """
        # Extract name and company information
        name = profile_data.get("name", "").split(" ")[0] if profile_data.get("name") else ""
        company = job_data.get("company", "")
        job_title = job_data.get("title", "")
        
        # Create date
        current_date = datetime.now().strftime("%B %d, %Y")
        
        # Create basic cover letter structure
        cover_letter = {
            "date": current_date,
            "candidate": {
                "name": profile_data.get("name", ""),
                "email": profile_data.get("email", ""),
                "phone": profile_data.get("phone", ""),
                "address": profile_data.get("location", "")
            },
            "recipient": {
                "name": "Hiring Manager",
                "title": "Hiring Manager",
                "company": company,
                "address": job_data.get("location", "")
            },
            "subject": f"Application for {job_title} Position",
            "greeting": "Dear Hiring Manager,",
            "introduction": f"I am writing to express my interest in the {job_title} position at {company}. With my background in {profile_data.get('headline', 'the field')}, I believe I would be a valuable addition to your team.",
            "body": [
                f"Throughout my career, I have developed skills in {', '.join(profile_data.get('skills', [])[:3])} that would translate well to this role. My professional experience includes positions at {', '.join([exp.get('company') for exp in profile_data.get('experience', [])[:2]])}.",
                f"I am particularly drawn to {company} because of its reputation in the industry and its commitment to excellence. The {job_title} role appeals to me because it aligns with my professional goals and skill set.",
                "I am confident that my experience and enthusiasm make me a strong candidate for this position. I welcome the opportunity to further discuss how my background, skills, and achievements would benefit your organization."
            ],
            "closing": "Thank you for considering my application. I look forward to the possibility of working with your team.",
            "signature": f"Sincerely,\n{profile_data.get('name', '')}"
        }
        
        return cover_letter
    
    def _generate_cover_letter_with_openai(self, profile_data: Dict[str, Any], job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate cover letter using OpenAI
        
        Args:
            profile_data: LinkedIn profile data
            job_data: LinkedIn job data
            
        Returns:
            Dict containing AI-generated cover letter content
        """
        if not openai.api_key:
            logger.warning("OpenAI API key not set, falling back to basic cover letter")
            return self._create_basic_cover_letter(profile_data, job_data)
        
        # Create a basic cover letter as fallback
        basic_letter = self._create_basic_cover_letter(profile_data, job_data)
        
        try:
            # Create summary of profile and job data for the prompt
            profile_summary = {
                "name": profile_data.get("name", ""),
                "headline": profile_data.get("headline", ""),
                "summary": profile_data.get("summary", ""),
                "location": profile_data.get("location", ""),
                "experience": [
                    {
                        "title": exp.get("title", ""),
                        "company": exp.get("company", ""),
                        "description": exp.get("description", "")
                    } for exp in profile_data.get("experience", [])[:3]  # Limit to 3 most recent experiences
                ],
                "skills": profile_data.get("skills", [])[:10],  # Limit to top 10 skills
                "education": [
                    {
                        "school": edu.get("school", ""),
                        "degree": edu.get("degree", ""),
                        "field_of_study": edu.get("field_of_study", "")
                    } for edu in profile_data.get("education", [])[:2]  # Limit to 2 most recent educations
                ]
            }
            
            job_summary = {
                "title": job_data.get("title", ""),
                "company": job_data.get("company", ""),
                "location": job_data.get("location", ""),
                "description": job_data.get("description", ""),
                "skills": job_data.get("skills", []),
                "seniority_level": job_data.get("seniority_level", "")
            }
            
            # Format as strings for the prompt
            profile_str = json.dumps(profile_summary, indent=2)
            job_str = json.dumps(job_summary, indent=2)
            
            model = self.config.get("openai_model", "gpt-4")
            
            # Create system message for our prompt
            system_message = """You are an expert cover letter writer helping a job seeker create a compelling,
            personalized cover letter. Given information about the candidate's profile and the job description,
            write a professional cover letter that:
            1. Highlights relevant skills and experiences that match the job requirements
            2. Demonstrates understanding of the company and role
            3. Uses a professional, enthusiastic tone
            4. Is concise (3-4 paragraphs) but impactful
            5. Includes specific accomplishments when possible
            6. Avoids clichés and generic statements
            
            Return your answer as a JSON object with the following structure:
            {
                "greeting": "personalized greeting",
                "introduction": "attention-grabbing opening paragraph",
                "body": ["paragraph 1", "paragraph 2", ...],
                "closing": "professional closing paragraph",
                "signature": "Sincerely,\\nCandidate Name"
            }"""
            
            # Call OpenAI API
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Here is the candidate's profile information:\n{profile_str}\n\nHere is the job description they're applying for:\n{job_str}\n\nPlease write a personalized cover letter."}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            # Extract the AI-generated content
            ai_content = json.loads(response.choices[0].message.content)
            
            # Update the basic letter with AI-generated content
            if "greeting" in ai_content:
                basic_letter["greeting"] = ai_content["greeting"]
            if "introduction" in ai_content:
                basic_letter["introduction"] = ai_content["introduction"]
            if "body" in ai_content:
                basic_letter["body"] = ai_content["body"]
            if "closing" in ai_content:
                basic_letter["closing"] = ai_content["closing"]
            if "signature" in ai_content:
                basic_letter["signature"] = ai_content["signature"]
            
            return basic_letter
        
        except Exception as e:
            logger.error(f"Error generating cover letter with OpenAI: {str(e)}")
            return basic_letter
    
    def _apply_cover_letter_template(self, cover_letter: Dict[str, Any], template: str) -> str:
        """
        Apply template formatting to cover letter content
        
        Args:
            cover_letter: Structured cover letter content
            template: Template name to apply
            
        Returns:
            String containing formatted cover letter in HTML
        """
        # Get template directory
        templates_dir = Path(self.config.get("cover_letter_templates_dir", "templates/cover_letter"))
        
        # Default to standard template
        if template not in ["standard", "modern", "professional", "creative", "executive"]:
            template = "standard"
        
        # Check if template exists, otherwise use a basic template
        template_file = templates_dir / f"{template}.html"
        
        if not template_file.exists():
            # Use basic template
            return self._generate_basic_cover_letter_html(cover_letter)
        
        try:
            # Read template file
            with open(template_file, "r") as f:
                template_html = f.read()
            
            # Replace placeholders with content
            # Date
            template_html = template_html.replace("{{date}}", cover_letter["date"])
            
            # Candidate info
            template_html = template_html.replace("{{candidate_name}}", cover_letter["candidate"]["name"])
            template_html = template_html.replace("{{candidate_email}}", cover_letter["candidate"]["email"])
            template_html = template_html.replace("{{candidate_phone}}", cover_letter["candidate"]["phone"])
            template_html = template_html.replace("{{candidate_address}}", cover_letter["candidate"]["address"])
            
            # Recipient info
            template_html = template_html.replace("{{recipient_name}}", cover_letter["recipient"]["name"])
            template_html = template_html.replace("{{recipient_title}}", cover_letter["recipient"]["title"])
            template_html = template_html.replace("{{recipient_company}}", cover_letter["recipient"]["company"])
            template_html = template_html.replace("{{recipient_address}}", cover_letter["recipient"]["address"])
            
            # Subject
            template_html = template_html.replace("{{subject}}", cover_letter["subject"])
            
            # Letter content
            template_html = template_html.replace("{{greeting}}", cover_letter["greeting"])
            template_html = template_html.replace("{{introduction}}", cover_letter["introduction"])
            
            # Body paragraphs
            body_html = ""
            for paragraph in cover_letter["body"]:
                body_html += f"<p>{paragraph}</p>"
            template_html = template_html.replace("{{body}}", body_html)
            
            # Closing
            template_html = template_html.replace("{{closing}}", cover_letter["closing"])
            template_html = template_html.replace("{{signature}}", cover_letter["signature"].replace("\n", "<br>"))
            
            return template_html
        except Exception as e:
            logger.error(f"Error applying cover letter template: {str(e)}")
            return self._generate_basic_cover_letter_html(cover_letter)
    
    def _generate_basic_cover_letter_html(self, cover_letter: Dict[str, Any]) -> str:
        """
        Generate basic cover letter HTML
        
        Args:
            cover_letter: Structured cover letter content
            
        Returns:
            String containing basic cover letter HTML
        """
        html = """<!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Cover Letter</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                .header { margin-bottom: 30px; }
                .date { text-align: right; margin-bottom: 20px; }
                .recipient { margin-bottom: 20px; }
                .subject { font-weight: bold; margin: 20px 0; }
                .content { margin: 20px 0; }
                .closing { margin-top: 30px; }
                .signature { margin-top: 50px; }
            </style>
        </head>
        <body>
        """
        
        # Header with candidate info
        html += "<div class='header'>"
        html += f"<p>{cover_letter['candidate']['name']}<br>"
        if cover_letter['candidate']['email']:
            html += f"{cover_letter['candidate']['email']}<br>"
        if cover_letter['candidate']['phone']:
            html += f"{cover_letter['candidate']['phone']}<br>"
        if cover_letter['candidate']['address']:
            html += f"{cover_letter['candidate']['address']}"
        html += "</p>"
        html += "</div>"
        
        # Date
        html += f"<div class='date'><p>{cover_letter['date']}</p></div>"
        
        # Recipient
        html += "<div class='recipient'>"
        html += f"<p>{cover_letter['recipient']['name']}<br>"
        if cover_letter['recipient']['title']:
            html += f"{cover_letter['recipient']['title']}<br>"
        if cover_letter['recipient']['company']:
            html += f"{cover_letter['recipient']['company']}<br>"
        if cover_letter['recipient']['address']:
            html += f"{cover_letter['recipient']['address']}"
        html += "</p>"
        html += "</div>"
        
        # Subject
        html += f"<div class='subject'><p>Subject: {cover_letter['subject']}</p></div>"
        
        # Letter content
        html += "<div class='content'>"
        html += f"<p>{cover_letter['greeting']}</p>"
        html += f"<p>{cover_letter['introduction']}</p>"
        
        for paragraph in cover_letter['body']:
            html += f"<p>{paragraph}</p>"
        
        html += f"<p>{cover_letter['closing']}</p>"
        html += "</div>"
        
        # Signature
        signature_html = cover_letter['signature'].replace("\n", "<br>")
        html += f"<div class='signature'><p>{signature_html}</p></div>"
        
        # Close HTML tags
        html += "</body></html>"
        
        return html
    
    def _convert_cover_letter_format(self, html_content: str, profile_id: str, job_id: str, format_type: str) -> Path:
        """
        Convert cover letter HTML to requested format
        
        Args:
            html_content: Cover letter in HTML format
            profile_id: LinkedIn profile ID
            job_id: LinkedIn job ID
            format_type: Output format (pdf, docx, txt)
            
        Returns:
            Path to the generated file
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        base_filename = f"cover_letter_{profile_id}_{job_id}_{timestamp}"
        
        # Always save HTML version
        html_file = self.cover_letters_dir / f"{base_filename}.html"
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
            
            pdf_file = self.cover_letters_dir / f"{base_filename}.pdf"
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
            
            docx_file = self.cover_letters_dir / f"{base_filename}.docx"
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
            txt_file = self.cover_letters_dir / f"{base_filename}.txt"
            with open(txt_file, "w", encoding="utf-8") as f:
                f.write(text)
                
            return txt_file
        except ImportError:
            logger.warning("BeautifulSoup not installed, creating basic text file")
            
            # Very basic HTML to text conversion
            import re
            
            text = html_content
            text = re.sub(r"<br\s*/?>\s*", "\n", text)
            text = re.sub(r"</(div|p|h1|h2|h3)>\s*", "\n", text)
            text = re.sub(r"<.*?>", "", text)
            
            # Save to file
            txt_file = self.cover_letters_dir / f"{base_filename}.txt"
            with open(txt_file, "w", encoding="utf-8") as f:
                f.write(text)
                
            return txt_file