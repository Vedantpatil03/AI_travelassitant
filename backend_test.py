import requests
import sys
import json
from datetime import datetime
import time

class TravelBotAPITester:
    def __init__(self, base_url="https://itinerabot.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.session_id = f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

            print(f"   Status Code: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - {name}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(str(response_data)) < 500:
                        print(f"   Response: {response_data}")
                    elif isinstance(response_data, list) and len(response_data) > 0:
                        print(f"   Response: Found {len(response_data)} items")
                    return True, response_data
                except:
                    return True, response.text
            else:
                print(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ FAILED - Request timed out after {timeout} seconds")
            return False, {}
        except Exception as e:
            print(f"❌ FAILED - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        return self.run_test("Root API Endpoint", "GET", "", 200)

    def test_status_endpoints(self):
        """Test status check endpoints"""
        # Test POST status
        status_data = {"client_name": "test_client"}
        success, response = self.run_test("Create Status Check", "POST", "status", 200, status_data)
        
        if success:
            # Test GET status
            self.run_test("Get Status Checks", "GET", "status", 200)
        
        return success

    def test_chat_endpoint(self):
        """Test the chat endpoint with travel queries"""
        print("\n🧳 Testing Chat Functionality...")
        
        # Test basic travel query
        chat_data = {
            "message": "Plan a trip to Paris for 5 days",
            "session_id": self.session_id,
            "budget": "$2000-3000",
            "location": "Paris, France",
            "duration": "5 days",
            "travelers": 2
        }
        
        success, response = self.run_test(
            "Chat with Travel Context", 
            "POST", 
            "chat", 
            200, 
            chat_data,
            timeout=60  # Longer timeout for AI response
        )
        
        if success and isinstance(response, dict):
            if 'message' in response and response['message']:
                print(f"   AI Response Length: {len(response['message'])} characters")
                print(f"   AI Response Preview: {response['message'][:200]}...")
                return True
            else:
                print("❌ Chat response missing 'message' field")
                return False
        
        return success

    def test_chat_without_context(self):
        """Test chat endpoint without travel context"""
        chat_data = {
            "message": "What are some popular travel destinations?",
            "session_id": self.session_id
        }
        
        return self.run_test(
            "Chat without Context", 
            "POST", 
            "chat", 
            200, 
            chat_data,
            timeout=60
        )

    def test_image_generation(self):
        """Test trip image generation"""
        print("\n🖼️ Testing Image Generation...")
        
        image_data = {
            "prompt": "Paris Eiffel Tower beautiful sunset",
            "session_id": self.session_id
        }
        
        success, response = self.run_test(
            "Generate Trip Image", 
            "POST", 
            "generate-trip-image", 
            200, 
            image_data,
            timeout=120  # Very long timeout for image generation
        )
        
        if success and isinstance(response, dict):
            if 'image_base64' in response and response['image_base64']:
                print(f"   Image Generated: {len(response['image_base64'])} base64 characters")
                return True
            else:
                print("❌ Image response missing 'image_base64' field")
                return False
        
        return success

    def test_chat_history(self):
        """Test chat history retrieval"""
        print("\n📚 Testing Chat History...")
        
        success, response = self.run_test(
            "Get Chat History", 
            "GET", 
            f"chat-history/{self.session_id}", 
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} messages in history")
            if len(response) > 0:
                print(f"   Sample message: {response[0] if len(str(response[0])) < 200 else str(response[0])[:200]}")
            return True
        
        return success

    def test_error_handling(self):
        """Test error handling with invalid requests"""
        print("\n⚠️ Testing Error Handling...")
        
        # Test invalid chat request
        invalid_chat = {"message": "", "session_id": ""}
        self.run_test("Invalid Chat Request", "POST", "chat", 422, invalid_chat)
        
        # Test invalid image request  
        invalid_image = {"prompt": "", "session_id": ""}
        self.run_test("Invalid Image Request", "POST", "generate-trip-image", 422, invalid_image)
        
        # Test non-existent chat history
        self.run_test("Non-existent Chat History", "GET", "chat-history/nonexistent", 200)

    def run_comprehensive_test(self):
        """Run all tests in sequence"""
        print("🚀 Starting AI Travel Assistant API Tests")
        print(f"Testing against: {self.base_url}")
        print(f"Session ID: {self.session_id}")
        print("=" * 60)

        # Test basic connectivity
        if not self.test_root_endpoint():
            print("❌ Root endpoint failed - stopping tests")
            return False

        # Test status endpoints
        self.test_status_endpoints()

        # Test core chat functionality
        if not self.test_chat_endpoint():
            print("❌ Core chat functionality failed")
            return False

        # Test chat without context
        self.test_chat_without_context()

        # Test image generation (this might fail with test API key)
        self.test_image_generation()

        # Test chat history
        self.test_chat_history()

        # Test error handling
        self.test_error_handling()

        # Print final results
        print("\n" + "=" * 60)
        print(f"📊 FINAL RESULTS: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL TESTS PASSED!")
            return True
        else:
            failed = self.tests_run - self.tests_passed
            print(f"⚠️ {failed} tests failed")
            return False

def main():
    tester = TravelBotAPITester()
    success = tester.run_comprehensive_test()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())