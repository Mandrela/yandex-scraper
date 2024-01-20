from rapsing import stage_1, init_driver


if __name__ == '__main__':
    odriver = init_driver('Firefox')
    try:
        stage_1(odriver, r'https://lms.yandex.ru/courses/1054/groups/9381')
    except Exception as ex:
        print(ex)
    finally:
        odriver.close()
        odriver.quit()
