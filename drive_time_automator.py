from selenium.common.exceptions import TimeoutException
from selenium.webdriver import FirefoxProfile
import user_agents



import re
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.proxy import *
import pandas as pd
import datetime
import time
import random
from selenium import webdriver, selenium

# Path to the Firefox profile
FIREFOX_PROFILE_PATH = None

# Managing proxy support:
PROXY_URL = None

MIN_DELAY = 2
MAX_DELAY = 6
MAX_TIMEOUT = 10

MAX_ROW_REQUESTS_USER_AGENT = 6

# if PROCESS_FILE_TIMEOUT_RETRIES is None, retry forever
PROCESS_FILE_TIMEOUT_RETRIES = 10
PROCESS_FILE_EXCEPTION_RETRIES = 10

# GOOGLE DIRECTIONS WORKING WITH SELENIUM

def google_directions_load_page(driver):
    """
    Loads the main google maps directions page
    @param driver:
    """
    driver.get("https://maps.google.com/maps/dir///")


def google_directions_select_travel_model_car(driver):
    """
    Selects the travel car mode from selector
    @param driver:
    """
    travel_mode_car_button = WebDriverWait(driver, MAX_TIMEOUT).until(EC.visibility_of_element_located((By.XPATH,
                                "//*[@class='directions-travel-mode-selector']//*[@travel_mode='0']//button")))
    travel_mode_car_button.click()


def google_directions_search(driver):
    """
    Executes the route calculation search
    @param driver:
    """
    # Click on search button doesn't work :?, use ENTER on input
    destination_input = WebDriverWait(driver, MAX_TIMEOUT).until(EC.visibility_of_element_located((By.XPATH,
                                "//div[@id='directions-searchbox-1']//input")))
    destination_input.send_keys(Keys.ENTER)


def google_directions_get_time_text(driver):
    """
     Gets the route time description
    @param driver:
    @return:
    """
    # Get expanded information card
    card_body_elem = WebDriverWait(driver, MAX_TIMEOUT).until(EC.visibility_of_element_located((By.XPATH,
                                "//*[@class='cards-card' and @role='navigation']//*[@class='cards-expanded']")))

    return card_body_elem.find_element_by_xpath("//*[contains(@class, 'cards-directions-duration-value')]").text


def google_directions_set_origin(driver, origin):
    """
    Writes the origin into the input element
    @param driver:
    @param origin: The origin input text
    """
    origin_input = WebDriverWait(driver, MAX_TIMEOUT).until(EC.visibility_of_element_located((By.XPATH,
                                                                      "//div[@id='directions-searchbox-0']//input")))
    origin_input.send_keys(Keys.END)
    origin_input.send_keys(Keys.SHIFT, Keys.HOME)
    origin_input.send_keys(Keys.BACK_SPACE)
    origin_input.send_keys(origin)


def google_directions_set_destination(driver, destination):
    """
    Writes the destination into the input element
    @param driver:
    @param destination: the destination input text
    """
    destination_input = WebDriverWait(driver, MAX_TIMEOUT).until(EC.visibility_of_element_located((By.XPATH,
                                                                      "//div[@id='directions-searchbox-1']//input")))
    destination_input.send_keys(Keys.END)
    destination_input.send_keys(Keys.SHIFT, Keys.HOME)
    destination_input.send_keys(Keys.BACK_SPACE)
    destination_input.send_keys(destination)
    pass


def google_directions_set_time_mode(driver):
    """
    Sets the time mode to allow specify a date time for the request
    @param driver:
    """
    time_listbox = WebDriverWait(driver, MAX_TIMEOUT).until(EC.visibility_of_element_located((By.XPATH,
                    "//*[contains(@class,'time-anchoring-selector')]//*[@role='listbox']")))
    time_listbox.click()
    time_listbox.find_element_by_xpath("//div[@id=':1']").click()


def google_directions_set_time(driver, departure_time_str):
    """
    Sets the route starting time in 24h format
    @param driver:
    @param departure_time_str: Time in 24h string format. For ex.: "8:00", "17:00"
    """
    time_input = WebDriverWait(driver, MAX_TIMEOUT).until(EC.visibility_of_element_located((By.XPATH,
                    "//*[contains(@class,'widget-directions-time-picker')]//input[@class='time-input']")))
    time_input.click()
    time_input.send_keys(Keys.END)
    time_input.send_keys(Keys.SHIFT, Keys.HOME)
    time_input.send_keys(Keys.BACK_SPACE)
    time_input.send_keys(Keys.BACKSPACE)
    time_input.send_keys(departure_time_str)
    time_input.send_keys(Keys.ENTER)


def google_directions_set_day_month(driver, day, month):
    """
    Sets the day and month, the route starting date
    @param driver:
    @param day: Day as integer (Starting from 1)
    @param month: Month as integer (From 1 to 12)
    """
    date_input_elem = WebDriverWait(driver, MAX_TIMEOUT).until(EC.visibility_of_element_located((By.CLASS_NAME, "date-input")))
    date_input_elem.click()
    calendar_elem = driver.find_element_by_class_name("goog-popupdatepicker")
    prev_month_elem = calendar_elem.find_element_by_class_name("goog-date-picker-previousMonth")
    next_month_elem = calendar_elem.find_element_by_class_name("goog-date-picker-nextMonth")
    curr_month = datetime.datetime.now().month
    if curr_month > month:
        for i in range(0, curr_month-month):
            prev_month_elem.click()
    else:
        for i in range(0, month-curr_month):
            next_month_elem.click()

    days_elem = calendar_elem.find_element_by_xpath("//*[@role='grid']")
    day_elem = days_elem.find_element_by_xpath("//td[text()='%s']" % str(day))
    day_elem.click()


# TIME PARSING METHODS

def parse_time_text_pair_and_get_max(time_text):
    """
    Parses the text containing the route time description
    Examples: '30 min - 1 h 25 min', '30 min - 1 h', '1 h - 2 h', '1h - 1h 15 min' , etc.
    For the cases: '15 - 20 min' , '1 - 2 h' this algorith always returns the last part.
    @param time_text: the route time description. Example "30 min - 1h"
    @return: the maximum time extracted from the description, in seconds
    """
    time_parts = time_text.split('-')
    max_time = -1
    for time_part in time_parts:
        time = parse_time_text_hours_mins(time_part.strip())
        if time > max_time:
            max_time = time
    return max_time


def parse_time_text_hours_mins(time_text):
    """
    Parses one of the pairs of the route time description
    @param time_text: One of the pairs of the route time description. Example "30 min"
    @return: time extracted from the description, in seconds
    """
    # If time_text has no units then return 0
    regexp = r'\s*(([0-9]+)\s*h)?\s*(([0-9]+)\s*min)?'
    # search find all groups
    m = re.search(regexp, time_text)
    hours = 0
    mins = 0
    if m:
        hours = int(m.group(2)) if m.group(2) != None else 0
        mins = int(m.group(4)) if m.group(4) != None else 0
    # returns seconds
    return hours*3600 + mins*60


# SELENIUM WEBDRIVER

def create_webdriver(proxy_url=None):
    """
    Creates the webdriver for Selenium
    @param proxy_url: Proxy url in string format "host:port". None if no proxy is used
    @return: the Selenium webdriver
    """
    driver = None
    chrome_options = webdriver.ChromeOptions()
    user_agent = user_agents.random_user_agent()
    print "Setting User Agent: %s" % user_agent
    chrome_options.add_argument("--user-agent=" + user_agent);

    if proxy_url is not None:
        my_proxy = proxy_url
        proxy = Proxy({
            'proxyType': ProxyType.MANUAL,
            'httpProxy': my_proxy,
            'ftpProxy': my_proxy,
            'sslProxy': my_proxy,
            'noProxy': '' # set this value as desired
        })
        #driver = webdriver.Firefox(firefox_profile=create_firefox_profile(firefox_profile_path=FIREFOX_PROFILE_PATH), proxy=proxy)

        print "Setting Proxy: %s" % proxy_url
        chrome_options.add_argument('--proxy-server=%s' % proxy_url)
    else:
        #driver = webdriver.Firefox(firefox_profile=create_firefox_profile(firefox_profile_path=FIREFOX_PROFILE_PATH))
        pass

    driver = webdriver.Chrome(chrome_options=chrome_options)
    return driver


def create_firefox_profile(firefox_profile_path=None):
    """
    Creates a firefox selenium webdriver profile.
    @param firefox_profile_path: Path to Firefox profile. Example "/Users/username/Library/Application Support/Firefox/Profiles/jtokyple.selenium"
    @return None if no profile. A FirefoxWebdriver Profile if needed
    """
    if firefox_profile_path is not None:
        profile = FirefoxProfile(firefox_profile_path)
        return profile
    else:
        return None
    pass

# PROCESSING METHODS

def wait_a_while(driver):
    time.sleep(random.randint(MIN_DELAY, MAX_DELAY))

def is_row_processed(dataframe, time_col1, time_col2, row_index):
    """
    Checks if a row from the csv has been processed. It checks the time columns.
    @param dataframe: the csv dataframe object
    @param time_col1: the time result 1
    @param time_col2: the time result 2
    @param row_index: the current csv row index being processed
    @return: True if the row has already been processed, else False
    """
    time_to_str1 = str(dataframe[time_col1][row_index])
    time_to_str2 = str(dataframe[time_col2][row_index])
    return time_to_str1 != '' and time_to_str1 != 'nan' and time_to_str2 != '' and time_to_str2 != 'nan'

def process_file(filepath, departure_day, departure_month, departure_time_str, origin_col1, origin_col2,
                 destination_col1, destination_col2, time_col1, time_col_text1, time_col2, time_col_text2):
    random.seed()
    """
    Process a csv file and fills its time result columns
    @param filepath: path for the csv file
    @param departure_day: departure day of month as integer (Starting from 1)
    @param departure_month: departure month as integer (From 1 to 12)
    @param departure_time_str: departure time in string 24h format (Ex: "8:00", "17:00")
    @param origin_col1: column name for first route origin
    @param origin_col2: column name for second route origin
    @param destination_col1: column name for first route destination
    @param destination_col2: column name for second route destination
    @param time_col1: column name for first route time result (Where time will be saved as seconds)
    @param time_col_text1: column name for first route time result (Where time will be saved a time description)
    @param time_col2: column name for second route time result (Where time will be saved as seconds)
    @param time_col_text2: column name for second route time result (Where time will be saved a time description)
    @raise:
    """
    print "Processing file %s" % filepath

    pd.options.mode.chained_assignment = None
    df = pd.read_csv(filepath)
    df_length = len(df)

    timeout_retries = 0
    exception_retries = 0
    process_finished = False
    last_timeout_row = -1
    last_exception_row = -1

    while not process_finished and (PROCESS_FILE_TIMEOUT_RETRIES is None or timeout_retries < PROCESS_FILE_TIMEOUT_RETRIES) \
        and (PROCESS_FILE_EXCEPTION_RETRIES is None or exception_retries < PROCESS_FILE_EXCEPTION_RETRIES):

        try:
            user_agent_requests = 0
            driver = create_webdriver(proxy_url=PROXY_URL)
            google_directions_load_page(driver)
            google_directions_select_travel_model_car(driver)

            time_setted = False

            for i in range(df_length):
                # First check if route has been calculated
                if not is_row_processed(df, time_col1, time_col2, i):
                    # Set first origin/destination
                    google_directions_set_origin(driver, str(df[origin_col1][i]))
                    google_directions_set_destination(driver, str(df[destination_col1][i]))

                    # Date and time only needs to be setted one time. (Doesn't change for all the rows)
                    if not time_setted:
                        wait_a_while(driver)
                        google_directions_search(driver)
                        google_directions_set_time_mode(driver)
                        google_directions_set_time(driver, departure_time_str)
                        google_directions_set_day_month(driver, departure_day, departure_month)
                        time_setted = True

                    # First route calculation
                    wait_a_while(driver)
                    google_directions_search(driver)
                    time_text = google_directions_get_time_text(driver)
                    df[time_col_text1][i] = time_text
                    df[time_col1][i] = parse_time_text_pair_and_get_max(time_text)
                    # Second origin/destination
                    if origin_col2 != origin_col1:
                        google_directions_set_origin(driver, str(df[origin_col2][i]))
                    if destination_col2 != destination_col1:
                        google_directions_set_destination(driver, str(df[destination_col2][i]))
                    # Second route calculation
                    wait_a_while(driver)
                    google_directions_search(driver)
                    time_text = google_directions_get_time_text(driver)
                    df[time_col_text2][i] = time_text
                    df[time_col2][i] = parse_time_text_pair_and_get_max(time_text)

                    # Print to console the current row
                    print "ROW %d, t1:%d, t2: %d" % (i, df[time_col1][i], df[time_col2][i])
                    # Some delay to avoid requests overload to Google

                    # To avoid loose calculations in a case of crash, we could write the csv file at each loop (Uncomment)
                    # df.to_csv(filepath, index=False)

                    user_agent_requests += 1
                    if user_agent_requests >= MAX_ROW_REQUESTS_USER_AGENT:
                        print "Max row requests x user agent reached. Changing user agent..."
                        break

                timeout_retries = 0
                exception_retries = 0

            process_finished = (i >= df_length-1)

        except TimeoutException:
            if last_timeout_row == i:
                last_timeout_row = i
                timeout_retries += 1
                print "Timeout Exception. Retrying...%d/%s" % (timeout_retries,
                                "Forever" if PROCESS_FILE_TIMEOUT_RETRIES is None else str(PROCESS_FILE_TIMEOUT_RETRIES))
        except Exception, err:
            if last_exception_row == i:
                last_exception_row = i
                exception_retries += 1
                print err
                print "Exception. Retrying...%d/%s" % (timeout_retries,
                                "Forever" if PROCESS_FILE_EXCEPTION_RETRIES is None else str(PROCESS_FILE_EXCEPTION_RETRIES))
        except:
            print "Unhandled Exception"
            raise
        finally:
            print "Saving csv file..."
            df.to_csv(filepath, index=False)
            driver.quit()
    print "Completed"


# Process drive_ca_sel_1100am.csv
process_file('drive_time_1100am.csv', 9, 4, '11:00 AM', 'Origin_Zip', 'Origin_Zip', 'Destination_BH', 'Destination_SM', 'time_to_BH', 'time_to_BH_str', 'time_to_SM', 'time_to_SM_str')

# Process drive_ca_sel_700pm.csv
process_file('drive_time_700pm.csv', 9, 4, '7:00 PM', 'Origin_BH', 'Origin_SM', 'Destination_Zip', 'Destination_Zip', 'time_from_BH', 'time_from_BH_str', 'time_from_SM', 'time_from_SM_str')

