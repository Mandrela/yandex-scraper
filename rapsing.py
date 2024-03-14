import time
import os
import keyboard
import subprocess
import json

from icecream import ic
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from login_password import login, password

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

ic.configureOutput(includeContext=True)


def init_driver(driver_name: str) -> webdriver.Chrome | webdriver.Firefox | None:
    """
    :param driver_name: Could be Firefox or Chrome only for now
    """
    if driver_name == 'Firefox':
        options = webdriver.FirefoxOptions()
    elif driver_name == 'Chrome':
        options = webdriver.ChromeOptions()
    else:
        return None
    useragent = UserAgent()
    options.add_argument(f'user-agent={useragent.random}')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument(f'--disable-model-download-verification=True')
    if driver_name == 'Firefox':
        return webdriver.Firefox(options=options)
    elif driver_name == 'Chrome':
        return webdriver.Chrome(options=options)


def redo_html_file(file_path: str) -> None:
    """
    Delete sensetive information from page
    :param file_path: HTML file path
    """
    soup = BeautifulSoup(open(file_path, 'rb'), 'lxml')
    for page in soup.find_all('span', class_='user-account__name'):
        page.replace_with('')
    for script in soup.find_all('script'):
        script.replace_with('')
    with open(file_path, 'wb') as file:
        file.write(soup.prettify('utf-8'))


def read_urls(file_path: str) -> list:
    temp = []
    for url in open(file_path, 'rt', encoding='utf8').readlines():
        temp.append(url.strip())
    return temp


def authorizate(driver: webdriver.Chrome | webdriver.Firefox, login: str, password: str) -> None:
    """
    Authorize in lms system
    """
    login_input = driver.find_element(By.ID, 'passp-field-login')
    login_input.clear()
    login_input.send_keys(login)
    time.sleep(2)

    login_input.send_keys(Keys.ENTER)
    time.sleep(4)

    password_input = driver.find_element(By.ID, 'passp-field-passwd')
    password_input.clear()
    password_input.send_keys(password)
    time.sleep(2)

    password_input.send_keys(Keys.ENTER)


def create_directory(driver: webdriver.Chrome | webdriver.Firefox, number: int, path: str) -> str:
    """
    Create directory with name that it takes from materals page
    """
    soup = BeautifulSoup(driver.page_source, 'lxml')
    file_name = ic(soup.find('article', class_='material').find('h1').text)
    try:
        os.mkdir(fr"{path}\{number}_{file_name}")
    except Exception as ex:
        print(ex)
    finally:
        return fr"{path}\{number}_{file_name}"


def save_page(driver: webdriver.Chrome | webdriver.Firefox, file_path: str) -> bool:
    """
    Save page by its page_source
    """
    if os.path.exists(file_path):
        return False
    with open(file_path, 'wt', encoding='utf8') as file:
        file.writelines(driver.page_source)
    return True


def save_pagen(file_path: str) -> None:
    """
    Save page by simulating pressing ctrl+s by user
    """
    keyboard.send('ctrl+s')
    time.sleep(3)
    keyboard.write(file_path)
    time.sleep(1)
    keyboard.send('enter')
    time.sleep(5)


def stage_1(driver: webdriver.Chrome | webdriver.Firefox, page_url: str) -> bool:
    """
    Get lessons links from page
    """
    driver.get(page_url)
    time.sleep(5)
    authorizate(driver, login, password)
    time.sleep(5)

    urls: list = []
    soup: BeautifulSoup = BeautifulSoup(driver.page_source, 'lxml')
    for item in ic(soup.find_all('li', class_='link-list__item')[::-1]):
        url: str = ic(item.find('a', class_='link-list__link').get('href'))
        if '/tasks/' not in url:
            urls.append(url)
    open('stage_1', 'wt').writelines(urls)
    try:
        indx: int = len(open('download_queue', 'rt').readlines())
        open('download_queue', 'wt').writelines(urls[indx:])
    except FileNotFoundError:
        open('download_queue', 'wt').writelines(urls)
    print('Stage 1 have been completed')
    return True


def stage_2(driver: webdriver.Chrome | webdriver.Firefox) -> bool:
    """
    Through every lesson and create json/file with every task link, file with materials yand that's all
    """
    try:
        result: list = ic(json.load(open('stage_2.json', 'rt')))['data']
    except FileNotFoundError:
        result: list = ic([])

    for lesson_url in open('download_queue', 'rt').readlines():
        semi_result: list = []
        driver.get(lesson_url)
        time.sleep(3)

        soup: BeautifulSoup = BeautifulSoup(driver.page_source, 'lxml')
        mat_link: str = ic(soup.find('a', class_='material-list__material-link').get('href'))
        if mat_link:
            semi_result.append('https://lms.yandex.ru' + mat_link)
        else:
            semi_result.append('')

        semi_result.extend(list(map(lambda x: 'https://lms.yandex.ru' + x.get('href'),
                                    soup.find_all('a', class_='student-task-list__task'))))
        result.append(semi_result)
    json.dump({'data': result}, open('stage_2.json', 'wt'))
    print('Stage 2 have been completed')
    return True


def stage_4(driver: webdriver.Chrome | webdriver.Firefox, url_file_path: str, url_folder_path: str) -> None:
    """
    create files with urls inside the given folder
    """
    for url in ic(read_urls(url_file_path)):
        driver.get(ic(url))
        time.sleep(5)

        save_page(driver, '')
        time.sleep(10)


def stage_5(driver: webdriver.Chrome | webdriver.Firefox, url_folder_path: str, download_folder_path: str) -> None:
    """
    download all tasks and materials from folder with urls to given folder
    """
    materials = ic(read_urls(fr'{url_folder_path}\materials.txt'))

    for cnt in range(len(ic(materials))):
        if materials[cnt]:
            driver.get(materials[cnt])
            time.sleep(5)
            directory = create_directory(driver, cnt + 1, download_folder_path)
            save_page(driver, fr'{directory}\materials.html')
        else:
            ic(os.mkdir(fr"{download_folder_path}\{cnt + 1}_СИКР"))
            directory = fr"{download_folder_path}\{cnt + 1}_СИКР"

        ccnt = 1
        for url in read_urls(fr"{url_folder_path}\{cnt + 1}.txt"):
            driver.get(url)
            time.sleep(5)

            jk = 1
            while jk < 3:
                try:
                    driver.find_element(By.CLASS_NAME, 'y4ef2d--task-description-opener').find_element(By.TAG_NAME,
                                                                                                       'a').click()
                    jk = 5
                except Exception:
                    jk += 1
                    time.sleep(3)

            time.sleep(2)
            save_pagen(fr'{directory}\{ccnt}_task.html')
            ccnt += 1


def stage_6(directory: str) -> None:
    """
    file processing in directory
    """
    open(fr'{directory}\delete_all_js.bat', 'wt', encoding='utf-8').writelines(['@echo off\n', 'erase /s /q *.js\n'])
    subprocess.run(fr'{directory}\delete_all_js.bat')

    for folder in os.listdir(directory):
        if os.path.isdir(folder):
            os.chdir(folder)

            for file in os.listdir():
                if os.path.isfile(file):
                    redo_html_file(ic(file))

            os.chdir(directory)


def main(course_link: str) -> None:
    path = os.path.abspath(os.curdir)
    try:
        stage_num: int = int(open('progress', 'rt').readline()) or 0
    except FileNotFoundError:
        if os.listdir(path):
            print('NYADMORESPACE')
            return
        else:
            stage_num = 0

    driver = init_driver('Firefox')
    stages: dict = {stage_1: [driver, course_link], stage_2: [driver]}

    try:
        for stage in sorted(stages.keys())[stage_num:]:
            stage_num += stage(*stages[stage])
            ic(f'{stage_num} stages done')
            open('progress', 'wt').write(str(stage_num))
    except Exception as ex:
        print(ex)
    finally:
        driver.close()
        driver.quit()


if __name__ == '__main__':
    main(input('Link here: '))
