"""
Test the complete API workflow
"""

import asyncio
import aiohttp
import json


async def test_api_workflow():
    """Test the complete API workflow"""
    print("=" * 80)
    print("TESTING COMPLETE API WORKFLOW")
    print("=" * 80)

    base_url = "http://localhost:8001/api/v1"

    user_requirements = "I need a chatbot for my e-commerce website that can handle customer service inquiries about products, orders, and returns"

    print(f"User Requirements: {user_requirements}")
    print(f"Base URL: {base_url}")

    async with aiohttp.ClientSession() as session:
        try:
            # Step 1: Start session
            print("\n" + "="*60)
            print("STEP 1: STARTING SESSION")
            print("="*60)

            start_data = {
                "user_requirements": user_requirements,
                "max_iterations": 3
            }

            async with session.post(f"{base_url}/sessions/start", json=start_data) as response:
                if response.status == 200:
                    session_data = await response.json()
                    session_id = session_data["session_id"]

                    print(f"SUCCESS: Session started")
                    print(f"Session ID: {session_id}")
                    print(f"Status: {session_data['status']}")
                    print(f"Next Agent: {session_data['next_agent']}")

                    # Show Product Manager response
                    if 'product_manager' in session_data['agent_responses']:
                        pm_resp = session_data['agent_responses']['product_manager']
                        print(f"\nPRODUCT MANAGER:")
                        print(f"  Type: {pm_resp['message_type']}")
                        print(f"  Confidence: {pm_resp['confidence']}")
                        print(f"  Content: {pm_resp['content'][:200]}...")
                else:
                    print(f"FAILED: {response.status} - {await response.text()}")
                    return

            # Step 2: Continue automatically to Technical Developer
            print("\n" + "="*60)
            print("STEP 2: TECHNICAL DEVELOPER")
            print("="*60)

            async with session.post(f"{base_url}/sessions/{session_id}/continue") as response:
                if response.status == 200:
                    tech_data = await response.json()

                    print(f"SUCCESS: Technical Developer processed")
                    print(f"Status: {tech_data['status']}")
                    print(f"Next Agent: {tech_data['next_agent']}")

                    # Show Technical Developer response
                    if 'technical_developer' in tech_data['agent_responses']:
                        tech_resp = tech_data['agent_responses']['technical_developer']
                        print(f"\nTECHNICAL DEVELOPER:")
                        print(f"  Type: {tech_resp['message_type']}")
                        print(f"  Confidence: {tech_resp['confidence']}")
                        print(f"  Content: {tech_resp['content'][:200]}...")
                else:
                    print(f"FAILED: {response.status} - {await response.text()}")
                    return

            # Step 3: Continue automatically to Team Lead
            print("\n" + "="*60)
            print("STEP 3: TEAM LEAD REVIEW")
            print("="*60)

            async with session.post(f"{base_url}/sessions/{session_id}/continue") as response:
                if response.status == 200:
                    tl_data = await response.json()

                    print(f"SUCCESS: Team Lead processed")
                    print(f"Status: {tl_data['status']}")
                    print(f"Completed: {tl_data['completed']}")
                    print(f"Requires User Input: {tl_data['requires_user_input']}")

                    # Show Team Lead response
                    if 'team_lead' in tl_data['agent_responses']:
                        tl_resp = tl_data['agent_responses']['team_lead']
                        print(f"\nTEAM LEAD:")
                        print(f"  Type: {tl_resp['message_type']}")
                        print(f"  Confidence: {tl_resp['confidence']}")
                        print(f"  Content: {tl_resp['content'][:200]}...")
                else:
                    print(f"FAILED: {response.status} - {await response.text()}")
                    return

            # Step 4: Get final conversation history
            print("\n" + "="*60)
            print("STEP 4: CONVERSATION HISTORY")
            print("="*60)

            async with session.get(f"{base_url}/sessions/{session_id}/conversation") as response:
                if response.status == 200:
                    conv_data = await response.json()
                    conversation = conv_data['conversation']

                    print(f"Total Messages: {len(conversation)}")
                    print(f"\nMessage Flow:")
                    for i, msg in enumerate(conversation, 1):
                        print(f"  {i}. {msg['agent_type']} -> {msg['message_type']} ({len(msg['content'])} chars)")
                        print(f"     {msg['content'][:100]}...")
                else:
                    print(f"FAILED: {response.status} - {await response.text()}")
                    return

            # Step 5: Get final status
            print("\n" + "="*60)
            print("STEP 5: FINAL STATUS")
            print("="*60)

            async with session.get(f"{base_url}/sessions/{session_id}/status") as response:
                if response.status == 200:
                    final_status = await response.json()

                    print(f"Final Status: {final_status['status']}")
                    print(f"State: {final_status['state']}")
                    print(f"Iterations: {final_status['current_iteration'] + 1}/{final_status['max_iterations']}")
                    print(f"Agent Outputs: {final_status['agent_outputs_count']}")
                    print(f"Conversation Messages: {final_status['conversation_history_length']}")
                    print(f"Final Prompt Available: {final_status['final_prompt_available']}")

                    if final_status.get('final_prompt_available'):
                        print(f"\n✅ FINAL PROMPT GENERATED!")
                else:
                    print(f"FAILED: {response.status} - {await response.text()}")

        except Exception as e:
            print(f"ERROR: {e}")
            return

    print("\n" + "="*80)
    print("API WORKFLOW TEST COMPLETED")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_api_workflow())