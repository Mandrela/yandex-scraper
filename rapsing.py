import time
import os
import keyboard
import subprocess
import json
import sys

from icecream import ic
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
try:
    from login_password import login, password
except ModuleNotFoundError:
    print('No login_password.py')
    sys.exit(-1)

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
    soup: BeautifulSoup = BeautifulSoup(driver.page_source, 'lxml')
    folder_name: str = ic(soup.find('article', class_='material').find('h1').text.replace(' ', '_'))
    result_path: str = fr"{path}\{number}_{folder_name}"
    try:
        os.mkdir(result_path)
    except Exception:
        open(f'{result_path}/del.bat', 'wt', encoding='utf-8').writelines(['@echo off\n', 'erase /q /s *.html\n'])
        subprocess.run(f'{result_path}/del.bat')
    finally:
        return result_path


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


def stage_1(driver: webdriver.Chrome | webdriver.Firefox) -> bool:
    """
    Get lessons links from page
    """
    time.sleep(5)
    urls: list = []
    soup: BeautifulSoup = BeautifulSoup(driver.page_source, 'lxml')
    for item in ic(soup.find_all('li', class_='link-list__item')[::-1]):
        url: str = ic(item.find('a', class_='link-list__link').get('href'))
        if '/tasks/' not in url:
            urls.append('https://lms.yandex.ru' + url + '\n')
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
    Through every lesson and create json with every material and task link
    """
    try:
        result: list = ic(json.load(open('stage_2.json', 'rt')))['data']
    except FileNotFoundError:
        result: list = ic([])

    lessons_urls: list[str] = open('download_queue', 'rt').readlines()
    progress_cnt: int = 0
    progress_max: int = len(lessons_urls)
    sleep_time: int = 4
    print(f'Estimated time: {sleep_time * (progress_max - progress_cnt) / 60:.1f} min')
    for lesson_url in lessons_urls:
        if not progress_cnt % 5:
            print(f'{progress_cnt / progress_max * 100:.0f}%')

        semi_result: list = []
        driver.get(lesson_url)
        time.sleep(sleep_time)

        soup: BeautifulSoup = BeautifulSoup(driver.page_source, 'lxml')
        try:
            mat_link: str = ic(soup.find('a', class_='material-list__material-link').get('href'))
            semi_result.append('https://lms.yandex.ru' + mat_link)
        except AttributeError:
            semi_result.append('')

        semi_result.extend(list(map(lambda x: 'https://lms.yandex.ru' + x.get('href'),
                                    soup.find_all('a', class_='student-task-list__task'))))
        result.append(semi_result)
        progress_cnt += 1
    json.dump({'data': result}, open('stage_2.json', 'wt'))
    print('Stage 2 have been completed')
    return True


def stage_3(driver: webdriver.Chrome | webdriver.Firefox) -> bool:
    data = json.load(open('stage_2.json'))['data']
    result_folder_path: str = fr'{os.path.abspath(os.curdir)}\_result'
    if not os.path.exists(result_folder_path):
        os.mkdir(result_folder_path)
        start_point: int = 0
    else:
        start_point: int = max(map(lambda x: int(x.split('_')[0]) - 1 if os.path.isdir(x) else 0,
                                   os.listdir(result_folder_path) + ['0_0']))

    progress_max: int = len(data)
    progress_cnt: int = start_point
    sleep_time_1: int = 4
    sleep_time_2: int = 5
    print(f'Estimated time(rude): {((progress_max - progress_cnt) * (sleep_time_1 + 7 * (sleep_time_2 + 20)))/ 60:.1f}'
          f' min')
    for index, item in enumerate(data[start_point:]):
        if item[0]:
            driver.get(item[0])
            time.sleep(sleep_time_1)
            directory_path: str = create_directory(driver, index + 1, result_folder_path)
            save_page(driver, fr'{directory_path}\materials.html')
        else:
            directory_path: str = fr'{result_folder_path}\{index + 1}_СИКР'
            try:
                ic(os.mkdir(directory_path))
            except Exception:
                pass

        for number, url in enumerate(item[1:]):
            driver.get(url)
            time.sleep(sleep_time_2)

            for _ in range(3):
                try:
                    driver.find_element(By.CLASS_NAME, 'y4ef2d--task-description-opener').find_element(By.TAG_NAME,
                                                                                                       'a').click()
                    break
                except Exception:
                    time.sleep(3)

            time.sleep(2)
            save_pagen(fr'{directory_path}\{number + 1}_task.html')
        print(f'{progress_cnt / progress_max * 100:.0f}%')
        progress_cnt += 1
    return True


def stage_4(directory: str) -> bool:
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
    return True


def main(course_link: str) -> None:
    path = os.path.abspath(os.curdir)
    try:
        stage_num: int = int(open('progress', 'rt').readline())
    except FileNotFoundError:
        if os.listdir(path).remove('login_password.py'):
            print('NYADMORESPACE')
            sys.exit(-1)
        else:
            stage_num = 0

    driver = init_driver('Firefox')
    stages: dict = {stage_1: [driver], stage_2: [driver], stage_3: [driver], stage_4: [fr'{path}\_result']}

    try:
        driver.get(course_link)
        time.sleep(5)
        authorizate(driver, login, password)
        time.sleep(2)

        for stage in list(stages.keys())[stage_num:]:
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
