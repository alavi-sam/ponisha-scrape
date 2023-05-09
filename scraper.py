import bs4
import requests
from bs4 import BeautifulSoup
import pandas as pd
import pyodbc
from DataAccessLayer.Connection import SQL


def get_cookie(username='alavi_amirmahdi@yahoo.com', password='im78cn23'):
    response = requests.post('https://ponisha.ir/login/', json={'username': username, 'password': password})
    return response.cookies


COOKIE = get_cookie()


def get_projects(page_number):
    url = f'https://ponisha.ir/search/projects/page/{page_number}'
    response = requests.get(url, cookies=COOKIE)
    parser = BeautifulSoup(response.content, 'html.parser')
    projects = parser.find_all('li', {'class': 'item relative'})
    return projects


def get_project_details(project_link):
    response = requests.get(project_link, cookies=COOKIE)
    return response


class ProjectPreviewParser:
    def __init__(self, project: bs4.Tag):
        self.project = project
        self.data_dict = dict()

    def get_link(self):
        url = self.project.find('a', {'class': 'absolute right0 left0 width-90 min-h-100 zx-900'.split(' ')})['href']
        return url

    def get_price(self):
        price = self.project.find('div', {'class': 'budget'}).find('span')['amount']
        return int(price)//10

    def get_skills(self):
        skill_list = list()
        container = self.project.find('div', {'class': 'labels clearfix'}).find_all('a')
        for label in container:
            skill_list.append(label['title'])
        return skill_list

    def get_bids(self):
        bids = self.project.find('div', {'class': 'col-sm-3 flip text-right full-height hidden-xs left'})\
            .find('div', {'class': 'row pt+'}).text
        bids_number = bids.split('پیشنهاد')[0].strip()
        return int(bids_number)

    def get_badges(self):
        is_urgent = False
        is_bold = False
        is_private = False
        is_fulltime = False
        container = self.project.find('div', {'class': 'labels clearfix'})
        labels = container.find_all('div', {'class': 'border-a border-color-12 pv ph+ border-rad-md border-thick'
                                                     ' text-center flip pull-left'})
        for label in labels:
            if label.text.strip() == 'فوری':
                is_urgent = True
            elif label.text.strip() == 'برجسته':
                is_bold = True
            elif label.text.strip() == 'محرمانه':
                is_private = True
            elif label.text.strip() == 'تمام وقت':
                is_fulltime = True

        return is_urgent, is_bold, is_private, is_fulltime

    def get_title(self):
        return self.project.find('a', {'class': 'no-link'})["title"]


class ProjectParser:
    def __init__(self, response: requests.Response):
        self.response = response
        self.parser = BeautifulSoup(response.content, 'html.parser')
        self.model = ProjectModel()

    def get_price(self):
        span_prices = self.parser.find(
            'div', {'class': 'row pv+++'}
        ).find(
            'div', {'class': 'clearfix rtl'}
        ).find_all('span')
        self.model.min_price, self.model.max_price = int(span_prices[0]["amount"]), int(span_prices[1]["amount"])

    def get_title(self):
        self.model.title = self.parser.find('h1', {'class': 'pv++'}).text.strip()

    def get_link(self):
        self.model.link = '/'.join(self.response.url.split('/')[:5])

    def get_description(self):
        paragraphs = self.parser.find('div', {'class': 'pt fa-1-2em lh-1-8'}).find_all('p')[1:]
        self.model.description = ''.join(list(map(lambda x: x.text.strip() + '\n', paragraphs)))

    def get_skills(self):
        skill_list = list()
        skill_container = self.parser.find_all('div', {'class': 'border-a border-color-3 pv ph+ border-rad-md border-thick text-center mv mh- flip pull-left'})
        for skill in skill_container:
            skill_list.append(skill.text)

        self.model.skills = skill_list



class ProjectPreviewModel:
    def __init__(self, link, price, skills, bids, is_urgent, is_bold, is_private, is_full, title):
        self.link = link
        self.price = price
        self.skills = skills
        self.bids = bids
        self.is_urgent = is_urgent
        self.is_bold = is_bold
        self.is_private = is_private
        self.is_fulltime = is_full
        self.title = title


class ProjectModel:
    def __init__(self, link, min_price, max_price, skills, bids, is_urgent, is_bold, is_private, is_full, title, employer):
        self.link = link
        self.min_price = min_price
        self.max_price = max_price
        self.skills = skills
        self.bids = bids
        self.is_urgent = is_urgent
        self.is_bold = is_bold
        self.is_private = is_private
        self.is_fulltime = is_full
        self.title = title
        self.employer = employer


def insert_to_db(project):
    global count_inserted_skill
    global count_inserted_projects
    global count_inserted_comb
    sql = SQL()
    sql.connect()
    cnx = sql.connection.cursor()
    cnx.execute(f"INSERT INTO ProjectsPreview\
                output inserted.ID\
                values (?, ?, ?, ?, ?, ?, ?, ?)",
                (project.title, project.price, project.link, project.bids, project.is_urgent, project.is_private,
                project.is_bold, project.is_fulltime)
                )
    count_inserted_projects += 1
    inserted_id = cnx.fetchone()[0]
    cnx.commit()
    for skill in project.skills:
        cnx.execute("SELECT skillName FROM Skills")
        skills_in_db = cnx.fetchall()
        if skill in list(map(lambda x: x[0], skills_in_db)):
            cnx.execute(f"SELECT ID FROM Skills where SkillName=?", skill)
            skill_id = cnx.fetchone()[0]
        else:
            cnx.execute(f"INSERT INTO Skills (SkillName)\
                        OUTPUT inserted.ID\
                        Values (?)", skill)
            count_inserted_skill += 1
            skill_id = cnx.fetchone()[0]
            cnx.commit()
        cnx.execute(f"INSERT INTO ProjectPreviewSkills(ProjectID, SkillID)\
                    Values(?, ?)", (inserted_id, skill_id))
        count_inserted_comb += 1
        cnx.commit()
        print(f"inserted skills: {count_inserted_skill} \ninserted projects: {count_inserted_projects}\n\
inserted comb: {count_inserted_comb}")


if __name__ == "__main__":
    count_inserted_skill = 0
    count_inserted_projects = 0
    count_inserted_comb = 0
    page_number = 1

    while True:
        # try:
            projects = get_projects(page_number)
            for project in projects:
                parser = ProjectPreviewParser(project)
                project_model = ProjectPreviewModel(parser.get_link(), parser.get_price(), parser.get_skills(), parser.get_bids(),
                                             parser.get_badges()[0], parser.get_badges()[1],  parser.get_badges()[2],
                                             parser.get_badges()[3], parser.get_title())
                insert_to_db(project_model)
            page_number += 1




## TODO: add get all projects function
## TODO: add Project class and extract all attrs