from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import RandomHeaders
import threading
import time
import sys
import os

# chrome option to prevent the window from closing after script completion - allow user to checkout #
opts_co = webdriver.ChromeOptions()
opts_co.add_experimental_option("detach", True)

# set environment variable to use drivers
chromedriver = os.path.dirname(__file__) + '/drivers/chromedriver'
os.environ["webdriver.chrome.driver"] = chromedriver
phantomjs = os.path.dirname(__file__) + '/drivers/phantomjs'
os.environ["phantomjs.binary.path"] = phantomjs

URL = sys.argv[1]
# if proxies provided in argv uses those - otherwise read proxies from file
if len(sys.argv) > 2:
	PROXIES = sys.argv[2:]
else:
	PROXIES = [line.rstrip('\n') for line in open('proxies.txt')]


def captcha_present(wait):
	try:
		# explicit wait - continually poll DOM looking for a captcha element (indicating splash bypass)
		wait.until(ec.visibility_of_element_located(("class name", "g-recaptcha")))
		return True
	except TimeoutException as tex:
		# captcha hasn't been found yet return false
		return False


def grabSS(proxy):
	while True:
		try:
			opts = webdriver.ChromeOptions()
			opts.add_argument('headless')
			opts.add_argument("start-maximized")
			opts.add_argument("--proxy-server=" + str(proxy))
			opts.add_argument("user-agent=" + str(RandomHeaders.LoadHeader()))
			driver = webdriver.Chrome(executable_path=chromedriver, chrome_options=opts)
			# implicitly retry polling DOM for 10 seconds before throwing an exception - website can lag during drop
			driver.implicitly_wait(10)
			# create a WebDriverWait object - explicit 60 second timeout
			wait = WebDriverWait(driver, 5)

			# load the splash page
			driver.get(URL)

			# wait until captcha found
			while not captcha_present(wait):
				print proxy + '\tstill waiting'
				driver.get_screenshot_as_file('{}.png'.format(proxy.replace(':', '').replace('.', '')))

			# splash page passed - save session cookies
			print proxy + '\tPASSED SPLASH PAGE!'
			cookies_list = driver.get_cookies()
			driver.close()
			driver.quit()

			# create a new driver for checkout
			opts_co.add_argument("--proxy-server=" + str(proxy))
			opts.add_argument("user-agent=" + str(RandomHeaders.LoadHeader()))
			driver = webdriver.Chrome(executable_path=chromedriver, chrome_options=opts_co)

			# you can only set cookies for the driver's current domain so visit the page first then set cookies
			driver.get(URL)
			# precautionary - delete all cookies first
			driver.delete_all_cookies()
			for cookie in cookies_list:
				# precautionary - prevent possible Exception - can only add cookie for current domain
				if "adidas" in cookie['domain']:
					driver.add_cookie(cookie)
			# once cookies are changed browser must be refreshed
			driver.refresh()

			# this IP can re-enter the queue after the 10 minute checkout period
			# to do so - simply wait for the 10 minute cart time to finish with an explicit sleep
			time.sleep(60 * 10)
		except Exception as exp:
			print(exp)
			driver.close()
			driver.quit()


if __name__ == "__main__":
	print PROXIES
	threads = [threading.Thread(target=grabSS, args=(proxy,)) for proxy in PROXIES]
	for thread in threads:
		thread.start()
	for thread in threads:
		thread.join()
