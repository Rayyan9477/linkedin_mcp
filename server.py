#!/usr/bin/env python
"""
LinkedIn MCP Server - Main entry point

This module implements the main server for the LinkedIn Model Context Protocol (MCP).
It handles incoming JSON-RPC 2.0 requests, processes them using the MCP handler,
and returns appropriate responses.
"""

import asyncio
import json
import logging
import signal
import sys
from typing import Any, Dict, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("linkedin_mcp.log")
    ]
)
logger = logging.getLogger("linkedin-mcp")

# Import local modules
from linkedin_mcp.core.mcp_handler import MCPHandler, MCPError, AuthenticationError, ValidationError
from linkedin_mcp.core.protocol import MCPRequest, SuccessResponse, ErrorResponse, Error

class LinkedInMCPServer:
    """
    Main server class for handling LinkedIn MCP requests.
    
    This class is responsible for:
    - Initializing the MCP handler
    - Processing incoming JSON-RPC 2.0 requests
    - Managing the server lifecycle
    - Handling graceful shutdown
    """
    
    def __init__(self):
        """Initialize the MCP server and handler."""
        self.handler = MCPHandler()
        self._shutdown_event = asyncio.Event()
        self._setup_signal_handlers()
        logger.info("LinkedIn MCP Server initialized")
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        if sys.platform != 'win32':
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(
                    sig, 
                    lambda s=sig: asyncio.create_task(self.shutdown(s.signal == signal.SIGINT))
                )
    
    async def shutdown(self, graceful: bool = True):
        """Shut down the server gracefully.
        
        Args:
            graceful: If True, wait for pending requests to complete.
        """
        if self._shutdown_event.is_set():
            return
            
        logger.info("Shutting down server...")
        self._shutdown_event.set()
        
        if graceful:
            # Add any cleanup code here
            logger.info("Waiting for pending requests to complete...")
            await asyncio.sleep(1)  # Give some time for active requests to complete
        
        logger.info("Server shutdown complete")
    
    async def handle_request(self, raw_request: str) -> str:
        """
        Process an incoming MCP request and return the response.
        
        Args:
            raw_request: The raw JSON-RPC 2.0 request as a string
            
        Returns:
            JSON string containing the response
        """
        request_id = None
        
        try:
            # Parse and validate the request
            try:
                request_data = json.loads(raw_request)
                request = MCPRequest(**request_data)
                request_id = request.id
                logger.info(f"Processing request: {request.method} (ID: {request_id})")
            except (json.JSONDecodeError, ValueError) as e:
                raise ValueError("Invalid JSON-RPC 2.0 request") from e
            
            # Process the request using the async handler
            response = await self.handler.process_request(request)
            
            # Ensure we have a valid response
            if not isinstance(response, (SuccessResponse, ErrorResponse)):
                response = SuccessResponse(id=request_id, result=response)
            
            return response.json()
            
        except MCPError as e:
            logger.error(f"MCP error: {str(e)}", exc_info=True)
            return ErrorResponse(
                id=request_id,
                error=Error(code=e.code, message=e.message, data=e.data)
            ).json()
            
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}", exc_info=True)
            return ErrorResponse(
                id=request_id,
                error=Error(
                    code=-32602,
                    message="Invalid parameters",
                    data={"errors": e.errors()}
                )
            ).json()
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return ErrorResponse(
                id=request_id,
                error=Error(
                    code=-32603,
                    message="Internal server error",
                    data={"error": str(e) if str(e) else "Unknown error"}
                )
            ).json()

async def read_stdin() -> str:
    """Read a line from stdin asynchronously."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sys.stdin.readline)

async def main():
    """
    Main entry point for the server.
    
    Sets up the server and processes requests from stdin asynchronously.
    """
    server = LinkedInMCPServer()
    logger.info("LinkedIn MCP Server started. Reading from stdin...")
    
    try:
        while not server._shutdown_event.is_set():
            try:
                # Read input asynchronously with timeout
                try:
                    line = await asyncio.wait_for(read_stdin(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                    
                line = line.strip()
                if not line:
                    continue
                
                # Process the request
                response = await server.handle_request(line)
                print(response, flush=True)
                
            except asyncio.CancelledError:
                logger.info("Received shutdown signal")
                break
                
            except Exception as e:
                logger.error(f"Error handling request: {str(e)}", exc_info=True)
                error_response = ErrorResponse(
                    id=None,
                    error=Error(code=-32603, message="Internal server error")
                )
                print(error_response.json(), flush=True)
                
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        return 1
    finally:
        await server.shutdown()
    
    return 0

def run_server():
    """Run the server with proper event loop handling."""
    if sys.platform == 'win32':
        # Windows requires special event loop policy
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        return asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(run_server())