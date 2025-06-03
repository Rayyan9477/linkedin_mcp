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
from linkedin_mcp.utils.template_manager import TemplateManager

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
    
    def generate_resume(self, profile_id: str, template: str = None, format_type: str = "pdf") -> Dict[str, Any]:
        """
        Generate a resume from LinkedIn profile data
        
        Args:
            profile_id: LinkedIn profile ID or 'me' for current authenticated user
            template: Template to use for the resume (e.g., 'modern', 'professional'). 
                    If None, uses the first available template.
            format_type: Output format (pdf, docx, txt, html, md)
            
        Returns:
            Dict containing the resume content and metadata
        """
        try:
            # Get profile data
            profile_data = self.profile_service.get_profile(profile_id)
            
            # Generate resume content
            resume_content = self._generate_resume_content(profile_data)
            
            # Get available templates
            template_manager = TemplateManager()
            available_templates = template_manager.get_available_templates('resume')
            
            if not available_templates:
                raise ValueError("No resume templates found")
                
            # If template not specified or not found, use the first available
            if not template or template not in available_templates:
                template = next(iter(available_templates))
                logger.info(f"Using template: {template}")
            
            # Determine output format and content type
            output_format = format_type.lower()
            content_type = 'html'  # Default content type for templates
            
            # Apply template and get content in the appropriate format
            if output_format in ['html', 'pdf', 'docx', 'txt']:
                content = template_manager.render_template('resume', template, 
                                                         self._prepare_resume_context(resume_content), 'html')
            elif output_format == 'md':
                content = template_manager.render_template('resume', template, 
                                                         self._prepare_resume_context(resume_content), 'md')
                content_type = 'md'
            else:
                raise ValueError(f"Unsupported format: {format_type}")
            
            # Convert to requested format
            output_file = self._convert_resume_format(
                content=content,
                profile_id=profile_id,
                format_type=output_format,
                content_type=content_type
            )
            
            return {
                "success": True,
                "message": "Resume generated successfully",
                "profile_id": profile_id,
                "template": template,
                "format": output_format,
                "file_path": str(output_file),
                "file_name": output_file.name,
                "content_type": f"application/{output_format}"
            }
            
        except Exception as e:
            logger.error(f"Error generating resume: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to generate resume: {str(e)}",
                "error": str(e)
            }
    
    def tailor_resume(self, profile_id: str, job_id: str, template: str = None, format_type: str = "pdf") -> Dict[str, Any]:
        """
        Generate a resume tailored for a specific job
        
        Args:
            profile_id: LinkedIn profile ID or 'me' for current authenticated user
            job_id: LinkedIn job ID to tailor the resume for
            template: Template to use for the resume (e.g., 'modern', 'professional'). 
                    If None, uses the first available template.
            format_type: Output format (pdf, docx, txt, html, md)
            
        Returns:
            Dict containing the tailored resume content and metadata
        """
        try:
            # Get profile and job data
            profile_data = self.profile_service.get_profile(profile_id)
            job_data = self.job_service.get_job_details(job_id)
            
            # Generate tailored resume content
            resume_content = self._generate_tailored_resume(profile_data, job_data)
            
            # Get available templates
            template_manager = TemplateManager()
            available_templates = template_manager.get_available_templates('resume')
            
            if not available_templates:
                raise ValueError("No resume templates found")
                
            # If template not specified or not found, use the first available
            if not template or template not in available_templates:
                template = next(iter(available_templates))
                logger.info(f"Using template: {template}")
            
            # Determine output format and content type
            output_format = format_type.lower()
            content_type = 'html'  # Default content type for templates
            
            # Apply template and get content in the appropriate format
            if output_format in ['html', 'pdf', 'docx', 'txt']:
                content = template_manager.render_template('resume', template, 
                                                         self._prepare_resume_context(resume_content), 'html')
            elif output_format == 'md':
                content = template_manager.render_template('resume', template, 
                                                         self._prepare_resume_context(resume_content), 'md')
                content_type = 'md'
            else:
                raise ValueError(f"Unsupported format: {format_type}")
            
            # Convert to requested format
            output_file = self._convert_resume_format(
                content=content,
                profile_id=profile_id,
                format_type=output_format,
                job_id=job_id,
                content_type=content_type
            )
            
            return {
                "success": True,
                "message": "Tailored resume generated successfully",
                "profile_id": profile_id,
                "job_id": job_id,
                "template": template,
                "format": output_format,
                "file_path": str(output_file),
                "file_name": output_file.name,
                "content_type": f"application/{output_format}"
            }
            
        except Exception as e:
            logger.error(f"Error generating tailored resume: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to generate tailored resume: {str(e)}",
                "error": str(e)
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
        Apply a template to the resume content using the template manager
        
        Args:
            resume_content: Structured resume content
            template: Template name to apply
            
        Returns:
            String containing formatted resume in HTML
            
        Raises:
            ValueError: If template rendering fails
        """
        try:
            from linkedin_mcp.utils.template_manager import TemplateManager
            
            # Initialize template manager
            template_manager = TemplateManager()
            
            # Check if template exists
            available_templates = template_manager.get_available_templates('resume')
            if not available_templates:
                logger.warning("No resume templates found, using basic template")
                return self._generate_basic_resume_html(resume_content)
                
            # If template not specified or not found, use the first available
            if not template or template not in available_templates:
                template = next(iter(available_templates))
                logger.info(f"Using template: {template}")
            
            # Transform resume content to match template context
            context = self._prepare_resume_context(resume_content)
            
            # Render the template
            return template_manager.render_template('resume', template, context, 'html')
        
        except Exception as e:
            logger.error(f"Error applying resume template: {str(e)}")
            return self._generate_basic_resume_html(resume_content)
    
    def _prepare_resume_context(self, resume_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare resume content for template rendering
        
        Args:
            resume_content: Raw resume content from _generate_resume_content
            
        Returns:
            Dict containing context for template rendering
        """
        # Extract profile information
        profile = {
            'name': resume_content.get('header', {}).get('name', ''),
            'headline': resume_content.get('header', {}).get('headline', ''),
            'summary': resume_content.get('summary', ''),
            'email': resume_content.get('header', {}).get('contact', {}).get('email', ''),
            'phone': resume_content.get('header', {}).get('contact', {}).get('phone', ''),
            'location': resume_content.get('header', {}).get('contact', {}).get('location', ''),
            'linkedin_url': resume_content.get('header', {}).get('contact', {}).get('linkedin', '')
        }
        
        # Extract experience
        experience = []
        for exp in resume_content.get('experience', []):
            date_parts = exp.get('date_range', '').split(' - ')
            experience.append({
                'title': exp.get('title', ''),
                'company': exp.get('company', ''),
                'location': exp.get('location', ''),
                'start_date': date_parts[0] if date_parts else '',
                'end_date': date_parts[1] if len(date_parts) > 1 else 'Present',
                'description': exp.get('description', '')
            })
        
        # Extract education
        education = []
        for edu in resume_content.get('education', []):
            date_parts = edu.get('date_range', '').split(' - ')
            education.append({
                'degree': edu.get('degree', ''),
                'school': edu.get('school', ''),
                'field': edu.get('field', ''),
                'start_date': date_parts[0] if date_parts else '',
                'end_date': date_parts[1] if len(date_parts) > 1 else 'Present',
                'description': edu.get('description', '')
            })
        
        # Extract skills
        skills = resume_content.get('skills', [])
        
        # Extract languages
        languages = resume_content.get('languages', [])
        
        # Extract projects
        projects = resume_content.get('projects', [])
        
        # Extract certifications
        certifications = resume_content.get('certifications', [])
        
        return {
            'profile': profile,
            'experience': experience,
            'education': education,
            'skills': skills,
            'languages': languages,
            'projects': projects,
            'certifications': certifications
        }
    
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
    
    def _convert_resume_format(self, content: str, profile_id: str, format_type: str, job_id: str = None, content_type: str = 'html') -> Path:
        """
        Convert resume content to the requested format
        
        Args:
            content: Resume content (HTML or Markdown)
            profile_id: LinkedIn profile ID
            format_type: Output format (pdf, docx, txt, md, html)
            job_id: Optional job ID for tailored resumes
            content_type: Type of content ('html' or 'md')
            
        Returns:
            Path to the generated resume file
            
        Raises:
            ValueError: If conversion to requested format fails
        """
        if content_type not in ['html', 'md']:
            logger.warning(f"Unsupported content type: {content_type}, defaulting to html")
            content_type = 'html'
            
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        if job_id:
            base_filename = f"resume_{profile_id}_{job_id}_{timestamp}"
        else:
            base_filename = f"resume_{profile_id}_{timestamp}"
        
        # Save the original content
        file_ext = content_type
        output_file = self.resumes_dir / f"{base_filename}.{file_ext}"
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        # If format matches content type, return as is
        if (format_type == 'html' and content_type == 'html') or \
           (format_type == 'md' and content_type == 'md') or \
           (format_type == 'txt' and content_type == 'md'):
            return output_file
        
        # Convert to requested format
        try:
            if format_type == "pdf":
                if content_type == 'html':
                    return self._convert_html_to_pdf(output_file, base_filename)
                else:  # md
                    return self._convert_md_to_pdf(output_file, base_filename)
                    
            elif format_type == "docx":
                if content_type == 'html':
                    return self._convert_html_to_docx(output_file, base_filename)
                else:  # md
                    return self._convert_md_to_docx(output_file, base_filename)
                    
            elif format_type == "txt":
                if content_type == 'html':
                    return self._convert_html_to_txt(output_file, base_filename)
                else:  # md
                    return self._convert_md_to_txt(output_file, base_filename)
                    
            elif format_type == 'html' and content_type == 'md':
                return self._convert_md_to_html(output_file, base_filename)
                
            elif format_type == 'md' and content_type == 'html':
                return self._convert_html_to_md(output_file, base_filename)
                
            else:
                logger.warning(f"Unsupported format conversion: {content_type} to {format_type}")
                return output_file
            import markdown
            import weasyprint
            
            # Convert MD to HTML
            with open(md_file, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            html_content = markdown.markdown(md_content)
            
            # Save as temporary HTML
            temp_html = self.resumes_dir / f"{base_filename}_temp.html"
            with open(temp_html, 'w', encoding='utf-8') as f:
                f.write(f"<html><body>{html_content}</body></html>")
            
            # Convert to PDF
            pdf_file = self.resumes_dir / f"{base_filename}.pdf"
            weasyprint.HTML(temp_html).write_pdf(pdf_file)
            
            # Clean up
            temp_html.unlink(missing_ok=True)
            return pdf_file
            
        except ImportError:
            logger.warning("markdown or weasyprint not installed, falling back to Markdown")
            return md_file
    
    def _convert_html_to_docx(self, html_file: Path, base_filename: str) -> Path:
        """Convert HTML file to DOCX using python-docx"""
        try:
            from htmldocx import HtmlToDocx
            from docx import Document
            
            docx_file = self.resumes_dir / f"{base_filename}.docx"
            
            # Initialize document
            document = Document()
            
            # Convert HTML to DOCX
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            HtmlToDocx().add_html_to_document(html_content, document)
            document.save(docx_file)
            
            return docx_file
            
        except ImportError:
            logger.warning("python-docx or htmldocx not installed, falling back to HTML")
            return html_file
    
    def _convert_md_to_docx(self, md_file: Path, base_filename: str) -> Path:
        """Convert Markdown file to DOCX using python-docx"""
        try:
            import markdown
            from htmldocx import HtmlToDocx
            from docx import Document
            
            # Read Markdown
            with open(md_file, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # Convert to HTML
            html_content = markdown.markdown(md_content)
            
            # Create DOCX
            docx_file = self.resumes_dir / f"{base_filename}.docx"
            document = Document()
            HtmlToDocx().add_html_to_document(html_content, document)
            document.save(docx_file)
            
            return docx_file
            
        except ImportError:
            logger.warning("Required packages not installed, falling back to Markdown")
            return md_file
    
    def _convert_html_to_txt(self, html_file: Path, base_filename: str) -> Path:
        """Convert HTML to plain text using html2text"""
        try:
            import html2text
            
            # Read HTML
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Convert to plain text
            text = html2text.html2text(html_content)
            
            # Save as text file
            txt_file = self.resumes_dir / f"{base_filename}.txt"
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(text)
                
            return txt_file
            
        except ImportError:
            logger.warning("html2text not installed, falling back to HTML")
            return html_file
    
    def _convert_md_to_txt(self, md_file: Path, base_filename: str) -> Path:
        """Convert Markdown to plain text (simple file extension change)"""
        txt_file = self.resumes_dir / f"{base_filename}.txt"
        md_file.rename(txt_file)
        return txt_file
    
    def _convert_html_to_md(self, html_file: Path, base_filename: str) -> Path:
        """Convert HTML to Markdown using html2text"""
        try:
            import html2text
            
            # Read HTML
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Convert to Markdown
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = True
            markdown_content = h.handle(html_content)
            
            # Save as Markdown file
            md_file = self.resumes_dir / f"{base_filename}.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
                
            return md_file
            
        except ImportError:
            logger.warning("html2text not installed, falling back to HTML")
            return html_file
    
    def _convert_md_to_html(self, md_file: Path, base_filename: str) -> Path:
        """Convert Markdown to HTML using markdown library"""
        try:
            import markdown
            
            # Read Markdown
            with open(md_file, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # Convert to HTML
            html_content = markdown.markdown(md_content)
            
            # Save as HTML file
            html_file = self.resumes_dir / f"{base_filename}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(f"<html><body>{html_content}</body></html>")
                
            return html_file
            
        except ImportError:
            logger.warning("markdown not installed, falling back to Markdown")
            return md_file
    
    def _convert_to_pdf(self, html_file: Path, base_filename: str) -> Path:
        """
        Convert HTML to PDF
        
        Args:
            html_file: Path to the HTML file to convert
            base_filename: Base name for the output file (without extension)

        Returns:
            Path to the generated PDF file, or the original HTML file if conversion fails
        """
        try:
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