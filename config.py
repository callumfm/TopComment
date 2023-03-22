from datetime import date

N_TOP_COMMENTS = 1
GET_WORST = False

START_DATE = date(2022, 10, 24)
END_DATE = date(2022, 11, 2)

URLS_CSV = "data/top_weekly.csv"
LOG_N_ITER = 25
SLEEP = 1
TIMEOUT = 5
CHROME_ARGS = ["--disable-dev-shm-usage", "--no-sandbox", "--disable-notifications", "headless"]
