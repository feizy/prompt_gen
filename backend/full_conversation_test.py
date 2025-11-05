"""
Full conversation test with all agents and detailed output
"""

import sys
import os
import asyncio

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agents.product_manager import ProductManagerAgent
from src.agents.technical_developer import TechnicalDeveloperAgent
from src.agents.team_lead import TeamLeadAgent
from src.agents.interfaces import AgentContext, AgentType, Message, MessageType


async def full_conversation_test():
    """Run full conversation test with detailed output"""
    print("=" * 80)
    print("FULL AGENT CONVERSATION TEST")
    print("=" * 80)

    user_requirements = "I need a chatbot for my e-commerce website that can handle customer service inquiries about products, orders, and returns"
    session_id = "full_test_session"

    print(f"\nUser Requirements: {user_requirements}")
    print(f"Session ID: {session_id}")

    # Initialize context
    context = AgentContext(
        session_id=session_id,
        user_requirements=user_requirements,
        current_iteration=0,
        max_iterations=5,
        conversation_history=[],
        supplementary_inputs=[],
        clarifying_questions=[]
    )

    # Initialize agents
    print("\n" + "="*60)
    print("STEP 1: INITIALIZING AGENTS")
    print("="*60)

    try:
        product_manager = ProductManagerAgent()
        technical_developer = TechnicalDeveloperAgent()
        team_lead = TeamLeadAgent()
        print("SUCCESS: All agents initialized successfully")
    except Exception as e:
        print(f"FAILED: Failed to initialize agents: {e}")
        return

    # Step 1: Product Manager Analysis
    print("\n" + "="*60)
    print("STEP 2: PRODUCT MANAGER ANALYSIS")
    print("="*60)

    try:
        print("Product Manager is analyzing requirements...")

        # Debug: Build messages like PM does
        conversation_messages = product_manager._build_conversation_messages(
            context=context,
            input_message=user_requirements,
            previous_messages=None
        )

        system_prompt = product_manager._build_system_prompt(context)
        print(f"PM System Prompt Length: {len(system_prompt)}")
        print(f"PM Conversation Messages: {len(conversation_messages)}")

        # Call Product Manager
        pm_response = await product_manager.process(
            input_message=user_requirements,
            context=context
        )

        print(f"\nPRODUCT MANAGER RESPONSE:")
        print(f"   Type: {pm_response.message_type}")
        print(f"   Confidence: {pm_response.confidence}")
        print(f"   Content Length: {len(pm_response.content)}")
        print(f"   Content Preview:\n{pm_response.content[:500]}...")

        # Add to conversation history
        pm_message = Message(
            id=1,
            agent_type=AgentType.PRODUCT_MANAGER,
            content=pm_response.content,
            message_type=MessageType(pm_response.message_type),
            timestamp=None,
            metadata={"confidence": pm_response.confidence}
        )
        context.conversation_history.append(pm_message)

    except Exception as e:
        print(f"FAILED Product Manager failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 2: Technical Developer Analysis
    print("\n" + "="*60)
    print("STEP 3: TECHNICAL DEVELOPER ANALYSIS")
    print("="*60)

    try:
        print("Technical Developer is analyzing technical feasibility...")

        tech_response = await technical_developer.process(
            input_message=pm_response.content,
            context=context
        )

        print(f"\nTECHNICAL TECHNICAL DEVELOPER RESPONSE:")
        print(f"   Type: {tech_response.message_type}")
        print(f"   Confidence: {tech_response.confidence}")
        print(f"   Content Length: {len(tech_response.content)}")
        print(f"   Content Preview:\n{tech_response.content[:500]}...")

        # Add to conversation history
        tech_message = Message(
            id=2,
            agent_type=AgentType.TECHNICAL_DEVELOPER,
            content=tech_response.content,
            message_type=MessageType(tech_response.message_type),
            timestamp=None,
            metadata={"confidence": tech_response.confidence}
        )
        context.conversation_history.append(tech_message)

    except Exception as e:
        print(f"FAILED Technical Developer failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 3: Team Lead Review
    print("\n" + "="*60)
    print("STEP 4: TEAM LEAD REVIEW")
    print("="*60)

    try:
        print("Team Lead is reviewing proposals...")

        tl_response = await team_lead.process(
            input_message=user_requirements,
            context=context
        )

        print(f"\nTEAM TEAM LEAD RESPONSE:")
        print(f"   Type: {tl_response.message_type}")
        print(f"   Confidence: {tl_response.confidence}")
        print(f"   Content Length: {len(tl_response.content)}")
        print(f"   Content Preview:\n{tl_response.content[:500]}...")

        # Add to conversation history
        tl_message = Message(
            id=3,
            agent_type=AgentType.TEAM_LEAD,
            content=tl_response.content,
            message_type=MessageType(tl_response.message_type),
            timestamp=None,
            metadata={"confidence": tl_response.confidence}
        )
        context.conversation_history.append(tl_message)

    except Exception as e:
        print(f"FAILED Team Lead failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Final Summary
    print("\n" + "="*80)
    print("FINAL CONVERSATION SUMMARY")
    print("="*80)

    print(f"Total Messages in Conversation: {len(context.conversation_history)}")

    for i, msg in enumerate(context.conversation_history, 1):
        print(f"\n--- Message {i} ---")
        print(f"Agent: {msg.agent_type.value}")
        print(f"Type: {msg.message_type.value}")
        print(f"Length: {len(msg.content)} chars")
        print(f"Content:\n{msg.content}")
        print("-" * 40)

    print("\nSUCCESS FULL CONVERSATION TEST COMPLETED SUCCESSFULLY!")
    print("All 3 agents have participated in the conversation.")


if __name__ == "__main__":
    asyncio.run(full_conversation_test())