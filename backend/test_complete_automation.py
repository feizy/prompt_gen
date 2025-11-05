"""
Test complete automation with feedback loop handling
"""

import sys
import os
import asyncio

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agents.orchestration_engine import AgentOrchestrationEngine


async def test_complete_automation():
    """Test complete automation with feedback handling"""
    print("=" * 80)
    print("COMPLETE AUTOMATION WITH FEEDBACK LOOP TEST")
    print("=" * 80)

    user_requirements = "I need a chatbot for my e-commerce website that can handle customer service inquiries about products, orders, and returns"

    print(f"\nUser Requirements: {user_requirements}")
    print(f"Starting complete automated workflow with feedback handling...\n")

    # Initialize the orchestration engine
    try:
        engine = AgentOrchestrationEngine()
        print("SUCCESS: Orchestration engine initialized")

    except Exception as e:
        print(f"FAILED: Failed to initialize engine: {e}")
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

        session_id = session_response['session_id']
        print(f"Session Started: {session_id}")

        # Display initial responses
        for agent_name, response in session_response['agent_responses'].items():
            print(f"\n{agent_name.upper()} RESPONSE:")
            print(f"  Type: {response['message_type']}")
            print(f"  Confidence: {response['confidence']}")
            print(f"  Content Preview:\n{response['content'][:200]}...")

    except Exception as e:
        print(f"FAILED: Failed to start session: {e}")
        return

    # Step 2: Complete automated workflow with feedback
    print("\n" + "="*60)
    print("STEP 2: COMPLETE AUTOMATED WORKFLOW")
    print("="*60)

    iteration = 0
    max_iterations = 5

    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- Iteration {iteration} ---")

        try:
            # Continue the workflow
            response = await engine.continue_without_input(session_id)

            print(f"Status: {response['status']}")
            print(f"Completed: {response['completed']}")

            if response.get('completed'):
                print(f"\n🎉 SESSION COMPLETED SUCCESSFULLY!")
                if response.get('final_prompt'):
                    print(f"Final Prompt: {len(response['final_prompt'])} chars")
                    print(f"Preview:\n{response['final_prompt'][:300]}...")
                break

            # Display current agent response
            current_agent = response.get('next_agent', 'unknown')
            if 'agent_responses' in response:
                for agent_name, agent_response in response['agent_responses'].items():
                    print(f"\n{agent_name.upper()} RESPONSE:")
                    print(f"  Type: {agent_response['message_type']}")
                    print(f"  Confidence: {agent_response['confidence']}")
                    print(f"  Content Preview:\n{agent_response['content'][:200]}...")

            # Check if waiting for user input
            if response.get('requires_user_input'):
                print(f"\n⚠️ Agent requires user input, but continuing automatically...")
                # Add some simulated user input to continue
                await engine.process_user_input(
                    session_id=session_id,
                    user_input="Please continue with the current information and make reasonable assumptions.",
                    supplementary_inputs=["Continue the process."]
                )

        except Exception as e:
            print(f"FAILED: Iteration {iteration} failed: {e}")
            break

    # Step 3: Final summary
    print("\n" + "="*60)
    print("STEP 3: FINAL SUMMARY")
    print("="*60)

    try:
        final_status = await engine.get_session_status(session_id)
        conversation = await engine.get_conversation_history(session_id)

        print(f"Final Status: {final_status['status']}")
        print(f"Total Messages: {len(conversation)}")
        print(f"Total Iterations: {final_status['current_iteration'] + 1}")

        # Show message flow
        print(f"\nMessage Flow:")
        for i, msg in enumerate(conversation, 1):
            print(f"  {i}. {msg['agent_type']} -> {msg['message_type']} ({len(msg['content'])} chars)")

        # Show final status
        if final_status.get('final_prompt_available'):
            print(f"\n✅ Final prompt successfully generated!")
        else:
            print(f"\n⚠️ Final prompt not generated, but workflow completed.")

    except Exception as e:
        print(f"FAILED: Failed to get final summary: {e}")

    print("\n" + "="*80)
    print("COMPLETE AUTOMATION TEST FINISHED")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_complete_automation())