import time
import schedule
from screenshot import ScreenshotTaker

def job():
    """Function to capture and save a screenshot."""
    screenshot_taker = ScreenshotTaker()
    screenshot_taker.capture_and_save()

def main():
    """Main function to schedule the screenshot capture every 2 minutes."""
    schedule.every(2).minutes.do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()