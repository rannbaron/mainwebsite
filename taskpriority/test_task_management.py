import unittest
import os
import re
from bs4 import BeautifulSoup

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_INDEX = os.path.join(REPO_ROOT, "dashboard", "index.html")
DASHBOARD_HTML = os.path.join(REPO_ROOT, "dashboard.html")

class TestTaskManagement(unittest.TestCase):
    def setUp(self):
        with open(DASHBOARD_INDEX, "r", encoding="utf-8") as f:
            self.index_html = f.read()
        with open(DASHBOARD_HTML, "r", encoding="utf-8") as f:
            self.root_html = f.read()
        self.soup = BeautifulSoup(self.index_html, "html.parser")

    def test_files_synchronized(self):
        """dashboard/index.html and dashboard.html must be 100% identical."""
        self.assertEqual(self.index_html, self.root_html)

    def test_filter_toolbar_elements(self):
        """Dashboard must contain search input and all 4 filter dropdowns plus reset button."""
        search_input = self.soup.find("input", {"id": "taskSearchInput"})
        self.assertIsNotNone(search_input, "Missing #taskSearchInput")

        filter_priority = self.soup.find("select", {"id": "filterPriority"})
        self.assertIsNotNone(filter_priority, "Missing #filterPriority")
        priority_options = [opt.get_text(strip=True) for opt in filter_priority.find_all("option")]
        self.assertIn("All Priorities", priority_options)
        self.assertIn("P10 Critical", priority_options)

        filter_completion = self.soup.find("select", {"id": "filterCompletion"})
        self.assertIsNotNone(filter_completion, "Missing #filterCompletion")

        filter_status = self.soup.find("select", {"id": "filterStatus"})
        self.assertIsNotNone(filter_status, "Missing #filterStatus")

        filter_model = self.soup.find("select", {"id": "filterModel"})
        self.assertIsNotNone(filter_model, "Missing #filterModel")

        count_badge = self.soup.find("div", {"id": "taskCountBadge"})
        self.assertIsNotNone(count_badge, "Missing #taskCountBadge")

    def test_sortable_column_headers(self):
        """All 6 column headers must have sort handlers and sort icons."""
        expected_cols = ["id", "priority", "title", "model", "progress", "status"]
        for col in expected_cols:
            th = self.soup.find("th", {"id": f"th-{col}"})
            self.assertIsNotNone(th, f"Missing #th-{col}")
            self.assertIn("sortable-th", th.get("class", []))
            self.assertIn(f"setSortColumn('{col}')", th.get("onclick", ""))

    def test_javascript_task_functions_present(self):
        """Crucial task manipulation functions must exist in the client JavaScript."""
        required_signatures = [
            "function changeTaskPriority(",
            "function changeTaskModel(",
            "function setSortColumn(",
            "function getFilteredAndSortedTasks(",
            "function renderTasksTable(",
            "function applyFiltersAndSort(",
            "function resetFilters(",
            "function handleCreateTask(",
            "function updateStatCards(",
            "const TASKS_STORAGE_KEY = 'task_dashboard_tasks_v1';",
        ]
        for sig in required_signatures:
            self.assertIn(sig, self.index_html, f"Missing JavaScript signature: {sig}")

    def test_stat_cards_ids(self):
        """Stat cards must have IDs for reactive real-time updates."""
        self.assertIsNotNone(self.soup.find(id="statCardTotal"))
        self.assertIsNotNone(self.soup.find(id="statCardP10"))
        self.assertIsNotNone(self.soup.find(id="statCardP89"))

    def test_default_tasks_count(self):
        """DEFAULT_TASKS must include all 17 system tasks."""
        matches = re.findall(r'id:\s*(\d+),\s*priority:\s*(\d+)', self.index_html)
        self.assertEqual(len(matches), 17, f"Expected 17 tasks in DEFAULT_TASKS, got {len(matches)}")

    def test_delete_task_action_and_agent_badges(self):
        """Verify delete task button and agent badges exist."""
        self.assertIn("function deleteTask(", self.index_html)
        self.assertIn("function getAssignedAgentBadge(", self.index_html)
        self.assertIn("btn-delete", self.index_html)
        self.assertIn("Dedicated Argon Agent", self.index_html)
        self.assertIn("Dedicated Flash High Agent", self.index_html)
        self.assertIn("Shared Flash Medium Agent", self.index_html)

    def test_model_defaults_by_priority(self):
        """Verify priorities 8-10 default to Argon, 5-7 to Flash High, 1-4 to Flash Medium."""
        self.assertIn("if (newPriority >= 8) {", self.index_html)
        self.assertIn("task.model = 'Gemini 4 Argon';", self.index_html)
        self.assertIn("task.model = 'Gemini 3.8 Flash (High)';", self.index_html)
        self.assertIn("task.model = 'Gemini 3.8 Flash (Medium)';", self.index_html)

if __name__ == "__main__":
    unittest.main()
