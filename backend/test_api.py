#!/usr/bin/env python3
"""
API Testing Script for Refactored Backend
Tests all major endpoints to ensure everything works correctly
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000/api"
TEST_USERNAME = "admin"  # Change to your test user
TEST_PASSWORD = "admin"  # Change to your test password


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_warning(message):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")


def print_info(message):
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")


class APITester:
    def __init__(self):
        self.token = None
        self.user = None
        self.test_floor_id = None
        self.test_log_id = None

    def login(self):
        """Test authentication login"""
        print_info("Testing login...")
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={
                    "username": TEST_USERNAME,
                    "password": TEST_PASSWORD
                }
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get('token')
                self.user = data.get('user')
                print_success(
                    f"Login successful as {self.user.get('username')} ({self.user.get('role')})")
                return True
            else:
                print_error(
                    f"Login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print_error(f"Login error: {str(e)}")
            return False

    def get_headers(self):
        """Get authorization headers"""
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

    def test_floors(self):
        """Test floors endpoint"""
        print_info("\nTesting floors endpoint...")
        try:
            response = requests.get(
                f"{BASE_URL}/floors",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                floors = response.json()
                print_success(f"Retrieved {len(floors)} floors")
                if floors:
                    self.test_floor_id = floors[0]['id']
                    print_info(
                        f"Using floor {floors[0]['name']} (ID: {self.test_floor_id}) for tests")
                return True
            else:
                print_error(f"Floors request failed: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Floors test error: {str(e)}")
            return False

    def test_work_logs(self):
        """Test work logs endpoints"""
        print_info("\nTesting work logs endpoints...")

        # Get all work logs
        try:
            response = requests.get(
                f"{BASE_URL}/work-logs",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                logs = response.json()
                print_success(f"Retrieved {len(logs)} work logs")
                if logs:
                    self.test_log_id = logs[0]['id']
                    print_info(
                        f"Sample log: {logs[0].get('worker_name')} - {logs[0].get('work_type')}")
                return True
            else:
                print_error(
                    f"Work logs request failed: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Work logs test error: {str(e)}")
            return False

    def test_dashboard_stats(self):
        """Test dashboard statistics endpoint"""
        print_info("\nTesting dashboard statistics...")
        try:
            response = requests.get(
                f"{BASE_URL}/work-logs/dashboard",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                stats = response.json()
                print_success(
                    f"Dashboard stats: {stats.get('total_logs')} total logs")
                print_info(f"Recent logs: {stats.get('recent_logs')}")
                return True
            else:
                print_error(f"Dashboard stats failed: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Dashboard stats error: {str(e)}")
            return False

    def test_tiles(self):
        """Test tiles endpoints"""
        print_info("\nTesting tiles endpoints...")

        if not self.test_floor_id:
            print_warning("No floor ID available, skipping tiles test")
            return False

        try:
            response = requests.get(
                f"{BASE_URL}/tiles/status/{self.test_floor_id}",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                status = response.json()
                tiles_exist = status.get('tiles_exist', False)
                if tiles_exist:
                    print_success(
                        f"Tiles exist for floor {self.test_floor_id}")
                else:
                    print_warning(
                        f"Tiles do not exist for floor {self.test_floor_id}")
                return True
            else:
                print_error(f"Tiles status failed: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Tiles test error: {str(e)}")
            return False

    def test_critical_sectors(self):
        """Test critical sectors endpoints"""
        print_info("\nTesting critical sectors endpoints...")

        try:
            response = requests.get(
                f"{BASE_URL}/critical-sectors",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                sectors = response.json()
                print_success(f"Retrieved {len(sectors)} critical sectors")
                return True
            else:
                print_error(f"Critical sectors failed: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Critical sectors error: {str(e)}")
            return False

    def test_notifications(self):
        """Test notifications endpoints"""
        print_info("\nTesting notifications endpoints...")

        try:
            response = requests.get(
                f"{BASE_URL}/notifications",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                notifications = response.json()
                print_success(f"Retrieved {len(notifications)} notifications")
                return True
            else:
                print_error(f"Notifications failed: {response.status_code}")
                try:
                    error_detail = response.json()
                    print_error(f"Error details: {error_detail}")
                except:
                    print_error(f"Response text: {response.text}")
                return False
        except Exception as e:
            print_error(f"Notifications error: {str(e)}")
            return False

    def test_assignments(self):
        """Test assignments endpoints"""
        print_info("\nTesting assignments endpoints...")

        try:
            response = requests.get(
                f"{BASE_URL}/assignments",
                headers=self.get_headers()
            )

            if response.status_code == 200:
                assignments = response.json()
                print_success(f"Retrieved {len(assignments)} assignments")
                return True
            else:
                print_error(f"Assignments failed: {response.status_code}")
                try:
                    error_detail = response.json()
                    print_error(f"Error details: {error_detail}")
                except:
                    print_error(f"Response text: {response.text}")
                return False
        except Exception as e:
            print_error(f"Assignments error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all API tests"""
        print("=" * 60)
        print("API Test Suite - Refactored Backend")
        print("=" * 60)

        results = {
            'login': False,
            'floors': False,
            'work_logs': False,
            'dashboard': False,
            'tiles': False,
            'sectors': False,
            'notifications': False,
            'assignments': False
        }

        # Login first
        results['login'] = self.login()
        if not results['login']:
            print_error("\nLogin failed. Cannot proceed with other tests.")
            return results

        # Run all tests
        results['floors'] = self.test_floors()
        results['work_logs'] = self.test_work_logs()
        results['dashboard'] = self.test_dashboard_stats()
        results['tiles'] = self.test_tiles()
        results['sectors'] = self.test_critical_sectors()
        results['notifications'] = self.test_notifications()
        results['assignments'] = self.test_assignments()

        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)

        passed = sum(1 for v in results.values() if v)
        total = len(results)

        for test_name, passed_test in results.items():
            status = "PASS" if passed_test else "FAIL"
            color = Colors.GREEN if passed_test else Colors.RED
            print(f"{color}{status}{Colors.END} - {test_name}")

        print("\n" + "=" * 60)
        success_rate = (passed / total) * 100
        print(f"Results: {passed}/{total} tests passed ({success_rate:.1f}%)")
        print("=" * 60)

        return results


def main():
    """Main test function"""
    tester = APITester()
    results = tester.run_all_tests()

    # Exit with appropriate code
    all_passed = all(results.values())
    exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
