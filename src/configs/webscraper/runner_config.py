from datetime import date

N_TOP_COMMENTS = 1

START_DATE = date(2022, 10, 25)
END_DATE = date(2022, 10, 26)

URLS_CSV = "data/top_weekly.csv"
LOG_LEVEL = "DEBUG"
LOG_N_ITER = 1
SLEEP = 0.5
TIMEOUT = 2
CHROME_ARGS = [
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-notifications",
    "--headless"
]
