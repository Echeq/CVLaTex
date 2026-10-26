"""Sample CVs for CVLaTeX.

Return dicts with the same shape as ``latex_gen.empty_data()`` filled with
realistic content in the language of the CV (Spanish, English or Chinese),
and without images, so the user sees how to complete each form section.

The three samples tell the same career story: identical dates, links, email
addresses, phone number, grades and entry counts. Only the prose, the labels
and the institution names are localized.
"""

import copy

import latex_gen


_LANGUAGES = ("zh", "es", "en")

# Header data shared by every language. The sample is deliberately fictional.
_EMAIL = "alex.ruiz@example.com"
_PHONE = "+34 600 000 000"
_SOCIALS = (
    {"network": "github", "label": "", "value": "github.com/example"},
    {"network": "linkedin", "label": "", "value": "linkedin.com/in/example"},
)

# Same institutions in the three samples; Chinese localizes their names.
_UNIVERSITIES = {
    "es": ("Universidad Politécnica de Madrid", "Universidad de Valladolid"),
    "en": ("Universidad Politécnica de Madrid", "Universidad de Valladolid"),
    "zh": ("马德里理工大学", "巴利亚多利德大学"),
}

_TEXT = {
    "es": {
        "name": "ALEJANDRO RUIZ MARTÍN",
        "profession": "Desarrollador de software backend",
        "address": "Madrid, España",
        "birth_label": "Nacimiento",
        "birth_value": "01/01/1995",
        "nationality_label": "Nacionalidad",
        "nationality_value": "Española",
        "summary": (
            "Desarrollador backend con seis años de experiencia en Python y Java. "
            "Especializado en APIs, microservicios y despliegues en la nube."
        ),
        "work_position": "Desarrollador Backend Senior",
        "work_end": "Actualidad",
        "work_achievements": (
            "Diseñé la API de pagos con FastAPI para más de dos millones de "
            "transacciones al mes.\n"
            "Mentoricé a tres desarrolladores junior y promoví las pruebas "
            "automatizadas."
        ),
        "internship1_position": "Becario de Desarrollo",
        "internship1_achievements": (
            "Automaticé los informes semanales con scripts de Python, ahorrando "
            "seis horas de trabajo."
        ),
        "internship2_position": "Becario de Análisis de Datos",
        "internship2_achievements": (
            "Limpié y analicé 200.000 registros de usuarios con Python y Pandas "
            "para el informe semanal de operaciones.\n"
            "Construí un panel de indicadores que redujo a la mitad el tiempo de "
            "preparación del informe mensual."
        ),
        "project1_name": "Rutas Sostenibles",
        "project1_description": (
            "Aplicación web que calcula rutas de transporte público con menor "
            "huella de carbono.\n"
            "Backend en Flask con datos abiertos GTFS y panel de estadísticas."
        ),
        "project1_result": "Primer premio del jurado entre 42 equipos",
        "project2_name": "Panel de Métricas Abiertas",
        "project2_description": (
            "Panel web que visualiza datos abiertos del Ayuntamiento de Madrid.\n"
            "Backend en FastAPI y PostgreSQL con actualización diaria de los datos."
        ),
        "project2_result": (
            "Más de 300 estrellas en GitHub y adoptado por tres organizaciones "
            "locales"
        ),
        "university_project_name": "Club de Robótica",
        "university_project_course": "Vocal de proyectos",
        "university_project_description": (
            "Coordiné talleres de robótica para estudiantes de primero y "
            "segundo curso.\n"
            "Organicé una competición interna con 12 equipos."
        ),
        "university_project_result": "Finalista en la competición regional",
        "degree_master": "Máster en Ingeniería Informática",
        "degree_bachelor": "Grado en Ingeniería del Software",
        "skill_languages": "Lenguajes",
        "skill_tools": "Herramientas",
        "skill_certs": "Certificaciones",
        "cert_values": "AWS Cloud Practitioner, Scrum Foundation",
        "language1": "Español",
        "language1_level": "Nativo",
        "language2": "Inglés",
        "language2_level": "C1 — Avanzado",
    },
    "en": {
        "name": "ALEJANDRO RUIZ MARTÍN",
        "profession": "Backend software developer",
        "address": "Madrid, Spain",
        "birth_label": "Date of birth",
        "birth_value": "01/01/1995",
        "nationality_label": "Nationality",
        "nationality_value": "Spanish",
        "summary": (
            "Backend developer with six years of experience in Python and Java, "
            "specializing in APIs, microservices and cloud deployments."
        ),
        "work_position": "Senior Backend Developer",
        "work_end": "Present",
        "work_achievements": (
            "Designed the payments API with FastAPI, handling more than two "
            "million transactions a month.\n"
            "Mentored three junior developers and championed automated testing."
        ),
        "internship1_position": "Software Development Intern",
        "internship1_achievements": (
            "Automated the weekly reports with Python scripts, saving six hours "
            "of work each week."
        ),
        "internship2_position": "Data Analysis Intern",
        "internship2_achievements": (
            "Cleaned and analysed 200,000 user records with Python and Pandas "
            "for the weekly operations report.\n"
            "Built a dashboard that halved the time needed to prepare the "
            "monthly report."
        ),
        "project1_name": "Sustainable Routes",
        "project1_description": (
            "Web app that calculates public transport routes with the lowest "
            "carbon footprint.\n"
            "Flask backend using open GTFS data, plus a statistics dashboard."
        ),
        "project1_result": "First prize from the jury among 42 teams",
        "project2_name": "Open Metrics Dashboard",
        "project2_description": (
            "Web dashboard that visualises open data from the City of Madrid.\n"
            "FastAPI and PostgreSQL backend with daily data refreshes."
        ),
        "project2_result": (
            "Over 300 stars on GitHub and adopted by three local organisations"
        ),
        "university_project_name": "Robotics Club",
        "university_project_course": "Project officer",
        "university_project_description": (
            "Coordinated robotics workshops for first- and second-year "
            "students.\n"
            "Organised an internal competition with 12 teams."
        ),
        "university_project_result": "Regional competition finalist",
        "degree_master": "Master's in Computer Engineering",
        "degree_bachelor": "Bachelor's in Software Engineering",
        "skill_languages": "Languages",
        "skill_tools": "Tools",
        "skill_certs": "Certifications",
        "cert_values": "AWS Cloud Practitioner, Scrum Foundation",
        "language1": "Spanish",
        "language1_level": "Native",
        "language2": "English",
        "language2_level": "C1 — Advanced",
    },
    "zh": {
        "name": "ALEJANDRO RUIZ MARTÍN",
        "profession": "后端软件开发工程师",
        "address": "西班牙马德里",
        "birth_label": "出生年月",
        "birth_value": "1995年1月1日",
        "nationality_label": "国籍",
        "nationality_value": "中国",
        "summary": (
            "拥有六年 Python 与 Java 开发经验的后端工程师，专注于 API、微服务"
            "与云端部署。"
        ),
        "work_position": "高级后端开发工程师",
        "work_end": "至今",
        "work_achievements": (
            "使用 FastAPI 设计支付 API，每月处理超过两百万笔交易。\n"
            "指导三名初级开发者，并推动自动化测试落地。"
        ),
        "internship1_position": "软件开发实习生",
        "internship1_achievements": (
            "使用 Python 脚本自动生成周报，每周节省六小时工作量。"
        ),
        "internship2_position": "数据分析实习生",
        "internship2_achievements": (
            "使用 Python 与 Pandas 清洗并分析 20 万条用户记录，为每周运营"
            "报告提供数据支持。\n"
            "搭建指标看板，将月度报告的准备时间缩短一半。"
        ),
        "project1_name": "可持续出行路线",
        "project1_description": (
            "计算碳排放最低的公共交通路线的 Web 应用。\n"
            "后端采用 Flask，接入 GTFS 开放数据，并提供统计面板。"
        ),
        "project1_result": "在 42 支队伍中获评委会一等奖",
        "project2_name": "开放指标看板",
        "project2_description": (
            "展示马德里市政府开放数据的 Web 指标看板。\n"
            "后端采用 FastAPI 与 PostgreSQL，数据每日更新。"
        ),
        "project2_result": "GitHub 获 300 余颗星，并被三家本地机构采用",
        "university_project_name": "机器人社团",
        "university_project_course": "项目负责人",
        "university_project_description": (
            "为大一、大二学生组织机器人工作坊。\n"
            "筹办 12 支队伍参加的校内比赛。"
        ),
        "university_project_result": "区域比赛决赛入围",
        "degree_master": "计算机工程硕士",
        "degree_bachelor": "软件工程学士",
        "skill_languages": "编程语言",
        "skill_tools": "工具",
        "skill_certs": "证书",
        "cert_values": "AWS 云从业者, Scrum Foundation",
        "language1": "西班牙语",
        "language1_level": "母语",
        "language2": "英语",
        "language2_level": "C1 — 高级",
    },
}


def _normalize_language(cv_language):
    """Return ``zh``, ``es`` or ``en``; fall back to ``es`` and never raise."""
    try:
        lang = str(cv_language or "es").strip().lower()
    except Exception:
        return "es"
    return lang if lang in _LANGUAGES else "es"


def _build_sample(lang):
    """Build the canonical career story with the text of ``lang``."""
    text = _TEXT[lang]
    university, bachelor_university = _UNIVERSITIES[lang]

    d = copy.deepcopy(latex_gen.empty_data())

    d["cv_language"] = lang
    d["template"] = "classic"
    d["name"] = text["name"]
    d["profession"] = text["profession"]
    d["email"] = _EMAIL
    d["phone"] = _PHONE
    d["address"] = text["address"]
    d["socials"] = copy.deepcopy(list(_SOCIALS))
    d["school_name"] = university

    d["extra_fields"] = [
        {"label": text["birth_label"], "value": text["birth_value"]},
        {"label": text["nationality_label"], "value": text["nationality_value"]},
    ]

    d["summary"] = text["summary"]

    d["work"] = [
        {
            "work_mode": "hybrid",
            "position": text["work_position"],
            "company": "Fintech Nova",
            "start": "2022",
            "end": text["work_end"],
            "achievements": text["work_achievements"],
            "logo": "",
        },
    ]

    d["internships"] = [
        {
            "work_mode": "onsite",
            "position": text["internship1_position"],
            "company": "Telecom Ibérica",
            "start": "2018",
            "end": "2019",
            "achievements": text["internship1_achievements"],
            "logo": "",
        },
        {
            "work_mode": "onsite",
            "position": text["internship2_position"],
            "company": "DataLab Valladolid",
            "start": "2017",
            "end": "2018",
            "achievements": text["internship2_achievements"],
            "logo": "",
        },
    ]

    d["projects"] = [
        {
            "name": text["project1_name"],
            "organization": "Hackathon Climate 2023",
            "start": "2023",
            "end": "2023",
            "description": text["project1_description"],
            "result": text["project1_result"],
            "link": "github.com/example/rutas-sostenibles",
            "logo": "",
        },
        {
            "name": text["project2_name"],
            "organization": "Open Data Madrid",
            "start": "2021",
            "end": "2021",
            "description": text["project2_description"],
            "result": text["project2_result"],
            "link": "github.com/example/panel-metricas",
            "logo": "",
        },
    ]

    d["university_projects"] = [
        {
            "name": text["university_project_name"],
            "course": text["university_project_course"],
            "organization": university,
            "start": "2018",
            "end": "2018",
            "description": text["university_project_description"],
            "result": text["university_project_result"],
            "link": "",
            "logo": "",
        },
    ]

    d["education"] = [
        {
            "degree_type": "master",
            "degree": text["degree_master"],
            "institution": university,
            "start": "2018",
            "end": "2020",
            "grade": "9.2 / 10",
            "logo": "",
        },
        {
            "degree_type": "bachelor",
            "degree": text["degree_bachelor"],
            "institution": bachelor_university,
            "start": "2014",
            "end": "2018",
            "grade": "8.5 / 10",
            "logo": "",
        },
    ]

    d["skills"] = [
        {"category": text["skill_languages"], "values": "Python, Java, SQL"},
        {"category": text["skill_tools"], "values": "Docker, Git, PostgreSQL"},
        {"category": text["skill_certs"], "values": text["cert_values"]},
    ]

    d["languages"] = [
        {"language": text["language1"], "level": text["language1_level"]},
        {"language": text["language2"], "level": text["language2_level"]},
    ]

    d["references"] = [
        {"name": "Ana Torres Ruiz", "contact": "ana.torres@fintechnova.com"},
    ]

    return d


def sample_data(cv_language="es"):
    """Return the sample CV in ``cv_language`` (``zh``, ``es`` or ``en``)."""
    return _build_sample(_normalize_language(cv_language))


def sample_data_zh():
    """Return the Chinese sample CV (same career story as the Spanish one)."""
    return sample_data("zh")


def sample_data_en():
    """Return the English sample CV (same career story as the Spanish one)."""
    return sample_data("en")
