"""Test the GUI demo functionality."""

import os
import subprocess
import time
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

# Mark all tests with demo marker for selective running
pytestmark = pytest.mark.demo


@pytest.fixture(scope="module")
def setup_gui():
    """Start the GUI development server for testing."""
    # Store original directory to return to after test
    original_dir = os.getcwd()
    
    # Change to the project root directory
    project_root = Path(__file__).parent.parent.parent.parent
    os.chdir(project_root)
    
    # Check if the GUI dev server is already running
    is_running = False
    try:
        import requests
        response = requests.get("http://localhost:5173")
        is_running = response.status_code == 200
    except:
        pass
    
    if not is_running:
        # Start the GUI development server
        gui_process = subprocess.Popen(
            ["npm", "run", "dev"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        
        # Wait for the server to start
        max_retries = 10
        retry_count = 0
        while retry_count < max_retries:
            try:
                import requests
                response = requests.get("http://localhost:5173")
                if response.status_code == 200:
                    break
            except:
                pass
            
            time.sleep(2)
            retry_count += 1
    else:
        gui_process = None
    
    yield
    
    # Clean up after test
    if gui_process:
        gui_process.terminate()
        gui_process.wait()
    
    os.chdir(original_dir)


@pytest.mark.skip(reason="Requires full GUI setup")
@pytest.mark.gui
def test_gui_homepage(setup_gui):
    """Test the GUI homepage loads correctly."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to the GUI
        page.goto("http://localhost:5173")
        
        # Check that the page loaded correctly
        expect(page).to_have_title("Code Story")
        
        # Check for main components
        expect(page.locator("text=Code Story")).to_be_visible()
        expect(page.locator("text=Graph")).to_be_visible()
        expect(page.locator("text=Ask")).to_be_visible()
        expect(page.locator("text=Ingestion")).to_be_visible()
        expect(page.locator("text=Configuration")).to_be_visible()
        
        browser.close()


@pytest.mark.skip(reason="Requires full GUI setup")
@pytest.mark.gui
def test_gui_configuration(setup_gui):
    """Test the GUI configuration page loads correctly."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to the GUI
        page.goto("http://localhost:5173/config")
        
        # Check that the page loaded correctly
        expect(page.locator("text=Configuration")).to_be_visible()
        
        # Check for configuration sections
        expect(page.locator("text=Neo4j Configuration")).to_be_visible()
        expect(page.locator("text=OpenAI Configuration")).to_be_visible()
        
        # Check for form elements
        expect(page.locator('label:has-text("Database URL")')).to_be_visible()
        expect(page.locator('label:has-text("Username")')).to_be_visible()
        expect(page.locator('label:has-text("Password")')).to_be_visible()
        expect(page.locator('label:has-text("Database Name")')).to_be_visible()
        
        browser.close()


@pytest.mark.skip(reason="Requires full GUI setup")
@pytest.mark.gui
def test_gui_ingestion(setup_gui):
    """Test the GUI ingestion page loads correctly."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to the GUI
        page.goto("http://localhost:5173/ingest")
        
        # Check that the page loaded correctly
        expect(page.locator("text=Ingestion")).to_be_visible()
        
        # Check for ingestion form
        expect(page.locator('label:has-text("Repository Path")')).to_be_visible()
        expect(page.locator('button:has-text("Start Ingestion")')).to_be_visible()
        
        browser.close()


@pytest.mark.skip(reason="Requires graph data")
@pytest.mark.gui
def test_gui_graph(setup_gui):
    """Test the GUI graph page loads correctly."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to the GUI
        page.goto("http://localhost:5173/graph")
        
        # Check that the page loaded correctly
        expect(page.locator("text=Graph Viewer")).to_be_visible()
        
        # Check for graph controls
        expect(page.locator("text=Graph Controls")).to_be_visible()
        
        browser.close()


@pytest.mark.skip(reason="Requires full setup")
@pytest.mark.gui
def test_gui_ask(setup_gui):
    """Test the GUI ask page loads correctly."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to the GUI
        page.goto("http://localhost:5173/ask")
        
        # Check that the page loaded correctly
        expect(page.locator("text=Ask")).to_be_visible()
        
        # Check for query input
        expect(page.locator('textarea')).to_be_visible()
        expect(page.locator('button:has-text("Ask Question")')).to_be_visible()
        
        browser.close()


@pytest.mark.skip(reason="Requires full setup")
@pytest.mark.gui
def test_gui_mcp(setup_gui):
    """Test the GUI MCP page loads correctly."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to the GUI
        page.goto("http://localhost:5173/mcp")
        
        # Check that the page loaded correctly
        expect(page.locator("text=MCP Playground")).to_be_visible()
        
        # Check for MCP components
        expect(page.locator("text=Template")).to_be_visible()
        
        browser.close()