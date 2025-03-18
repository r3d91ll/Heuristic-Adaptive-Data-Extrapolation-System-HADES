#!/usr/bin/env python3
"""
Test script for the MCP server's stdio transport functionality.
This simulates how Windsurf will interact with the MCP server.
"""

import json
import subprocess
import sys
import time

def main():
    # Start the MCP server as a subprocess
    server_process = subprocess.Popen(
        [sys.executable, "-m", "src.mcp.server", "--stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/home/todd/ML-Lab/Heuristic-Adaptive-Data-Extrapolation-System-HADES",
        text=True,
        bufsize=1  # Line buffered
    )
    
    try:
        # Step 1: Initialize
        print("Sending initialize request...")
        initialize_request = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "initialize",
            "params": {}
        }
        server_process.stdin.write(json.dumps(initialize_request) + "\n")
        server_process.stdin.flush()
        
        # Read response
        initialize_response = server_process.stdout.readline()
        print(f"Initialize response: {initialize_response}")
        
        # Step 2: List tools
        print("\nSending list_tools request...")
        list_tools_request = {
            "jsonrpc": "2.0",
            "id": "2",
            "method": "list_tools",
            "params": {}
        }
        server_process.stdin.write(json.dumps(list_tools_request) + "\n")
        server_process.stdin.flush()
        
        # Read response
        list_tools_response = server_process.stdout.readline()
        print(f"List tools response: {list_tools_response}")
        
        # Step 3: Execute a tool (show_databases)
        print("\nSending execute_tool request for show_databases...")
        execute_tool_request = {
            "jsonrpc": "2.0",
            "id": "3",
            "method": "execute_tool",
            "params": {
                "name": "show_databases",
                "parameters": {}
            }
        }
        server_process.stdin.write(json.dumps(execute_tool_request) + "\n")
        server_process.stdin.flush()
        
        # Read response
        execute_tool_response = server_process.stdout.readline()
        print(f"Execute tool response: {execute_tool_response}")
        
        # Step 4: Shutdown
        print("\nSending shutdown request...")
        shutdown_request = {
            "jsonrpc": "2.0",
            "id": "4",
            "method": "shutdown",
            "params": {}
        }
        server_process.stdin.write(json.dumps(shutdown_request) + "\n")
        server_process.stdin.flush()
        
        # Read response
        shutdown_response = server_process.stdout.readline()
        print(f"Shutdown response: {shutdown_response}")
        
        print("\nTest completed successfully!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Make sure to clean up
        print("Terminating server process...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        
        # Check for any errors on stderr
        stderr_output = server_process.stderr.read()
        if stderr_output:
            print(f"Server stderr output:\n{stderr_output}")

if __name__ == "__main__":
    main()
