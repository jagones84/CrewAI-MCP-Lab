import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from utils.comfy_check import check_comfyui_connection
from utils.llm_controllers import OllamaController
from agents import MarketingAgents
from tasks import MarketingTasks

class TestComponents(unittest.TestCase):

    def test_check_comfyui_connection_failure(self):
        """Test that the connection check returns False when server is down."""
        # We assume ComfyUI is NOT running on a random port
        result = check_comfyui_connection(port=12345)
        self.assertFalse(result)

    @patch('agents.MarketingAgents.market_researcher')
    def test_agent_initialization(self, mock_researcher):
        """Test that agents can be initialized with config."""
        config = {'llm': {'provider': 'openai', 'model': 'gpt-4o'}}
        agents = MarketingAgents(config)
        self.assertIsNotNone(agents)
        self.assertEqual(agents.config, config)

    def test_task_creation(self):
        """Test that tasks are created with correct descriptions."""
        from crewai import Agent
        tasks = MarketingTasks()
        # Create a dummy agent
        agent = Agent(role="Test Role", goal="Test Goal", backstory="Test Backstory")
        task = tasks.research_product(agent, "Test Product", "output.md")
        
        self.assertIn("Test Product", task.description)
        self.assertEqual(task.output_file, "output.md")
        self.assertEqual(task.agent, agent)

    @patch('utils.llm_controllers.requests.get')
    def test_ollama_controller_check_status(self, mock_get):
        """Test Ollama controller status check."""
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        config = {'model': 'llama3'}
        controller = OllamaController(config)
        self.assertTrue(controller.check_server_status())
        
        # Mock failed response
        mock_get.side_effect = Exception("Connection refused")
        self.assertFalse(controller.check_server_status())

if __name__ == '__main__':
    unittest.main()
