# IZU Course Information Form Downloader

This script automates the bulk downloading of Course Information Forms (Ders Bilgi Formu / Syllabus) in PDF format from the Istanbul Sabahattin Zaim University (İZÜ) Kampus system (kampus.izu.edu.tr). It allows you to specify a range of academic terms and downloads all available forms for the courses within those terms.

## Features

*   Downloads course forms for a specified range of academic terms (e.g., "2019 - 2020 Güz" to "2021 - 2022 Bahar").
*   Organizes downloaded PDFs into folders named after the academic term.
*   Handles login automatically using environment variables.
*   Uses `selenium` and `webdriver-manager` to control a Chrome browser.
*   Supports optional headless browsing (running without a visible Chrome window).
*   Includes timeouts and retries for robustness.
*   Skips already downloaded files.
*   Sanitizes filenames derived from course titles.

## Prerequisites

*   **Python:** Version 3.7 or higher recommended.
*   **Google Chrome:** The script requires Google Chrome browser to be installed.
*   **İZÜ Kampus Account:** You need valid login credentials (student email and password).

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd <repository-directory>
    ```
2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    This will install `selenium` and `webdriver-manager`. `webdriver-manager` will automatically download the correct `chromedriver` executable compatible with your installed Chrome version the first time you run the script.

## Configuration

1.  **Set Environment Variables:**
    The script requires your İZÜ Kampus login credentials to be set as environment variables. **Do not hardcode them directly into the script.**

    *   **On Linux/macOS:**
        ```bash
        export IZU_MAIL="your_student_mail@std.izu.edu.tr"
        export IZU_PASS="your_kampus_password"
        ```
        You can add these lines to your `~/.bashrc`, `~/.zshrc`, or other shell configuration file for persistence. Alternatively, you can set them just for the current session before running the script.

    *   **On Windows (Command Prompt):**
        ```cmd
        set IZU_MAIL="your_student_mail@std.izu.edu.tr"
        set IZU_PASS="your_kampus_password"
        ```
    *   **On Windows (PowerShell):**
        ```powershell
        $env:IZU_MAIL = "your_student_mail@std.izu.edu.tr"
        $env:IZU_PASS = "your_kampus_password"
        ```
    *   **Using a `.env` file (Recommended):**
        You can create a file named `.env` in the script's directory:
        ```dotenv
        IZU_MAIL="your_student_mail@std.izu.edu.tr"
        IZU_PASS="your_kampus_password"
        ```
        Then, install `python-dotenv` (`pip install python-dotenv`) and add these lines near the top of the Python script:
        ```python
        from dotenv import load_dotenv
        load_dotenv()
        ```

2.  **Adjust Script Settings (Optional):**
    Open the `izu_course_form_downloader.py` file and modify the settings within the `USER SETTINGS` section near the top:
    *   `DOWNLOAD_ROOT`: Change the default download directory if desired.
    *   `HEADLESS`: Set to `True` to run Chrome without a visible window (recommended after confirming it works).
    *   `START_TERM_HUMAN` / `END_TERM_HUMAN`: **Crucially, set these to the exact term names as they appear in the İZÜ Kampus dropdown menu.**
    *   `DOWNLOAD_TIMEOUT` / `SELENIUM_WAIT_TIMEOUT`: Increase these values (in seconds) if you have a slow internet connection or the website is slow to respond.

## Usage

1.  Ensure you have configured the environment variables (`IZU_MAIL`, `IZU_PASS`).
2.  Navigate to the script's directory in your terminal.
3.  Run the script:
    ```bash
    python izu_course_form_downloader.py
    ```
4.  The script will:
    *   Launch Chrome (visibly or headlessly based on the `HEADLESS` setting).
    *   Log in to İZÜ Kampus.
    *   Navigate to the "Ders Materyalleri" section.
    *   Iterate through the specified academic terms.
    *   For each term, select it, click "Display", and download the PDF form for each listed course.
    *   Save the PDFs into subdirectories named after the term within your `DOWNLOAD_ROOT` folder.
    *   Log its progress to the console.

## Troubleshooting

*   **Login Failure:** Double-check your `IZU_MAIL` and `IZU_PASS` environment variables. Ensure they are set correctly in the shell session where you run the script. Try logging in manually to verify credentials.
*   **Timeout Errors:** Increase `SELENIUM_WAIT_TIMEOUT` or `DOWNLOAD_TIMEOUT` in the script settings if the script fails waiting for elements or downloads.
*   **`WebDriverException` or `chromedriver` errors:** `webdriver-manager` usually handles this. Ensure Chrome is up-to-date. You might need to clear the webdriver-manager cache (`~/.wdm` or `%USERPROFILE%\.wdm`) or check for firewall/antivirus interference. Running the script *without* `HEADLESS = True` first can help diagnose browser issues.
*   **Script Stops Unexpectedly:** Check the console logs for error messages. The website structure (element IDs, selectors) might have changed, requiring updates to the script's constants (like `COURSE_MATERIALS_MENU_SELECTOR`, `TERM_DROPDOWN_ID`, etc.).
*   **No Forms Downloaded for a Term:** The term might genuinely have no forms available, or the selectors used to find course tabs/download links might need adjustment if the website layout changed.

## Disclaimer

This script is provided for personal, educational use only. Use it responsibly and ethically.
*   **Do not overload the İZÜ Kampus servers.** The script includes small delays, but avoid running it excessively.
*   **Respect the website's terms of service.** Automation might be against their policy. Use at your own risk.
*   The maintainers are not responsible for any misuse or consequences arising from the use of this script. Website structure changes may break the script's functionality at any time.

## License

MIT License.