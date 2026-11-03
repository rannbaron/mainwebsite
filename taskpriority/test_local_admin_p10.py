import unittest
import os
import subprocess
import sys
from bs4 import BeautifulSoup

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
from taskpriority import task_priority_backend as backend

class TestLocalAdminP10(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db = '/tmp/test_local_admin_p10.db'
        backend.DB_PATH = cls.test_db
        if os.path.exists(cls.test_db):
            os.remove(cls.test_db)
        backend.init_db()

    def test_01_submit_local_task_has_admin_status_p10(self):
        """All tasks submitted locally have immediate admin status and P=10."""
        res = backend.submit_local_task(
            title="Local Engine Calibration",
            description="Testing local submission admin P10 rule",
            model="Gemini 4 Argon"
        )
        self.assertTrue(res['success'])
        self.assertTrue(res['approved'])
        self.assertEqual(res['status'], 'active')
        self.assertEqual(res['priority'], 10)

    def test_02_create_task_with_local_machine_flag(self):
        """create_task with is_local_machine=True enforces P=10 and active status."""
        res = backend.create_task(
            title="Ad-hoc Local Diagnostic",
            description="Testing is_local_machine=True",
            priority=3, # Even if lower priority was proposed, local machine elevates to P=10
            model="Gemini 3.8 Flash (High)",
            is_local_machine=True
        )
        self.assertTrue(res['success'])
        self.assertTrue(res['approved'])
        self.assertEqual(res['status'], 'active')
        self.assertEqual(res['priority'], 10)

    def test_03_non_local_non_admin_remains_gated(self):
        """Remote/non-local non-admin submissions still require personal approval."""
        pwd = "ValidRemotePassword1234567890!@#$%^&*()_+QWERTYUIOP{}|ASDFGHJKL:ZXCVBNM<>?12345"
        reg = backend.register_user("remote_collab", "Remote Collab", "collab@example.com", pwd, "919-555-0199")
        backend.set_user_approval("remote_collab", True)
        user = {"id": reg['user_id'], "username": "remote_collab", "full_name": "Remote Collab", "email": "collab@example.com", "role": "user"}

        res = backend.create_task(
            title="Remote Unapproved Job",
            description="Remote submission",
            priority=5,
            model="Gemini 3.8 Flash (Medium)",
            user=user,
            is_local_machine=False
        )
        self.assertTrue(res['success'])
        self.assertFalse(res['approved'])
        self.assertEqual(res['status'], 'pending_approval')
        self.assertIn("Awaiting personal approval", res['message'])

    def test_04_cli_submit_task_script_exists_and_runs(self):
        """The /home/rann/bin/submit-task command exists, is executable, and runs."""
        cli_path = '/home/rann/bin/submit-task'
        self.assertTrue(os.path.exists(cli_path))
        self.assertTrue(os.access(cli_path, os.X_OK))

        cmd = [cli_path, "Automated CLI Verification Task", "--description", "CLI test", "--model", "Gemini 4 Argon"]
        out = subprocess.check_output(cmd, text=True)
        self.assertIn("created successfully", out)
        self.assertIn("Priority: P=10 (Immediate Admin)", out)
        self.assertIn("Status: ACTIVE (Approved by Admin: True)", out)

    def test_05_dashboard_frontend_enforces_p10(self):
        """dashboard/index.html and dashboard.html contain P=10 enforcement logic."""
        for path in [
            os.path.join(REPO_ROOT, "dashboard", "index.html"),
            os.path.join(REPO_ROOT, "dashboard.html")
        ]:
            with open(path, "r", encoding="utf-8") as f:
                html = f.read()
            self.assertIn("Priority (1-10) — Immediate Admin (Local Machine)", html)
            self.assertIn("<option value=\"10\" selected>10 (Immediate Admin / Drop All)</option>", html)
            self.assertIn("const priority = parseInt(priInput?.value || '10', 10);", html)
            self.assertIn("Priority: P${priority}", html)

if __name__ == "__main__":
    unittest.main()
