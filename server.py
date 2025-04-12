#!/usr/bin/env python
"""
LinkedIn MCP Server - Main entry point
This serves as the main MCP server implementation for LinkedIn interaction
"""

import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("linkedin-mcp")

# Import local modules
from linkedin_mcp.core.mcp_handler import MCPHandler
from linkedin_mcp.core.protocol import (
    MCPRequest,
    MCPResponse,
    Error,
    SuccessResponse,
    ErrorResponse,
)

class LinkedInMCPServer:
    def __init__(self):
        self.handler = MCPHandler()
        logger.info("LinkedIn MCP Server initialized")

    def handle_request(self, raw_request: str) -> str:
        """
        Process incoming MCP request and return the response
        """
        try:
            # Parse the incoming request
            request_data = json.loads(raw_request)
            request = MCPRequest(**request_data)
            logger.info(f"Received request: {request.method} with id {request.id}")
            
            # Process the request using the handler
            result = self.handler.process_request(request)
            
            # Prepare the response
            response = SuccessResponse(
                id=request.id,
                result=result
            )
            
            return json.dumps(response.dict())
        except json.JSONDecodeError:
            logger.error("Invalid JSON in request")
            error_response = ErrorResponse(
                id=None,  # We don't know the ID if JSON parsing failed
                error=Error(code=-32700, message="Parse error: Invalid JSON")
            )
            return json.dumps(error_response.dict())
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            error_response = ErrorResponse(
                id=getattr(request, "id", None),
                error=Error(code=-32603, message=f"Internal error: {str(e)}")
            )
            return json.dumps(error_response.dict())

def main():
    """
    Main entry point for the server
    Reads requests from stdin and writes responses to stdout
    """
    server = LinkedInMCPServer()
    logger.info("LinkedIn MCP Server started. Reading from stdin...")
    
    # Process input line by line from stdin
    for line in sys.stdin:
        line = line.strip()
        if line:
            response = server.handle_request(line)
            # Output response to stdout
            print(response, flush=True)

if __name__ == "__main__":
    main()