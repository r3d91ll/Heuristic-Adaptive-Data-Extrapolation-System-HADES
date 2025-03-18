#!/usr/bin/env python3
"""
Test script for the MCP server's stdio transport functionality with the Windsurf protocol.
"""

import json
import subprocess
import sys
import time
import os
import signal
import threading

def main():
    # Start the MCP server as a subprocess
    print("Starting MCP server...")
    server_process = subprocess.Popen(
        [
            "/home/todd/ML-Lab/Heuristic-Adaptive-Data-Extrapolation-System-HADES/.venv/bin/python",
            "-m", 
            "src.mcp.server",
            "--stdio"
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/home/todd/ML-Lab/Heuristic-Adaptive-Data-Extrapolation-System-HADES",
        text=True,
        bufsize=1,  # Line buffered
        env=os.environ.copy()  # Use current environment with .env file loaded
    )
    
    # Set a timeout for the entire process
    timeout = 10  # seconds
    kill_timer = threading.Timer(timeout, lambda: server_process.send_signal(signal.SIGTERM))
    kill_timer.start()
    
    try:
        # Wait for server to initialize (should receive serverInfo notification)
        print("Waiting for server initialization...")
        for _ in range(10):  # Try reading several times with timeout
            if server_process.stdout.readable() and not server_process.poll():
                server_info = server_process.stdout.readline()
                if server_info:
                    print(f"Server info: {server_info.strip()}")
                    break
            time.sleep(0.5)
        
        # First send initialize request with protocol version
        print("\nSending initialize request...")
        initialize_request = {
            "jsonrpc": "2.0",
            "id": "init-0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "HADES Test Client",
                    "version": "1.0.0"
                }
            }
        }
        server_process.stdin.write(json.dumps(initialize_request) + "\n")
        server_process.stdin.flush()
        
        # Read initialization response
        init_response = server_process.stdout.readline()
        print(f"Initialize response: {init_response.strip()}")
        
        # Then explicitly request tools list
        print("\nSending tools/list request...")
        list_tools_request = {
            "jsonrpc": "2.0",
            "id": "init-1",
            "method": "tools/list",
            "params": {}
        }
        server_process.stdin.write(json.dumps(list_tools_request) + "\n")
        server_process.stdin.flush()
        
        # Read tools response
        tools_response = server_process.stdout.readline()
        print(f"Tools response: {tools_response.strip()}")
        
        # Step 1: Send a tool execution request (show_databases)
        print("\nSending tools/call request for show_databases...")
        execute_request = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "tools/call",
            "params": {
                "name": "show_databases",
                "arguments": {}
            }
        }
        server_process.stdin.write(json.dumps(execute_request) + "\n")
        server_process.stdin.flush()
        
        # Read response
        execute_response = server_process.stdout.readline()
        print(f"Execute response: {execute_response.strip()}")
        
        # Step 2: Send another request (pathrag_retrieve)
        print("\nSending execute_tool request for pathrag_retrieve...")
        retrieve_request = {
            "jsonrpc": "2.0",
            "id": "test-2",
            "method": "execute_tool",
            "params": {
                "name": "pathrag_retrieve",
                "parameters": {
                    "query": "What databases are available?",
                    "max_paths": 3
                }
            }
        }
        server_process.stdin.write(json.dumps(retrieve_request) + "\n")
        server_process.stdin.flush()
        
        # Read response
        retrieve_response = server_process.stdout.readline()
        print(f"Retrieve response: {retrieve_response.strip()}")
        
        print("\nTest completed successfully!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Cancel the kill timer if it's still running
        kill_timer.cancel()
        
        # Always read stderr for debugging (with timeout)
        stderr_data = []
        while server_process.stderr.readable() and not server_process.poll():
            try:
                line = server_process.stderr.readline()
                if not line:
                    break
                stderr_data.append(line)
            except Exception:
                break
            
        stderr_output = ''.join(stderr_data)
        if stderr_output:
            print(f"\nServer stderr output:\n{stderr_output}")
            
        # Make sure to clean up
        print("Terminating server process...")
        if server_process.poll() is None:
            try:
                server_process.terminate()
                server_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                print("Force killing the server process...")
                server_process.kill()
                
        print("Test completed.")

if __name__ == "__main__":
    main()
