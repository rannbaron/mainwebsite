#!/usr/bin/env python3
"""
Task Priority Dashboard Defensive Security & Penetration Audit Suite
=====================================================================
Executes rigorous penetration testing across OWASP Top 10 vectors:
1. Password Complexity & Entropy Boundary Testing
2. Plaintext Leakage & Salted Hash Storage Verification
3. SQL Injection (SQLi) Parameterized Immunity Testing
4. Multi-Factor Authentication (2FA) Bypass & Brute-Force Testing
5. Broken Object Level Authorization (BOLA / IDOR) & Approval Gating
6. Non-Admin Task Initiation Approval Interception
7. Zero-Search Engine Reconnaissance & Indexing Shielding
"""

import os
import sys
import secrets
import sqlite3
import unittest

# Import backend module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import task_priority_backend as backend

class TestTaskPrioritySecurityAudit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Use isolated test database in /tmp
        backend.DB_PATH = '/tmp/test_task_priority_audit.db'
        if os.path.exists(backend.DB_PATH):
            os.remove(backend.DB_PATH)
        backend.init_db()

        # Seed test admin account
        cls.valid_admin_pwd = "SuperSecretAdminPassword1234567890!@#$%^&*()_+QWERTYUIOP{}|ASDFGHJKL:ZXCVBNM<>?12345"
        res = backend.register_user("admin_rann", "Rann Bar-On", "rann@rannbar-on.com", cls.valid_admin_pwd, "919-660-2800")
        cls.admin_user_id = res['user_id']
        backend.set_user_approval("admin_rann", True)
        backend.seed_default_tasks(cls.admin_user_id)

    # --------------------------------------------------------------------------
    # 1. PASSWORD COMPLEXITY & ENTROPY TESTS
    # --------------------------------------------------------------------------
    def test_01_password_length_boundary(self):
        """Rejects passwords under 50 characters."""
        short_49 = "Aa1!" * 12 + "1"  # 49 chars
        ok, msg = backend.validate_password_strength(short_49)
        self.assertFalse(ok)
        self.assertIn("at least 50 characters", msg)

        exact_50 = "Aa1!" * 12 + "Aa1!"  # 52 chars
        ok, _ = backend.validate_password_strength(exact_50)
        self.assertTrue(ok)

    def test_02_password_character_diversity(self):
        """Enforces mix of uppercase, lowercase, numbers, and symbols."""
        no_upper = "a" * 40 + "123456789!@#$%^&*"
        ok, msg = backend.validate_password_strength(no_upper)
        self.assertFalse(ok)
        self.assertIn("uppercase letter", msg)

        no_lower = "A" * 40 + "123456789!@#$%^&*"
        ok, msg = backend.validate_password_strength(no_lower)
        self.assertFalse(ok)
        self.assertIn("lowercase letter", msg)

        no_num = "Aa" * 25 + "!@#$%^&*()_+{}:<>?"
        ok, msg = backend.validate_password_strength(no_num)
        self.assertFalse(ok)
        self.assertIn("number", msg)

        no_sym = "Aa1" * 20
        ok, msg = backend.validate_password_strength(no_sym)
        self.assertFalse(ok)
        self.assertIn("special character", msg)

    # --------------------------------------------------------------------------
    # 2. ZERO PLAINTEXT PASSWORD STORAGE VERIFICATION
    # --------------------------------------------------------------------------
    def test_03_zero_plaintext_storage(self):
        """Ensures plaintext passwords never exist anywhere in the database."""
        test_pwd = "P@ssw0rd_Testing_Plaintext_Storage_Zero_Tolerance_Rule_50Chars!12345"
        res = backend.register_user("bob_auditor", "Bob Auditor", "bob@example.com", test_pwd, "555-0199")
        self.assertTrue(res['success'])

        conn = sqlite3.connect(backend.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT username, password_hash, salt FROM users WHERE username = 'bob_auditor'")
        row = cursor.fetchone()
        conn.close()

        stored_hash = row[1]
        stored_salt = row[2]

        # Verify plaintext does NOT appear in hash or salt
        self.assertNotIn(test_pwd, stored_hash)
        self.assertNotIn(test_pwd, stored_salt)
        self.assertTrue(stored_hash.startswith("$2b$12$") or len(stored_hash) >= 64)

    def test_04_unique_salt_uniqueness(self):
        """Ensures identical passwords produce distinct hashes via per-user salts."""
        pwd = "IdenticalPasswordForTwoDifferentAccounts_SecurityAuditTest_50Chars!123"
        res1 = backend.register_user("user_alpha", "User Alpha", "alpha@example.com", pwd, "555-0101")
        res2 = backend.register_user("user_beta", "User Beta", "beta@example.com", pwd, "555-0102")
        self.assertTrue(res1['success'])
        self.assertTrue(res2['success'])

        conn = sqlite3.connect(backend.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, salt FROM users WHERE username IN ('user_alpha', 'user_beta')")
        rows = cursor.fetchall()
        conn.close()

        self.assertNotEqual(rows[0][0], rows[1][0], "Hashes must differ due to cryptographic salt!")
        self.assertNotEqual(rows[0][1], rows[1][1], "Salts must be cryptographically unique!")

    # --------------------------------------------------------------------------
    # 3. SQL INJECTION (SQLi) IMMUNITY
    # --------------------------------------------------------------------------
    def test_05_sql_injection_defense(self):
        """Attacks username and login with classic SQL injection vectors."""
        sqli_payloads = [
            "' OR '1'='1",
            "admin' --",
            "' UNION SELECT 1, 'admin', 'hash', 'salt', 'approved', 'admin' --",
            "'; DROP TABLE users; --",
            "admin' /*",
        ]
        for payload in sqli_payloads:
            res = backend.authenticate_user_step1(payload, "SomeDummyPassword1234567890!@#$%^&*()_AaBbCcDdEeFfGgHh")
            self.assertFalse(res['success'], f"SQLi payload breached authentication: {payload}")

        # Verify users table still exists and is untouched
        conn = sqlite3.connect(backend.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertGreater(count, 0)

    # --------------------------------------------------------------------------
    # 4. MULTI-FACTOR AUTHENTICATION (2FA) & BRUTE-FORCE TESTS
    # --------------------------------------------------------------------------
    def test_06_two_factor_auth_challenge(self):
        """Validates 2FA flow: Step 1 requires Step 2 token verification."""
        auth1 = backend.authenticate_user_step1("admin_rann", self.valid_admin_pwd)
        self.assertTrue(auth1['success'])
        self.assertEqual(auth1['step'], '2FA_REQUIRED')
        user_id = auth1['user_id']

        # Query database to retrieve active token hash
        conn = sqlite3.connect(backend.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, expires_at FROM two_factor_tokens WHERE user_id = ? AND consumed = 0", (user_id,))
        token_row = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(token_row)

    def test_07_two_factor_brute_force_lockout(self):
        """Enforces max 3 failed 2FA attempts before automatic token invalidation."""
        auth1 = backend.authenticate_user_step1("admin_rann", self.valid_admin_pwd)
        user_id = auth1['user_id']

        # Attempt 1: Wrong code
        ok1, msg1 = backend.verify_2fa_challenge(user_id, "000000")
        self.assertFalse(ok1)
        self.assertIn("attempt(s) remaining", msg1)

        # Attempt 2: Wrong code
        ok2, msg2 = backend.verify_2fa_challenge(user_id, "111111")
        self.assertFalse(ok2)

        # Attempt 3: Wrong code -> triggers invalidation
        ok3, msg3 = backend.verify_2fa_challenge(user_id, "222222")
        self.assertFalse(ok3)

        # Attempt 4: Should now be locked out / token expired
        ok4, msg4 = backend.verify_2fa_challenge(user_id, "333333")
        self.assertFalse(ok4)
        self.assertTrue("No active 2FA challenge" in msg4 or "invalidated" in msg4 or "Too many" in msg4)

    # --------------------------------------------------------------------------
    # 5. AUTHORIZATION & PERSONAL APPROVAL GATING (BOLA / IDOR)
    # --------------------------------------------------------------------------
    def test_08_unapproved_user_access_blocked(self):
        """Unapproved user is permanently gated from obtaining session tokens."""
        pwd = "ValidPasswordMeetingAllComplexityRules1234567890!@#$%^&*()_+"
        reg = backend.register_user("unapproved_alice", "Alice Smith", "alice@example.com", pwd, "555-0300")
        self.assertTrue(reg['success'])
        self.assertEqual(reg['status'], 'pending_approval')

        # Attempt to log in while unapproved
        auth = backend.authenticate_user_step1("unapproved_alice", pwd)
        self.assertFalse(auth['success'])
        self.assertIn("pending administrator approval", auth['error'])

    # --------------------------------------------------------------------------
    # 6. NON-ADMIN TASK INITIATION APPROVAL INTERCEPTION
    # --------------------------------------------------------------------------
    def test_09_task_initiation_approval_interception(self):
        """Non-admin user task creation is gated until Rann gives personal approval."""
        # Approve user first so they can log in
        backend.set_user_approval("bob_auditor", True)
        user = {"id": 2, "username": "bob_auditor", "full_name": "Bob Auditor", "email": "bob@example.com", "role": "user"}

        # Bob creates a task
        res = backend.create_task("Non-Admin Proposes New Experiment", "Details of new experiment", 7, "Claude 3.5 Sonnet", 10, user)
        self.assertTrue(res['success'])
        self.assertFalse(res['approved'])
        self.assertEqual(res['status'], 'pending_approval')
        self.assertIn("Awaiting personal approval from Rann", res['message'])

        # Admin approves the task
        approved = backend.approve_task(res['task_id'])
        self.assertTrue(approved)

    # --------------------------------------------------------------------------
    # 7. SEARCH ENGINE SHIELDING (ZERO INDEXING)
    # --------------------------------------------------------------------------
    def test_10_robots_txt_disallow_rules(self):
        """Verifies robots.txt explicitly disallows dashboard and taskpriority paths."""
        robots_path = '/home/rann/src/website/mainwebsite/robots.txt'
        self.assertTrue(os.path.exists(robots_path))
        with open(robots_path, 'r') as f:
            content = f.read()
        self.assertIn("Disallow: /dashboard/", content)
        self.assertIn("Disallow: /*dashboard*", content)
        self.assertIn("Disallow: /taskpriority/", content)
        self.assertIn("Disallow: /*taskpriority*", content)

    # --------------------------------------------------------------------------
    # 8. TASK DELETION & REACTIVE AUDITING
    # --------------------------------------------------------------------------
    def test_11_delete_task_functionality(self):
        """Verifies task deletion, database removal, and audit logging."""
        create_res = backend.create_task(
            "Test Task For Deletion", "Scope details", priority=6,
            user={"id": self.admin_user_id, "username": "admin_rann", "role": "admin"}
        )
        self.assertTrue(create_res['success'])
        task_id = create_res['task_id']

        # Confirm task exists
        conn = sqlite3.connect(backend.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
        self.assertIsNotNone(cursor.fetchone())
        conn.close()

        # Delete task
        del_ok = backend.delete_task(task_id, user={"id": self.admin_user_id, "username": "admin_rann"})
        self.assertTrue(del_ok)

        # Confirm task no longer exists
        conn = sqlite3.connect(backend.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
        self.assertIsNone(cursor.fetchone())

        # Verify audit log contains TASK_DELETED
        cursor.execute("SELECT details FROM audit_logs WHERE event_type = 'TASK_DELETED' ORDER BY id DESC LIMIT 1")
        audit_row = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(audit_row)
        self.assertIn(str(task_id), audit_row[0])

        # Attempting to delete already-deleted task returns False
        del_again = backend.delete_task(task_id)
        self.assertFalse(del_again)

    # --------------------------------------------------------------------------
    # 9. PRIORITY-BASED MODEL DEFAULTS & AGENT TIERING
    # --------------------------------------------------------------------------
    def test_12_priority_model_defaults_and_agent_tiering(self):
        """
        Enforces tiering architecture:
        - P 8-10: Gemini 4 Argon, dedicated agent 'argon-agent-<id>'
        - P 5-7:  Gemini 3.8 Flash (High), dedicated agent 'flash-high-agent-<id>'
        - P 1-4:  Gemini 3.8 Flash (Medium), shared agent 'shared-flash-medium-coordinator'
        """
        # Test helper functions
        for p in [10, 9, 8]:
            self.assertEqual(backend.get_default_model_for_priority(p), "Gemini 4 Argon")
            self.assertEqual(backend.get_assigned_agent(p, 42), "argon-agent-42")

        for p in [7, 6, 5]:
            self.assertEqual(backend.get_default_model_for_priority(p), "Gemini 3.8 Flash (High)")
            self.assertEqual(backend.get_assigned_agent(p, 42), "flash-high-agent-42")

        for p in [4, 3, 2, 1]:
            self.assertEqual(backend.get_default_model_for_priority(p), "Gemini 3.8 Flash (Medium)")
            self.assertEqual(backend.get_assigned_agent(p, 42), "shared-flash-medium-coordinator")

        # Test creation with omitted model
        admin_u = {"id": self.admin_user_id, "username": "admin_rann", "role": "admin"}
        t10 = backend.create_task("P10 Task", priority=10, user=admin_u)
        self.assertEqual(t10['model'], "Gemini 4 Argon")
        self.assertEqual(t10['assigned_agent'], f"argon-agent-{t10['task_id']}")

        t6 = backend.create_task("P6 Task", priority=6, user=admin_u)
        self.assertEqual(t6['model'], "Gemini 3.8 Flash (High)")
        self.assertEqual(t6['assigned_agent'], f"flash-high-agent-{t6['task_id']}")

        t3 = backend.create_task("P3 Task", priority=3, user=admin_u)
        self.assertEqual(t3['model'], "Gemini 3.8 Flash (Medium)")
        self.assertEqual(t3['assigned_agent'], "shared-flash-medium-coordinator")

    # --------------------------------------------------------------------------
    # 10. DYNAMIC PRIORITY & MODEL TIER UPDATES
    # --------------------------------------------------------------------------
    def test_13_dynamic_priority_and_model_updates(self):
        """Updating priority or model dynamically re-assigns the agent."""
        admin_u = {"id": self.admin_user_id, "username": "admin_rann", "role": "admin"}
        task = backend.create_task("Dynamic Upgrade Task", priority=3, user=admin_u)
        task_id = task['task_id']
        self.assertEqual(task['assigned_agent'], "shared-flash-medium-coordinator")

        # Upgrade to P9 -> automatically switches to Argon and dedicated argon agent
        res_up = backend.update_task_priority_and_model(task_id, new_priority=9, user=admin_u)
        self.assertTrue(res_up['success'])
        self.assertEqual(res_up['model'], "Gemini 4 Argon")
        self.assertEqual(res_up['assigned_agent'], f"argon-agent-{task_id}")

        # Downgrade to P6 -> automatically switches to Flash High and dedicated flash-high agent
        res_mid = backend.update_task_priority_and_model(task_id, new_priority=6, user=admin_u)
        self.assertTrue(res_mid['success'])
        self.assertEqual(res_mid['model'], "Gemini 3.8 Flash (High)")
        self.assertEqual(res_mid['assigned_agent'], f"flash-high-agent-{task_id}")

        # Downgrade to P2 -> automatically switches to Flash Medium and shared coordinator
        res_low = backend.update_task_priority_and_model(task_id, new_priority=2, user=admin_u)
        self.assertTrue(res_low['success'])
        self.assertEqual(res_low['model'], "Gemini 3.8 Flash (Medium)")
        self.assertEqual(res_low['assigned_agent'], "shared-flash-medium-coordinator")

    # --------------------------------------------------------------------------
    # 11. CLI --delete-task FLAG VERIFICATION
    # --------------------------------------------------------------------------
    def test_14_cli_delete_task(self):
        """Verifies CLI flag --delete-task successfully removes tasks."""
        import subprocess
        admin_u = {"id": self.admin_user_id, "username": "admin_rann", "role": "admin"}
        task = backend.create_task("CLI Delete Candidate", priority=5, user=admin_u)
        t_id = task['task_id']

        cli_res = subprocess.run(
            [sys.executable, backend.__file__, "--delete-task", str(t_id)],
            capture_output=True,
            text=True,
            env=dict(os.environ, TASK_PRIORITY_DB_PATH=backend.DB_PATH)
        )
        self.assertEqual(cli_res.returncode, 0)
        self.assertIn(f"Task #{t_id} deleted successfully", cli_res.stdout)

        # Deleting again should fail with code 1
        cli_res_fail = subprocess.run(
            [sys.executable, backend.__file__, "--delete-task", str(t_id)],
            capture_output=True,
            text=True,
            env=dict(os.environ, TASK_PRIORITY_DB_PATH=backend.DB_PATH)
        )
        self.assertEqual(cli_res_fail.returncode, 1)

if __name__ == '__main__':
    unittest.main()

