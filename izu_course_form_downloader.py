"""
İZÜ – Course-Information-Form bulk downloader
--------------------------------------------
Downloads course information forms (Ders Bilgi Formu / Syllabus)
in PDF format from the IZU Kampus system for a specified range of academic terms.

Requires:
  - Python 3.7+
  - Google Chrome browser installed
  - IZU_MAIL and IZU_PASS environment variables set with your campus login credentials.
"""

import os
import sys
import time
import unicodedata
import shutil
import logging
from pathlib import Path
from typing import Set

# Third-party imports
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("Required libraries not found. Please install them:")
    print("pip install selenium webdriver-manager")
    sys.exit(1)

# ─────────────── USER SETTINGS ───────────────
# Root directory where term folders with PDFs will be saved
DOWNLOAD_ROOT = Path.home() / "IZU_CourseForms"
# Run Chrome in headless mode (no GUI)? Set to True after initial successful run.
HEADLESS = False
# Define the range of academic terms to download (inclusive)
# Use the exact format shown in the IZU Kampus dropdown.
START_TERM_HUMAN = "2019 - 2020 Güz"
END_TERM_HUMAN = "2021 - 2022 Bahar"
# Maximum time (seconds) to wait for a single PDF download to complete
DOWNLOAD_TIMEOUT = 90
# Maximum time (seconds) to wait for page elements to load
SELENIUM_WAIT_TIMEOUT = 30
# ──────────────────────────────────────────────

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)

# --- Constants ---
KAMPUS_LOGIN_URL = "https://kampus.izu.edu.tr/login"
KAMPUS_HOME_URL_PART = "/Home"
COURSE_MATERIALS_MENU_SELECTOR = 'a[MenuIlsemNo="2087"]' # "Ders Materyalleri"
TERM_DROPDOWN_ID = "DONEM"
DISPLAY_BUTTON_ID = "OgrDersDonemSecBtn"
COURSE_TABS_SELECTOR = "ul.nav-tabs li a"
# XPath to find the download link within the *active* course tab
ACTIVE_DOWNLOAD_LINK_XPATH = (
    "//div[contains(@class,'tab-pane') and contains(@class,'active')]"
    "//a[contains(@onclick,'downloadCourseInfoForm(')]"
)

# --- Helper Functions ---

# Map Turkish season names (and variations) to a normalized English version
_SEASON_MAP = {
    "guz": "fall", "güz": "fall", "sonbahar": "fall",
    "bahar": "spring", "ilkbahar": "spring",
    "yaz": "summer",
    "kis": "winter", "kış": "winter"
}

def normalize_term_label(text: str) -> str:
    """Normalizes term labels for comparison (lowercase, ASCII, mapped seasons)."""
    if not text: return ""
    # Replace common separators, convert to lowercase
    t = text.replace('-', ' ').replace(':', ' ').lower()
    # Remove diacritics (e.g., ş -> s, ı -> i, ü -> u)
    t = unicodedata.normalize('NFKD', t)
    t = ''.join(c for c in t if not unicodedata.combining(c))
    # Map Turkish seasons to English and reconstruct the string
    return ' '.join(_SEASON_MAP.get(word, word) for word in t.split())

def create_driver() -> webdriver.Chrome:
    """Initializes and returns a configured Selenium Chrome WebDriver."""
    log.info("Initializing Chrome WebDriver...")
    prefs = {
        # Set download directory and disable PDF viewer/prompt
        "download.default_directory": str(DOWNLOAD_ROOT),
        "plugins.always_open_pdf_externally": True,
        "download.prompt_for_download": False,
        "safebrowsing.enabled": True # Enable safe browsing checks
    }
    opts = webdriver.ChromeOptions()
    opts.add_experimental_option("prefs", prefs)
    # Suppress excessive logging from Chrome/WebDriver
    opts.add_argument("--log-level=3")
    opts.add_experimental_option('excludeSwitches', ['enable-logging']) # Hide DevTools listening message
    if HEADLESS:
        log.info("Headless mode enabled.")
        opts.add_argument("--headless=new") # Use the new headless mode
        opts.add_argument("--window-size=1920,1080") # Often needed for headless
        opts.add_argument("--disable-gpu") # Sometimes necessary for headless stability

    try:
        # Use webdriver-manager to automatically handle chromedriver
        # Use os.devnull for cross-platform suppression of webdriver-manager logs
        service = Service(ChromeDriverManager().install(), log_path=os.devnull)
        driver = webdriver.Chrome(service=service, options=opts)
        log.info("WebDriver initialized successfully.")
        return driver
    except Exception as e:
        log.error(f"Failed to initialize WebDriver: {e}")
        log.error("Ensure Google Chrome is installed and accessible.")
        log.error("If issues persist, try running without headless mode first.")
        sys.exit(1)

def wait_for_new_pdf(prev_pdfs: Set[str], timeout: int) -> Path | None:
    """
    Waits until a new PDF file appears in DOWNLOAD_ROOT.

    Args:
        prev_pdfs: A set of PDF filenames present before the download started.
        timeout: Maximum time in seconds to wait.

    Returns:
        The Path object of the newly downloaded PDF, or None if timed out.
    """
    start_time = time.time()
    check_interval = 2  # seconds between checks
    last_log_time = 0

    while time.time() - start_time < timeout:
        try:
            current_pdfs = {p.name for p in DOWNLOAD_ROOT.glob("*.pdf")}
            new_files = current_pdfs - prev_pdfs
            if new_files:
                # Check for temporary download files (.crdownload)
                new_pdf_name = next(iter(new_files))
                if not new_pdf_name.lower().endswith(".crdownload"):
                    new_file_path = DOWNLOAD_ROOT / new_pdf_name
                    # Brief pause to ensure file handle is released
                    time.sleep(0.5)
                    # Check if file size is non-zero (basic check for completion)
                    if new_file_path.exists() and new_file_path.stat().st_size > 0:
                        elapsed = time.time() - start_time
                        log.info(f"      ✓ Download complete: '{new_pdf_name}' ({elapsed:.1f}s)")
                        return new_file_path
                    else:
                        # File might still be writing or empty
                        log.debug(f"      ... Detected '{new_pdf_name}', waiting for completion...")

            # Log progress periodically
            if time.time() - last_log_time > 10:
                 log.info(f"      ... Waiting for download ({int(time.time() - start_time)}s elapsed)")
                 last_log_time = time.time()

        except FileNotFoundError:
            # DOWNLOAD_ROOT might not exist initially on first download
            log.debug("      ... Download directory not found yet, waiting...")
        except Exception as e:
            log.warning(f"      ! Error checking for new PDF: {e}")

        time.sleep(check_interval)

    log.warning(f"      ✘ Timed out after {timeout}s waiting for PDF download.")
    return None

def sanitize_filename(filename: str) -> str:
    """Removes or replaces characters invalid for filenames."""
    # Remove characters invalid in Windows/Linux/MacOS filenames
    # Keep spaces, hyphens, underscores, parentheses, and basic alphanumerics
    sanitized = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '(', ')', '.'))
    # Replace multiple spaces with a single space
    sanitized = ' '.join(sanitized.split())
    return sanitized.strip()

def download_courses_for_term(driver: webdriver.Chrome, wait: WebDriverWait, term_dir: Path):
    """Downloads all course forms for the currently selected term."""
    main_window = driver.current_window_handle
    course_index = 0
    while True:
        # Re-find tabs each iteration as page structure might change slightly
        try:
            course_tabs = driver.find_elements(By.CSS_SELECTOR, COURSE_TABS_SELECTOR)
            if course_index >= len(course_tabs):
                log.info(f"  Processed all {len(course_tabs)} course tabs for this term.")
                break # No more tabs left

            tab = course_tabs[course_index]
            course_title_raw = tab.text.strip()
            if not course_title_raw:
                 log.warning(f"  Tab {course_index + 1} has no title, skipping.")
                 course_index += 1
                 continue

            course_title_safe = sanitize_filename(course_title_raw)
            destination_pdf = term_dir / f"{course_title_safe}.pdf"

            log.info(f"  [{course_index + 1}/{len(course_tabs)}] Processing: {course_title_raw}")

            if destination_pdf.exists():
                log.info(f"      ✓ Already downloaded: '{destination_pdf.name}' - Skipping.")
                course_index += 1
                continue

            # --- Click Tab ---
            try:
                # Use JavaScript click as it can be more reliable with complex UIs
                driver.execute_script("arguments[0].click();", tab)
                # Short pause for tab content to potentially load/become active
                time.sleep(0.7)
            except Exception as e:
                log.error(f"      ✘ Failed to click tab '{course_title_raw}': {e}")
                course_index += 1
                continue # Skip to next course

            # --- Find and Click Download Link ---
            download_link = None
            try:
                # Wait for the link within the *active* tab pane
                wait.until(EC.visibility_of_element_located((By.XPATH, ACTIVE_DOWNLOAD_LINK_XPATH)))
                download_link = driver.find_element(By.XPATH, ACTIVE_DOWNLOAD_LINK_XPATH)
                # Scroll link into view before clicking
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", download_link)
                time.sleep(0.3) # Brief pause after scroll

                # Get current PDFs before clicking download
                pdfs_before_download = {p.name for p in DOWNLOAD_ROOT.glob("*.pdf")}
                log.info("      → Clicking download link...")
                driver.execute_script("arguments[0].click();", download_link)

                # --- Wait for Download ---
                new_pdf_path = wait_for_new_pdf(pdfs_before_download, DOWNLOAD_TIMEOUT)

                if new_pdf_path:
                    # Ensure term directory exists
                    term_dir.mkdir(parents=True, exist_ok=True)

                    # Handle potential filename collisions (though unlikely with sanitized names)
                    final_destination = destination_pdf
                    counter = 1
                    while final_destination.exists():
                        final_destination = term_dir / f"{course_title_safe}_{counter}.pdf"
                        counter += 1

                    # Move the downloaded file
                    try:
                        shutil.move(new_pdf_path, final_destination)
                        log.info(f"      ✓ Moved to: '{final_destination.relative_to(DOWNLOAD_ROOT)}'")
                    except Exception as e:
                        log.error(f"      ✘ Failed to move '{new_pdf_path.name}' to '{final_destination}': {e}")
                else:
                    log.warning(f"      ✘ Download failed or timed out for '{course_title_raw}'.")

            except TimeoutException:
                log.warning(f"      ✘ Download link not found or not visible for '{course_title_raw}' after waiting.")
            except NoSuchElementException:
                 log.warning(f"      ✘ Download link element could not be found for '{course_title_raw}'.")
            except Exception as e:
                log.error(f"      ✘ An unexpected error occurred during download for '{course_title_raw}': {e}")

            # --- Cleanup and Advance ---
            # Close any extra tabs/windows opened by the download click (if any)
            try:
                all_windows = driver.window_handles
                if len(all_windows) > 1:
                    for window in all_windows:
                        if window != main_window:
                            driver.switch_to.window(window)
                            driver.close()
                    driver.switch_to.window(main_window)
            except Exception as e:
                log.warning(f"      ! Could not close extra browser windows: {e}")

            time.sleep(0.5) # Small delay before processing next tab
            course_index += 1

        except Exception as e:
            log.error(f"  ! An unexpected error occurred processing course index {course_index}: {e}")
            log.info("  Attempting to continue with the next course...")
            course_index += 1 # Try to prevent infinite loop on persistent error


# ──────────────────────── MAIN LOGIC ─────────────────────────
def main():
    """Main execution function."""
    log.info("Starting IZU Course Form Downloader...")
    DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    log.info(f"Downloads will be saved to: {DOWNLOAD_ROOT}")

    # --- Get Credentials ---
    izu_mail = os.getenv("IZU_MAIL")
    izu_pass = os.getenv("IZU_PASS")
    if not (izu_mail and izu_pass):
        log.error("Missing credentials. Set IZU_MAIL and IZU_PASS environment variables.")
        sys.exit(1)
    log.info("Credentials loaded from environment variables.")

    driver = None # Initialize driver to None for finally block
    try:
        driver = create_driver()
        wait = WebDriverWait(driver, SELENIUM_WAIT_TIMEOUT)
        # Use a longer wait specifically for the potentially slow course list loading
        long_wait = WebDriverWait(driver, DOWNLOAD_TIMEOUT) # Reuse download timeout

        # --- Login ---
        log.info(f"Navigating to login page: {KAMPUS_LOGIN_URL}")
        driver.get(KAMPUS_LOGIN_URL)
        wait.until(EC.presence_of_element_located((By.ID, "user_name")))
        driver.find_element(By.ID, "user_name").send_keys(izu_mail)
        driver.find_element(By.ID, "user_pas").send_keys(izu_pass + Keys.RETURN)
        wait.until(EC.url_contains(KAMPUS_HOME_URL_PART))
        log.info("Login successful.")

        # --- Navigate to Course Materials ---
        log.info("Navigating to 'Ders Materyalleri'...")
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, COURSE_MATERIALS_MENU_SELECTOR)))
        # Use JS click for sidebar items as they might have complex event handlers
        driver.execute_script(
            f"document.querySelector('{COURSE_MATERIALS_MENU_SELECTOR}').click()")

        # Wait for the term dropdown to be present and populated
        log.info("Waiting for semester dropdown...")
        wait.until(EC.presence_of_element_located((By.ID, TERM_DROPDOWN_ID)))
        # Add a small wait specifically for options to populate within the Select element
        wait.until(lambda d: len(Select(d.find_element(By.ID, TERM_DROPDOWN_ID)).options) > 1)
        log.info("Semester dropdown loaded.")

        # --- Identify Target Terms ---
        term_select_element = Select(driver.find_element(By.ID, TERM_DROPDOWN_ID))
        all_term_options = term_select_element.options
        all_term_labels = [opt.text.strip() for opt in all_term_options]

        norm_start = normalize_term_label(START_TERM_HUMAN)
        norm_end = normalize_term_label(END_TERM_HUMAN)
        log.info(f"Looking for terms from '{START_TERM_HUMAN}' ({norm_start}) to '{END_TERM_HUMAN}' ({norm_end})")

        try:
            # Find indices based on normalized labels for robustness
            start_index = next(i for i, label in enumerate(all_term_labels) if normalize_term_label(label) == norm_start)
            end_index = next(i for i, label in enumerate(all_term_labels) if normalize_term_label(label) == norm_end)
        except StopIteration:
            log.error("Could not find the specified start or end term in the dropdown.")
            log.error(f"Available terms: {all_term_labels}")
            return # Exit function gracefully

        # Determine the correct slice, handling reversed chronological order
        if start_index <= end_index:
            target_labels = all_term_labels[start_index : end_index + 1]
        else: # If start term is chronologically after end term in the list
            target_labels = all_term_labels[end_index : start_index + 1]
            # Reverse to process chronologically if needed, though order might not matter
            # target_labels.reverse() # Optional: uncomment if chronological processing is desired

        log.info(f"Found {len(target_labels)} terms to process: {', '.join(target_labels)}")

        # --- Process Each Term ---
        for term_label in target_labels:
            norm_label = normalize_term_label(term_label)
            # Skip summer terms if desired (optional)
            # if "summer" in norm_label:
            #     log.info(f"\nSkipping summer term: {term_label}")
            #     continue

            log.info(f"\n===== Processing Term: {term_label} =====")

            # ➊ Select Term in Dropdown
            try:
                # Find the option's value attribute corresponding to the label
                term_value = next(opt.get_attribute("value") for opt in all_term_options if opt.text.strip() == term_label)
                # Use JS to set the value and trigger change event for Select2/dynamic dropdowns
                driver.execute_script(f"$('#{TERM_DROPDOWN_ID}').val('{term_value}').trigger('change');")
                time.sleep(0.5) # Allow JS/UI to update
                log.info(f"  Selected term '{term_label}' in dropdown.")
            except StopIteration:
                 log.error(f"  Could not find value for term '{term_label}'. Skipping.")
                 continue
            except Exception as e:
                log.error(f"  Failed to select term '{term_label}': {e}. Skipping.")
                continue

            # ➋ Click "Display" Button
            try:
                display_button = driver.find_element(By.ID, DISPLAY_BUTTON_ID)
                # Scroll button into view and use JS click
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", display_button)
                time.sleep(0.3)
                driver.execute_script("arguments[0].click();", display_button)
                log.info("  Clicked 'Display' button.")
            except Exception as e:
                log.error(f"  Failed to click 'Display' button: {e}. Skipping term.")
                continue

            # ➌ Wait for Course Tabs to Load
            try:
                # Use the longer wait here as this can be slow
                log.info("  Waiting for course tabs to load...")
                long_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, COURSE_TABS_SELECTOR)))
                # Optional: Check if any tabs actually loaded vs just the container
                if not driver.find_elements(By.CSS_SELECTOR, COURSE_TABS_SELECTOR):
                     log.info("  Term appears empty (no course tabs found).")
                     continue
                log.info("  Course tabs loaded.")
            except TimeoutException:
                log.warning("  Timed out waiting for course tabs. Term might be empty or page failed to load.")
                continue # Skip to next term

            # ➍ Download Courses for the Term
            # Sanitize term label for directory name (replace potential problematic chars)
            term_dir_name = term_label.replace(':', '-').replace('/', '_').strip()
            term_download_path = DOWNLOAD_ROOT / term_dir_name
            download_courses_for_term(driver, wait, term_download_path)

        log.info("\n===== All requested terms processed successfully! =====")

    except TimeoutException as e:
        log.error(f"A timeout occurred: {e}")
        log.error("Consider increasing SELENIUM_WAIT_TIMEOUT or DOWNLOAD_TIMEOUT.")
    except NoSuchElementException as e:
         log.error(f"Could not find a critical element on the page: {e}")
         log.error("The website structure might have changed.")
    except Exception as e:
        log.exception("An unexpected error occurred during execution.") # Logs traceback
    finally:
        if driver:
            log.info("Closing WebDriver.")
            driver.quit()

if __name__ == "__main__":
    main()
