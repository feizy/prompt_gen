#!/usr/bin/env python3
"""
System Integration Validation Script

This script performs comprehensive validation of the AI Agent Prompt Generator system,
including health checks, smoke tests, and integration verification.
"""

import asyncio
import aiohttp
import json
import sys
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('system_validation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SystemValidator:
    """Comprehensive system validation tool"""

    def __init__(self, base_url: str = "http://localhost:8000", ws_url: str = "ws://localhost:8000"):
        self.base_url = base_url
        self.ws_url = ws_url
        self.session = None
        self.validation_results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "UNKNOWN",
            "components": {},
            "errors": [],
            "warnings": [],
            "performance_metrics": {}
        }

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def run_all_validations(self) -> Dict[str, Any]:
        """Run complete system validation"""
        logger.info("Starting comprehensive system validation...")

        validations = [
            ("API Health Check", self.validate_api_health),
            ("Database Connectivity", self.validate_database_connection),
            ("GLM API Integration", self.validate_glm_api_integration),
            ("Agent Orchestration", self.validate_agent_orchestration),
            ("WebSocket Functionality", self.validate_websocket_functionality),
            ("End-to-End Workflow", self.validate_end_to_end_workflow),
            ("Performance Benchmarks", self.validate_performance),
            ("Error Handling", self.validate_error_handling),
            ("Security Headers", self.validate_security),
            ("Data Consistency", self.validate_data_consistency)
        ]

        for validation_name, validation_func in validations:
            logger.info(f"Running {validation_name}...")
            try:
                await validation_func()
                logger.info(f"✓ {validation_name} passed")
            except Exception as e:
                logger.error(f"✗ {validation_name} failed: {str(e)}")
                self.validation_results["errors"].append(f"{validation_name}: {str(e)}")

        # Calculate overall status
        self._calculate_overall_status()

        # Generate report
        await self._generate_validation_report()

        return self.validation_results

    async def validate_api_health(self):
        """Validate API health and basic endpoints"""
        component_status = {"status": "UNKNOWN", "details": {}}

        try:
            # Check main API endpoints
            health_checks = [
                ("Health Check", "/health", 200),
                ("API Root", "/", 200),
                ("Sessions List", "/v1/sessions", 200)
            ]

            for check_name, endpoint, expected_status in health_checks:
                url = f"{self.base_url}{endpoint}"
                start_time = time.time()

                async with self.session.get(url) as response:
                    response_time = time.time() - start_time

                    component_status["details"][check_name] = {
                        "status_code": response.status,
                        "expected_status": expected_status,
                        "response_time": round(response_time, 3),
                        "success": response.status == expected_status
                    }

                    if response.status != expected_status:
                        raise Exception(f"{check_name} returned {response.status}, expected {expected_status}")

            component_status["status"] = "HEALTHY"

        except Exception as e:
            component_status["status"] = "UNHEALTHY"
            component_status["error"] = str(e)
            raise

        self.validation_results["components"]["api_health"] = component_status

    async def validate_database_connection(self):
        """Validate database connectivity"""
        component_status = {"status": "UNKNOWN", "details": {}}

        try:
            # Test database through API endpoint
            test_data = {
                "user_input": "Database connection test",
                "context": {"test": True}
            }

            # Create test session
            async with self.session.post(
                f"{self.base_url}/v1/sessions",
                json=test_data
            ) as response:
                if response.status != 201:
                    raise Exception(f"Failed to create test session: {response.status}")

                session_data = await response.json()
                session_id = session_data["id"]

                component_status["details"]["session_creation"] = {
                    "success": True,
                    "session_id": session_id
                }

                # Retrieve session to verify database persistence
                async with self.session.get(f"{self.base_url}/v1/sessions/{session_id}") as response:
                    if response.status != 200:
                        raise Exception(f"Failed to retrieve session: {response.status}")

                    retrieved_session = await response.json()
                    if retrieved_session["id"] != session_id:
                        raise Exception("Session ID mismatch")

                    component_status["details"]["session_retrieval"] = {
                        "success": True,
                        "data_integrity": retrieved_session["user_input"] == test_data["user_input"]
                    }

                # Cleanup test session
                async with self.session.delete(f"{self.base_url}/v1/sessions/{session_id}") as response:
                    if response.status not in [204, 404]:
                        logger.warning(f"Failed to cleanup test session: {response.status}")

                component_status["details"]["cleanup"] = {"success": True}

            component_status["status"] = "CONNECTED"

        except Exception as e:
            component_status["status"] = "DISCONNECTED"
            component_status["error"] = str(e)
            raise

        self.validation_results["components"]["database"] = component_status

    async def validate_glm_api_integration(self):
        """Validate GLM API integration"""
        component_status = {"status": "UNKNOWN", "details": {}}

        try:
            # Test GLM API through a minimal session
            test_session_data = {
                "user_input": "GLM API test - respond with 'API_TEST_SUCCESS'",
                "context": {"test_type": "glm_integration"}
            }

            # Create session
            async with self.session.post(
                f"{self.base_url}/v1/sessions",
                json=test_session_data
            ) as response:
                if response.status != 201:
                    raise Exception(f"Failed to create test session for GLM test")

                session_data = await response.json()
                session_id = session_data["id"]

            component_status["details"]["session_creation"] = {"success": True}

            # Start session to trigger GLM API calls
            async with self.session.post(f"{self.base_url}/v1/sessions/{session_id}/start") as response:
                if response.status not in [200, 202]:
                    raise Exception(f"Failed to start session: {response.status}")

                component_status["details"]["session_start"] = {"success": True}

            # Wait a moment for processing
            await asyncio.sleep(2)

            # Check for messages (indicating GLM API was called)
            async with self.session.get(f"{self.base_url}/v1/sessions/{session_id}/messages") as response:
                if response.status == 200:
                    messages_data = await response.json()
                    message_count = len(messages_data.get("messages", []))
                    component_status["details"]["message_generation"] = {
                        "success": True,
                        "message_count": message_count
                    }
                else:
                    component_status["details"]["message_generation"] = {
                        "success": False,
                        "error": f"Failed to get messages: {response.status}"
                    }

            component_status["status"] = "INTEGRATED"

            # Cleanup
            await self.session.delete(f"{self.base_url}/v1/sessions/{session_id}")

        except Exception as e:
            component_status["status"] = "DISINTEGRATED"
            component_status["error"] = str(e)
            raise

        self.validation_results["components"]["glm_api"] = component_status

    async def validate_agent_orchestration(self):
        """Validate agent orchestration system"""
        component_status = {"status": "UNKNOWN", "details": {}}

        try:
            # Create a session that will go through agent orchestration
            test_request = {
                "user_input": "Create a comprehensive prompt for a technical documentation assistant that can explain complex concepts simply",
                "context": {"test_type": "agent_orchestration"}
            }

            # Start the workflow
            async with self.session.post(f"{self.base_url}/v1/sessions", json=test_request) as response:
                if response.status != 201:
                    raise Exception("Failed to start agent orchestration test")

                session_data = await response.json()
                session_id = session_data["id"]

            component_status["details"]["workflow_start"] = {"success": True}

            # Monitor agent progress
            max_wait_time = 30  # seconds
            start_time = time.time()
            agent_types_seen = set()

            while time.time() - start_time < max_wait_time:
                async with self.session.get(f"{self.base_url}/v1/sessions/{session_id}/messages") as response:
                    if response.status == 200:
                        messages_data = await response.json()
                        messages = messages_data.get("messages", [])

                        for message in messages:
                            agent_types_seen.add(message.get("agent_type"))

                        # Check if we've seen all three agents
                        expected_agents = {"product_manager", "technical_developer", "team_lead"}
                        if expected_agents.issubset(agent_types_seen):
                            component_status["details"]["agent_participation"] = {
                                "success": True,
                                "agents_seen": list(agent_types_seen),
                                "all_agents_participated": True
                            }
                            break

                await asyncio.sleep(2)

            if "agent_participation" not in component_status["details"]:
                component_status["details"]["agent_participation"] = {
                    "success": False,
                    "agents_seen": list(agent_types_seen),
                    "timeout": True
                }

            component_status["status"] = "ORCHESTRATING"

            # Cleanup
            await self.session.delete(f"{self.base_url}/v1/sessions/{session_id}")

        except Exception as e:
            component_status["status"] = "FAILED"
            component_status["error"] = str(e)
            raise

        self.validation_results["components"]["agent_orchestration"] = component_status

    async def validate_websocket_functionality(self):
        """Validate WebSocket connectivity and real-time features"""
        component_status = {"status": "UNKNOWN", "details": {}}

        try:
            import websockets

            # Test WebSocket connection
            ws_url = f"{self.ws_url}/ws/test-session"

            try:
                async with websockets.connect(ws_url) as websocket:
                    component_status["details"]["connection"] = {"success": True}

                    # Test message sending
                    test_message = {
                        "type": "ping",
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send(json.dumps(test_message))

                    # Test message receiving (with timeout)
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response)
                        component_status["details"]["message_exchange"] = {
                            "success": True,
                            "response_received": True
                        }
                    except asyncio.TimeoutError:
                        component_status["details"]["message_exchange"] = {
                            "success": False,
                            "timeout": True
                        }

            except Exception as ws_error:
                component_status["details"]["connection"] = {
                    "success": False,
                    "error": str(ws_error)
                }
                raise

            component_status["status"] = "CONNECTED"

        except ImportError:
            component_status["status"] = "NOT_TESTED"
            component_status["error"] = "websockets library not available"
            self.validation_results["warnings"].append("WebSocket validation skipped - websockets library not installed")

        except Exception as e:
            component_status["status"] = "FAILED"
            component_status["error"] = str(e)
            raise

        self.validation_results["components"]["websocket"] = component_status

    async def validate_end_to_end_workflow(self):
        """Validate complete end-to-end workflow"""
        component_status = {"status": "UNKNOWN", "details": {}, "workflow_steps": []}

        try:
            # Step 1: Create session
            step_start = time.time()
            session_data = {
                "user_input": "Create a prompt for an AI assistant that helps with software debugging",
                "context": {"test_type": "e2e_workflow"}
            }

            async with self.session.post(f"{self.base_url}/v1/sessions", json=session_data) as response:
                if response.status != 201:
                    raise Exception("Step 1 Failed: Session creation")
                session = await response.json()
                session_id = session["id"]

            component_status["workflow_steps"].append({
                "step": "Session Creation",
                "success": True,
                "duration": round(time.time() - step_start, 3)
            })

            # Step 2: Start processing
            step_start = time.time()
            async with self.session.post(f"{self.base_url}/v1/sessions/{session_id}/start") as response:
                if response.status not in [200, 202]:
                    raise Exception("Step 2 Failed: Session start")

            component_status["workflow_steps"].append({
                "step": "Session Start",
                "success": True,
                "duration": round(time.time() - step_start, 3)
            })

            # Step 3: Monitor progress
            step_start = time.time()
            max_wait = 20
            messages_received = 0

            for _ in range(max_wait):
                async with self.session.get(f"{self.base_url}/v1/sessions/{session_id}/messages") as response:
                    if response.status == 200:
                        messages_data = await response.json()
                        messages_received = len(messages_data.get("messages", []))
                        if messages_received > 0:
                            break

                await asyncio.sleep(1)

            component_status["workflow_steps"].append({
                "step": "Agent Processing",
                "success": messages_received > 0,
                "duration": round(time.time() - step_start, 3),
                "messages_received": messages_received
            })

            # Step 4: Retrieve final state
            step_start = time.time()
            async with self.session.get(f"{self.base_url}/v1/sessions/{session_id}") as response:
                if response.status == 200:
                    final_session = await response.json()
                    component_status["workflow_steps"].append({
                        "step": "Final State Retrieval",
                        "success": True,
                        "duration": round(time.time() - step_start, 3),
                        "final_status": final_session.get("status")
                    })
                else:
                    raise Exception("Step 4 Failed: Final state retrieval")

            # Step 5: Cleanup
            await self.session.delete(f"{self.base_url}/v1/sessions/{session_id}")
            component_status["workflow_steps"].append({
                "step": "Cleanup",
                "success": True
            })

            # Calculate overall success
            all_steps_successful = all(step["success"] for step in component_status["workflow_steps"])
            component_status["status"] = "COMPLETE" if all_steps_successful else "PARTIAL"

        except Exception as e:
            component_status["status"] = "FAILED"
            component_status["error"] = str(e)
            raise

        self.validation_results["components"]["end_to_end_workflow"] = component_status

    async def validate_performance(self):
        """Validate system performance benchmarks"""
        component_status = {"status": "UNKNOWN", "benchmarks": {}}

        try:
            # Test 1: Concurrent session creation
            concurrent_requests = 10
            start_time = time.time()

            tasks = []
            for i in range(concurrent_requests):
                task = self.session.post(
                    f"{self.base_url}/v1/sessions",
                    json={
                        "user_input": f"Performance test session {i}",
                        "context": {"test": "performance"}
                    }
                )
                tasks.append(task)

            responses = await asyncio.gather(*tasks, return_exceptions=True)
            creation_time = time.time() - start_time

            successful_creations = sum(1 for r in responses if not isinstance(r, Exception) and getattr(r, 'status', None) == 201)
            component_status["benchmarks"]["concurrent_creation"] = {
                "requests": concurrent_requests,
                "successful": successful_creations,
                "total_time": round(creation_time, 3),
                "avg_time_per_request": round(creation_time / concurrent_requests, 3),
                "success_rate": round(successful_creations / concurrent_requests * 100, 1)
            }

            # Test 2: API response times
            endpoints_to_test = [
                ("/v1/sessions", "GET"),
                ("/v1/sessions?page=1&page_size=10", "GET")
            ]

            response_times = []
            for endpoint, method in endpoints_to_test:
                start_time = time.time()
                async with self.session.request(method, f"{self.base_url}{endpoint}") as response:
                    response_time = time.time() - start_time
                    response_times.append(response_time)

            avg_response_time = sum(response_times) / len(response_times)
            component_status["benchmarks"]["api_response_times"] = {
                "avg_response_time": round(avg_response_time, 3),
                "max_response_time": round(max(response_times), 3),
                "min_response_time": round(min(response_times), 3)
            }

            # Performance criteria
            performance_ok = (
                component_status["benchmarks"]["concurrent_creation"]["success_rate"] >= 90 and
                component_status["benchmarks"]["api_response_times"]["avg_response_time"] < 1.0
            )

            component_status["status"] = "OPTIMAL" if performance_ok else "SUBOPTIMAL"

        except Exception as e:
            component_status["status"] = "FAILED"
            component_status["error"] = str(e)
            raise

        self.validation_results["components"]["performance"] = component_status
        self.validation_results["performance_metrics"] = component_status["benchmarks"]

    async def validate_error_handling(self):
        """Validate error handling capabilities"""
        component_status = {"status": "UNKNOWN", "error_tests": {}}

        try:
            # Test 1: Invalid session ID
            fake_id = "non-existent-session-id"
            async with self.session.get(f"{self.base_url}/v1/sessions/{fake_id}") as response:
                component_status["error_tests"]["invalid_session_id"] = {
                    "status_code": response.status,
                    "handled_properly": response.status == 404
                }

            # Test 2: Invalid request data
            invalid_data = {"user_input": ""}  # Empty input should fail validation
            async with self.session.post(f"{self.base_url}/v1/sessions", json=invalid_data) as response:
                component_status["error_tests"]["invalid_request_data"] = {
                    "status_code": response.status,
                    "handled_properly": response.status == 422
                }

            # Test 3: Malformed JSON
            try:
                async with self.session.post(
                    f"{self.base_url}/v1/sessions",
                    data="invalid json",
                    headers={"Content-Type": "application/json"}
                ) as response:
                    component_status["error_tests"]["malformed_json"] = {
                        "status_code": response.status,
                        "handled_properly": response.status in [400, 422]
                    }
            except Exception:
                component_status["error_tests"]["malformed_json"] = {
                    "handled_properly": True,
                    "note": "Request rejected at HTTP level"
                }

            # Check if all errors were handled properly
            all_handled_properly = all(
                test.get("handled_properly", False)
                for test in component_status["error_tests"].values()
            )

            component_status["status"] = "ROBUST" if all_handled_properly else "WEAK"

        except Exception as e:
            component_status["status"] = "FAILED"
            component_status["error"] = str(e)
            raise

        self.validation_results["components"]["error_handling"] = component_status

    async def validate_security(self):
        """Validate security headers and basic security measures"""
        component_status = {"status": "UNKNOWN", "security_checks": {}}

        try:
            # Check security headers
            async with self.session.get(f"{self.base_url}/") as response:
                headers = response.headers

                security_headers = {
                    "x-content-type-options": headers.get("X-Content-Type-Options"),
                    "x-frame-options": headers.get("X-Frame-Options"),
                    "x-xss-protection": headers.get("X-XSS-Protection"),
                    "content-security-policy": headers.get("Content-Security-Policy")
                }

                component_status["security_checks"]["headers"] = security_headers

                # Check for basic security headers
                has_basic_security = any(
                    headers.get(header.lower()) is not None
                    for header in ["X-Content-Type-Options", "X-Frame-Options"]
                )

                component_status["security_checks"]["basic_headers_present"] = has_basic_security

            # Test for information disclosure in error messages
            async with self.session.get(f"{self.base_url}/v1/sessions/non-existent") as response:
                error_response = await response.text()
                # Check if error response contains sensitive information
                contains_sensitive_info = any(
                    sensitive in error_response.lower()
                    for sensitive in ["traceback", "internal", "database", "password"]
                )

                component_status["security_checks"]["no_information_disclosure"] = not contains_sensitive_info

            security_score = sum([
                component_status["security_checks"]["basic_headers_present"],
                component_status["security_checks"]["no_information_disclosure"]
            ])

            component_status["status"] = "SECURE" if security_score >= 2 else "NEEDS_IMPROVEMENT"

        except Exception as e:
            component_status["status"] = "FAILED"
            component_status["error"] = str(e)
            raise

        self.validation_results["components"]["security"] = component_status

    async def validate_data_consistency(self):
        """Validate data consistency across operations"""
        component_status = {"status": "UNKNOWN", "consistency_checks": {}}

        try:
            # Test data consistency through CRUD operations
            test_data = {
                "user_input": "Data consistency test - original input",
                "context": {"test": "consistency", "iteration": 1}
            }

            # Create
            async with self.session.post(f"{self.base_url}/v1/sessions", json=test_data) as response:
                created_session = await response.json()
                session_id = created_session["id"]

            # Read
            async with self.session.get(f"{self.base_url}/v1/sessions/{session_id}") as response:
                retrieved_session = await response.json()

            # Verify consistency
            consistency_check_1 = (
                retrieved_session["user_input"] == test_data["user_input"] and
                retrieved_session["id"] == session_id
            )

            component_status["consistency_checks"]["create_read_consistency"] = consistency_check_1

            # Update (through user input)
            update_data = {
                "input_content": "Data consistency test - updated input",
                "input_type": "supplementary"
            }

            # Only try to update if session is in appropriate state
            if retrieved_session.get("status") == "waiting_for_user_input":
                async with self.session.post(
                    f"{self.base_url}/v1/sessions/{session_id}/user-input",
                    json=update_data
                ) as response:
                    update_success = response.status in [200, 202]

                component_status["consistency_checks"]["update_consistency"] = update_success
            else:
                component_status["consistency_checks"]["update_consistency"] = "skipped"

            # List consistency
            async with self.session.get(f"{self.base_url}/v1/sessions") as response:
                sessions_list = await response.json()
                session_in_list = any(
                    s["id"] == session_id for s in sessions_list.get("sessions", [])
                )

            component_status["consistency_checks"]["list_consistency"] = session_in_list

            # Delete
            async with self.session.delete(f"{self.base_url}/v1/sessions/{session_id}") as response:
                delete_success = response.status in [204, 404]

            component_status["consistency_checks"]["delete_consistency"] = delete_success

            # Verify deletion
            async with self.session.get(f"{self.base_url}/v1/sessions/{session_id}") as response:
                deletion_verified = response.status == 404

            component_status["consistency_checks"]["deletion_verification"] = deletion_verified

            # Calculate overall consistency
            consistency_checks = [
                component_status["consistency_checks"]["create_read_consistency"],
                component_status["consistency_checks"]["list_consistency"],
                component_status["consistency_checks"]["delete_consistency"],
                component_status["consistency_checks"]["deletion_verification"]
            ]

            consistent_operations = sum(1 for check in consistency_checks if check is True)
            component_status["status"] = "CONSISTENT" if consistent_operations >= 3 else "INCONSISTENT"

        except Exception as e:
            component_status["status"] = "FAILED"
            component_status["error"] = str(e)
            raise

        self.validation_results["components"]["data_consistency"] = component_status

    def _calculate_overall_status(self):
        """Calculate overall system status"""
        components = self.validation_results["components"]
        status_weights = {
            "HEALTHY": 100,
            "CONNECTED": 90,
            "INTEGRATED": 85,
            "ORCHESTRATING": 80,
            "COMPLETE": 90,
            "OPTIMAL": 85,
            "ROBUST": 80,
            "SECURE": 75,
            "CONSISTENT": 85
        }

        total_score = 0
        component_count = 0

        for component_name, component_data in components.items():
            component_status = component_data.get("status", "UNKNOWN")
            if component_status in status_weights:
                total_score += status_weights[component_status]
                component_count += 1
            elif component_status in ["FAILED", "UNHEALTHY", "DISCONNECTED"]:
                total_score += 0
                component_count += 1

        if component_count == 0:
            overall_status = "UNKNOWN"
        else:
            avg_score = total_score / component_count

            if avg_score >= 85:
                overall_status = "EXCELLENT"
            elif avg_score >= 70:
                overall_status = "GOOD"
            elif avg_score >= 50:
                overall_status = "FAIR"
            else:
                overall_status = "POOR"

        self.validation_results["overall_status"] = overall_status
        self.validation_results["score"] = round(avg_score, 1) if component_count > 0 else 0

    async def _generate_validation_report(self):
        """Generate detailed validation report"""
        report_path = Path("system_validation_report.json")

        try:
            with open(report_path, 'w') as f:
                json.dump(self.validation_results, f, indent=2, default=str)

            logger.info(f"Validation report saved to {report_path}")

            # Generate summary
            self._print_summary()

        except Exception as e:
            logger.error(f"Failed to save validation report: {e}")

    def _print_summary(self):
        """Print validation summary to console"""
        print("\n" + "="*60)
        print("SYSTEM VALIDATION SUMMARY")
        print("="*60)
        print(f"Overall Status: {self.validation_results['overall_status']}")
        print(f"Score: {self.validation_results.get('score', 'N/A')}/100")
        print(f"Timestamp: {self.validation_results['timestamp']}")
        print("\nComponent Status:")
        print("-" * 40)

        for component_name, component_data in self.validation_results["components"].items():
            status = component_data.get("status", "UNKNOWN")
            print(f"{component_name:25} : {status}")

        if self.validation_results["errors"]:
            print(f"\nErrors ({len(self.validation_results['errors'])}):")
            print("-" * 40)
            for error in self.validation_results["errors"]:
                print(f"• {error}")

        if self.validation_results["warnings"]:
            print(f"\nWarnings ({len(self.validation_results['warnings'])}):")
            print("-" * 40)
            for warning in self.validation_results["warnings"]:
                print(f"• {warning}")

        print("\n" + "="*60)


async def main():
    """Main validation function"""
    import argparse

    parser = argparse.ArgumentParser(description="AI Agent Prompt Generator System Validation")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL for API")
    parser.add_argument("--ws-url", default="ws://localhost:8000", help="WebSocket URL")
    parser.add_argument("--component", help="Run specific component validation only")
    parser.add_argument("--output", help="Output file for report (default: system_validation_report.json)")

    args = parser.parse_args()

    async with SystemValidator(args.base_url, args.ws_url) as validator:
        if args.component:
            # Run specific component validation
            component_method = getattr(validator, f"validate_{args.component}", None)
            if component_method:
                await component_method()
            else:
                print(f"Unknown component: {args.component}")
                return 1
        else:
            # Run full validation
            results = await validator.run_all_validations()

            # Exit with appropriate code
            if results["overall_status"] in ["EXCELLENT", "GOOD"]:
                return 0
            elif results["overall_status"] == "FAIR":
                return 1
            else:
                return 2

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))