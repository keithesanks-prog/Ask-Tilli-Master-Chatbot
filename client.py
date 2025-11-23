import requests
import sys
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
ASK_ENDPOINT = f"{BASE_URL}/agent/ask"

def main():
    print("-" * 50)
    print("Master Chatbot - Interactive Client")
    print("-" * 50)
    print(f"Connecting to server at: {BASE_URL}")
    print("Type 'quit', 'exit', or 'q' to stop.")
    print("-" * 50)

    # Check if server is running
    try:
        requests.get(f"{BASE_URL}/health")
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to server at {BASE_URL}")
        print("Please ensure 'start_server.ps1' is running in another terminal.")
        sys.exit(1)

    while True:
        try:
            question = input("\nYou: ").strip()
            
            if not question:
                continue
                
            if question.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break

            # Prepare request payload
            payload = {
                "question": question,
                # Optional fields can be added here if needed
                # "grade_level": "Grade 1",
                # "student_id": "student_001"
            }

            print("Thinking...", end="\r")
            
            # Send request
            response = requests.post(ASK_ENDPOINT, json=payload)
            
            # Clear "Thinking..."
            print(" " * 20, end="\r")

            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "No answer provided.")
                sources = data.get("data_sources", [])
                
                print(f"Agent: {answer}")
                if sources:
                    print(f"\n[Sources: {', '.join(sources)}]")
            else:
                print(f"Error ({response.status_code}): {response.text}")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()
