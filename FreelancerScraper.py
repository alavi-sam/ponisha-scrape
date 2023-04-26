import requests
from scraper import SQL
import time
from bs4 import BeautifulSoup
import jdatetime
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


class Request:
    def __init__(self, headless=True):
        self.opt = Options()
        self.opt.headless = headless
        self.driver = Chrome('chromedriver.exe', options=self.opt)

    def get(self, url):
        self.driver.get(url)
        return self.driver.page_source


def get_all_freelancers(page_number):
    url = f"https://ponisha.ir/search/freelancers/page/{page_number}"
    response = requests.get(url)
    parser = BeautifulSoup(response.content, 'html.parser')
    return [profile['href'] for profile in parser.find_all('a', {'class': 'avatar'})]


def get_last_page_number(url):
    headers = {'user-agent': "Mozilla\/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit\/537.36 (KHTML, like Gecko) Chrome\/60.0.3112.113 Safari\/537.36"}
    response = requests.get(url, headers=headers)
    parser = BeautifulSoup(response.content, 'html.parser')
    return int(parser.find('ul', {'class': 'pagination hidden-xs'}).find_all('li')[-2].text)


class FreelancerModel:
    def __init__(self, username=None, country=None, city=None, projects_done=None, followers=None,
                 description=None, skill_list=None, join_date=None, profile_url=None):
        self.username = username
        self.country = country
        self.city = city
        # self.projects_done = projects_done
        # self.followers = followers
        self.description = description
        self.skill_list = skill_list
        self.join_date = join_date
        self.profile_url = profile_url


class FreelancerScraper:

    date_dict = {
        "فروردین": 1,
        "اردیبهشت": 2,
        "خرداد": 3,
        "تیر": 4,
        "مرداد": 5,
        "شهریوری": 6,
        "مهر": 7,
        "آبان": 8,
        "آذر": 9,
        "دی": 10,
        "بهمن": 11,
        "اسفند": 12
    }

    def __init__(self, url):
        self.parser = self.get_content(url)
        self.model = FreelancerModel()
        self.model.profile_url = url

    @staticmethod
    def get_content(url):
        response = requests.get(url)
        content = BeautifulSoup(response.content, 'html.parser')
        return content

    def get_projects_done(self):
        self.model.projects_done = self.parser.find('li', {'class': 'user-projects-done grid-33'}).find(
                                                                                                'span', {'class': 'num'}
                                                                                                        ).text

    def get_username(self):
        self.model.username = self.parser.find(
            'div', {'class': 'username clearfix'}
        ).find_all('span')[-1].text

    def get_followers_number(self):
        self.model.followers = self.parser.find(
            'li', {'class': 'user-followers grid-33'}
        ).find('a').find('span')

    def get_description(self):
        self.model.description = self.parser.find('div', {'class': 'description pt'}).text

    def get_skill_list(self):
        skill_container = self.parser.find('div', {'class': 'col-md-offset-2'}).find_all('a')
        skill_list = [skill.text for skill in skill_container]
        self.model.skill_list = skill_list

    def get_geo(self):
        geo = self.parser.find('div', {'class': 'location tc-9'}).text
        self.model.country = geo.split(',')[0]
        self.model.city = geo.split(',')[1]

    def get_join_date(self):
        date_container = self.parser.find('div', {'class': 'joined-at fa-0-9em tc-9'}).text
        date_list = date_container.strip().split(":")[1].strip().split("آخرین فعالیت")[0].strip().split(" ")
        date_list[1] = self.date_dict[date_list[1]]
        date_list = list(map(date_list))
        gregorian_date = jdatetime.datetime(year=date_list[0], month=date_list[1], day=date_list[2]).togregorian()
        self.model.join_date = gregorian_date

    def to_model(self):
        self.get_skill_list()
        self.get_description()
        self.get_username()
        self.get_geo()
        self.get_join_date()
        # self.get_projects_done()
        # self.get_followers_number()
        return self.model


def insert_freelancer(model: FreelancerModel):
    instance = SQL()
    instance.connect()
    cnx = instance.connection.cursor()
    cnx.execute("""EXECUTE [dbo].[InsertFreeLancer] 
                   ?
                  ,?
                  ,?
                  ,?
                  ,?
                  ,?""".replace('\n', ' '), (
        model.username, model.profile_url, model.country, model.city, model.description, model.join_date
    ))
    cnx.commit()
    insetred_id = cnx.fetchone()[0]
    for skill in model.skill_list:
        cnx.execute("""EXECUTE [dbo].[InsertFreelanceSkill] 
                       ?
                      ,?""".replace('\n', ' '), (insetred_id, skill))

        cnx.commit()


if __name__ == "__main__":
    page_number = 1
    c = 0
    # last_page_number = get_last_page_number('https://ponisha.ir/search/freelancers/page/1')

    while True:
        try:
            links = get_all_freelancers(page_number)
        except:
            break
        for link in links:
            scraper = FreelancerScraper(url=link)
            freelancer_model = scraper.to_model()
            insert_freelancer(freelancer_model)
            c += 1
            print(c)

