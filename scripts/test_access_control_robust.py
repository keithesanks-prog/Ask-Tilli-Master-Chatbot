import asyncio
import sys
import os
from unittest.mock import MagicMock, patch
from fastapi import HTTPException, Request
from datetime import datetime

# Ensure app is in path
sys.path.append('c:/Users/ksank/Master-Chatbot')

from app.routers.agent import ask_question
from app.models.query_models import AskRequest
from app.models.data_models import AssessmentDataSet, EMTRecord

async def test_access_control():
    print("Running Data Access Control Tests...")
    
    # Mock request object
    mock_request = MagicMock(spec=Request)
    mock_request.client.host = "127.0.0.1"
    
    # Create a valid mock dataset to avoid ZeroDivisionError
    mock_dataset = AssessmentDataSet()
    mock_dataset.emt_data = [EMTRecord(student_id="s1", assessment_date=datetime.now(), emotion_score=0.5, metadata={})]
    mock_dataset.real_data = []
    mock_dataset.sel_data = []

    # Mock side-effect services
    with patch('app.routers.agent.audit_logger'), \
         patch('app.routers.agent.harmful_content_detector') as mock_hcd:
        
        # Configure HCD to return "safe" result
        mock_hcd.detect_harmful_content.return_value = {"is_harmful": False}
        mock_hcd.should_block_response.return_value = False
        
        # Test Case 1: Valid Access (Same School)
        print("\nTest 1: Valid Access (School 1 -> School 1)")
        user_s1 = {"user_id": "u1", "school_id": "School 1", "role": "educator"}
        req_s1 = AskRequest(question="How did School 1 perform?")
        try:
            with patch('app.services.data_router.DataRouter.fetch_data') as mock_fetch, \
                 patch('app.middleware.data_access.verify_data_access', return_value=True), \
                 patch('app.services.llm_engine.LLMEngine.generate_response', return_value="Mock"):
                
                mock_fetch.return_value = mock_dataset
                await ask_question(mock_request, req_s1, user_s1)
            print("PASS: Access allowed")
        except HTTPException as e:
            print(f"FAIL: {e.detail}")

        # Test Case 2: Invalid Access (Cross School)
        print("\nTest 2: Invalid Access (School 1 -> School 2)")
        req_s2 = AskRequest(question="How did School 2 perform?")
        try:
            with patch('app.services.data_router.DataRouter.fetch_data'), \
                 patch('app.middleware.data_access.verify_data_access', return_value=True), \
                 patch('app.services.llm_engine.LLMEngine.generate_response', return_value="Mock"):
                 
                await ask_question(mock_request, req_s2, user_s1)
            print("FAIL: Access should have been denied")
        except HTTPException as e:
            if e.status_code == 403:
                print(f"PASS: Access denied as expected: {e.detail}")
            else:
                print(f"FAIL: Wrong error code {e.status_code}")

        # Test Case 3: Robust Matching (Partial Name)
        print("\nTest 3: Robust Matching (Lincoln High -> School Lincoln)")
        # Note: Updated question to "School Lincoln" to trigger extraction
        user_lincoln = {"user_id": "u2", "school_id": "Lincoln High School", "role": "educator"}
        req_lincoln = AskRequest(question="How did School Lincoln perform?")
        try:
            with patch('app.services.data_router.DataRouter.fetch_data') as mock_fetch, \
                 patch('app.middleware.data_access.verify_data_access', return_value=True), \
                 patch('app.services.llm_engine.LLMEngine.generate_response', return_value="Mock"):
                
                mock_fetch.return_value = mock_dataset
                await ask_question(mock_request, req_lincoln, user_lincoln)
            print("PASS: Partial match allowed")
        except HTTPException as e:
            print(f"FAIL: Partial match denied: {e.detail}")

if __name__ == "__main__":
    asyncio.run(test_access_control())
