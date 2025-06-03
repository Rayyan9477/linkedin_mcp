"""
Template manager for resume and cover letter generation
Handles loading and rendering templates from the filesystem
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger("linkedin-mcp")

class TemplateManager:
    """
    Manages templates for resume and cover letter generation
    """
    
    def __init__(self, template_dirs: Optional[List[str]] = None):
        """
        Initialize the template manager
        
        Args:
            template_dirs: List of directories to search for templates
        """
        # Default template directories
        default_dirs = [
            Path(__file__).parent.parent / "templates",
            Path.home() / ".linkedin_mcp" / "templates"
        ]
        
        # Add any additional directories
        self.template_dirs = [Path(d) for d in (template_dirs or [])] + default_dirs
        
        # Ensure template directories exist
        for template_dir in self.template_dirs:
            template_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader([str(d) for d in self.template_dirs]),
            autoescape=select_autoescape(['html', 'xml', 'md']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Register custom filters and extensions here if needed
        # self.env.filters['custom_filter'] = custom_filter_function
        
    def get_available_templates(self, template_type: str) -> Dict[str, str]:
        """
        Get a list of available templates of the specified type
        
        Args:
            template_type: Type of template ('resume' or 'cover_letter')
            
        Returns:
            Dict mapping template names to their display names
        """
        templates = {}
        
        for template_dir in self.template_dirs:
            type_dir = template_dir / template_type
            if not type_dir.exists():
                continue
                
            for template_file in type_dir.glob("*.j2"):
                template_name = template_file.stem
                display_name = template_name.replace("_", " ").title()
                templates[template_name] = display_name
        
        return templates
    
    def render_template(
        self, 
        template_type: str, 
        template_name: str, 
        context: Dict[str, Any],
        output_format: str = 'html'
    ) -> str:
        """
        Render a template with the given context
        
        Args:
            template_type: Type of template ('resume' or 'cover_letter')
            template_name: Name of the template file (without extension)
            context: Dictionary of variables to pass to the template
            output_format: Output format ('html', 'pdf', 'txt', 'md')
            
        Returns:
            Rendered template as a string
            
        Raises:
            FileNotFoundError: If template file is not found
            jinja2.TemplateError: If there's an error rendering the template
        """
        # Construct template path
        template_path = f"{template_type}/{template_name}.j2"
        
        try:
            # Load and render the template
            template = self.env.get_template(template_path)
            rendered = template.render(**context)
            
            # Post-process based on output format if needed
            if output_format == 'md':
                # Ensure markdown has proper line endings
                rendered = '\n'.join(line.rstrip() for line in rendered.split('\n'))
            
            return rendered
            
        except Exception as e:
            logger.error(f"Error rendering template {template_path}: {str(e)}")
            raise
    
    def get_template_preview(
        self, 
        template_type: str, 
        template_name: str,
        sample_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get a preview of a template with sample data
        
        Args:
            template_type: Type of template ('resume' or 'cover_letter')
            template_name: Name of the template file (without extension)
            sample_context: Optional sample context to use for preview
            
        Returns:
            Rendered preview as a string
        """
        if sample_context is None:
            sample_context = self._get_sample_context(template_type)
            
        try:
            return self.render_template(template_type, template_name, sample_context)
        except Exception as e:
            logger.error(f"Error generating template preview: {str(e)}")
            return f"Error generating preview: {str(e)}"
    
    def _get_sample_context(self, template_type: str) -> Dict[str, Any]:
        """
        Get sample context data for a template type
        
        Args:
            template_type: Type of template ('resume' or 'cover_letter')
            
        Returns:
            Dictionary of sample data
        """
        if template_type == 'resume':
            return {
                'profile': {
                    'name': 'John Doe',
                    'headline': 'Senior Software Engineer',
                    'summary': 'Experienced software engineer with 5+ years of experience...',
                    'location': 'San Francisco, CA',
                    'email': 'john.doe@example.com',
                    'phone': '(123) 456-7890',
                    'linkedin_url': 'https://linkedin.com/in/johndoe',
                    'github_url': 'https://github.com/johndoe'
                },
                'experience': [
                    {
                        'title': 'Senior Software Engineer',
                        'company': 'Tech Corp',
                        'location': 'San Francisco, CA',
                        'start_date': '2020-01-01',
                        'end_date': 'Present',
                        'description': 'Led development of key features...'
                    }
                ],
                'education': [
                    {
                        'degree': 'B.S. Computer Science',
                        'school': 'University of California, Berkeley',
                        'graduation_year': '2015'
                    }
                ],
                'skills': ['Python', 'JavaScript', 'AWS', 'Docker', 'Kubernetes'],
                'languages': ['English (Native)', 'Spanish (Fluent)']
            }
        else:  # cover_letter
            return {
                'date': '2023-11-15',
                'hiring_manager': 'Hiring Manager',
                'company': 'Tech Innovations Inc.',
                'address': '123 Tech Street\nSan Francisco, CA 94105',
                'position': 'Senior Software Engineer',
                'job_description': 'We are looking for an experienced software engineer...',
                'candidate': {
                    'name': 'John Doe',
                    'email': 'john.doe@example.com',
                    'phone': '(123) 456-7890',
                    'address': '456 Candidate Ave\nSan Francisco, CA 94110'
                },
                'opening_paragraph': 'I am excited to apply for the Senior Software Engineer position...',
                'body_paragraphs': [
                    'With over 5 years of experience in software development...',
                    'In my current role at Tech Corp, I have led multiple projects...'
                ],
                'closing_paragraph': 'I am excited about the opportunity to contribute to your team...',
                'signature': 'Best regards,'
            }
