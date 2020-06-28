import asyncio
import logging
# import threading
import time
from PIL import Image
import requests
from io import BytesIO
import matplotlib.pyplot as plt
from enum import Enum
import pickle

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By

from conf.Config import CONFIG

slot_found = False
logger = logging.getLogger(__name__)

chrome_webdriver_path = CONFIG["basic"]["chrome_webdriver_path"]
amazon_home_url = CONFIG["basic"]["amazon_home_url"]
amazon_fresh_home_url = CONFIG["basic"]["amazon_fresh_home_url"]
amazon_fresh_sign_in_url = CONFIG["basic"]["amazon_fresh_sign_in_url"]

account = CONFIG["credential"]["account"]
password = CONFIG["credential"]["password"]
cookie_file_name = CONFIG["credential"]["cookie_file_name"]

account_element_id = CONFIG["DOM"]["account_element_id"]
password_element_id = CONFIG["DOM"]["password_element_id"]
continue_element_id = CONFIG["DOM"]["continue_element_id"]
sign_in_element_id = CONFIG["DOM"]["sign_in_element_id"]
captcha_element_id = CONFIG["DOM"]["captcha_element_id"]
captcha_guess_element_id = CONFIG["DOM"]["captcha_guess_element_id"]
remember_me_element_name = CONFIG["DOM"]["remember_me_element_name"]
otp_code_element_name = CONFIG["DOM"]["otp_code_element_name"]
shop_cart_element_id = CONFIG["DOM"]["shop_cart_element_id"]
checkout_continue_name = CONFIG["DOM"]["checkout_continue_name"]
amazon_fresh_welcome_id = CONFIG["DOM"]["amazon_fresh_welcome_id"]

authentication_required_title_xpath = CONFIG["DOM"]["authentication_required_title_xpath"]
second_authentication_required_title_xpath = CONFIG["DOM"]["second_authentication_required_title_xpath"]
authentication_required_enter_otp_title_xpath = CONFIG["DOM"]["authentication_required_enter_otp_title_xpath"]
authentication_required_enter_otp_input_xpath = CONFIG["DOM"]["authentication_required_enter_otp_input_xpath"]
anti_automation_challenge_title_xpath = CONFIG["DOM"]["anti_automation_challenge_title_xpath"]
anti_automation_challenge_captcha_xpath = CONFIG["DOM"]["anti_automation_challenge_captcha_xpath"]
anti_automation_challenge_input_xpath = CONFIG["DOM"]["anti_automation_challenge_input_xpath"]
anti_automation_challenge_submit_xpath = CONFIG["DOM"]["anti_automation_challenge_submit_xpath"]
shop_cart_page_checkout_input_xpath = CONFIG["DOM"]["shop_cart_page_checkout_input_xpath"]


class AuthenticationRequiredType(Enum):
    UNKNOWN = 0
    OTP = 1


async def test():
    global slot_found
    while not slot_found:
        print(slot_found)
        slot_found = True
        await asyncio.sleep(1)
    print("Finished")


def get_web_driver():
    driver = webdriver.Chrome(executable_path=chrome_webdriver_path)
    return driver


def display_image(url):
    response = requests.get(url)
    image = Image.open(BytesIO(response.content))
    plot = plt.imshow(image)
    plt.show()


def has_authentication_required(driver: webdriver.Chrome) -> bool:
    try:
        element = driver.find_element_by_xpath(authentication_required_title_xpath)
        if "Authentication" in element.text:
            return True
        return False
    except NoSuchElementException:
        return False


def has_second_authentication_required(driver: webdriver.Chrome) -> bool:
    try:
        element = driver.find_element_by_xpath(second_authentication_required_title_xpath)
        if "Authentication" in element.text:
            return True
        return False
    except NoSuchElementException:
        return False


def get_authentication_required_type(driver: webdriver.Chrome) -> AuthenticationRequiredType:
    try:
        _ = driver.find_element_by_xpath(authentication_required_enter_otp_title_xpath)
        return AuthenticationRequiredType.OTP
    except NoSuchElementException:
        pass
    return AuthenticationRequiredType.UNKNOWN


def solve_authentication_required(driver: webdriver.Chrome):
    try:
        if get_authentication_required_type(driver) is AuthenticationRequiredType.OTP:
            otg = str(input("OTG is: "))
            if otg:
                driver.find_element_by_xpath(anti_automation_challenge_input_xpath).send_keys(otg)
                driver.find_element_by_xpath(anti_automation_challenge_submit_xpath).click()
            else:
                raise NoSuchElementException
        element = driver.find_element_by_id(continue_element_id)
        element.click()
    except NoSuchElementException:
        logger.error("Not able to solve Authentication required page")


def has_anti_automation_challenge(driver: webdriver.Chrome) -> bool:
    try:
        element = driver.find_element_by_xpath(anti_automation_challenge_title_xpath)
        if "Challenge" in element.text:
            return True
        return False
    except NoSuchElementException:
        return False


def solve_anti_automation_challenge(driver: webdriver.Chrome):
    try:
        element = driver.find_element_by_xpath(anti_automation_challenge_captcha_xpath)
        captcha_url = element.get_attribute("src")
        display_image(captcha_url)
        captcha = str(input("Anti-Automation Challenge Captcha is: "))
        if captcha:
            driver.find_element_by_xpath(anti_automation_challenge_input_xpath).send_keys(captcha)
            driver.find_element_by_xpath(anti_automation_challenge_submit_xpath).click()
        else:
            raise NoSuchElementException
    except NoSuchElementException:
        logger.error("Not able to solve anti-automation challenge page")


def sign_in(driver: webdriver.Chrome):
    global logger
    success = False
    try:
        driver.get(amazon_fresh_sign_in_url)
        driver.find_element_by_id(account_element_id).send_keys(account)
        driver.find_element_by_id(continue_element_id).click()
        WebDriverWait(driver, 3).until(expected_conditions.visibility_of_element_located((By.ID, password_element_id)))
        driver.find_element_by_id(password_element_id).send_keys(password)
        driver.find_element_by_name(remember_me_element_name).click()
        driver.find_element_by_id(sign_in_element_id).click()
        captcha_url = driver.find_element_by_id(captcha_element_id).get_attribute("src")
        display_image(captcha_url)
        captcha = str(input("The captcha is: "))
        if captcha:
            driver.find_element_by_id(password_element_id).send_keys(password)
            driver.find_element_by_id(captcha_guess_element_id).send_keys(captcha)
            driver.find_element_by_id(sign_in_element_id).click()
        else:
            raise RuntimeError("Unable to get captcha from input")
        if has_authentication_required(driver):
            solve_authentication_required(driver)
        if has_anti_automation_challenge(driver):
            solve_anti_automation_challenge(driver)
        if has_second_authentication_required(driver):
            solve_authentication_required(driver)
        WebDriverWait(driver, 120).until(expected_conditions.visibility_of_element_located((By.ID, shop_cart_element_id)))
        success = True
    except TimeoutException:
        logger.error("Time out when signing in")
    except Exception as ex:
        logger.error("Unable to login due to: " + str(ex))
    return success


def sign_in_with_cookies(driver: webdriver.Chrome) -> bool:
    logger.info("Starting to sign in using pickled cookie")

    try:
        cookies_file = open(cookie_file_name, "rb")
        cookies = pickle.load(cookies_file)
        driver.get(amazon_fresh_home_url)
        for cookie in cookies:
            if 'expiry' in cookie:
                del cookie['expiry']
            driver.add_cookie(cookie)
    except IOError:
        logger.error("Unable to use pickled cookie to sign in")
        return False
    driver.refresh()
    try:
        WebDriverWait(driver, 10).until(expected_conditions.visibility_of_element_located((By.ID, amazon_fresh_welcome_id)))
        if "signin" in driver.find_element_by_id(amazon_fresh_welcome_id).get_attribute("href"):
            return False
        else:
            return True
    except Exception:
        logger.error("Failed to use pickled cookie to sign in")


def goto_checkout_page(driver: webdriver.Chrome) -> bool:
    try:
        try:
            shop_cart = driver.find_element_by_id(shop_cart_element_id)
            shop_cart.click()
            WebDriverWait(driver, 10).until(expected_conditions.visibility_of_element_located((By.XPATH, shop_cart_page_checkout_input_xpath)))
            checkout_input = driver.find_element_by_xpath(shop_cart_page_checkout_input_xpath)
            checkout_input.click()
            WebDriverWait(driver, 10).until(expected_conditions.visibility_of_element_located((By.NAME, checkout_continue_name)))
            continue_href = driver.find_element_by_name(checkout_continue_name)
            continue_href.click()
            WebDriverWait(driver, 10).until(expected_conditions.visibility_of_element_located((By.ID, password_element_id)))
            try:
                password_input = driver.find_element_by_id(password_element_id)
                password_input.send_keys(password)
                remember_me = driver.find_element_by_name(remember_me_element_name)
                if not remember_me.is_selected():
                    remember_me.click()
                sign_in_input = driver.find_element_by_id(sign_in_element_id)
                sign_in_input.click()
            except NoSuchElementException:
                logger.info("Sign in not needed, proceeding")
        except TimeoutException:
            logger.info("No sign in needed, skipping ...")
        return True
    except NoSuchElementException:
        logger.error("Unable to go to checkout page")
        return False


def main():
    global logger
    logger = logging.getLogger("Main")
    handler = logging.FileHandler("slot_checker.log")
    formatter = logging.Formatter("%(asctime)s %(name)s %(funcName)s:%(lineno)d %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    driver = get_web_driver()
    logger.info("Start signing in")

    # successfully_logged_in = sign_in(driver)
    #
    # if successfully_logged_in:
    #     goto_checkout_page(driver)
    # else:
    #     logger.info("Unable to sign in, quitting ...")
    #
    # checkout_url = driver.current_url
    # with open("cookies.pkl", "wb") as cookies_file:
    #     cookies = driver.get_cookies()
    #     pickle.dump(cookies, cookies_file)




    time.sleep(10000)
    driver.quit()

    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(test())

    # current_thread = threading.Thread(target=tracker, args=(loop,))
    # current_thread.run()


if __name__ == '__main__':
    main()
