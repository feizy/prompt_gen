"""
Test the complete automation orchestration engine
"""

import sys
import os
import asyncio

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agents.orchestration_engine import AgentOrchestrationEngine


async def test_automation_engine():
    """Test the complete automated workflow"""
    print("=" * 80)
    print("AUTOMATED AGENT ORCHESTRATION ENGINE TEST")
    print("=" * 80)

    user_requirements = "I need a chatbot for my e-commerce website that can handle customer service inquiries about products, orders, and returns"

    print(f"\nUser Requirements: {user_requirements}")
    print(f"Starting automated workflow...\n")

    # Initialize the orchestration engine
    try:
        engine = AgentOrchestrationEngine()
        print("SUCCESS: Orchestration engine initialized")

        # Check engine status
        status = engine.get_engine_status()
        print(f"Engine Status: {status}")

    except Exception as e:
        print(f"FAILED: Failed to initialize engine: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 1: Start the automated session
    print("\n" + "="*60)
    print("STEP 1: STARTING AUTOMATED SESSION")
    print("="*60)

    try:
        session_response = await engine.start_prompt_generation_session(
            user_requirements=user_requirements,
            max_iterations=3
        )

        print(f"Session Started: {session_response['session_id']}")
        print(f"Status: {session_response['status']}")
        print(f"Next Agent: {session_response['next_agent']}")

        # Display Product Manager response
        pm_response = session_response['agent_responses']['product_manager']
        print(f"\nPRODUCT MANAGER RESPONSE:")
        print(f"  Type: {pm_response['message_type']}")
        print(f"  Confidence: {pm_response['confidence']}")
        print(f"  Requires User Input: {pm_response['requires_user_input']}")
        print(f"  Content Preview:\n{pm_response['content'][:300]}...")

        session_id = session_response['session_id']

    except Exception as e:
        print(f"FAILED: Failed to start session: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 2: Continue automatically (without user input)
    print("\n" + "="*60)
    print("STEP 2: AUTOMATIC TECHNICAL DEVELOPER ANALYSIS")
    print("="*60)

    try:
        tech_response = await engine.continue_without_input(session_id)

        print(f"Status: {tech_response['status']}")
        print(f"Next Agent: {tech_response['next_agent']}")

        # Display Technical Developer response
        if 'technical_developer' in tech_response['agent_responses']:
            tech_dev_response = tech_response['agent_responses']['technical_developer']
            print(f"\nTECHNICAL DEVELOPER RESPONSE:")
            print(f"  Type: {tech_dev_response['message_type']}")
            print(f"  Confidence: {tech_dev_response['confidence']}")
            print(f"  Content Preview:\n{tech_dev_response['content'][:300]}...")

    except Exception as e:
        print(f"FAILED: Failed to get technical developer response: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 3: Continue automatically to Team Lead review
    print("\n" + "="*60)
    print("STEP 3: AUTOMATIC TEAM LEAD REVIEW")
    print("="*60)

    try:
        tl_response = await engine.continue_without_input(session_id)

        print(f"Status: {tl_response['status']}")
        print(f"Completed: {tl_response['completed']}")

        # Display Team Lead response
        if 'team_lead' in tl_response['agent_responses']:
            team_lead_response = tl_response['agent_responses']['team_lead']
            print(f"\nTEAM LEAD RESPONSE:")
            print(f"  Type: {team_lead_response['message_type']}")
            print(f"  Confidence: {team_lead_response['confidence']}")
            print(f"  Content Preview:\n{team_lead_response['content'][:300]}...")

        # Check if session is completed
        if tl_response.get('completed'):
            print(f"\nSESSION COMPLETED SUCCESSFULLY!")
            if tl_response.get('final_prompt'):
                print(f"Final Prompt Generated: {len(tl_response['final_prompt'])} chars")
                print(f"Final Prompt Preview:\n{tl_response['final_prompt'][:200]}...")

    except Exception as e:
        print(f"FAILED: Failed to get team lead response: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 4: Show final conversation history
    print("\n" + "="*60)
    print("STEP 4: FINAL CONVERSATION HISTORY")
    print("="*60)

    try:
        conversation = await engine.get_conversation_history(session_id)
        print(f"Total Messages: {len(conversation)}")

        for i, msg in enumerate(conversation, 1):
            print(f"\n--- Message {i} ---")
            print(f"Agent: {msg['agent_type']}")
            print(f"Type: {msg['message_type']}")
            print(f"Length: {len(msg['content'])} chars")
            print(f"Content:\n{msg['content'][:200]}...")
            print("-" * 40)

    except Exception as e:
        print(f"FAILED: Failed to get conversation history: {e}")

    # Step 5: Final status
    print("\n" + "="*60)
    print("STEP 5: FINAL SESSION STATUS")
    print("="*60)

    try:
        final_status = await engine.get_session_status(session_id)
        print(f"Final Status: {final_status}")

        print(f"\nSession Summary:")
        print(f"  - Total Iterations: {final_status['current_iteration'] + 1}")
        print(f"  - Agent Outputs: {final_status['agent_outputs_count']}")
        print(f"  - Conversation Messages: {final_status['conversation_history_length']}")
        print(f"  - Final Prompt Available: {final_status['final_prompt_available']}")
        print(f"  - Last Activity: {final_status['last_activity']}")

    except Exception as e:
        print(f"FAILED: Failed to get final status: {e}")

    print("\n" + "="*80)
    print("AUTOMATION ENGINE TEST COMPLETED")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_automation_engine())